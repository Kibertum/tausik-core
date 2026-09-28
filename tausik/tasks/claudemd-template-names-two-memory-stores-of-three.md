---
slug: claudemd-template-names-two-memory-stores-of-three
title: "Шаблон CLAUDE.md называет два хранилища памяти из трёх: общая база 1.8 не попала в таблицу маршрутизации"
status: done
epic: release-19-renar-conformance
story: release19-tracker-promises
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - "tests/test_memory_template_names_three_stores.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_compaction_contract.py"
  - "docs/en/knowledge-store.md"
  - "docs/ru/knowledge-store.md"
  - CLAUDE.md
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/**"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "docs/en/*.md"
  - "docs/ru/*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-13T16:15:32Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

Шаблон, который bootstrap раскладывает в КАЖДЫЙ проект, называет все три хранилища памяти и правило выбора между ними.

## Acceptance Criteria

1. Таблица маршрутизации памяти в build_full_body называет ТРИ хранилища: память проекта, общую базу знаний 1.8 и auto-memory агента. Заголовок «two systems» исправлен вместе с содержимым — он и есть утверждение.
2. Правка доезжает до ВСЕХ шаблонов, которые тикет GitLab #6 перечисляет: CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md. Форма закрывается перечислением из кода.
3. Названо, ПОЧЕМУ это не мелочь: главная возможность 1.8 отсутствует на двери, которая раскладывается в каждый проект. Это тот же дефект «главное не названо на входе», который мы правили в README, whats-new и changelog 1.8 — но эта дверь ведёт к КАЖДОМУ пользователю.
4. НЕГАТИВНЫЙ сценарий: тест сверяет число хранилищ в шаблоне с фактическим числом маршрутов памяти в коде, чтобы расхождение не могло вернуться молча.

## Plan

## Rollback

git revert коммита; правка в одном шаблоне

## Journal

- 2026-09-13T16:15:28Z [implementation] — AC-1 ✓ bootstrap_templates.MEMORY names three destinations with a criterion each — Project memory (memory add), Shared knowledge (memory add --global, read back as 'Shared knowledge — from other projects'), Agent auto-memory; heading 'choose the destination by what the fact is about' carries no count; tests/test_memory_template_names_three_stores.py::TestTheTableNamesEveryStore::test_the_three_stores_and_their_criteria_are_named, ::test_the_heading_states_no_count, ::test_the_litmus_names_both_branches (the hard litmus routes to memory add AND memory add --global — review HIGH), ::test_the_shared_store_is_named_as_it_is_read_back (ties to service_knowledge_aggregates). AC-2 ✓ one body feeds CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md — ::test_every_generated_body_carries_all_three parametrised over the four outputs AND both tiers (standard, minimal — MINIMAL_MEMORY in bootstrap_templates_tiers.py fixed too, review HIGH). AC-3 ✓ why it is not cosmetic is in the module docstring and the CHANGELOG entry: the routing table is the one document every agent reads as law, and a destination absent from it is never chosen. AC-4 ✓ (NEGATIVE) ::test_the_row_count_is_the_number_of_routes_the_code_has derives 3 from the code (1 + --global flag on the memory add parser + non-empty memory_sinks.DEFAULT_SINKS); the docstring states exactly what it does not guard (a publish-only path). Line budget 80-180 of the generated CLAUDE.md paid for by folding the types line into the first row (183 -> 180). docs/{en,ru}/knowledge-store.md disambiguate 'two stores' (TAUSIK's) from three destinations; this repository's own CLAUDE.md table gained the shared-store row (dogfooding, review MEDIUM). 136 tests across the six related files; verify run #2627 signed. Domain: the table an agent routes by names every place knowledge can go, and its size is counted from the code.
