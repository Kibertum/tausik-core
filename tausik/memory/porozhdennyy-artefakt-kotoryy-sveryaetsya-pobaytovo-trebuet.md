---
slug: porozhdennyy-artefakt-kotoryy-sveryaetsya-pobaytovo-trebuet
title: "Порождённый артефакт, который сверяется ПОБАЙТОВО, требует пина eol=lf в .gitattributes — иначе красное в каждом клоне на Windows"
type: convention
tags:
  - freshness
  - generated
  - git
  - windows
task: roadmap-artifact-predates-decision-256
edges: []
---

core.autocrlf=true, и checkout САМ переписывает LF в CRLF. Любой файл, который мы пишем с newline="\n" и читаем обратно сырым (newline=""), после свежего клона не совпадёт сам с собой: охрана свежести сообщит «протух» о файле, которого никто не трогал. В репозитории это уже третий случай: renar/**, tausik/** и теперь ROADMAP.md — первые два несут в .gitattributes комментарий именно об этом. Заводя четвёртый такой артефакт, пиши пин В ТОТ ЖЕ коммит, что и генератор, и подтверждай его тестом через `git check-attr eol <файл>`, а не глазами: пина, которого нет, не отличить от пина, который есть, пока не появится второй клон.
