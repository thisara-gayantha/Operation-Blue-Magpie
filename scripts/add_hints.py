#!/usr/bin/env python3
"""
add_hints.py — adds per-challenge HINTS to CTFd so the "Hint" button appears for
players. Put at: scripts/add_hints.py  (reads platform/ctfd/hints.json)

Run after the challenges are seeded, with an admin API token
(CTFd -> Admin -> Settings -> Access Tokens):
    CTFD_URL=https://localhost CTFD_TOKEN=<token> python scripts/add_hints.py

Stdlib only. Hints are matched to challenges by their leading "S1".."S6" token.
Each hint costs points (set in hints.json), which is the normal CTFd behaviour.
"""
from __future__ import annotations
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
URL = os.environ.get("CTFD_URL", "https://localhost").rstrip("/")
TOKEN = os.environ.get("CTFD_TOKEN", "")
if not TOKEN:
    sys.exit("Set CTFD_TOKEN to an admin Access Token.")

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
H = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}


def api(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, headers=H, method=method)
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        return json.loads(r.read())


def main() -> None:
    hints = json.loads((REPO / "platform" / "ctfd" / "hints.json").read_text())
    chals = api("GET", "/api/v1/challenges").get("data", [])
    added = 0
    for c in chals:
        key = c["name"].split()[0]           # "S1" from "S1 · The Phishing Lure"
        for h in hints.get(key, []):
            api("POST", "/api/v1/hints",
                {"challenge_id": c["id"], "content": h["content"], "cost": h["cost"]})
            added += 1
            print(f"  [{key}] hint added (cost {h['cost']})")
    print(f"\nDone — {added} hints added. The Hint button now shows on those challenges.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[!] {e}\n    Is CTFd up, the token valid, and hints.json present?")
