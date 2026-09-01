#!/usr/bin/env bash
# Owner-only approval for a persistent Agent Factory proposal.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
proposal_id="${1:-}"
approved_by="${2:-owner}"
[[ "$proposal_id" =~ ^ap_[0-9a-f]{12}$ ]] || {
  echo "Usage: ./orgo/approve-agent.sh ap_123456789abc [approver-name]" >&2
  exit 2
}

python3 "$HERMES_HOME/cofounder/services/agent_factory.py" \
  approve "$proposal_id" --approved-by "$approved_by"
echo "The proposal is approved once. Ask the Co-Founder to activate that exact proposal ID."
