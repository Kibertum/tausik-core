---
slug: powershell-5-1-get-content-set-content-lomaet-ishodniki-bom
title: "PowerShell 5.1 Get-Content/Set-Content ломает исходники: BOM + мохибейк на не-ASCII"
type: gotcha
tags:
  - encoding
  - gotcha
  - powershell
  - tooling
  - windows
task: gate-activity-blind-to-post-scope
edges: []
---

`(Get-Content f -Raw).Replace(a,b) | Set-Content f -Encoding utf8` выглядит как безобидная замена строки и портит файл ДВАЖДЫ:

1. `Set-Content -Encoding utf8` в Windows PowerShell 5.1 пишет UTF-8 С BOM (EF BB BF). Первые байты файла становятся мусором для инструментов, ожидающих чистый UTF-8.
2. `Get-Content -Raw` читает в системной ANSI-кодировке, а не UTF-8 — каждое тире, кавычка-ёлочка и кириллица возвращаются как мохибейк и в таком виде записываются обратно.

Проверил на tests/test_gate_runs_persist.py: после «замены имени класса» файл получил BOM и «â€"» вместо тире. Тесты при этом ПРОШЛИ — Python съел BOM и мохибейк в докстрингах, то есть зелёный прогон эту порчу не ловит. Заметно только байтовой проверкой:
  $b=[IO.File]::ReadAllBytes(f); $b[0..2]  # 239,187,191 = BOM
  [IO.File]::ReadAllText(f,[Text.Encoding]::UTF8) -match 'Ã|â€'

Правило: правки исходников — ТОЛЬКО инструментом Edit/Write. PowerShell для файлов использовать нельзя даже для «однострочной замены». Откат: git checkout -- <file>, затем повторить правку через Edit.
