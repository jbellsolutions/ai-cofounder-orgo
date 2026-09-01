# The managed-agent stack

This release adds the three services from the reference video to the AI
Co-Founder without turning them into three disconnected add-ons.

```text
Owner in Slack or Telegram
          │
          ▼
AI Co-Founder ── A2A + Kanban ── Leadership profiles
      │                                  │
      ├── Honcho memory ─────────────────┘
      ├── Latitude traces ───────────────┘
      └── Agent Bundle company identity
          (inbox, phone, TEST-mode card)
```

## What each service does

| Service | Job in this system | Scope |
|---|---|---|
| Honcho | Long-term reasoning memory and continuity between channels | Every profile is a distinct AI peer in one customer workspace |
| Agent Bundle | A company-owned inbox, phone number, and controlled card | Co-Founder only; other roles request action through A2A |
| Latitude | Traces, errors, token use, tool calls, evaluations, and improvement signals | One observer covers the multiplexed gateway and labels every profile |
| A2A | Requests, consultations, negotiation, and cross-computer handoffs | Every approved profile and authenticated external peer |
| Kanban | Durable work, dependencies, evidence, reviews, and retry state | Shared operating record for the team |

The separation is deliberate. Copying one inbox, phone, or card credential to
every profile would make revocation and attribution harder. The Co-Founder is
the identity broker: a worker sends a structured A2A request, policy decides
whether approval is required, and the Co-Founder performs the approved action.

## Connect it once

After the Co-Founder and team are installed, the setup AI runs:

```bash
./orgo/connect-agent-stack.sh
```

The owner handles only the private sign-in or verification screens. The helper:

1. connects Honcho and synchronizes a separate peer for every profile;
2. runs the pinned Agent Bundle installer, imports its credentials into the
   private default-profile environment, and leaves cards in TEST mode;
3. connects Latitude tracing in metadata-only or sanitized mode;
4. optionally authorizes Latitude's workspace-management MCP;
5. restarts Hermes and prints a status report containing key presence only,
   never credential values.

The repository update can install definitions and code, but it cannot safely
invent service accounts or complete private OAuth. Unconnected services remain
disabled and do not break the agent.

## Latitude privacy modes

**Metadata only** is the default. It records timing, model, token counts, tool
names, status, errors, approvals, subagents, and profile labels. It does not
send conversation or tool content.

**Sanitized semantic traces** additionally send bounded message and tool
content after Hermes secret-pattern redaction. Use this only when the owner
wants conversation-level evaluation, such as intent or frustration signals,
and the customer data policy permits it. There is no raw-capture mode.

The observer is bounded, asynchronous, HTTPS-only, and fail-open. If Latitude
is unavailable, the agent keeps working and drops telemetry rather than
blocking customer work.

## Official references

- [Honcho memory in Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho)
- [Agent Bundle](https://theagentbundle.com/)
- [Latitude OpenTelemetry exporter](https://docs.latitude.so/telemetry/otel-exporter)
- [Latitude MCP](https://docs.latitude.so/getting-started/mcp)
- [Hermes A2A](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/a2a)
