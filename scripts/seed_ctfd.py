#!/usr/bin/env python3
"""
seed_ctfd.py — populate CTFd with all six Operation Blue Magpie challenges,
INCLUDING their file attachments (this is what fixes "artefacts/network diagram
missing" — the files are uploaded to each challenge automatically).

It also sets the (case-sensitive) flags and enforces the S1-to-S6 prerequisite
chain, hiding each locked stage until its previous stage is solved.

Run it AFTER `docker compose up -d` and after you finish the CTFd setup wizard
(create the admin), then create an admin API token in:
    Sign in as admin -> user menu -> Settings -> Access Tokens -> Generate

Usage (from the host, needs `pip install requests`):
    CTFD_URL=https://localhost CTFD_TOKEN=<token> python scripts/seed_ctfd.py

Or with no host Python, from inside the Docker network (see docs/SETUP-WINDOWS.md):
    docker run --rm --network obm_frontend_net -v "%cd%":/work -w /work \
      -e CTFD_URL=http://ctfd:8000 -e CTFD_TOKEN=<token> \
      python:3.12-slim sh -c "pip install -q requests && python scripts/seed_ctfd.py"
"""
from __future__ import annotations
import argparse
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
STARTING_AWARD_NAME = "Starting Hint Balance"
STARTING_AWARD_DESCRIPTION = "One-time 30-point starting credit for challenge hints."
STARTING_POINTS = 30

if not TOKEN:
    sys.exit("Set CTFD_TOKEN to an admin Access Token (sign in as admin -> user menu -> Settings -> Access Tokens).")

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
    }
    r = S.get(
        f"{URL}/api/v1/challenges",
        headers=H,
        verify=VERIFY,
        params={"view": "admin"},
    )
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


def remove_duplicate_stage_challenges() -> None:
    r = S.get(
        f"{URL}/api/v1/challenges",
        headers=H,
        verify=VERIFY,
        params={"view": "admin"},
    )
    r.raise_for_status()
    by_name: dict[str, list[dict]] = {}
    stage_names = {challenge["name"] for challenge in CH}
    for challenge in r.json().get("data", []):
        if challenge.get("name") in stage_names:
            by_name.setdefault(challenge["name"], []).append(challenge)

    duplicate_groups = {
        name: sorted(challenges, key=lambda challenge: challenge["id"])
        for name, challenges in by_name.items()
        if len(challenges) > 1
    }
    if not duplicate_groups:
        print("  [cleanup] no duplicate stage challenges found")
        return

    submissions: dict[int, int] = {}
    page = 1
    while True:
        r = S.get(
            f"{URL}/api/v1/submissions",
            headers=H,
            verify=VERIFY,
            params={"view": "admin", "page": page},
        )
        r.raise_for_status()
        data = r.json()
        for submission in data.get("data", []):
            challenge_id = submission.get("challenge_id")
            if isinstance(challenge_id, int):
                submissions[challenge_id] = submissions.get(challenge_id, 0) + 1
        pagination = data.get("meta", {}).get("pagination", {})
        if page >= pagination.get("pages", 1):
            break
        page += 1

    winners: dict[str, dict] = {}
    for name, challenges in duplicate_groups.items():
        with_submissions = [
            challenge
            for challenge in challenges
            if submissions.get(challenge["id"], 0)
        ]
        if len(with_submissions) > 1:
            details = ", ".join(
                f"id={challenge['id']} ({submissions[challenge['id']]} submission(s))"
                for challenge in with_submissions
            )
            raise RuntimeError(
                f"Duplicate {name} challenges have submission history on multiple "
                f"records ({details}); refusing to delete either."
            )
        winners[name] = with_submissions[0] if with_submissions else challenges[0]

    for name, challenges in duplicate_groups.items():
        winner = winners[name]
        winner_id = winner["id"]
        r = S.get(
            f"{URL}/api/v1/challenges/{winner_id}/hints",
            headers=H,
            verify=VERIFY,
        )
        r.raise_for_status()
        known_hints = {
            (hint.get("content"), hint.get("cost"))
            for hint in r.json().get("data", [])
        }

        for duplicate in challenges:
            duplicate_id = duplicate["id"]
            if duplicate_id == winner_id:
                continue

            r = S.get(
                f"{URL}/api/v1/challenges/{duplicate_id}/hints",
                headers=H,
                verify=VERIFY,
            )
            r.raise_for_status()
            for hint in r.json().get("data", []):
                key = (hint.get("content"), hint.get("cost"))
                if key in known_hints:
                    continue
                r = S.post(
                    f"{URL}/api/v1/hints",
                    headers=H,
                    verify=VERIFY,
                    json={
                        "challenge_id": winner_id,
                        "content": hint["content"],
                        "cost": hint["cost"],
                    },
                )
                r.raise_for_status()
                known_hints.add(key)

            r = S.delete(
                f"{URL}/api/v1/challenges/{duplicate_id}",
                headers=H,
                verify=VERIFY,
            )
            r.raise_for_status()
            print(f"  [cleanup] removed duplicate {name} (id={duplicate_id})")

        if submissions.get(winner_id):
            print(
                f"  [cleanup] kept {name} (id={winner_id}) to preserve "
                f"{submissions[winner_id]} submission(s)"
            )
    print(f"  [cleanup] duplicate stage entries consolidated")


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


