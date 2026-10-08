---
slug: zaimstvovannuyu-ideyu-v-changelog-soprovozhdat-atributsiey
title: "Заимствованную идею в CHANGELOG сопровождать атрибуцией источника"
type: convention
tags:
  - attribution
  - borrow
  - changelog
  - convention
task: null
edges: []
---

Когда реализуется фича, идею которой мы подчерпнули из внешнего продукта/статьи (например story borrow-cubest-onyx: cubest, onyx/Danswer, техника Anthropic contextual-retrieval), запись в CHANGELOG.md/CHANGELOG.ru.md ОБЯЗАНА называть источник — «(заимствование cubest)», «(паттерн onyx)», «(техника Anthropic)». Правило пользователя (сессия #138): в changelog для таких фич упоминаем именно ОТКУДА взята идея. Источник уже проставлен в goal каждой borrow-задачи, чтобы всплыть при реализации. Не путать с собственными фичами (export/import) — там атрибуции нет, идея своя.
