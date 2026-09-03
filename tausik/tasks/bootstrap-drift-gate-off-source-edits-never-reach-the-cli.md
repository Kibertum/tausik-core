---
slug: bootstrap-drift-gate-off-source-edits-never-reach-the-cli
title: "Гейт bootstrap_drift ВЫКЛЮЧЕН — правка в scripts/ не доезжает до работающего CLI и MCP, и об этом никто не узнаёт"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "scripts/gate_registry.py и gate_runner.py: новый гейт НЕ заводится, третье звено живёт внутри существующего bootstrap_drift (одна проверка одной цепи); mcp_reaper.py: перезапуск/убийство процессов не делается (решение #189 — только сообщать)"
relevant_files:
  - "scripts/running_source_drift.py"
  - "scripts/gate_bootstrap_drift.py"
  - "harness/claude/mcp/project/server.py"
  - "tests/test_running_source_drift.py"
  - "tests/test_bootstrap_drift_gate.py"
  - "docs/ru/architecture.md"
  - "docs/en/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/running_source_drift.py"
  - "scripts/gate_bootstrap_drift.py"
  - "harness/claude/mcp/project/server.py"
  - "tests/test_running_source_drift.py"
  - "tests/test_bootstrap_drift_gate.py"
  - "docs/ru/*.md"
  - "docs/en/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T15:52:51Z"
---

## Goal

НАЙДЕНО ЗАМЕРОМ #191-БД, ПОБОЧНО. Закрыв задачу о новом гейте claudemd_state_drift, я увидел, что он НЕ ПОЯВИЛСЯ в списке гейтов task-done, хотя объявлен в scripts/gate_registry.py и его тесты зелёные. Причина: `.tausik/tausik` — обёртка, которая исполняет код из РАЗВЁРНУТОГО профиля (.claude/scripts/, первый существующий из claude/cursor/windsurf/codex/qwen/kilo/opencode), а не из scripts/. То же и у MCP-сервера. Правка в scripts/ вступает в силу только после `python bootstrap/bootstrap.py --ide all`. Записано памятью #438.

ЧТО ИМЕННО МОЛЧАЛО. Гейт bootstrap_drift существует ровно для этого («Fail if deployed IDE profiles drift from scripts/ source», severity=block, trigger=task-done) и в этом проекте стоит [OFF]. То есть страж, поставленный против «правка не вступила в силу», сам выключен, и отказ невидим: тесты зелёные (они импортируют из scripts/), гейты зелёные (они исполняются из .claude/), и обе стороны говорят правду о разном коде.

ЦЕНА, ЗАМЕРЕННАЯ, А НЕ ПРЕДПОЛОЖЕННАЯ. `bootstrap.py --check --ide all` показал 15 дрейфующих файлов в пяти профилях, и среди них НЕ ТОЛЬКО новый гейт: там gate_command_runner.py, то есть починка инъекции полной ленты (TAUSIK_VERIFY_FULL=1 подставляет -m '' вместо стирания addopts), УЖЕ ЗАКОММИЧЕННАЯ в 6b81b78, до работающего CLI не доехала. Закрытая и оплаченная работа лежала неисполняемой.

ЧТО ДЕЛАЕТСЯ: понять, ПОЧЕМУ гейт выключен (осознанное решение или тихий дефолт), и либо включить, либо заменить механизмом, который не требует ручного bootstrap. НЕГАТИВНОЕ, ОБЯЗАТЕЛЬНОЕ: правка scripts/gate_registry.py без последующего bootstrap обязана ОТКАЗАТЬ закрытие задачи, а не закрыть его зелёным — проверяется мутацией: внести правку в источник, не разворачивать, убедиться, что task-done краснеет.

СМЕЖНОЕ: claudemd-drift-gates-do-not-notice-an-emptied-dynamic-block (эта задача найдена внутри неё), claudemd-dynamic-block-wiped-to-an-empty-project.

## Acceptance Criteria

