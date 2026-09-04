---
slug: kanal-powershell-ispolnyaet-python-c-chestno-lomayutsya
title: "Канал PowerShell исполняет python -c честно; ломаются только вложенные двойные кавычки, и ломаются громко"
type: gotcha
tags:
  - powershell
  - premise
  - tooling
  - windows
task: powershell-channel-cannot-read-python-dash-c
edges: []
---

Замер #213 по девяти формам (журнал задачи powershell-channel-cannot-read-python-dash-c): stdout отдаётся, $LASTEXITCODE честный (0/1/3), кириллица под -X utf8 в порядке, json с одинарными кавычками внутри двойных работает. Единственный отказ: Windows PowerShell 5.1 искажает `\"` и съедает внутренние двойные кавычки при передаче аргумента нативному процессу — python получает `print(sq outer)` и падает SyntaxError с rc=1. Формы «пустой stdout при rc=0» НЕТ, маскировки отказа под отрицательный результат нет. Премиса из передачи #207 снята; действующее правило «команду с вложенными кавычками писать файлом» покрывает реальный отказ. Не заводить задач на «канал не читает python -c».
