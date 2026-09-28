---
slug: rule-on-ruff-016-new-defaults
title: "Принять или отвергнуть новые умолчания ruff 0.16: 1539 находок, по каждому правилу решение"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - pyproject.toml
  - "scripts/tausik_constants.py"
  - "scripts/project_backend.py"
  - "tests/test_cascade_delete.py"
  - "tests/test_graph_memory.py"
  - "tests/test_tausik_backend.py"
  - "tests/test_skill_content_scan.py"
  - "tests/test_brain_scrubbing.py"
  - "tests/test_brain_universality.py"
scope_paths:
  - pyproject.toml
  - "scripts/**"
  - "tests/**"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:27:34Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#85"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Набор правил ruff — осознанный выбор проекта на 0.16, а не наследство от 0.15: по каждому новоумолчальному правилу принято решение включить или отвергнуть, с записанной причиной.

## Acceptance Criteria

1. Every rule ruff 0.16.5 enables by default beyond the project's select (58 rules, counted under the project config) has a recorded ruling — adopt, reject or split out — with its reason, in one decision grouped by class. 2. The adopted rules join [tool.ruff.lint] select and their findings are fixed at the code: PLE2515, PLE2502, PLR0124, B017, PYI036. 3. NEGATIVE: ruff check under the project config is clean afterwards, and the tests whose data carried invisible characters still test the SAME characters (written as escapes, not removed). 4. NEGATIVE: rules whose findings touch the silent-error principle (S110/S112 try-except-pass/continue, RUF100 stale noqa) are split into their own tasks, not rejected in bulk.

## Plan

## Rollback

git revert правки pyproject; select возвращается к E4,E7,E9,F,BLE001

## Journal

- 2026-09-23T23:19:38Z [implementation] — Measurement (session #269, ruff 0.16.5 on PATH): --isolated defaults over scripts tests bootstrap harness = 2388 findings in 58 rules; counted per rule under the PROJECT config (--extend-select <rule>) every rule still has findings, largest RUF100 546, I001 203, PLW1510 196, SIM115 125, ISC004 105, S110 72, UP017 67; correctness-class: PLE2515 5, PLE2502 1, PLR0124 1, PLR0133 2, B017 8, DTZ001/005/011 1 each, PYI036 1.
- 2026-09-23T23:21:41Z [implementation] — AC-1: ✓ review — decision #388 records a ruling for every one of the 58 rules, grouped: adopted 5, rejected as deliberate, rejected as cosmetic churn, split out 3; counts from the per-rule measurement logged above.
- 2026-09-23T23:21:41Z [implementation] — AC-2: ✓ measurement — pyproject select now E4,E7,E9,F,BLE001,PLE2515,PLE2502,PLR0124,B017,PYI036; findings fixed: 5 zero-width chars escaped by ruff --fix, 1 literal U+202E escaped, tausik_constants val!=val -> math.isnan, project_backend __exit__ annotation, 8 raises(Exception) narrowed (test_cascade_delete x4, test_graph_memory x2, test_tausik_backend x2) — 328 tests in those modules pass, so every narrowed type was the real one.
- 2026-09-23T23:21:41Z [implementation] — AC-3: ✓ measurement — negative: ruff check scripts tests bootstrap harness under the project config is clean on BOTH ruff 0.16.5 (PATH) and 0.15.12 (venv); tests/test_skill_content_scan.py and tests/test_brain_scrubbing.py still feed the same U+200B/U+202E characters (escapes build identical strings) and pass.
- 2026-09-23T23:21:42Z [implementation] — AC-4: ✓ review — negative: split out as tasks try-except-pass-sites-judged-against-silent-errors, open-without-context-manager-sites-judged, stale-noqa-comments-removed-with-a-ratchet (story deferred-110-audit-hygiene), not rejected.
