# S6 — Total Compromise  (Linux/System Security · Hard · capstone)

**Container:** `s6_linux` (SSH-reachable Linux box).
**Owner:** Challenge Design B (S4–S6).

## What it is
Using the `svc-deploy` SSH credential recovered in S5, the participant logs in
as an unprivileged service account and escalates to root through a **deliberate
SUID misconfiguration**, reading the root flag.

- **Final committed vulnerability:** SUID misconfiguration (privilege
  escalation).
- **Root flag:** `/root/flag.txt`.

## Input from S5 (locked)
- SSH credential: `svc-deploy : Bl@ckout#Deploy1`

## Flag
- `/root/flag.txt` → format `CPAY{S6_<slug>_<6-hex-token>}`.

## Tools (intended)
manual enumeration / linpeas · GTFOBins

## Isolation (locked)
- **User-namespace remapping** at the Docker daemon level so container-root ≠
  host-root (configured in `/etc/docker/daemon.json` — see Step 7/8).
- Reachable only inside `challenge_net`; ICC off → cannot reach `s4_web`.
- Per-container CPU/memory limits.
- No internet egress (firewall, Step 8).

## Layout (to be built in Step 7)
```
s6/
├── Dockerfile          # base image + sshd + svc-deploy account + SUID target
└── build/              # helper files (e.g. flag placeholder, entrypoint)
```
