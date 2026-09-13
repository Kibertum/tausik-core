---
slug: gates-json-quoted-the-invented-chain-verbatim-and-
title: "gates.json quoted the invented chain verbatim and the citation guard refuses it"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tausik/gates.json"
  - "tests/test_gate_class_surface.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T15:28:50Z"
---

## Goal

tests/test_gate_class_surface.py::test_every_test_gates_json_cites_actually_exists holds every file::node citation in tausik/gates.json to a real symbol; the _remeasured_2026_09_13 comment written in task the-closure-auditor-reads-class-method-and-param-c quoted tests/test_hooks.py::TestBashFirewall::test_dangerous_commands_blocked[...] as the EXAMPLE of a citation git never had — the same trap as memory #699, one hour later, in a file the guard reads. The full lane went red on exactly that test (1 failed, 10562 passed).

## Acceptance Criteria

AC-1: the comment names the example by its task (l26-firewall-quote-regression) and by a paraphrase, not by a node id; test_every_test_gates_json_cites_actually_exists passes. AC-2 (negative): the guard's own negative test test_the_guard_refuses_an_invented_citation still refuses an invented citation, and before the edit the guard failed on the quoted chain (measured in the full lane). AC-3: tests/test_closure_evidence_remainder.py and tests/test_gate_class_surface.py pass; verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T15:27:40Z [implementation] — AC-2 (negative) measured BEFORE the edit: full lane on the working tree — FAILED tests/test_gate_class_surface.py::test_every_test_gates_json_cites_actually_exists (1 failed, 10562 passed, 21 skipped): gates.json promised a node id whose method git never had, because the auditor task's comment quoted it verbatim as an example.
- 2026-09-13T15:28:47Z [implementation] — AC-1 ✓ tausik/gates.json names the example by its task (l26-firewall-quote-regression) and a paraphrase; tests/test_gate_class_surface.py::test_every_test_gates_json_cites_actually_exists passes. AC-2 ✓ (NEGATIVE) ::test_the_guard_refuses_an_invented_citation passes (the guard still refuses); before the edit the guard failed on the quoted chain — full lane, logged above. AC-3 ✓ tests/test_closure_evidence_remainder.py + tests/test_gate_class_surface.py: 29 passed; verify run #2621 signed. Memory #700 (gotcha) recorded. Domain: two readers of verbatim node ids — the journal extractor and the gates.json guard — and the example is named by task in both.
