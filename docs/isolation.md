# Isolation model (Step 8)

Five controls keep the lab self-contained. All are **verified by
`scripts/isolation_check.sh`** — that script is the source of truth; if a control
regresses, the check fails.

| # | Control | How it's enforced | Verified by |
|---|---|---|---|
| 1 | Challenge boxes cannot reach the internet | `setup_firewall.sh` DOCKER-USER rules drop new egress from `challenge_net` | check 1 |
| 2 | Challenge boxes cannot reach the platform DB | `backend_net` is `internal: true`; firewall also drops challenge→backend | check 2 |
| 3 | S4 and S6 cannot reach each other | `challenge_net` has inter-container comms disabled (`enable_icc=false`) | check 3 |
| 4 | Platform DB/cache have no external route | `backend_net` `internal: true` | check 4 |
| 5 | S4's MySQL is reachable only by the S4 app | `s4_db` sits on `s4_db_net` (`internal: true`), not on `challenge_net` | check 5 |
| 6 | Container-root ≠ host-root (S6) | daemon `userns-remap` (see below) | manual (see below) |
| — | Per-container CPU/memory caps | `deploy.resources.limits` in compose | `docker stats` |
| — | S4 app dropped privileges | `cap_drop: ALL` + `no-new-privileges` on `s4_web` | `docker inspect` |

## Applying the controls (Ubuntu x86_64 VM)

1. **user-namespace remapping** (daemon-level, affects the whole daemon):
   ```bash
   sudo cp platform/docker/daemon.json.example /etc/docker/daemon.json   # merge if you already have one
   sudo systemctl restart docker
   docker info | grep -i userns          # should show "userns"
   ```
2. Bring the stack up, then apply the egress firewall (re-apply after every
   `up`, because Docker rewrites iptables on start — `reset.sh` does this):
   ```bash
   docker compose up -d
   sudo scripts/setup_firewall.sh
   ```
3. Verify:
   ```bash
   scripts/isolation_check.sh
   ```

## Docker Desktop (Mac) caveat

On Docker Desktop the daemon runs inside a LinuxKit VM behind vpnkit, so the
host `iptables` rules in `setup_firewall.sh` do not apply the way they do on a
Linux host, and `userns-remap`'s "container-root ≠ host-root" argument is weaker
(the real host is the VM, not macOS). Checks 3–5 (ICC, internal networks) still
hold on the Mac because they are enforced by Docker networking itself, but the
**egress-firewall + userns checks (1, 2, 6) are graded on the Ubuntu VM**. This
is recorded in `docs/build-notes.md`.
