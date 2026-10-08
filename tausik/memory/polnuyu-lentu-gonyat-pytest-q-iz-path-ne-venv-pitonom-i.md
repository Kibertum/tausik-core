---
slug: polnuyu-lentu-gonyat-pytest-q-iz-path-ne-venv-pitonom-i
title: "Полную ленту гонять `pytest -q` из PATH: не venv-питоном и НИКОГДА не с -o addopts=\"\""
type: gotcha
tags:
  - lane
  - pytest
  - tests
  - xdist
task: audit-hook-test-is-invisible-and-reds-the-full-lane
edges: []
---

Три способа запустить ленту, два из них ломают замер:

1) `.tausik/venv/Scripts/python.exe -m pytest` — ПАДАЕТ: «unrecognized arguments: -n». В этом venv нет pytest-xdist, а pyproject.toml:69 объявляет addopts = "-m 'not slow' -n auto". Этот venv обслуживает CLI фреймворка, а НЕ тесты: гейт pytest зовёт голый `pytest` из PATH (stacks/python/*.json:15), то есть системный интерпретатор, где xdist есть. Расхождение не дефект — так устроено.

2) `-o addopts=""` как обход пункта 1 — ХУЖЕ ПАДЕНИЯ: снимает не только `-n auto` (лента уходит на одно ядро), но и `-m 'not slow'` (в прогон входят slow-тесты). В #193 такой прогон висел дольше 10 минут и был убит. Ровно этот тупик уже оплачен замером #186: 32м24с против 3м48с; правильный способ снять только фильтр маркеров — `-m ''`, он парсится позже и перебивает addopts, оставляя всё остальное на месте (так и делает gate_command_runner.py:437 под TAUSIK_VERIFY_FULL=1).

3) ПРАВИЛЬНО: `pytest -q -p no:cacheprovider` из PATH, из корня проекта. Замер #193: 7374 passed, 24 skipped за 108 s. Это ДВЕ МИНУТЫ, а не «11-13 минут», как записано в передаче смены — то есть у пропуска полной ленты нет ценового оправдания.
