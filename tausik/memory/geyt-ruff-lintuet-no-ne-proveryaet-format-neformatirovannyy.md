---
slug: geyt-ruff-lintuet-no-ne-proveryaet-format-neformatirovannyy
title: "Гейт ruff линтует, но НЕ проверяет формат — неформатированный код проходит все гейты"
type: gotcha
tags: []
task: adapt-delta-leaves-an-orphan-when-the-guard-refuses
edges: []
---

Гейт ruff объявлен как 'ruff check {files}' (scripts/gate_registry.py) — это ЛИНТЕР, а не проверка формата. 'ruff format --check' не выполняется НИ на одном триггере, поэтому неформатированный код проходит и commit, и verify, и task done.

ЗАМЕР (#211): scripts/service_adapts.py на HEAD (коммит ecc311e) был неформатирован в ДВУХ местах — adapt_add:102 и adapt_set_status:298 — и оба внесены работой #210, прошедшей все гейты зелёными. Обнаружено случайно: я запустил 'ruff format --check' по своей привычке, и он указал на строку ВНЕ моей правки; сверка с 'git show HEAD:файл' подтвердила, что расхождение было до меня.

ПРАКТИКА, ПОКА ЭТО ТАК: правя файл, прогоняй 'ruff format --check' по нему отдельно и не считай зелёный ruff признаком форматированности. Если формат правишь — правь только СВОЙ файл, иначе дифф раздувается чужими строками.
