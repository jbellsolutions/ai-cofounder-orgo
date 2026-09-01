#!/usr/bin/env bash
# Install the AI Co-Founder core on an Orgo Linux computer.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_TAG="v2026.8.31"
HERMES_COMMIT="29112bef099274229cadff79cdff7bf7b99c4b77"
INSTALLER_SHA256="85ef536d455e51ab67aa74d79272efd49fe717597dbaadfd3cca179a905f4706"

say() { printf '\n%s\n' "$*"; }
fail() { printf '\nSetup stopped: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Linux" ] || fail "this installer belongs on the Orgo Linux computer"
if [ "$(id -u)" -eq 0 ]; then
  ELEVATE=()
else
  command -v sudo >/dev/null 2>&1 || fail "this account needs administrator access"
  ELEVATE=(sudo)
fi

say "AI Co-Founder for Orgo"
echo "This installs the public team profile and policy. Private account"
echo "connections remain on this computer and never enter the repository."

say "1 of 5 — Checking the computer"
if ! command -v git >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  "${ELEVATE[@]}" apt-get update -qq
  "${ELEVATE[@]}" apt-get install -y -qq ca-certificates curl git python3
fi

installed_commit=""
for candidate in /usr/local/lib/hermes-agent "$HERMES_HOME/hermes-agent"; do
  if [ -d "$candidate/.git" ]; then
    installed_commit="$(git -C "$candidate" rev-parse HEAD 2>/dev/null || true)"
    [ "$installed_commit" = "$HERMES_COMMIT" ] && break
  fi
done

if [ "$installed_commit" != "$HERMES_COMMIT" ]; then
  say "2 of 5 — Installing the reviewed Hermes v0.21.0 release"
  installer="$(mktemp)"
  trap 'rm -f "${installer:-}"' EXIT
  curl -fsSL "https://raw.githubusercontent.com/NousResearch/hermes-agent/$HERMES_COMMIT/scripts/install.sh" -o "$installer"
  actual_sha="$(sha256sum "$installer" | awk '{print $1}')"
  [ "$actual_sha" = "$INSTALLER_SHA256" ] || fail "the Hermes installer checksum did not match the reviewed release"
  bash "$installer" --skip-setup --branch "$HERMES_TAG" --commit "$HERMES_COMMIT" --force-commit
  rm -f "$installer"
  trap - EXIT
else
  say "2 of 5 — The reviewed Hermes release is already installed"
fi
command -v hermes >/dev/null 2>&1 || fail "Hermes did not install correctly"

say "3 of 5 — Installing the AI Co-Founder core"
python3 "$REPO_DIR/services/install_profiles.py" \
  --root "$REPO_DIR" --home "$HERMES_HOME" --mode cofounder

say "4 of 5 — Locking the human-facing channels until the owner connects them"
hermes config set gateway.platforms.slack.enabled false >/dev/null
hermes config set gateway.platforms.telegram.enabled false >/dev/null
mkdir -p "$HOME/Desktop"

say "5 of 5 — Verifying the core"
"$REPO_DIR/orgo/verify.sh" --allow-unconnected --core-only

cat <<'TEXT'

The AI Co-Founder core is installed.

Next:
  1. Run: hermes setup
  2. Confirm one harmless local answer.
  3. Run: ./orgo/create-team.sh

Create the team before connecting Slack, Telegram, Calendar, CRM, or proposals.
That lets the profiles inherit only the working model connection—not the
owner's human-channel or business-app credentials.
TEXT
