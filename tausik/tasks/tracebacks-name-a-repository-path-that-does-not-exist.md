---
slug: tracebacks-name-a-repository-path-that-does-not-exist
title: "Трассировки называют путь репозитория, которого не существует: устаревшие .pyc пережили переезд дерева и врут об именах файлов"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: "pytest-конфигурация (addopts, PYTHONDONTWRITEBYTECODE) НЕ меняется — скорость ленты не мерилась; vendors/, research/, .tausik/ чистке не подлежат никогда"
relevant_files:
  - "scripts/pyc_hygiene.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/project_parser.py"
  - "tests/test_pyc_hygiene.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/pyc_hygiene.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/project_parser.py"
  - "tests/test_pyc_hygiene.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T16:30:59Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО ЗАМЕРОМ В СЕССИИ #187, ПОБОЧНО. При разборе падений полной ленты под xdist сторож зависаний напечатал трассировку, в которой файл теста назван так:

  File "D:\Work\Personal\claude\tests\test_bootstrap_skills_coverage.py", line 41 in _run_bootstrap

Этого пути НЕ СУЩЕСТВУЕТ. Проверено: os.path.realpath('.') даёт D:\Work\Kibertum\clients\kibertum\tausik\core; каталога D:\Work\Personal\claude в файловой системе нет; junction/симлинка на пути тоже нет (dir /AL — File Not Found). То есть трассировка называет адрес, по которому ничего не лежит.

