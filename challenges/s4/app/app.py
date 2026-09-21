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
 :root{color-scheme:light dark}
 body{font-family:system-ui,Segoe UI,Roboto,sans-serif;max-width:420px;margin:6vh auto;padding:0 16px}
 h1{font-size:1.3rem} .card{border:1px solid #8884;border-radius:12px;padding:20px}
 label{display:block;margin:.6rem 0 .2rem;font-size:.9rem}
 input{width:100%;padding:.55rem;border:1px solid #8886;border-radius:8px;box-sizing:border-box}
 button{margin-top:1rem;width:100%;padding:.6rem;border:0;border-radius:8px;background:#2b6cb0;color:#fff;font-weight:600}
 pre{white-space:pre-wrap;word-break:break-word;background:#8881;padding:12px;border-radius:8px}
 .note{color:#c33;font-size:.8rem;margin-top:1rem}
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
