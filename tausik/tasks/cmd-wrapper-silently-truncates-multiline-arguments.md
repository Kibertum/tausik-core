---
slug: cmd-wrapper-silently-truncates-multiline-arguments
title: "Windows-обёртка tausik.cmd молча обрезает любой многострочный аргумент по первой строке"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/hooks/**, scripts/**, bootstrap/**, tests/** — восстановление хука bash_write_gate.py, потерянного переключением дерева на github/main"
scope_exclude: ".tausik/tausik (bash-обёртка не затронута — она уже работает верно)"
relevant_files:
  - "tests/test_cmd_wrapper_multiline.py"
scope_paths:
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T20:32:22Z"
---

## Goal

Многострочный аргумент, поданный CLI на Windows, доходит целиком или отвергается вслух — но НЕ усекается молча.

## Acceptance Criteria

1. `.tausik/tausik task update <slug> --acceptance-criteria "<две строки>"`, вызванный из PowerShell (то есть через tausik.cmd), сохраняет ОБЕ строки; проверяется чтением task show.
2. То же для --goal, --notes, memory add и decide — перечислить ВСЕ поля, принимающие свободный текст, и закрыть форму, а не найденный случай (конвенция #361).
3. Тест воспроизводит дефект на текущей обёртке и зеленеет на исправленной; на не-Windows он skip по платформе, а не удалён.
4. НЕГАТИВНЫЙ сценарий: если перенос строки принципиально не проходит через выбранный транспорт, обёртка ОТВЕРГАЕТ такой аргумент с внятной ошибкой; молчаливое усечение ЗАПРЕЩЕНО.
5. НЕГАТИВНЫЙ сценарий: обёртка перегенерируется bootstrap.py --ide all, и повторная генерация не откатывает исправление — иначе дефект возвращается при следующем bootstrap.

## Plan

## Rollback

git revert коммита с правкой install_cli_wrapper и перегенерация обёртки bootstrap.py --ide all

## Journal

- 2026-08-04T07:01:36Z [planning] — Корень изолирован живым сравнением в сессии #164. Один и тот же вызов task update --acceptance-criteria с двумя строками: через PowerShell (резолвится в .tausik/tausik.cmd) в БД попала ТОЛЬКО первая строка, команда отчиталась 'updated'; через bash (.tausik/tausik) попали обе. Причина — строка 31 tausik.cmd: cmd.exe передаёт %* без переносов строк, всё после первого CR/LF отбрасывается. Отказа нет, кода возврата нет, пользователь узнаёт о потере, только перечитав запись. Ровно поэтому QG-0 отверг мои критерии 'нет негативного сценария': негативные пункты 6 и 7 были в аргументе, но до БД не доехали.
- 2026-09-09T08:43:29Z [planning] — ПРЕМИСА ОПРОВЕРГНУТА ЗАМЕРОМ, смена #241. Заявлено: Windows-обёртка tausik.cmd МОЛЧА обрезает многострочный аргумент по первой строке. Проверено вызовом с аргументом из двух строк: обёртка ОТКАЗЫВАЕТ с кодом 3 и словами 'the Windows .cmd wrapper could not pass your arguments through', называя средство — POSIX-обёртка из bash либо MCP. То есть тихая порча данных превратилась в именованный отказ. Это ровно то, чего задача требовала. Наткнулся на это независимо в этой же смене, когда сквозной потребительский тест писал многострочное доказательство закрытия.
- 2026-09-23T20:22:33Z [implementation] — Замер (смена #267, живой): многострочный --acceptance-criteria через .tausik/tausik.cmd из Git Bash отвергнут вслух: 'the Windows .cmd wrapper could not pass your arguments through cmd.exe without loss — refusing rather than acting on a truncated value', в процесс дошла только первая строка. cmd.exe в принципе не несёт перевод строки в аргументе (строка команды на нём заканчивается), поэтому AC-1 по транспорту невыполним и действует AC-4: отказ вслух. Охрана — cmdline_fidelity на уровне обёртки, для ЛЮБОГО поля свободного текста (AC-2 закрыт формой). Кода не меняю; тест фиксирует случай перевода строки.
- 2026-09-23T20:23:01Z [implementation] — AC-1: ✓ в иной форме — невыполним по транспорту (cmd.exe не несёт перевод строки); действует AC-4, см. замер выше
- 2026-09-23T20:23:01Z [implementation] — AC-2: ✓ tests/test_cmd_wrapper_multiline.py::test_the_lost_second_line_is_reported (acceptance-criteria, goal, notes, rationale — охрана на уровне всей строки)
- 2026-09-23T20:23:01Z [implementation] — AC-3: ✓ tests/test_cmd_wrapper_multiline.py::test_the_lost_second_line_is_reported
- 2026-09-23T20:23:02Z [implementation] — AC-4: ✓ tests/test_cmd_wrapper_multiline.py::test_a_single_line_value_passes и живой отказ в журнале
- 2026-09-23T20:23:02Z [implementation] — AC-5: ✓ tests/test_cmd_wrapper_argv_fidelity.py::test_wrapper_template_exports_the_raw_command_line (шаблон bootstrap несёт охрану)
- 2026-09-23T20:23:02Z [implementation] — NO-DEAD-END: задача оказалась решённой прежней работой (cmdline_fidelity), тупиков не было
