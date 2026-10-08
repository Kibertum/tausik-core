---
slug: class-surface-baseline-podnyat-pod-routing-matrix
task: at-red-with-tc-green-routes-to-interpretation-not-code
date: "2026-09-06"
edges: []
---

## Decision

class_surface baseline поднят под routing-matrix: SQLiteBackend 155→158 (+3: at_result_add/at_results_for/at_latest_outcome), ProjectService 140→143 (+3: at_record_result/at_diagnose/at_release_readiness). route_at_tc — ЧИСТАЯ функция, намеренно оставлена module-level (не метод), поэтому не входит в счёт — та же экономия, что normalize_usage_time_bound уже применяет.

## Rationale

at-red-with-tc-green-routes-to-interpretation-not-code добавила append-only историю исходов AT + диагностику/релизную готовность — новая функциональность того же класса, что решения #327-#329.
