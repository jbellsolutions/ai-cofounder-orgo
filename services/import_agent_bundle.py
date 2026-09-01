#!/usr/bin/env python3
"""Import Agent Bundle's temporary MCP config into the default Hermes profile."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("mcpServers"), dict):
        raise ValueError("Agent Bundle did not produce an MCP server map")
    return value


def secret_from(config: dict[str, Any], server: str, section: str, key: str) -> str:
    servers = config["mcpServers"]
    entry = servers.get(server)
    if not isinstance(entry, dict):
        return ""
    values = entry.get(section)
    if not isinstance(values, dict):
        return ""
    for candidate, value in values.items():
        if candidate.lower() == key.lower() and isinstance(value, str):
            return value.strip()
    return ""


def upsert_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text().splitlines() if path.exists() else []
    keys = set(values)
    kept = [line for line in existing if line.split("=", 1)[0].strip() not in keys]
    kept.extend(f"{key}={value}" for key, value in values.items())
    handle, temp_name = tempfile.mkstemp(prefix=".env.agent-bundle.", dir=path.parent)
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write("\n".join(kept) + "\n")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def config_set(key: str, value: Any) -> None:
    encoded = json.dumps(value, separators=(",", ":")) if not isinstance(value, str) else value
    result = subprocess.run(
        ["hermes", "config", "set", key, encoded],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"could not configure {key}: {result.stderr.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--sandbox", action="store_true")
    args = parser.parse_args()

    config = load(args.config.resolve())
    mail = secret_from(config, "agentmail", "headers", "x-api-key")
    phone = secret_from(config, "agentphone", "env", "AGENTPHONE_API_KEY")
    cards = isinstance(config["mcpServers"].get("agent-cards"), dict)
    if not mail or not phone or not cards:
        raise ValueError("Agent Bundle did not complete all three products")
    if not args.sandbox and (
        not re.fullmatch(r"am_[A-Za-z0-9_-]+", mail)
        or not re.fullmatch(r"sk_live_[A-Za-z0-9_-]+", phone)
    ):
        raise ValueError("Agent Bundle returned an unexpected credential format")

    upsert_env(args.home.expanduser().resolve() / ".env", {
        "AGENTMAIL_API_KEY": mail,
        "AGENTPHONE_API_KEY": phone,
    })
    config_set("mcp_servers.agent-cards.enabled", True)
    config_set("mcp_servers.agentmail.enabled", True)
    config_set("mcp_servers.agentphone.enabled", True)
    print(json.dumps({
        "agent_cards": "configured-test-mode",
        "agentmail": "configured",
        "agentphone": "configured",
        "credentials_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Agent Bundle import stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
