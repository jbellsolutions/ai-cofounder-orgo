#!/usr/bin/env python3
"""Canary-first fleet releases across Orgo API and ordinary SSH hosts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import tempfile
from typing import Any
from urllib import error, parse, request


SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
GITHUB_REPO = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def validate_inventory(value: dict[str, Any], *, require_canary: bool = False) -> list[dict[str, Any]]:
    if value.get("schema_version") != 1:
        raise ValueError("unsupported inventory schema")
    owners = value.get("allowed_github_owners")
    targets = value.get("targets")
    if not isinstance(owners, list) or not owners or not isinstance(targets, list):
        raise ValueError("inventory needs an owner allowlist and targets")
    seen: set[str] = set()
    for target in targets:
        if not isinstance(target, dict) or not SAFE_ID.fullmatch(str(target.get("id", ""))):
            raise ValueError("every target needs a safe unique id")
        if target["id"] in seen:
            raise ValueError(f"duplicate target: {target['id']}")
        seen.add(target["id"])
        provider = target.get("provider")
        if provider not in {"orgo", "ssh"}:
            raise ValueError(f"unsupported provider for {target['id']}")
        repo = GITHUB_REPO.fullmatch(str(target.get("repository", "")))
        if not repo or repo.group(1).lower() not in {str(owner).lower() for owner in owners}:
            raise ValueError(f"repository for {target['id']} is outside the GitHub owner allowlist")
        if provider == "orgo" and not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
            str(target.get("computer_id", "")),
        ):
            raise ValueError(f"invalid Orgo computer id for {target['id']}")
        if provider == "ssh" and not SSH_HOST.fullmatch(str(target.get("ssh_host", ""))):
            raise ValueError(f"invalid SSH config host for {target['id']}")
        if target.get("channel") not in {"canary", "stable"}:
            raise ValueError(f"invalid release channel for {target['id']}")
    if require_canary and len([target for target in targets if target.get("enabled") and target.get("channel") == "canary"]) != 1:
        raise ValueError("exactly one enabled canary target is required")
    return targets


def resolve_commit(repository: str, ref: str) -> str:
    result = subprocess.run(["git", "ls-remote", repository, ref], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("could not resolve the release from GitHub")
    value = result.stdout.split()[0] if result.stdout.split() else ""
    if not COMMIT.fullmatch(value):
        raise RuntimeError("GitHub did not return one exact release commit")
    return value


def verify_release_contract(repository: str, commit: str) -> None:
    required = ("services/fleet_node.py", "services/install_profiles.py", "orgo/verify.sh", "fleet/release.json")
    with tempfile.TemporaryDirectory(prefix="ai-guy-release-check-") as directory:
        initialized = subprocess.run(["git", "init", "--quiet", "--bare", directory], capture_output=True)
        fetched = subprocess.run(
            ["git", "-C", directory, "fetch", "--quiet", "--depth", "1", repository, commit],
            capture_output=True,
        )
        if initialized.returncode or fetched.returncode:
            raise RuntimeError("could not inspect the exact release contract")
        for path in required:
            present = subprocess.run(["git", "-C", directory, "cat-file", "-e", f"{commit}:{path}"], capture_output=True)
            if present.returncode:
                raise ValueError(f"{repository} has not adopted the managed update contract at {commit[:12]}")


def orgo_credentials() -> tuple[str, str]:
    key = os.environ.get("ORGO_API_KEY", "").strip()
    base = os.environ.get("ORGO_API_BASE_URL", "https://api.orgo.ai").rstrip("/")
    if key:
        parsed = parse.urlparse(base)
        return key, base + "/api" if parsed.path in {"", "/"} else base
    path = Path.home() / ".orgo/credentials.json"
    value = load_json(path)
    profiles = value.get("profiles", {})
    selected = profiles.get(value.get("current", "default"), {}) if isinstance(profiles, dict) else {}
    key = str(selected.get("apiKey", "")).strip()
    base = str(selected.get("apiBaseUrl", base)).rstrip("/")
    if not key:
        raise RuntimeError("Orgo is not connected on this control computer")
    parsed = parse.urlparse(base)
    return key, base + "/api" if parsed.path in {"", "/"} else base


def remote_script(target: dict[str, Any], commit: str, run_id: str, action: str) -> str:
    values = (target["id"], target["repository"], commit, run_id)
    if not SAFE_ID.fullmatch(values[0]) or not GITHUB_REPO.fullmatch(values[1]) or not COMMIT.fullmatch(values[2]):
        raise ValueError("unsafe remote release value")
    if action not in {"deploy", "rollback"}:
        raise ValueError("unsupported remote release action")
    q_id, q_repo, q_commit, q_run = map(shlex.quote, values)
    if action == "rollback":
        return f"set -euo pipefail\npython3 \"$HOME/.local/share/ai-guy-fleet/releases/{q_id}/{q_commit}/services/fleet_node.py\" rollback --run-id {q_run} --target-id {q_id}\n"
    return f"""set -euo pipefail
base="$HOME/.local/share/ai-guy-fleet"
cache="$base/cache/{q_id}.git"
release="$base/releases/{q_id}/{q_commit}"
mkdir -p "$base/cache" "$base/releases/{q_id}"
if [ ! -d "$cache" ]; then git clone --quiet --mirror {q_repo} "$cache"; fi
git -C "$cache" remote set-url origin {q_repo}
git -C "$cache" fetch --quiet --prune origin
git -C "$cache" cat-file -e {q_commit}^{{commit}}
if [ ! -f "$release/services/fleet_node.py" ]; then
  temp="$(mktemp -d "$base/.release.XXXXXX")"
  git -C "$cache" archive {q_commit} | tar -x -C "$temp"
  mv "$temp" "$release"
