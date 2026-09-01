#!/usr/bin/env python3
"""Atomic, credential-preserving release application on one Hermes computer."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any


SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")
PROFILES = ("head-of-ops", "revenue-partner", "affiliate-revenue-partner", "finance-risk", "research-analysis")


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def managed_paths(home: Path) -> list[Path]:
    hermes = home / ".hermes"
    paths = [
        hermes / "config.yaml",
        hermes / "SOUL.md",
        hermes / "profile.yaml",
        hermes / ".ai-cofounder-role",
        hermes / "skills/shared",
        hermes / "skills/roles/ai-cofounder",
        hermes / "plugins/latitude-observer",
        hermes / "cofounder/assets",
        hermes / "cofounder/services",
        hermes / "cofounder/company",
        hermes / "cofounder/seed-manifest.json",
    ]
    for profile in PROFILES:
        profile_home = hermes / "profiles" / profile
        paths.extend((
            profile_home / "config.yaml",
            profile_home / "SOUL.md",
            profile_home / "skills",
            profile_home / "profile.yaml",
            profile_home / ".ai-cofounder-role",
        ))
    return paths


def copy_path(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def snapshot(home: Path, state_root: Path, run_id: str) -> Path:
    backup = state_root / "backups" / run_id
    if backup.exists():
        raise ValueError("a backup already exists for this run")
    files = backup / "files"
    files.mkdir(parents=True, mode=0o700)
    os.chmod(backup, 0o700)
    os.chmod(files, 0o700)
    records: list[dict[str, Any]] = []
    for path in managed_paths(home):
        relative = path.relative_to(home)
        exists = path.exists() or path.is_symlink()
        records.append({"path": str(relative), "existed": exists})
        if exists:
            copy_path(path, files / relative)
    profile_roots = [
        {"path": str((home / ".hermes/profiles" / profile).relative_to(home)), "existed": (home / ".hermes/profiles" / profile).is_dir()}
        for profile in PROFILES
    ]
    current_path = state_root / "current.json"
    previous_current = json.loads(current_path.read_text()) if current_path.is_file() else None
    (backup / "manifest.json").write_text(json.dumps({
        "paths": records,
        "profile_roots": profile_roots,
        "previous_current": previous_current,
    }, indent=2) + "\n")
    (backup / "manifest.json").chmod(0o600)
    return backup


def restore(home: Path, backup: Path) -> None:
    manifest = json.loads((backup / "manifest.json").read_text())
    for record in manifest["paths"]:
        target = home / record["path"]
        remove_path(target)
        if record["existed"]:
            copy_path(backup / "files" / record["path"], target)
    for record in manifest.get("profile_roots", []):
        if not record["existed"]:
            remove_path(home / record["path"])
    current_path = backup.parents[1] / "current.json"
    if manifest.get("previous_current") is None:
        remove_path(current_path)
    else:
        current_path.write_text(json.dumps(manifest["previous_current"], indent=2, sort_keys=True) + "\n")
        current_path.chmod(0o600)


def gateway(action: str) -> None:
    if not shutil.which("hermes"):
        return
    run(["hermes", "gateway", action], check=False)


def emit(value: dict[str, Any]) -> None:
    print("AI_GUY_RESULT=" + json.dumps(value, separators=(",", ":"), sort_keys=True))


def deploy(args: argparse.Namespace, home: Path, state_root: Path) -> int:
    release = args.release.resolve()
    required = (release / "services/install_profiles.py", release / "orgo/verify.sh", release / "fleet/release.json")
    if not all(path.is_file() for path in required):
        raise ValueError("release is missing the managed update contract")
    static = run([str(release / "orgo/verify.sh"), "--static"], check=False)
    if static.returncode:
        raise RuntimeError("release failed static verification before installation")

    backup = snapshot(home, state_root, args.run_id)
    gateway("stop")
    try:
        installed = run([
            sys.executable,
            str(release / "services/install_profiles.py"),
            "--root", str(release),
            "--home", str(home / ".hermes"),
            "--mode", "all",
        ], check=False)
        if installed.returncode:
            raise RuntimeError("profile installation did not complete")
        gateway("restart")
        verified = run([str(release / "orgo/verify.sh"), "--allow-unconnected"], check=False)
        if verified.returncode:
            raise RuntimeError("post-update verification did not pass")
    except Exception:
        gateway("stop")
        restore(home, backup)
        gateway("restart")
        emit({"action": "deploy", "status": "rolled-back", "run_id": args.run_id, "target": args.target_id})
        raise

    current = {
        "run_id": args.run_id,
        "target": args.target_id,
        "release": str(release),
        "stack_version": json.loads((release / "fleet/release.json").read_text())["stack_version"],
        "updated_at": int(time.time()),
    }
    (state_root / "current.json").write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    (state_root / "current.json").chmod(0o600)
    emit({"action": "deploy", "status": "healthy", **current})
    return 0


def rollback(args: argparse.Namespace, home: Path, state_root: Path) -> int:
    backup = state_root / "backups" / args.run_id
    if not (backup / "manifest.json").is_file():
        raise ValueError("no rollback snapshot exists for this run")
    gateway("stop")
    restore(home, backup)
    gateway("restart")
    emit({"action": "rollback", "status": "restored", "run_id": args.run_id, "target": args.target_id})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("deploy", "rollback"))
    parser.add_argument("--release", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    if not SAFE_ID.fullmatch(args.target_id) or not RUN_ID.fullmatch(args.run_id):
        raise ValueError("invalid target or run identifier")
    if args.action == "deploy" and args.release is None:
        raise ValueError("deploy requires --release")

    home = args.home.expanduser().resolve()
    state_root = home / ".local/state/ai-guy-fleet"
    state_root.mkdir(parents=True, mode=0o700)
    os.chmod(state_root, 0o700)
    with (state_root / "update.lock").open("w") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return deploy(args, home, state_root) if args.action == "deploy" else rollback(args, home, state_root)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BlockingIOError:
        print("Another agent update is already running.", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"Fleet node stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
