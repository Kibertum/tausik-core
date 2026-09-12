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
