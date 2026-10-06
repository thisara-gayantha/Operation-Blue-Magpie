# scripts

Helper scripts. Built in the step noted; each is designed to be idempotent and
safe to re-run.

| Script | Purpose | Step |
|---|---|---|
| `gen_certs.sh` | Generate self-signed TLS cert/key into `platform/nginx/certs/` | 4 |
| `gen_flags.py` | Generate the six `CPAY{...}` flags + their hashes; write a `flags.local` (git-ignored) and the hashed values for CTFd import | 5 |
| `gen_artifacts.py` / `.sh` | Build S1–S3 + S5 static artefacts (eml, png+stego, pcap, hash dump) reproducibly | 5 |
| `isolation_check.sh` | Verify isolation: S4↔S6 blocked, challenge_net has no internet, backend_net has no external route | 8 |
| `reset.sh` | `docker compose down -v && docker compose up -d`; confirm clean state | 9 |
| `run_tests.sh` | Execute the test matrix (functional / flag / isolation / resource / end-to-end) and write results to `docs/test-results.md` | 10 |

> Scripts write **real** results only. A test is recorded as passing only after
> it has actually run on the target host.
