# Operation Blue Magpie — CTF Play Box

IE3132 Penetration Testing · SLIIT · Assignment 01 (Implementation)

An **isolated, self-contained** Capture-The-Flag lab built on Docker Compose.
It reproduces a fictional intrusion against **CeylonPay** (a made-up Sri Lankan
digital payment processor) across six chained stages, for an *authorised
assessment team* practising on a staging replica.

> ⚠️ **Safety boundary (non-negotiable).** Every vulnerability, credential and
> target in this repository exists **only inside this isolated Docker
> environment**. Nothing here is ever pointed at a real host, a real network, or
> any system outside this project's containers. See [`SAFETY.md`](SAFETY.md).

---

## Scenario

CeylonPay has been breached. Participants play an authorised assessment team
reproducing the intrusion, stage by stage, on an isolated staging replica. Each
stage's output is the next stage's input (a single chained kill-chain).

| Stage | Title | Domain | Difficulty | Hands off to next |
|---|---|---|---|---|
| S1 | The Phishing Lure | Digital Forensics | Easy | staging URL + `network_diagram.png` |
| S2 | The Leaked Blueprint | Forensics (metadata/stego) | Easy | username + internal host |
| S3 | Traffic Reconstruction | Networking | Moderate | login endpoint + credential |
| S4 | The Foothold | Web Security (SQL injection) | Moderate | `users` table dump (MD5) |
| S5 | Cracking the Vault | Web + Applied Crypto | Moderate–Hard | SSH credential |
| S6 | Total Compromise | Linux/System Security | Hard (capstone) | root flag via SUID priv-esc |

**Flag format:** `CPAY{S<n>_<slug>_<6-hex-token>}` — case-sensitive, one per
stage, stored **hashed** in CTFd.

## Architecture (locked)

- **Platform:** [CTFd](https://github.com/CTFd/CTFd) on Docker Compose, target
  host **Ubuntu 24.04 LTS, x86_64**.
- **Three Docker networks:**
  - `frontend_net` — Nginx ↔ CTFd (only entry point published to the host).
  - `backend_net` — **internal only**: CTFd ↔ PostgreSQL ↔ Redis. No external route.
  - `challenge_net` — S4 web app + S6 Linux box, **mutually isolated** (inter-container
    comms disabled), egress to the internet blocked by firewall rules.
- **S4** uses a **separate MySQL** database (never the platform PostgreSQL).
- **S1 / S2 / S3 / S5** are **static file attachments** in CTFd — no dedicated containers.

```
                 host :443
                    │
              ┌─────▼─────┐   frontend_net
              │   Nginx   │◄──────────────► CTFd
              └───────────┘                  │  backend_net (internal)
                                             ├──► PostgreSQL
                                             └──► Redis

  challenge_net (ICC off, no internet egress)
     ├──► S4 web app ──(private db-net)──► MySQL (users table, MD5 hashes)
     └──► S6 Linux/SSH box (SUID misconfig → /root/flag.txt)
```

## Repository layout

```
operation-blue-magpie/
├── docker-compose.yml       # platform stack + challenge stubs (skeleton)
├── .env.example             # copy to .env and fill in; .env is git-ignored
├── SAFETY.md                # scope & safety boundary
├── platform/
│   ├── nginx/               # reverse proxy + TLS config
│   └── ctfd/                # CTFd config / challenge import (flags, hashing)
├── challenges/
│   ├── s1/ … s3/ , s5/      # static-artefact generators (eml, png+stego, pcap, hashes)
│   ├── s4/                  # vulnerable web app + MySQL seed (SQL injection)
│   └── s6/                  # vulnerable Linux/SSH box (SUID misconfiguration)
├── scripts/                 # setup / reset / isolation-check / test-matrix helpers
└── docs/                    # build notes, test results, viva-prep pack
```

## Quick start (target: Ubuntu 24.04 x86_64 with Docker Engine + Compose v2)

> Status: **scaffold**. The stack is being filled in step by step — see
> [Build status](#build-status). Do not assume a step works until it is marked ✅.

```bash
cp .env.example .env          # then edit .env and set real secrets + pinned image tags
docker compose up -d          # bring up the platform stack
docker compose ps             # verify services are healthy
```

Reset to a clean state:

```bash
docker compose down -v && docker compose up -d
```

## Build status

Language throughout the report and this repo stays **proposed / planned** until a
piece is genuinely built **and run**. This table is the single source of truth
for what is real.

| Step | Item | Status |
|---|---|---|
| 1 | Repo scaffold | ✅ scaffold complete — `docker compose config` validates |
| 2 | Base Docker networks | ✅ defined — `docker compose config` validates |
| 3 | CTFd + PostgreSQL + Redis | 🟡 defined (arch-portable); **host run pending** (Postgres first-run to verify) |
| 4 | Nginx reverse proxy + TLS | 🟡 config + cert generator written (`gen_certs.sh` tested); **live TLS serve pending on host** |
| 5 | S1–S3 + S5 static artefacts | ✅ generated + solve-verified (S1 base64, S2 OpenStego round-trip, S3 HTTP stream, S5 crack) |
| 6 | S4 web app + MySQL (SQLi) | ✅ built + injection verified (manual UNION dump + sqlmap) — see build-notes for the mysql:8.0 re-check |
| 7 | S6 Linux/SSH box (SUID) | 🟡 built; SUID escalation verified on Ubuntu 24.04 — `docker compose build s6_linux` pending on Docker host |
| 8 | Isolation controls + verification | ⬜ not started |
| 9 | Reset/recovery | ⬜ not started |
| 10 | Full test matrix | ⬜ not started |

Legend: ⬜ not started · 🟡 in progress · ✅ built **and** verified on the target host.

## Team

| Member | Student ID | Role |
|---|---|---|
| Gayantha S A T | IT24101567 | CTF Platform & Architecture |
| Kulaweera K S I | IT24103220 | Challenge Design A (S1–S3) |
| Arachchi K A M B | IT24100634 | Challenge Design B (S4–S6) |
| Dasanayake H T N | IT24100967 | Integration, Testing & Documentation |

Module: IE3132 Penetration Testing · Lecturer: Mr. Kanishka Yapa.
