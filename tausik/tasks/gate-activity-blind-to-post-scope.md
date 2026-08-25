---
slug: gate-activity-blind-to-post-scope
title: "Defect: metrics gate_activity строит known-список из get_gates_for_trigger — post-scope гейт, ни разу не сработавший, невидим"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 18
defect_of: gate-registry-single-source
scope: "scripts/backend_queries_metrics.py, tests/test_gate_runs_persist.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/gate_run_record.py (gate_activity сам корректен — он честно докладывает то, что ему передали), scripts/gate_registry.py, scripts/project_config.py (фильтр фаз верен и остаётся)"
relevant_files:
  - "scripts/backend_queries_metrics.py"
  - "tests/test_gate_runs_persist.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T21:34:58Z"
---

## Goal

gate-registry-single-source ввёл фазу post_scope и исключил такие гейты из get_gates_for_trigger (они не имеют сигнатуры (gate, files) и раннер не должен их звать). Но backend_queries_metrics.gate_activity_summary строит список ИЗВЕСТНЫХ гейтов именно из get_gates_for_trigger("verify"/"task-done") — значит verify_first и changelog в него не попадают. Последствие точечное, но ровно то, против чего заведена конвенция #226: строки, которые гейт уже записал, в отчёте видны (они приходят из таблицы), а гейт, который НИ РАЗУ не сработал, не появится с runs=0 — «эта охрана не срабатывала ни разу» отрендерится тишиной. Это самый ценный факт, который таблица gate_runs умеет сказать, и именно он теряется. Цель: known-список собирается из ОБЕИХ фаз — триггерные гейты плюс post-scope из реестра (gate_registry.specs_for_phase), с тестом на то, что никогда не запускавшийся post-scope гейт попадает в never_fired.

## Acceptance Criteria

1. `gate_activity_summary` собирает known-список из обеих фаз: триггерные гейты (get_gates_for_trigger для "verify" и "task-done") плюс post-scope гейты из `gate_registry.specs_for_phase(PHASE_POST_SCOPE)`. Best-effort остаётся best-effort: сбой чтения конфига не должен обнулять реестровую часть — реестр это статика в памяти, он доступен даже когда конфиг сломан.
2. Тест: post-scope гейт, для которого в gate_runs НЕТ ни одной строки, попадает в `never_fired` с runs=0 (конвенция #226 — «ни разу не срабатывал» не рендерится тишиной).
3. Тест: post-scope гейт со строками отражается корректно (runs/failures), дублей в known-списке нет.
4. Регресс: tests/test_gate_runs_persist.py и tests/test_gate_runs_failures.py зелёные; полный pytest зелёный.
5. CHANGELOG.md + CHANGELOG.ru.md обновлены (конвенция #275).

## Plan

## Rollback

git revert коммита. Изменение локально в одном методе (расширение списка known), схема и данные не трогаются.

## Journal

- 2026-07-23T21:34:56Z [implementation] — Root cause: gate-registry-single-source introduced the post_scope phase and correctly excluded those gates from get_gates_for_trigger (they take the close context, not (gate, files)) - but did not audit the OTHER readers of that function. backend_queries_metrics.gate_activity_summary used it as its source of 'known gates', so the exclusion silently narrowed the metrics report. The general lesson: narrowing a shared query is a change to every consumer of it, not only to the caller you narrowed it for. AC1 PASS - known set now spans both phases; the registry half is gathered outside the config try-block. AC2 PASS - tests/test_gate_runs_persist.py::TestKnownSetSpansBothPhases::test_never_fired_post_scope_gate_is_visible (verify_first and changelog appear in never_fired with runs=0). AC3 PASS - test_post_scope_rows_are_counted_and_not_duplicated (one row, runs=1, no duplicate from the union). Plus test_broken_config_cannot_blank_the_registry_half. AC4 PASS - test_gate_runs_persist + test_gate_runs_failures + test_gate_registry: 47 passed; ruff All checks passed. AC5 PASS - CHANGELOG.md and CHANGELOG.ru.md updated. Negative: the defect itself is the negative scenario and is asserted directly - with the fix reverted, test_never_fired_post_scope_gate_is_visible fails because a gate with zero rows is absent from the report rather than listed with runs=0; test_broken_config_cannot_blank_the_registry_half covers the unreadable-config branch. Domain: outside the tests the report now answers the question it exists to answer for a real project - .tausik/tausik gates status lists 12 gates and the metrics known-set covers all of them, so a QG-2 gate that never fires is legible as a fact instead of as silence. Encoding note: an intermediate PowerShell edit added a BOM and mangled non-ASCII in the test file; caught by a byte check, reverted via git checkout and redone with the editor - recorded as memory #285 because a green suite does NOT catch it.
- 2026-07-23T21:35:08Z [done] — Root cause (regression): сужение общего запроса get_gates_for_trigger (исключение фазы post_scope) было верным для его вызывающего — раннера гейтов, — но выполнено без аудита ОСТАЛЬНЫХ потребителей; gate_activity_summary использовал ту же функцию как источник «известных гейтов», поэтому исключение молча сузило метрики, и post-scope гейт с нулём строк исчез из отчёта вместо runs=0. Prevention: сужение общей функции-запроса — это изменение для КАЖДОГО её потребителя, а не только для того, ради кого сужали; перед изменением семантики shared-запроса грепать все call-sites и решать по каждому явно. В самой задаче это правило нарушено дважды подряд (сначала в реестре, потом поймано только сквозной проверкой), поэтому оно записано конвенцией, а не только здесь.
