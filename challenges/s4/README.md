# S4 — The Foothold  (Web Security: SQL injection · Moderate)

**Container:** `s4_web` (web app) + `s4_db` (dedicated MySQL).
**Owner:** Challenge Design B (S4–S6).

## What it is
A deliberately vulnerable CeylonPay staging web app with a **genuine,
exploitable SQL injection** against its own MySQL database. Using the S3
credential and the `/api/v1/login` endpoint as the entry point, the participant
exploits the injection to dump the `users` table.

- **Final committed vulnerability class:** SQL injection (not "SQLi or auth
  flaw" — SQLi is the fixed choice).
- **Database:** a **separate MySQL** instance (`s4_db`), never the platform
  PostgreSQL.
- **Seed:** `users` table with **unsalted MD5** password hashes.

## Hand-off to S5 (locked)
- Dump of the `users` table (unsalted MD5 hashes) — the input S5 cracks.

## Flag
- Format `CPAY{S4_<slug>_<6-hex-token>}`.

## Tools (intended)
Burp Suite · sqlmap

## Isolation (locked)
- `cap_drop: ALL` + `no-new-privileges:true` on `s4_web`.
- `s4_db` on an internal `s4_db_net`, reachable only by `s4_web`.
- Per-container CPU/memory limits.
- On `challenge_net` with ICC off → cannot reach `s6_linux`.

## Layout (to be built in Step 6)
```
s4/
├── app/            # Flask or PHP source + Dockerfile (implementer's choice)
└── seed/           # *.sql loaded via /docker-entrypoint-initdb.d (users table)
```