ПРИЧИНА, ГИПОТЕЗА ПЕРВОГО ПОРЯДКА (проверить, а не принять): co_filename кэшированного байт-кода. Репозиторий когда-то жил по адресу D:\Work\Personal\claude, .pyc были скомпилированы там, дерево переехало, а tests/__pycache__/*.pyc остались. Python валидирует .pyc по mtime и размеру ИСХОДНИКА, а не по его пути, поэтому кэш считается годным, и код-объект приносит с собой СТАРОЕ имя файла. В дереве такие .pyc видны глазами: tests/__pycache__/test_gates.cpython-311-pytest-9.0.2.pyc и соседние с разными версиями pytest, то есть кэш копился долго.

ЧЕМ ЭТО ПЛОХО, А НЕ КОСМЕТИКА. Диагностика падения — это чтение трассировки. Трассировка, называющая несуществующий файл, отправляет читателя искать файл, которого нет, и первое, что он заподозрит, — что тест лежит в другом дереве или что запущено не то. В этой самой сессии на проверку этого ушёл отдельный заход. Проект держит нулевую толерантность к тихим ошибкам; трассировка, врущая об адресе, — ровно такая ошибка, только она врёт не о факте, а о том, где факт искать.

ЧТО ПРОВЕРИТЬ ДО КОДА (ЗАМЕРОМ, НЕ РАССУЖДЕНИЕМ):
1) Подтвердить причину: прочитать co_filename из подозрительного .pyc напрямую и сверить с путём исходника. Если совпадения нет — причина названа верно.
2) Сколько таких .pyc в дереве и в каких каталогах (tests/, scripts/, bootstrap/, зеркала IDE).
3) Влияет ли устаревший кэш на ЧТО-ТО кроме имён в трассировках — например, на гейт размера файла, на аудит неиспользуемого кода, на поиск. Мерить вызовом.
4) Отдельно: не попадают ли __pycache__ в какой-нибудь обход дерева, который мы считаем чистым.

ВОЗМОЖНЫЕ ЛЕЧЕНИЯ, ВЫБИРАТЬ ПОСЛЕ ЗАМЕРА, А НЕ СЕЙЧАС: разовая чистка __pycache__ (лечит сегодня, не удерживает); PYTHONDONTWRITEBYTECODE / -p no:cacheprovider в лентах (меняет скорость, надо мерить); гейт, краснеющий на .pyc, чей co_filename не совпадает с деревом (удерживает, но стоит прогона); признать это фактом окружения и записать в память как gotcha. Ни один вариант не выбран.

СВЯЗЬ: найдено при работе над full-lane-runs-serial-on-a-twenty-core-machine, но к ней НЕ относится и её не блокирует — сами падения объясняются сторожем зависаний, а не кэшем.

## Acceptance Criteria

AC1 ПРИЧИНА ПОДТВЕРЖДЕНА ЗАМЕРОМ, НЕ ПРИНЯТА: co_filename прочитан из .pyc напрямую (marshal). Цифры #207: 2561 .pyc в дереве (без vendors/research), 543 с каталогом, не совпадающим с каталогом исходника после normpath, из них 527 указывают на несуществующее дерево d:\work\personal\claude (tests 432, scripts 69, bootstrap 16, hooks 6, harness 4); 16 — относительные пути, не ложь. Теги: cpython-311/313/314, pytest 8/9 — кэш копился месяцами.
AC2 ДЕРЖАЩАЯ ПРОВЕРКА, А НЕ РАЗОВАЯ ЧИСТКА: новый модуль scripts/pyc_hygiene.py — stale_bytecode(root) перечисляет .pyc, чей co_filename не резолвится в каталог рядом с __pycache__; doctor печатает раздел с числом и первыми именами и называет лекарство (`tausik doctor --fix-bytecode` или команда удаления); чистка удаляет ТОЛЬКО перечисленные файлы (интерпретатор пересоздаёт их сам), никогда не трогает vendors/research/.tausik.
AC3 ПОСЛЕ ЧИСТКИ: stale = 0 (цифра в журнале), полная лента зелёная с перекомпиляцией; замер «влияет ли кэш на что-то кроме трассировок»: filesize/class_surface/audit ходят по исходникам и __pycache__ исключают — проверено grep по вызовам и записано.
AC4 ТЕСТЫ tests/test_pyc_hygiene.py на СИНТЕТИКЕ: исходник компилируется в tmp/a/, кэш переносится под tmp/b/ — детектор называет файл; свежий кэш рядом с исходником — не называет; относительный co_filename — не ложь; чистка удаляет только названное и отчитывается числом; doctor-раздел зелёный при нуле и красный при одном.
AC5 МУТАЦИИ: снять normpath-сравнение; чистить всё подряд; раздел doctor молчит при stale>0 — каждая убита названным тестом.
AC6 scoped verify, полная лента один раз (строка passed/failed), ruff/mypy чисто, CHANGELOG.md и CHANGELOG.ru.md синхронно, docs/ru доктора обновлены, bootstrap --ide all перед done. Сложность: medium (доктор, новый модуль, CLI-флаг, тесты) — оценено ПОСЛЕ инвентаря.

## Plan

## Rollback

Чистка устаревших .pyc и защита от их появления. Откат: git revert для кода; удалённые .pyc восстанавливаются самим интерпретатором при следующем запуске, потерять нечего.

## Journal

- 2026-09-03T16:24:53Z [implementation] — ЗАМЕР ПО ПУНКТАМ ЗАДАЧИ: (1) причина подтверждена чтением co_filename через marshal: 543 из 2561 .pyc несут каталог, не совпадающий с владельцем __pycache__ после normpath, 527 — несуществующее дерево d:\work\personal\claude, 16 — относительные пути (не ложь); теги cpython-311/313/314, pytest 8/9. (2) По каталогам: tests 432, scripts 69, bootstrap 16, hooks 6, harness/mcp 4. (3) Влияние на прочее: 12 модулей scripts/ упоминают __pycache__ — все как исключение при обходе (filesize, class_surface, bootstrap_check, drift); гейты ходят по исходникам; кэш влияет только на co_filename в трассировках. (4) Обходы дерева, считающиеся чистыми, __pycache__ не включают. Живой doctor из исходников: WARN «527 .pyc name a directory that is not theirs» с лекарством --fix-bytecode. МУТАЦИИ 5/5 УБИТЫ: normpath снят; purge чистит всё подряд; раздел doctor молчит; относительный путь как stale; read-only деревья обходятся — каждая названным тестом test_pyc_hygiene.py.
- 2026-09-03T16:26:36Z [implementation] — ОШИБКА ПО ХОДУ (память #527, потребители): инвентарь вызывающих cmd_doctor снял grep по scripts/ — ноль — и написал args.fix_bytecode напрямую; 11 тестов doctor зовут cmd_doctor с голым namespace без поля -> AttributeError. Потребители функции живут и в tests/. Возвращён getattr с умолчанием False; файл doctor ровно 500 строк (гейт: > 500).
- 2026-09-03T16:29:50Z [implementation] — Root cause (config-error): кэш байт-кода пережил переезд дерева — CPython валидирует .pyc по mtime и размеру исходника, а не по пути, и co_filename старого адреса жил в трассировках месяцами; ни один контроль не читал co_filename. Prevention: doctor читает co_filename и сравнивает КАТАЛОГ с владельцем __pycache__ после нормализации; чистка только по списку; проверка держится в каждом прогоне doctor. Verification checklist: AC-1: ✓ замер в журнале (2561/543/527). AC-2: ✓ tests/test_pyc_hygiene.py::TestDoctorRow::test_warns_names_the_old_tree_and_the_remedy. AC-3: ✓ живой doctor --fix-bytecode: purged 527 of 527, после — «none»; полная лента 8632 passed / 25 skipped / 0 failed (строка прочитана). AC-4: ✓ tests/test_pyc_hygiene.py::TestDetection::test_a_cache_carried_to_another_tree_names_the_old_path. AC-5: ✓ мутации 5/5 в журнале. AC-6: ✓ verify green, ruff/mypy чисто, docs/ru+en cli.md, CHANGELOG.md + CHANGELOG.ru.md, bootstrap выполнен. Domain: следующая трассировка из tests/ назовёт файл, который существует; doctor красен, если кэш снова переедет.
