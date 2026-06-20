# Security Policy

## Supported versions

TAUSIK ships fixes on the latest minor line. Security fixes land on the newest
patch release; please upgrade before reporting.

| Version | Supported |
|---|---|
| 1.5.x | ✅ |
| < 1.5 | ❌ (upgrade) |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately via GitHub **Security Advisories**:
[Report a vulnerability](https://github.com/Kibertum/tausik-core/security/advisories/new).

Include: affected version (`tausik --version` / `pyproject.toml`), repro steps,
and impact. We aim to acknowledge within a few business days and to coordinate a
fix + disclosure timeline with you.

## Scope

TAUSIK is a local-first, stdlib-only CLI/MCP framework — it runs and stores data
on your machine and makes no phone-home calls. Relevant surfaces:

- **Verification receipts** — ed25519-signed (`tausik-signed/v1`); receipt
  forgery/replay or signature-bypass is in scope.
- **Quality gates / hooks** — bypass of a fail-closed gate (QG-0/QG-2), the
  scope write-gate, or the push gate.
- **Shell-less gate runner** — command-injection via stack/gate templates.
- **Supply chain** — skill/stack install signature checks.

Out of scope: issues requiring a pre-compromised machine or operator-set bypass
env vars (e.g. `TAUSIK_SKIP_HOOKS`), and third-party skills/MCP servers you opt
into from external repos (report those upstream).
