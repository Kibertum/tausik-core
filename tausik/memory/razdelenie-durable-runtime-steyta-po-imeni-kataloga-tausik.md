---
slug: razdelenie-durable-runtime-steyta-po-imeni-kataloga-tausik
title: "Разделение durable/runtime стейта — по ИМЕНИ каталога (tausik/ vs .tausik/), не по .gitignore-исключениям"
type: pattern
tags:
  - gates
  - gitignore
  - roundtrip
  - state-git
task: state-git-roundtrip-gate
edges: []
---

Git-native durable-проекция живёт в НЕ-dotted `tausik/` (трекается по умолчанию), runtime — в dotted `.tausik/` (игнорируется line 20 .gitignore: DB-кэш, venv, ключи, receipts, логи). Разделение структурное по имени — НЕ требует `!`-исключений или разгитигноривания. state-git-export намеренно выбрал `tausik/` чтобы оно было видимо, `.tausik/` — приватно. Урок: при добавлении git-native артефактов клади их в не-dotted путь рядом с dotted-runtime, а не пытайся исключать подпути из игнора. Round-trip гейт (gate_state_roundtrip) вешай на trigger COMMIT, НЕ task-done: закрытие задачи мутирует БД и может auto-close родителя (story/epic), поэтому task-done-проверка флагала бы собственную in-flight запись как дрейф. Граница коммита — где 'файлы в git обязаны сходиться с БД'. Гейт opt-in (SKIP при отсутствии tausik/tausik.db) + fail-open (внутренний сбой не роняет коммит), ExportError→red. auto_export держит дерево в синке (config state.auto_export, дефолт OFF).
