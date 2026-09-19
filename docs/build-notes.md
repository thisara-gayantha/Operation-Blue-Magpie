# Build notes & open technical flags

Running log of implementation decisions and anything that needs verification or
might be infeasible (per Section 7: flag, don't silently work around).

## Open items to verify

1. **CTFd on PostgreSQL.** CTFd's official Compose ships with MariaDB. Postgres
   is supported via `DATABASE_URL`, but first-run setup + migrations must be
   verified on the target host during Step 3. If a genuine blocker appears,
   raise it with the team before deviating from the locked design (which
   mandates PostgreSQL for the platform).
   - Status: **unverified** (platform not yet run here).

2. **Image tags.** All image tags are parameterised in `.env` and must be pinned
   to verified registry tags (ideally `@sha256` digests) before first build.
   `CTFD_IMAGE` ships as `VERIFY_ME` on purpose. — **pending**

3. **User-namespace remapping (S6).** `userns-remap` is a Docker **daemon**
   setting (`/etc/docker/daemon.json`), not a per-service compose flag. It
   affects the whole daemon, so document the daemon config and confirm the rest
   of the stack still runs under remap during Step 7/8. — **pending**

4. **challenge_net egress blocking.** `internal: true` would break published
   participant ports, so `challenge_net` is a normal bridge with ICC off and
   egress blocked by explicit firewall rules (Step 8). Verify the rules survive
   `docker compose down/up` (Docker rewrites iptables chains) — the isolation
   check must be re-run after any restart. — **pending**

## Decisions log
- (add dated entries as implementation proceeds)

## Test results
- See `docs/test-results.md` (created in Step 10; empty until real runs exist).
