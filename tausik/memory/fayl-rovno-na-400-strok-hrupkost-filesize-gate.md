---
slug: fayl-rovno-na-400-strok-hrupkost-filesize-gate
title: "Файл ровно на 400 строк = хрупкость filesize-gate"
type: gotcha
tags:
  - filesize
  - gate
  - refactor
  - regression
task: fix-gate-runner-filesize-regression
edges: []
---

Модуль ровно на лимите 400 строк — мина: любая правка (даже +5 строк exempt-списка) ломает filesize-gate. Поймано в этой сессии: align-filesize-gate task добавил 5 строк в gate_runner.py (был 400) → 405 violation. Фикс не «подрезать комменты» (вернёт ту же хрупкость), а извлечь когезивный блок в свой модуль с re-export. Правило: при правке файла >380 строк сначала проверь wc -l; если близко к 400 — выноси, не дописывай. Gate сканирует только changed-files задачи, поэтому такие latent-нарушения не видны до repo-wide проверки `find scripts -name '*.py' -exec wc -l`.
