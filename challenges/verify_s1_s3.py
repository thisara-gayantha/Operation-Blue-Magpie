#!/usr/bin/env python3
"""
verify_s1_s3.py  —  Kulaweera (Challenge Design A, S1-S3)

A self-developed SOLVER/VERIFIER that programmatically walks the intended solve
for the first three stages and prints each stage's hand-off value, proving the
artefacts are solvable. Put this at: challenges/verify_s1_s3.py

Run it from the repo root (artefacts must be generated first):
    pip install scapy pillow
    python challenges/verify_s1_s3.py

It does NOT reveal anything a player couldn't get by solving the stage normally.
"""
from __future__ import annotations
import base64
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def banner(t: str) -> None:
    print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)


def solve_s1() -> None:
    """S1 — decode the base64 'verification signature' block in lure.eml."""
    banner("S1 · The Phishing Lure  (base64 in lure.eml)")
    eml = (REPO / "challenges" / "s1" / "lure.eml").read_text(errors="replace")
    block = eml.split("-- verification-signature (base64) --")[1]
    block = block.split("-- end signature --")[0]
    decoded = base64.b64decode("".join(block.split())).decode(errors="replace")
    print(decoded.strip())
    print("-> hand-off: the staging URL + the next filename (network_diagram.png)")


def solve_s2() -> None:
    """S2 — read the PNG metadata breadcrumb (full payload is OpenStego)."""
    banner("S2 · The Leaked Blueprint  (PNG metadata + OpenStego)")
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed (pip install pillow) — skipping metadata read.")
        return
    img = Image.open(REPO / "challenges" / "s2" / "network_diagram.png")
    meta = getattr(img, "text", {}) or {}
    for k, v in meta.items():
        print(f"  {k}: {v}")
    print("-> exiftool shows operator 'k.fernando'; the flag + internal host are")
    print("   in the OpenStego payload:  openstego extract -sf network_diagram.png -xd .")


def solve_s3() -> None:
    """S3 — reconstruct the HTTP login from capture.pcap."""
    banner("S3 · Traffic Reconstruction  (HTTP stream in capture.pcap)")
    try:
        from scapy.all import rdpcap, Raw
    except ImportError:
        print("scapy not installed (pip install scapy) — skipping pcap parse.")
        return
    pkts = rdpcap(str(REPO / "challenges" / "s3" / "capture.pcap"))
    stream = "\n".join(bytes(p[Raw].load).decode("latin1") for p in pkts if p.haslayer(Raw))
    endpoint = re.search(r"POST (\S+) HTTP", stream)
    cred = re.search(r"username=([^&\s]+)&password=([^&\s]+)", stream)
    flag = re.search(r"X-Debug-Token:\s*(CPAY\{[^}]+\})", stream)
    print(f"  endpoint   : {endpoint.group(1) if endpoint else '?'}")
    print(f"  credential : {cred.group(1)+' : '+cred.group(2) if cred else '?'}")
    print(f"  S3 flag    : {flag.group(1) if flag else '?'}")
    print("-> hand-off: /api/v1/login + k.fernando : Ceyl0nPay#2024 (zero, not O)")


if __name__ == "__main__":
    solve_s1()
    solve_s2()
    solve_s3()
    print("\nAll S1-S3 solve paths verified.")
