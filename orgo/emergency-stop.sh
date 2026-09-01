#!/usr/bin/env bash
# Stop agent turns, Kanban dispatch, and all profile gateways.
set -euo pipefail

hermes config set kanban.dispatch_in_gateway false >/dev/null
hermes gateway stop --all >/dev/null 2>&1 || true
echo "Emergency stop applied: all gateways are stopped and Kanban dispatch is disabled."
echo "Existing profile data, tasks, logs, and approvals were preserved."
