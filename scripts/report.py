#!/usr/bin/env python3
"""
report.py  —  Dasanayake (Integration, Testing & Documentation)

A self-developed AUTOMATION/TESTING script: runs the functional, flag-injection
and resource/privilege checks against the running stack and writes a clean HTML
test report to docs/test-report.html with pass/fail and a timestamp.
Put this at: scripts/report.py

Usage (stack must be up):
    python scripts/report.py
    python scripts/report.py http://localhost:8004    # S4 base, optional

Stdlib only (urllib + subprocess). Records only what it actually observes.
"""
from __future__ import annotations
import datetime
import json
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
S4 = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8004").rstrip("/")
results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, str(e)
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {detail}")


def http_code(url: str) -> int:
    ctx = ssl.create_default_context(); ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url, timeout=8, context=ctx) as r:
        return r.getcode()


def c_ctfd():
    code = http_code("https://localhost/")
    return code in (200, 302), f"CTFd via Nginx/TLS returned HTTP {code}"


def c_s4_health():
    with urllib.request.urlopen(S4 + "/healthz", timeout=8) as r:
        body = r.read().decode()
    return '"ok"' in body, f"S4 /healthz: {body.strip()}"


def c_s4_inject():
    data = json.dumps({"username": "zzz' UNION SELECT id, value, name FROM secrets-- -",
                       "password": "x"}).encode()
    req = urllib.request.Request(S4 + "/api/v1/login", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read().decode()
    return "CPAY{S4_" in body, "UNION injection returned the S4 flag" if "CPAY{S4_" in body else "no flag returned"


def c_limits():
    out = subprocess.run(["docker", "inspect", "-f", "{{.HostConfig.Memory}}", "obm_s4_web"],
                         capture_output=True, text=True, timeout=15).stdout.strip()
    return out.isdigit() and int(out) > 0, f"s4_web memory limit = {out}"


def c_capdrop():
    out = subprocess.run(["docker", "inspect", "-f", "{{.HostConfig.CapDrop}}", "obm_s4_web"],
                         capture_output=True, text=True, timeout=15).stdout
    return "ALL" in out.upper(), f"s4_web CapDrop = {out.strip()}"


checks = [
    ("CTFd reachable (Nginx/TLS)", c_ctfd),
    ("S4 app healthy", c_s4_health),
    ("S4 SQL injection yields flag", c_s4_inject),
    ("S4 resource limit set", c_limits),
    ("S4 cap_drop=ALL", c_capdrop),
]

if __name__ == "__main__":
    print("Running test matrix ...")
    for name, fn in checks:
        check(name, fn)
    passed = sum(1 for _, ok, _ in results if ok)
    rows = "".join(
        f'<tr><td>{n}</td><td class="{ "p" if ok else "f" }">{"PASS" if ok else "FAIL"}</td>'
        f'<td>{d}</td></tr>' for n, ok, d in results)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>OBM Test Report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:860px;margin:30px auto;padding:0 16px;color:#111}}
h1{{color:#0b1220}} .m{{color:#555}} table{{border-collapse:collapse;width:100%;margin-top:14px}}
th,td{{border:1px solid #ddd;padding:9px 12px;text-align:left}} th{{background:#eef3fb;color:#1e3a8a}}
.p{{color:#0f9d76;font-weight:700}} .f{{color:#d92d3f;font-weight:700}}</style></head><body>
<h1>Operation Blue Magpie — Test Report</h1>
<p class="m">Run: {datetime.datetime.now().isoformat(timespec='seconds')} · {passed}/{len(results)} passed</p>
<table><thead><tr><th>Test</th><th>Result</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>
<p class="m">Note: S6 end-to-end (SSH + SUID escalation) is verified manually and recorded separately.</p>
</body></html>"""
    out = REPO / "docs" / "test-report.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"\n{passed}/{len(results)} passed  ->  {out}")