def grant_initial_points() -> None:
    current_user = S.get(f"{URL}/api/v1/users/me", headers=H, verify=VERIFY)
    current_user.raise_for_status()
    admin_id = current_user.json()["data"]["id"]

    users = []
    page = 1
    while True:
        r = S.get(f"{URL}/api/v1/users", headers=H, verify=VERIFY,
                  params={"view": "admin", "page": page})
        r.raise_for_status()
        data = r.json()
        users.extend(data.get("data", []))
        pagination = data.get("meta", {}).get("pagination", {})
        if page >= pagination.get("pages", 1):
            break
        page += 1

    r = S.get(f"{URL}/api/v1/awards", headers=H, verify=VERIFY)
    r.raise_for_status()
    awards = r.json().get("data", [])
    credited = 0
    for user in users:
        user_id = user["id"]
        if user_id == admin_id:
            continue

        matches = [
            award for award in awards
            if award.get("user_id") == user_id
            and award.get("name") == STARTING_AWARD_NAME
        ]
        if matches:
            keep = next(
                (award for award in matches if award.get("value") == STARTING_POINTS),
                None,
            )
            for duplicate in matches:
                if duplicate is keep:
                    continue
                r = S.delete(
                    f"{URL}/api/v1/awards/{duplicate['id']}",
                    headers=H,
                    verify=VERIFY,
                )
                r.raise_for_status()
            if keep:
                continue

        r = S.post(
            f"{URL}/api/v1/awards",
            headers=H,
            verify=VERIFY,
            json={
                "user_id": user_id,
                "name": STARTING_AWARD_NAME,
                "description": STARTING_AWARD_DESCRIPTION,
                "value": STARTING_POINTS,
            },
        )
        r.raise_for_status()
        awards.append(r.json()["data"])
        credited += 1

    print(f"  [points] {STARTING_POINTS} starting points granted to {credited} existing player(s)")


def set_stage_prerequisites() -> None:
    r = S.get(
        f"{URL}/api/v1/challenges",
        headers=H,
        verify=VERIFY,
        params={"view": "admin"},
    )
    r.raise_for_status()

    stage_keys = [challenge["key"] for challenge in CH]
    stage_ids: dict[str, int] = {}
    for challenge in r.json().get("data", []):
        name = challenge.get("name", "")
        key = name.split(maxsplit=1)[0] if name else ""
        if key not in stage_keys:
            continue
        if key in stage_ids:
            raise RuntimeError(
                f"Multiple challenges found for {key}; refusing to set prerequisites."
            )
        challenge_id = challenge.get("id")
        if not isinstance(challenge_id, int):
            raise RuntimeError(f"Challenge {key} has no valid numeric id.")
        stage_ids[key] = challenge_id

    missing = [key for key in stage_keys if key not in stage_ids]
    if missing:
        raise RuntimeError("Could not resolve challenge ids for: " + ", ".join(missing))

    first_id = stage_ids[stage_keys[0]]
    r = S.patch(
        f"{URL}/api/v1/challenges/{first_id}",
        headers=H,
        verify=VERIFY,
        json={"requirements": {"prerequisites": [], "anonymize": False}},
    )
    r.raise_for_status()
    print(f"  [{stage_keys[0]}] no prerequisites")
    for index in range(1, len(stage_keys)):
        previous, current = stage_keys[index - 1], stage_keys[index]
        r = S.patch(
            f"{URL}/api/v1/challenges/{stage_ids[current]}",
            headers=H,
            verify=VERIFY,
            json={"requirements": {
                "prerequisites": [stage_ids[previous]],
                "anonymize": "preview",
            }},
        )
        r.raise_for_status()
        print(
            f"  [{current}] requires {previous} (id={stage_ids[previous]}); "
            "name shown; details and files locked"
        )


