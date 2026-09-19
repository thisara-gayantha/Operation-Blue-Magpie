#!/usr/bin/env bash
# Generate a self-signed TLS certificate for the Nginx edge (Step 4).
# Lab use only — self-signed, so browsers will warn; that is expected here.
#
# Usage:  ./scripts/gen_certs.sh [common_name]
#   common_name defaults to $SERVER_NAME from .env, else "localhost".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERT_DIR="$REPO_ROOT/platform/nginx/certs"

# Pull SERVER_NAME from .env if present.
CN="${1:-}"
if [[ -z "$CN" && -f "$REPO_ROOT/.env" ]]; then
    CN="$(grep -E '^SERVER_NAME=' "$REPO_ROOT/.env" | cut -d= -f2- || true)"
fi
CN="${CN:-localhost}"

mkdir -p "$CERT_DIR"

if [[ -f "$CERT_DIR/obm.crt" && -f "$CERT_DIR/obm.key" ]]; then
    echo "Certs already exist in $CERT_DIR (obm.crt / obm.key). Delete them to regenerate."
    exit 0
fi

echo "Generating self-signed cert for CN=$CN ..."
openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/obm.key" \
    -out "$CERT_DIR/obm.crt" \
    -days 365 \
    -subj "/C=LK/O=Operation Blue Magpie (LAB)/CN=$CN" \
    -addext "subjectAltName=DNS:$CN,DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/obm.key"
echo "Done:"
echo "  $CERT_DIR/obm.crt"
echo "  $CERT_DIR/obm.key   (keep private; git-ignored)"
