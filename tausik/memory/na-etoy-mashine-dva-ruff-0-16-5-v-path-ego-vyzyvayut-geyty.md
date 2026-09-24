---
slug: na-etoy-mashine-dva-ruff-0-16-5-v-path-ego-vyzyvayut-geyty
title: "На этой машине два ruff: 0.16.5 в PATH (его вызывают гейты и verify-pytest) и 0.15.12 в .tausik/venv"
type: gotcha
tags:
  - "ruff,versions,verify"
task: ruff-format-is-not-gated-and-86-files-diverged
edges: []
---

Смена #267: перечень неотформатированных файлов, посчитанный venv-ным ruff, не совпал с тем, что видел pytest под verify (системный Python, ruff 0.16.5). У 0.16 и формат вывода другой: диагностика ' --> PATH:L:C' вместо 'Would reformat: PATH'. Любой инструмент, чей вердикт сравнивается с гейтом, вызывать тем же бинарём, что и гейт (shutil.which('ruff')), а не python -m ruff из venv.
