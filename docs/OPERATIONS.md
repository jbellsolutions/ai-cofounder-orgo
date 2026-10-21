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

## The gateway

One Hermes gateway serves every profile. It runs as the supervisord program
`cofounder-gateway`, which `./orgo/create-team.sh` installs at
`/etc/supervisor/conf.d/cofounder-gateway.conf`. supervisord restarts the
gateway after any exit, including a clean exit with code 0 or 1. The one
exception is code 78, Hermes's fatal-configuration exit, which needs a fix
rather than a retry.

The agent never restarts its own gateway. A restart started from inside the
gateway is killed by the gateway's own shutdown before it can start the
replacement, and that left a co-founder silent for 33 minutes on 2026-10-21.
The `gateway-guard` plugin blocks those tool calls in every profile. When a
change needs a restart, the Co-Founder asks the owner for one.

The owner restarts the gateway by sending `/restart` in Slack or Telegram, or
from a shell on the computer:

```bash
supervisorctl status cofounder-gateway
supervisorctl restart cofounder-gateway
```

Do not run `hermes gateway restart` or `hermes gateway stop` from a shell. On
an Orgo computer Hermes cannot see supervisord, so it fights the supervisor.
`stop` kills the supervised process, and supervisord starts it again.
`restart` stops it the same way, then tries to start a second gateway in the
foreground of your shell, racing supervisord's restart for the profile lock.
If the shell's copy wins, supervisord retries until the program is FATAL, and
the gateway dies when the shell closes. The `./orgo/connect-*.sh` scripts
already restart the gateway through supervisorctl.

Logs are in `/var/log/cofounder-gateway.log` and `~/.hermes/logs/gateway.log`.

## Emergency stop

From Slack use `/stop` for the active turn. For the whole team run:

```bash
./orgo/emergency-stop.sh
```

This stops the supervised gateway through supervisorctl, stops any other
gateway on the computer, and disables Kanban dispatch. The stop holds across a
reboot: the program's `autostart` stays off until you resume, and the connect
scripts will not start it either. It preserves profiles, tasks, logs,
approvals, and data for investigation. After resolving the cause:

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

Say “Update all of my agents to the approved release” to a setup AI with this
repository. It follows the canary, verification, promotion, and rollback
contract in [Fleet updates](FLEET-UPDATES.md). Do not track `latest`. Runtime
upgrades remain separately reviewed and pinned. Owner-modified SOUL and skills
are preserved by the managed-seed manifest.

## Customer isolation

Use a separate [Orgo](https://orgo.ai?r=aiguy) workspace or clear customer trust boundary. Do not share
customer credentials, memory, tasks, or company context across installations.
A workspace payment plan is an account decision; it does not replace data and
permission isolation inside the computers.
