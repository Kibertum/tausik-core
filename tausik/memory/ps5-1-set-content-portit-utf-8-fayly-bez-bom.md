---
slug: ps5-1-set-content-portit-utf-8-fayly-bez-bom
title: "PS5.1 Set-Content портит UTF-8 файлы без BOM"
type: gotcha
tags:
  - encoding
  - powershell
  - windows
task: v15s-rule6-rollback-plan
edges: []
---

Get-Content -Raw читает UTF-8-без-BOM как ANSI (cp1251) -> -replace -> Set-Content пишет mojibake (превращает кириллицу/em-dash/галочки в кракозябры). НИКОГДА не редактировать файлы репо через PowerShell pipeline. Только Edit/Write tools или python io с encoding=utf-8. Инцидент: session 78 повредил README.md, README.ru.md, test_qg2_gates.py, test_task_start_model_banner.py, test_rule6_rollback.py — восстановлены из git.
