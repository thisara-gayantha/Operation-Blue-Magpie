# Challenge build & intended solves (S1–S3, S5)

**Private — keep this repo private; this file documents the solution path.**

## Build order

```bash
python3 scripts/gen_flags.py       # mint flags -> challenges/.flags.json (git-ignored)
python3 scripts/gen_artifacts.py   # build S1 eml, S3 pcap, S5 dump+wordlist, S2 cover+payload
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

**S5 — users_dump.txt.** Unsalted MD5s. `svc-deploy` cracks with the supplied
`s5_wordlist.txt` to `Bl@ckout#Deploy1` (the S6 SSH password). `vault-service`
cracks with a 6-hex mask (`hashcat -a 3 -m 0 ... ?h?h?h?h?h?h`, or John
`--mask`) to the S5 token; wrap it as `CPAY{S5_vault_<token>}`.
→ hands off: `svc-deploy : Bl@ckout#Deploy1`.

## Tooling notes
- S2 embedding needs OpenStego (Java). The build machine's OpenStego version
  produces the box's `network_diagram.png`; participants extract with the same
  tool.
- S5 `svc-deploy` is deterministically crackable because the themed wordlist
  includes the real password; decoy accounts (rockyou-style) add noise.
