# Skill store supply-chain threat model

> Task `l26-skill-supply-chain-threat`. Russian mirror:
> [`skill-supply-chain-threat-model.ru.md`](../ru/skill-supply-chain-threat-model.md).
> Companion to [`security.md`](security.md).

## Why this exists

The dominant 2026 attack vector is not the MCP server — it is the **markdown
skill**. A skill's payload is *prose the agent reads verbatim*, so signature
scanning of the *bytes* proves who published it but says nothing about hidden
intent in the *text*. The public data:

- **Snyk ToxicSkills** (2026-02-05): of 3 984 skills sampled, 36.8 % had
  problems, 13.4 % critical; 76 confirmed malicious (8 still live at
  publication); 91 % of the malicious ones used prompt injection; 10.9 % carried
  hardcoded secrets.
- **ClawHavoc** (Feb 2026): 341 malicious skills out of 2 857, dropping the AMOS
  infostealer; the registry purged 2 419.
- **Unit 42** (Jun 2026): scanner evasion by inflating the README to 22 MB;
  runtime substitution of the agent's recommendations.
- **Orca** (May 2026): scanning happens only at creation, so swapping the
  artifact *after* the check succeeds.

Unit 42's framing cuts to the root: the ecosystem **lacks isolation between a
skill's logic and the agent's authority**. This document models TAUSIK's own
skill store against those primitives and records, per vector, whether it is
mitigated, accepted, or deferred — with the actual code that does the work.

## What TAUSIK already does (the trust boundary)

There are **two** paths a skill can take into the activated `.claude/skills/`
tree — `install` (`skill_manager.install_skill` → `copy_skill`) and `activate`
(`service_skills.skill_activate`) — and **both** run the same guards. (Review
s146 found the content scan had at first been added only to `copy_skill`, leaving
`activate` a signature-checked but content-unscanned bypass; the invisible-Unicode
scan is now the shared guard `skill_content_scan.assert_skill_tree_clean` that
both call — the recurrence of an install/activate drift the `skill_tree_ignore`
docstring already warned about.) Before any file lands, each path performs, in
order:

1. **ed25519 publisher-signature check** (`supply_verify_install.check_skill_signature`,
   `install_skill`): `block` refuses, `warn` proceeds (the adoption path for
   unsigned repos / no pinned key yet), `ok` verifies against the key pinned per
   repo. OMS / Sigstore was evaluated and **rejected by the owner** — TAUSIK
   stays on its own ed25519 receipts and pinned keys.
2. **Path-traversal guard** (`_validate_path_inside`): the skill source must
   resolve inside the repo dir.
3. **Symlink-smuggling guard** (`copy_skill`, `shutil.copytree(..., symlinks=False)`):
   a hostile repo cannot smuggle an absolute path (`~/.aws/credentials`,
   `/etc/shadow`) into the skills tree via a symlink.
4. **Invisible-Unicode content scan** (`skill_content_scan.scan_skill_tree`,
   added by this task — see below).

Two structural facts outside the install path matter as much:

- **Project config is untrusted.** `.tausik/config.json` travels with the repo
  and sits in the *project* trust tier (`config_trust.py`); it may only
  **tighten** enforcement, never weaken it. A malicious repo cannot use its
  committed config to disable a gate or lower a severity.
- **Hooks are not repo-carried.** `.claude/` (including `settings.json`, which
  wires the hooks) is **gitignored and generated locally** by `bootstrap` from
  the vendored framework. A freshly cloned project carries no executable hooks;
  the user must run bootstrap to materialize them.

## Threat table

