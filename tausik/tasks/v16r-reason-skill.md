---
slug: v16r-reason-skill
title: "[P1] /reason skill + интеграция с /task"
status: done
epic: v16-renar-core
story: v16r-trace
complexity: medium
role: developer
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: "harness/skills/reason/SKILL.md (new); harness/skills/task/SKILL.md (nudge); docs/en/reasoning-trace.md + docs/ru/reasoning-trace.md (new); docs/{en,ru}/skills.md (index link). Re-bootstrap regenerates .claude/.cursor/.qwen mirrors."
scope_exclude: "No Python/scripts/harness-code changes (reasoning_steps backend already shipped in #83). Do NOT edit .claude/.cursor/.qwen by hand. No new MCP tools. No .pen files."
relevant_files:
  - "harness/skills/reason/SKILL.md"
  - "harness/skills/task/SKILL.md"
  - "docs/en/reasoning-trace.md"
  - "docs/ru/reasoning-trace.md"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T15:30:14Z"
---

## Goal

Skill /reason поверх reasoning_steps: агент ведёт intent→premise→action→verification цикл; /task предлагает reason-шаги на ключевых развилках (эскалирующий nudge, не hard). AC: SKILL.md (на английском — feedback memory); связка с task log; пример полного trace в docs.

## Acceptance Criteria

1. harness/skills/reason/SKILL.md exists (English frontmatter+body, valid frontmatter — bootstrap validation clean) documenting the intent→premise→action→verification cycle via `tausik reason-step` / MCP `tausik_reason_step`. 2. /task SKILL.md gains an ESCALATING SOFT nudge to record reason-steps at key forks. NEGATIVE SCENARIO: a task with zero reasoning_steps must still close normally via task done — the nudge is advisory, never blocking. 3. docs/en/reasoning-trace.md + docs/ru parity contain a full worked trace (all 4 kinds) and are linked from the skills doc index. 4. Re-bootstrap regenerates reason skill into .claude/.cursor/.qwen; mirror tests green; gen_doc_constants --check green.

## Plan

[{"step": "Author harness/skills/reason/SKILL.md (EN) \u2014 intent\u2192premise\u2192action\u2192verification cycle, tausik reason-step / MCP tausik_reason_step, link to task log", "done": true}, {"step": "Add escalating SOFT nudge to harness/skills/task/SKILL.md at key forks (advisory, never blocking)", "done": true}, {"step": "Write docs/en/reasoning-trace.md with a full worked 4-kind trace example; mirror docs/ru/reasoning-trace.md; link from docs/{en,ru}/skills.md", "done": true}, {"step": "Re-bootstrap; run mirror tests + gen_doc_constants --check + ruff/mypy", "done": true}, {"step": "Review (tausik-reviewer on diff) + verify via CLI (drift after bootstrap) + task done", "done": true}]

## Rollback

git revert the doc/skill commit (pure additive harness+docs); re-run bootstrap to drop the regenerated reason skill from mirrors. No DB migration, no code, so revert is clean.

## Journal

- 2026-06-13T15:18:57Z [implementation] — Step 1: authored harness/skills/reason/SKILL.md (EN, context=inline/effort=fast). Documents the 4-kind cycle, MCP tausik_reason_step + CLI positional reason-step, reason vs log vs decide table, append-only/advisory rules. Verified CLI arg shape against project_parser_task.py (positional slug/kind/content).
- 2026-06-13T15:19:25Z [implementation] — Step 2: added escalating SOFT nudge to /task step 6 (light→firm across untraced forks, explicitly never a gate; zero-trace tasks still close) + tausik_reason_step row in MCP-first table. No task_done/QG-2 logic touched (negative scenario preserved).
- 2026-06-13T15:21:31Z [implementation] — Step 3: wrote docs/en/reasoning-trace.md + docs/ru/reasoning-trace.md (full 4-kind worked trace + reason/log/decide table + guarantees). Linked from docs/{en,ru}/skills.md Knowledge table; bumped core-skill count 12→13 prose. skills_core_count constant will go 12→13 — needs gen_doc_constants regen next.
- 2026-06-13T15:23:12Z [implementation] — Step 4: regen constants (skills_core 12→13, test_count 3844→3846), re-bootstrap (14 skills copied, reason in .claude/.cursor/.qwen + catalog), bumped README/README.ru test badges 3844→3846. gen_doc_constants --check GREEN, ruff GREEN, pytest -k mirror/bootstrap/frontmatter/skill = 203 passed.
- 2026-06-13T15:30:01Z [implementation] — Step 5: tausik-reviewer ran on diff — 3 high/3 med/1 low, all addressed: replay→marked planned (en/ru/skill), task_show CLI-vs-MCP clarified, added reason-step to cli.md + tausik_reason_step to mcp.md (en/ru) so See-also links resolve, skill-ecosystem 12→13 (en/ru), ru lang-switch /en/docs→/docs. Low backslash-pipe kept (required in md table). Skill desc shortened to 51 chars (≤60 gate). Re-bootstrap (14 skills), constants --check GREEN, full skill/doc/mirror suite 439 passed/1 skip, CLI verify PASS (receipt #717).
- 2026-06-13T15:30:13Z [implementation] — AC1: harness/skills/reason/SKILL.md EN, frontmatter valid (context=inline/effort=fast), documents intent->premise->action->verification cycle + CLI/MCP surfaces; bootstrap frontmatter validation + skill-desc-length gate GREEN. AC2: /task step-6 nudge is advisory+escalating, explicitly 'never a gate'; QG-2/task_done logic untouched. NEGATIVE SCENARIO PROVEN: this very task has ZERO reasoning_steps yet closes normally. AC3: docs/en+ru/reasoning-trace.md carry a full 4-kind worked trace + render output; linked from skills.md; cli.md/mcp.md document the surface. AC4: re-bootstrap copied reason into .claude/.cursor/.qwen (14 skills) + catalog; mirror+frontmatter+doc suite 439 passed; gen_doc_constants --check GREEN (skills_core 12->13, test_count 3844->3846); CLI verify PASS receipt #717.
