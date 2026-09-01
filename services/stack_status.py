#!/usr/bin/env python3
"""Report integration posture without printing any credential values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


PROFILES = (
    "default",
    "head-of-ops",
    "revenue-partner",
    "affiliate-revenue-partner",
    "finance-risk",
    "research-analysis",
)


def env_names(path: Path) -> set[str]:
    names: set[str] = set()
    if not path.exists():
        return names
    for line in path.read_text(errors="ignore").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            names.add(stripped.split("=", 1)[0].strip())
    return names


def nonsecret_env_value(path: Path, name: str, default: str = "") -> str:
    if not path.exists():
        return default
    for line in path.read_text(errors="ignore").splitlines():
        if line.split("=", 1)[0].strip() == name and "=" in line:
            return line.split("=", 1)[1].strip()
    return default


def hermes_get(profile: str, key: str) -> str:
    command = ["hermes"] if profile == "default" else ["hermes", "-p", profile]
    result = subprocess.run([*command, "config", "get", key], text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def enabled(value: str) -> bool:
    return value.lower() in {"true", "1", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home() / ".hermes")
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    env_file = home / ".env"
    names = env_names(env_file)
    honcho_profiles = {
        profile: hermes_get(profile, "memory.provider") == "honcho"
        for profile in PROFILES
        if profile == "default" or (home / "profiles" / profile).is_dir()
    }
    result = {
        "honcho": {
            "configured": (home / "honcho.json").is_file() or "HONCHO_API_KEY" in names,
            "profiles": honcho_profiles,
        },
        "agent_bundle": {
            "agent_cards_enabled": enabled(hermes_get("default", "mcp_servers.agent-cards.enabled")),
            "agentmail_enabled": enabled(hermes_get("default", "mcp_servers.agentmail.enabled")),
            "agentphone_enabled": enabled(hermes_get("default", "mcp_servers.agentphone.enabled")),
            "agentmail_key_present": "AGENTMAIL_API_KEY" in names,
            "agentphone_key_present": "AGENTPHONE_API_KEY" in names,
            "shared_with_workers": False,
            "worker_access": "a2a-request-to-default",
        },
        "latitude": {
            "observer_installed": (home / "plugins/latitude-observer/plugin.yaml").is_file(),
            "api_key_present": "LATITUDE_API_KEY" in names,
            "project_present": "LATITUDE_PROJECT_SLUG" in names,
            "capture_mode": nonsecret_env_value(env_file, "LATITUDE_CAPTURE_MODE", "metadata"),
            "workspace_mcp_enabled": enabled(hermes_get("default", "mcp_servers.latitude.enabled")),
        },
        "a2a": {
            "gateway_enabled": enabled(hermes_get("default", "gateway.platforms.a2a.enabled")),
            "multiplex_enabled": enabled(hermes_get("default", "gateway.multiplex_profiles")),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
