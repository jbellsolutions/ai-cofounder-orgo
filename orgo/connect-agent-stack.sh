#!/usr/bin/env bash
# Connect Honcho, Agent Bundle, and Latitude without exposing credentials.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="$HERMES_ROOT/.env"
PROFILES=(head-of-ops revenue-partner affiliate-revenue-partner finance-risk research-analysis)
AGENT_BUNDLE_INTEGRITY='sha512-hXdLoC8JU+1HUedAAnVD7eiZue+teY7roVv9pCYuqp793GxhbpCkZbNY+yxhnDciA68Bg3BgKh8gt8MGGLcxqA=='
AGENTPHONE_INTEGRITY='sha512-ijxBPb/L9SQVCZpjqmdU2dZhzuM2iMA1ZWUV/kTnd2W6n6VDtNLNNZMHi2AJvh5xNwBnmXe8kiQIR47z+ciVzA=='

mkdir -p "$HERMES_ROOT"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

secret() { local value; read -r -s -p "$1: " value; printf '\n' >&2; printf '%s' "$value"; }
upsert() {
  local key=$1 value=$2 temp
  temp="$(mktemp "$HERMES_ROOT/.env.stack.XXXXXX")"
  awk -v key="$key" 'index($0, key "=") != 1 { print }' "$ENV_FILE" > "$temp"
  printf '%s=%s\n' "$key" "$value" >> "$temp"
  chmod 600 "$temp"
  mv "$temp" "$ENV_FILE"
}

install_definitions() {
  python3 "$REPO_DIR/services/install_profiles.py" --root "$REPO_DIR" --home "$HERMES_ROOT" --mode cofounder
}

connect_honcho() {
  echo
  echo "Honcho gives every role continuous memory while keeping a distinct AI peer identity."
  hermes memory setup honcho
  hermes honcho sync
  hermes config set memory.provider honcho >/dev/null
  for profile in "${PROFILES[@]}"; do
    if [ -d "$HERMES_ROOT/profiles/$profile" ]; then
      hermes -p "$profile" config set memory.provider honcho >/dev/null
    fi
  done
  hermes honcho peers
}

connect_agent_bundle() {
  local bundle_config bundle_integrity phone_integrity
  echo
  echo "Agent Bundle creates one controlled company inbox, phone, and TEST-mode card."
  echo "The Co-Founder owns the credentials. Other roles request use through A2A."
  command -v node >/dev/null 2>&1 || { echo "Node.js 18 or newer is required." >&2; return 1; }
  bundle_integrity="$(npm view agentbundle-cli@0.2.2 dist.integrity)"
  phone_integrity="$(npm view agentphone-mcp@0.7.0 dist.integrity)"
  [ "$bundle_integrity" = "$AGENT_BUNDLE_INTEGRITY" ] || { echo "Agent Bundle package integrity did not match the reviewed release." >&2; return 1; }
  [ "$phone_integrity" = "$AGENTPHONE_INTEGRITY" ] || { echo "AgentPhone package integrity did not match the reviewed release." >&2; return 1; }
  bundle_config="$(mktemp "$HERMES_ROOT/agent-bundle.XXXXXX.json")"
  trap 'rm -f "${bundle_config:-}"' RETURN
  AGENT_BUNDLE_MCP_CONFIG="$bundle_config" npx --yes agentbundle-cli@0.2.2 --yes
  python3 "$REPO_DIR/services/import_agent_bundle.py" --config "$bundle_config" --home "$HERMES_ROOT"
  rm -f "$bundle_config"
  trap - RETURN
  echo "Authorize the Agentcard MCP connection. Cards remain in TEST mode."
  hermes mcp login agent-cards
}

connect_latitude() {
  echo
  echo "Latitude receives agent traces for monitoring and evaluation."
  echo "1. Sanitized semantic traces — supports intent and frustration signals"
  echo "2. Metadata only — timing, tools, model, errors, and tokens; no conversation content"
  read -r -p "Choose 1 or 2: " capture_choice
  case "$capture_choice" in
    1) capture_mode=sanitized ;;
    2) capture_mode=metadata ;;
    *) echo "Choose 1 or 2." >&2; return 1 ;;
  esac
  latitude_key="$(secret "Paste the Latitude project API key")"
  [ -n "$latitude_key" ] || { echo "The API key cannot be blank." >&2; return 1; }
  read -r -p "Paste the Latitude project slug: " latitude_project
  [ -n "$latitude_project" ] || { echo "The project slug cannot be blank." >&2; return 1; }
  [[ "$latitude_key" != *[[:space:]]* ]] || { echo "The API key format was not recognized." >&2; return 1; }
  [[ "$latitude_project" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || { echo "The project slug format was not recognized." >&2; return 1; }
  upsert LATITUDE_API_KEY "$latitude_key"
  upsert LATITUDE_PROJECT_SLUG "$latitude_project"
  upsert LATITUDE_CAPTURE_MODE "$capture_mode"
  unset latitude_key
  hermes plugins enable latitude-observer
  read -r -p "Also connect Latitude's workspace-management tools? [Y/n]: " connect_mcp
  case "${connect_mcp:-Y}" in
    Y|y|Yes|yes)
      hermes config set mcp_servers.latitude.enabled true >/dev/null
      hermes mcp login latitude
      ;;
    *) echo "Tracing is enabled; workspace-management tools remain disabled." ;;
  esac
}

show_status() {
  python3 "$REPO_DIR/services/stack_status.py" --home "$HERMES_ROOT"
}

if [ "${1:-}" = "--status" ]; then
  show_status
  exit 0
fi

install_definitions
echo "Connect the managed-agent stack"
echo "  1. Everything: Honcho + Agent Bundle + Latitude"
echo "  2. Honcho only"
echo "  3. Agent Bundle only"
echo "  4. Latitude only"
echo "  5. Show status"
read -r -p "Choose 1, 2, 3, 4, or 5: " choice
case "$choice" in
  1) connect_honcho; connect_agent_bundle; connect_latitude ;;
  2) connect_honcho ;;
  3) connect_agent_bundle ;;
  4) connect_latitude ;;
  5) show_status; exit 0 ;;
  *) echo "Choose 1, 2, 3, 4, or 5." >&2; exit 1 ;;
esac

hermes gateway restart >/dev/null 2>&1 || true
echo
echo "Stack connection complete. No credential values were printed."
show_status
