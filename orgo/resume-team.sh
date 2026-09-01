#!/usr/bin/env bash
# Resume the team after the owner resolves the stop reason.
set -euo pipefail

hermes config set kanban.dispatch_in_gateway true >/dev/null
hermes gateway start >/dev/null
echo "The Co-Founder gateway and Kanban dispatcher are running again."
