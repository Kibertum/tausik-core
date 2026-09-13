---
slug: relevant-files-swallows-a-comma-joined-list-as-one-path
title: "GitLab #13: --relevant-files \"a.py,b.py\" принимается как ОДИН путь — область QG-2 портится молча, а отказ приходит от verify как «на эти файлы нет тестов»"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Тикет GitLab #13 (владелец, из проекта kibertum-org на 1.8.0): `task update <slug> --relevant-files "a.py,b.py,c.py"` сохраняет один элемент со склейкой; `verify --task` затем отвечает «No tests mapped for ['a.py,b.py,c.py']» — ошибка всплывает не там, где сделана, и звучит как проблема проекта. Справка `--relevant-files … JSON-list scope` подталкивает к запятой, а контракт argparse — nargs='*' через пробел. Цена не косметическая: relevant_files — область QG-2, и с испорченным списком scoped-гейты не запускаются ни по одному настоящему файлу. ЗАМЕР, смена #251: scripts/project_parser_task.py:155 и :251 — nargs='*' без разбора запятой; в scripts/service_task.py, project_cli_task.py разбора нет. Починка по выбору тикета «не молчать»: значение с запятой внутри (и без такого файла на диске) ОТВЕРГАЕТСЯ при записи с текстом «пути передаются через пробел: --relevant-files a.py b.py» — не разбивается тихо, потому что запятая в имени файла легальна и разбить «честный» путь значило бы сломать его; справка переформулирована («space-separated; stored as a JSON list»). Тот же разбор для MCP tausik_task_update/task_done relevant_files (список строк — элемент с запятой тоже отвергается). Заодно task update предупреждает о путях, которых нет на диске (третий вариант тикета), не блокируя: файл может появиться позже.

## Acceptance Criteria

AC-1: `task update <slug> --relevant-files "a.py,b.py"` (элемент с запятой, файла с таким именем нет) отвергается с сообщением, называющим верную форму через пробел; relevant_files задачи не изменяются. AC-2: тот же элемент через MCP tausik_task_update / tausik_task_done relevant_files отвергается тем же текстом (одна реализация проверки). AC-3: НЕГАТИВ: путь с запятой, который СУЩЕСТВУЕТ на диске, принимается — запятая в имени легальна. AC-4: справка --relevant-files больше не говорит «JSON-list» о формате ввода; говорит «space-separated». AC-5: `task update` печатает предупреждение о несуществующих путях, не блокируя запись. AC-6: signed verify; CHANGELOG EN/RU.

## Plan

## Rollback

git revert; значения с запятой снова принимаются как один путь.

## Journal
