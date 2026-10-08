---
slug: novyy-test-ne-dobavlennyy-v-git-nevidim-dlya-rezolvera
title: "Новый тест, не добавленный в git, невидим для резолвера областей"
type: gotcha
tags:
  - "tests,git,selector"
task: null
edges: []
---

Резолвер тестовых рёбер читает ОТСЛЕЖИВАЕМЫЕ файлы, поэтому только что созданный tests/test_X.py не выбирается ни одним ребром, и test_crosscutting_registry падает с «no change to any tracked source file would ever select these tests». Лечится не объявлением CROSSCUTTING_SCOPE, а git add. Замер смены #278: стоило одного полного прогона ленты (4 минуты) плюс вызов на разбор.
