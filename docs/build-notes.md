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
- 2026-09-21 — **S4 built + verified.** Flask app with an intentional UNION-based
  SQL injection in `POST /api/v1/login` (username param, 3 columns). Verified by
  standing up a real MySQL-compatible DB, loading the generated seed, and
  exploiting it: auth bypass, full `users` dump (matches the S5 hand-off exactly),
  and flag read from `secrets`. sqlmap also confirmed the injection and dumped the
  flag. Note: local verification used MariaDB 10.11 (MySQL-compatible fork); the
  container image is `mysql:8.0` per the locked design — the query/technique is
  identical on both, but re-run the sqlmap check once on the real `mysql:8.0`
  container. App runs unprivileged on port 8080 with `cap_drop=ALL` +
  `no-new-privileges`; `s4_db` is on an internal `s4_db_net` reachable only by the app.
- App/base image versions (`Flask 3.0.3`, `PyMySQL 1.1.1`, `gunicorn 22.0.0`,
  `python:3.12-slim`) resolve via pip here, but re-confirm on the build host.
- 2026-09-22 — **S6 built + escalation verified.** `ubuntu:24.04` box with sshd,
  the `svc-deploy` account (S5 hand-off), and a deliberate SUID-root `find`. The
  escalation technique was verified on an Ubuntu 24.04 host: an unprivileged user
  is denied direct read of the root-only `/root/flag.txt`, but SUID `find` →
  `/bin/sh -p` yields euid 0 and reads the flag. The **container image build**
  (`docker compose build s6_linux`) still has to be run on the Docker host — no
  Docker in the authoring sandbox. `no-new-privileges` is deliberately NOT set on
  s6 (it would break the SUID escalation).
- **Host plan (agreed):** develop on the Mac (Docker Desktop, arm64); run the
  final graded isolation checks + full end-to-end matrix on an Ubuntu 24.04
  x86_64 VM (UTM), where `userns-remap` and host firewall egress rules behave as
  the report locks them.

## Test results
- See `docs/test-results.md` (created in Step 10; empty until real runs exist).
