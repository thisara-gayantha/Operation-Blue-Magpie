# Safety & Scope

Operation Blue Magpie is an **educational Capture-The-Flag lab** for the IE3132
Penetration Testing module at SLIIT. It is designed, built and run entirely
inside an isolated Docker environment.

## The boundary

- **CeylonPay is fictional.** There is no real company, no real customer data,
  no real payment system. Every domain name (`*.ceylonpay.lk`), account,
  credential and host in this project is invented for the exercise.
- **All targets are local containers.** The vulnerable web app (S4) and Linux
  box (S6) exist only as containers on this project's Docker networks. They are
  never deployed to, or aimed at, any real host or network.
- **No internet egress from challenge containers.** Firewall rules (Step 8)
  block challenge containers from reaching the internet or the platform
  database. This both keeps the lab self-contained and prevents any accidental
  outbound activity.
- **Deliberately weak by design.** The SQL-injection point (S4) and SUID
  misconfiguration (S6) are intentional teaching targets, equivalent to
  standard training ranges (DVWA, OWASP Juice Shop, Metasploitable,
  VulnHub-style boxes). They demonstrate *how a defender finds and fixes* these
  issues in a sandbox.

## Operating rules

1. Run this only on a host you control that is set aside for the exercise
   (a dedicated VM or lab machine), never on production infrastructure.
2. Do not expose the challenge ports to an untrusted network. The intended
   audience is the assessment team on an isolated segment.
3. Credentials and flags in this repo are lab artefacts. Do not reuse any of
   them anywhere real.
4. The isolation controls (network internal flags, ICC off, capability drops,
   `no-new-privileges`, user-namespace remapping, resource limits, egress
   firewall) are part of the deliverable and must be verified before the box is
   used — see `scripts/` and the test matrix.

If any control turns out to be technically infeasible on the target host, it is
flagged in `docs/` rather than quietly worked around.
