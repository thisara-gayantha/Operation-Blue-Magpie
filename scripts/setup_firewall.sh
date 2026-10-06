#!/usr/bin/env bash
# Egress firewall for the challenge segment (Step 8).  LINUX HOST (the Ubuntu
# x86_64 build/verify VM). Blocks the challenge containers from reaching the
# internet and the platform database, using the DOCKER-USER chain so the rules
# survive Docker's own iptables management.
#
# NOTE: on Docker Desktop for Mac these host iptables rules do NOT apply the same
# way (the daemon runs in a VM behind vpnkit). Run + verify this on the Ubuntu
# VM, which is where the graded isolation checks happen. See docs/isolation.md.
#
# backend_net and s4_db_net are already `internal: true` (Docker gives them no
# external route), so this script's job is the challenge_net bridge.
#
# Re-run this after every `docker compose up` — Docker rewrites iptables on
# start, so the rules must be re-applied (reset.sh does this automatically).
set -euo pipefail

need_root() { [[ $EUID -eq 0 ]] || { echo "run as root (sudo)"; exit 1; }; }
need_root

CHAL_NET="obm_challenge_net"
BACK_NET="obm_backend_net"

subnet() { docker network inspect "$1" -f '{{(index .IPAM.Config 0).Subnet}}'; }
CHAL="$(subnet "$CHAL_NET")"
BACK="$(subnet "$BACK_NET")"
echo "challenge_net subnet: $CHAL"
echo "backend_net  subnet: $BACK"

# Idempotent: drop our previous rules first (ignore errors if absent).
while iptables -D DOCKER-USER -s "$CHAL" -j OBM_CHAL 2>/dev/null; do :; done
iptables -F OBM_CHAL 2>/dev/null || true
iptables -X OBM_CHAL 2>/dev/null || true

iptables -N OBM_CHAL
# Allow return traffic for connections initiated INTO the challenge boxes
# (participants reach S4/S6 via published host ports — that return path is fine).
iptables -A OBM_CHAL -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
# Explicitly deny any path to the platform database network.
iptables -A OBM_CHAL -d "$BACK" -j DROP
# Allow challenge boxes to talk to the Docker DNS resolver on the host only.
iptables -A OBM_CHAL -d 127.0.0.11/32 -j RETURN
# Block NEW egress to the internet (anything outside RFC1918).
iptables -A OBM_CHAL -d 10.0.0.0/8      -j DROP
iptables -A OBM_CHAL -d 172.16.0.0/12   -j DROP
iptables -A OBM_CHAL -d 192.168.0.0/16  -j DROP
iptables -A OBM_CHAL -j DROP            # default: drop new outbound to the internet

# Hook the challenge subnet into our chain from DOCKER-USER.
iptables -I DOCKER-USER -s "$CHAL" -j OBM_CHAL

echo "Applied. Verify with scripts/isolation_check.sh"
