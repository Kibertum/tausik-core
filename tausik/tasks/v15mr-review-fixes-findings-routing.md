---
slug: v15mr-review-fixes-findings-routing
title: "v15mr-review-fixes: адресовать findings адверсариального ревью routing-эпика"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing_matrix.py, scripts/model_routing_adherence.py, tests/test_model_routing.py, docs/ru/research/model-routing-matrix.md, tests/*, README.md, docs/_generated/constants.json"
scope_exclude: null
relevant_files:
  - "scripts/model_routing_matrix.py"
  - "scripts/model_routing_adherence.py"
  - "tests/test_model_routing.py"
  - "tests/test_routing_adherence.py"
  - "docs/ru/research/model-routing-matrix.md"
  - README.md
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/model_routing_matrix.py"
  - "scripts/model_routing_adherence.py"
  - "docs/ru/research/model-routing-matrix.md"
  - "tests/*"
  - README.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T15:36:45Z"
---

## Goal

Исправить H1-H3 + M1-M3 + L1/L2/L4 находки Sonnet-ревью эпика v15-model-routing: герметичность теста (config={}), честный display для override point-release, импорт _model_family из matrix, multi-token family guard, VALID_PHASES из _MATRIX, пересчёт match по семействам, schema_version guard, fable в slug-map, docstring. H4 — doc-нота про implement-phase adherence.

## Acceptance Criteria

1. _model_family возвращает None при наличии >1 family-токена в id (multi-token guard). 2. _spec_from_model_id отдаёт честный display: точный известный id -> tier-display, иначе сам id (override claude-opus-4-9 НЕ показывает "Opus 4.8"). 3. VALID_PHASES выводится из _MATRIX (single source); aggregate_adherence пересчитывает match по recommended_family==actual_family, schema_version!=1 строки пропускаются. 4. record_adherence импортирует _model_family из model_routing_matrix; тест format_suggestion не читает реальный .tausik/config.json (config={}). 5. Негативный кейс (ошибочный/невалидный ввод): неизвестный/мульти-токен model id -> _model_family возвращает None и адекватный fallback, ошибка НЕ выбрасывается. 6. pytest зелёный; ruff/mypy/filesize чисто.

## Plan

## Rollback

git revert — изменения изолированы в model_routing_matrix.py/model_routing_adherence.py + тесты

## Journal

- 2026-06-14T15:36:44Z [implementation] — AC verified: 1. ✓ _model_family returns None on >1 family token (multi-token guard) — tests/test_model_routing.py::test_multi_token_model_id_is_ambiguous_none; single token still resolves 2. ✓ _spec_from_model_id honest display: exact known id->tier display, else id verbatim — test_override_future_pointrelease_keeps_honest_display (claude-opus-4-9 display==id, != 'Opus 4.8') 3. ✓ VALID_PHASES=tuple(_MATRIX.keys()) — test_valid_phases_derived_from_matrix; aggregate_adherence recomputes match from families + skips schema_version!=1 — test_recomputes_match_ignoring_persisted_flag + test_future_schema_rows_skipped 4. ✓ record_adherence imports _model_family from model_routing_matrix (definition site, H3); test_format_suggestion_is_one_line passes config={} (hermetic, H1). L2 (fable in _PROFILE_SLUG_BY_MODEL_ID) was already present — verified no change needed. H4 doc note added re implement-phase adherence 5. ✓ Negative: unknown id ('claude-sonnet-opus-x' multi-token, 'gpt-9') -> _model_family None, no raise; override unknown family -> display=id, suggest_model returns valid 3-key dict (existing test_config_override_unknown_model_id_used_as_display) 6. ✓ pytest 97 routing tests green; ruff+mypy clean; filesize model_routing_matrix.py 266 / model_routing_adherence.py 175 (<400); doc-constants 4151 in sync
