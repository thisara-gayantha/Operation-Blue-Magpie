#!/usr/bin/env python3
"""
gen_flags.py — mint the six Operation Blue Magpie flags.

Flag format (locked):  CPAY{S<n>_<slug>_<6-hex-token>}   case-sensitive.

Each run generates fresh random 6-hex tokens, so every deployment of the box
has unique flags. Outputs:

  challenges/.flags.json   (git-ignored)  machine-readable {stage: flag, ...},
                                          consumed by gen_artifacts.py
  flags.local              (git-ignored)  human-readable list for configuring
                                          CTFd and for the team's reference
  docs/flags.hashed.txt    (committable)  SHA-256 of each flag only — a
                                          non-reversible manifest so the repo
                                          records WHICH flags exist without
                                          leaking their values

Nothing here touches a real system; flags are lab tokens.
"""
from __future__ import annotations
import hashlib
import json
import secrets
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Stage -> slug (locked). Token is random per run.
SLUGS = {
    "S1": "phish",
    "S2": "blueprint",
    "S3": "traffic",
    "S4": "foothold",
    "S5": "vault",
    "S6": "root",
}


def make_token() -> str:
    """6 hex chars (24 bits) — matches the locked CPAY{...} format."""
    return secrets.token_hex(3)


def main() -> None:
    flags: dict[str, str] = {}
    tokens: dict[str, str] = {}
    for stage, slug in SLUGS.items():
        tok = make_token()
        tokens[stage] = tok
        flags[stage] = f"CPAY{{{stage}_{slug}_{tok}}}"

    # .flags.json — includes the raw token too, so gen_artifacts can embed the
    # S5 crackable token without re-parsing the flag string.
    flags_json = REPO / "challenges" / ".flags.json"
    flags_json.write_text(json.dumps({"flags": flags, "tokens": tokens}, indent=2))

    # flags.local — plaintext for the team + CTFd config.
    lines = ["# Operation Blue Magpie — FLAGS (lab secret, git-ignored)",
             "# Configure these as case-sensitive static flags in CTFd.", ""]
    for stage in SLUGS:
        lines.append(f"{stage}  {flags[stage]}")
    (REPO / "flags.local").write_text("\n".join(lines) + "\n")

    # docs/flags.hashed.txt — SHA-256 only (safe to commit).
    hashed = ["# SHA-256 of each flag (non-reversible manifest). Not the flags.",
              ""]
    for stage in SLUGS:
        h = hashlib.sha256(flags[stage].encode()).hexdigest()
        hashed.append(f"{stage}  sha256={h}")
    (REPO / "docs" / "flags.hashed.txt").write_text("\n".join(hashed) + "\n")

    print("Generated 6 flags.")
    print(f"  -> {flags_json.relative_to(REPO)}   (git-ignored)")
    print(f"  -> flags.local                        (git-ignored)")
    print(f"  -> docs/flags.hashed.txt              (committable)")
    print("\nConfigure these in CTFd (case-sensitive):")
    for stage in SLUGS:
        print(f"  {stage}: {flags[stage]}")


if __name__ == "__main__":
    main()
