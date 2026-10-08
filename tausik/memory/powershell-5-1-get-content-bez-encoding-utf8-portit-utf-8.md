---
slug: powershell-5-1-get-content-bez-encoding-utf8-portit-utf-8
title: "PowerShell 5.1: Get-Content без -Encoding utf8 портит UTF-8 файл при обратной записи (двойное кодирование + BOM)"
type: gotcha
tags:
  - encoding
  - powershell
  - tooling
  - windows
task: powershell-tool-bypasses-bash-firewall
edges: []
---

Поймано вживую в сессии #134 на docs/ru/hooks.md и docs/en/hooks.md.

`(Get-Content file -Raw) -replace ... | Set-Content file -Encoding utf8` — выглядит безобидно и УНИЧТОЖАЕТ файл. В Windows PowerShell 5.1 `Get-Content` для файла без BOM читает в системной ANSI-кодировке (cp1251), кириллица превращается в мусор, а обратная запись в utf8 закрепляет мусор и добавляет BOM. git diff показал 157 изменённых строк в файле, где менялась одна подстрока.

ЧТО ДЕЛАТЬ:
- Для правки текста — инструмент Edit, а не shell-конвейер. Он читает и пишет в UTF-8 и не трогает остальной файл.
- Если правка всё же через PowerShell: `[System.IO.File]::ReadAllText($p)` / `WriteAllText` / `ReadAllLines` / `WriteAllLines` — .NET по умолчанию UTF-8 без BOM в обе стороны, это безопасно (проверено на bash_firewall.py и agent-contract.md в той же сессии — оба целы).
- `Get-Content -Encoding utf8` на чтении обязателен, если уж Get-Content.

ПРИЗНАК УЖЕ СЛУЧИВШЕЙСЯ ПОРЧИ: `git diff --stat` показывает изменение всего файла вместо правки; первые байты `ef bb bf` там, где BOM'а не было. Лечение: `git checkout -- <файл>` и переделать правку Edit'ом.
