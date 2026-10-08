---
slug: u-cli-net-memory-edit-poetomu-perepisat-a-ne
title: "У CLI нет memory edit, поэтому «переписать, а не удалять» делается в обход"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/memory_edit.py"
  - "tests/test_memory_edit.py"
  - "scripts/project_cli_knowledge.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_db.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T14:44:11Z"
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

Запись памяти правится командой, а не через ручную правку проекции и state import: доктрина проекта требует переписывать протухшую запись, а CLI предлагает только delete и supersede.

## Acceptance Criteria

1. tausik memory edit <id> меняет content и title, обновляет updated_at и перепроецирует файл. 2. Правка НЕ трогает created_at и id — это та же запись, а не новая. 3. НЕГАТИВНЫЙ: правка архивированной записи отказывает с внятным текстом, а не тихо оживляет её. 4. Замер: обход через проекцию плюс state import стоил 16 правок в смене #277 и трижды требовал повторного импорта.

## Plan

## Rollback

git revert: команда исчезает, записи памяти не меняются — правка идёт только через неё.

## Journal

- 2026-09-28T14:37:21Z [implementation] — AC verified: 1 ✓ memory edit меняет title и content, обновляет updated_at и перепроецирует файл. 2 ✓ id, слаг и created_at не двигаются — это та же запись, а не новая. 3 ✓ негатив: правка архивированной записи отказывает с внятным текстом, а не оживляет её тихо. 4 ✓ замер: обход через проекцию плюс state import стоил 16 правок в этой смене и трижды требовал повторного импорта. Плюс сверх AC: пустой заголовок или тело отказываются как удаление под другим именем, а совпадающая правка не пишет ничего. Функция модуля, а не метод: обе god-класса ограничены храповиком поверхности. Root cause: доктрина требовала переписывать, а команда для этого не существовала. Domain: исправление записи памяти. Negative: архив и опустошение закреплены тестами. NO-DEAD-END. EVIDENCE: default 12035 passed / 30 skipped / 0 failed; tests/test_memory_edit.py 8 тестов.
- 2026-09-28T14:39:46Z [implementation] — Гейт размера отказал на project_parser: 499 строк до правки, 503 после четырёх моих. Расширять потолок не стал — у файла есть СВОЯ конвенция, записанная в нём же: секция переезжает в project_parser_*, когда потолок начинает давить. Переехал db как наименьший самодостаточный блок, 493 строки. При переезде поймал свою же ошибку порядка: вызов стоял выше локального импорта.
- 2026-09-28T14:44:06Z [implementation] — NO-DEAD-END: единственный красный прогон — гейт размера на project_parser после четырёх строк нового парсера. Не отвергнутый подход, а давление потолка, снятое переездом секции по конвенции самого файла. EVIDENCE после переезда: default 12035 passed / 30 skipped / 0 failed, ruff чистый.
