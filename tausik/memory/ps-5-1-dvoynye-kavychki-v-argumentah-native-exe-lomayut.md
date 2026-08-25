---
slug: ps-5-1-dvoynye-kavychki-v-argumentah-native-exe-lomayut
title: "PS 5.1: двойные кавычки в аргументах native exe ломают передачу"
type: gotcha
tags:
  - git
  - powershell
  - quoting
task: null
edges: []
---

PowerShell 5.1 не экранирует встроенные двойные кавычки при передаче аргументов native exe (git, tausik.cmd): git commit -m @'...текст с "..."...'@ разрывается на pathspec-ошибки, tausik memory add с \" в content — на unrecognized arguments. Правило: в значениях аргументов через PS не использовать символ двойной кавычки (заменять «», <> или убирать); для structured-данных (--evidence-json, memory add с кавычками) использовать MCP-инструменты вместо CLI.
