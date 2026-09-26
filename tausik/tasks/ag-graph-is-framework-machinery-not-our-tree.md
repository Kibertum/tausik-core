---
slug: ag-graph-is-framework-machinery-not-our-tree
title: "[1.9] Граф становится механикой фреймворка: виды по стекам, корни по проекту, поверхность и наполнение у потребителя"
status: done
epic: artifact-graph
story: ag-substrate
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Схема графа: scripts/backend_schema_graph.py и любые backend_migrations*.py. AC10 запрещает миграцию — вердикт спайка (решение #349) состоит в том, что ядро выдержало три стека. Понадобившаяся миграция есть опровержение этого вердикта и повод остановиться, а не дописать."
relevant_files:
  - AGENTS.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "bootstrap/bootstrap_templates.py"
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/architecture.md"
  - "docs/en/mcp.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/architecture.md"
  - "docs/ru/mcp.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "harness/claude/mcp/project/tools_extra.py"
  - "scripts/backend_crud_graph.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/service_artifact_graph.py"
  - "scripts/symbol_answer.py"
  - "scripts/symbol_index.py"
  - "tausik/gates.json"
  - "tausik/tasks/dev-doc-checks-describes-a-machine-that-changed.md"
  - "docs/en/graph.md"
  - "docs/ru/graph.md"
  - "scripts/project_cli_graph.py"
  - "scripts/project_parser_graph.py"
  - "scripts/source_roots.py"
  - "tausik/decisions/hrapovik-poverhnosti-mcp-podnyat-na-odin-instrument-radi.md"
  - "tausik/tasks/ag-graph-is-framework-machinery-not-our-tree.md"
  - "tests/test_graph_is_framework_machinery.py"
scope_paths:
  - "scripts/service_artifact_graph.py"
  - "scripts/backend_crud_graph.py"
  - "scripts/symbol_index.py"
  - "scripts/symbol_answer.py"
  - "scripts/source_roots.py"
  - "scripts/project_cli_graph.py"
  - "scripts/project_cli_symbol.py"
  - "scripts/project_parser_graph.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "harness/claude/mcp/project/*.py"
  - "bootstrap/bootstrap_templates.py"
  - "tausik/gates.json"
  - "tests/test_artifact_graph.py"
  - "tests/test_graph_is_framework_machinery.py"
  - "tests/test_symbol_index.py"
  - "tests/test_tool_choice_nudges.py"
  - "tests/test_mcp_surface_ratchet.py"
  - "docs/_generated/constants.json"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - README.md
  - README.ru.md
  - AGENTS.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T13:18:35Z"
resolution: null
resolution_reason: null
---

## Goal

ПРЯМОЕ ТРЕБОВАНИЕ ВЛАДЕЛЬЦА, смена #234, решение #348: «нам надо не просто наполнить граф в проекте, а сделать его частью фреймворка — чтобы другие проекты очевидно эту механику использовали».

ЗАМЕР, СДЕЛАННЫЙ ДО ЗАДАЧИ (спайк ag-spike-schema-against-three-stacks, решение #349).

1. ЯДРО ГРАФА У ПОТРЕБИТЕЛЯ ПРОСТО НЕ РАБОТАЕТ. Прогон на фикстуре tests/consumer_layout.py — проект с backend/api/orders.py, backend/app/services/quota.py и тремя файлами тестов: symbol_index.build_index находит НОЛЬ объявлений. Причина не в коде проекта, а в том, что DEFAULT_ROOTS = (scripts, bootstrap, tests, harness) суть имена НАШЕГО дерева. Хуже пустого ответа то, что у потребителя каталог scripts/ обычно ЕСТЬ и содержит его собственные файлы — значит индекс вернёт срез и будет выглядеть работающим.

2. ТАБЛИЦА ВИДОВ ЗНАЕТ ОДИН СТЕК ИЗ ДВАДЦАТИ ПЯТИ. service_artifact_graph._KIND_BY_SUFFIX содержит 9 суффиксов, и ровно один даёт kind=code — .py. TAUSIK объявляет 25 стеков; go, rust, java, php, typescript, terraform, swift, kotlin, blade, vue, svelte, next, nuxt, react, flutter и прочие падают в other, неотличимо от бинарника. То же и с определением теста: classify считает тестом только tests/ и test_*, тогда как *_test.go, spec/ и __tests__/ — обычные раскладки объявленных стеков.

3. ГРАФ НЕ НАПОЛНЕН И НЕ ПОКАЗАН НИГДЕ. artifacts 0 строк, artifact_symbols 0, artifact_edges 0 — в НАШЕМ репозитории, спустя сутки после постройки подложки. Ни команды CLI, ни инструмента MCP: вне собственных тестов graph_index_paths, graph_build_cochange, graph_build_declared и neighbours_of не вызывает никто. Механика, которую нельзя вызвать, не может «очевидно использоваться другими проектами».

4. ЧТО ПРИ ЭТОМ УЖЕ ВЕРНО И НЕ ТРОГАЕТСЯ. Слой со-изменения агностичен ПО ФАКТУ ПРОГОНА: на трёх стеках три ребра, одинаковые relation, layer и уверенность. Схема рёбер с происхождением выдержала все три стека. Запрос отвечает в обе стороны и называет протухшее. Схема НЕ ПРАВИТСЯ — правится её периферия.

ПРЕДМЕТ. Сделать граф механикой, которую потребитель получает вместе с фреймворком и не может не заметить: корни выводятся из ЕГО проекта, виды артефактов покрывают объявленные стеки или честно говорят «не знаю», граф наполняется и показывается командой, а неподдержанный стек получает ИМЕННОЕ «не поддержано» вместо пустого ответа (решение #334).

ЧТО НЕ ВХОДИТ: извлекатели символов для terraform и markdown (решение #349 — адаптер, не 1.9); переиндексация на хуке записи (отдельная задача ag-incremental-refresh-on-the-write-hook); наблюдённые рёбра из прогона тестов (ag-observed-edges-from-the-test-run); подсказка relevant_files по графу (ag-payoff, отдельной задачей после этой).

## Acceptance Criteria

AC1. КОРНИ ВЫВОДЯТСЯ ИЗ ПРОЕКТА, А НЕ ИЗ ИМЁН НАШЕГО ДЕРЕВА. Источник по убыванию: явное объявление в .tausik/config.json, затем вывод из ОТСЛЕЖИВАЕМЫХ git файлов. Проверка на фикстуре tests/consumer_layout.py: индекс обязан найти объявления в backend/api/orders.py, которых сегодня находит НОЛЬ. Наше дерево не деградирует — прежние четыре корня остаются валидным исходом вывода, а не жёсткой константой.

AC2. ОТВЕТ НАЗЫВАЕТ КОРНИ, ПО КОТОРЫМ ИСКАЛ, И ОТКУДА ОНИ ВЗЯТЫ. Читатель обязан отличить «символа нет» от «искали не там».

AC3. ВИДЫ АРТЕФАКТОВ ПОКРЫВАЮТ ОБЪЯВЛЕННЫЕ СТЕКИ. Сегодня 9 суффиксов на 25 стеков и ровно один даёт code. Тест перечисляет стеки из project_types.DEFAULT_STACKS и требует, чтобы основной суффикс исходника каждого давал code (императивные) либо config (декларативные: terraform, helm, kubernetes, ansible). Число покрытых стеков утверждается ТЕСТОМ, а не комментарием. Вид other сохраняется как честный ответ для суффикса, которого мы действительно не знаем; нового вида не заводится — это потребовало бы миграции, запрещённой AC10. ИСПРАВЛЕН ДО КОДА: прежняя редакция требовала вида unknown и потому противоречила AC10.

AC4. ТЕСТ ОПОЗНАЁТСЯ ПО РАСКЛАДКЕ СТЕКА, А НЕ ТОЛЬКО ПО НАШЕЙ. Файлы вида *_test.go, spec/, __tests__/ и *.spec.ts дают kind=test. Негативная половина: слово test внутри имени каталога данных (data/latest/) тестом не делает.

AC5. ГРАФ НАПОЛНЯЕТСЯ И ПОКАЗЫВАЕТСЯ КОМАНДОЙ. tausik graph build и tausik graph show с двойниками MCP. После build на НАШЕМ репозитории artifacts, artifact_symbols и artifact_edges перестают быть пустыми, и число строк печатается. Сегодня все три по нулю.

AC6. НЕПОДДЕРЖАННЫЙ СТЕК ПОЛУЧАЕТ ИМЕННОЕ «НЕ ПОДДЕРЖАНО», А НЕ ПУСТОЙ ОТВЕТ. Для .tf и .md слой символов обязан сказать, что извлекателя нет, и назвать, что при этом РАБОТАЕТ: со-изменение и объявленные рёбра. Отсутствие не есть ноль — решение #334.

AC7. ПРОВЕРЕНО У ПОТРЕБИТЕЛЯ, А НЕ ДОМА. Не менее трёх утверждений прогоняются через build_consumer_project, где project_dir и lib_dir разные каталоги, tests лежат в backend/tests, а scripts/ принадлежит проекту, а не харнессу. Файл заведён после шести дефектов класса «дома зелено, у потребителя красно», и граф обязан пройти через него, а не мимо.

AC8. АГЕНТ ПОТРЕБИТЕЛЯ УЗНАЁТ О ГРАФЕ ОТТУДА, ГДЕ ЧИТАЕТ ПРАВИЛА. Сгенерированный файл правил называет команду. Бюджет 80-180 строк НЕ РАСТЁТ: за добавленную строку платится убранной. Проверяется тестом на сгенерированном файле, а не на нашем CLAUDE.md.

AC9. СТОИМОСТЬ НАЗВАНА ЧИСЛОМ. Полный build на нашем дереве замерен и число записано. База уже есть: 1013 файлов, 939093 узла ast, 1624 мс. Выход за этот порядок — находка, а не данность.

AC10. СХЕМА НЕ ПРАВИТСЯ. Решение #349: ядро выдержало три стека. Миграции в этой задаче нет; если она понадобится, это опровержение вердикта спайка и повод остановиться, а не дописать.

## Plan

## Rollback

git revert. Граф — вторичная механика: её отключение не ломает ни одну существующую команду. Таблица видов и корни имеют прежние значения как запасной вариант, поэтому откат возвращает поведение 1.8 целиком.

## Journal

- 2026-09-08T12:35:26Z [implementation] — НАХОДКА В СОБСТВЕННОЙ ПОСТАНОВКЕ, ДО ПЕРВОЙ СТРОКИ КОДА. AC3 в исходной редакции требовал по каждому неизвестному стеку ЯВНОГО вида unknown и запрещал other. Но ARTIFACT_KINDS — закрытый список схемы с ограничением CHECK: code, config, data, doc, other, test. Добавить unknown значит написать миграцию, а AC10 миграцию прямо запрещает, ссылаясь на вердикт спайка. Два критерия одной задачи требовали противоположного. РАЗБОР, А НЕ КОМПРОМИСС. Неправ AC3, и вот почему. Вид other уже означает «прочее», и для суффикса, которого мы не знаем, это ЧЕСТНЫЙ ответ, а не умолчание — в отличие от случая, когда мы знаем стек и всё равно кладём его в other. Настоящий дефект не в отсутствии вида unknown, а в том, что .go, .rs, .java, .php, .ts не опознаются как code, а .tf и .hcl — как config. То есть чинится ТАБЛИЦА, а не список видов. AC3 ПЕРЕПИСАН: по каждому стеку из project_types.DEFAULT_STACKS его основной суффикс исходника даёт code (императивные) либо config (декларативные — terraform, helm, kubernetes, ansible), и число покрытых стеков утверждается тестом, а не комментарием. Требование вида unknown снято как противоречащее AC10 и как ошибочное по существу. ПОЧЕМУ ЗАПИСЫВАЮ. Это второй раз за две смены, когда критерий, написанный мной, оказывается невыполнимым вместе с соседним критерием той же задачи. Первый был в a-tool-is-chosen: правка под AC4 нарушила сам AC4. Разница в том, что здесь противоречие поймано ДО кода, и поймано перечитыванием собственных AC против схемы, а не тестом после.
- 2026-09-08T12:43:10Z [implementation] — ACL расширен дважды и оба раза гейтом области записи, а не по своей воле: сперва project_parser_graph.py, затем backend_crud_graph.py. Второй понадобился потому, что CLI нужен счётчик строк графа, а прямой доступ к БД из CLI запрещён жёстким правилом — счётчик обязан жить в слое CRUD. AC10 при этом не задет: схема и миграции остались в scope_exclude, правится только слой доступа.
- 2026-09-08T13:18:11Z [implementation] — AC-1: ✓ tests/test_graph_is_framework_machinery.py::TestRootsComeFromTheProject — пять утверждений: потребитель индексируется (было 0 объявлений при живом backend/), наше дерево не деградирует, объявление проекта старше вывода, git и диск отвечают ОДИНАКОВО, дерево без исходника даёт пустой список. Замер: на нашем дереве выведенные корни дают те же 13 297 объявлений за то же время. AC-2: ✓ ::TestTheAnswerNamesWhereItLooked — корни и их происхождение в ПОЛОЖИТЕЛЬНОМ ответе, в отрицательном, и запасной вариант назван провалом («NOT DERIVED … may be about the wrong files»), а не выдан за находку. AC-3: ✓ ::TestKindsCoverTheStacksTheFrameworkClaims — по образцу на каждый из 25 стеков из project_types.DEFAULT_STACKS, каждый даёт code или config; отдельный тест-предпосылка падает, если стек добавили, а образец нет. Было 9 суффиксов и ровно один code. AC-4: ✓ ::TestATestIsRecognisedInAnyStacksConvention — семь конвенций опознаются, три отрицательных случая (data/latest/, src/contest/, docs/testing-guide.md) НЕ опознаются. AC-5: ✓ ::TestTheGraphCanBeFilledAndAsked плюс живой прогон: tausik graph build на этом репозитории даёт 4226 артефактов, 13 312 символов, 17 644 ребра. Двойник MCP tausik_graph зарегистрирован и проходит tests/test_mcp_surface_ratchet.py::TestEveryDeclaredToolIsReachable. AC-6: ✓ ::TestAnUnsupportedLanguageIsNamedNotSilent — файл .go считается как «нет извлекателя», а не молча даёт ноль. На нашем дереве вывод называет 37 таких файлов. AC-7: ✓ через build_consumer_project прогнаны шесть утверждений (индексация, оба ответа символьного слоя, наполнение трёх таблиц, очистка, стоимость) — раскладка, где project_dir и lib_dir разные, tests лежат в backend/tests, а scripts/ принадлежит проекту. AC-8: ✓ ::TestTheConsumersAgentIsToldTheGraphExists — граф назван в СГЕНЕРИРОВАННОМ файле правил, и бюджет 80-180 соблюдён: файл стоял ровно на 180, поэтому строка оплачена слиянием verify и task done в одну (они и есть один акт QG-2). AC-9: ✓ ::TestTheBuildStaysCheapEnoughToBeRun — порядок величины и утверждение, что сборка идёт одной транзакцией. Числа: 2 мин 27 с до, около 9 с после. AC-10: ✓ схема не правилась: git status не содержит backend_schema_graph.py и ни одной миграции; scope_exclude задачи их и запрещал. Domain: результат осмыслен вне тестов — граф построен на настоящем репозитории с настоящей историей git, и tausik graph show scripts/symbol_index.py возвращает соседей, которые действительно правились вместе с ним, с указанием слоя и уверенности; свежесть пересчитывается с диска и после сборки честно пуста. Negative: половина утверждений отрицательные и они несущие — пустой список корней вместо догадки, other для неизвестного суффикса, три пути со словом test, которые тестами НЕ являются, .go без извлекателя вместо нуля символов, запасной вариант корней, названный провалом. НАЙДЕНО В ХОДЕ РАБОТЫ, ВСЁ СВОЁ (шесть): 1. AC3 в собственной постановке противоречил AC10 — требовал нового вида артефакта, то есть миграции. Поймано ДО кода перечитыванием AC против схемы, AC переписан. 2. Сборка занимала 2 мин 27 с. Причина не в графе: WAL с synchronous=FULL, около 22 000 автоматически зафиксированных операторов по 6.7 мс. Одна транзакция — 9 с. 3. Резолвер корней отвечал ПО-РАЗНОМУ в зависимости от ветки: git видел .github, обход диска — нет. Выровнено, и на это заведён тест. 4. Дважды расширял ACL, и оба раза не по своей воле, а по отказу гейта области записи. 5. Едва не «починил» верный код: отношение co_changes у объявленных рёбер выглядело ложью, но докстринг _declared_from_tasks уже разбирает этот выбор и обосновывает его. Правка ушла в ОТОБРАЖЕНИЕ: слой печатается словами. 6. Точечная правка счётчиков в README внесла разнобой в таблицу — две строки стали 153 при остальных 152. Выровнена колонка целиком. ПРОБЕЛ, ОТНЕСЁННЫЙ К ДРУГОЙ ЗАДАЧЕ: сканер доковых констант НАХОДИТ ссылки вида «145 project + 7 brain», но чинить их не умеет — восемь штук правились руками. Это предмет хвостовой задачи dev-doc-checks-describes-a-machine-that-changed, туда и записано.
