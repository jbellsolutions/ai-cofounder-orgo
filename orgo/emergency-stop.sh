#!/usr/bin/env bash
# Stop agent turns, Kanban dispatch, and every gateway until resume-team.sh.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
status=0

hermes config set kanban.dispatch_in_gateway false >/dev/null || status=1
# supervisorctl stop, never a kill: supervisord restarts a gateway that exits
# without being stopped through it. This also keeps the gateway down after a
# reboot, then stops any gateway supervisord does not own.
python3 "$REPO_DIR/services/gateway_service.py" stop || status=1

if [ "$status" -ne 0 ]; then
  echo "Emergency stop is incomplete; see the errors above." >&2
  exit 1
fi
echo "Emergency stop applied: all gateways are stopped and Kanban dispatch is disabled."
echo "The gateway stays stopped, including after a reboot, until ./orgo/resume-team.sh."
echo "Existing profile data, tasks, logs, and approvals were preserved."
