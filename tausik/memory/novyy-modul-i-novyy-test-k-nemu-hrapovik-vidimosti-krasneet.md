---
slug: novyy-modul-i-novyy-test-k-nemu-hrapovik-vidimosti-krasneet
title: "Новый модуль и новый тест к нему: храповик видимости краснеет, пока оба не в индексе"
type: gotcha
tags: []
task: adr-013-conditional-obligations-expire-when-subject-appears
edges: []
---

test_crosscutting_registry::TestInvisibleToEveryEdge сообщил, что новый тестовый файл не выберет ни одно изменение. Причина не в тесте и не в импортах: _invisible_to_every_edge спрашивает настоящий резолвер по _tracked_sources, то есть по git-ОТСЛЕЖИВАЕМЫМ файлам. Новый модуль в scripts/ лежал неотслеженным, поэтому ребра импорта не существовало. После git add обоих файлов гейт зелёный без единой правки кода. Не бросайся объявлять CROSSCUTTING_SCOPE и не вноси файл в _INVISIBLE_BASELINE: сначала проверь git status.
