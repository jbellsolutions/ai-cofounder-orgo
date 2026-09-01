# Business tools

AI Co-Founder ships with Hermes research, browser, file, memory, skills, tasks,
Kanban, vision, image, computer-use, scheduling, and A2A capabilities. External
business systems are attached only after the owner authorizes the specific
account.

## Calendar, inbox, Drive, CRM, and business apps

`./orgo/connect-tools.sh` connects one selected profile to Composio. The default
is AI Co-Founder:

```bash
./orgo/connect-tools.sh
./orgo/connect-tools.sh --profile head-of-ops
./orgo/connect-tools.sh --profile revenue-partner
```

Each profile receives its own private connector configuration. Attach only the
accounts and scopes that role needs. The connector is marked `untrusted`, so
content from email, documents, calendar descriptions, or CRM fields is data,
not agent authority.

Safe first tests:

- Read the next three calendar events; do not change anything.
- List three inbox subject lines; do not send, move, or mark anything.
- Read one approved Drive document; do not share or edit it.
- Count open CRM opportunities; do not change a record.

Calendar changes, sends, shares, CRM mutation, bulk work, and sensitive data
disclosure require approval under the permission policy.

## Proposals

The same helper registers PandaDoc's global or European MCP and starts its OAuth
flow. First ask for a private draft named `Connection Test`. Verify the draft
inside PandaDoc and confirm it has no recipient and was not sent.

Price, discount, terms, claims, recipient, and sending require the proper
approval. A draft is not a commercial commitment.

## Agent Factory

AI Co-Founder alone receives the local `mcp-agent-factory` toolset. The MCP
service can list templates, propose a role, list proposals, and activate an
already owner-approved proposal. See [Agent Factory](AGENT-FACTORY.md).

## Tool access versus permission

Tool availability is role-specific in [`org/registry.json`](../org/registry.json).
Permission is effect-specific in
[`policies/permissions.json`](../policies/permissions.json). Both must allow an
action. Access never overrides approval.
