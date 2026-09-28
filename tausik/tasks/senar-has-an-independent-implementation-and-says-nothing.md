---
slug: senar-has-an-independent-implementation-and-says-nothing
title: "У SENAR есть независимое внедрение, и об этом не сказано ни на сайте, ни в README"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-outward-loop-and-test-authorship
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "docs/**"
  - "*.md"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#110"
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

Читатель SENAR видит, что стандарт применён не только его авторами: стандарт с двумя реализациями читается иначе, чем стандарт с одной.

## Acceptance Criteria

1. Названо внедрение: kiaquila/unicorn-hub несёт docs/senar-mapping.md и спеку 003-senar-process-layer, реализуя SENAR как supervised verification layer. Проверено чтением файлов, не по описанию репозитория.
2. Упоминание стоит на первом экране senar.tech и в README репозитория SENAR, а не в глубине.
3. Формулировка НЕ преувеличивает: это одно внедрение возрастом меньше полугода, а не признание отрасли. Слово «внедрения» во множественном числе без второго примера ЗАПРЕЩЕНО.
4. НЕГАТИВНЫЙ сценарий: если внедрение исчезнет или перестанет соответствовать SENAR, упоминание снимается. Проверка раз в релиз.

## Plan

## Rollback

git revert правки README; изменения только в тексте

## Journal
