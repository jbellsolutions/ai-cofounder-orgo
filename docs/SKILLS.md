# Skills

Hermes loads its maintained bundled skill catalog plus this repository's custom
company skills. Official skill documentation:
[https://hermes-agent.nousresearch.com/docs/skills](https://hermes-agent.nousresearch.com/docs/skills).

## Installed for every profile

- `a2a-collaboration` — correct use of Bot Mode, A2A, Kanban, delegation, and
  the negotiation contract.
- `kanban-work` — durable task contracts, heartbeats, artifacts, reviews,
  blocking, and real completion.
- `approval-safety` — action tiers, approval scope, permanent denials,
  verification, and audit records.

## Role skills

- `ai-cofounder`
- `head-of-ops`
- `revenue-partner`
- `affiliate-revenue-partner`
- `finance-risk`
- `research-analysis`

Each profile receives only its own role skill plus the shared skills. The
installer does not replace an owner-modified skill on update unless the file is
still identical to the prior managed copy.

## Installing new skills

Treat a skill as executable instruction. Review source, commands, network
access, credential requirements, write behavior, and licensing before
installation. Keep `skills.write_approval` and `skills.guard_agent_created`
enabled. Install into the profile that needs the capability rather than every
profile. Test first with read-only inputs and a denied consequential action.

Never allow a downloaded skill to rewrite company policy, standing identity,
memory, or approval rules without a human-reviewed change.