AC1 ПЕРЕДИАГНОЗ ЗАПИСАН ЦИФРАМИ: первое звено (гейт [OFF]) закрыто решением #287 — показано выводом gates status и списком гейтов task-done; задача чинит ТРЕТЬЕ звено — живой процесс со старым кодом.
AC2 НЕГАТИВНЫЙ, ОБЯЗАТЕЛЬНЫЙ: процесс, стартовавший из копии реального развёрнутого профиля (.claude/scripts, все .py), после изменения ОДНОГО файла в этой копии получает от run_bootstrap_drift_gate БЛОК, называющий файл и действие «перезапустить MCP-сервер / закрыть через CLI»; тот же гейт в свежем процессе — PASS. Замерено дочерним процессом, цифры в журнале.
AC3 ЛОЖНЫЙ БЛОК ИСКЛЮЧЁН ПО ПОСТРОЕНИЮ: сравнение по содержимому (sha1), а не по mtime — повторное развёртывание без изменений содержимого даёт PASS; __pycache__ и не-.py файлы не сравниваются (объявлено).
AC4 СНИМОК БЕРЁТСЯ ПРИ СТАРТЕ: явный вызов record_start в main() harness/claude/mcp/project/server.py (тест-храповик на текст сервера) плюс снимок при первом импорте; record_start идемпотентен — повторный вызов не сдвигает точку отсчёта (иначе гейт можно «обнулить» вызовом).
AC5 МУТАЦИИ: не менее четырёх (снять проверку из гейта; сравнивать mtime вместо хэша; сделать record_start не идемпотентным; убрать вызов из сервера) — каждая убита названным тестом.
AC6 ДОКУМЕНТАЦИЯ: докстринг gate_bootstrap_drift называет три звена; docs/ru гейтов обновлены; CHANGELOG.md и CHANGELOG.ru.md синхронно; остаток назван (каталог mcp/ сервера покрыт вторым корнем или объявлен непокрытым).
AC7 scoped verify зелёный, полная лента ОДИН раз в конце со строкой passed/failed, mypy и ruff чисто, bootstrap --ide all перед done.

## Plan

## Rollback

git revert коммита: гейт bootstrap_drift возвращается к двум звеньям (источник vs развёрнутый профиль), проверка живого процесса исчезает; ослабления защиты относительно #206 нет, миграций нет

## Journal

