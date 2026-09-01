#!/usr/bin/env python3
"""Install and safely update the AI Co-Founder Hermes profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
MODEL_SECRET_KEYS = {
    "AI_GATEWAY_API_KEY",
    "ANTHROPIC_API_KEY",
    "CEREBRAS_API_KEY",
    "COHERE_API_KEY",
    "DASHSCOPE_API_KEY",
    "DEEPSEEK_API_KEY",
    "FIREWORKS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "LITELLM_API_KEY",
    "MINIMAX_API_KEY",
    "MISTRAL_API_KEY",
    "MODEL_API_KEY",
    "MOONSHOT_API_KEY",
    "NVIDIA_API_KEY",
    "NOUS_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "PERPLEXITY_API_KEY",
    "SAMBANOVA_API_KEY",
    "TOGETHER_API_KEY",
    "XAI_API_KEY",
    "ZAI_API_KEY",
}


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def hermes_args(profile: str, *args: str) -> list[str]:
    if profile == "default":
        return ["hermes", *args]
    return ["hermes", "-p", profile, *args]


def config_set(profile: str, key: str, value: Any) -> None:
    encoded = json.dumps(value, separators=(",", ":")) if not isinstance(value, str) else value
    result = run(*hermes_args(profile, "config", "set", key, encoded), check=False)
    if result.returncode:
        raise RuntimeError(f"could not set {key} for {profile}: {result.stderr.strip()}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {path}")
    return value


def load_manifest(path: Path) -> dict[str, str]:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def sync_file(source: Path, target: Path, prior: dict[str, str], current: dict[str, str]) -> None:
    key = str(target)
    source_hash = digest(source)
    previous_hash = prior.get(key)
    replace = not target.exists() or (previous_hash is not None and digest(target) == previous_hash)
    if replace:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        current[key] = source_hash
    else:
        current[key] = previous_hash or digest(target)


def sync_tree(source: Path, target: Path, prior: dict[str, str], current: dict[str, str]) -> None:
    for source_file in sorted(path for path in source.rglob("*") if path.is_file()):
        sync_file(source_file, target / source_file.relative_to(source), prior, current)


def set_profile_metadata(profile_home: Path, display_name: str, description: str) -> None:
    path = profile_home / "profile.yaml"
    lines = path.read_text().splitlines() if path.exists() else []
    kept = [line for line in lines if not line.startswith(("display_name:", "description:"))]
    kept.append(f"display_name: {json.dumps(display_name)}")
    kept.append(f"description: {json.dumps(description)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(kept) + "\n")
    path.chmod(0o600)


def scrub_named_profile_env(profile_home: Path) -> None:
    """Keep model credentials copied at creation; remove channels, apps, and peers."""
    env_file = profile_home / ".env"
    if not env_file.exists():
        return
    kept: list[str] = []
    for raw in env_file.read_text().splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            kept.append(raw)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in MODEL_SECRET_KEYS or key.startswith("HERMES_MODEL_"):
            kept.append(raw)
    env_file.write_text("\n".join(kept) + ("\n" if kept else ""))
    env_file.chmod(0o600)


def install_profile_files(
    root: Path,
    profile: dict[str, Any],
    profile_home: Path,
    prior: dict[str, str],
    current: dict[str, str],
) -> None:
    source_soul = root / "profiles" / profile["id"] / "SOUL.md"
    target_soul = profile_home / "SOUL.md"
    first_managed_install = str(target_soul) not in prior
    if target_soul.exists() and first_managed_install:
        backup = profile_home / "SOUL.md.before-ai-cofounder"
        if not backup.exists():
            shutil.copy2(target_soul, backup)
    if first_managed_install:
        target_soul.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_soul, target_soul)
        current[str(target_soul)] = digest(source_soul)
    else:
        sync_file(source_soul, target_soul, prior, current)
    sync_tree(root / "skills/shared", profile_home / "skills/shared", prior, current)
    role_name = profile["role_skill"].split("/")[-1]
    sync_tree(root / "skills/roles" / role_name, profile_home / "skills/roles" / role_name, prior, current)
    profile_home.chmod(0o700)
    target_soul.chmod(0o600)
    (profile_home / ".ai-cofounder-role").write_text(profile["id"] + "\n")
    set_profile_metadata(profile_home, profile["display_name"], profile["description"])


def configure_common(profile: dict[str, Any]) -> None:
    profile_id = profile["id"]
    settings: dict[str, Any] = {
        "agent.bot_mode_protocol": True,
        "agent.max_turns": 60,
        "agent.verify_on_stop": True,
        "approvals.mode": "manual",
        "approvals.mcp_reload_confirm": True,
        "approvals.destructive_slash_confirm": True,
        "skills.write_approval": True,
        "skills.guard_agent_created": True,
        "tool_loop_guardrails.hard_stop_enabled": True,
        "compression.tail_mode": "lean",
        "privacy.redact_pii": True,
        "security.redact_secrets": True,
        "terminal.home_mode": "profile",
    }
    for platform, toolsets in profile["toolsets"].items():
        settings[f"platform_toolsets.{platform}"] = toolsets
    if profile_id != "default":
        settings.update({
            "gateway.multiplex_profiles": False,
            "gateway.platforms.slack.enabled": False,
            "gateway.platforms.telegram.enabled": False,
            "gateway.platforms.a2a.enabled": False,
            "mcp_servers.agent-factory.enabled": False,
        })
    for key, value in settings.items():
        config_set(profile_id, key, value)


def served_agents(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    routes: dict[str, Any] = {}
    for profile in profiles:
        if profile["id"] == "default":
            continue
        a2a = profile["a2a"]
        routes[profile["id"]] = {
            "profile": profile["id"],
            "path": a2a["path"].lstrip("/"),
            "tenant": a2a["tenant"],
            "name": profile["display_name"],
            "description": profile["description"],
            "advertised_toolsets": a2a["capabilities"],
            "timeout": 300,
        }
    return routes


def configure_default_gateway(root_home: Path, profiles: list[dict[str, Any]]) -> None:
    named = [profile["id"] for profile in profiles if profile["id"] != "default"]
    service = root_home / "cofounder/services/agent_factory_mcp.py"
    state = root_home / "cofounder"
    python_candidates = (
        Path("/usr/local/lib/hermes-agent/venv/bin/python"),
        root_home / "hermes-agent/venv/bin/python",
    )
    hermes_python = next((str(path) for path in python_candidates if path.is_file()), sys.executable)
    settings: dict[str, Any] = {
        "gateway.multiplex_profiles": True,
        "gateway.multiplex_profile_allowlist": named,
        "gateway.platforms.a2a.enabled": True,
        "gateway.platforms.a2a.extra.port": 9900,
        "gateway.platforms.a2a.extra.advertised_toolsets": ["strategy", "orchestration", "decision-briefs"],
        "gateway.platforms.a2a.extra.agents": served_agents(profiles),
        "kanban.dispatch_in_gateway": True,
        "kanban.dispatch_interval_seconds": 30,
        "kanban.auto_decompose": True,
        "kanban.auto_decompose_per_tick": 1,
        "kanban.orchestrator_profile": "default",
        "kanban.max_in_progress": 3,
        "kanban.max_in_progress_per_profile": 1,
        "kanban.auto_promote_children": True,
        "kanban.failure_limit": 3,
        "mcp_servers.agent-factory.command": hermes_python,
        "mcp_servers.agent-factory.args": [str(service)],
        "mcp_servers.agent-factory.env": {
            "COFOUNDER_STATE_DIR": str(state),
            "COFOUNDER_ASSETS_DIR": str(state / "assets"),
        },
        "mcp_servers.agent-factory.trust": "trusted",
        "mcp_servers.agent-factory.enabled": True,
    }
    for key, value in settings.items():
        config_set("default", key, value)


def ensure_named_profile(profile: dict[str, Any], root_home: Path) -> Path:
    profile_id = profile["id"]
    if not PROFILE_NAME.fullmatch(profile_id):
        raise ValueError(f"invalid profile id: {profile_id}")
    profile_home = root_home / "profiles" / profile_id
    if not profile_home.exists():
        result = run(
            "hermes",
            "profile",
            "create",
            profile_id,
            "--clone",
            "--description",
            profile["description"],
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"could not create {profile_id}: {result.stderr.strip()}")
    scrub_named_profile_env(profile_home)
    return profile_home


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--mode", choices=("cofounder", "team", "all"), required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    root_home = args.home.expanduser().resolve()
    registry = load_json(root / "org/registry.json")
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("org registry has no profiles")
    by_id = {profile["id"]: profile for profile in profiles}
    if set(by_id) != {"default", "head-of-ops", "revenue-partner", "affiliate-revenue-partner", "finance-risk", "research-analysis"}:
        raise ValueError("initial profile roster does not match the release contract")

    root_home.mkdir(parents=True, exist_ok=True)
    state = root_home / "cofounder"
    manifest_path = state / "seed-manifest.json"
    prior = load_manifest(manifest_path)
    current: dict[str, str] = {}

    for source_name in ("org", "policies", "agent-templates", "services", "routines", "skills"):
        sync_tree(root / source_name, state / "assets" / source_name, prior, current)
    sync_tree(root / "services", state / "services", prior, current)
    sync_tree(root / "company", state / "company", prior, current)

    selected: list[dict[str, Any]] = []
    if args.mode in ("cofounder", "all"):
        selected.append(by_id["default"])
    if args.mode in ("team", "all"):
        for profile_id in ("head-of-ops", "revenue-partner", "affiliate-revenue-partner", "finance-risk", "research-analysis"):
            selected.append(by_id[profile_id])

    # Register the bounded MCP before the default toolset references its dynamic
    # mcp-agent-factory name. Team-only updates already have this from core setup.
    if args.mode in ("cofounder", "all"):
        configure_default_gateway(root_home, profiles)

    for profile in selected:
        profile_home = root_home if profile["id"] == "default" else ensure_named_profile(profile, root_home)
        install_profile_files(root, profile, profile_home, prior, current)
        configure_common(profile)

    configure_default_gateway(root_home, profiles)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    manifest_path.chmod(0o600)

    if args.mode in ("team", "all"):
        run("hermes", "kanban", "init")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Profile installation stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
