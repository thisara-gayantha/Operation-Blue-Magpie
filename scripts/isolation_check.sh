#!/usr/bin/env bash
# Verify the isolation model (Step 8). Each check expects a connection to be
# BLOCKED; it prints PASS when the traffic is correctly denied, FAIL otherwise.
# Uses throwaway alpine containers so it tests the networks, not app internals.
#
# Run after `docker compose up -d` (and setup_firewall.sh on the Linux VM).
set -uo pipefail

CHAL_NET="obm_challenge_net"
BACK_NET="obm_backend_net"
pass=0; fail=0

ip_of() { docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}" "$1" 2>/dev/null | awk '{print $1}'; }

# run_blocked "<description>" <docker run args...> -- <cmd inside>
# PASS if the command FAILS (connection blocked / times out).
check_blocked() {
  local desc="$1"; shift
  if docker run --rm "$@" >/dev/null 2>&1; then
    echo "  FAIL  $desc  (connection SUCCEEDED — not isolated)"; fail=$((fail+1))
  else
    echo "  PASS  $desc  (blocked)"; pass=$((pass+1))
  fi
}

echo "== Isolation checks =="

# 1. challenge_net -> internet must be blocked
check_blocked "challenge_net -> internet (1.1.1.1:443)" \
  --network "$CHAL_NET" alpine sh -c 'wget -T5 -q -O- https://1.1.1.1 >/dev/null'

# 2. challenge_net -> platform DB (PostgreSQL) must be blocked
DBIP="$(ip_of obm_ctfd_db)"
check_blocked "challenge_net -> platform PostgreSQL (${DBIP:-?}:5432)" \
  --network "$CHAL_NET" alpine sh -c "nc -z -w5 ${DBIP:-10.255.255.1} 5432"

# 3. S4 <-> S6 must be blocked (ICC off on challenge_net)
S6IP="$(ip_of obm_s6_linux)"
check_blocked "challenge_net peer -> S6 sshd (${S6IP:-?}:22)  [ICC off]" \
  --network "$CHAL_NET" alpine sh -c "nc -z -w5 ${S6IP:-10.255.255.2} 22"

# 4. backend_net must have no external route (internal: true)
check_blocked "backend_net -> internet (1.1.1.1:443)" \
  --network "$BACK_NET" alpine sh -c 'wget -T5 -q -O- https://1.1.1.1 >/dev/null'

# 5. S4's MySQL must not be reachable from challenge_net (it is on s4_db_net)
S4DBIP="$(ip_of obm_s4_db)"
check_blocked "challenge_net -> S4 MySQL (${S4DBIP:-?}:3306)" \
  --network "$CHAL_NET" alpine sh -c "nc -z -w5 ${S4DBIP:-10.255.255.3} 3306"

echo "-------------------------------------------"
echo "isolation: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
