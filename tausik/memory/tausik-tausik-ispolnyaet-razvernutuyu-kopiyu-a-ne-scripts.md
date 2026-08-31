---
slug: tausik-tausik-ispolnyaet-razvernutuyu-kopiyu-a-ne-scripts
title: ".tausik/tausik исполняет РАЗВЁРНУТУЮ копию, а не scripts/ — правка не доходит до CLI до bootstrap"
type: gotcha
tags:
  - bootstrap
  - cli
  - deploy
  - drift
  - verify
task: verify-handle-dies-on-a-tasks-own-export-file
edges: []
---

Обёртка .tausik/tausik ищет каталог scripts в ПЕРВОМ существующем .<ide>/scripts (IDE_LIST=claude cursor windsurf codex qwen kilo opencode; у нас срабатывает .claude/scripts) и НИКОГДА не берёт scripts/ из корня. Значит любая правка в scripts/ до `python bootstrap/bootstrap.py --ide all` для CLI не существует вовсе.

ЧЕМ ЭТО ОПАСНО ИМЕННО ЗДЕСЬ, А НЕ ВООБЩЕ. Замерено в #194 на задаче verify-handle-dies-on-a-tasks-own-export-file: verify #1887 записал прогон СТАРЫМ кодом (хеш по объявленному списку, fe9b5f34f45f), а task done посчитал НОВЫМ (хеш по покрытию, 351c6d0014c2) — и отказал. Отказ был верный и совершенно непонятный: он сообщает про изменившиеся файлы, тогда как не менялся ни один, а разошёлся КОД ДВУХ СТОРОН. Гейт bootstrap_drift ловит это на task done, то есть на ВТОРОМ звене, когда ложный прогон verify уже записан в verification_runs.

ПОРЯДОК: правка scripts/ -> bootstrap --ide all -> ТОЛЬКО ПОТОМ первый verify. bootstrap ПЕРЕД проверкой, а не после отказа гейта. Цена нарушения — потраченный прогон verify и разбор расхождения хешей, которого нет.

Перезапуск MCP — ТРЕТЬЕ звено и отдельное: сервер держит код с момента старта, и новый модуль, созданный в сессии, ему не виден до перезапуска. Для verify/task done это значит: после правки scripts/ ходи CLI, а не MCP.
