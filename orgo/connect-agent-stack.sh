#!/usr/bin/env bash
# Phone, inbox and TEST cards are separate selections for every installed role.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-}" in
  --honcho) shift; exec "$ROOT/orgo-onboard" connect honcho "$@" ;;
  --latitude) shift; exec "$ROOT/orgo-onboard" connect latitude "$@" ;;
  --status) shift; exec "$ROOT/orgo-onboard" status "$@" ;;
  *) exec "$ROOT/orgo-onboard" resume ;;
esac
