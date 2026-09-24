---
slug: renar-corpus-v11-reassessment
title: "Корпус RENAR перешёл на v1.1 — манифест заявляет renar-version 1.0, переоценка по §13.4.3"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/renar_br_premise.py (new: BR/level/implements premise + ratchet + the vacuous verdict), scripts/renar_mandatory_clauses.py (eighth clause), scripts/renar_normative_inapplicability.py (third declaration), scripts/renar_conformance.py (RENAR_VERSION), regenerated RENAR-CONFORMANCE.yaml and renar/conformance.md, tests, CHANGELOG EN/RU."
scope_exclude: null
relevant_files:
  - "scripts/renar_br_premise.py"
  - "scripts/renar_mandatory_clauses.py"
  - "scripts/renar_normative_inapplicability.py"
  - "scripts/renar_conformance.py"
  - "tests/test_renar_br_premise.py"
  - "tests/test_renar_mandatory_clauses.py"
  - "tests/test_renar_standard_drift.py"
  - "tests/test_renar_conformance.py"
scope_paths:
  - "scripts/renar_br_premise.py"
  - "scripts/renar_mandatory_clauses.py"
  - "scripts/renar_normative_inapplicability.py"
  - "scripts/renar_conformance.py"
  - "scripts/renar_standard_drift.py"
  - "renar/conformance.md"
  - "renar/specs/at-generation-procedure.md"
  - RENAR-CONFORMANCE.yaml
  - "tests/test_renar_br_premise.py"
  - "tests/test_renar_mandatory_clauses.py"
  - "tests/test_renar_standard_drift.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_normative_inapplicability.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "tausik/tasks/renar-corpus-v11-reassessment.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T18:24:28Z"
---

## Goal

ЗАМЕР, смена #247, 2026-09-12: внешний корпус стандарта ([вычеркнуто: dev-machine-path]/Kibertum/clients/kibertum/standards/renar, коммит 30f4a64 от 18:09) стал редакцией v1.1, а renar/conformance.md и RENAR-CONFORMANCE.yaml заявляют renar-version 1.0. tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us красный на этой машине: детектор 'standard' даёт version-behind (warn) — §13.4.3 требует re-assessment при minor-выпуске. Известно заранее (журнал our-conformance-generator-cites-the-wrong-chapter): §13.3.8 implements-edge на v1.1 становится обязательным — положений восемь, а не семь. Контекст владельца: решение об отказе от заявки RENAR-1 (§1.5.4, internal product) — переоценка может быть подъёмом версии манифеста и восьмым положением, а не новой заявкой; это решение владельца, не агента.

## Acceptance Criteria

AC-1: the owner's choice is recorded as a decision before any edit: bump the manifest to renar-version 1.1 with §13.3.8 assessed, or keep 1.0 and declare the re-assessment pending with a date. AC-2: whichever is chosen, test_renar_standard_drift::test_the_live_corpus_agrees_with_us is green on a machine with the v1.1 corpus and still skips cleanly without one. AC-3 (negative): a corpus edition ahead of the manifest is still reported as version-behind by the detector (unit test with a synthetic corpus), so the fix is the assessment, not the detector. AC-4: the eighth clause §13.3.8 (implements-edge) is either met and evidenced, or listed under unmet-clauses — never silently omitted. AC-5: full lane green; CHANGELOG EN/RU.

## Plan

[{"step": "Decision recorded; renar_br_premise.py: level/BR/implements carriers, premise_broken ratchet, implements_edge_clause", "done": true}, {"step": "Eighth clause in eval_mandatory_clauses, third normative-inapplicability declaration, RENAR_VERSION 1.1; tests (count 8, ratchet positive/negative, live DB premise holds)", "done": true}, {"step": "Regenerate manifest + renar/ export, drift test green on the v1.1 corpus, CHANGELOG, verify, close", "done": true}]

## Rollback

git revert коммита переоценки; манифест возвращается к 1.0.

## Journal

- 2026-09-12T17:27:55Z [planning] — ASSESSMENT PREPARED (session #250), no edit made — AC-1 is the owner's decision. Corpus at commit c3dd6b0 (v1.1). §13.3.8 text: implements[] is mandatory on BR with level=subsystem whose parent system has >=1 approved BR; the carrier must run the implements-edge validation control point of §10.11.1. Our substrate: NO BR class and NO level column exist (backend_schema_specs holds specs/task_specs/adapts; the 'implements' relation in task_specs and in the artifact graph is task→spec / code→requirement, not BR→BR). So the clause's subject has no carrier here — the same shape as §13.3.5 today (basis 'vacuous', renar_tc_premise ratchet). Recommended shape of the eighth verdict: key 'implements-edge-subsystem', confirmed true, basis 'vacuous', premise-watched-by a ratchet that goes red the moment a table or column holding a BR level appears; the §10.11.1 control point listed under normative-inapplicability with the same premise (an implements[] on a BR cannot be written, so a gate over it would be the degenerate control §13.9.4 forbids). Migration guide 12-migration-v11.md rows 3 and 9 are the only mandatory re-assessments: row 3 (§13.3.5 on the set version) stays vacuous for us (no TC class). Rows 1/2/4/15/19 (status/version removed from SPEC, TC schema) touch RENAR-2+ signals only; with level: null no claim is affected, but the manifest's lifecycle_statuses_used signal must be re-read under v1.1 semantics in the same edit. Owner's choice: (a) bump renar-version to 1.1, manifest-version +1, eighth verdict as above, drift test green; or (b) keep 1.0 and declare the re-assessment pending with a date. Estimated cost of (a): one medium task (generator + mandatory clauses module + ratchet test + docs), ~1 session.
- 2026-09-12T18:24:25Z [implementation] — AC-1 ✓ decision #364 recorded before any edit (option (a), owner's 'продолжай по всем задачам' after the recommendation). AC-2 ✓ tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us green on this machine against corpus c3dd6b0 (v1.1); the same test skips via corpus_root() None where no corpus is configured (unchanged path). AC-3 ✓ tests/test_renar_standard_drift.py::test_a_newer_edition_is_a_finding — synthetic corpus v1.1 against our_version 1.0 still reports version-behind; the detector was not touched. AC-4 ✓ RENAR-CONFORMANCE.yaml: mandatory-clauses-confirmed.implements-edge-subsystem: true with basis vacuous and premise-watched-by (tests/test_renar_mandatory_clauses.py::test_every_clause_carries_a_basis_from_the_closed_list — 8 clauses, ::test_the_bases_are_what_the_measurement_table_decided, ::test_the_named_watches_resolve_to_real_tests); the §10.11.1 control point under normative-inapplicability (tests/test_renar_br_premise.py::test_the_control_point_declaration_is_registered_and_watched); ratchet positive on three carrier kinds ::test_a_carrier_of_any_kind_breaks_the_premise[3 ids], negative ::test_a_level_column_without_subsystem_is_not_a_carrier, canonical schema holds ::test_the_canonical_schema_holds_the_premise. AC-5 ✓ 306 RENAR tests + 91 doc guards green; renar export --check OK; CHANGELOG EN/RU entry; whats-new figure recounted 228 → 229 by its own guard; verify run #2539 signed. Root cause (edge-case): the corpus edition moved under us and the manifest's version was a literal nothing re-assessed — prevention: the drift detector already reddens on version-behind (that is what caught it), and the eighth clause now carries a schema ratchet that runs in CI, unlike the TC premise guard. Domain: an auditor reading the manifest sees renar-version 1.1, an eighth confirmation whose basis says it is vacuous and why, and the exact function that would end the vacuity — no true reads as a measurement.
