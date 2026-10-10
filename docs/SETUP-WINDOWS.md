# Setup — Windows + Docker Desktop (turnkey)

This ZIP ships with everything pre-generated (flags, challenge artefacts, the
S2 stego PNG, the TLS cert, the S4 DB seed, the S6 build files, and a ready
`.env`). On Windows you only need **Docker Desktop** — no Python, OpenSSL or Java.

## 0. Prerequisites
- Install **Docker Desktop for Windows** (WSL2 backend) and make sure it's
  running (whale icon in the tray).
- Unzip this folder somewhere **without spaces**, e.g. `C:\obm\operation-blue-magpie`.

## 1. Bring the stack up
Open **PowerShell** in the folder and run:
```powershell
docker compose up -d --build
docker compose ps        # wait until services are healthy
```

## 2. First-run CTFd setup
1. Open **https://localhost** → click through the self-signed certificate warning.
2. Complete the CTFd **setup wizard**: create the **admin** account, name the
   event `Operation Blue Magpie`.
3. The seeder sets **Challenge Visibility** to **Private** and **Registration
   Visibility** to **Public**. Participants can create accounts, but must sign
   in before viewing challenges or downloading their attachments.

## 3. Load the six challenges (with files attached)
This is what fixes "artefacts / network diagram missing" — it uploads each
challenge's file automatically.

1. Sign in as the admin, open the **user menu → Settings → Access Tokens**,
   then select **Generate** and copy the token. This is in the signed-in
   account's settings, not the separate Admin configuration panel.
2. In PowerShell (replace `PASTE_TOKEN`; no host Python needed — it runs in a
   throwaway container):
```powershell
docker run --rm --network obm_frontend_net -v "${PWD}:/work" -w /work `
  -e CTFD_URL=http://ctfd:8000 -e CTFD_TOKEN=PASTE_TOKEN -e CTFD_TARGET_HOST=localhost `
  python:3.12-slim sh -c "pip install -q requests && python scripts/seed_ctfd.py"
```
You should see all six challenges created or updated, flags set, files attached,
and the S1-to-S6 prerequisite chain applied. Players can see the names of all
stages, but later stages are locked until the previous stage is solved. Clicking
a locked stage explains which stage must be completed first; its details and
files remain inaccessible. If duplicate stage records exist, the seeder keeps
the record with submission history, transfers its configured hints from the
duplicate, and deletes the duplicate so no `???` placeholder cards remain. The
seeder checks every required attachment before changing CTFd and can be safely
re-run.

To only remove duplicate stage cards on an already-seeded instance, use the
same command with `--cleanup-duplicates` instead. It preserves submission
history and repairs the stage prerequisite settings without reseeding files,
awards, or the theme.

To attach the per-stage hints after the challenges exist, run the existing
`scripts/add_hints.py` script with an admin API token. It is safe to rerun: it
adds missing hints and removes duplicates without changing the configured hints.
```powershell
docker run --rm --network obm_frontend_net -v "${PWD}:/work" -w /work `
  -e CTFD_URL=http://ctfd:8000 -e CTFD_TOKEN=PASTE_TOKEN `
  python:3.12-slim sh -c "python scripts/add_hints.py"
```

Each player starts with 30 points to spend on hints. Rebuild CTFd with
`docker compose up -d --build ctfd` after changing the plugin or Dockerfile.
The seeder gives existing non-admin players the same one-time 30-point award;
the plugin automatically grants it to newly registered players.

> If teammates play from **other PCs**, use your machine's LAN IP instead of
> `localhost` for `CTFD_TARGET_HOST` (that value only fills the S4/S6 connection
> hints in the challenge text), and open ports 443 / 8004 / 2226 in Windows
> Firewall.

## 4. Theme
The seeder in step 3 **already applied the theme** (it pushes
`platform/ctfd/theme-custom.css` into CTFd's Custom CSS). Just hard-refresh
(`Ctrl+Shift+R`). If you ever want to tweak it, edit that file and re-run the
step-3 command, or paste it manually in **Admin → Config → Theme → Custom CSS**.

## 5. Play
| What | Where |
|---|---|
| CTF platform | `https://localhost` |
| S4 vulnerable app | `http://localhost:8004` |
| S6 SSH box | `ssh svc-deploy@localhost -p 2226` |

The flags are listed in `flags.local` (for your reference / grading).

## Reset to a clean state
```powershell
docker compose down -v
docker compose up -d --build
```
Then repeat step 3 (re-seed) — a fresh CTFd DB starts empty.

## Notes
- The `.sh` helper scripts (`setup_firewall.sh`, `isolation_check.sh`,
  `run_tests.sh`) need **WSL** or **Git Bash**. On Docker Desktop the host
  iptables egress firewall does not apply the same way as on a bare Linux host,
  but the network isolation enforced by Docker itself (internal `backend_net` /
  `s4_db_net`, and inter-container comms disabled on `challenge_net`) still holds.
  See `docs/isolation.md`.
- To regenerate flags/artefacts yourself (optional; needs Python + Java/OpenStego
  in WSL): `python scripts/gen_flags.py && python scripts/gen_artifacts.py &&
  bash scripts/embed_s2.sh`, then re-seed.