fi
python3 "$release/services/fleet_node.py" deploy --release "$release" --run-id {q_run} --target-id {q_id}
"""


def execute(target: dict[str, Any], script: str) -> dict[str, Any]:
    if target["provider"] == "ssh":
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", target["ssh_host"], "bash", "-s"],
            input=script, text=True, capture_output=True, timeout=900,
        )
        output = result.stdout
        if result.returncode:
            raise RuntimeError(f"{target['id']} update failed")
    else:
        key, base = orgo_credentials()
        endpoint = f"{base}/computers/{parse.quote(target['computer_id'], safe='')}/bash"
        body = json.dumps({"command": script}).encode()
        req = request.Request(endpoint, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "ai-guy-fleet/1.0",
        })
        try:
            with request.urlopen(req, timeout=900) as response:
                payload = json.loads(response.read())
        except (error.URLError, error.HTTPError, ValueError) as exc:
            raise RuntimeError(f"{target['id']} Orgo update failed") from exc
        output = str(payload.get("output") or payload.get("stdout") or "")
        if payload.get("exit_code", payload.get("exitCode", 0)) != 0:
            raise RuntimeError(f"{target['id']} update failed")
    for line in reversed(output.splitlines()):
        if line.startswith("AI_GUY_RESULT="):
            return json.loads(line.split("=", 1)[1])
    raise RuntimeError(f"{target['id']} returned no signed-off health result")


def state_root() -> Path:
    root = Path.home() / ".local/state/ai-guy-fleet/runs"
    root.mkdir(parents=True, mode=0o700)
    os.chmod(root.parent, 0o700)
    os.chmod(root, 0o700)
    return root


def save_run(value: dict[str, Any]) -> None:
    path = state_root() / f"{value['run_id']}.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.chmod(0o600)
    os.replace(temp, path)


def load_run(run_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", run_id):
        raise ValueError("invalid run id")
    return load_json(state_root() / f"{run_id}.json")


def make_plan(inventory_path: Path, ref: str) -> dict[str, Any]:
    inventory = load_json(inventory_path)
    targets = validate_inventory(inventory, require_canary=True)
    enabled = [target for target in targets if target.get("enabled")]
    commits: dict[tuple[str, str], str] = {}
    for target in enabled:
        target_ref = str(target.get("ref") or ref)
        key = (target["repository"], target_ref)
        if key not in commits:
            commits[key] = resolve_commit(target["repository"], target_ref)
            verify_release_contract(target["repository"], commits[key])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    release_digest = hashlib.sha256(json.dumps({"|".join(key): value for key, value in commits.items()}, sort_keys=True).encode()).hexdigest()[:10]
    run_id = f"{stamp}-{release_digest}-{secrets.token_hex(2)}"
    inventory_bytes = inventory_path.resolve().read_bytes()
    return {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": stamp,
        "inventory": str(inventory_path.resolve()),
        "inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "ref": ref,
        "status": "planned",
        "targets": [
            {
                "id": target["id"],
                "channel": target["channel"],
                "ref": str(target.get("ref") or ref),
                "commit": commits[(target["repository"], str(target.get("ref") or ref))],
                "status": "pending",
            }
            for target in enabled
        ],
    }


def target_map(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = Path(run["inventory"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != run["inventory_sha256"]:
        raise ValueError("inventory changed after this release was planned; make a new plan")
    inventory = load_json(path)
    return {target["id"]: target for target in validate_inventory(inventory, require_canary=True) if target.get("enabled")}


def apply_group(run: dict[str, Any], channel: str, action: str = "deploy") -> None:
    inventory = target_map(run)
    for record in run["targets"]:
        if record["channel"] != channel:
            continue
        if action == "deploy" and record["status"] == "healthy":
            continue
        if action == "rollback" and record["status"] not in {"healthy", "complete"}:
            continue
        target = inventory[record["id"]]
        record["status"] = "updating" if action == "deploy" else "rolling-back"
        save_run(run)
        try:
            result = execute(target, remote_script(target, record["commit"], run["run_id"], action))
            record["status"] = result["status"]
        except Exception:
            record["status"] = "failed"
            run["status"] = "failed"
            save_run(run)
            raise
        save_run(run)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "plan", "canary", "promote", "rollback", "status"))
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--ref", default="refs/heads/main")
    parser.add_argument("--run-id")
    parser.add_argument("--approval")
    args = parser.parse_args()

    if args.command in {"validate", "plan"}:
        if not args.inventory:
            raise ValueError("this command requires --inventory")
        if args.command == "validate":
            targets = validate_inventory(load_json(args.inventory))
            print(json.dumps({"valid": True, "targets": len(targets)}, sort_keys=True))
            return 0
        run = make_plan(args.inventory, args.ref)
        save_run(run)
    else:
        if not args.run_id:
            raise ValueError("this command requires --run-id")
        run = load_run(args.run_id)

    if args.command == "plan":
        pass
    elif args.command == "canary":
        if run["status"] != "planned" or args.approval != f"CANARY {run['run_id']}":
            raise ValueError("canary requires a planned release and the exact approval record")
        apply_group(run, "canary")
        run["status"] = "canary-healthy"
        save_run(run)
    elif args.command == "promote":
        if run["status"] != "canary-healthy" or args.approval != f"PROMOTE {run['run_id']}":
            raise ValueError("promotion requires a healthy canary and the exact approval phrase")
        apply_group(run, "stable")
        run["status"] = "complete"
        save_run(run)
    elif args.command == "rollback":
        if args.approval != f"ROLLBACK {run['run_id']}":
            raise ValueError("rollback requires the exact approval phrase")
        apply_group(run, "stable", "rollback")
        apply_group(run, "canary", "rollback")
        run["status"] = "rolled-back"
        save_run(run)
    print(json.dumps(run, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Fleet manager stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
