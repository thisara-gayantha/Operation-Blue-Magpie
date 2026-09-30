#!/usr/bin/env python3
"""
Operation Blue Magpie — S4 "The Foothold" vulnerable web app  (LAB ONLY).

CeylonPay staging login portal. The /api/v1/login endpoint contains a
DELIBERATE, unparameterised SQL query (string concatenation) so participants can
practise UNION-based SQL injection against the app's own MySQL database and dump
the `users` table. The S4 flag lives in a `secrets` table reachable via the same
injection.

This is an intentional teaching target, equivalent to DVWA / OWASP Juice Shop.
It runs only inside the isolated `challenge_net`; it is never exposed to a real
network. Do not deploy this outside the lab.
"""
import hashlib
import os

import pymysql
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

DB = dict(
    host=os.environ.get("MYSQL_HOST", "s4_db"),
    port=int(os.environ.get("MYSQL_PORT", "3306")),
    user=os.environ.get("MYSQL_USER", "appuser"),
    password=os.environ.get("MYSQL_PASSWORD", "apppass"),
    database=os.environ.get("MYSQL_DATABASE", "ceylonpay_app"),
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)

LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CeylonPay — Staging Portal</title>
<style>
 :root{color-scheme:dark;--bg:#0a0d13;--surface:#10151f;--surface-2:#151b27;--border:#26303f;--border-2:#38455c;--text:#e8eef7;--muted:#94a2b8;--faint:#63718a;--accent:#4c9aff;--accent-soft:rgba(76,154,255,.14)}
 *{box-sizing:border-box}
 body{font-family:Inter,system-ui,sans-serif;color:var(--text);max-width:452px;min-height:100vh;margin:0 auto;padding:clamp(18px,5vw,32px);display:flex;flex-direction:column;justify-content:center;background:radial-gradient(900px 420px at 50% -8%,rgba(76,154,255,.08),transparent 60%),linear-gradient(rgba(76,154,255,.028) 1px,transparent 1px) 0 0/46px 46px,linear-gradient(90deg,rgba(76,154,255,.028) 1px,transparent 1px) 0 0/46px 46px,var(--bg)}
 h1{font-family:'Space Grotesk',system-ui,sans-serif;font-size:1.4rem;color:#fff;overflow-wrap:anywhere}
 .card{min-width:0;border:1px solid var(--border);border-radius:8px;padding:clamp(16px,5vw,24px);background:var(--surface);box-shadow:0 12px 34px rgba(0,0,0,.3)}
 label{display:block;margin:.8rem 0 .3rem;color:var(--muted);font-size:.9rem}
 input{display:block;width:100%;min-width:0;padding:.7rem .75rem;border:1px solid var(--border);border-radius:8px;background:var(--surface-2);color:var(--text);font:inherit}
 input:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
 button{margin-top:1rem;width:100%;min-height:44px;padding:.7rem;border:1px solid var(--accent);border-radius:8px;background:var(--accent);color:#04121f;font:600 1rem 'Space Grotesk',system-ui,sans-serif;cursor:pointer}
 button:hover{filter:brightness(1.08)}
 pre{max-width:100%;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--surface-2);border:1px solid var(--border);padding:12px;border-radius:8px;color:var(--text)}
 .note{color:#ff7b88;font-size:.8rem;margin-top:1rem}
 @media(max-width:360px){body{padding:16px}h1{font-size:1.2rem}}
 @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important}}
</style></head>
<body>
 <h1>CeylonPay <span style="opacity:.6">· staging</span></h1>
 <div class="card">
  <label for="u">Username</label><input id="u" value="k.fernando">
  <label for="p">Password</label><input id="p" type="password">
  <button onclick="go()">Sign in</button>
  <pre id="out" hidden></pre>
 </div>
 <p class="note">STAGING REPLICA — authorised assessment use only.</p>
 <script>
 async function go(){
   const r = await fetch('/api/v1/login',{method:'POST',
     headers:{'Content-Type':'application/json'},
     body:JSON.stringify({username:document.getElementById('u').value,
                          password:document.getElementById('p').value})});
   const o=document.getElementById('out'); o.hidden=false;
   o.textContent = JSON.stringify(await r.json(), null, 2);
 }
 </script>
</body></html>"""


@app.get("/")
def index():
    return Response(LOGIN_PAGE, mimetype="text/html")


@app.get("/healthz")
def healthz():
    try:
        conn = pymysql.connect(**DB)
        conn.close()
        return jsonify(status="ok")
    except Exception as e:  # pragma: no cover
        return jsonify(status="db-unavailable", error=str(e)), 503


@app.post("/api/v1/login")
def login():
    data = request.get_json(silent=True) or request.form
    username = data.get("username", "")
    password = data.get("password", "")
    pw_md5 = hashlib.md5(password.encode()).hexdigest()

    # !!! INTENTIONALLY VULNERABLE — string-concatenated SQL (no parameters). !!!
    # This is the whole point of S4: a real UNION-injectable query. The username
    # field is the injection point; there are three selected columns.
    query = ("SELECT id, username, role FROM users "
             f"WHERE username = '{username}' AND password = '{pw_md5}'")

    try:
        conn = pymysql.connect(**DB)
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        conn.close()
    except Exception as e:
        # Verbose DB errors are deliberate here (error-based SQLi practice).
        return jsonify(status="error", query=query, error=str(e)), 200

    if rows:
        return jsonify(status="authenticated", results=list(rows))
    return jsonify(status="invalid-credentials", results=[])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
