#!/usr/bin/env bash
# Reset the whole box to a clean state (Step 9): tear down (including volumes),
# rebuild, bring up, and re-apply the egress firewall (Docker rewrites iptables
# on every `up`, so the rules must be re-applied afterwards).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO"

echo "== down (removing volumes for a clean slate) =="
docker compose down -v --remove-orphans

echo "== up (rebuilding challenge images) =="
docker compose up -d --build

echo "== waiting for services to report healthy =="
for _ in $(seq 1 30); do
  if ! docker compose ps --format '{{.Health}}' 2>/dev/null | grep -qiE 'starting|unhealthy'; then
    break
  fi
  sleep 3
done
docker compose ps

# Re-apply the egress firewall on Linux hosts (needs root). Skipped on Docker
# Desktop / Mac, where those host rules don't apply (see docs/isolation.md).
if [[ "$(uname -s)" == "Linux" ]] && command -v iptables >/dev/null 2>&1; then
  echo "== re-applying egress firewall =="
  sudo "$SCRIPT_DIR/setup_firewall.sh" || echo "  (firewall step needs sudo; run: sudo scripts/setup_firewall.sh)"
else
  echo "== skipping host firewall (not a Linux host) — see docs/isolation.md =="
fi

echo "Done. Clean state is up."
