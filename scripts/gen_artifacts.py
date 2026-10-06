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

    # Fixed lab MAC addresses so scapy never probes the network to resolve them
    # (avoids the getmacbyip / /dev/bpf warnings and keeps generation offline).
    c2s = Ether(src="02:42:0a:0a:0e:07", dst="02:42:ac:14:00:0a")  # client -> server
    s2c = Ether(src="02:42:ac:14:00:0a", dst="02:42:0a:0a:0e:07")  # server -> client
    isn_c, isn_s = 1000, 5000
    pkts = []
    # 3-way handshake
    pkts.append(c2s/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="S", seq=isn_c))
    pkts.append(s2c/IP(src=server_ip, dst=client_ip)/TCP(sport=sport, dport=cport, flags="SA", seq=isn_s, ack=isn_c+1))
    pkts.append(c2s/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="A", seq=isn_c+1, ack=isn_s+1))
    # request
    pkts.append(c2s/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="PA", seq=isn_c+1, ack=isn_s+1)/Raw(load=http_req.encode()))
    ack_after_req = isn_c + 1 + len(http_req)
    pkts.append(s2c/IP(src=server_ip, dst=client_ip)/TCP(sport=sport, dport=cport, flags="A", seq=isn_s+1, ack=ack_after_req))
    # response
    pkts.append(s2c/IP(src=server_ip, dst=client_ip)/TCP(sport=sport, dport=cport, flags="PA", seq=isn_s+1, ack=ack_after_req)/Raw(load=http_resp.encode()))
    pkts.append(c2s/IP(src=client_ip, dst=server_ip)/TCP(sport=cport, dport=sport, flags="A", seq=ack_after_req, ack=isn_s+1+len(http_resp)))

    out = REPO / "challenges" / "s3" / "capture.pcap"
    wrpcap(str(out), pkts)
    print(f"[S3] {out.relative_to(REPO)}  ({len(pkts)} packets)")


# ============================================================================
# Shared CeylonPay user set — the SAME rows seed the S4 MySQL `users` table and
# form the S5 hash dump, so S4's dump chains straight into S5.
# ============================================================================
def ceylonpay_users(token: str) -> list[tuple[str, str, str]]:
    """(username, plaintext_password, role). The plaintext is what MD5s into the
    stored hash; it is never shipped — only the MD5 is."""
    return [
        (S3_USER, S3_PASS, "analyst"),          # k.fernando — the S3 login (valid)
        ("a.silva", "password1", "user"),
        ("n.perera", "sunshine", "user"),
        ("r.jayasuriya", "liverpool", "user"),
        ("d.wickrama", "iloveyou", "user"),
        ("s.bandara", "qwerty123", "user"),
        (S6_SSH_USER, S6_SSH_PASS, "service"),  # svc-deploy -> S6 SSH password
        ("vault-service", token, "service"),    # md5(6-hex token) -> S5 flag token
    ]


# ============================================================================
# S5 — Cracking the Vault  (users_dump.txt + s5_wordlist.txt)
# ============================================================================
def build_s5(flags: dict, tokens: dict) -> None:
    token = tokens["S5"]                      # 6-hex; cracked via mask ?h*6
    users = ceylonpay_users(token)

    rows = [f"{u}:{md5(pw)}" for (u, pw, _role) in users]
    dump = REPO / "challenges" / "s5" / "users_dump.txt"
    dump.write_text("# users table dump (unsalted MD5) — recovered from S4\n"
                    "# format: username:md5\n" + "\n".join(rows) + "\n")

    # Curated wordlist so svc-deploy is deterministically crackable in the lab
    # (decoys are also rockyou-style). The 6-hex vault token is NOT in the list —
    # it is meant to fall to a mask attack, not a dictionary.
    wl = [pw for (_u, pw, _r) in users if _u != "vault-service"] + [
        "Deploy2023", "Bl@ckout#Deploy0", "Bl@ckout#Deploy2", "changeme",
    ]
    (REPO / "challenges" / "s5" / "s5_wordlist.txt").write_text("\n".join(wl) + "\n")
    print(f"[S5] {dump.relative_to(REPO)}  ({len(rows)} hashes) + s5_wordlist.txt")


# ============================================================================
# S4 — The Foothold  (MySQL seed init.sql — vulnerable app's own database)
# ============================================================================
def build_s4_seed(flags: dict, tokens: dict) -> None:
    users = ceylonpay_users(tokens["S5"])
    flag = flags["S4"]

    def sql_str(s: str) -> str:
        return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"

    lines = [
        "-- Operation Blue Magpie S4 — CeylonPay staging app database (LAB).",
        "-- Auto-generated by gen_artifacts.py; git-ignored (contains the flag).",
        "-- Unsalted MD5 password hashes are INTENTIONAL (the teaching point).",
        "",
        "CREATE TABLE IF NOT EXISTS users (",
        "  id INT AUTO_INCREMENT PRIMARY KEY,",
        "  username VARCHAR(64) NOT NULL,",
        "  password CHAR(32) NOT NULL,      -- unsalted MD5",
        "  role VARCHAR(32) NOT NULL DEFAULT 'user'",
        ");",
        "",
    ]
    for (u, pw, role) in users:
        lines.append(
            f"INSERT INTO users (username, password, role) VALUES "
            f"({sql_str(u)}, {sql_str(md5(pw))}, {sql_str(role)});"
        )
    # secrets table — the S4 flag, reachable via UNION-based injection.
    lines += [
        "",
        "CREATE TABLE IF NOT EXISTS secrets (",
        "  id INT AUTO_INCREMENT PRIMARY KEY,",
        "  name VARCHAR(64) NOT NULL,",
        "  value VARCHAR(128) NOT NULL",
        ");",
        f"INSERT INTO secrets (name, value) VALUES ('ctf_flag', {sql_str(flag)});",
        "",
    ]
    out = REPO / "challenges" / "s4" / "seed" / "init.sql"
    out.write_text("\n".join(lines) + "\n")
    print(f"[S4] {out.relative_to(REPO)}  ({len(users)} users + secrets/flag)")


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


# ============================================================================
# S6 — Total Compromise  (root flag + SSH credential for the container build)
# ============================================================================
def build_s6(flags: dict) -> None:
    s6build = REPO / "challenges" / "s6" / "build"
    s6build.mkdir(parents=True, exist_ok=True)
    # Consumed by challenges/s6/Dockerfile at build time (both git-ignored).
    (s6build / "flag.txt").write_text(flags["S6"] + "\n")        # -> /root/flag.txt
    (s6build / "svc_pass.txt").write_text(S6_SSH_PASS + "\n")    # svc-deploy password
    print("[S6] challenges/s6/build/flag.txt + svc_pass.txt")


def main() -> None:
    flags, tokens = load_flags()
    build_s1(flags)
    build_s3(flags)
    build_s5(flags, tokens)
    build_s4_seed(flags, tokens)
    build_s6(flags)
    build_s2(flags)
    print("\nDone. Next: run scripts/embed_s2.sh to produce the final network_diagram.png")


if __name__ == "__main__":
    main()
