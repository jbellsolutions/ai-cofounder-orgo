# Operating the AI Co-Founder

## Daily

- Review the Co-Founder daily brief.
- Resolve owner decisions and expiring approvals.
- Inspect blocked, aging, failed, and review-stage Kanban work.
- Confirm the top three owned actions and stop lower-value drift.
- Watch model/provider errors, token or cost anomalies, and connector health.

Install the daily brief and weekly review after the destination channel works:

```bash
./orgo/setup-routines.sh
```

Scheduled jobs use continuity, so the brief can distinguish what is new from
what it already reported. They do not send or mutate business systems from the
prompt.

## Weekly

- Reconcile revenue, pipeline, delivery, customer, finance, and capacity data.
- Decide continue, modify, pause, or stop for every active initiative.
- Review agent accuracy, cost, repeated failures, rework, and approval events.
- Review A2A peers, unusual traffic, loop stops, and audit entries.
- Refresh company priorities and archive completed work without deleting audit.

## Emergency stop

From Slack use `/stop` for the active turn. For the whole team run:

```bash
./orgo/emergency-stop.sh
```

This stops every gateway and disables Kanban dispatch. It preserves profiles,
tasks, logs, approvals, and data for investigation. After resolving the cause:

```bash
./orgo/resume-team.sh
./orgo/verify.sh
```

## Backups

Use Hermes backup/profile export facilities before a runtime update, policy
change, profile retirement, or production split. Store backups privately; even
when exported keys are stripped, memory and session history may contain
sensitive business information.

## Updates

Do not track `latest`. Review a new Hermes release, update the tag, commit, and
installer hash together, run repository tests, deploy to a non-production
clone, test identity/tool denials/A2A/Kanban/restart, then promote. Owner-modified
SOUL and skills are preserved by the managed-seed manifest.

## Customer isolation

Use a separate Orgo workspace or clear customer trust boundary. Do not share
customer credentials, memory, tasks, or company context across installations.
A workspace payment plan is an account decision; it does not replace data and
permission isolation inside the computers.
