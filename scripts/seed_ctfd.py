#!/usr/bin/env python3
"""
seed_ctfd.py — populate CTFd with all six Operation Blue Magpie challenges,
INCLUDING their file attachments (this is what fixes "artefacts/network diagram
missing" — the files are uploaded to each challenge automatically).

It also sets the (case-sensitive) flags and keeps all challenge cards visible;
the stage hand-offs are described in the challenge text rather than gated.

Run it AFTER `docker compose up -d` and after you finish the CTFd setup wizard
(create the admin), then create an admin API token in:
    CTFd -> Admin -> Settings -> Access Tokens -> Generate

Usage (from the host, needs `pip install requests`):
    CTFD_URL=https://localhost CTFD_TOKEN=<token> python scripts/seed_ctfd.py

Or with no host Python, from inside the Docker network (see docs/SETUP-WINDOWS.md):
    docker run --rm --network obm_frontend_net -v "%cd%":/work -w /work \
      -e CTFD_URL=http://ctfd:8000 -e CTFD_TOKEN=<token> \
      python:3.12-slim sh -c "pip install -q requests && python scripts/seed_ctfd.py"
"""
from __future__ import annotations
import json
import hashlib
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("This script needs 'requests'.  pip install requests")

import urllib3
urllib3.disable_warnings()  # self-signed cert on https://localhost

REPO = Path(__file__).resolve().parents[1]
URL = os.environ.get("CTFD_URL", "https://localhost").rstrip("/")
TOKEN = os.environ.get("CTFD_TOKEN", "")
TARGET = os.environ.get("CTFD_TARGET_HOST", "the CTF host (ask your instructor)")
VERIFY = os.environ.get("CTFD_VERIFY", "false").lower() == "true"

if not TOKEN:
    sys.exit("Set CTFD_TOKEN to an admin Access Token (CTFd -> Admin -> Settings -> Access Tokens).")

H = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
S = requests.Session()

# --- challenge definitions (files are attached automatically) ----------------
CH = [
    dict(key="S1", name="S1 · The Phishing Lure", category="Forensics", value=100,
         files=["challenges/s1/lure.eml"],
         desc=("CeylonPay's SOC forwarded a suspicious email. Analyse the attached "
               "`lure.eml` (headers, strings, base64) to find where the attacker "
               "pointed the victim next.\n\nFlag format: `CPAY{...}`")),
    dict(key="S2", name="S2 · The Leaked Blueprint", category="Forensics", value=100,
         files=["challenges/s2/network_diagram.png"],
         desc=("The lure linked to this network diagram. Something is hidden inside "
               "it — check the metadata (`exiftool`) and look below the surface "
               "(OpenStego, **not** steghide — this is a PNG).\n\nFlag format: `CPAY{...}`")),
    dict(key="S3", name="S3 · Traffic Reconstruction", category="Network", value=200,
         files=["challenges/s3/capture.pcap"],
         desc=("We captured traffic to the internal API. Open `capture.pcap` in "
               "Wireshark and follow the HTTP stream to recover the login endpoint "
               "and credential.\n\nFlag format: `CPAY{...}`")),
    dict(key="S4", name="S4 · The Foothold", category="Web", value=300, files=[],
         desc=(f"Using the credential from S3, attack the CeylonPay staging app at "
               f"**http://{TARGET}:8004/**. The login is vulnerable to SQL injection — "
               f"dump the `users` table and find the flag.\n\nTools: Burp Suite, "
               f"sqlmap.\n\nFlag format: `CPAY{{...}}`")),
    dict(key="S5", name="S5 · Cracking the Vault", category="Crypto", value=400,
         files=["challenges/s5/users_dump.txt", "challenges/s5/s5_wordlist.txt"],
         desc=("The dump holds unsalted MD5 hashes. Crack `svc-deploy` (use the "
               "provided wordlist) to recover the SSH password, and crack the "
               "`vault-service` hash (6-hex mask) for this stage's flag.\n\n"
               "Tools: hashcat / John.\n\nFlag format: `CPAY{...}`")),
    dict(key="S6", name="S6 · Total Compromise", category="System", value=500, files=[],
         desc=(f"SSH into the box with the S5 credential: "
               f"`ssh svc-deploy@{TARGET} -p 2226`. Escalate to root via a SUID "
               f"misconfiguration (check `find / -perm -4000`, then GTFOBins) and "
               f"read `/root/flag.txt`.\n\nFlag format: `CPAY{{...}}`")),
]


def flags() -> dict:
    p = REPO / "challenges" / ".flags.json"
    if not p.exists():
        sys.exit("challenges/.flags.json missing — run scripts/gen_flags.py first.")
    return json.loads(p.read_text())["flags"]


def create_challenge(c) -> int:
    payload = {
        "name": c["name"], "category": c["category"], "description": c["desc"],
        "value": c["value"], "state": "visible", "type": "standard",
        "requirements": {},
    }
    r = S.get(f"{URL}/api/v1/challenges", headers=H, verify=VERIFY)
    r.raise_for_status()
    existing = next((item for item in r.json().get("data", [])
                     if item.get("name") == c["name"]), None)
    if existing:
        r = S.patch(f"{URL}/api/v1/challenges/{existing['id']}", headers=H,
                    verify=VERIFY, json=payload)
        r.raise_for_status()
        return existing["id"]
    r = S.post(f"{URL}/api/v1/challenges", headers=H, verify=VERIFY, json=payload)
    r.raise_for_status()
    return r.json()["data"]["id"]


