---
slug: cmd-wrapper-silently-truncates-multiline-arguments
title: "Windows-обёртка tausik.cmd молча обрезает любой многострочный аргумент по первой строке"
status: planning
epic: arch-debt-post-18
story: adp18-module-boundaries
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/hooks/**, scripts/**, bootstrap/**, tests/** — восстановление хука bash_write_gate.py, потерянного переключением дерева на github/main"
scope_exclude: ".tausik/tausik (bash-обёртка не затронута — она уже работает верно)"
relevant_files: []
scope_paths:
  - "bootstrap/*.py"
  - "scripts/*.py"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
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
