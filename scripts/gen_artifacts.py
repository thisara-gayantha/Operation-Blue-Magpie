#!/usr/bin/env python3
"""
gen_artifacts.py — build the static challenge artefacts for S1, S3, S5 and the
S2 cover+payload. Run scripts/gen_flags.py first (it writes challenges/.flags.json).

Everything produced here is fictional CeylonPay lab content for the isolated
Operation Blue Magpie CTF. Flag VALUES come from .flags.json at runtime, so this
script never hardcodes them.

Outputs (all git-ignored — regenerate any time):
  challenges/s1/lure.eml
  challenges/s3/capture.pcap
  challenges/s5/users_dump.txt
  challenges/s5/s5_wordlist.txt
  challenges/s2/network_diagram_cover.png   (cover; embed with scripts/embed_s2.sh)
  challenges/s2/s2_payload.txt              (secret embedded into the PNG)
"""
from __future__ import annotations
import hashlib
import json
import textwrap
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ---- Locked scenario hand-off values (NOT the flags) -----------------------
STAGING_URL = "http://staging.ceylonpay.lk"
NEXT_FILE = "network_diagram.png"
S2_USER = "k.fernando"
INTERNAL_HOST = "api-internal.ceylonpay.lk"
LOGIN_ENDPOINT = "/api/v1/login"
S3_USER = "k.fernando"
S3_PASS = "Ceyl0nPay#2024"          # zero, not letter O
S6_SSH_USER = "svc-deploy"
S6_SSH_PASS = "Bl@ckout#Deploy1"


def load_flags() -> tuple[dict, dict]:
    p = REPO / "challenges" / ".flags.json"
    if not p.exists():
        raise SystemExit("challenges/.flags.json missing — run scripts/gen_flags.py first.")
    data = json.loads(p.read_text())
    return data["flags"], data["tokens"]


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


# ============================================================================
# S1 — The Phishing Lure  (lure.eml)
# ============================================================================
def build_s1(flags: dict) -> None:
    import base64
    flag = flags["S1"]

    # The hand-off + flag, base64-encoded — recovered with `base64 -d` / strings.
    hidden = (
        f"CeylonPay staging portal: {STAGING_URL}\n"
        f"Asset to retrieve next: {NEXT_FILE}\n"
        f"FLAG: {flag}\n"
    )
    b64 = base64.b64encode(hidden.encode()).decode()
    b64_wrapped = "\n".join(textwrap.wrap(b64, 76))

    msg = EmailMessage()
    # Look-alike sender domain (ceylonpay-secure.lk, not ceylonpay.lk) — a clue.
    msg["From"] = "CeylonPay IT Support <it-support@ceylonpay-secure.lk>"
    msg["To"] = "Kasun Fernando <k.fernando@ceylonpay.lk>"
    msg["Reply-To"] = "helpdesk@secure-verify-mail.com"      # mismatch — clue
    msg["Subject"] = "[ACTION REQUIRED] Verify the updated network diagram"
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain="ceylonpay-secure.lk")
    msg["X-Originating-IP"] = "[203.0.113.66]"               # external — clue
    msg["Received"] = ("from mail.secure-verify-mail.com (unknown [203.0.113.66]) "
                       "by mx.ceylonpay.lk with ESMTP; " + formatdate(localtime=False))

    body = f"""\
Dear Kasun,

As part of the quarterly infrastructure review, IT Support has published an
updated network diagram to the staging portal. Please review it at your
earliest convenience:

    {STAGING_URL}

The relevant asset is attached to the portal as "{NEXT_FILE}". Kindly confirm
the layout is accurate for your team.

For audit purposes, this message carries a verification signature block below.

Regards,
CeylonPay IT Support

-- verification-signature (base64) --
{b64_wrapped}
-- end signature --
"""
    msg.set_content(body)

    out = REPO / "challenges" / "s1" / "lure.eml"
    out.write_bytes(bytes(msg))
    print(f"[S1] {out.relative_to(REPO)}")


# ============================================================================
# S3 — Traffic Reconstruction  (capture.pcap)
# ============================================================================
def build_s3(flags: dict) -> None:
    from scapy.all import Ether, IP, TCP, Raw, wrpcap

    flag = flags["S3"]
    client_ip, server_ip = "10.10.14.7", "172.20.0.10"
    cport, sport = 49678, 80

    body = f"username={S3_USER}&password={S3_PASS}"
    http_req = (
        f"POST {LOGIN_ENDPOINT} HTTP/1.1\r\n"
        f"Host: {INTERNAL_HOST}\r\n"
        f"User-Agent: curl/8.4.0\r\n"
        f"Accept: */*\r\n"
        f"Content-Type: application/x-www-form-urlencoded\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"\r\n{body}"
    )
    resp_json = (
        '{"status":"ok","user":"' + S3_USER + '",'
        '"note":"session established for ' + LOGIN_ENDPOINT + '"}'
    )
    http_resp = (
        "HTTP/1.1 200 OK\r\n"
        "Server: nginx\r\n"
        "Content-Type: application/json\r\n"
        f"X-Debug-Token: {flag}\r\n"
        f"Content-Length: {len(resp_json)}\r\n"
        f"\r\n{resp_json}"
    )

    eth = Ether()
    isn_c, isn_s = 1000, 5000
    pkts = []
    # 3-way handshake
    pkts.append(eth/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="S", seq=isn_c))
    pkts.append(eth/IP(src=server_ip, dst=client_ip)/TCP(sport=sport, dport=cport, flags="SA", seq=isn_s, ack=isn_c+1))
    pkts.append(eth/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="A", seq=isn_c+1, ack=isn_s+1))
    # request
    pkts.append(eth/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="PA", seq=isn_c+1, ack=isn_s+1)/Raw(load=http_req.encode()))
    ack_after_req = isn_c + 1 + len(http_req)
    pkts.append(eth/IP(src=server_ip, dst=client_ip)/TCP(sport=sport, dport=cport, flags="A", seq=isn_s+1, ack=ack_after_req))
    # response
    pkts.append(eth/IP(src=server_ip, dst=client_ip)/TCP(sport=sport, dport=cport, flags="PA", seq=isn_s+1, ack=ack_after_req)/Raw(load=http_resp.encode()))
    pkts.append(eth/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="A", seq=ack_after_req, ack=isn_s+1+len(http_resp)))

    out = REPO / "challenges" / "s3" / "capture.pcap"
    wrpcap(str(out), pkts)
    print(f"[S3] {out.relative_to(REPO)}  ({len(pkts)} packets)")


