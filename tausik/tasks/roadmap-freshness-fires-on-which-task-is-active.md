---
slug: roadmap-freshness-fires-on-which-task-is-active
title: "Свежесть карты релиза срабатывает на ТЕКУЩЕЙ активной задаче, а не на остатке — красное на файле, который никто не менял"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: simple
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/release_roadmap.py"
  - "tests/test_release_roadmap.py"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/release_roadmap.py"
  - "tests/test_release_roadmap.py"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T14:02:37Z"
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
---

## Goal

ROADMAP.md печатает остаток по статусам («planning 4» / «active 1, planning 3»), поэтому START любой задачи делает закоммиченную карту устаревшей, и полный прогон краснеет на файле, которого никто не трогал. Предмет карты — ЧТО ОСТАЛОСЬ в релизе, а не кто что держит прямо сейчас (это отвечает `tausik team`). Дефект заведён внутри one-implementation-per-command-mcp-over-cli: обнаружен полным прогоном сразу после старта задачи, в ту же смену, когда карта была сделана (roadmap-artifact-predates-decision-256). Чинить внутри чужой задачи не стал — предмет другой.

## Acceptance Criteria

AC-1 (предмет карты — остаток, а не кто что держит сейчас): перевод задачи planning→active НЕ меняет ни байта в порождённой карте. Тест рендерит карту, переводит задачу в active, рендерит снова и требует побайтового равенства. Сегодня это красное — колонка «Остаток по статусам» печатает «active 1».
AC-2 (охрана не потеряла зубы): ЗАКРЫТИЕ задачи по-прежнему меняет карту — тест на то же tmp-БД требует РАЗЛИЧИЯ после перевода в done. Иначе лекарство отменило бы саму охрану свежести.
AC-3 (потеря информации возмещена, а не проглочена): факт плана, который стоил колонки, — сколько задач ЗАБЛОКИРОВАНО — остаётся в карте отдельной величиной; blocked есть свойство плана, а не состояние текущей минуты.
AC-4: мутации объявлены и убиты по ветви либо объявлены эквивалентными; полный прогон, mypy, ruff, bootstrap --check; CHANGELOG в обоих файлах; карта перевыпущена.

## Plan

## Rollback

## Journal

- 2026-09-06T14:02:29Z [implementation] — AC verified: 1. ✓ перевод planning→active не меняет карту — тест test_starting_a_task_does_not_move_the_map рендерит, переводит статус, рендерит снова и требует побайтового равенства; до правки это было красным, потому что колонка печатала «active 1». Подтверждено и на живом дереве: полный прогон (9098 passed) прошёл ЗЕЛЁНЫМ при активной задаче, чего до правки не бывало. 2. ✓ охрана не потеряла зубы — test_closing_a_task_does_move_the_map требует РАЗЛИЧИЯ после перевода в done; мутация P3, снявшая blocked с остатка, и мутация P1, подменившая охраняемый статус на transient, убиты по ветви. 3. ✓ потеря возмещена: колонка «Заблокировано» публикует BLOCKED_STATUS отдельной величиной, итог по релизу тоже (сейчас 1); test_being_stuck_is_still_published проверяет строку «| 1 | 1 | 0 |». 4. ✓ мутаций 3, все KILLED по ветви (P1 BLOCKED_STATUS→active, P2 колонка печатает done, P3 blocked вычтен из остатка); мутатор удалён сразу; полный прогон 9098 passed / 27 skipped, mypy Success 353 файла, ruff All checks passed, bootstrap --check без дрейфа; CHANGELOG в обоих файлах; карта перевыпущена. Negative: подмена охраняемого статуса на transient («active») даёт красное на test_starting_a_task_does_not_move_the_map — сценарий, ради которого задача заведена, проверен именно с той стороны, с которой он ломался. Domain: карта теперь отвечает на вопрос «что осталось в релизе» и не отвечает на «кто что держит сейчас» — второе спрашивают у `tausik team`. Для читателя вне репозитория это разница между планом и снимком минуты.
