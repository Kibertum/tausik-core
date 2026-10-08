---
slug: cli-ispolnyaet-razvernutyy-profil-artefakt-porozhdaemyy
title: "CLI исполняет РАЗВЁРНУТЫЙ профиль: артефакт, порождаемый командой (RENAR-CONFORMANCE.yaml), регенерируй ТОЛЬКО после bootstrap"
type: convention
tags:
  - bootstrap
  - cli
  - renar
task: ar-existence-is-probed-by-three-guessed-table-names
edges: []
---

В #208 renar conformance --write после правки scripts/renar_clause_reactive_adapt.py отдал старую строку probed [...]: .tausik/tausik запускает .claude/scripts, а не scripts/. Гейт bootstrap_drift это поймает при закрытии, но порождённый артефакт к тому моменту уже лежит в дереве старым и смотрится «сгенерированным». Порядок: правка scripts -> тесты (они импортируют scripts/ напрямую) -> bootstrap --ide all -> регенерация артефакта -> verify заново (handle протухает, #499/#506).
