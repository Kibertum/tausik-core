---
slug: relevant-files-swallows-a-comma-joined-list-as-one-path
title: "GitLab #13: --relevant-files \"a.py,b.py\" принимается как ОДИН путь — область QG-2 портится молча, а отказ приходит от verify как «на эти файлы нет тестов»"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/project_parser_task.py, scripts/project_cli_task.py, scripts/service_task.py (или новый scripts/relevant_files_input.py), harness/claude/mcp/project/handlers_task*.py, tests/, docs/ru/cli.md, docs/en/cli.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Не разбивать по запятой тихо; не менять хранение (JSON-список в БД); не трогать scope_paths."
relevant_files:
  - "scripts/relevant_files_input.py"
  - "scripts/service_task.py"
  - "scripts/task_done_scope.py"
  - "scripts/service_task_done.py"
  - "scripts/project_parser_task.py"
  - "tests/test_relevant_files_input.py"
  - "tests/test_task_done_scope.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T12:25:13Z"
---

## Goal

Тикет GitLab #13 (владелец, из проекта kibertum-org на 1.8.0): `task update <slug> --relevant-files "a.py,b.py,c.py"` сохраняет один элемент со склейкой; `verify --task` затем отвечает «No tests mapped for ['a.py,b.py,c.py']» — ошибка всплывает не там, где сделана, и звучит как проблема проекта. Справка `--relevant-files … JSON-list scope` подталкивает к запятой, а контракт argparse — nargs='*' через пробел. Цена не косметическая: relevant_files — область QG-2, и с испорченным списком scoped-гейты не запускаются ни по одному настоящему файлу. ЗАМЕР, смена #251: scripts/project_parser_task.py:155 и :251 — nargs='*' без разбора запятой; в scripts/service_task.py, project_cli_task.py разбора нет. Починка по выбору тикета «не молчать»: значение с запятой внутри (и без такого файла на диске) ОТВЕРГАЕТСЯ при записи с текстом «пути передаются через пробел: --relevant-files a.py b.py» — не разбивается тихо, потому что запятая в имени файла легальна и разбить «честный» путь значило бы сломать его; справка переформулирована («space-separated; stored as a JSON list»). Тот же разбор для MCP tausik_task_update/task_done relevant_files (список строк — элемент с запятой тоже отвергается). Заодно task update предупреждает о путях, которых нет на диске (третий вариант тикета), не блокируя: файл может появиться позже.

## Acceptance Criteria

AC-1: `task update <slug> --relevant-files "a.py,b.py"` (элемент с запятой, файла с таким именем нет) отвергается с сообщением, называющим верную форму через пробел; relevant_files задачи не изменяются. AC-2: тот же элемент через MCP tausik_task_update / tausik_task_done relevant_files отвергается тем же текстом (одна реализация проверки). AC-3: НЕГАТИВ: путь с запятой, который СУЩЕСТВУЕТ на диске, принимается — запятая в имени легальна. AC-4: справка --relevant-files больше не говорит «JSON-list» о формате ввода; говорит «space-separated». AC-5: `task update` печатает предупреждение о несуществующих путях, не блокируя запись. AC-6: signed verify; CHANGELOG EN/RU.

## Plan

## Rollback

git revert; значения с запятой снова принимаются как один путь.

## Journal

- 2026-09-13T12:22:44Z [implementation] — Сделано: scripts/relevant_files_input.py (check_declared_paths + notice_for_json_list) — один валидатор на три входа: service_task.task_update (CLI update, verify --relevant-files), task_done_scope.persist_declared_scope (task done CLI+MCP, пишет через backend; получил tausik_dir и notices, чтобы task done показывал ту же пометку). Отказ — элемент с запятой, не существующий на диске, ≥2 частей, каждая похожа на путь (/ или .); существующий путь с запятой принимается; несуществующий — NOTE (верхний регистр, как читает _print_with_warnings); обратные слэши нормализуются как в gate_test_resolver. state import объявлен намеренно непроверяемым (файл — экспорт строки, прошедшей проверку при объявлении). Справка update: SPACE-separated. ЖИВОЙ РЕПРО GitLab #13 на развёрнутом CLI: до bootstrap — принято (ловушка: .tausik/tausik исполняет .claude/scripts), после — Error с верной формой; правильная форма через пробел записана. Ревью tausik-reviewer: 1 high (state_import — документировано как trust-the-file), 2 medium (пометка терялась на task done — исправлено; эвристика могла отказать одиночному имени с запятой — сужена), 3 low (NOTE регистр, backslash, размер файлов 500/500) — все учтены. 21 тест, dedupe на базе.
- 2026-09-13T12:25:10Z [implementation] — AC-1 ✓ живой развёрнутый CLI: `task update … --relevant-files "scripts/relevant_files_input.py,tests/test_relevant_files_input.py"` → Error с текстом «carries a comma … paths are passed SPACE-separated: --relevant-files a.py b.py»; relevant_files задачи не изменились (журнал); tests/test_relevant_files_input.py::TestACommaJoinedValueIsRefusedByTheRightForm::test_update_refuses_and_stores_nothing проверяет и отказ, и НЕзапись. AC-2 ✓ ::test_task_done_declaration_is_judged_the_same_way — persist_declared_scope (путь task done, CLI и MCP через backend) отвергает тем же RIGHT_FORM; одна реализация — relevant_files_input.check_declared_paths. AC-3 ✓ (НЕГАТИВ) ::TestTheCommaIsNotSplitSilently::test_an_existing_path_with_a_comma_in_its_name_is_accepted — существующий `scripts/a,b.py` принят как есть; ::test_a_single_not_yet_created_name_with_a_comma_is_a_note_not_a_refusal — граница эвристики. AC-4 ✓ ::test_the_help_text_no_longer_invites_the_comma — справка update говорит SPACE-separated и не говорит «JSON-list scope». AC-5 ✓ ::TestAMissingPathIsAWarningNotARefusal — NOTE о несуществующих путях, запись не блокируется; ::test_task_done_shows_the_same_note_as_update — та же пометка на закрытии. AC-6 ✓ verify #2585 подписан (scoped 86 файлов тестов, 6 прямых); CHANGELOG EN/RU; docs/{en,ru}/cli.md. Domain: агент, набравший список через запятую, получает отказ в момент ввода с верной формой, а не «нет тестов» от verify через полчаса; область QG-2 больше не может стать пустой молча.
