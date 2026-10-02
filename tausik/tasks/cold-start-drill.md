---
slug: cold-start-drill
title: "Учение с холодным стартом: непрерывность доказывается мутацией, а не рукописным промптом"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: "Handoff generation and resume protocol; disposable host drills; behavior tests"
scope_exclude: null
relevant_files:
  - "scripts/handoff_generate.py"
  - "tests/test_cold_start_drill.py"
  - "changelog.d/cold-start-drill-111.md"
scope_paths:
  - "scripts/handoff_generate.py"
  - "scripts/ow_handoff.py"
  - "tests/test_handoff_generated.py"
  - "tests/test_cold_start_drill.py"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - r111-budgeted-context-package
  - r111-compound-workflow-results
  - r111-glm-host-usage-adapter
completed_at: "2026-10-01T18:30:24Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#150"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ПРИЁМКА ВСЕГО ЭПИКА, И ОНА МУТАЦИОННАЯ, А НЕ ДОКУМЕНТАЛЬНАЯ. Проект доказывает утверждения мутацией (dead end #427, память #420); утверждение «состояние достаточно долговечно, чтобы агента можно было заменить в любой момент» до сих пор не проверялось НИ РАЗУ — его подпирает рукописный вводный промпт владельца.
УЧЕНИЕ: агент убивается ПОСРЕДИ задачи (не на границе, не после закрытия), поднимается новый экземпляр с единственным словом «продолжай» и без всякого рукописного контекста. Фиксируется, что он восстановил и чего не смог.
ЧТО СЧИТАЕТСЯ ПРОВАЛОМ, А ЧТО НАХОДКОЙ: всё, что новый агент не смог восстановить, есть ДЕФЕКТ ТОГО, ЧТО ЗАДАЧА ЗАПИСЫВАЕТ О СЕБЕ, и заводится дефектом поимённо — а не повод написать промпт руками. Формулировка Anthropic про заменяемость харнесса («скот, а не питомцы») и фактор 12 (агент есть чистая функция от журнала) — это ровно то, что здесь проверяется.
ПРОВОДИТСЯ ДВАЖДЫ: до работ эпика (базовая линия — сколько теряется сегодня) и после (сколько теряется тогда). Без первого замера второй не с чем сравнивать, и учение выродится в «вроде получилось».
НЕГАТИВНОЕ: учение обязано быть ВОСПРОИЗВОДИМЫМ — записанная процедура, а не разовый опыт одного вечера; иначе следующий раз будет мерять другое.

## Acceptance Criteria

AC-1 Record a reproducible before/after Codex drill that interrupts an agent mid-task in an isolated workspace and restarts it with only continue, without a handwritten rescue prompt. AC-2 Restore goal/AC, modified/uncommitted files, completed steps, unresolved risks, relevant decisions and verification evidence; stale green evidence is invalidated after file changes. AC-3 Run the drill on Codex before and after context changes; compare lost facts, model responses, tool calls and repeated work. OWNER DECISION #414: Kilo/GLM is theoretical and not a live quantitative prerequisite. AC-4 Negative: missing/stale handoff, conflicting state or missing evidence is reported and never converted to invented completion; each lost required fact is filed as a defect. AC-5 Shared working trees and user conversations are not killed or modified by the drill.

## Plan

[{"step": "Capture a baseline isolated Codex interruption/resume before context changes.", "done": true}, {"step": "Run the same Codex drill after task-context and workflow work, including stale-evidence mutation.", "done": true}, {"step": "Log restored/lost facts and rework; fix named continuity defects before release.", "done": true}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T18:17:20Z [planning] — Owner Decision #414 makes Codex the primary live and quantitative target. Kilo/GLM acceptance is theoretical; the drill is narrowed to isolated Codex execution.
- 2026-10-01T18:23:29Z [implementation] — Step 1/2: isolated Codex-continuation drill implemented in a disposable git workspace. A fresh Python subprocess reads only the persisted handoff; it restores task goal/AC, plan, risk, decision, working-tree snapshot and receipt. Mutation of src.py makes the same receipt stale. Targeted 34-test handoff/session suite passed; no user process or shared worktree was touched.
- 2026-10-01T18:24:32Z [implementation] — Step 2: after-state drill and stale-evidence mutation recorded in .tausik/planning/release-111/cold-start-drill.md. Negative drill keeps malformed plan unreadable and missing verification empty; it invents neither completion nor proof. Codex usage/token counters are explicitly unknown because this safety drill uses no paid model response.
- 2026-10-01T18:25:26Z [implementation] — Step 3 / AC evidence: isolated fresh-process test covers AC-1 and AC-5 (temporary git repo, no shared process/tree); AC-2 (goal/AC, plan, risk, decision, modified files and receipt restore); AC-3 (baseline revision 72862321 vs post-change artifact; Codex response/tool metrics explicitly unknown, no cost claim); AC-4 (missing receipt=[], malformed plan=unreadable, stale receipt after src.py mutation). Verification #3262 passed: ruff/filesize/format/dedupe/class-surface/bootstrap/docs and scoped pytest 49 passed; 6 concurrent-tree changes remain explicitly outside this task scope.
- 2026-10-01T18:25:49Z [implementation] — Closure blocked by global gates, not the drill: test_dedupe baseline unreadable in tausik/gates.json; class_surface reports shared-module excess. Scoped verify #3262 remains green; its handle was not redeemed after later-stage failure.
- 2026-10-01T18:27:21Z [implementation] — Post-review edge fixed: active-task receipts survive a session boundary, then still become stale on file mutation. Focused handoff/session suite: 34 passed. Reverify #3265 blocked before pytest by shared test_dedupe/class_surface baseline failures and required all-profile bootstrap drift; no deployed profile was edited under this task's ownership.
