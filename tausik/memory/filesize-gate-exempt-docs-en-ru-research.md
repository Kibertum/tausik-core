---
slug: filesize-gate-exempt-docs-en-ru-research
title: "filesize gate exempt: docs/{en,ru}/research/*"
type: convention
tags:
  - config
  - filesize
  - gates
  - research
task: null
edges: []
---

Audit research dumps в `docs/{en,ru}/research/` — auto-generated артефакты `audit_pytest_dedupe.py` и аналогичных скриптов. Они large by design (текущий 2026-05-07 dump = 1033 строки, 212 групп × ~5 строк) и не требуют 400-line filesize cap.

Конфиг в `.tausik/config.json` (gitignored — local-only):
```json
{
  "gates": {
    "filesize": {
      "exempt_files": [
        "docs/en/research/*",
        "docs/ru/research/*"
      ]
    }
  }
}
```

Glob patterns совпадают на любой файл в research/ subdir. Если бы это был commit-tracked config, нужно было бы добавить в bootstrap defaults.
