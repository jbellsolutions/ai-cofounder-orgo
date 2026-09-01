#!/usr/bin/env bash
# Install the daily brief and weekly business review after channels are ready.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Where should scheduled output go?"
echo "  1. AI Co-Founder Bot Chat"
echo "  2. Slack home channel"
echo "  3. Telegram home chat"
read -r -p "Choose 1, 2, or 3: " choice
case "$choice" in
  1) deliver=bot-chat ;;
  2) deliver=slack ;;
  3) deliver=telegram ;;
  *) echo "Choose 1, 2, or 3." >&2; exit 1 ;;
esac

if ! hermes cron list | grep -Fq "AI Co-Founder Daily Brief"; then
  hermes cron create "every 1d at 08:00" "$(cat "$REPO_DIR/routines/daily-brief.prompt")" \
    --name "AI Co-Founder Daily Brief" --deliver "$deliver" --continuity
fi
if ! hermes cron list | grep -Fq "AI Co-Founder Weekly Review"; then
  hermes cron create "0 9 * * 1" "$(cat "$REPO_DIR/routines/weekly-review.prompt")" \
    --name "AI Co-Founder Weekly Review" --deliver "$deliver" --continuity
fi
echo "The daily brief and weekly review are scheduled in the computer's timezone."
