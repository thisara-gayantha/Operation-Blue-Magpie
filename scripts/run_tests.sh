#!/usr/bin/env bash
# Test matrix (Step 10). Runs the real checks against the live stack and writes
# results to docs/test-results.md. Records ONLY what it actually observes.
#
# Prereq: `docker compose up -d` (and setup_firewall.sh on the Linux VM).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO" || exit 1
# shellcheck disable=SC1091
[[ -f .env ]] && set -a && . ./.env && set +a
HTTPS_PORT="${HTTPS_PORT:-443}"
S4_HTTP_PORT="${S4_HTTP_PORT:-8004}"
S6_SSH_PORT="${S6_SSH_PORT:-2226}"

pass=0; fail=0; results=""
record() { # <PASS|FAIL> <name> <detail>
  local st="$1" name="$2" detail="$3"
  [[ "$st" == PASS ]] && pass=$((pass+1)) || fail=$((fail+1))
  results+="| $name | $st | ${detail//|/\\|} |"$'\n'
  printf '  %-4s %s\n' "$st" "$name"
}
ok() { record PASS "$1" "$2"; }
no() { record FAIL "$1" "$2"; }

echo "== Functional =="
code="$(curl -k -s -o /dev/null -w '%{http_code}' "https://localhost:${HTTPS_PORT}/" || echo 000)"
[[ "$code" =~ ^(200|302)$ ]] && ok "CTFd reachable via Nginx/TLS" "HTTP $code" || no "CTFd reachable via Nginx/TLS" "HTTP $code"

h="$(curl -s "http://localhost:${S4_HTTP_PORT}/healthz" || true)"
echo "$h" | grep -q '"status":"ok"' && ok "S4 app healthy" "$h" || no "S4 app healthy" "${h:-no response}"

if nc -z -w5 localhost "${S6_SSH_PORT}" 2>/dev/null; then ok "S6 sshd port open" "localhost:${S6_SSH_PORT}"; else no "S6 sshd port open" "closed"; fi

echo "== Flag / injection (S4 UNION -> secrets) =="
inj='{"username":"zzz'"'"' UNION SELECT id, value, name FROM secrets-- -","password":"x"}'
r="$(curl -s -X POST "http://localhost:${S4_HTTP_PORT}/api/v1/login" -H 'Content-Type: application/json' -d "$inj" || true)"
echo "$r" | grep -q 'CPAY{S4_' && ok "S4 SQL injection yields flag" "flag returned" || no "S4 SQL injection yields flag" "${r:-no response}"

echo "== Resource limits =="
for c in obm_s4_web obm_s6_linux; do
  mem="$(docker inspect -f '{{.HostConfig.Memory}}' "$c" 2>/dev/null || echo 0)"
  [[ "${mem:-0}" -gt 0 ]] && ok "resource limit set: $c" "memory=${mem}" || no "resource limit set: $c" "memory=${mem:-0}"
done

echo "== Privilege drop (S4) =="
cap="$(docker inspect -f '{{.HostConfig.CapDrop}}' obm_s4_web 2>/dev/null || echo '')"
echo "$cap" | grep -qi ALL && ok "S4 cap_drop=ALL" "$cap" || no "S4 cap_drop=ALL" "${cap:-none}"

echo "== Isolation matrix =="
if "$SCRIPT_DIR/isolation_check.sh"; then ok "isolation_check.sh" "all checks blocked"; else no "isolation_check.sh" "see output above"; fi

# --- write report ---
out="docs/test-results.md"
{
  echo "# Test results"
  echo
  echo "Run: $(date -u '+%Y-%m-%d %H:%M:%SZ')  ·  host: $(uname -sm)"
  echo
  echo "| Test | Result | Detail |"
  echo "|---|---|---|"
  printf '%s' "$results"
  echo
  echo "**$pass passed, $fail failed.**"
  echo
  echo "> Manual (not automated here): S6 end-to-end — SSH as svc-deploy, SUID"
  echo "> \`find\` escalation, read /root/flag.txt. Record the outcome by hand."
} > "$out"

echo "-------------------------------------------"
echo "$pass passed, $fail failed  ->  $out"
[[ $fail -eq 0 ]]
