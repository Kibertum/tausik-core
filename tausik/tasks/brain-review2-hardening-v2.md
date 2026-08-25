---
slug: brain-review2-hardening-v2
title: "Review-2 bundle: CRIT/HIGH/MED fixes from second review pass"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-bypass-marker-hardening
scope: "scripts/brain_runtime.py, scripts/hooks/_common.py, scripts/brain_scrubbing.py, scripts/brain_sync.py (schema-drift test только), scripts/hooks/brain_search_proactive.py, tests/test_service_knowledge_decide.py, tests/test_hooks_common.py, tests/test_brain_scrubbing.py, tests/test_brain_sync.py, tests/test_brain_search_proactive_hook.py"
scope_exclude: "LOW findings (NFKD false-positive docs, ttl_days=0 docs), MED findings из первого ревью (уже в backlog — brain-sync-transaction-atomicity, WAL mode, cursor advance etc)"
relevant_files:
  - "scripts/brain_runtime.py"
  - "scripts/brain_scrubbing.py"
  - "scripts/brain_sync.py"
  - "scripts/hooks/_common.py"
  - "scripts/hooks/brain_search_proactive.py"
  - "tests/test_service_knowledge_decide.py"
  - "tests/test_brain_scrubbing.py"
  - "tests/test_brain_sync.py"
  - "tests/test_hooks_common.py"
  - "tests/test_brain_search_proactive_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T12:27:35Z"
---

## Goal

Закрыть находки второго review: CRIT-1 (brain_runtime format issues_list[dict]), HIGH-1 (homoglyph map неполный — Cyrillic lowercase + Greek lowercase), HIGH-2 (anchor bypass: U+2028/2029 line seps, tilde fences, indented blocks), MED-1 (schema drift test), MED-2 (double urldecode + HTML entity), MED-4 (sqlite error broadening + ORDER BY fix + stdin size cap в hook)

## Acceptance Criteria

AC1 (CRIT-1): brain_runtime.py форматирует scrub_blocked из issues[dict] через detector keys (не raw match/hint): scrub_blocked: filesystem_paths, emails. Тест в test_service_knowledge_decide использует real dict shape.
AC2 (HIGH-1a): _HOMOGLYPHS расширен Cyrillic lowercase (в н т м к + б з і ї є ё ш щ and more) и Greek lowercase (α β γ δ ε ζ η θ ι κ λ μ ν ο π ρ σ τ υ φ χ ψ ω).
AC3 (HIGH-1b): Verified by test: 'αpex' блокируется ['apex'], 'Вrincess' блокируется ['brincess'], 'мanager' блокируется ['manager'], 'νext' блокируется ['next'].
AC4 (HIGH-2a): marker_present_anchored не split'ит по U+2028/U+2029 (использует .split('\\n') или предварительный strip). Test: '\\u2028confirm: cross-project\\u2028' в одной строке prose → False.
AC5 (HIGH-2b): Fence regex покрывает ``` И ~~~. Test: marker внутри ~~~block~~~ → False.
AC6 (HIGH-2c): Indented (4-space / tab) marker line отвергается. Test: 4-space indented 'confirm: cross-project' → False.
AC7 (MED-1): Новый тест parses brain_schema.SCHEMA_SQL и assert'ит что _ALLOWED_COLS_OF[cat] == schema_cols - {'id'} для всех 4 категорий.
AC8 (MED-2): _detect_blocklist применяет unquote в цикле до стабильности (bound 3) И html.unescape. Test: '%2570rincess' + '&#112;rincess' блокируются ['[вычеркнуто: third-party-project]'].
AC9 (MED-4a): brain_search_proactive.py ловит sqlite3.Error (broader), обе функции _lookup_* обёрнуты try/except.
AC10 (MED-4b): ORDER BY fetched_at переписан на Python-sort через _parse_iso_to_epoch. Test: 2 row с '...Z' и '....000Z' — freshest выигрывает.
AC11 (MED-4c): stdin чтение через .read(cap) с size limit (1MB). Test: 2MB stdin → graceful exit 0.
AC12: ruff + mypy scripts/ clean.
AC13: Full suite 1575+N pass где N — новые тесты.

## Plan

## Rollback

## Journal

- 2026-04-24T12:24:08Z [implementation] — AC verified: 1. CRIT-1 brain_runtime использует detector keys не raw match (injection-safe) ✓ 2-3. HIGH-1: _HOMOGLYPHS +25 codepoints (Cyrillic lowercase в/н/т/м/к + Greek lowercase α/β/ν/ρ/τ/μ etc) ✓ 4-6. HIGH-2: U+2028/2029/0085/\v/\f stripped перед split; fence regex ` ``` ` + ~~~; _INDENTED_RE отвергает 4+spaces/tab marker lines ✓ 7. MED-1: test_allowed_cols_matches_schema парсит SCHEMA_SQL regex + сверяет с _ALLOWED_COLS_OF ✓ 8. MED-2: _fully_decode итерирует unquote+html.unescape до 3 раз или стабильности; double-encode (%2570) и HTML entity (&#112;/&#x70;) блокируются ✓ 9. MED-4a: sqlite3.Error broader catch + try/except на _lookup_exact_url ✓ 10. MED-4b: ORDER BY заменён на max() по parsed epoch; mixed ISO formats sort correctly ✓ 11. MED-4c: _STDIN_SIZE_CAP=1MiB в _read_stdin_json ✓ 12. ruff + mypy scripts/ clean ✓ 13. Full suite 1598/1598 (было 1575, +23 новых теста) ✓
