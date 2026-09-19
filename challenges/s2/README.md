# S2 — The Leaked Blueprint  (Forensics: metadata/stego · Easy)

**Container:** none — static file attachment in CTFd.
**Owner:** Challenge Design A (S1–S3).

## Artefact
- `network_diagram.png` — carries a hidden payload. Metadata (`exiftool`) and a
  steganographic layer reveal the flag and hand-off values.

## Hand-off to S3 (locked)
- Username: `k.fernando`
- Internal host: `api-internal.ceylonpay.lk`

## Flag
- Format `CPAY{S2_<slug>_<6-hex-token>}`.

## Tools (intended)
`exiftool` · **OpenStego** (NOT steghide — steghide does not support PNG)

Generator (embeds payload with OpenStego) + final PNG land in Step 5.