- 2026-08-30T20:18:02Z [planning] — [#191-БД] ВТОРОЙ СЛОЙ ТОГО ЖЕ ОТКАЗА, ЗАМЕРЕН ПРЯМО ПРИ ЗАКРЫТИИ ЗАДАЧИ: РАЗВЁРНУТЬ ПРОФИЛЬ НЕДОСТАТОЧНО, ПОКА ЖИВ СТАРЫЙ ПРОЦЕСС MCP. После `bootstrap --ide all` команда `.tausik/tausik gates status` (свежий процесс) показывает «[ON] claudemd_state_drift (block) -> task-done, commit». Но закрытие задачи ЧЕРЕЗ MCP в той же сессии дважды подряд отработало БЕЗ этого гейта: в списке шли filesize, class_surface, memory_route, renar_drift_schema, renar_drift_provenance, skill_spec_conformance — и всё. Причина: сервер MCP запущен ДО развёртывания и держит реестр гейтов в памяти своего процесса. СЛЕДСТВИЕ ДЛЯ ЭТОЙ ЗАДАЧИ: цепочка «правка в scripts/ → bootstrap → гейт действует» имеет ТРИ звена, а не два, и третье (перезапуск сервера MCP) сегодня не выражено нигде и не проверяется ничем. Агент, работающий по правилу MCP-first, получает зелёные закрытия по СТАРОМУ набору гейтов и не имеет способа это заметить: обе стороны молчат. ЧТО ЭТО ЗНАЧИТ ДЛЯ ОБЪЁМА ЗАДАЧИ: включить bootstrap_drift — необходимо, но НЕ достаточно. Нужен ещё признак «набор гейтов в работающем сервере отличается от набора в источнике», иначе останется ровно та же дыра, только на одно звено дальше. ПРОВЕРКА ДЛЯ СЛЕДУЮЩЕГО: сравнить вывод `.tausik/tausik gates status` (свежий процесс, читает развёрнутый профиль с диска) со списком гейтов в JSON-ответе tausik_task_done (живой процесс MCP). Расхождение = сервер устарел.
- 2026-09-03T15:42:22Z [planning] — [#207] ПЕРЕДИАГНОЗ ПО ПАМЯТИ #530: механизм в заголовке устарел. gates status (CLI, свежий процесс) и tausik_gates_status (живой MCP) ОБА показывают [ON] bootstrap_drift (block) -> task-done; гейт включён через закоммиченный tausik/policy.json решением #287 (задача this-repos-strictness-lives-in-a-gitignored-file), и на закрытии первой задачи #207 он прошёл в списке из 8 гейтов вместе с claudemd_state_drift. Первое и второе звено цепи «правка -> bootstrap -> гейт» закрыты чужой работой. ОСТАЁТСЯ ТРЕТЬЕ ЗВЕНО из заметки #191-БД: живой процесс MCP держит реестр гейтов и код обработчиков, загруженные ДО развёртывания, и ничем это не сообщает. Сегодня расхождения нет (17 гейтов там и там) — но это совпадение, а не механизм. ДИЗАЙН: новый модуль scripts/running_source_drift.py — снимок sha1 всех .py каталога, из которого работает процесс (для MCP это .claude/scripts, 379 файлов), берётся при старте (явно в main() сервера + при первом импорте); gate_bootstrap_drift сравнивает снимок с диском на task-done и БЛОКИРУЕТ с remedy «перезапусти MCP-сервер или закрой через CLI (свежий процесс)». Хэш, а не mtime: повторный bootstrap без изменений содержимого не должен давать ложный блок.
- 2026-09-03T15:46:54Z [implementation] — ЗАМЕР AC2 на КОПИИ реального развёрнутого профиля .claude/scripts (379 .py + новый модуль = 380): дочерний процесс стартует из копии, record_start, затем родитель дописывает одну строку в gate_registry.py копии -> run_bootstrap_drift_gate в дочернем: PASSED False, первая строка «Stale process: 1 file(s) ... changed AFTER it started», remedy «restart» назван. Свежий процесс после той же правки: строки «Stale process» НЕТ (третье звено чисто), гейт красен по ВТОРОМУ звену — 15 файлов реального .claude/ не совпадают с scripts/, потому что текущая правка ещё не развёрнута; это верный ответ гейта, а не ложный. СТОИМОСТЬ: снимок 380 файлов — 39-49 мс на тёплом кэше, 72 мс на реальном .claude/scripts; сравнение 40 мс. Первый прогон показал 2.0 с на снимок и 11 с на сравнение — первое касание свежескопированных файлов (антивирус/холодный кэш), одноразово, при повторе 40 мс. Оговорка: второй пробник без синхронизации READY «не увидел» правку — гонка пробника (правка легла до снимка), не дефект: пробник с READY правку видит, и тест test_a_real_child_process_sees_the_edit_made_under_it синхронизирован.
- 2026-09-03T15:48:29Z [implementation] — МУТАЦИИ 5/5 УБИТЫ, каждая названным тестом: (1) гейт не спрашивает changed_since_start — 2 теста TestGateThirdLink; (2) сравнение по mtime вместо содержимого — test_identical_rewrite_is_not_a_change; (3) record_start пересъёмка при каждом вызове — 4 теста, включая test_first_call_wins; (4) вызов record_start снят из main() сервера — test_the_server_pins_its_start_at_the_top_of_main; (5) добавленные/удалённые файлы не считаются — test_an_added_and_a_removed_file_are_both_named. Оговорка #536: мутации автора; ревью на починку обязательно. ОСТАТОК ОБЪЯВЛЕН: снимок только .py (JSON/MD/sh профиля не сравниваются); сервер, не вызвавший record_start, закрепляется храповиком на текст server.py, а не механикой.
- 2026-09-03T15:51:33Z [implementation] — Root cause (missing-validation): гейт bootstrap_drift сравнивал два состояния НА ДИСКЕ (источник и развёрнутый профиль) и не имел понятия о третьем — коде, загруженном в живой процесс; долгоживущий MCP-сервер после развёртывания исполнял старый реестр и обработчики, и ни один контроль об этом не говорил, потому что обе проверяемые стороны на диске совпадали. Prevention: у цепи «правка -> развёртывание -> действие» проверять каждое звено, включая процесс; точка отсчёта снимается при старте и не сдвигается вызовом; сравнение по содержимому, чтобы штатное развёртывание не давало ложного блока; лекарство называется в самом отказе.
- 2026-09-03T15:51:34Z [implementation] — AC-1: ✓ передиагноз в журнале: gates status и tausik_gates_status оба [ON] bootstrap_drift, включён policy.json (#287), список task-done из 8 гейтов включает claudemd_state_drift. AC-2: ✓ замер дочерним процессом на копии реального профиля (380 файлов): stale -> блок «Stale process» с именем файла и remedy restart; fresh -> третье звено чисто; плюс test_a_real_child_process_sees_the_edit_made_under_it. AC-3: ✓ tested via test_identical_rewrite_is_not_a_change, test_pycache_and_non_python_files_are_not_compared. AC-4: ✓ tested via test_the_server_pins_its_start_at_the_top_of_main, TestRecordStartIsAReference (3 теста). AC-5: ✓ мутации 5/5, перечень в журнале. AC-6: ✓ докстринг gate_bootstrap_drift называет три звена; docs/ru и docs/en architecture.md; CHANGELOG.md + CHANGELOG.ru.md синхронно; остаток (.py only, храповик на текст сервера) объявлен. AC-7: ✓ scoped verify #1989 PASS, полная лента 8584 passed / 25 skipped / 0 failed (строка прочитана), mypy чисто, ruff чисто по файлам задачи, bootstrap --ide all выполнен перед done. Domain: после развёртывания этой правки живой MCP-сервер этой сессии сам станет «stale» и любое закрытие через него будет отклонено с указанием перезапустить — ровно сценарий #191, теперь видимый; закрытие через CLI проходит.
