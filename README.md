**English** | [Русский](README.ru.md)

<p align="center"><img src="docs/assets/tausik-logo.png" width="200" alt="TAUSIK"></p>

# TAUSIK

**AI coding agents that can't *quietly* fake "done."**

TAUSIK sits on top of the AI coding agent you already use — Claude Code, Cursor, Codex and others — and checks its work. The agent must open a task with a definition of "done" before it edits code, and must show passing checks before it closes the task. Every decision and every failed approach is remembered for the next session. For developers who don't want to take "tests pass" on faith.

**Where it sits.** The field calls this discipline *harness engineering*: a harness is the agent loop, the tool interface, context management and control mechanisms. TAUSIK is not a harness — the loop and the tools belong to Claude Code, Cursor, Codex and the rest. It is the verification and control layer on top of them: what makes it different is that nothing counts as done without evidence.

[![v1.11.2](https://img.shields.io/badge/version-v1.11.2-blue.svg)](https://github.com/Kibertum/tausik-core/releases)
[![signed receipts: ed25519](https://img.shields.io/badge/signed%20receipts-ed25519-6f42c1.svg)](docs/en/receipts.md)
[![13064 tests](https://img.shields.io/badge/tests-13064-brightgreen.svg)](#proof-tausik-built-tausik)
[![coverage 76%](https://img.shields.io/badge/coverage-76%25-green.svg)](#proof-tausik-built-tausik)
[![0 dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#whats-inside)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://python.org)

---

## See it catch a lie

This is real output of `tausik demo` (about 10 seconds, no network, no LLM key, run in a throwaway sandbox):

```
== The agent says "tests pass" without running them, and tries to close.
   Error: QG-2 Implementation Gate failed: verify-first — QG-2: task 'fix-add' declares no relevant_files, so no verify run can certify it...

== The real check runs. The claim was false.
   FAILED tests/test_calc.py::test_add - assert 0 == 4
   1 failed in 0.09s
   Receipt: signed (run #2, key bacfee7a6aef38ea).

== The agent actually fixes the bug. Now the close goes through, with a receipt.
   Receipt: signed (run #3, key bacfee7a6aef38ea).
   Task 'fix-add' completed.
```

Run it yourself after installing: `.tausik/tausik demo`.

## Install

You need Python 3.11+ and git. Bootstrap sets up Claude Code by default; for another host add `--ide claude|cursor|qwen|kilo|opencode|codex` (or `--ide all`) to the second command. Running it again later with another `--ide` is safe. In your project:

```bash
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
echo ".tausik/" >> .gitignore
```

Then **restart your IDE**. The IDE talks to TAUSIK through MCP (Model Context Protocol, the standard way an AI agent calls outside tools), and it picks up new MCP servers only at start.

Bootstrap detects your stack and turns on the matching checks.

## Check it worked

```bash
.tausik/tausik status          # macOS, Linux, Git Bash
.tausik\tausik.cmd status      # Windows cmd or PowerShell
```

You should see `Tasks: 0/0 done`. If the command is not found, bootstrap did not finish — run it again and read its last lines.

## Your first task

Say these three things to your agent:

```
start working
```
```
fix the bug — button doesn't work on mobile
```
```
ship it
```

The agent opens a session, writes a task with acceptance criteria (the checklist that defines "done"), makes the change, runs your tests and a review, checks every criterion, and commits. You describe the outcome; TAUSIK makes the agent do the steps it would otherwise skip.

**[Full quick-start guide →](docs/en/quickstart.md)** · **[Agent quickstart →](docs/en/agent-quickstart.md)** (written for the AI agent itself)

---

## What changes for you

| Your agent does this | TAUSIK does this |
|---|---|
| Says "I'll just refactor this" and edits 30 files | **Blocked.** No code edits until a task is open. |
| Declares "done" with nothing to show for it | **Blocked.** The task can't close until each acceptance criterion has evidence. |
| Reports a green build you have to take on faith | **Signed receipt.** The passing result is signed and tied to the exact commit, so it can't be copied from an older run or edited afterwards. |
| Tries the same broken approach for the third time | **Project memory.** Failed approaches are recorded; the agent sees what didn't work. |
| Quietly skips the tests | **A separate check step.** Skipping it is visible, not silent. |

The difference is one word: **evidence.**

## The two checkpoints

**Before work starts:** no goal or no acceptance criteria → the task can't start.

```
$ .tausik/tausik task start fix-mobile-button
BLOCKED (QG-0): task has no acceptance criteria.
Define what "done" means before writing code.
```

**Before the task closes:** no passing check for the current commit → the task can't close.

```
$ .tausik/tausik task done fix-mobile-button --ac-verified
BLOCKED (QG-2): no valid verification receipt for HEAD a1b2c3d.
Run `tausik verify --task fix-mobile-button` first.
```

The messages call them QG-0 and QG-2 (quality gates). If a checkpoint can't decide, it blocks rather than lets the task through.

**What this does not promise.** TAUSIK stops an honest agent from drifting. It is not a sandbox against an agent that deliberately works around it; it makes such attempts visible and recorded instead. It does not promise to save tokens either: the one measurement (in 1.9) found no saving on this pair (the same tasks run with and without the feature being measured) — 198,848 against 195,055 tokens (+1.9%), 326,323 against 292,715 bytes read while exploring (+11.5%), and the code-search tool (`search_code`) was never called. The full list is in **[Known limitations →](docs/en/known-limitations.md)**.

## Signed receipts

`tausik verify` runs your checks and signs the result with an ed25519 key, tied to the commit. `task done` checks that signature before it closes the task. You can check a receipt offline with `tausik receipt verify <file>`; pass the project's public key (`--pub`) to also prove who issued it.

**[How signed receipts work →](docs/en/receipts.md)**

## Why not .cursorrules / AGENTS.md?

Those are **suggestions** — text the agent reads and can ignore when it's inconvenient. TAUSIK **blocks**: hooks (scripts your IDE runs before each agent action) refuse edits without a task, the close refuses without evidence, and receipts prove the result.

---

## What's inside

- **Tasks with a lifecycle** — Epic → Story → Task; a task can't start without a definition of done or close without evidence.
- **Signed receipts** — checkable offline; skill and stack releases are signed too.
- **Project memory** — decisions, patterns, conventions and dead ends in a local SQLite database, loaded into every new session.
- **A shared knowledge base** — one per person, across projects, on your machine only. **[How it differs from project memory →](docs/en/knowledge-store.md)**
- **Hooks** — no code without a task, a guard on risky shell commands, a one-time ticket for each push, auto-format.
- **Metrics and model routing** — throughput, first-pass success, cost per task; recommends a cheaper model for simple tasks (Claude, [z.ai GLM](docs/en/kilo-zai.md)).

<details>
<summary>Raw counts</summary>

- **147 MCP tools** — full programmatic access to the project database.
- **23 real-time hooks** — task gate, bash firewall, push gate, auto-format, drift detection, memory pre/post audit, and more.
- **25 stack-aware verify suites** — pytest, ruff, mypy, tsc, eslint, cargo, go vet, phpstan, helm-lint, hadolint, and others, scoped to the files you touched.
- **13 core skills** auto-deployed; the official store has only `docs`, `excel`, and `pdf`, installed one at a time so unused instructions add no prompt cost.
- **6 automatic metrics**, **a shared local knowledge store** (`~/.tausik-knowledge`, `--global`), **batch execution** (`/run plan.md`).

</details>

## Supported IDEs

| IDE | MCP tools | Skills | Hooks | Status |
|---|---|---|---|---|
| **Claude Code** | 147 | 13 core + opt-in | 23 (full) | First-class |
| **Qwen Code** | 147 | 13 core + opt-in | 23 (parity with Claude) | First-class |
| **Kilo Code** (+ [z.ai GLM](docs/en/kilo-zai.md)) | 147 | 13 core + opt-in | — (gates at task start/done) | First-class via MCP |
| **Cursor** | 147 | 13 core + opt-in | — (gates at task start/done) | Supported via MCP |
| VSCode + Claude Extension | 147 | 13 core + opt-in | 23 | Tested E2E |
| **Codex CLI** | 147 | 13 core + opt-in | 23 (same declaration as Claude; enforce once you trust the project hooks in Codex) | First-class, live-verified in 1.9 |
| **OpenCode** | 147 | 13 core + opt-in | — (one QG-0 plugin; gates at task start/done) | Supported via MCP |
| Windsurf | MCP + rules | host-dependent | host-specific | Expected / manual |

Hooks run in **Claude Code, Qwen Code and Codex** (Codex runs them only after you trust the project — see the [Codex enforcement matrix](docs/en/model-providers.md#codex-enforcement-matrix)). Other hosts get the same tools and skills, with the checkpoints applied at `task start` and `task done`.

---

## Proof: TAUSIK built TAUSIK

Every feature and fix of TAUSIK went through the same checkpoints that ship in the box.

- **Every task closed with a goal and acceptance criteria**, none without a passing check.
- **13064 tests**; **76% line coverage** of `scripts/` (refresh with `pytest tests/ --cov=scripts --cov-report=json:coverage.json`).
- **0 core dependencies** — Python 3.11+ standard library; MCP packages live in an isolated `.tausik/venv/`.
- **One disclosed update endpoint** — every session-start attempt sends an anonymous GET to `api.github.com/repos/Kibertum/tausik-core/releases/latest`; a newer release blocks the start. The request contains no project name, path, user, schema or installed version. `"updates": {"check": false}` in `.tausik/config.json` sends no request and allows start with an explicit unverified-version warning. The standalone cached check remains at most daily.

## The standard behind it

TAUSIK conforms to SENAR v1.5 Core, self-declared, as of 2026-09-23. [SENAR](https://senar.tech) is an open engineering standard for AI-assisted development; you don't need to read it to use TAUSIK. The disclosure the standard requires with that claim: No SHALL is handled under §13.5, and no SHOULD of the claimed scope is unimplemented. **[TAUSIK and SENAR →](docs/en/senar.md)** · **[Compliance matrix →](docs/en/senar-compliance-matrix.md)**

## What's new

**[What changed in 1.11 →](docs/en/whats-new-1.11.md)**, including measured gains and their honest limits. Earlier: **[1.10 →](docs/en/whats-new-1.10.md)**, **[1.9 →](docs/en/whats-new-1.9.md)**, **[1.8 →](docs/en/whats-new-1.8.md)**. Found a mismatch between the docs and behavior? [File an issue](https://github.com/Kibertum/tausik-core/issues).

## License

[Apache License 2.0](LICENSE)
