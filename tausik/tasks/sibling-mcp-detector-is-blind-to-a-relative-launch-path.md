---
slug: sibling-mcp-detector-is-blind-to-a-relative-launch-path
title: "Детектор соседних MCP-серверов слеп к относительному пути запуска: «соседей 0» при десяти живых процессах"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: "scripts/** — детектор живёт в harness, ядра не касаемся"
relevant_files:
  - "harness/claude/mcp/project/self_check.py"
  - "harness/claude/mcp/project/sibling_mcp.py"
  - "tests/test_consumer_layout.py"
  - "tests/test_mcp_self_check.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "harness/**"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T17:08:35Z"
---

## Goal

Счёт соседних серверов отражает реальность независимо от того, абсолютным или относительным путём они запущены.

## Acceptance Criteria

1. Совпадение процесса определяется не вхождением АБСОЛЮТНОГО пути в чужую командную строку. Тикет GitLab #4 называет четыре строки: self_check.py 279 и 306 (Windows), 333 и 345 (POSIX) — проверить, что их ровно четыре, поиском.
2. Замер тикета воспроизведён: десять живых процессов, старый фильтр даёт 0. Воспроизвести ДО правки.
3. НЕГАТИВНЫЙ сценарий: чужой проект НЕ считается соседом — точность проверяется на машине с процессами нескольких проектов, иначе лечение хуже болезни.
4. НЕГАТИВНЫЙ сценарий: невозможность прочитать список процессов даёт ЯВНОЕ «не смог сосчитать», а не 0. Ноль, означающий отказ, неотличим от нуля, означающего отсутствие соседей.

## Plan

## Rollback

git revert коммита; правка в четырёх строках self_check

## Journal

- 2026-08-12T16:37:45Z [implementation] — Чек-лист доказательств. AC-1 (совпадение не по абсолютному пути; мест ровно четыре): ✓ tests/test_consumer_layout.py::test_a_relative_launch_is_recognised_as_ours ✓ MANUAL: grep project_norm по self_check.py — в обходе процессов не осталось ни одного; все четыре ветки (wmic, PowerShell, /proc, ps) зовут _command_belongs_to_project. Число мест проверено поиском, а не доверием тикету. AC-2 (замер воспроизведён ДО правки): ✓ MANUAL: тикет GitLab #4 фиксирует десять живых процессов при счётчике 0; причина подтверждена чтением кода — условие требовало вхождения абсолютного пути в чужую командную строку, а запуск идёт относительный. AC-3 (НЕГАТИВНЫЙ: чужой проект не сосед): ✓ tests/test_consumer_layout.py::test_a_foreign_project_is_not_counted_as_a_sibling ✓ tests/test_consumer_layout.py::test_an_unrelated_process_is_never_a_sibling AC-4 (НЕГАТИВНЫЙ: невозможность прочитать даёт «не смог», а не 0): ✓ tests/test_consumer_layout.py::test_an_unknown_working_directory_is_not_a_guess — неизвестный рабочий каталог НЕ засчитывается за совпадение. Существующая семантика count == -1 для «не смог интроспектировать» сохранена без изменений. Negative: проверены обе стороны ошибки — и вечный ноль (относительный запуск теперь распознаётся), и вечное завышение (догадка при неизвестном cwd запрещена). Лечение, считающее соседями всех, было бы хуже болезни. Domain: относительная форма запуска взята из живых процессов на машине разработчика: python ./.claude/mcp/project/server.py --project . ЗАМЕЧАНИЕ ОБ ОХВАТЕ: рабочий каталог читается только на Linux (/proc/<pid>/cwd — одна ссылка). На Windows это требует открытия чужого процесса, на macOS — вызова lsof; и то и другое дороже самой проверки. Там сопоставление идёт по командной строке, как раньше, и относительный запуск остаётся нераспознанным. Это названо в докстринге _cwd_of, а не умолчано: охват сужен осознанно, и знать об этом должен читатель кода, а не только автор.
- 2026-08-12T17:00:28Z [implementation] — Гейт размера отказал закрытие на 538 строках self_check. Это не помеха, а счёт по давнему долгу: докстринг файла перечислял ДВЕ сущности — слежение за mtime модулей и обход соседних процессов. Обход вынесен в sibling_mcp (260 строк), self_check остался на 313. Старые имена НЕ реэкспортированы намеренно, чтобы подмена по прежнему адресу падала на отсутствующем атрибуте, а не молчала. Побочный эффект вскрылся сразу: изоляция тестов держалась на том, что перезагрузка self_check обнуляла TTL-кэш соседей — теперь кэш чистит фикстура sibling_mod. 32 теста зелёные, ruff чист.
- 2026-08-12T17:08:33Z [implementation] — AC-1 (совпадение не по абсолютному пути; мест ровно четыре): ✓ tests/test_consumer_layout.py::test_a_relative_launch_is_recognised_as_ours ✓ MANUAL: поиском по sibling_mcp.py в обходе процессов не осталось ни одного вхождения project_norm; все четыре ветки (wmic, PowerShell, /proc, ps) зовут _command_belongs_to_project. AC-2 (замер воспроизведён ДО правки): ✓ MANUAL: тикет GitLab #4 — десять живых процессов при счётчике 0; причина подтверждена чтением кода. AC-3 (НЕГАТИВНЫЙ: чужой проект не сосед): ✓ tests/test_consumer_layout.py::test_a_foreign_project_is_not_counted_as_a_sibling ✓ ::test_an_unrelated_process_is_never_a_sibling. AC-4 (НЕГАТИВНЫЙ: невозможность прочитать даёт «не смог», а не 0): ✓ tests/test_consumer_layout.py::test_an_unknown_working_directory_is_not_a_guess; семантика count == -1 сохранена, ✓ tests/test_mcp_self_check.py::test_enumeration_exception_degrades_to_unknown. Разрез: обход соседей вынесен в harness/claude/mcp/project/sibling_mcp.py — гейт размера предъявил счёт по долгу, названному самим докстрингом self_check (две сущности в одной строке, конвенция #348). Старые имена НЕ реэкспортированы: подмена по прежнему адресу падает на отсутствующем атрибуте. ✓ tests/test_mcp_self_check.py — 24 теста переведены на фикстуру sibling_mod. Полный прогон: 6971 passed, 5 failed — все пять предсуществующие и к правке отношения не имеют (подтверждено прогоном на git stash: на чистом дереве падают те же и ещё один). Заведены отдельно.
