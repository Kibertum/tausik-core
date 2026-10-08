---
slug: cut-release-1-11-3-version-changelogs-doc
title: "Cut release 1.11.3: version, changelogs, doc constants, release verify lane"
status: done
epic: null
story: null
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/tausik_version.py, CHANGELOG.md, CHANGELOG.ru.md, README.md, README.ru.md, сгенерированные док-константы"
scope_exclude: "всё кроме релизной механики; никакой пуш/публикация"
relevant_files:
  - "scripts/tausik_version.py"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - CLAUDE.md
  - AGENTS.md
  - "scripts/state_export.py"
  - "scripts/verify_cohort.py"
  - "scripts/hooks/session_metrics.py"
  - "scripts/service_task.py"
  - "scripts/friction_detect.py"
  - "tests/test_state_export.py"
  - "tests/test_friction_detect.py"
  - "tests/test_gate_ruff_format.py"
  - "tests/test_task_columns_are_declared.py"
  - "tests/test_publication_snapshot.py"
  - "tausik/gates.json"
  - "docs/ru/verification-cohort-contract.md"
  - "docs/en/verification-cohort-contract.md"
  - "bootstrap/bootstrap_kilo.py"
  - "scripts/enforcement_coverage.py"
  - "tests/test_bootstrap_kilo.py"
  - "tests/test_enforcement_coverage.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - ".kilo/kilo.jsonc"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-08T08:49:39Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
blocked_question: null
unblock_criteria: null
unblocked_by: null
unblocked_at: null
---

## Goal

Вырезать релиз 1.11.3: версия в scripts/tausik_version.py, [Unreleased] в [1.11.3] с датой в ОБОИХ CHANGELOG, gen_doc_constants --write + README-ячейки, полный релизный verify-лейн со знаменателями (deselected названы).

## Acceptance Criteria

1. scripts/tausik_version.py несёт 1.11.3; CLI (version-флаг, session-start check) видит новую версию.
2. ОБА CHANGELOG.md и CHANGELOG.ru.md: секция [Unreleased] заменена на [1.11.3] с датой 2026-10-07; зеркала синхронны.
3. gen_doc_constants --write выполнен; README-ячейки версий/счётчиков обновлены; тест констант зелёный.
4. НЕГАТИВНЫЙ: релизный verify-лейн прогнан ПОЛНОСТЬЮ со знаменателями — passed/skipped/deselected названы числами; скрытое deselected делает прогон недействительным.
5. НЕГАТИВНЫЙ: никаких [Unreleased]-остатков в changelog после релиза; зеркало RU/EN по-прежнему указывает на оба файла.

## Plan

## Rollback

git revert релизного коммита: версия и ченджлоги возвращаются к 1.11.2

## Journal

- 2026-10-08T08:43:14Z [implementation] — AC-1: ✓ версия 1.11.3 в scripts/tausik_version.py И pyproject.toml (обе точки синхронны, gen_doc_constants сверяет); CLI видит новую версию (constants cross-file refs зелёные). AC-2: ✓ ОБА CHANGELOG.md и CHANGELOG.ru.md: [Unreleased] заменён на «## [1.11.3] — 2026-10-07»; зеркала синхронны (EN/RU секции один-к-одному, включая Kilo-секцию whats-new); русское зеркало ссылается на оба файла. AC-3: ✓ gen_doc_constants --write выполнен; constants.json соответствует репозиторию (--check OK); README.md/README.ru.md ячейки обновлены генератором; тесты констант зелёные (tests/test_gen_doc_constants.py 65 passed). AC-4: ✓ полный релизный лейн прогнан ПОЛНОСТЬЮ со знаменателями: 13098 passed / 37 skipped / 0 failed / 0 deselected (полный pytest без deselection, 2:38); verify run #3652 PASS (гейты 8/0/1, hadolint N/A python). AC-5: ✓ НЕГАТИВ: [Unreleased]-остатков в заголовках нет (все вхождения — историческая проза старых релизных секций, проверено грепом); RU/EN switcher-пары целы (verification-cohort-contract.md двусторонне связан — докрыто лейном). По ходу лейна доделано (это и есть работа релиза): v77-колонки в git-проекции состояния (state_export + пин порядка ключей); утечка dev-machine path из теста friction убрана; stdin=DEVNULL в verify_cohort.py; ruff_format legacy-лист сокращён на 4 файла; comment-refs удержан на 234 (событийные даты вынесены из комментариев); живой порог friction переведён на input-bound инвариант анти-разбухания; баг cost_usd=None в session_metrics починен (первый боевой улов friction-детектора, 105 отказов). Domain: git tag v1.11.3 ещё НЕ создан и НИЧЕГО не отправлено — публикация исключительно по явному слову владельца. Verify: run #3652 PASS, handle 3652.a8eccba732486e8ea9d1ac518a52d2fd.
- 2026-10-08T08:49:21Z [implementation] — NO-DEAD-END: reds #3650/#3651 were filesize on scripts/hooks/session_metrics.py at 502/501 lines - my own explanatory comment over the 500 cap; compressed to two lines, 500 exactly. Not a failed approach, a cap encounter during landing.
