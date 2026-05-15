# TAUSIK promo landing — OD brief

> Skill: `saas-landing` · Design system: `Linear` (или `Vercel` / `Stripe`)
> Output: single long-scroll page, EN copy, dark-by-default, responsive.
> Target domain: **tausik.tech**

---

## 1. Product (one-liner)

**TAUSIK** — AI development framework that adds **enforced quality gates** to coding agents (Claude Code, Cursor, Qwen, Windsurf). Think *Git for AI workflow*: sessions, tasks, decisions, and dead-ends tracked locally; the agent **physically cannot skip** plan or test steps.

## 2. Audience

Developers who already use AI coding agents and have been bitten by silent failures:
- agents that claim "done" without running tests,
- context lost between sessions,
- the same bug fix attempted three times because failed approaches were forgotten,
- linters and type-checks quietly skipped on the path to "looks good."

Not absolute beginners — people who have shipped code with an AI agent and want **discipline** without losing speed.

## 3. Tone of voice

Serious, technical, no marketing fluff. Short sentences. Numbers over adjectives. Confident but specific — every claim backed by a concrete mechanism or metric. Style reference: **Linear**, **Vercel**, **Stripe** docs pages — black/near-black background, restrained accent color, generous whitespace, monospace for code.

Avoid: rocket emoji, "🚀 Supercharge your workflow", vague "10x faster" claims, hand-drawn doodles.

## 4. Hero section

- **H1:** `Git for AI workflow.`
- **Sub-H1 (1 line):** AI development framework — plan, build, ship with quality control. Three messages. Full engineering cycle. Quality gates that the agent can't skip.
- **Primary CTA:** `Get started → ` (anchor to install section)
- **Secondary CTA:** `View on GitHub` → https://github.com/Kibertum/tausik-core
- **Micro-proof row under CTAs:** badges line — `Apache 2.0` · `Python 3.11+` · `3,378 tests passing` · `0 dependencies` · `MCP-native`

Optional hero visual on the right: a terminal/code window showing the three-message demo (`start working` → `fix the bug` → `ship it`) with annotations on the side (`/start opens session`, `/task creates AC`, `/ship runs gates → commits`).

## 5. Section: "Without TAUSIK vs With TAUSIK"

Two-column table, problem on the left, mechanism on the right. Source rows (use verbatim):

| Without TAUSIK | With TAUSIK |
|---|---|
| Agent starts coding immediately | Must define goal + acceptance criteria first (QG-0) |
| Claims "done" without proof | Completion blocked until every criterion has evidence (QG-2) |
| Context lost between sessions | Decisions, patterns, dead ends persist in local SQLite |
| Same mistake repeated 3 times | Failed approaches recorded — agent sees what didn't work |
| No tests, no linting | 25 stack-aware checks auto-run (pytest, ruff, tsc, eslint, cargo, go vet…) |
| No visibility into process | 6 metrics tracked automatically — throughput, defect rate, lead time |

Section subtitle: **"Enforcement, not suggestion. The agent physically can't skip steps."**

## 6. Section: "Three messages. Full engineering cycle."

Three large terminal cards, each showing one message and what the framework does:

1. **`start working`** — Opens session, loads handoff from last session, refreshes CLAUDE.md memory tail.
2. **`fix the bug — button doesn't work on mobile`** — Interviews you on edge cases, creates a task with acceptance criteria, writes the code, runs tests + lint + 5 parallel review agents, verifies each AC has evidence.
3. **`ship it`** — Runs `tausik verify` (cached 10 min), passes QG-2, commits, asks before pushing.

Underneath: *"That's it. You describe what you want. The framework enforces how it gets done."*

## 7. Section: "What you get"

Six-card grid (2×3), each card with an icon, a 2-3 word heading, one sentence:

1. **Quality gates** — QG-0 blocks `task start` without goal+AC. QG-2 blocks `task done` without verify evidence.
2. **Project memory** — SQLite + FTS5 for patterns, gotchas, decisions, dead-ends. Re-injected at session start.
3. **Verify-First** — Heavy tests on a separate `verify` step, cached for 10 minutes; closing a task is millisecond.
4. **19 real-time hooks** — Task gate, bash firewall, push gate, auto-format, memory audits — block bad actions before they happen.
5. **103 MCP tools** — Full programmatic access to the project DB. Works the same in Claude Code, Cursor, Qwen Code, Windsurf.
6. **Cross-project brain** *(optional)* — Notion-mirrored decisions, patterns, gotchas with privacy-preserving project hashes.

## 8. Section: "Quick start — 10 minutes"

Show the install snippet in a fenced code block, fixed-width terminal styling:

```bash
cd your-project
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
echo ".tausik/" >> .gitignore
```

Then a one-line note: *"Restart your IDE — done. Bootstrap auto-detects your stack and enables matching quality gates."*

CTA next to it: `Read the full quick-start →` linking to `docs/en/quickstart.md`.

## 9. Section: "Dogfooding — TAUSIK built TAUSIK"

Four stat cards, large numbers:

- **732** tasks completed
- **73** sessions
- **3,378** tests passing
- **0** core dependencies

Below the numbers, one sentence: *"Every feature, every refactor, every bug fix went through the same quality gates that ship with the framework."*

## 10. Section: "Supported IDEs"

Six small logo tiles + status:

- **VSCode + Claude Extension** — Officially tested
- **Cursor** — Officially tested
- **Claude Code (CLI)** — Expected (partial matrix)
- **Qwen Code** — Expected (partial matrix)
- **Windsurf** — Expected (partial matrix)
- **Codex / OpenCode-style agents** — Expected (manual validation)

Caveat under the grid: *"103 MCP tools and the 12 core skills work everywhere. Real-time hooks live in Claude Code and Qwen Code today; Cursor and Windsurf get the same enforcement at QG-0 and QG-2 task transitions."*

## 11. Section: "Built on SENAR"

One-paragraph attribution: *"TAUSIK implements **SENAR** — an open engineering standard for AI-assisted development. Quality gates, session management, metrics, verification checklists — all defined in SENAR. See [senar.tech](https://senar.tech) for the spec."*

## 12. Footer

- License: Apache 2.0
- GitHub: github.com/Kibertum/tausik-core
- Methodology: senar.tech
- Year-stamp: © 2026

---

## Layout & visual notes

- **Dark mode by default** (#0A0A0A background, #FAFAFA text), single-accent color picked from Linear's palette (electric purple `#5E6AD2`) used sparingly for CTAs and inline emphasis.
- **Typography:** Inter (UI) + JetBrains Mono / IBM Plex Mono (code).
- **No screenshots** of the framework yet — use abstract code cards / terminal-like blocks with annotated lines.
- **Long-scroll**, one page, sticky thin top bar with logo on the left, `Docs` / `GitHub` / `Get started` on the right.
- **Responsive** — collapse the two-column tables on mobile to stacked cards.

## What NOT to include

- No pricing — it's OSS, free, no tiers.
- No testimonials with fake names.
- No "100x developer" copy.
- No big background videos / hero animations — kills load and feels off-brand.
- No "Trusted by" logo wall (we don't have public users to cite yet).

## Versioning

The current public version is **v1.4.0** — near-stable pre-2.0 release. If a "current version" badge is shown anywhere, it must read `v1.4.0`. Numbers in stats (`732 tasks`, `73 sessions`, `3378 tests`) are exact, not "1000+" style approximations.
