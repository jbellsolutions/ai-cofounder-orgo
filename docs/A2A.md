# A2A: how the team talks and negotiates

Every profile is A2A-enabled, but the implementation deliberately uses the
right communication path for each distance.

## Same computer

- Bot Mode direct messages are best for short consultations and receipts.
- Bot Mode rooms are useful for a bounded leadership discussion.
- Kanban is required for durable work, dependencies, reviews, human input,
  retries, and artifacts.

Hermes itself recommends Kanban or in-process delegation for agents on the same
machine. A2A is the standards-based interface for process, machine, or framework
boundaries.

## A2A routes

One gateway on port 9900 advertises the team:

| Agent | Path | Capability summary |
|---|---|---|
| AI Co-Founder | `/` | Strategy, orchestration, priorities, decision briefs |
| Head of Operations | `/head-of-ops` | Operations, projects, calendar, documents, process |
| Revenue Partner | `/revenue-partner` | GTM, offers, pipeline, CRM, proposals |
| Affiliate Revenue Partner | `/affiliate-revenue-partner` | Affiliates, partnerships, enablement, reporting |
| Finance & Risk | `/finance-risk` | Economics, forecast, budget, evidence, risk |
| Research & Analysis | `/research-analysis` | Research, validation, comparison, synthesis |

Each path serves its own Agent Card and forwards the task into that profile's
persistent session. The default multiplex gateway remains the only listener.

## Security

A2A without a token binds only to localhost. Remote setup requires both a token
and an explicit wider bind. `orgo/connect-a2a.sh` uses:

- private Tailscale IPv4 addresses;
- separate incoming and outgoing URL-safe tokens;
- an authenticated peer name and trusted-peer allowlist;
- 60 requests per minute per identity;
- a three-turn anti-loop cap;
- Hermes prompt-injection filtering and outbound secret redaction;
- append-only `~/.hermes/a2a_audit.jsonl`;
- no outbound A2A tools inside an inbound A2A turn.

Do not expose port 9900 directly to the public internet. Do not use one shared
token for unrelated customers. Rotate a peer's token when its machine or
operator changes.

## Negotiation contract

Use the structured contract in
[`org/message-contract.json`](../org/message-contract.json):

```text
REQUEST  objective, deliverable, owner, scope, evidence, approval, acceptance
COUNTER  capacity, dependency, risk, or scoped alternative
COMMIT   task ID, assignee, due point, budget, acceptance tests
STATUS   progress, evidence, blocker, forecast
REVIEW   completed result and verification
ACCEPT   independent acceptance
REWORK   failed acceptance and required correction
ESCALATE unresolved authority, money, legal, privacy, security, or reputation
```

Conversation does not replace the Kanban task. A message cannot grant budget,
permission, or approval.

## Connect a separate computer

1. Join both computers to the same Tailscale network.
2. Generate a different incoming token on each computer.
3. On the Co-Founder computer, run `./orgo/connect-a2a.sh`.
4. Configure the reciprocal peer on the other computer.
5. Restart both gateways.
6. Fetch the root and named Agent Cards.
7. Send one harmless readiness request with a stable context ID.
8. Confirm the reply, conversation history, peer identity, route, and audit row.

## Acceptance test

Ask the external Funding Revenue Partner to review a fictional, non-sensitive
offer-fit scenario. It should answer as the correct role. Then address
`/finance-risk` on the Co-Founder computer and request an economics review. The
Finance & Risk profile should answer, the A2A audit should show the trusted peer
and route, and neither inbound turn should have an outbound A2A tool.

Official reference: [Hermes A2A](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/a2a).
