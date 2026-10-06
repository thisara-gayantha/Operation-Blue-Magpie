#!/usr/bin/env bash
# Embed the S2 payload into the cover PNG with OpenStego (RandomLSB), producing
# the final challenges/s2/network_diagram.png that gets uploaded to CTFd.
#
# Prereqs: Java + OpenStego 0.8.x. Point OPENSTEGO_JAR at openstego.jar, or put
# `openstego` on PATH. Download: https://github.com/syvaidya/openstego/releases
#
# Run scripts/gen_artifacts.py first (it writes the cover + payload).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
S2="$REPO/challenges/s2"

COVER="$S2/network_diagram_cover.png"
PAYLOAD="$S2/s2_payload.txt"
OUT="$S2/network_diagram.png"

[[ -f "$COVER" && -f "$PAYLOAD" ]] || {
    echo "Cover/payload missing — run: python3 scripts/gen_artifacts.py" >&2
    exit 1
}

run_openstego() {
    if [[ -n "${OPENSTEGO_JAR:-}" ]]; then
        java -Djava.awt.headless=true -jar "$OPENSTEGO_JAR" "$@"
    elif command -v openstego >/dev/null 2>&1; then
        openstego "$@"
    else
        echo "OpenStego not found. Set OPENSTEGO_JAR=/path/to/openstego.jar" >&2
        exit 1
    fi
}

run_openstego embed -mf "$PAYLOAD" -cf "$COVER" -sf "$OUT"
echo "Created $OUT"
echo "Verify:  openstego extract -sf \"$OUT\" -xd /tmp/s2check"
