---
slug: razlichat-sistemnoe-i-ruchnoe-gashenie-rebra-cherez
title: "Различать системное и ручное гашение ребра через invalidated_by"
type: dead_end
tags: []
task: orphaned-edges-never-converge-so-every-departure-pays-for-them
edges: []
---

Approach: Различать системное и ручное гашение ребра через invalidated_by
Reason: Замысел был точный: пометить ребро, погашенное уходом цели, чтобы `memory unlink` отвечал «уже закончилось при уходе цели», а не отказывал вызывающему. Опровергнуто схемой: invalidated_by есть ВНЕШНИЙ КЛЮЧ на memory_edges(id), поэтому сторожевое значение вроде -1 нарушает ограничение — property-тест дал FOREIGN KEY constraint failed. Менять схему ради различения не стоит: отвязка уже погашенного ребра всё равно ничего не делает в обоих случаях. Взято проще — отвязка стала идемпотентной и называет, КОГДА ребро закончилось.