def add_flag(cid: int, content: str) -> None:
    r = S.get(f"{URL}/api/v1/flags", headers=H, verify=VERIFY)
    r.raise_for_status()
    existing = next((item for item in r.json().get("data", [])
                     if item.get("challenge_id", item.get("challenge")) == cid), None)
    if existing:
        if existing.get("content") != content or existing.get("type") != "static":
            r = S.patch(f"{URL}/api/v1/flags/{existing['id']}", headers=H,
                        verify=VERIFY,
                        json={"content": content, "type": "static", "data": ""})
            r.raise_for_status()
        return
    # case-sensitive static flag; field name differs across CTFd versions.
    for field in ("challenge_id", "challenge"):
        r = S.post(f"{URL}/api/v1/flags", headers=H, verify=VERIFY, json={
            field: cid, "content": content, "type": "static", "data": ""})
        if r.status_code < 300:
            return
    r.raise_for_status()


def upload_file(cid: int, path: Path) -> None:
    r = S.get(f"{URL}/api/v1/challenges/{cid}/files", headers=H, verify=VERIFY)
    r.raise_for_status()
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    if any(item.get("sha1sum") == digest for item in r.json().get("data", [])):
        return
    with path.open("rb") as fh:
        r = S.post(f"{URL}/api/v1/files",
                   headers={"Authorization": f"Token {TOKEN}"}, verify=VERIFY,
                   files={"file": (path.name, fh)},
                   data={"challenge_id": cid, "type": "challenge"})
    r.raise_for_status()


def require_artifacts() -> None:
    missing = [rel for challenge in CH for rel in challenge["files"]
               if not (REPO / rel).is_file()]
    if missing:
        files = "\n  ".join(missing)
        sys.exit("Required challenge artefacts are missing:\n  " + files +
                 "\nRun scripts/gen_artifacts.py and scripts/embed_s2.sh, then retry.")


def set_participant_visibility() -> None:
    r = S.patch(f"{URL}/api/v1/configs", headers=H, verify=VERIFY,
                    json={"challenge_visibility": "private",
                      "registration_visibility": "public"})
    r.raise_for_status()


def apply_theme() -> None:
    """Set CTFd's rendered theme header to the project-wide stylesheet."""
    css_path = REPO / "platform" / "ctfd" / "theme-custom.css"
    if not css_path.exists():
        print("  ! theme CSS not found — skipping theme")
        return
    css = css_path.read_text()
    header = f"<style>\n{css}\n</style>"
    r = S.patch(f"{URL}/api/v1/configs", headers=H, verify=VERIFY,
                json={"theme_header": header})
    if r.status_code < 300:
        print("  [theme] Global stylesheet applied (hard-refresh the browser to see it)")
    else:
        print(f"  ! theme apply failed ({r.status_code}); paste "
              "platform/ctfd/theme-custom.css into Admin -> Config -> Theme -> Custom CSS")


def set_home_page() -> None:
    """Replace the default CTFd index page with the branded Blue Magpie hero."""
    html_path = REPO / "platform" / "ctfd" / "index-page.html"
    if not html_path.exists():
        return
    try:
        pages = S.get(f"{URL}/api/v1/pages", headers=H, verify=VERIFY).json().get("data", [])
        idx = [p for p in pages if p.get("route") in ("index", "")]
        if not idx:
            print("  ! index page not found; paste platform/ctfd/index-page.html into Admin -> Pages")
            return
        r = S.patch(f"{URL}/api/v1/pages/{idx[0]['id']}", headers=H, verify=VERIFY,
                    json={"content": html_path.read_text(), "format": "html"})
        print("  [home] branded index page applied" if r.status_code < 300
              else f"  ! home page apply failed ({r.status_code}); paste it in Admin -> Pages")
    except Exception as e:  # best-effort
        print(f"  ! home page step skipped ({e}); paste platform/ctfd/index-page.html in Admin -> Pages")


def main() -> None:
    require_artifacts()
    fl = flags()
    print(f"Seeding {URL} ...")
    set_participant_visibility()
    print("  [visibility] challenges require sign-in; registration is public")
    ids = {}
    for c in CH:
        cid = create_challenge(c)
        ids[c["key"]] = cid
        add_flag(cid, fl[c["key"]])
        for rel in c["files"]:
            p = REPO / rel
            upload_file(cid, p)
        n = len([f for f in c["files"] if (REPO / f).exists()])
        print(f"  [{c['key']}] created (id={cid}), flag set, {n} file(s) attached")

    print("  all six stages are visible; solve hand-offs remain in each description")

    apply_theme()
    set_home_page()
    print("\nDone. Six challenges live (with files), theme applied, home page branded.")


if __name__ == "__main__":
    main()
