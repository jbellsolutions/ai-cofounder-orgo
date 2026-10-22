#!/usr/bin/env bash
# Resume the team after the owner resolves the stop reason.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

hermes config set kanban.dispatch_in_gateway true >/dev/null
python3 "$REPO_DIR/services/gateway_service.py" start
echo "The Co-Founder gateway and Kanban dispatcher are running again."
