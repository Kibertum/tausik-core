---
slug: arhivatsiya-zadach-neobratima-komandy-snyat
title: "Архивация задач необратима: команды снять archived_at нет, а Rollback обещает обратное"
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
  - "scripts/project_cli_hygiene.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_hygiene_unarchive.py"
  - "docs/en/task-archive-spec.md"
  - "docs/ru/task-archive-spec.md"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-28T15:58:09Z"
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

Мягкая архивация задач обратима командой, как обещает её же спецификация и Rollback задач, которые на неё ссылаются. Сейчас снять archived_at нельзя ничем, кроме прямого SQL, а прямой доступ к БД проекту запрещён.

## Acceptance Criteria

1. Замер ДО: путей, снимающих archived_at, ноль — ни у задач, ни у памяти; при этом Rollback задачи о гигиене обещает обратимость командой. 2. Команда снимает archived_at по слагу и по возрасту, с сухим прогоном. 3. НЕГАТИВНЫЙ: разархивация не меняет status и completed_at — она снимает признак скрытия, а не оживляет задачу. 4. Спецификация и Rollback перестают обещать то, чего нет: либо команда есть, либо обещание убрано.

## Plan

## Rollback

## Journal

- 2026-09-28T15:46:38Z [implementation] — AC-1 замер ДО: путей, снимающих archived_at, НОЛЬ. grep -rnI 'archived_at' по scripts/ harness/ docs/ даёт 25 живых совпадений, все читающие (WHERE archived_at IS NULL / IS NOT NULL) либо ставящие метку (_archive_apply, memory_archive). Ни одного UPDATE ... SET archived_at = NULL. backend_graph.py:106 говорит это прямо про память: 'the project has no memory_unarchive and no path that clears archived_at'. При этом Rollback задачи project-hygiene-sweep-with-ratchets:72 обещает 'архивация задач мягкая (archived_at), обратима командой' — обещание без реализации на 877 строках-кандидатах.
- 2026-09-28T15:56:57Z [implementation] — AC-2 (команда по слагу и по возрасту, с сухим прогоном): ✓ tests/test_hygiene_unarchive.py::TestTheSelectorsAreTheTwoWaysBackIn (4 теста) и ::TestTheDryRunIsTheDefault (4). tausik hygiene unarchive --slug S | --archived-within DAYS, dry-run по умолчанию. Живой смоук: 'Hygiene unarchive: nothing archived matches slug=nope'. Селектор ОБЯЗАТЕЛЕН — голый unarchive отклоняется ServiceError. --archived-within, а не «старше»: откатывать надо только что применённую партию, самые старые архивные строки — те, что должны остаться скрытыми.
- 2026-09-28T15:56:58Z [implementation] — AC-3 НЕГАТИВНЫЙ (status и completed_at не меняются): ✓ ::TestOnlyTheHidingFlagMoves::test_status_and_completed_at_survive_the_round_trip и ::test_the_row_returns_to_task_list. Двигаются только archived_at и updated_at; проверка идёт по task_list, потому что смысл признака — листинг. AC-4 (спека и claim перестают обещать чего нет): ✓ команда есть, и claim теперь ПРОВЕРЯЕТСЯ: ::TestThePromiseIsCheckedAndNotJustWritten читает спеку (en+ru) и требует, чтобы названная команда разбиралась парсером. Снят и обратный ложный claim: docs/{en,ru}/cli.md говорил 'НЕОБРАТИМО: команды, снимающей archived_at, нет' двумя строками ниже прозы про обратимость.
- 2026-09-28T15:57:05Z [implementation] — Domain: команда проверена на живой базе проекта, не только в tmp-фикстуре — hygiene unarchive --slug nope печатает отсутствие как отсутствие и ничего не пишет. Полная лента: 12068 прошли, 30 пропущены, 0 отказов, 184 с; было 12053 до задачи (+15 новых тестов). ruff и ruff format чисты; редеплой профилей выполнен ДО закрытия. Заодно снят ложный claim в architecture.md (en+ru): 'read-only гигиена проекта' про команду, которая пишет с --confirm с версии 1.5.
