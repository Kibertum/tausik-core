---
slug: gen-doc-constants-does-not-fix-readme-counts
title: "Гейт check_docs советует команду, которая не приводит гейт в зелёное"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/gen_doc_constants.py (флаг --write), scripts/doc_drift_scanners.py (функция write_cross_file_fixes, переиспользует существующие паттерны), scripts/hooks/check_docs.py (совет), tests/. Мета-тест — новый tests/test_gate_advice_is_actionable.py."
scope_exclude: "Не менять сами счётчики руками. Не трогать version-скан (сделан отдельно)."
relevant_files:
  - "scripts/gen_doc_constants.py"
  - "scripts/doc_drift_scanners.py"
  - "scripts/hooks/check_docs.py"
  - "tests/test_doc_write_fixes.py"
  - "tests/test_gate_advice_is_actionable.py"
  - "docs/en/dev-doc-checks.md"
  - "docs/ru/dev-doc-checks.md"
  - skills.example.json
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T17:18:36Z"
---

## Goal

Гейт check_docs при дрейфе печатает «run gen_doc_constants.py and re-commit», но скрипт правит только constants.json; четыре doc-count места в README (бейдж-URL, бейдж-label, bold, проза) и cross-file version/mcp/code-счётчики правятся руками. Выполнение совета оставляет гейт красным. Напоролся дважды за релиз. Добавить gen_doc_constants --write: регенерит constants.json И чинит все cross-file места, которые проверяет --check (test/mcp/code-счётчики по CROSS_FILE_SCAN_TARGETS, version-refs по VERSION_SCAN_TARGETS), подставляя из тех же узких паттернов и только ВНЕ fenced-блоков. Совет гейта переписать на --write. Плюс мета-тест на класс: у каждого гейта, печатающего «run X», прогоном убедиться, что X делает --check зелёным.

## Acceptance Criteria

1) gen_doc_constants --write регенерит constants.json И правит cross-file doc-count места (бейдж-URL, бейдж-label, bold, проза) + version-refs. 2) После --write гейт --check зелёный без ручных правок — проверено прогоном на искусственно рассинхронизированном README. 3) Совет check_docs советует команду, которая реально приводит его в зелёное. 4) --write идемпотентен: повторный запуск даёт пустой diff. 5) Мета-тест: для каждого гейта, печатающего 'run X', прогоном подтвердить, что X делает состояние валидным. Негативные сценарии: 6) Ошибка, если --write трогает числа ВНУТРИ fenced-блоков (примеры кода) или исторические version-refs. 7) Ошибка, если совет гейта снова не работает — мета-тест это ловит. 8) Ошибка, если --write переписывает файлы без нужды (не пустой diff при синхронном состоянии). 9) Ошибка, если полный прогон даёт новое падение против базы.

## Plan

## Rollback

git checkout -- scripts/ tests/

## Journal

- 2026-07-10T17:18:24Z [implementation] — AC verified: 1. ✓ gen_doc_constants --write регенерит constants.json И правит cross-file места — write_cross_file_fixes в doc_drift_scanners.py, переиспользует _TEST_COUNT/_MCP_COUNT/_CODE_COUNT_PATTERNS + version-refs. Живой прогон на репозитории: 'Fixed cross-file refs in README.md/README.ru.md'. 2. ✓ После --write --check зелёный без ручных правок — доказано на искусственно рассинхронизированном README (scratchpad/write_probe.py: до rc=1, после rc=0 GREEN) и мета-тестом test_advised_command_turns_a_red_check_green. 3. ✓ Совет check_docs переписан на '--write'; test_check_docs_advises_the_command_that_actually_fixes_it читает исходник хука. 4. ✓ Идемпотентно — test_idempotent, test_write_is_idempotent_end_to_end, живой второй прогон 'already in sync'. 5. ✓ Мета-тест tests/test_gate_advice_is_actionable.py: петля дрейф->совет->зелёный замкнута end-to-end (build_constants_doc замокан, остальное — реальный код). Негативные: 6. ✓ test_never_touches_fenced_examples — числа в fenced-блоках (tests-999-brightgreen, ![999 tests]) не тронуты; test_foreign_version_untouched — SENAR v1.3, Python v3.11 целы. 7. ✓ test_writer_closes_every_gap_the_scanner_reports: после writer scan_test_counts даёт []. 8. ✓ test_in_sync_file_is_not_rewritten — пустой diff при синхронном состоянии. 9. ✓ Полный прогон 4420 passed, 12 skipped, 0 failed; ruff All checks passed. Root cause (logic-error + неполное покрытие): (а) gen_doc_constants правил только constants.json, cross-file места — руками; совет гейта не приводил его в зелёное. (б) Дыра шире: _TEST_COUNT_PATTERNS матчил только англ. '![N tests]'/'**N tests**' и несуществующий 'tests-N%20passed'; реальный бейдж 'tests-N-brightgreen', русские формы и проза 'covered by N'/'покрыто N' не проверялись вообще — '4341 тестов' висел в ru README через релизы. Prevention: (1) инструмент починки чинит ВСЁ, что флагует проверка, и сам себя перепроверяет; (2) гейт, печатающий 'run X', обязан иметь тест, что X делает состояние валидным (мета-тест); (3) паттерны покрывают все языки и форматы, узко и по структурным якорям. Память #199. Побочно закрыто из бэклога: skills-example-sources-dead-config — секция sources удалена из skills.example.json (ноль читателей, только external_skills читается), JSON валиден, 5 external_skills целы.
