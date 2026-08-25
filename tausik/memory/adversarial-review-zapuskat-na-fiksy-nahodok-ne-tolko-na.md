---
slug: adversarial-review-zapuskat-na-fiksy-nahodok-ne-tolko-na
title: "Adversarial-review запускать НА ФИКСЫ находок, не только на исходную реализацию"
type: convention
tags:
  - quality-process
  - review
  - security
  - senar
task: l26-hook-contract-review
edges: []
---

При закрытии security-adjacent задачи через adversarial-review: после того как ревьюер нашёл баги и ты их исправил — ПЕРЕПРОГНАТЬ ревью на сами фиксы. В l26-hook-contract-review round-1 нашёл CRITICAL+HIGH; мои фиксы round-1 ВНЕСЛИ новую CRITICAL-регрессию (фильтр отбрасывал безопасные quoted-имена с ()/& → заново открыл обход), которую поймал только round-2. Один проход ревью проверяет реализацию, но НЕ проверяет качество исправлений — а исправление под давлением «закрыть» само по себе источник дефектов (класс #128/#268: 4 бага в УЖЕ закрытых задачах). Практика: цикл find→fix→re-review до раунда, чистого по critical/high; для механических хвостовых фиксов (MEDIUM/LOW под тестами) достаточно регрессионных тестов без нового LLM-раунда. Связано с [[review-security-adjacent-mandatory]].
