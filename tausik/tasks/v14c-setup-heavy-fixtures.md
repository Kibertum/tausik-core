---
slug: v14c-setup-heavy-fixtures
title: "C9: setup-heavy тесты → fixture extraction"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: simple
role: qa
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "tests/test_brain_sync.py, tests/test_audit_pytest_dedupe.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "test_brain_runtime_web_cache.py (consolidation done in C8); production scripts"
relevant_files:
  - "tests/test_brain_sync.py"
  - "tests/test_audit_pytest_dedupe.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T11:04:21Z"
---

## Goal

test_brain_sync.py 40-line dict construction в 8 тестов → fixture _web_cache_page(). test_brain_runtime_web_cache.py large patch blocks → conftest fixture. test_audit_pytest_dedupe.py heavy subprocess wrapping. Net -300 lines, same coverage.

## Acceptance Criteria

1. tests/test_brain_sync.py: введены compact property helpers (`_title`, `_rich_text`, `_url`, `_date`, `_number`, `_select`, `_multi_select`) + `_web_cache_page(**overrides)` builder. 2. test_map_web_cache + test_map_web_cache_default_ttl_when_missing переписаны через helpers — 40-line dict сократился до ≤8 lines per test. 3. tests/test_audit_pytest_dedupe.py: subprocess wrapping в TestCli.test_real_repo_runs (lines 128-145) вынесен в module-level helper `_run_audit_script(repo)` — каждый будущий subprocess test может переиспользовать. 4. NEGATIVE: тестовая поверхность сохранена — все assert'ы на row[<field>] по-прежнему ловят те же отклонения от map_page_to_row contract. Property helpers не маскируют тип-конкретные регрессии (Title vs rich_text, число vs строка). 5. Pytest scoped 2 файла — GREEN. 6. CHANGELOG.md + CHANGELOG.ru.md entry в [Unreleased] Phase C.

## Plan

[{"step": "Read test_brain_sync.py lines 50-235 + test_audit_pytest_dedupe.py 110-145", "done": true}, {"step": "Add property helpers + _web_cache_page() to test_brain_sync.py", "done": true}, {"step": "Rewrite test_map_web_cache + test_map_web_cache_default_ttl_when_missing", "done": true}, {"step": "Add _run_audit_script(repo) helper to test_audit_pytest_dedupe.py + use in test_real_repo_runs", "done": true}, {"step": "Pytest scoped on 2 files \u2192 GREEN", "done": true}, {"step": "CHANGELOG entries (EN+RU)", "done": true}, {"step": "Verify + task_done", "done": true}]

## Rollback

## Journal

- 2026-05-07T11:04:21Z [implementation] — AC-1: ✓ Введены compact property helpers в test_brain_sync.py: `_title`, `_rich_text`, `_url`, `_date`, `_number`, `_select`, `_multi_select` + `_web_cache_page(**property_overrides)` builder с sensible defaults. AC-2: ✓ test_map_web_cache переписан на `_web_cache_page()` (38-line inline → 1 line); test_map_web_cache_default_ttl_when_missing использует helpers напрямую (sparse skeleton сохранён, но каждое property — однострочный вызов). AC-3: ✓ test_audit_pytest_dedupe.py — `_venv_python(repo)` + `_run_audit_script(repo, *args)` extracted to module-level; `TestCli.test_real_repo_runs` стал ~3 строки (single helper call + 2 asserts). AC-4 (NEGATIVE): ✓ Helpers возвращают точные dict shapes которые `map_page_to_row` инспектит — title-vs-rich_text-vs-select-vs-multi_select разделение всё ещё load-bearing; assertion surface не изменилась — те же `assert row[<field>] == ...`; CLI smoke по-прежнему проверяет `r.returncode == 0` + `"pytest dedupe audit" in r.stdout`. AC-5: ✓ Pytest scoped на 2 файлах: 30 passed in 0.79s, GREEN. AC-6: ✓ CHANGELOG.md + CHANGELOG.ru.md entry добавлен в [Unreleased] Phases B+C, EN+RU sync. Side-note: test_brain_runtime_web_cache.py originally в scope C9, но patch-blocks consolidation landed earlier в C8 — задача проведена с двухфайловым scope (отмечено в CHANGELOG entry). Verify run recorded (scope=standard, exit=0).
