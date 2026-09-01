---
slug: rm-ne-yavlyaetsya-tselyu-zapisi-dlya-geyta-test-vokrug-rm
title: "rm НЕ является целью записи для гейта: тест вокруг rm зелен ВХОЛОСТУЮ"
type: gotcha
tags: []
task: write-gate-resolves-relative-paths-against-the-wrong-directory
edges: []
---

write_targets возвращает пусто для всех форм rm (rm -f, rm -rf, со звёздочкой). Поэтому воспроизведение дефекта командой rm даёт код 0 независимо от того, есть дефект или нет — тест проходит, ничего не проверив. В #205 запись задачи цитировала именно rm, и первый тест был зелёным вхолостую. Для проверки гейта бери команду, которая ДЕЙСТВИТЕЛЬНО пишет: touch, cp, tee, sed -i, перенаправление.
