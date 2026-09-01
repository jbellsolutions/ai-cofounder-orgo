#!/usr/bin/env bash
# Create the five named leadership profiles after the model is connected.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

command -v hermes >/dev/null 2>&1 || { echo "Run orgo/setup.sh first." >&2; exit 1; }
[ -f "$HERMES_HOME/SOUL.md" ] || { echo "The Co-Founder core is missing. Run orgo/setup.sh first." >&2; exit 1; }

echo "Creating the AI Co-Founder leadership team"
echo "Named profiles inherit the current model connection. Human-channel and"
echo "business-app credentials are removed from every named profile."

python3 "$REPO_DIR/services/install_profiles.py" \
  --root "$REPO_DIR" --home "$HERMES_HOME" --mode team

hermes gateway install >/dev/null
hermes gateway restart >/dev/null 2>&1 || hermes gateway start >/dev/null
"$REPO_DIR/orgo/verify.sh" --allow-unconnected

cat <<'TEXT'

The leadership team is installed:
  Head of Operations
  Revenue Partner
  Affiliate Revenue Partner
  Finance & Risk Lead
  Research & Analysis Lead

Next: run ./orgo/connect-channels.sh and connect the Co-Founder to Slack or
Telegram. The other profiles are already available through Bot Mode, Kanban,
and their authenticated A2A routes.
TEXT