# ============================================================================
# S5 — Cracking the Vault  (users_dump.txt + s5_wordlist.txt)
# ============================================================================
def build_s5(flags: dict, tokens: dict) -> None:
    token = tokens["S5"]                      # 6-hex; cracked via mask ?h*6

    # Decoy accounts with rockyou-style passwords (noise) + the two that matter.
    decoys = {
        "a.silva": "password1",
        "n.perera": "sunshine",
        "r.jayasuriya": "liverpool",
        "d.wickrama": "iloveyou",
        "s.bandara": "qwerty123",
    }
    rows = []
    for user, pw in decoys.items():
        rows.append(f"{user}:{md5(pw)}")
    # svc-deploy -> S6 SSH password (hand-off); crackable via the provided wordlist
    rows.append(f"{S6_SSH_USER}:{md5(S6_SSH_PASS)}")
    # vault-service -> md5 of the 6-hex S5 token; crack via mask attack to read it,
    # then wrap as CPAY{{S5_vault_<token>}}
    rows.append(f"vault-service:{md5(token)}")

    dump = REPO / "challenges" / "s5" / "users_dump.txt"
    dump.write_text("# users table dump (unsalted MD5) — recovered from S4\n"
                    "# format: username:md5\n" + "\n".join(rows) + "\n")

    # Curated wordlist so svc-deploy is deterministically crackable in the lab.
    wl = list(decoys.values()) + [
        "Deploy2023", "Bl@ckout#Deploy0", "Bl@ckout#Deploy1", "Bl@ckout#Deploy2",
        "ceylonpay", "Ceyl0nPay#2024", "svc-deploy", "changeme",
    ]
    (REPO / "challenges" / "s5" / "s5_wordlist.txt").write_text("\n".join(wl) + "\n")
    print(f"[S5] {dump.relative_to(REPO)}  ({len(rows)} hashes) + s5_wordlist.txt")


# ============================================================================
# S2 — The Leaked Blueprint  (cover PNG + payload; embed separately with OpenStego)
# ============================================================================
def build_s2(flags: dict) -> None:
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

    flag = flags["S2"]
    s2dir = REPO / "challenges" / "s2"

    # --- payload (the secret embedded into the PNG) ---
    payload = (
        "CeylonPay — internal network blueprint (CONFIDENTIAL)\n"
        f"Prepared by operator: {S2_USER}\n"
        f"Internal API host: {INTERNAL_HOST}\n"
        f"FLAG: {flag}\n"
    )
    (s2dir / "s2_payload.txt").write_text(payload)

    # --- cover image: a simple network diagram ---
    W, H = 960, 600
    img = Image.new("RGB", (W, H), (245, 247, 250))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        fbig = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
        fbig = font

    d.text((24, 20), "CeylonPay — Staging Network Diagram", fill=(20, 30, 60), font=fbig)

    def box(x, y, w, h, label, color):
        d.rectangle([x, y, x + w, y + h], outline=(40, 50, 70), width=2, fill=color)
        d.text((x + 12, y + h // 2 - 10), label, fill=(15, 20, 40), font=font)

    box(60, 110, 180, 60, "Internet", (223, 232, 245))
    box(60, 250, 180, 60, "Edge Firewall", (223, 232, 245))
    box(380, 110, 200, 60, "Web / Nginx", (214, 240, 224))
    box(380, 250, 200, 60, INTERNAL_HOST, (214, 240, 224))
    box(720, 180, 180, 60, "PostgreSQL", (245, 228, 222))
    for a, b in [((150,170),(150,250)), ((240,280),(380,280)),
                 ((480,170),(480,250)), ((580,280),(720,210)), ((480,140),(480,110))]:
        d.line([a, b], fill=(90, 100, 120), width=2)
    d.text((24, H - 40), "Classification: INTERNAL — do not distribute", fill=(150, 40, 40), font=font)

    # exiftool breadcrumb in PNG text metadata (reveals the operator name).
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Author", S2_USER)
    meta.add_text("Comment", "Exported from CeylonPay NetDocs. Contains embedded notes.")
    out = s2dir / "network_diagram_cover.png"
    img.save(out, "PNG", pnginfo=meta)
    print(f"[S2] {out.relative_to(REPO)} + s2_payload.txt "
          f"(embed into final {NEXT_FILE} with scripts/embed_s2.sh)")


def main() -> None:
    flags, tokens = load_flags()
    build_s1(flags)
    build_s3(flags)
    build_s5(flags, tokens)
    build_s2(flags)
    print("\nDone. Next: run scripts/embed_s2.sh to produce the final network_diagram.png")


if __name__ == "__main__":
    main()
