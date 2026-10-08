---
slug: detectors-degrade-to-findings-never-crash
title: "Detectors degrade to findings, never crash"
type: pattern
tags:
  - "renar,drift,sweep"
task: null
edges: []
---

A drift/validation detector that scans live-DB state must treat malformed values (non-numeric int columns, bad enums) as findings, not exceptions — crashing defeats the detector's purpose (CLI tracebacks; warn-gates swallow it silently as clean). Pattern: try-parse → on failure append a '<thing>-invalid' finding and set the parsed value to None, then guard dependent checks with 'if v is not None'. Do NOT 'continue' the row loop after a parse failure — a bare continue masks co-occurring checks later in the same loop body (e.g. signed-signature check). Found in renar_drift.py detect_schema_drift, sweep #87.
