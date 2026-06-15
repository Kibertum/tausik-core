**English** | [Русский](README.ru.md)

# TAUSIK

**AI agents that can't fake "done."**

TAUSIK is a discipline layer for AI coding agents. It turns the agent's word — "tests pass," "the task is done" — into something you can actually verify. Plan before code, ship with proof, remember every decision. Not suggestions the agent can ignore: hard gates it physically cannot skip.

[![signed receipts: ed25519](https://img.shields.io/badge/signed%20receipts-ed25519-6f42c1.svg)](docs/en/receipts.md)
[![4348 tests](https://img.shields.io/badge/tests-4348-brightgreen.svg)](#proof-tausik-built-tausik)
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
| Reports a green build you have to take on faith | **ed25519 signed receipt.** The green is cryptographically bound to the gate and the commit — it can't be forged or replayed. |
| Tries the same broken approach for the third time | **Project memory.** Failed approaches are recorded; the agent sees what didn't work. |
| Quietly skips the test/lint pipeline | **Separate `verify` step.** Heavy gates run on their own trigger and get cached — skipping is visible, not silent. |

The difference is one word: **enforcement.**

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

**Enforce, not suggest.** Two quality gates and a set of real-time hooks block the agent the moment it tries to cut a corner. No `--force`, no "please remember to test."

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
- **4348 tests** — the enforcement core is the most-tested part.
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
- **Real-time enforcement** — hooks for the no-code-without-a-task gate, a bash firewall, a single-use push ticket, and auto-format.
- **Metrics & routing** — throughput, first-pass success, defect-escape and lead-time tracked automatically; per-task cost/token budgets; complexity-aware model routing.

<details>
<summary>Raw counts</summary>

- **124 MCP tools** (117 project + 7 brain) — full programmatic access to the project database.
- **21 real-time hooks** — task gate, bash firewall, push gate, auto-format, drift detection, memory pre/post audit, and more.
- **25 stack-aware verify suites** — pytest, ruff, mypy, tsc, eslint, cargo, go vet, phpstan, helm-lint, hadolint, and others, scoped to the files you touched.
- **13 core skills** auto-deployed (+ `/brain` once configured); 20 official skills opt-in via `bootstrap --include-official` or `tausik skill install <name>`.
- **6 automatic metrics**, **cross-project shared brain** (optional, Notion-mirrored), **batch execution** (`/run plan.md`).

</details>

---

## Supported IDEs

Multi-IDE by design, but we're honest about what's validated end-to-end.

| IDE | MCP tools | Skills | Hooks | Status |
|---|---|---|---|---|
| **Claude Code** | 124 | 13 core + opt-in | 21 (full) | First-class |
| **Qwen Code** | 124 | 13 core + opt-in | 21 (parity with Claude) | First-class |
| **Cursor** | 124 | 13 core + opt-in | — (gates at task start/done) | Supported via MCP |
| VSCode + Claude Extension | 124 | 13 core + opt-in | 21 | Tested E2E |
| Windsurf / Codex-style | MCP + rules | host-dependent | host-specific | Expected / manual |

Hooks — the real-time rails (no code without a task, bash firewall, push gate) — run in **Claude Code and Qwen Code**. Cursor, Windsurf and other MCP hosts get the same 124 tools and skills, with quality gates enforced at `task start` and `task done`.

---

## Install

```bash
cd your-project
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
```

Bootstrap auto-detects your stack and enables matching gates; the project name comes from the directory. Restart your IDE afterward so the MCP servers load.

**[Full quick-start guide →](docs/en/quickstart.md)**

---

## Methodology

TAUSIK is the reference implementation of [SENAR](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open engineering standard for AI-assisted development. The gates, sessions, metrics and verification checklists all come from the spec; you don't have to read it to use the framework.

**[More about SENAR →](docs/en/senar.md)**

---

## v1.5 — pre-2.0, and confident about it

v1.5 is a hardening release on the road to 2.0: signed receipts, fail-closed gates, external adversarial review for high-risk closures, closure-risk scoring, structured root cause. The enforcement core is **locked and covered by 4348 tests**, dogfooded daily. On uncommon paths you may still hit doc-vs-behavior drift — if you do, [file an issue](https://github.com/Kibertum/tausik-core/issues) and we'll converge it before 2.0.

## License

[Apache License 2.0](LICENSE)
