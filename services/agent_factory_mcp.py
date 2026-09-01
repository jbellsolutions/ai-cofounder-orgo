#!/usr/bin/env python3
"""MCP surface for the bounded AI Co-Founder Agent Factory."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_factory import Factory  # noqa: E402

try:
    from mcp.server import MCPServer
except ImportError as exc:  # pragma: no cover - exercised in the Hermes venv
    raise SystemExit("Run this service with the Hermes virtualenv Python.") from exc


server = MCPServer(
    "ai-cofounder-agent-factory",
    instructions=(
        "Controlled persistent-profile factory. Proposals are safe. Activation "
        "succeeds only after a separate human approval record exists. No delete, "
        "credential, permission, infrastructure, billing, or command tool exists."
    ),
)


@server.tool()
def agent_templates() -> str:
    """List the persistent role templates the owner has allowlisted."""
    factory = Factory()
    rows = []
    for template_id in factory.policy["allowed_template_ids"]:
        _, template = factory.template(template_id)
        rows.append({
            "template_id": template_id,
            "display_name": template["display_name"],
            "manager": template["manager"],
            "description": template["description"],
            "requires_human_approval": True,
        })
    return json.dumps(rows, indent=2)


@server.tool()
def agent_propose(template_id: str, need: str, profile_name: str = "", manager: str = "") -> str:
    """Create a durable proposal for an allowlisted profile; does not activate it.

    Args:
        template_id: Exact template ID returned by agent_templates.
        need: Concrete capability gap and business reason.
        profile_name: Optional lowercase profile name.
        manager: Optional existing manager profile ID.
    """
    proposal = Factory().propose(template_id, need, profile_name or None, manager or None)
    return json.dumps({
        "proposal_id": proposal["proposal_id"],
        "status": proposal["status"],
        "profile_name": proposal["profile_name"],
        "human_approval_required": True,
        "next_step": "Ask the owner to approve this proposal through the private approval helper.",
    }, indent=2)


@server.tool()
def agent_proposals() -> str:
    """List profile proposals and their current status without exposing secrets."""
    rows = [
        {key: item.get(key) for key in ("proposal_id", "template_id", "profile_name", "manager", "status", "created_at", "activated_at")}
        for item in Factory().list()
    ]
    return json.dumps(rows, indent=2)


@server.tool()
def agent_activate(proposal_id: str) -> str:
    """Activate an already owner-approved proposal and register its safe A2A route.

    This call cannot create approval. It fails closed unless the private
    proposal carries a matching one-time owner approval record.
    """
    proposal = Factory().activate(proposal_id)
    return json.dumps({
        "proposal_id": proposal["proposal_id"],
        "status": proposal["status"],
        "profile_name": proposal["profile_name"],
        "activated_at": proposal.get("activated_at"),
    }, indent=2)


if __name__ == "__main__":
    asyncio.run(server.run_stdio_async())
