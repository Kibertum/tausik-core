**English** | [Русский](README.ru.md)

<p align="center"><img src="docs/assets/tausik-logo.png" width="200" alt="TAUSIK"></p>

# TAUSIK

**AI agents that can't *quietly* fake "done."**

TAUSIK is a discipline layer for AI coding agents. It turns the agent's word — "tests pass," "the task is done" — into something you can actually verify. Plan before code, ship with proof, remember every decision. Not suggestions the agent can ignore: a discipline rail that refuses the easy shortcut and makes the ones it can't refuse visible and recorded — with tamper-evidence against outside edits, not a firewall that claims to stop a determined agent.

[![v1.9.0](https://img.shields.io/badge/version-v1.9.0-blue.svg)](https://github.com/Kibertum/tausik-core/releases)
[![signed receipts: ed25519](https://img.shields.io/badge/signed%20receipts-ed25519-6f42c1.svg)](docs/en/receipts.md)
[![10146 tests](https://img.shields.io/badge/tests-10146-brightgreen.svg)](#proof-tausik-built-tausik)
[![coverage 76%](https://img.shields.io/badge/coverage-76%25-green.svg)](#proof-tausik-built-tausik)
[![0 dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#whats-inside)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://python.org)

---

## Without TAUSIK / With TAUSIK

| Your agent does this | TAUSIK does this |
|---|---|
| Says "I'll just refactor this" and edits 30 files | **No active task → BLOCKED.** No code edits until a task is open. |
| Declares "done" with nothing to show for it | **QG-2 blocks the close.** Every acceptance criterion needs evidence. |
| Reports a green build you have to take on faith | **ed25519 signed receipt.** The green is cryptographically bound to the gate and the commit — an outside edit to the database can't forge or replay it. |
| Tries the same broken approach for the third time | **Project memory.** Failed approaches are recorded; the agent sees what didn't work. |
| Quietly skips the test/lint pipeline | **Separate `verify` step.** Heavy gates run on their own trigger and get cached — skipping is visible, not silent. |

The difference is one word: **evidence.**

---

## The 30-second try

Tell your agent:

```
Add https://github.com/Kibertum/tausik-core as a git submodule in .tausik-lib,
run python .tausik-lib/bootstrap/bootstrap.py --init,
add .tausik/ to .gitignore
```

It runs all three steps. Restart your IDE so the MCP servers load — done. Now drive the whole engineering cycle with three messages:

```
start working
```
```
fix the bug — button doesn't work on mobile
```
```
ship it
```

The agent opens a session, writes a task with acceptance criteria, codes, runs tests and review, verifies each criterion against evidence, commits, and offers to push. You described what you wanted; the framework forced the steps you skip when you trust the agent too much.

---

## Verifiable trust

This is what makes TAUSIK different from every prompt-based ruleset.

- **`tausik verify` emits an ed25519-signed receipt** (`tausik-signed/v1`) bound to the exact gate signature and the HEAD commit sha.
- **`task done` validates that receipt before it lets the task close.** A green that wasn't actually produced — or was produced for a different commit — fails the check.
- **Receipts are portable.** Export one and verify it offline with no SDK, via a stateless HTTP endpoint or the no-SDK example.
- **Skill and stack releases are signed too** — installs verify the signature before writing anything to disk.

**What this means for you:** when an agent tells you the build is green, you don't have to believe it. You have a signed receipt that proves it — or proves it lied.

**[How signed receipts work →](docs/en/receipts.md)**

---

## How it works

**Plan before code.** `/plan` opens with an interview — the agent asks about behavior, edge cases, and constraints, then writes tasks with acceptance criteria. No code until "done" is defined.

**Ship with proof.** `/ship` runs parallel code review, tests, verifies every criterion against evidence, commits, and offers to push — one command, full pipeline, signed receipt at the end.

**Remember everything.** Decisions, patterns, conventions, and dead ends live in a local SQLite + FTS5 database and are re-injected at session start. New session, same context — no re-explaining the project.

**Discipline, not suggestion.** Two quality gates and a set of real-time hooks refuse the common shortcuts (no code without a task, no close without evidence) and make the ones they can't refuse visible and recorded. No `--force`, no "please remember to test." The threat model is silent drift by an honest agent, not a determined one working around the rail.

---

## The two gates

**QG-0 — before work starts.** No goal, no acceptance criteria → the task can't start.

```
$ tausik task start fix-mobile-button
BLOCKED (QG-0): task has no acceptance criteria.
Define what "done" means before writing code.
```

**QG-2 — before the task closes.** No verify evidence → the task can't be marked done.

```
$ tausik task done fix-mobile-button --ac-verified
BLOCKED (QG-2): no valid verification receipt for HEAD a1b2c3d.
Run `tausik verify --task fix-mobile-button` first.
```

Both are fail-closed: a gate that can't evaluate blocks rather than waves the task through.

---

## Proof: TAUSIK built TAUSIK

TAUSIK was built with TAUSIK — every feature, refactor, and bug fix went through the gates that ship in the box. Not as a vanity metric, as the strongest test of the contract:

- **Every task closed with a goal + acceptance criteria.** Zero closed without verify evidence.
- **10146 tests** — the discipline core is the most-tested part.
- **76% line coverage** (baseline, `scripts/`, 4124 selected tests) — refresh with `pytest tests/ --cov=scripts --cov-report=json:coverage.json` and update the badge; CI uploads `coverage.json` as a build artifact on every PR.
- **0 core dependencies** — Python 3.11+ stdlib only; MCP deps live in an isolated `.tausik/venv/`.
- **0 phone-home calls** — everything runs and stays on your machine.

---

## Why not .cursorrules / AGENTS.md?

Those are **suggestions** — text the agent reads and is free to ignore the moment it's inconvenient. TAUSIK is **hard blocks**: hooks intercept edits, gates refuse to close, receipts prove the green. The rulebook becomes a rail.

---

## What's inside

- **Lifecycle & gates** — Epic → Story → Task with a state machine; QG-0 at start, QG-2 at close, both fail-closed.
- **Verifiable trust** — ed25519 signed verification receipts, offline-checkable, with supply-chain signing for skills and stacks.
- **Project memory** — SQLite + FTS5 store of decisions, patterns, conventions and dead ends, re-injected every session.
- **A shared knowledge base** — one file per person, not per project. `--global` puts a pattern or a dead end where the NEXT project will find it; search reads both stores. It never leaves this machine, and it has a backup that stays here too. **[How it differs from project memory →](docs/en/knowledge-store.md)**
- **Real-time discipline rails** — hooks for the no-code-without-a-task gate, a bash firewall, a single-use push ticket, and auto-format.
- **Metrics & routing** — throughput, first-pass success, defect-escape and lead-time tracked automatically; per-task cost/token budgets; complexity-aware model routing across vendor families (Claude and [z.ai GLM](docs/en/kilo-zai.md), data-driven, no code change).

<details>
<summary>Raw counts</summary>

- **146 MCP tools** — full programmatic access to the project database.
- **22 real-time hooks** — task gate, bash firewall, push gate, auto-format, drift detection, memory pre/post audit, and more.
- **25 stack-aware verify suites** — pytest, ruff, mypy, tsc, eslint, cargo, go vet, phpstan, helm-lint, hadolint, and others, scoped to the files you touched.
- **13 core skills** auto-deployed; 20 official skills opt-in via `bootstrap --include-official` or `tausik skill install <name>`.
- **6 automatic metrics**, **a shared local knowledge store** (`~/.tausik-knowledge`, `--global`), **batch execution** (`/run plan.md`).

</details>

---

## Supported IDEs

Multi-IDE by design, but we're honest about what's validated end-to-end.

| IDE | MCP tools | Skills | Hooks | Status |
|---|---|---|---|---|
| **Claude Code** | 146 | 13 core + opt-in | 22 (full) | First-class |
| **Qwen Code** | 146 | 13 core + opt-in | 22 (parity with Claude) | First-class |
| **Kilo Code** (+ [z.ai GLM](docs/en/kilo-zai.md)) | 146 | 13 core + opt-in | — (gates at task start/done) | First-class via MCP |
| **Cursor** | 146 | 13 core + opt-in | — (gates at task start/done) | Supported via MCP |
| VSCode + Claude Extension | 146 | 13 core + opt-in | 22 | Tested E2E |
| **Codex CLI** | 146 | 13 core + opt-in | 22 (same declaration as Claude; enforce once you trust the project hooks in Codex) | First-class, live-verified in 1.9 |
| **OpenCode** | 146 | 13 core + opt-in | — (one QG-0 plugin; gates at task start/done) | Supported via MCP |
| Windsurf | MCP + rules | host-dependent | host-specific | Expected / manual |

Hooks — the real-time rails (no code without a task, bash firewall, push gate) — run in **Claude Code, Qwen Code and Codex** (Codex runs a project's hooks only after you trust them; an untrusted profile enforces nothing — see the [Codex enforcement matrix](docs/en/model-providers.md#codex-enforcement-matrix)). Kilo, Cursor, OpenCode, Windsurf and other MCP hosts get the same 146 tools and skills, with quality gates applied at `task start` and `task done`.

**Kilo Code + z.ai (GLM):** bootstrap with `--ide kilo` and TAUSIK runs as a first-class MCP host driven by GLM models — model routing recommends within the active model's family (a `glm-*` session gets GLM verdicts), all as data, no code change. See **[Kilo + z.ai →](docs/en/kilo-zai.md)**.

---

## Install

```bash
cd your-project
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
```

Bootstrap auto-detects your stack and enables matching gates; the project name comes from the directory. Restart your IDE afterward so the MCP servers load. Target a specific host with `--ide claude|cursor|qwen|kilo|opencode|codex` (or `--ide all`; e.g. `--ide kilo` for [Kilo Code + z.ai GLM](docs/en/kilo-zai.md), `--ide codex` for Codex CLI).

**[Full quick-start guide →](docs/en/quickstart.md)** · **[Agent quickstart →](docs/en/agent-quickstart.md)** (for the AI agent: connect on its host, then the cycle as exact calls)

---

## Methodology

TAUSIK is the reference implementation of [SENAR v1.3 Core](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open engineering standard for AI-assisted development. The gates, sessions, metrics and verification checklists all come from the spec; you don't have to read it to use the framework.

**TAUSIK claims SENAR v1.3 Core** — that edition and no other. Later editions are in preparation and are not claimed here or anywhere else in the project — a conformance claim to a standard that is still moving is exactly the kind of statement this framework exists to refuse. Every place that names the edition is checked against one constant by `tests/test_senar_version_claim.py`.

**[More about SENAR →](docs/en/senar.md)**

---

## v1.9 — the release that stopped taking its own word for things

1.8 answered "does the framework enforce discipline". 1.9 makes two statements
about the product and requires each to be measured. One of them is not measured
yet, and this page says so rather than leaving it to be discovered.

**The artifact graph became framework machinery, not a table in our database.**
`tausik graph` answers what to read in order to change a file, and what a change
will break — from three kinds of evidence kept apart: what git saw change
together, what a task declared, and what a test run actually reached. Roots are
asked of the PROJECT rather than assumed from our own layout, so a consumer
project is indexed as itself. Measured: an unranked neighbour list costs 2,881 KB
to read; the ranked answer costs 927 bytes.
**[The graph →](docs/en/graph.md)**

**Evidence stopped being a claim about itself.** A gate now declares WHICH
CHANGE does not happen while its verdict is negative, and every blocking gate
has a test that hands it a violation and requires red. A test never observed
failing has not shown it can fail, and that history is now recorded. A receipt
says WHO ran the verification, so separation of duties is a checkable property
rather than a sentence in the documentation — and the first thing it showed is
that on the verify path there is no separation: across 29 tasks recording both a
starting and a closing model, none differ.

**A quantity that cannot be obtained is ABSENT, not nought.** That sounds like a
nicety until you look at the numbers: the telemetry asserted 55,471 times that
work had cost $0.00, and model pinning had never fired in 231 sessions. Both
defects looked exactly like "a feature nobody needs".

**The token-saving figure is MEASURED ONCE, and on this pair there is no saving.**
Telemetry produces no figure (of 57,251 rows, 233 carry input tokens; no
"without TAUSIK" baseline exists); the figure came from a paired replay on a
fixed corpus ([protocol §7, in
Russian](docs/ru/research/rag-nudge-replay-protocol.md)): with the rag-first
nudges 198,848 against 195,055 tokens (+1.9%), 326,323 against 292,715 bytes of
exploration results (+11.5%), and `search_code` never called with or without
them. One reading on one corpus — that alone is published as fact.

**[What changed in 1.9 →](docs/en/whats-new-1.9.md)**
([Русский](docs/ru/whats-new-1.9.md)) — including the breaking changes and their
migrations. Earlier releases: **[1.8 →](docs/en/whats-new-1.8.md)**.

v1.9 continues the hardening on the road to 2.0: signed receipts, fail-closed
gates, external adversarial review for under-evidenced closures, closure-risk
scoring, structured root cause, and a skill supply chain that verifies the same
way on every platform.

A theme runs through this release's fixes, and it is worth stating plainly: a
mechanism that works and that nothing calls is indistinguishable from one that
does not work. The graph was built and held zero rows. A schema table added by
migration alone was missing from every fresh install, and failed silently. A
detector for invented closure citations existed and nobody ran it. All three now
have a caller and a test that goes red without one. What the rail proves is
bounded on purpose — tamper-evidence against outside edits, not attestation
against the agent that holds the key ([receipts](docs/en/receipts.md)). On
uncommon paths you may still hit doc-vs-behavior drift — if you do,
[file an issue](https://github.com/Kibertum/tausik-core/issues) and we'll
converge it before 2.0.

## License

[Apache License 2.0](LICENSE)
