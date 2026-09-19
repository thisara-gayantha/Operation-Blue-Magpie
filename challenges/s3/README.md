# S3 — Traffic Reconstruction  (Networking · Moderate)

**Container:** none — static file attachment in CTFd.
**Owner:** Challenge Design A (S1–S3).

## Artefact
- `capture.pcap` — a packet capture. Reconstructing the HTTP conversation
  reveals the login endpoint and a credential, plus the flag.

## Hand-off to S4 (locked)
- Endpoint: `/api/v1/login`
- Credential: `k.fernando : Ceyl0nPay#2024`
  (that is a **zero** in `Ceyl0nPay`, not a letter O)

## Flag
- Format `CPAY{S3_<slug>_<6-hex-token>}`.

## Tools (intended)
Wireshark · `tshark`

Generator (crafts the pcap) + final `capture.pcap` land in Step 5.
