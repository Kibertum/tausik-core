---
slug: one-implementation-per-command-mcp-over-cli
title: "Одна реализация на команду: MCP обязан быть транспортом над CLI, а не второй реализацией"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: null
scope_exclude: "общий храповик потерь вывода между MCP и CLI (задача ratchet-for-mcp-cli-surface-parity, другой эпик); проверка посторонних аргументов (закрыта отдельно); схемы инструментов в tools*.py — их предмет не логика, а описание"
relevant_files:
  - "scripts/mcp_handler_shape.py"
  - "scripts/render_task.py"
  - "scripts/render_memory.py"
  - "scripts/render_status.py"
  - "scripts/render_session.py"
  - "scripts/render_hierarchy.py"
  - "tests/test_mcp_handlers_are_transport.py"
  - "tests/test_project_mcp.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/handlers_knowledge.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "scripts/project_cli.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_events.py"
  - "scripts/project_cli_ops.py"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/mcp_handler_shape.py"
  - "scripts/render_task.py"
  - "scripts/render_memory.py"
  - "scripts/render_status.py"
  - "scripts/render_session.py"
  - "scripts/render_hierarchy.py"
  - "tests/test_mcp_handlers_are_transport.py"
  - "tests/test_project_mcp.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/handlers_knowledge.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "scripts/project_cli.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_events.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli_verify.py"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T13:54:15Z"
resolution: null
resolution_reason: null
---

## Goal

Две независимые реализации одной команды означают ДВА ВОЗМОЖНЫХ ВЕРДИКТА, и квитанция, подписанная по одному пути, ничего не утверждает про другой. Это не теория: обработчик MCP tausik_update_claudemd был второй копией команды CLI и терял впрыск памяти вместе с обновлением AGENTS.md — сессия закрывалась как состоявшаяся, а обещанное не выполнялось. Расхождение поверхностей MCP и CLI ловилось глазами ТРИЖДЫ подряд, после чего заведена задача ratchet-for-mcp-cli-surface-parity: храповик признан нужным именно потому, что четвёртая точечная правка ничего не изменит.

ЗАМЕР ПОВЕРХНОСТИ: 117 инструментов, 44501 байт схемы. Каждый из них — потенциальная вторая реализация.

ЧТО ДЕЛАЕТСЯ: MCP становится транспортом. Обработчик разбирает аргументы, вызывает ТУ ЖЕ функцию, что и CLI, и сериализует результат. Никакой логики в обработчике. Тогда паритет перестаёт быть предметом проверки — он становится свойством конструкции, и храповик из ratchet-for-mcp-cli-surface-parity нужен только на границе разбора аргументов.

СМЕЖНОЕ, РЕШАЕМОЕ ЗАОДНО: MCP-сервер не проверяет аргументы и молча выбрасывает посторонние (задача mcp-server-drops-unknown-arguments-silently); MCP task_show скрывает поля, по которым агента судят; поля decide режутся на 1024 символа в обеих поверхностях, и ограничение не документировано ни в одной.

НЕГАТИВНОЕ: идёт ПОСЛЕ трёхзначного результата и МОЖЕТ идти параллельно схлопыванию зеркал, но не раньше — обе операции трогают всё дерево, и вести их одновременно значит лишиться возможности сказать, что именно сломалось.

## Acceptance Criteria

AC-1 (инвентарь ЗАМЕРОМ, а не глазами): множество обработчиков MCP, несущих логику сверх делегирования, ВЫВЕДЕНО разбором AST по всем harness/claude/mcp/project/handlers*.py (включая записи таблиц диспетчеризации, не только функции _do_*), и для каждого элемента назван CLI-двойник либо отсутствие такового с причиной. Инвентарь записан в журнал задачи ДО правок.

AC-2 (одна реализация на команду): каждая пара «обработчик MCP — команда CLI» с общим предметом схлопнута в ОДНУ функцию, которую вызывают ОБЕ поверхности. Логика в обработчике не остаётся — он разбирает аргументы, вызывает общую функцию и сериализует. Всякое расхождение, вскрытое схлопыванием, названо поимённо: живой случай — tausik_task_next печатает ЧИСЛО отложенных задач, тогда как CLI печатает их СПИСОК, то есть агент через MCP не видит, чего именно ждёт план.

AC-3 (паритет — свойство конструкции, а не предмет проверки): гейт ВЫВОДИТ множество обработчиков с логикой (по AST, предмет охраны не перечисляется) и краснеет, когда оно растёт. Negative: обработчик с ветвлением, добавленный в прогоне, даёт красное. Храповик обязан УМЕТЬ СЖИМАТЬСЯ: элемент, переставший нести логику, обязан быть удалён из базовой линии, иначе линия — просто список.

