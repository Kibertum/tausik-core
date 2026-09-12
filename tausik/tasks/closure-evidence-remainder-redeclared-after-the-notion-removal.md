---
slug: closure-evidence-remainder-redeclared-after-the-notion-removal
title: "Closure-evidence remainder re-declared after the Notion removal"
status: done
epic: landscape-2026-h2
story: repo-hygiene-19
complexity: simple
role: qa
stack: python
tier: trivial
call_budget: 8
defect_of: null
scope: "One baseline block in tausik/gates.json and a decision; no journal is rewritten."
scope_exclude: "No edits to any closed task's journal; no change to the collector or the audit."
relevant_files:
  - "tausik/gates.json"
  - "tests/test_closure_evidence_remainder.py"
scope_paths:
  - "tausik/gates.json"
  - "tausik/tasks/closure-evidence-remainder-redeclared-after-the-notion-removal.md"
  - "tausik/stories/repo-hygiene-19.md"
  - "tausik/decisions"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T18:38:35Z"
---

## Goal

Rule 9.5 sweep, session #250: tausik coherence reports rotted closure citations 87 against the declared remainder 31 and never-existed 39 against 20. Attribution by git: 58 of the rotted refs are test files deleted with their subject by the Notion removal 77703c4a (decision #358); 14 of the 'never existed' are bare-name citations of test_brain_*.py that resolved by basename until the same commit deleted the files; 3 are this session's own citations, corrected in-journal by the closure warning (the collector counts the first citation, journals are append-only); 1 (tests/test_pwsh_write_gate_hook.py) is a named absence in the journal text. The remainder is a declared quantity that may only shrink, so raising it is a decision to be argued, not a chore.

## Acceptance Criteria

AC-1: decision recorded arguing the raise with the attribution (58 + 14 rotted with their subject in 77703c4a; 3 corrected in-journal; 1 named absence) before gates.json changes. AC-2: tausik/gates.json closure_evidence.baseline equals the measured 87/39 with the cause in the comment, and tausik coherence no longer reports the two HIGH closure-evidence findings. AC-3 (negative): the remainder stays a ceiling — a later run that measures above 87/39 is again ABOVE the declared remainder (collector unchanged, tests/test_repo_coherence.py green). AC-4: signed verify on tausik/gates.json.

## Plan

## Rollback

git revert of the one commit; the remainder returns to 31/20.

## Journal

- 2026-09-12T18:38:27Z [implementation] — AC-1 ✓ decision #365 recorded before the edit, attribution 58 + 14 (77703c4a) / 3 (corrected in-journal) / 1 (named absence). AC-2 ✓ tausik/gates.json closure_evidence.baseline = 87/39 with _remeasured_comment naming the cause; tausik coherence now reports both closure-evidence lines as LOW 'declared remainder, unchanged' instead of HIGH. AC-3 ✓ tests/test_closure_evidence_remainder.py::test_превышение_остатка_даёт_high (growth above the remainder is HIGH again), ::test_остаток_выше_измеренного_просит_подтянуть (a remainder above the measurement is itself a finding — no headroom), ::test_база_объявлена_и_названа_числом, ::test_причина_записана_рядом_с_числом; 22 passed. AC-4 ✓ verify run #2546 signed. Root cause (regression): the Notion removal deleted 32 test files that 72 closure citations named; the remainder was measured before that decision. Prevention: the remainder comment now names the removal commit, and the collector's ceiling catches the next growth. Domain: a reader of coherence sees 87 rotted citations with the commit that rotted them, not a silent HIGH.
