---
slug: obertka-tausik-tausik-pod-git-bash-raskryvaet-shablony-v
title: "Обёртка .tausik/tausik под Git Bash РАСКРЫВАЕТ шаблоны в аргументах: scripts/*.py приходит в Python списком из 404 файлов, длинный scope превращается в E2BIG"
type: gotcha
tags:
  - cli
  - glob
  - gotcha
  - msys
  - scope
  - windows
  - wrapper
task: null
edges: []
---

Замер смены #266: task add ... --scope-paths scripts/*.py tests/*.py через bash-обёртку сохранил в scope_paths 750 имён файлов вместо двух шаблонов (runtime MSYS раскрывает wildcard-аргументы перед exec нативного python.exe даже при кавычках в вызывающем Python), а задача с scripts/*.py + tests/*.py + docs/**.md упала с «Argument list too long» (код 126). Симптом легко принять за раздутое окружение — это не оно. Обход: шаблоны передавать через .tausik/tausik.cmd (cmd.exe и CPython ничего не раскрывают; многострочные аргументы там по-прежнему режутся, поэтому текст — через bash, шаблоны — через cmd). Вторая находка той же смены: story add с существующим slug падает сырым traceback (задача story-add-duplicate-slug-is-a-traceback-not-a-refusal, github#187).
