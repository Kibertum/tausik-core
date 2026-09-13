---
slug: tausik-tausik-ispolnyaet-razvernutuyu-kopiyu-claude-scripts
title: ".tausik/tausik исполняет РАЗВЁРНУТУЮ копию (.claude/scripts), а не scripts/ — живой репро на CLI до bootstrap проверяет старый код"
type: gotcha
tags:
  - bootstrap
  - cli
  - deploy
  - live-check
task: relevant-files-swallows-a-comma-joined-list-as-one-path
edges: []
---

Смена #252, дважды за одну смену: (1) `doc roadmap` после правки scripts/release_roadmap.py породил карту старым кодом; (2) живой репро GitLab #13 (`task update --relevant-files "a,b"`) на CLI ПРИНЯЛ значение после того, как валидатор уже лежал в scripts/. Причина: обёртка .tausik/tausik ищет первый .<ide>/scripts и запускает его — копию, которую кладёт bootstrap. Правило: любая проверка «живьём через CLI» после правки scripts/ начинается с `python bootstrap/bootstrap.py --ide all` (или копирования файла во все .<ide>/scripts), иначе замер говорит о прошлом дереве. MCP-сервер в этом же состоянии — «stale process» (bootstrap_drift), и его перезапустить из сессии нельзя: закрывать через CLI.
