---
slug: v14c-rewrite-brittle-tests
title: "C8: rewrite brittle implementation-detail тестов (5 файлов)"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: simple
role: qa
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "tests/test_audit_pytest_dedupe.py, tests/test_brain_sync.py, tests/test_brain_hook_utils.py, tests/test_brain_runtime_web_cache.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "никаких production scripts/* — только tests + CHANGELOG"
relevant_files:
  - "tests/test_audit_pytest_dedupe.py"
  - "tests/test_brain_sync.py"
  - "tests/test_brain_hook_utils.py"
  - "tests/test_brain_runtime_web_cache.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T11:00:16Z"
---

## Goal

test_audit_pytest_dedupe.py:104 (filename pin → glob), test_brain_sync.py:275 (CREATE TABLE regex → AST), test_audit_pytest_dedupe.py:91 (literal strings → behavior check), test_brain_hook_utils.py:188 (exact ISO format — keep but add tolerance), test_brain_runtime_web_cache.py mock-only consolidation.

## Acceptance Criteria

1. test_audit_pytest_dedupe.py:104 — filename pin переписан в glob (любой файл `tausik-1.4-pytest-dedupe-*.md` под docs/ru/research/), не привязан к конкретной дате 2026-05-02. 2. test_audit_pytest_dedupe.py:91 — literal-string assert "No duplicate test scenarios detected" заменён на behavior check (например, отсутствие группы дубликатов в structured output, либо assert на len()/keys() rather than точная строка). 3. test_brain_sync.py:275 — regex-парсинг CREATE TABLE заменён на AST/structured подход: `sqlite3.connect(":memory:").executescript(SCHEMA_SQL)` + `PRAGMA table_info` для извлечения столбцов; regex выкинут. 4. test_brain_hook_utils.py:188 — exact ISO format kept (тест проверяет конкретный edge-case '.000Z' vs 'Z'), но добавлена tolerance для второстепенных формат-вариаций (например, microseconds, '+00:00' vs 'Z'); тест должен ловить epoch-сравнение, а не строковое. 5. test_brain_runtime_web_cache.py — mock-only consolidation: повторяющиеся patch блоки вынесены в helper/fixture (DRY); тестовая поверхность сохранена. 6. Все исправленные тесты PASS — pytest scoped на 4 файла green. 7. NEGATIVE: новые тесты не теряют coverage (старые AC сохранены — namely glob matches actually present file, behavior assert ловит реальный delta, schema-drift guard всё ещё falls when column added). 8. CHANGELOG entry в [Unreleased] v1.4.0 polish (Phase C).

## Plan

[{"step": "Read all 5 spots full context (line\u00b110)", "done": true}, {"step": "Fix #1: test_audit_pytest_dedupe.py:104 \u2014 filename pin \u2192 glob", "done": true}, {"step": "Fix #2: test_audit_pytest_dedupe.py:91 \u2014 literal \u2192 behavior check", "done": true}, {"step": "Fix #3: test_brain_sync.py:275 \u2014 regex \u2192 sqlite3 PRAGMA table_info", "done": true}, {"step": "Fix #4: test_brain_hook_utils.py:188 \u2014 ISO tolerance helper", "done": true}, {"step": "Fix #5: test_brain_runtime_web_cache.py \u2014 patch helper fixture (mock-only DRY)", "done": true}, {"step": "Pytest scoped on 4 files \u2192 GREEN", "done": true}, {"step": "CHANGELOG.md + CHANGELOG.ru.md entry", "done": true}, {"step": "Verify + task_done", "done": true}]

## Rollback

## Journal

- 2026-05-07T11:00:16Z [implementation] — AC-1: ✓ test_audit_pytest_dedupe.py:104 — pinned filename `tausik-1.4-pytest-dedupe-2026-05-02.md` заменён на `glob("tausik-1.4-pytest-dedupe-*.md")` + sorted + `hits[-1]` для latest dated sibling. AC-2: ✓ test_audit_pytest_dedupe.py:91 (test_empty_groups_clean_message → renamed test_empty_groups_omits_per_test_rows) — два literal-string asserts заменены на behavior-контраст empty-vs-populated: empty render NOT enumerates per-test rows, populated DOES; output non-empty (scaffolding remains). AC-3: ✓ test_brain_sync.py:275 — regex parsing CREATE TABLE заменён на `sqlite3.connect(":memory:").executescript(SCHEMA_SQL)` + `PRAGMA table_info(<table>)` — реальный SQLite-парсер, multi-line/CHECK/FOREIGN KEY обрабатываются движком. AC-4: ✓ test_brain_hook_utils.py:188 — оригинальный кейс ('.000Z' vs 'Z') сохранён, parametrize добавил 2 новых ISO-варианта (microsecond '.000000Z' + fractional '.5Z') — tolerance band расширен. AC-5: ✓ test_brain_runtime_web_cache.py — `_patched_store(return_value)` `@contextmanager` хелпер; 7 тестов сконсолидированы (test_ok_returns_true_and_page_id, test_ok_not_mirrored_returns_true, test_scrub_blocked_returns_false_with_detector_names, test_scrub_blocked_without_issues, test_notion_error_returns_false, test_title_override_truncates_at_60, test_falls_back_to_url_when_title_empty); 6-line patch блок → 1 line с helper. test_exception_inside_returns_false НЕ тронут (использует side_effect, не store_record). AC-6: ✓ pytest scoped на 4 файлах: 65 passed in 2.94s, GREEN. AC-7 (NEGATIVE): ✓ Coverage сохранён: glob ловит реальный artefact (test passed), behavior-контраст ловит регрессию empty↔populated, schema-drift guard всё ещё падает при column drift (sqlite engine более строгий чем regex), parametrize расширил ISO-coverage не сужая. AC-8: ✓ CHANGELOG.md + CHANGELOG.ru.md — заголовок [Unreleased] обновлён "Phase B" → "Phases B + C", добавлен entry на верх Added/Добавлено секций (EN+RU sync). Net diff: 4 test-файла + CHANGELOG.md + CHANGELOG.ru.md. Production-код не менялся (scope_exclude соблюдён). Verify run #542 recorded (scope=standard, exit=0).
