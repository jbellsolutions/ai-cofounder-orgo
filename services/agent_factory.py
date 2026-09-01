#!/usr/bin/env python3
"""Bounded persistent-profile factory for AI Co-Founder.

The MCP surface can propose, inspect, and activate an already owner-approved
proposal. Approval itself is deliberately CLI-only. There is no delete,
credential, permission, infrastructure, billing, or arbitrary-command action.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from typing import Any


NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
MODEL_SECRET_KEYS = {
    "AI_GATEWAY_API_KEY", "ANTHROPIC_API_KEY", "CEREBRAS_API_KEY",
    "COHERE_API_KEY", "DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY",
    "FIREWORKS_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
    "HF_TOKEN", "HUGGINGFACE_TOKEN", "LITELLM_API_KEY", "MINIMAX_API_KEY",
    "MISTRAL_API_KEY", "MODEL_API_KEY", "MOONSHOT_API_KEY", "NVIDIA_API_KEY",
    "NOUS_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
    "PERPLEXITY_API_KEY", "SAMBANOVA_API_KEY", "TOGETHER_API_KEY",
    "XAI_API_KEY", "ZAI_API_KEY",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def write_private(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.chmod(0o600)
    temp.replace(path)


def canonical_hash(proposal: dict[str, Any]) -> str:
    protected = {
        key: value
        for key, value in proposal.items()
        if key not in {"approval", "status", "activated_at", "proposal_hash"}
    }
    body = json.dumps(protected, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


class Factory:
    def __init__(self, state_dir: Path | None = None, assets_dir: Path | None = None):
        self.state = (state_dir or Path(os.environ.get("COFOUNDER_STATE_DIR", "~/.hermes/cofounder"))).expanduser().resolve()
        self.assets = (assets_dir or Path(os.environ.get("COFOUNDER_ASSETS_DIR", self.state / "assets"))).expanduser().resolve()
        self.policy = load(self.assets / "policies/agent-factory.json")
        self.registry = load(self.assets / "org/registry.json")
        self.proposals = self.state / "proposals"

    def template(self, template_id: str) -> tuple[Path, dict[str, Any]]:
        if template_id not in self.policy["allowed_template_ids"]:
            raise ValueError("template is not allowlisted")
        directory = self.assets / "agent-templates" / template_id
        template = load(directory / "template.json")
        if template.get("template_id") != template_id:
            raise ValueError("template identity mismatch")
        if not (directory / "SOUL.md").is_file():
            raise ValueError("template has no SOUL.md")
        return directory, template

    def propose(self, template_id: str, need: str, profile_name: str | None = None, manager: str | None = None) -> dict[str, Any]:
        if not need.strip():
            raise ValueError("need is required")
        _, template = self.template(template_id)
        name = (profile_name or template["default_profile_name"]).strip()
        if not NAME.fullmatch(name) or name == "default":
            raise ValueError("profile name must use lowercase letters, numbers, and dashes")
        profile_home = Path.home() / ".hermes/profiles" / name
        if profile_home.exists():
            raise ValueError("profile already exists")
        manager_id = (manager or template["manager"]).strip()
        known = {profile["id"] for profile in self.registry["profiles"]}
        known.update(path.name for path in (Path.home() / ".hermes/profiles").glob("*") if path.is_dir())
        if manager_id not in known:
            raise ValueError("manager does not exist")
        proposal_id = "ap_" + uuid.uuid4().hex[:12]
        proposal = {
            "schema_version": 1,
            "proposal_id": proposal_id,
            "status": "proposed",
            "created_at": now(),
            "template_id": template_id,
            "profile_name": name,
            "display_name": template["display_name"],
            "manager": manager_id,
            "need": need.strip(),
            "description": template["description"],
            "capabilities": template["capabilities"],
            "external_writes": False,
            "credentials": [],
            "human_approval_required": True,
        }
        proposal["proposal_hash"] = canonical_hash(proposal)
        write_private(self.proposals / f"{proposal_id}.json", proposal)
        return proposal

    def get(self, proposal_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"ap_[0-9a-f]{12}", proposal_id):
            raise ValueError("invalid proposal id")
        path = self.proposals / f"{proposal_id}.json"
        if not path.is_file():
            raise ValueError("proposal not found")
        return load(path)

    def list(self) -> list[dict[str, Any]]:
        if not self.proposals.exists():
            return []
        return [load(path) for path in sorted(self.proposals.glob("ap_*.json"))]

    def approve(self, proposal_id: str, approved_by: str) -> dict[str, Any]:
        if not approved_by.strip():
            raise ValueError("approved_by is required")
        proposal = self.get(proposal_id)
        if proposal["status"] not in {"proposed", "approved"}:
            raise ValueError("only a proposed profile can be approved")
        if proposal.get("proposal_hash") != canonical_hash(proposal):
            raise ValueError("proposal changed after creation")
        expected = f"APPROVE {proposal_id}"
        if not sys.stdin.isatty():
            raise ValueError("owner approval requires an interactive private terminal")
        entered = input(f"Type {expected} to approve persistent profile creation: ")
        if entered != expected:
            raise ValueError("approval phrase did not match")
        proposal["status"] = "approved"
        proposal["approval"] = {
            "approved_by": approved_by.strip(),
            "approved_at": now(),
            "one_time": True,
            "proposal_hash": proposal["proposal_hash"],
        }
        write_private(self.proposals / f"{proposal_id}.json", proposal)
        return proposal

    @staticmethod
    def _run(*args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(args, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
        return result

    @staticmethod
    def _config_set(profile: str, key: str, value: Any) -> None:
        args = ["hermes"] if profile == "default" else ["hermes", "-p", profile]
        encoded = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
        Factory._run(*args, "config", "set", key, encoded)

    @staticmethod
    def _scrub_env(home: Path) -> None:
        path = home / ".env"
        if not path.exists():
            return
        kept = []
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                kept.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in MODEL_SECRET_KEYS or key.startswith("HERMES_MODEL_"):
                kept.append(line)
        path.write_text("\n".join(kept) + ("\n" if kept else ""))
        path.chmod(0o600)

    def _current_dynamic_routes(self) -> tuple[list[str], dict[str, Any]]:
        initial = [profile["id"] for profile in self.registry["profiles"] if profile["id"] != "default"]
        routes = {}
        for profile in self.registry["profiles"]:
            if profile["id"] == "default":
                continue
            a2a = profile["a2a"]
            routes[profile["id"]] = {
                "profile": profile["id"], "path": a2a["path"].lstrip("/"),
                "tenant": a2a["tenant"], "name": profile["display_name"],
                "description": profile["description"],
                "advertised_toolsets": a2a["capabilities"], "timeout": 300,
            }
        for item in self.list():
            if item.get("status") != "active":
                continue
            name = item["profile_name"]
            if name not in initial:
                initial.append(name)
            routes[name] = {
                "profile": name, "path": name, "tenant": name,
                "name": item["display_name"], "description": item["description"],
                "advertised_toolsets": item["capabilities"], "timeout": 300,
            }
        return initial, routes

    def activate(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.get(proposal_id)
        if proposal["status"] == "active":
            return proposal
        if proposal["status"] != "approved" or not proposal.get("approval"):
            raise ValueError("owner approval record is required")
        if proposal.get("proposal_hash") != canonical_hash(proposal):
            raise ValueError("proposal changed after approval")
        if proposal["approval"].get("proposal_hash") != proposal["proposal_hash"]:
            raise ValueError("approval does not match proposal")
        directory, template = self.template(proposal["template_id"])
        profiles_root = Path.home() / ".hermes/profiles"
        active_count = sum(1 for path in profiles_root.glob("*") if path.is_dir()) if profiles_root.exists() else 0
        if active_count >= int(self.policy["max_active_named_profiles"]):
            raise ValueError("active profile cap reached")
        name = proposal["profile_name"]
        home = profiles_root / name
        if home.exists():
            raise ValueError("profile name is now in use")

        self._run("hermes", "profile", "create", name, "--clone", "--description", proposal["description"])
        self._scrub_env(home)
        shutil.copy2(directory / "SOUL.md", home / "SOUL.md")
        shared = self.assets / "skills" / "shared"
        if shared.exists():
            shutil.copytree(shared, home / "skills/shared", dirs_exist_ok=True)
        metadata = home / "profile.yaml"
        existing = metadata.read_text().splitlines() if metadata.exists() else []
        existing = [line for line in existing if not line.startswith("display_name:")]
        existing.append(f"display_name: {json.dumps(proposal['display_name'])}")
        metadata.write_text("\n".join(existing) + "\n")
        metadata.chmod(0o600)

        defaults = self.policy["activation_defaults"]
        for key, value in {
            "agent.bot_mode_protocol": True,
            "approvals.mode": "manual",
            "approvals.destructive_slash_confirm": True,
            "skills.write_approval": True,
            "skills.guard_agent_created": True,
            "tool_loop_guardrails.hard_stop_enabled": True,
            "terminal.home_mode": "profile",
            "gateway.multiplex_profiles": False,
            "gateway.platforms.slack.enabled": False,
            "gateway.platforms.telegram.enabled": False,
            "gateway.platforms.a2a.enabled": False,
            "mcp_servers.agent-factory.enabled": False,
            "platform_toolsets.cli": defaults["toolsets"],
            "platform_toolsets.a2a": defaults["a2a_inbound_toolsets"],
        }.items():
            self._config_set(name, key, value)

        proposal["status"] = "active"
        proposal["activated_at"] = now()
        write_private(self.proposals / f"{proposal_id}.json", proposal)
        allowlist, routes = self._current_dynamic_routes()
        self._config_set("default", "gateway.multiplex_profile_allowlist", allowlist)
        self._config_set("default", "gateway.platforms.a2a.extra.agents", routes)
        self._run("hermes", "gateway", "restart")
        return proposal


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled AI Co-Founder profile factory")
    sub = parser.add_subparsers(dest="command", required=True)
    propose = sub.add_parser("propose")
    propose.add_argument("template_id")
    propose.add_argument("--need", required=True)
    propose.add_argument("--name")
    propose.add_argument("--manager")
    approve = sub.add_parser("approve")
    approve.add_argument("proposal_id")
    approve.add_argument("--approved-by", required=True)
    activate = sub.add_parser("activate")
    activate.add_argument("proposal_id")
    show = sub.add_parser("show")
    show.add_argument("proposal_id")
    sub.add_parser("list")
    args = parser.parse_args()
    factory = Factory()
    if args.command == "propose":
        result = factory.propose(args.template_id, args.need, args.name, args.manager)
    elif args.command == "approve":
        result = factory.approve(args.proposal_id, args.approved_by)
    elif args.command == "activate":
        result = factory.activate(args.proposal_id)
    elif args.command == "show":
        result = factory.get(args.proposal_id)
    else:
        result = factory.list()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Agent Factory stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
