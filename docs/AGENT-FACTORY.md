# Controlled Agent Factory

The Agent Factory lets the Co-Founder identify a real capability gap, propose
an allowlisted persistent role, and activate the exact approved proposal. It is
not an unrestricted self-replication system.

## Available templates

- Content & Distribution Agent
- CRM & Proposal Coordinator
- Customer Success Agent
- Systems & Automation Agent

Each ships with a manager, mission, SOUL, capabilities, safe toolset, no human
channel credentials, no business-app credentials, no terminal, no external
write tools, and its own A2A route after activation.

## Lifecycle

1. Co-Founder checks whether the installed team can do the work.
2. It calls `agent_templates`, then `agent_propose` with the capability gap and
   intended manager.
3. The factory saves an immutable proposal and returns `ap_…`.
4. The owner reviews the role, reason, manager, tools, and profile cap.
5. A setup agent runs the private helper:

   ```bash
   ./orgo/approve-agent.sh ap_123456789abc owner-name
   ```

   The owner types the exact confirmation phrase. The approval is one-time and
   hash-bound to the unchanged proposal contents.
6. Co-Founder calls `agent_activate` for that proposal ID.
7. The factory checks template allowlist, unique name, existing manager,
   approval match, profile cap, role files, safe toolsets, and route uniqueness.
8. It creates the profile from the working model connection, strips channel and
   business-app credentials, installs the role and shared skills, registers the
   profile with Bot Mode and A2A, and restarts the multiplex gateway.
9. The Co-Founder assigns a safe identity and permission test before real work.

## Tools intentionally absent

There is no factory tool to approve, delete a profile, delete data, create or
resize an Orgo computer, change billing, grant a credential, change permission
or policy, trust a peer, or run an arbitrary command.

Retirement remains an owner-operated process because Hermes profile deletion
removes state. Back up/export the profile, reassign open tasks, revoke unique
credentials, remove routes, verify retention requirements, and then use the
standard Hermes deletion confirmation outside the Agent Factory.

## Profile cap

The default cap is 12 named profiles. More profiles increase model cost,
credential surface, routing complexity, and review load. Increase the cap only
through a reviewed policy change, not an agent request.