| # | Vector (source) | Applies to TAUSIK? | Status | Mitigation / rationale |
|---|---|---|---|---|
| 1 | **Post-verification swap** (Orca) — pass review, swap the artifact afterward | Partial | **Mitigated at install / accepted for already-installed** | Every `install`/`update` re-fetches and re-runs signature + content scan, so a swapped upstream artifact is caught on next install. Residual: an *already-installed* skill is not re-verified until re-installed. Re-scan-on-activation is a cheap future hardening (deferred, not built). |
| 2 | **Silent overwrite by same name** | Yes (mechanically) | **Mitigated** | `copy_skill` does `rmtree(dst)` then `copytree`, so it *does* overwrite — but only *after* the signature check and content scan pass, and only from an explicitly repo-added, key-pinned source. The overwrite is gated, not silent. |
| 3 | **Invisible-Unicode instructions** (U+E0000 tag block, zero-width, bidi) | Yes — was an open gap | **Mitigated (this task)** | New `skill_content_scan` detector blocks install when SKILL.md or any prose file hides agent-directed text (see below). Signature proves *who*; this proves *what*. |
| 4 | **Scanner-bloat** (Unit 42, 22 MB README to make a scanner skip the file) | Marginal | **Accepted (residual: memory)** | Our content scan has **no skip-large-file escape hatch** — it reads the file fully, so the Unit-42 evasion does not apply. The only residual is memory cost of reading a giant file; a per-file size cap is a cheap follow-up (deferred). |
| 5 | **Install-count gaming** (inflate popularity to earn trust) | No | **Not applicable** | TAUSIK surfaces no popularity/download-count ranking (verified by absence in `skill_catalog`/`skill_repos`). Skills are adopted by explicit `skill repo add` + `skill install`, not by a trending list, so there is no counter to game. |
| 6 | **Repo-supplied hooks execute before consent** (CVE-2025-59536, CVSS 8.7) | Largely no | **Mitigated by design** | See analysis below. |

## CVE-2025-59536 analysis (AC2)

The CVE: hooks defined in a repo-supplied `.claude/settings.json` executed
*before* the consent dialog, so merely opening a cloned repo ran attacker code.
TAUSIK's hook mechanism has the same *shape* (settings.json → hook commands), so
the analogy demands an explicit verdict.

**Verdict: the vector does not apply to a cloned TAUSIK project, by design.**
`.claude/settings.json` is gitignored and is **generated locally** by bootstrap;
it is never carried by the repo. Opening a clone runs no hooks — bootstrap is an
explicit, user-initiated step, which *is* the consent boundary the CVE was
missing. Two residual paths are named and dispositioned rather than left silent:

- **Tampered vendored framework.** If a project vendors a modified framework
  (`.tausik-lib` submodule) and the user runs bootstrap, the generated hooks
  come from that code. This is a framework-integrity problem, not a skill-store
  one; it is bounded by the framework being a pinned dependency the user
  controls, plus the bootstrap-drift gate and signed verification receipts.
  **Status: accepted** (out of this store's boundary).
- **Config redirection.** Even if a repo shipped a crafted `.tausik/config.json`,
  the project tier is untrusted and can only tighten — it cannot point a hook at
  attacker code or weaken a gate. **Status: mitigated** (`config_trust.py`).

**Chosen measure:** document and hold the invariant — keep `.claude/` gitignored,
keep hooks locally generated, keep the project config tier untrusted. No new
consent dialog is warranted because the precondition (repo-carried executable
hooks) does not exist. If a future change ever tracked `.claude/settings.json`,
this verdict flips and a pre-trust consent gate becomes mandatory.

## The implemented mitigation — invisible-Unicode detector (AC4)

`scripts/skill_content_scan.py` detects hidden-instruction Unicode in skill prose,
and the shared guard `assert_skill_tree_clean` — called by **both** `copy_skill`
(install) and `skill_activate` — refuses a skill that contains any:

- **U+E0000–U+E007F** Unicode tag block — the primary 2026 "invisible
  instructions" vector.
- Zero-width formatting (U+200B/C/D, U+2060, and U+FEFF except a leading BOM).
- Bidi overrides / isolates (U+202A–U+202E, U+2066–U+2069; Trojan Source,
  CVE-2021-42574).
- U+00AD soft hyphen.

It scans every prose/config/script file a skill ships — not only `.md` — because
a payload in `references/notes.py` or `data/config.json` reaches the agent just
as surely as one in `SKILL.md` (review s146, C2). Files are decoded with
`errors="replace"`, so a file with a deliberately-invalid byte is still scanned
rather than silently skipped (the fail-open closed in review s146, C3). It
**complements** `brain_scrubbing._ZERO_WIDTH_RE`, which silently *strips* such
characters while matching a brain blocklist: here we *detect and block*, and
additionally cover the U+E0000 tag block the brain regex predates. Covered by
`tests/test_skill_content_scan.py` and `tests/test_skill_activate_supply_chain.py`
(a poisoned skill fails on both the install and the activate path).
