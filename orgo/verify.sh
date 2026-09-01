#!/usr/bin/env bash
set -euo pipefail

ALLOW_UNCONNECTED=false
CORE_ONLY=false
STATIC_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --allow-unconnected) ALLOW_UNCONNECTED=true ;;
    --core-only) CORE_ONLY=true ;;
    --static) STATIC_ONLY=true ;;
    *) echo "Unknown verification option: $arg" >&2; exit 2 ;;
  esac
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
EXPECTED_COMMIT="29112bef099274229cadff79cdff7bf7b99c4b77"

python3 -m json.tool "$REPO_DIR/orgo/deployment.json" >/dev/null
python3 -m json.tool "$REPO_DIR/org/registry.json" >/dev/null
python3 -m json.tool "$REPO_DIR/org/message-contract.json" >/dev/null
python3 -m json.tool "$REPO_DIR/policies/permissions.json" >/dev/null
python3 -m json.tool "$REPO_DIR/policies/agent-factory.json" >/dev/null
python3 -m json.tool "$REPO_DIR/slack-manifest.json" >/dev/null
python3 -m json.tool "$REPO_DIR/stack/manifest.json" >/dev/null
python3 -m json.tool "$REPO_DIR/fleet/release.json" >/dev/null
python3 -m json.tool "$REPO_DIR/fleet/inventory.example.json" >/dev/null
find "$REPO_DIR/orgo" -type f -name '*.sh' -print0 | xargs -0 bash -n
python3 -m compileall -q "$REPO_DIR/services" "$REPO_DIR/plugins" "$REPO_DIR/tests"
python3 -m unittest discover -s "$REPO_DIR/tests" -p 'test_*.py' -v

if [ "$STATIC_ONLY" = true ]; then
  echo "AI Co-Founder static verification passed."
  exit 0
fi

command -v hermes >/dev/null 2>&1 || { echo "Hermes is not installed." >&2; exit 1; }
[ -f "$HERMES_HOME/SOUL.md" ]
[ -f "$HERMES_HOME/skills/roles/ai-cofounder/SKILL.md" ]
[ -f "$HERMES_HOME/cofounder/assets/policies/permissions.json" ]
[ -f "$HERMES_HOME/cofounder/services/agent_factory_mcp.py" ]
[ -f "$HERMES_HOME/plugins/latitude-observer/plugin.yaml" ]

installed=""
for candidate in /usr/local/lib/hermes-agent "$HERMES_HOME/hermes-agent"; do
  if [ -d "$candidate/.git" ]; then
    installed="$(git -C "$candidate" rev-parse HEAD 2>/dev/null || true)"
    [ "$installed" = "$EXPECTED_COMMIT" ] && break
  fi
done
[ "$installed" = "$EXPECTED_COMMIT" ] || { echo "Hermes is not at the reviewed commit." >&2; exit 1; }

hermes config get gateway.multiplex_profiles 2>/dev/null | grep -qi true
hermes config get gateway.platforms.a2a.enabled 2>/dev/null | grep -qi true
hermes config get kanban.orchestrator_profile 2>/dev/null | grep -q default
hermes config get approvals.mode 2>/dev/null | grep -q manual
hermes config get tool_loop_guardrails.hard_stop_enabled 2>/dev/null | grep -qi true

if [ "$CORE_ONLY" = false ]; then
  for profile in head-of-ops revenue-partner affiliate-revenue-partner finance-risk research-analysis; do
    [ -f "$HERMES_HOME/profiles/$profile/SOUL.md" ]
    [ -d "$HERMES_HOME/profiles/$profile/skills/shared/a2a-collaboration" ]
    hermes -p "$profile" config get platform_toolsets.cli 2>/dev/null | grep -q a2a
    hermes -p "$profile" config get platform_toolsets.a2a 2>/dev/null | grep -q kanban
    if hermes -p "$profile" config get platform_toolsets.a2a 2>/dev/null | grep -q 'a2a'; then
      echo "Inbound A2A for $profile can chain to another peer." >&2
      exit 1
    fi
  done
  hermes config get gateway.multiplex_profile_allowlist 2>/dev/null | grep -q research-analysis
  hermes config get gateway.platforms.a2a.extra.agents 2>/dev/null | grep -q affiliate-revenue-partner
  hermes kanban stats >/dev/null
fi

if [ "$ALLOW_UNCONNECTED" = false ]; then
  hermes doctor
  hermes gateway status
  hermes mcp list | grep -q agent-factory
  curl -fsS http://127.0.0.1:9900/.well-known/agent-card.json >/dev/null
  if [ "$CORE_ONLY" = false ]; then
    for route in head-of-ops revenue-partner affiliate-revenue-partner finance-risk research-analysis; do
      curl -fsS "http://127.0.0.1:9900/$route/.well-known/agent-card.json" >/dev/null
    done
  fi
fi

echo "AI Co-Founder Orgo verification passed."
