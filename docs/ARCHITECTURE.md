# Architecture

AI Co-Founder is a hybrid business-orchestration system built from persistent
Hermes profiles, one durable work board, authenticated agent communication, and
an encoded permission layer.

## The four planes

```text
Human interface       Slack · Telegram · Hermes Desktop
                           │
Executive control     AI Co-Founder (default profile)
                           │
Work and authority    Kanban board · org registry · permissions · approvals
                           │
Specialist team       Ops · Revenue · Affiliate · Finance/Risk · Research
                           │
Connected systems     Calendar · inbox · Drive · CRM · PandaDoc · approved MCPs
```

### Conversation plane

Hermes Bot Mode supports named profiles, direct bot-to-bot messages, group
rooms, and durable Bot Chats. A2A supplies a standards-based boundary for
processes, machines, and other agent frameworks. Conversation can request,
counter, consult, or report. It does not change authority.

### Workflow plane

Hermes Kanban is the source of truth for work that crosses agents. It stores
tasks, owners, dependencies, comments, heartbeats, reviews, retries, artifacts,
and completion state outside the chat transcript. The Co-Founder owns root
work; department leaders may create scoped child tasks.

### Authority plane

[`policies/permissions.json`](../policies/permissions.json) defines autonomy,
approval, and permanent denial. [`org/registry.json`](../org/registry.json)
defines managers, roles, toolsets, A2A capabilities, and Kanban authority. A
prompt cannot silently grant more authority than those artifacts.

### Execution plane

Each specialist is a separate Hermes profile with its own SOUL, configuration,
memory, sessions, skills, cron jobs, credentials, and state database. The
default gateway multiplexes the selected profiles, so one process can serve the
team while preserving profile-scoped state and secret lookup.

Hermes profiles are not operating-system sandboxes. A profile separates Hermes
state but does not by itself prevent the same OS user from reading another
directory. This template removes terminal access from the profile toolsets and
uses `terminal.home_mode: profile`, but materially incompatible secrets or
filesystem trust should still be separated onto different Orgo computers.

## Compact deployment

The default setup runs on one Orgo computer:

```text
ai-guy-cofounder
├── default                      AI Co-Founder + owner channels
├── head-of-ops                  named profile
├── revenue-partner              named profile
├── affiliate-revenue-partner    named profile
├── finance-risk                 named profile
└── research-analysis            named profile
```

One gateway owns Slack/Telegram, Kanban dispatch, Bot Mode, and port 9900. Each
named profile has a multiplex route and A2A Agent Card. This shape is easiest
to teach in a webinar and uses one Orgo computer slot.

## Production funding deployment

The generic repository can later be split without changing its role contract:

```text
Computer 1  AI Co-Founder Core
Computer 2  Leadership and Operations Hub
Computer 3  Existing Funding Revenue Partner
Computer 4  Reserved worker or regulated-data boundary
```

Tailscale provides private reachability. Per-peer A2A tokens provide identity,
allowlisting, rate limits, redaction, and audit. The existing Funding Revenue
Partner remains a peer instead of being overwritten by the generic template.

## Runtime pin and supply chain

The installer downloads the Hermes install script from the exact release
commit, verifies its SHA-256 hash, passes the exact tag and commit to the
official installer, and later verifies the checkout commit. This release is
pinned because it includes Bot Mode, `hermes peer`, selective multiplex
profile serving, Kanban, A2A profile routing, protected-instruction approvals,
and the global stop controls used by this template.

## Failure and recovery

- Provider/configuration errors block jobs before spending when Hermes can
  detect them.
- Kanban caps concurrent work at three tasks and one task per profile.
- Repeated tool failures hard-stop instead of merely warning.
- Tasks use durable state and idempotency keys instead of chat replay.
- `orgo/emergency-stop.sh` stops every gateway and disables Kanban dispatch
  without deleting profiles, work, logs, or approvals.
- `orgo/resume-team.sh` restores dispatch only after the owner resolves the
  stop reason.

Official references:

- [Hermes profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Hermes Bot Mode](https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode)
- [Hermes Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)
- [Hermes A2A](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/a2a)
- [Hermes v0.21.0 release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31)
