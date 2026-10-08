---
slug: tausik-renar-conformance-write-ispolnyaet-razvernutyy
title: "tausik renar conformance --write исполняет РАЗВЁРНУТЫЙ профиль: регенерация до bootstrap собирает артефакт СТАРЫМ кодом"
type: gotcha
tags:
  - bootstrap
  - cli
  - process
  - renar
task: our-only-spec-is-derived-without-either-allowed-source-field
edges: []
---

Обёртка .tausik/tausik ищет каталог scripts в первом найденном профиле (.claude, .cursor, .windsurf, .codex, .qwen, .kilo, .opencode) и запускает ЕГО, а не scripts/ в корне. Замер в #212: правка генератора манифеста, затем --write СРАЗУ — записан manifest-version 16 БЕЗ нового раздела, и охрана несвежести осталась красной с сообщением «regenerate», хотя регенерация уже была сделана. Выглядит как дефект генератора, а является стойлостью профиля.

ПОРЯДОК ОБЯЗАТЕЛЕН: правка исходников → bootstrap.py --ide all → --check → ТОЛЬКО ПОТОМ регенерация артефакта командой CLI → полная лента → verify. Это дополняет память #551 (ни одной правки после bootstrap) со стороны ДАННЫХ: регенерация есть запись данных, её место ПОСЛЕ bootstrap, а не до.

ЕСЛИ РЕГЕНЕРАЦИЯ УЖЕ СЛУЧИЛАСЬ СТАРЫМ КОДОМ: не оставляй выданный номер версии. git checkout -- RENAR-CONFORMANCE.yaml возвращает закоммиченную версию, после чего регенерация даёт следующий номер без дыры. Незакоммиченная версия записью журнала не была, поэтому её выбрасывание НЕ есть переиспользование номера.
