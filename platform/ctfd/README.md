# platform/ctfd

CTFd configuration and challenge import.

Planned contents:
- `challenges.yml` / import bundle (Step 5+) — the six stages defined with their
  descriptions, categories, difficulty, attached files, and **flags configured as
  hashed static flags** (`CPAY{...}`, case-sensitive).
- First-run setup notes (admin account, event name "Operation Blue Magpie",
  visibility, and Postgres validation — see `docs/build-notes.md`).

Flags themselves are produced by `scripts/gen_flags.py`; only their **hashed**
form lives in CTFd. Keep plaintext flags out of committed files where practical.
