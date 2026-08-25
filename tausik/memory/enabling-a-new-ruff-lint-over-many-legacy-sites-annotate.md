---
slug: enabling-a-new-ruff-lint-over-many-legacy-sites-annotate
title: "Enabling a new ruff lint over many legacy sites: annotate-then-flip (atomic-safe)"
type: pattern
tags:
  - ble001
  - ci
  - lint
  - noqa
  - ruff
task: qa-enforce-ble001-blind-except
edges: []
---

To enable a ruff rule that flags many existing sites (e.g. BLE001, 133 sites) without breaking CI mid-way: (1) annotate ALL sites with `# noqa: <CODE> — <reason>` FIRST (script over `ruff check --select <CODE> --output-format=concise`), (2) enable the rule via `[tool.ruff.lint] extend-select=["<CODE>"]` as the LAST step. Partial progress is safe because RUF100 (unused-noqa) is NOT in this project's select, so dormant noqas are harmless until the flip. ruff accepts a free-text reason after the code (`# noqa: BLE001 — why`) — verified, no parse/RUF100 issue. CI lints only scripts/ tests/ bootstrap/ (harness/**/mcp excluded). Calibration finding: TAUSIK's `except Exception` sites are deliberate best-effort (telemetry/config-fallback/cleanup/hooks), several already log — so reasoned noqa is correct; narrowing was NOT needed. Regression-guard with a subprocess `ruff --select <CODE>` test so new unjustified blind catches fail CI.
