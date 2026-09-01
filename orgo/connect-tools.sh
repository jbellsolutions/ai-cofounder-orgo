#!/usr/bin/env bash
# Connect business tools to one explicitly selected profile.
set -euo pipefail

PROFILE="default"
if [ "${1:-}" = "--profile" ]; then
  PROFILE="${2:-}"
fi
case "$PROFILE" in
  default|head-of-ops|revenue-partner|affiliate-revenue-partner|finance-risk|research-analysis) ;;
  *) echo "Choose a profile from org/registry.json." >&2; exit 1 ;;
esac

HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
if [ "$PROFILE" = "default" ]; then
  PROFILE_HOME="$HERMES_ROOT"
  HERMES=(hermes)
else
  PROFILE_HOME="$HERMES_ROOT/profiles/$PROFILE"
  HERMES=(hermes -p "$PROFILE")
fi
ENV_FILE="$PROFILE_HOME/.env"
[ -d "$PROFILE_HOME" ] || { echo "That profile is not installed." >&2; exit 1; }
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

secret() { local value; read -r -s -p "$1: " value; printf '\n' >&2; printf '%s' "$value"; }
upsert() {
  local key=$1 value=$2 temp
  temp="$(mktemp "$PROFILE_HOME/.env.tmp.XXXXXX")"
  awk -v key="$key" 'index($0, key "=") != 1 { print }' "$ENV_FILE" > "$temp"
  printf '%s=%s\n' "$key" "$value" >> "$temp"
  chmod 600 "$temp"
  mv "$temp" "$ENV_FILE"
}

echo "Connect business tools to profile: $PROFILE"
echo "  1. Calendar, inbox, Drive, CRM, and apps through Composio"
echo "  2. PandaDoc proposals"
echo "  3. Show this profile's current connections"
read -r -p "Choose 1, 2, or 3: " choice
case "$choice" in
  1)
    echo "Open https://app.composio.dev and copy a consumer key beginning ck_."
    value="$(secret "Paste the ck_ consumer key")"
    [[ "$value" == ck_* ]] || { echo "The consumer key must begin with ck_." >&2; exit 1; }
    upsert COMPOSIO_API_KEY "$value"
    unset value
    "${HERMES[@]}" config set mcp_servers.composio.url https://connect.composio.dev/mcp >/dev/null
    "${HERMES[@]}" config set mcp_servers.composio.headers.x-consumer-api-key '${COMPOSIO_API_KEY}' >/dev/null
    "${HERMES[@]}" config set mcp_servers.composio.trust untrusted >/dev/null
    "${HERMES[@]}" config set mcp_servers.composio.timeout 180 >/dev/null
    "${HERMES[@]}" config set mcp_servers.composio.enabled true >/dev/null
    echo "Connect only the intended accounts in Composio."
    echo "First test: Read my next three calendar events. Do not change anything."
    ;;
  2)
    echo "  1. Global PandaDoc"
    echo "  2. European PandaDoc"
    read -r -p "Choose 1 or 2: " region
    case "$region" in
      1) url=https://mcp.pandadoc.com/v1/mcp ;;
      2) url=https://mcp.pandadoc.eu/v1/mcp ;;
      *) echo "Choose 1 or 2." >&2; exit 1 ;;
    esac
    "${HERMES[@]}" config set mcp_servers.pandadoc.url "$url" >/dev/null
    "${HERMES[@]}" config set mcp_servers.pandadoc.auth oauth >/dev/null
    "${HERMES[@]}" config set mcp_servers.pandadoc.trust untrusted >/dev/null
    "${HERMES[@]}" config set mcp_servers.pandadoc.timeout 180 >/dev/null
    "${HERMES[@]}" config set mcp_servers.pandadoc.enabled true >/dev/null
    "${HERMES[@]}" mcp login pandadoc
    echo 'First test: Create a private draft proposal titled "Connection Test". Do not send it.'
    ;;
  3) "${HERMES[@]}" mcp list ;;
  *) echo "Choose 1, 2, or 3." >&2; exit 1 ;;
esac

hermes gateway restart >/dev/null 2>&1 || true
