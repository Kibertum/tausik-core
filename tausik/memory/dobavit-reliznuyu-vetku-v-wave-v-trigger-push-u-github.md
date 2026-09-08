---
slug: dobavit-reliznuyu-vetku-v-wave-v-trigger-push-u-github
title: "Добавить релизную ветку v*-wave в триггер push у .github/workflows/tests.yml, чтобы опубликованная л"
type: dead_end
tags: []
task: null
edges: []
---

Approach: Добавить релизную ветку v*-wave в триггер push у .github/workflows/tests.yml, чтобы опубликованная лента увидела разработку
Reason: Рабочая ветка на GitHub не уходит вовсе (решение #260): git branch -r показывает там main и release/*, но не v1-9-wave. Триггер на ветку, которая туда не пушится, — мёртвая строка. Разработка проверяется GitLab-пайплайном, который идёт на любой ветке; красный значок GitHub объясняется тем, что на main не пушили с 25.08, и лечится слиянием, а не конфигурацией.
