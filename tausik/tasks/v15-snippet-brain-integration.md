---
slug: v15-snippet-brain-integration
title: "[1.5] Brain integration — extract --scope brain пишет snippet в Notion"
status: done
epic: v15-snippet-system
story: v15-snippet-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli_snippet.py, scripts/project_parser.py, tests/*, README.md, docs/_generated/constants.json"
scope_exclude: "scripts/brain_mcp_write.py, scripts/brain_snippet_detect.py, scripts/brain_runtime.py (read-only deps), .claude/ (bootstrap-generated)"
relevant_files:
  - "scripts/project_cli_snippet.py"
  - "scripts/project_parser.py"
  - "tests/test_snippet_brain_extract.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/project_cli_snippet.py"
  - "scripts/project_parser.py"
  - "tests/*"
  - README.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T15:59:57Z"
---

## Goal

Связать локальные snippets с cross-project brain. CLI `tausik snippet extract <id> --scope brain` — читает snippet из локальной таблицы, формирует brain_artifact_card payload с taxonomy_kind=snippet (через классификатор v15-snippet-classifier как validation), вызывает brain_mcp_write.store_record. Также: при detect-cluster с occurrences ≥ N (config knob brain.auto_propose_snippet_threshold) — auto-suggest extract. Tests: extract flow, taxonomy validation, auto-propose threshold. Это (5/5) — финальная интеграция, требует все 4 предыдущих.

## Acceptance Criteria

1. CLI `tausik snippet extract <id> --scope brain` читает snippet из локальной таблицы, формирует brain patterns-card (name/description/when_to_use/example), классификатор detect_artifact_kind задаёт artifact_taxonomy_kind (snippet|pattern), вызывает brain_mcp_write.store_record(category=patterns) через brain_runtime.open_brain_deps. 2. При `snippet detect` кластер с occurrences>=N (config knob brain.auto_propose_snippet_threshold, opt-in) печатает advisory-предложение запустить extract --scope brain. 3. Негативный кейс (ошибочный ввод/невыполнимое условие): brain не настроен/disabled -> понятное сообщение, без падения и без записи; несуществующий snippet id -> сообщение 'not found', exit без ошибки; threshold не задан -> auto-propose молчит. 4. pytest: extract flow (mock open_brain_deps+store_record), taxonomy через классификатор, auto-propose threshold, негатив (brain off, id отсутствует).

## Plan

## Rollback

git revert — additive CLI subcommand + parser; удаление extract-ветки из project_cli_snippet.py и subparser из project_parser.py возвращает прежнее поведение; БД/Notion не мутируются при revert

## Journal

- 2026-06-14T15:59:56Z [implementation] — AC verified: 1. ✓ `snippet extract <id> --scope brain` reads snippet (get_snippet), builds patterns-card via _snippet_to_pattern_card (name/description/when_to_use/example fenced), detect_artifact_kind sets artifact_taxonomy_kind (snippet|pattern), store_record(category=patterns) via brain_runtime.open_brain_deps + brain_store_format — tests/test_snippet_brain_extract.py::TestExtract::test_extract_calls_store_record + TestPatternCard 2. ✓ snippet detect captures (id,occurrences); _maybe_propose_brain_extract prints advisory 'snippet extract <id> --scope brain' for clusters with occurrences>=brain.auto_propose_snippet_threshold (opt-in, brain enabled) — TestAutoPropose::test_proposes_when_threshold_met 3. ✓ Negative: brain disabled/not-configured -> 'not configured' message, store_record NOT called (test_brain_disabled_message_no_write); missing id -> 'not found' (test_missing_snippet_id); threshold unset or brain off -> auto-propose silent (test_silent_when_threshold_unset/disabled); unsupported scope -> message (test_unsupported_scope) 4. ✓ pytest tests/test_snippet_brain_extract.py 8 passed; ruff/mypy clean; filesize project_parser.py 397 / project_cli_snippet.py 159 (<400); bootstrap synced; doc-constants 4170 in sync
