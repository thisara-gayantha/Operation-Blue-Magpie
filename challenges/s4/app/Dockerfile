# S4 vulnerable web app (CeylonPay staging portal). LAB ONLY.
# Multi-arch base (works on Ubuntu x86_64 and Apple Silicon arm64).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

# Run unprivileged. Combined with cap_drop=ALL + no-new-privileges in compose,
# the app has no path to escalate on the host.
RUN useradd -m -u 10001 appuser
USER appuser

EXPOSE 8080
# gunicorn on a high port (no CAP_NET_BIND_SERVICE needed once caps are dropped).
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "--access-logfile", "-", "app:app"]