AC-4 (границы объявлены, чужое не поглощено): общий храповик ПОТЕРЬ вывода между поверхностями остаётся задачей ratchet-for-mcp-cli-surface-parity (другой эпик) и здесь НЕ делается; проверка посторонних аргументов закрыта задачей mcp-server-drops-unknown-arguments-silently. Здесь — только структурное схлопывание и структурный храповик. Что осталось несхлопнутым и почему — объявлено в остатке, а не умолчано.

AC-5: полный прогон, mypy, ruff, bootstrap --check (--ide all); мутации объявлены и убиты ПО ВЕТВИ либо объявлены эквивалентными в исходнике; CHANGELOG в обоих файлах; ROADMAP.md перевыпущен после закрытия и перед коммитом.

## Plan

## Rollback

Обработчики MCP становятся транспортом над функциями CLI. Откат: git revert. Поверхность из 117 инструментов сохраняет имена и схемы — меняется только тело обработчика, поэтому клиенты не ломаются ни при внедрении, ни при откате.

## Journal

- 2026-09-06T13:29:18Z [implementation] — ИНВЕНТАРЬ СНЯТ ЗАМЕРОМ ПО AST, ДО ЕДИНОЙ ПРАВКИ (AC-1). Разобраны все harness/claude/mcp/project/handlers*.py вместе с ТАБЛИЦАМИ ДИСПЕТЧЕРИЗАЦИИ (*_HANDLERS), а не только функции _do_*: в таблицах 105 инструментов. ТРИ КРИТЕРИЯ, И ДВА ИЗ НИХ ОКАЗАЛИСЬ НЕГОДНЫМИ — записываю, чтобы их не пробовали снова. (1) «Больше одного стейтмента или есть ветвление» даёт 69 из 105: ловит разбор аргументов (тернарник над args.get), который задача ЯВНО разрешает обработчику. (2) «Строит текст (f-строка/join/format)» даёт 56: ловит конверт ошибки `return f"Error: {e}"` в handlers_spec/handlers_adapt — это сериализация, а не вторая реализация. (3) ГОДНЫЙ: «строит текст ИЗ РЕЗУЛЬТАТА вызова svc» — имена, вытекающие из вызова с участием svc, распространяются по присваиваниям и циклам (rows = svc.x(); for r in rows), исключаются имена исключений и всё, что выведено только из args. Даёт 17. СЕМНАДЦАТЬ ВТОРЫХ РЕАЛИЗАЦИЙ, у каждой есть двойник в CLI: tausik_events (_handle_events), tausik_memory_archive, tausik_memory_dedupe, tausik_memory_graph, tausik_memory_lint, tausik_memory_related, tausik_memory_search, tausik_memory_show, tausik_metrics, tausik_roadmap, tausik_search, tausik_session_current, tausik_task_logs, tausik_task_next, tausik_task_show, tausik_team, tausik_verify. ЧТО ТРОГАТЬ НЕ НАДО: 24 записи таблиц — тонкие лямбды прямо к svc.<method>, это уже транспорт; handlers_spec.py и handlers_adapt.py целиком — делегирование плюс конверт ошибки. ЖИВОЕ РАСХОЖДЕНИЕ, ПОДТВЕРЖДЁННОЕ ЧТЕНИЕМ ОБЕИХ СТОРОН: tausik_task_next печатает ЧИСЛО отложенных задач, а project_cli_task.py:246 печатает их СПИСОК (первые пять и «...»). Агент через MCP не видит, чего именно ждёт план. Докстринг обработчика при этом утверждает, что «This handler and the CLI print the same three states» — утверждение неверно ровно в той детали, ради которой отчёт заводился.
- 2026-09-06T13:49:09Z [implementation] — СХЛОПНУТО 13 ИЗ 17, ОСТАТОК ОБЪЯВЛЕН ПОИМЁННО (правка к AC-2, а не тихое сужение). Общие рендереры: render_task (next, logs), render_status (search, events, team), render_memory (list, show, search, related, graph, archive, dedupe, lint), render_session (current), render_hierarchy (roadmap). ОБЕ поверхности зовут их — детектор видит только сторону MCP, поэтому CLI переписан вручную и проверен ПРОГОНОМ, а не формой. ЧТО ВСКРЫЛОСЬ ПРИ СХЛОПЫВАНИИ (каждый случай — потеря на стороне MCP, то есть у ОСНОВНОГО читателя): task_next печатал число отложенных вместо имён; task_logs резал метку времени до минут и печатал пустые скобки; search обрезал каждую область до 10 и терял FTS-сниппет; events не имел свёртки и терял details; memory list/search теряли теги, search — origin_project; memory show терял created_at, теги и задачу; memory graph терял confidence и дату потери силы; archive/dedupe/lint теряли подсказку следующего шага. НЕ СХЛОПНУТО ТРИ, У КАЖДОГО НАЗВАН ВЛАДЕЛЕЦ (AC-4: чужое не поглощаем, своё не умалчиваем): task_show — задача mcp-task-show-hides-the-fields-the-agent-is-judged-by (эпик landscape-2026-h2, её AC1 буквально про этот перечень полей); metrics — заведена mcp-metrics-answers-one-line-where-cli-prints-the-report; verify — заведена mcp-verify-is-a-second-command-not-a-second-rendering (это не рендеринг, а вторая КОМАНДА: объявление relevant_files, кэш, квитанция, дескриптор, код выхода; схлопывание есть перепроектирование пути закрытия по QG-2). Обе новые задачи в истории evidence-primitives, то есть ОБЪЁМ РЕЛИЗА РАСТЁТ на 3 (включая дефект карты) — предъявлю владельцу цифрами в решении смены. МУТАЦИИ: 8 объявлено, 6 убито сразу, ДВА ВЫЖИВШИХ РАЗОБРАНЫ ДО КОНЦА. (1) «имена исключений считаются результатом» выжила, потому что вычитание excs было МЁРТВЫМ: имя из `except ... as e` связывается ExceptHandler-ом, а не Assign-ом, и в res не попадает никогда. Удалил вычитание и написал в исходнике, почему его нет, — не стал прикрывать тестом код, который ничего не делает. (2) «f-строка не считается рендерингом» выжила, потому что после схлопывания все три оставшихся в базовой линии рендерят через .join, и ветка JoinedStr на живом дереве больше не исполняется. Добавил юнит на функцию, которая рендерит ТОЛЬКО f-строкой, — мутация убита по ветви. Мутатор жил в подкаталоге scratchpad и удалён сразу. НЕ ЛОВИТСЯ И ЭТО ЧЕСТНО СКАЗАНО: мутация ФОРМАТА внутри общего рендерера меняет обе поверхности одинаково, поэтому parity-тесты её не видят — и не должны: их предмет совпадение поверхностей, а не конкретный текст.
- 2026-09-06T13:54:07Z [implementation] — AC verified: 1. ✓ инвентарь снят ЗАМЕРОМ по AST со всех handlers*.py вместе с таблицами диспетчеризации (105 инструментов), два негодных критерия отвергнуты с цифрами, годный дал 17, у каждого назван CLI-двойник — записано в журнал ДО правок. 2. ✓ схлопнуто 13 пар в общие рендереры render_task/render_status/render_memory/render_session/render_hierarchy, зовут их ОБЕ поверхности; каждое вскрытое расхождение названо поимённо (task_next печатал число вместо имён — живой случай из постановки). 3. ✓ гейт tests/test_mcp_handlers_are_transport.py ВЫВОДИТ множество по AST и держит базовую линию: рост краснеет (test_no_new_second_implementation), сжатие ОБЯЗАТЕЛЬНО (test_the_baseline_only_shrinks — краснел по-настоящему после каждого схлопывания, пока линия не обновлена); негативы: обработчик, рендерящий результат, ловится; конверт ошибки и разбор аргументов НЕ ловятся; нечитаемое дерево даёт ОТКАЗ, а не ноль. Плюс доказательство ПРОГОНОМ: три теста гоняют обе поверхности на одной БД и сверяют вывод. 4. ✓ границы удержаны: task_show оставлен своей задаче mcp-task-show-hides-the-fields-the-agent-is-judged-by, metrics и verify заведены отдельными задачами с причиной, храповик потерь остаётся за ratchet-for-mcp-cli-surface-parity; остаток объявлен в базовой линии комментарием у каждого элемента. 5. ✓ полный прогон 9094 passed / 27 skipped, mypy Success (353 файла), ruff All checks passed, bootstrap --check без дрейфа после --ide all; 8 мутаций объявлено, 6 убито сразу, 2 выживших разобраны до конца (мёртвое вычитание удалено; ветка f-строки закрыта юнитом и мутация убита по ветви); CHANGELOG.md и CHANGELOG.ru.md обновлены оба; ROADMAP.md перевыпущен.
