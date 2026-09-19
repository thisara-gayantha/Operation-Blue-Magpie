# S5 — Cracking the Vault  (Web + Applied Cryptography · Moderate–Hard)

**Container:** none — static file attachment in CTFd (the hash dump).
**Owner:** Challenge Design B (S4–S6).

## What it is
Using the `users` table dump from S4 (unsalted MD5 hashes), the participant
cracks the relevant hash(es) and recovers the SSH service credential for S6.

## Input from S4
- `users` table dump — unsalted MD5 hashes (provided as the S5 attachment,
  `*.hashes` / `*.dump`).

## Hand-off to S6 (locked)
- SSH credential: `svc-deploy : Bl@ckout#Deploy1`

## Flag
- Format `CPAY{S5_<slug>_<6-hex-token>}`.

## Tools (intended)
hashcat / John the Ripper · CyberChef

Dump/hash file generation lands in Step 5 (kept consistent with the S4 seed so
the cracked value equals the S6 SSH password).
