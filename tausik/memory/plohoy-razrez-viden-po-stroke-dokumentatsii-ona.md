---
slug: plohoy-razrez-viden-po-stroke-dokumentatsii-ona
title: "Плохой разрез виден по строке документации: она ПЕРЕЧИСЛЯЕТ сущности вместо того, чтобы назвать домен"
type: convention
tags:
  - code-review
  - diagnostics
  - filesize
  - module-boundaries
  - split
task: filesize-rejoin-cap-deformed-wrappers
edges: []
---

Диагностический признак, найденный в filesize-rejoin-cap-deformed-wrappers и годный для повторного применения: если строка документации модуля перечисляет несвязанные сущности через запятую («CLI handlers — memory, gates, skill, fts, update-claudemd»; «metrics, search, events, explore, audit, run, dead-end»), то границу этого модуля назвать одним словом НЕЛЬЗЯ, и он почти наверняка остаток разреза под лимит, а не домен. Признак дешёвый (читается автоматически, ast.get_docstring) и точный: из 33 модулей полосы 360-400 он выделил ровно те 2, что провалили критерий, не дав ни одного ложного срабатывания на 31 защитимом. Обратный признак тоже работает: модуль, чья дока называет домен одним словом (trust, vendor, parser, migrations, conformance, export), границу держит. Второй, более сильный признак — РАЗРЫВ ДОМЕНА: файл, названный доменом, не содержит команду/сущность этого домена (project_cli_metrics.py держал dispatch_metrics_subcmd, а cmd_metrics лежала в project_cli_ops.py; project_cli_audit_extra.py держал подкоманды аудита, а cmd_audit — там же). Разрыв неверен независимо от значения cap и чинится в первую очередь. Имена-маркеры остатка: *_extra, *_ops, *_common, *_utils, *_misc, *_part2 — «extra» буквально значит «что не влезло». Связано с #346 (проверять запуском, а не импортом) и критерием из mcp-handlers-god-module-split.
