# Update every agent safely

The normal owner experience is one sentence:

> Update all of my agents to the approved release.

The setup AI does the technical work. It returns once after the Co-Founder
canary is healthy and asks for one consequential decision: promote that exact
release to the remaining computers, or stop. The owner never needs to sign in
to every server or repeat installation steps.

## What happens behind that sentence

```text
Resolve exact commits
        │
        ▼
Create immutable plan ── no machine changes
        │
        ▼
Snapshot + update Co-Founder canary
        │
        ├── fails ── restore local snapshot, stop rollout
        │
        ▼
Verify profiles + gateway + A2A + repository tests
        │
        ▼
Owner approves this run
        │
        ▼
Update stable computers one at a time
        │
        ▼
Final health and version report
```

Orgo targets use the workspace-scoped Orgo API. DigitalOcean targets use an
existing, named SSH configuration. Both run the same node-side update contract,
so health checks and rollback behavior do not drift by host.

## First-time control-plane setup

The setup AI makes a private copy of
[`fleet/inventory.example.json`](../fleet/inventory.example.json) at:

```text
~/.config/ai-guy/fleet.json
```

It replaces the examples with verified Orgo computer IDs or SSH config names,
the correct GitHub repository for each agent, and one canary. This private file
contains routing information but no server password, API key, or agent secret.
It is never committed.

Each enabled repository must contain this same managed update contract. The
Co-Founder proves it first. Head of Ops, Revenue Partner, and future agent
repositories can adopt the contract individually before they are enabled in
the fleet.

## Commands the setup AI uses

These are documented for auditability; the owner does not need to type them.

```bash
python3 services/fleet_manager.py validate \
  --inventory ~/.config/ai-guy/fleet.json

python3 services/fleet_manager.py plan \
  --inventory ~/.config/ai-guy/fleet.json

python3 services/fleet_manager.py canary --run-id RUN_ID \
  --approval "CANARY RUN_ID"
```

The setup AI supplies that record only when the owner's current request clearly
authorizes an update. The owner does not have to copy or type the phrase.

After a clear owner approval for the healthy run, the setup AI records the
approval and promotes it:

```bash
python3 services/fleet_manager.py promote --run-id RUN_ID \
  --approval "PROMOTE RUN_ID"
```

If a previously healthy machine must be restored, the setup AI records the
owner's rollback decision and runs:

```bash
python3 services/fleet_manager.py rollback --run-id RUN_ID \
  --approval "ROLLBACK RUN_ID"
```

## What is preserved

- model, Slack, Telegram, app, Agent Bundle, Latitude, and Honcho credentials;
- OAuth sessions and connector authorization;
- Hermes conversations, task history, and Honcho memory;
- customer files and company operating data;
- local customizations outside files managed by the repository seed manifest.

Before a change, the node makes a private local snapshot of managed profiles,
skills, policy assets, plugin code, and configuration. Snapshots remain mode
`700/600` on that computer because configuration can be sensitive. A failed
install or health check automatically restores the snapshot and restarts the
gateway.

## Controls that cannot be bypassed by an agent

- Branch names are resolved to exact 40-character commits before deployment.
- GitHub repository owners must be allowlisted in the private inventory.
- Exactly one enabled canary is required.
- The inventory is hashed into the plan and cannot change mid-run.
- Stable promotion and rollback require a run-specific owner approval record.
- Computers update sequentially; one failure stops the rollout.
- Inventory cannot provide arbitrary commands or destination paths.
- The updater does not create/delete computers, change Orgo plans, change
  billing, rotate credentials, or grant itself new permissions.

## Current proof boundary

This repository is the first managed release and the AI Co-Founder is its
canary. A live rollout begins only after that computer exists, its private
inventory entry is verified, and the owner explicitly asks to update it.
Existing Orgo computers are never silently assumed to be the Co-Founder and
are not modified by template creation.
