---
slug: ne-obyavlyat-changelog-i-obschie-stranitsy-docs-v-relevant
title: "Не объявлять CHANGELOG и общие страницы docs в --relevant-files задачи: следующая запись в CHANGELOG гасит все выданные квитанции verify"
type: convention
tags:
  - changelog
  - convention
  - receipt
  - relevant-files
  - verify
task: null
edges: []
---

Смена #266: четыре задачи прошли verify, но task done отказал «the files this receipt covers have changed» — между verify и закрытием в CHANGELOG.md/ru и docs/*/sessions.md дописывались записи ДРУГИХ задач, а эти файлы входили в объявленную область каждой. Хэндл привязан к хешу покрытия, и общий файл делает его хрупким для всех задач сразу. Правило: в --relevant-files — код и тесты задачи; CHANGELOG и общие страницы проверяют гейты закрытия (changelog_gate читает git, doc-гейты — дерево). Если страница — собственный продукт задачи, объявлять можно, но закрывать сразу после verify, без правок других задач между ними.
