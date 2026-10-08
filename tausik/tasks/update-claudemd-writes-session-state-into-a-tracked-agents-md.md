---
slug: update-claudemd-writes-session-state-into-a-tracked-agents-md
title: "GitLab #14: update-claudemd пишет DYNAMIC-блок (сессия, ветка, хвост памяти, чужие знания) в версионируемый AGENTS.md безусловно — грязное дерево и предупреждение, которое нечем снять"
status: done
epic: release-19-renar-conformance
story: release19-tracker-promises
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/claudemd_writer.py, scripts/project_config.py, tests/, docs/en/configuration.md, docs/ru/configuration.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files:
  - "scripts/claudemd_writer.py"
  - "scripts/claudemd_state.py"
  - "scripts/gate_claudemd_state.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/project_cli_extra.py"
  - "harness/claude/mcp/project/handlers_skill.py"
  - "tests/test_sibling_dynamic_block.py"
  - "tests/test_update_claudemd_agents.py"
  - "tests/test_claudemd_state_gate.py"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths:
  - "scripts/*.py"
  - "harness/**"
  - "tests/*.py"
  - "docs/en/*.md"
  - "docs/ru/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-13T16:34:38Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "gitlab#14"
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

Тикет GitLab #14 (владелец, kibertum-org на 1.8.0): claudemd_writer.resolve_sibling_targets добавляет AGENTS.md к целям DYNAMIC-записи, если он существует; в проекте, где CLAUDE.md сознательно выведен из-под git ради автообновления, AGENTS.md остаётся версионируемым — и туда каждую сессию попадают номер сессии, ветка, счётчики, хвост памяти и «Shared knowledge — from other projects». Следствия: `M AGENTS.md` после одного /start; WARN «undeclared: AGENTS.md» в каждой квитанции verify, который нельзя снять честно; история либо засоряется, либо расходится; знание чужих проектов уезжает в историю репозитория. Тикет предлагает три варианта (писать DYNAMIC только в первичный файл; ручка `claudemd.sibling_dynamic: false`; писать в сиблинг только то, что осмысленно в свежем клоне). Это выбор поведения, а не правка одной строки — решение #366 выносит его в 1.10. Задача: принять вариант (рекомендация — ручка с умолчанием «как сейчас» ПЛЮС усечённый блок в сиблинге без чужих знаний), реализовать, покрыть тестами обе ветки ручки и мутацией «ручка игнорируется», задокументировать в configuration.md EN/RU, ответить в тикете.

## Acceptance Criteria

AC-1: the behaviour is chosen and recorded by decision: knob claudemd.sibling_dynamic (default true) — the AGENTS.md sibling keeps receiving the DYNAMIC block, but TRIMMED: without 'Shared knowledge — from other projects'; existing projects do not break. AC-2: with the knob false AGENTS.md receives no DYNAMIC block and is not touched; with it true the sibling is refreshed; both paths tested on a temporary project through the CLI and the MCP handler. AC-3 (negative): the shared-knowledge section is never written into the sibling at any knob value — a project whose only knowledge is shared yields a sibling block with no memory tail at all, and the claudemd_state gate does NOT flag that sibling as drift (it judges the sibling against the trimmed expectation). AC-4 (negative, mutation): a writer that reads the knob but ignores it (writes the full block to the sibling, or writes with the knob false) is caught by the tests — an error, not a silent pass. AC-5: docs/{en,ru}/configuration.md describe the knob; CHANGELOG EN/RU; the reply in GitLab #14 is prepared for the owner. AC-6: signed verify.

## Plan

## Rollback

git revert; ручка исчезает, сиблинг снова получает полный блок.

## Journal

- 2026-09-13T16:34:35Z [implementation] — AC-1 ✓ behaviour recorded by decision #370 and implemented: knob claudemd.sibling_dynamic (claudemd_writer.SIBLING_DYNAMIC_KEY, default true — the sibling keeps being refreshed, TRIMMED of 'Shared knowledge — from other projects'); existing projects keep the refresh; tests/test_sibling_dynamic_block.py::TestTheKnob::test_default_refreshes_the_sibling[cli] and [mcp]. AC-2 ✓ ::TestTheKnob::test_false_leaves_the_sibling_untouched[cli] and [mcp] (AGENTS.md byte-identical, CLAUDE.md refreshed); ::test_the_knob_is_read_from_this_projects_config; the knob is read from the .tausik/ beside the file being written — ::TestForeignKnowledgeNeverReachesTheSibling::test_the_knob_is_read_from_the_project_that_owns_the_files (--claudemd <other project> honours THAT project's opt-out — review HIGH). AC-3 ✓ (NEGATIVE) ::test_the_shared_section_is_in_the_primary_and_not_in_the_sibling parametrised over default/explicit-true × cli/mcp; ::test_a_project_whose_only_knowledge_is_shared_gives_the_sibling_no_tail (no '### Memory tail' heading over nothing, 'Session:' still written); ::TestTheGateJudgesWhatTheWriterWrites::test_a_sibling_with_no_tail_because_all_knowledge_is_foreign_is_not_drift and ::test_a_sibling_the_policy_does_not_write_is_not_judged — gate_claudemd_state walks the writer's plan_dynamic_writes; and the gate still catches the failure it exists for: ::test_a_sibling_that_lost_its_own_tail_is_still_drift. AC-4 ✓ (NEGATIVE, mutation) ::TestAWriterThatIgnoresTheKnobIsCaught::test_writing_the_full_block_to_the_sibling_is_visible (strip disabled → the foreign section reaches the sibling, which the real tests refuse) and ::test_writing_with_the_knob_false_is_visible (knob ignored → AGENTS.md changes, which test_false_leaves_the_sibling_untouched refuses). AC-5 ✓ docs/{en,ru}/configuration.md: section 'Agent-instruction files (the DYNAMIC block)' with the key, its default, the JSON-boolean note and the example; CHANGELOG EN/RU; whats-new figure 248; the GitLab #14 reply drafted for the owner (posting is the owner's act). AC-6 ✓ verify run #2629 signed. Review (tausik-reviewer): 1 HIGH (knob read from the caller's db, not the owner of the files — fixed, tested), 2 MEDIUM (silent fallback → logged; CROSSCUTTING_SCOPE names all five producers), 2 LOW (stacked separators collapsed + asserted; docs note on the JSON boolean) — all applied. 252 tests across the seven related files; mypy clean. Domain: what a tracked file receives is a policy the project sets, and the gate judges by the same policy.
