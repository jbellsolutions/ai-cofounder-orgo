#!/usr/bin/env bash
# Connect the whole local profile roster to one authenticated A2A peer.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="$HERMES_HOME/.env"
CONFIG_FILE="$HERMES_HOME/config.yaml"
PROFILES=(default head-of-ops revenue-partner affiliate-revenue-partner finance-risk research-analysis)

secret() { local value; read -r -s -p "$1: " value; printf '\n' >&2; printf '%s' "$value"; }
upsert() {
  local key=$1 value=$2 temp
  temp="$(mktemp "$HERMES_HOME/.env.tmp.XXXXXX")"
  awk -v key="$key" 'index($0, key "=") != 1 { print }' "$ENV_FILE" > "$temp"
  printf '%s=%s\n' "$key" "$value" >> "$temp"
  chmod 600 "$temp"
  mv "$temp" "$ENV_FILE"
}
current_value() {
  local key=$1
  awk -v key="$key" 'index($0, key "=") == 1 { sub("^[^=]*=", ""); print; exit }' "$ENV_FILE"
}

[ -f "$CONFIG_FILE" ] || { echo "Run orgo/setup.sh first." >&2; exit 1; }
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
command -v tailscale >/dev/null 2>&1 || {
  echo "Tailscale is required so A2A stays private. Install and connect it first." >&2
  exit 1
}
local_ip="$(tailscale ip -4 | head -n 1)"
[[ "$local_ip" =~ ^100\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "This computer is not connected to Tailscale." >&2
  exit 1
}

read -r -p "Peer name (for example funding-revenue): " peer_name
[[ "$peer_name" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "Use lowercase letters, numbers, and dashes." >&2; exit 1; }
read -r -p "Peer Tailscale IPv4 address: " peer_ip
[[ "$peer_ip" =~ ^100\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "That is not a Tailscale IPv4 address." >&2; exit 1; }
incoming="$(secret "Paste the token this peer will use to call the Co-Founder team")"
outgoing="$(secret "Paste the token the Co-Founder team will use to call this peer")"
[[ "$incoming" =~ ^[A-Za-z0-9._~-]{32,}$ ]] || { echo "Use a URL-safe incoming token at least 32 characters long." >&2; exit 1; }
[[ "$outgoing" =~ ^[A-Za-z0-9._~-]{32,}$ ]] || { echo "Use a URL-safe outgoing token at least 32 characters long." >&2; exit 1; }

existing_tokens="$(current_value A2A_PEER_TOKENS)"
filtered_tokens="$(printf '%s' "$existing_tokens" | tr ',' '\n' | awk -F: -v peer="$peer_name" '$1 != peer && NF == 2' | paste -sd, -)"
new_tokens="$peer_name:$incoming"
[ -n "$filtered_tokens" ] && new_tokens="$filtered_tokens,$new_tokens"
upsert A2A_PEER_TOKENS "$new_tokens"

existing_trusted="$(current_value A2A_TRUSTED_PEERS)"
new_trusted="$(printf '%s\n%s\n' "$(printf '%s' "$existing_trusted" | tr ',' '\n')" "$peer_name" | awk 'NF && !seen[$0]++' | paste -sd, -)"
upsert A2A_TRUSTED_PEERS "$new_trusted"
upsert A2A_HOST 0.0.0.0
upsert A2A_PORT 9900
upsert A2A_AGENT_NAME ai-cofounder
upsert A2A_PUBLIC_URL "http://$local_ip:9900"
upsert A2A_MAX_PINGPONG_TURNS 3
upsert A2A_RATE_LIMIT 60
unset incoming existing_tokens filtered_tokens new_tokens

for profile in "${PROFILES[@]}"; do
  if [ "$profile" = default ]; then
    HERMES=(hermes)
  else
    [ -d "$HERMES_HOME/profiles/$profile" ] || continue
    HERMES=(hermes -p "$profile")
  fi
  "${HERMES[@]}" config set "a2a_agents.$peer_name.url" "http://$peer_ip:9900" >/dev/null
  "${HERMES[@]}" config set "a2a_agents.$peer_name.auth.type" bearer >/dev/null
  "${HERMES[@]}" config set "a2a_agents.$peer_name.auth.token" "$outgoing" >/dev/null
  "${HERMES[@]}" config set "a2a_agents.$peer_name.timeout" 120 >/dev/null
done
unset outgoing

chmod 600 "$CONFIG_FILE" 2>/dev/null || true
hermes gateway restart >/dev/null 2>&1 || true
echo "A2A is configured for the trusted peer and every installed team profile."
echo "Test the peer's Agent Card, then send one harmless readiness request."
