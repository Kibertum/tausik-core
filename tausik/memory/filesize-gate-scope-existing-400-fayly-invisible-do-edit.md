---
slug: filesize-gate-scope-existing-400-fayly-invisible-do-edit
title: "Filesize gate scope: existing >400 файлы invisible до edit"
type: gotcha
tags:
  - filesize
  - gates
  - scope
  - tech-debt
  - v14b
task: v14b-brain-universality-heuristic
edges: []
---

Filesize gate (gate_runner.run_filesize_gate, max_lines=400) запускается ТОЛЬКО на relevant_files конкретной задачи (scoped verify). Файл может неограниченно расти >400 пока ни одна активная задача его не затронет — gate о нём не знает. Когда новая задача делает мелкий edit в такой файл, gate внезапно блокирует с накопленным долгом, и автору приходится делать unplanned split как side-fix.

Случай в живой практике: scripts/service_knowledge.py был 431 строка на HEAD после v14b-memory-cleanup-cli (добавлены memory_archive + memory_dedupe). Тогдашняя задача scope не включала service_knowledge.py до edit-факта (relevant_files посчитались на старте, файл попал в scope после первого edit). Filesize gate коммита проскочил. Следующая задача v14b-brain-universality-heuristic добавила 1 import + 1 вызов в memory_add — и упала на 434 строках, пришлось делать side-split (memory hygiene + exploration в отдельные модули).

Why: scoped gate — это правильный design (не задерживать unrelated работу), но scope = relevant_files === touched files в данный момент, а не "все файлы которые могли вырасти". Без full-suite filesize check (или explicit exempt list) долг копится тихо.

How to apply: (1) Перед началом задачи на крупном модуле проверить wc -l целевого файла — если уже близко к 400, сразу планировать split в plan steps. (2) Раз в N задач прогонять `tausik verify` без --task (full-sweep) или просто `python -c 'from gate_runner import run_filesize_gate; ...'` на топ-20 файлов scripts/ — surface накопленные нарушения. (3) Альтернатива: добавить commit hook который запускает filesize на ВСЕ изменённые-в-проекте файлы за N последних коммитов — отдельная задача стоит ли (сравнить с инвазивностью).
