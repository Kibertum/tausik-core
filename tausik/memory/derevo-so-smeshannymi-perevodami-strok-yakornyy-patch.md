---
slug: derevo-so-smeshannymi-perevodami-strok-yakornyy-patch
title: "Дерево со СМЕШАННЫМИ переводами строк: якорный патч обязан определять EOL пофайлово, иначе тихо не находит ничего"
type: gotcha
tags:
  - crlf
  - patching
  - setup-fail
  - windows
task: this-repos-strictness-lives-in-a-gitignored-file
edges: []
---

Замерено в #197. Одно и то же предложение правилось в 8 файлах; скрипт читал с newline="" (сохранение) и искал якоря с "\n". Совпало ровно 2 из 6: scripts/gate_verify_first.py и tests/test_opencode_bootstrap.py — LF, а scripts/gate_command_policy.py, scripts/project_config.py, tests/test_config_trust.py, tests/test_gate_command_neutering.py, docs/{en,ru}/config-trust-tiers.md, CHANGELOG*.md — CRLF. Дерево смешанное, и это НЕ видно ни из git status, ни из чтения файла обычными средствами.

**Почему:** якорь с "\n" физически не встречается в CRLF-файле. Если бы харнесс не требовал count == 1, четыре правки просто не применились бы, а скрипт отчитался бы об успехе — ровно тот класс тихого отказа, против которого заведена память #457.

**Как применять:** в любом скрипте, который патчит по якорю, читай `io.open(p, encoding="utf-8", newline="")`, вычисляй `eol = "\r\n" if "\r\n" in s else "\n"` и подставляй его в ОБА конца (`old.replace("\n", eol)`, `new.replace("\n", eol)`) перед сравнением. Проверка `s.count(anchor) != 1` -> отдельный исход SETUP-FAIL обязательна: она и есть то, что превращает молчаливый промах в громкий. Связано: [[senar-mutation-anchor-one-line-windows]].
