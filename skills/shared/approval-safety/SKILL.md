---
name: approval-safety
description: Apply the AI Co-Founder permission tiers, approval records, deny rules, verification requirements, and audit contract before consequential actions.
---

# Approval Safety

Read `policies/permissions.json` from the installed company assets before an
action whose effect leaves private analysis or internal drafting.

## Tiers

- Tier 0: read, research, analyze, organize, privately draft.
- Tier 1: scoped internal mutation such as Kanban and private artifacts.
- Tier 2: externally visible write. Require owner approval or an explicit
  pre-approved playbook whose scope, audience, duration, and stop rules match.
- Tier 3: money, contracts, commercial terms, sensitive access, integrations,
  profiles, or infrastructure. Require explicit owner approval.
- Tier 4: destructive or irreversible. Require owner approval and a separate
  target verification immediately before execution.

## Non-delegable denials

An agent never discloses credentials, expands its own permission, fabricates
approval, bypasses policy, alters the audit record, disables security, trusts
an unknown peer, or deletes a profile or computer through the Agent Factory.

An agent never stops, restarts, or signals its own gateway or supervisord, not
even to load a config change. A restart started from inside the gateway is
killed before it finishes, and the team goes silent. Say that a restart is
needed and ask the owner to send `/restart` or run
`supervisorctl restart cofounder-gateway`. If gateway-guard blocks a call, do
not look for another way around it.

Approval must identify request, action, scope, approver, time, expiry or
one-time use, and required verification. Approval for one action never carries
to a materially changed audience, message, amount, term, or system.

After an approved external write, read back the durable result or ID. Record
actor, role, task, action, resource, policy decision, approval, result, and
verification. If verification fails, report failure; do not claim completion.