STAGE_LOCK_UI_JS = """<script>
(function(){
  if(window.location.pathname.replace(/\\/$/,"")!=="/challenges") return;
  var lockedStages={};
  var notice;
  var noticeTimer;

  function showNotice(message){
    if(!notice){
      notice=document.createElement("div");
      notice.className="obm-stage-notice";
      notice.setAttribute("role","status");
      notice.setAttribute("aria-live","polite");
      document.body.appendChild(notice);
    }
    notice.textContent=message;
    notice.classList.add("is-visible");
    window.clearTimeout(noticeTimer);
    noticeTimer=window.setTimeout(function(){
      notice.classList.remove("is-visible");
    },3600);
  }

  function markLockedCards(){
    document.querySelectorAll("button.challenge-button").forEach(function(button){
      var stage=lockedStages[String(button.value)];
      if(!stage) return;
      button.classList.add("challenge-locked");
      button.setAttribute("aria-disabled","true");
      button.setAttribute("title",stage.message);
    });
  }

  document.addEventListener("click",function(event){
    var target=event.target instanceof Element
      ? event.target.closest("button.challenge-button") : null;
    if(!target) return;
    var stage=lockedStages[String(target.value)];
    if(!stage) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    showNotice(stage.message);
  },true);

  fetch("/api/v1/challenges").then(function(response){
    if(!response.ok) throw new Error("Challenge list returned HTTP "+response.status);
    return response.json();
  }).then(function(response){
    response.data.forEach(function(challenge){
      if(challenge.type!=="hidden") return;
      var match=/^S([2-6])\\b/.exec(challenge.name||"");
      var message=match
        ? "Complete S"+(Number(match[1])-1)+" before accessing S"+match[1]+"."
        : "Complete the previous challenge to unlock this stage.";
      lockedStages[String(challenge.id)]={message:message};
    });
    markLockedCards();
    new MutationObserver(markLockedCards).observe(document.body,{
      childList:true,
      subtree:true
    });
  }).catch(function(error){
    console.error("Could not load stage-lock information.",error);
  });
})();
</script>"""


# Default to dark, then drive the toggle from the root theme attribute so stored
# preferences and every navbar theme icon stay in sync with the active mode.
THEME_TOGGLE_JS = """<script>
(function(){
  var d=document.documentElement;
  var theme;
  try{ theme=localStorage.getItem("theme"); }catch(e){ console.warn("Theme preference could not be read.",e); }
  if(theme!=="light" && theme!=="dark") theme="dark";
  d.setAttribute("data-bs-theme",theme);
  try{ localStorage.setItem("theme",theme); }catch(e){ console.warn("Theme preference could not be saved.",e); }
  function icons(){
    var dark=d.getAttribute("data-bs-theme")==="dark";
    document.querySelectorAll(".theme-switch i.fas").forEach(function(i){
      i.classList.toggle("fa-moon",dark); i.classList.toggle("fa-sun",!dark); });
  }
  document.addEventListener("click",function(ev){
    var target=ev.target instanceof Element ? ev.target : null;
    var b=target && target.closest(".theme-switch");
    if(!b) return;
    ev.preventDefault(); ev.stopImmediatePropagation();
    var t=d.getAttribute("data-bs-theme")==="dark"?"light":"dark";
    d.setAttribute("data-bs-theme",t);
    try{ localStorage.setItem("theme",t); }catch(e){ console.warn("Theme preference could not be saved.",e); }
    icons();
  },true);
  window.addEventListener("load",icons);
})();
</script>"""


def apply_theme() -> None:
    """Set CTFd's rendered theme header to the project-wide stylesheet."""
    css_path = REPO / "platform" / "ctfd" / "theme-custom.css"
    if not css_path.exists():
        print("  ! theme CSS not found — skipping theme")
        return
    css = css_path.read_text()
    header = f"{THEME_TOGGLE_JS}\n{STAGE_LOCK_UI_JS}\n<style>\n{css}\n</style>"
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
    parser = argparse.ArgumentParser(description="Seed Operation Blue Magpie into CTFd.")
    parser.add_argument(
        "--cleanup-duplicates",
        action="store_true",
        help="merge hints, remove duplicate stage records, and restore the stage locks only",
    )
    args = parser.parse_args()

    if args.cleanup_duplicates:
        print(f"Cleaning duplicate stage challenges in {URL} ...")
        remove_duplicate_stage_challenges()
        set_stage_prerequisites()
        print("Done. The six original stage entries and their solve history are preserved.")
        return

    require_artifacts()
    fl = flags()
    print(f"Seeding {URL} ...")
    remove_duplicate_stage_challenges()
    set_participant_visibility()
    print("  [visibility] challenges require sign-in; registration is public")
    grant_initial_points()
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

    set_stage_prerequisites()
    print("  [gating] S1 is open; each later stage unlocks after the previous stage is solved")

    apply_theme()
    set_home_page()
    print("\nDone. Six challenges live (with files), theme applied, home page branded.")


if __name__ == "__main__":
    main()
