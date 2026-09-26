---
slug: the-closure-auditor-reads-class-method-and-param-c
title: "The closure auditor reads Class::method and [param] citations as never-existed since the extractor learned them"
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
  - "scripts/audit_closure_evidence.py"
  - "tests/test_audit_closure_evidence.py"
  - "tausik/gates.json"
  - "scripts/closure_citation_check.py"
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T15:18:31Z"
---

## Goal

scripts/audit_closure_evidence._classify splits a citation once on '::' and looks the remainder up as ONE name, so 'tests/x.py::TestA::test_b' and 'tests/x.py::test_b[en]' — forms the extractor reads whole since GitLab #16 (46161e24) — never match the module's names and fall to git log -S, which cannot find 'TestA::test_b' either: verdict NEVER_EXISTED. Measured live: tausik coherence reports HIGH 908 never-existed against the declared remainder of 39; 872 of the 908 are Class::method and 10 are [param] forms; task done printed the NOTE on three committed tests this session. The auditor must resolve the chain (every segment a def/class in the module, the [param] id stripped) and the remainder must be re-measured.

## Acceptance Criteria

AC-1: audit_closure_evidence classifies 'tests/t.py::TestA::test_b' and 'tests/t.py::test_b[en]' as RESOLVED when TestA and test_b are defined in the module; unit tests in tests/test_audit_closure_evidence.py. AC-2 (negative): 'tests/t.py::TestA::test_missing' stays NEVER_EXISTED with a successor candidate, and 'tests/t.py::TestNope::test_b' (class not in the module) is not resolved either; and the pre-fix behaviour is reproduced as the failing case (the same Class::method ref under the old single-name lookup → NEVER_EXISTED). AC-3: live re-measurement after the fix — tausik coherence no longer reports the 908 HIGH; the counts in tausik/gates.json closure_evidence.baseline are set to the measured numbers with the reason written beside them, and tests/test_closure_evidence_remainder.py passes. AC-4: closure_citation_check prints no NOTE for the three committed citations of this session (test_publish_cli Class::method, test_release_notes_1_9 Class::method and [en]); verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T14:52:35Z [implementation] — Measured before the fix: tausik audit evidence --json -> counts rotted 87 / never_existed 908 / illustrative 16; by form: never_existed class::method 872, method[param] 10, file 21, method 5; rotted class::method 17. tausik coherence: [HIGH] 908 closure citation(s) name a test git NEVER had — ABOVE the declared remainder of 39. Cause: 46161e24 widened TEST_REF_RE to whole node ids; _classify still does ref.partition('::') and looks up 'TestA::test_b' as one name.
- 2026-09-13T14:56:34Z [implementation] — Fix: audit_closure_evidence.member_segments cuts the [param] id at the first bracket, then splits the chain on '::'; _classify requires every segment among the module's def/class names, asks git and offers a successor for the FIRST missing one. No regex (convention #301, structural test). Re-measured live after bootstrap redeploy: rotted 99 / never_existed 35 (was 87/39 declared, 908 never_existed measured under the defect); tausik coherence now [LOW] 99 and [LOW] 35 'declared remainder, unchanged' — the HIGH 908 is gone. Spot-checked the 9 Class::method left in never_existed: e.g. test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file — the method exists (line 295), the CLASS never did (git -S empty): the verdict is right (convention #669). tausik/gates.json baseline set to 99/35 with the reason beside it.
- 2026-09-13T15:12:53Z [implementation] — Review (tausik-reviewer): 2 HIGH, 1 MEDIUM, 1 LOW — all applied. (1) chain is followed STRUCTURALLY: test_b must sit in the body of TestA (missing_in_chain, module_of, _child_named); a single segment keeps the flat lookup; (2) every missing link is asked of git and the WORST answer is the verdict (NEVER_EXISTED > ROTTED > UNKNOWN), missing_segments carried in the finding; (3) gates.json comment reconciled PER CITATION against the 09-12 pair — old extractor + old auditor re-run today reproduce 87/39 exactly; new 99/35 explained by key (28 keys stay as 31 ids, 11 keys no longer findings, 4 new: 3 ecosystem examples from the GitLab #16 journal + 1 class-exists-method-never; rotted 82 keys stay as 91 ids, 5 gone, 8 new leaves renamed under living classes); (4) the tautological test replaced by a monkeypatched reproduction on the auditor itself (member_segments -> [member] gives NEVER_EXISTED for a committed Class::method; restored gives no finding); nested-class chain, misplaced leaf, invented leaf under a renamed class, bare name flat, empty chain all tested. Baseline set to 99/36: the 36th is this task's own journal quoting a wrong chain verbatim (memory #699). tausik coherence: 0 findings above declared. 32 tests in test_audit_closure_evidence; 159 in the six related files; mypy clean.
- 2026-09-13T15:18:28Z [implementation] — AC-1 ✓ tests/test_audit_closure_evidence.py::TestANodeIdIsAChainOfNames::test_class_and_method_both_defined_resolves (TestGroup::test_kept → no finding, resolved_unique 1), ::test_a_parametrised_id_is_the_method_it_names (TestGroup::test_kept[en] → no finding), ::test_a_nested_class_chain_is_followed_link_by_link (TestOuter::TestInner::test_leaf resolves; TestOuter::test_leaf names the skipped link), ::test_a_bare_name_keeps_the_flat_lookup, ::test_an_id_carrying_its_own_double_colon_is_cut_at_the_bracket. AC-2 ✓ (NEGATIVE) ::test_one_invented_link_is_never_existed_with_its_successor[invented-leaf] (TestGroup::test_kep → NEVER_EXISTED, successor test_kept) and [invented-class] (TestNope::test_kept → NEVER_EXISTED, successor TestGroup); ::test_a_method_defined_elsewhere_than_under_the_named_class_is_not_resolved (leaf at module level, chain wrong → a finding, missing_segments names the leaf); ::test_an_invented_leaf_under_a_renamed_class_is_never_existed_not_rot (worst verdict wins); ::test_a_member_that_reduces_to_no_segment_is_not_vacuously_resolved; pre-fix behaviour reproduced ON THE AUDITOR: ::test_the_old_single_name_lookup_is_what_produced_the_908 monkeypatches member_segments to the whole tail → NEVER_EXISTED for a committed Class::method; restored → no finding. AC-3 ✓ live re-measurement after bootstrap redeploy: tausik audit evidence --json → rotted 99 / never_existed 35 over done tasks (36 with this task's own journal, which quotes a wrong chain verbatim — memory #699); tausik coherence → 0 findings 'ABOVE the declared' (was [HIGH] 908); tausik/gates.json closure_evidence.baseline = 99/36 with _remeasured_2026_09_13 reconciled PER CITATION against the 09-12 pair (old extractor 8dac7a4c + old auditor re-run today reproduce 87/39 exactly: never_existed 28 keys stay as 31 ids, 11 keys no longer findings, 4 new; rotted 82 keys stay as 91 ids, 5 gone, 8 new leaves renamed under living classes); tests/test_closure_evidence_remainder.py passes (159 in the six related files). AC-4 ✓ scripts/closure_citation_check.py goes through the same auditor: the three citations of this session (test_publish_cli Class::method, test_release_notes_1_9 Class::method and [en]) classify RESOLVED (probe script: resolved_unique 3, the one invented name still named). verify run #2619 signed. Review: tausik-reviewer 2 HIGH (structural chain, worst verdict) + 1 MEDIUM (arithmetic) + 1 LOW (empty chain), all applied; the two structurally identical negatives parametrised, dedupe ratchet 290/686 held. mypy clean. Domain: a closure citation is judged by what the module DEFINES where the citation says, and the remainder is a reconciled measurement, not a remembered one.
- 2026-09-26T18:44:26Z [done] — EVIDENCE-UNPROVEN: test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file — git never carried this path or member under any directory
