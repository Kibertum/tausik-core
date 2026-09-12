---
slug: renar-corpus-v11-reassessment
title: "Корпус RENAR перешёл на v1.1 — манифест заявляет renar-version 1.0, переоценка по §13.4.3"
status: planning
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "renar/conformance.md"
  - RENAR-CONFORMANCE.yaml
  - "scripts/renar_conformance.py"
  - "scripts/renar_standard_drift.py"
  - "tests/test_renar_standard_drift.py"
  - "tests/test_renar_conformance.py"
  - "docs/en/renar*.md"
  - "docs/ru/renar*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/renar-corpus-v11-reassessment.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #247, 2026-09-12: внешний корпус стандарта (d:/Work/Kibertum/clients/kibertum/standards/renar, коммит 30f4a64 от 18:09) стал редакцией v1.1, а renar/conformance.md и RENAR-CONFORMANCE.yaml заявляют renar-version 1.0. tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us красный на этой машине: детектор 'standard' даёт version-behind (warn) — §13.4.3 требует re-assessment при minor-выпуске. Известно заранее (журнал our-conformance-generator-cites-the-wrong-chapter): §13.3.8 implements-edge на v1.1 становится обязательным — положений восемь, а не семь. Контекст владельца: решение об отказе от заявки RENAR-1 (§1.5.4, internal product) — переоценка может быть подъёмом версии манифеста и восьмым положением, а не новой заявкой; это решение владельца, не агента.

## Acceptance Criteria

AC-1: the owner's choice is recorded as a decision before any edit: bump the manifest to renar-version 1.1 with §13.3.8 assessed, or keep 1.0 and declare the re-assessment pending with a date. AC-2: whichever is chosen, test_renar_standard_drift::test_the_live_corpus_agrees_with_us is green on a machine with the v1.1 corpus and still skips cleanly without one. AC-3 (negative): a corpus edition ahead of the manifest is still reported as version-behind by the detector (unit test with a synthetic corpus), so the fix is the assessment, not the detector. AC-4: the eighth clause §13.3.8 (implements-edge) is either met and evidenced, or listed under unmet-clauses — never silently omitted. AC-5: full lane green; CHANGELOG EN/RU.

## Plan

## Rollback

git revert коммита переоценки; манифест возвращается к 1.0.

## Journal

- 2026-09-12T17:27:55Z [planning] — ASSESSMENT PREPARED (session #250), no edit made — AC-1 is the owner's decision. Corpus at commit c3dd6b0 (v1.1). §13.3.8 text: implements[] is mandatory on BR with level=subsystem whose parent system has >=1 approved BR; the carrier must run the implements-edge validation control point of §10.11.1. Our substrate: NO BR class and NO level column exist (backend_schema_specs holds specs/task_specs/adapts; the 'implements' relation in task_specs and in the artifact graph is task→spec / code→requirement, not BR→BR). So the clause's subject has no carrier here — the same shape as §13.3.5 today (basis 'vacuous', renar_tc_premise ratchet). Recommended shape of the eighth verdict: key 'implements-edge-subsystem', confirmed true, basis 'vacuous', premise-watched-by a ratchet that goes red the moment a table or column holding a BR level appears; the §10.11.1 control point listed under normative-inapplicability with the same premise (an implements[] on a BR cannot be written, so a gate over it would be the degenerate control §13.9.4 forbids). Migration guide 12-migration-v11.md rows 3 and 9 are the only mandatory re-assessments: row 3 (§13.3.5 on the set version) stays vacuous for us (no TC class). Rows 1/2/4/15/19 (status/version removed from SPEC, TC schema) touch RENAR-2+ signals only; with level: null no claim is affected, but the manifest's lifecycle_statuses_used signal must be re-read under v1.1 semantics in the same edit. Owner's choice: (a) bump renar-version to 1.1, manifest-version +1, eighth verdict as above, drift test green; or (b) keep 1.0 and declare the re-assessment pending with a date. Estimated cost of (a): one medium task (generator + mandatory clauses module + ratchet test + docs), ~1 session.
