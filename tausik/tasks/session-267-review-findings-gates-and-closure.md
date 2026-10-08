---
slug: session-267-review-findings-gates-and-closure
title: "Ревью смены #267 (гейты и закрытие): ReDoS пользовательских регулярок RAG, dead-end --task с несуществующим слагом молча теряет привязку, metrics падает на цели без min/max, эскалация глотает ошибки молча"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/codebase-rag/rag_languages.py"
  - "harness/claude/mcp/codebase-rag/rag_indexer.py"
  - "scripts/dead_end_gate.py"
  - "scripts/metric_methods.py"
  - "scripts/render_metrics.py"
  - "tests/test_review_267_fixes.py"
  - "tests/test_senar.py"
  - "tests/test_memory_block.py"
  - "tests/test_state_projection_tracks_db.py"
scope_paths:
  - "harness/claude/mcp/codebase-rag/rag_languages.py"
  - "harness/claude/mcp/codebase-rag/rag_indexer.py"
  - "scripts/dead_end_gate.py"
  - "scripts/metric_methods.py"
  - "scripts/render_metrics.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T21:17:59Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

Три HIGH и один LOW из состязательного ревью (tausik-reviewer, смена #267) исправлены в коде этой же смены: пользовательская регулярка rag.boundaries не может повесить индексатор; dead_end с несуществующей задачей отказывает, а не пишет NULL; отчёт метрик не падает на кривой цели; сбой эскалации пересечения виден.

## Acceptance Criteria

1. rag.boundaries: регулярка с вложенными квантификаторами отвергается при загрузке с записью в problems; строка длиннее предела не подаётся pattern.match; тест с (a+)+$ завершается быстро.
2. НЕГАТИВНЫЙ: dead-end --task <несуществующий> отказывает с именем слага, ничего не пишет; тест.
3. НЕГАТИВНЫЙ: metric_targets с basis, но без min/max, не применяется и называется в заметках; tausik metrics не падает; блок методов в render_metrics в том же try/except, что остальные секции; тест.
4. Сбой escalate печатает строку в stderr, а не глотается молча; тест.
5. CHANGELOG EN+RU.

## Plan

## Rollback

git revert; правки локальны в rag_languages/rag_indexer, dead_end_gate, metric_methods/render_metrics

## Journal

- 2026-09-23T21:02:44Z [implementation] — AC-1: ✓ tests/test_review_267_fixes.py::test_a_nested_quantifier_regex_is_refused_at_load
- 2026-09-23T21:02:44Z [implementation] — Сделано по ревью (tausik-reviewer): rag_languages отвергает вложенные квантификаторы (_NESTED_QUANTIFIER), rag_indexer подаёт регулярке первые 400 символов строки; dead_end_gate.bind_task проверяет существование задачи; metric_methods.targets не применяет цель без min/max, render_metrics оборачивает блок методов в try/except, escalate печатает сбой в stderr. Затронутые тесты (test_senar, test_memory_block, test_state_projection_tracks_db) давали несуществующий t1 — получили настоящую задачу. LOW про MIN_REASON и устаревающие цифры basis — не правлю: осознанный компромисс и предмет релизного чек-листа.
- 2026-09-23T21:02:45Z [implementation] — AC-1: ✓ tests/test_review_267_fixes.py::test_a_long_line_cannot_make_a_boundary_regex_run_long
- 2026-09-23T21:02:45Z [implementation] — AC-2: ✓ tests/test_review_267_fixes.py::test_a_dead_end_naming_a_missing_task_is_refused
- 2026-09-23T21:02:46Z [implementation] — AC-3: ✓ tests/test_review_267_fixes.py::test_a_target_without_a_bound_is_not_used_and_the_report_survives
- 2026-09-23T21:02:46Z [implementation] — AC-4: ✓ tests/test_review_267_fixes.py::test_a_failing_escalation_is_said_out_loud
- 2026-09-23T21:02:46Z [implementation] — AC-5: ✓ CHANGELOG EN+RU. NO-DEAD-END: красные прогоны — тесты с несуществующей задачей t1, которые новое правило законно отвергло
