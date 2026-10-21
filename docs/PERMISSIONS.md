# Permissions and approvals

The policy is designed around the effect of an action, not how politely an
agent asks for it. Access to a tool is never assumed to be permission to use it.

## Action inventory

| Action | Risk class | Default |
|---|---|---|
| Read local/company context | Read-only local | Allow inside role |
| Read approved external source or account | External read | Allow inside approved scope |
| Write private artifact or update assigned task | Scoped local mutation | Allow and log |
| Send message, publish, schedule, change CRM/calendar, send proposal | External write | Approval or exact approved playbook |
| Spend, contract, set price/discount/affiliate term, add integration/profile/computer | High impact | Explicit owner approval |
| Delete data/profile/computer, bulk destructive mutation | Destructive | Owner approval plus target verification |
| Read or copy a credential | Credential-bearing | Minimize; never disclose; audit access |

The authoritative machine-readable version is
[`policies/permissions.json`](../policies/permissions.json).

## Approval is scoped

A valid approval names:

- request and task;
- exact action and target;
- audience, amount, terms, or data scope;
- approver;
- time and expiry or one-time use;
- verification required after execution.

Approval for one email is not approval for a campaign. Approval for a private
proposal draft is not approval to send it. Approval for one partner's terms is
not approval to reuse them. Material changes require a fresh decision.

## Role differences

AI Co-Founder can create root tasks, coordinate departments, and use the
bounded Agent Factory. It cannot bypass owner gates.

Department leaders can create child tasks inside their department. They cannot
change the org chart or grant themselves more tools.

Workers can update assigned work, attach evidence, request review, block, or
escalate. They cannot create root work, change policy, or act outside role.

Incoming A2A sessions have read, analysis, file, memory, and Kanban tools. They
do not receive outbound A2A, terminal, delegation, computer-use, credentials,
or external-write MCP tools. This blocks peer-driven fanout and confused-deputy
chains.

## Permanent denials

Agents cannot disclose credentials, fabricate approval, expand their own
permissions, bypass policy, alter or delete the audit record, disable security,
trust an unknown peer, delete profiles, delete infrastructure, access a
factory arbitrary-command surface, or stop, restart, or signal their own
gateway.

## Gateway restarts

Every conversation runs through the gateway. An agent that restarts it takes
the whole team offline, and a restart started from inside the gateway does not
finish, because the gateway's shutdown kills it before the replacement starts.
`gateway.self_restart` is a permanent denial, and these controls enforce it:

- The `gateway-guard` plugin is installed and enabled in every profile home,
  because Hermes loads plugins per profile. Its `pre_tool_call` hook blocks
  terminal, code, process, and MCP calls that would stop, restart, or signal
  the gateway or supervisord. It also blocks calls that reference
  `_HERMES_GATEWAY`, run `hermes update` or this repository's lifecycle
  scripts, or edit the guard, the plugin list, or `/etc/supervisor`.
- The gateway runs with `--external-supervisor`. That also turns on Hermes's
  own check in the gateway's terminal tool, which refuses
  `hermes gateway stop|restart` while the gateway is supervised.
- `services/gateway_service.py` refuses to restart, start, or pause the
  gateway when a gateway process calls it.
- Agent Factory activation does not restart the gateway. The owner sends
  `/restart` to load a new profile.

Only the owner restarts the gateway, with `/restart` or with
`supervisorctl restart cofounder-gateway` from a shell outside it. Running
`hermes gateway restart` from a shell fights the supervisor; see
[Operations](OPERATIONS.md#the-gateway).

## Verification and logging

Every consequential action records actor, role, task, resource, policy
decision, approval ID, result, and verification. An external write is complete
only after reading back a durable result or ID. Failure to verify is reported
as failure.

The automated repository tests confirm the role toolsets, inbound A2A deny
surface, approval tiers, permanent denial list, and absence of dangerous Agent
Factory tools. Live acceptance tests deliberately ask the Co-Founder to spend,
send, delete, and self-expand; each must stop.
