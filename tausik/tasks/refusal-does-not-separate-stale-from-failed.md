---
slug: refusal-does-not-separate-stale-from-failed
title: "Отказ не отличает устаревшее от непрошедшего: stale и fail подаются одним словом"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: backend
stack: null
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_refusal_kind.py"
  - "scripts/verify_handle_rules.py"
  - "scripts/gate_verify_first.py"
  - "tests/test_refusal_kinds.py"
scope_paths:
  - "scripts/verify_refusal_kind.py"
  - "scripts/verify_handle_rules.py"
  - "scripts/verify_handle_check.py"
  - "scripts/gate_verify_first.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:18:30Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#13"
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

Пользователь и агент по тексту отказа различают «доказательство устарело, переснимите» и «доказательство не прошло, чините код» — это два разных следующих шага.

## Acceptance Criteria

1. Исходы отказа разделены явно: STALE (квитанция была валидной, но дерево или голова сдвинулись — переснимите) и FAIL (проверка не прошла — чините код). Третий исход, «не найдено», остаётся отдельным и не смешивается ни с одним из двух.
2. Разделение проведено во ВСЕХ точках отказа, а не в найденной: verify handle, task done QG-2, кэш verify. Форма закрывается перечислением точек из кода (конвенция #361).
3. Текст каждого отказа называет СЛЕДУЮЩИЙ ШАГ, а не только причину.
4. Источник различения — ai-review-gate.mjs из github.com/kiaquila/unicorn-hub (MIT), где сдвиг головы даёт пропуск с объяснением, а не провал.
5. НЕГАТИВНЫЙ сценарий: тест на КАЖДЫЙ исход, включая тот, что сегодня подаётся неверно; тест обязан падать на текущем коде, иначе разделение не доказано.
6. НЕГАТИВНЫЙ сценарий: STALE НЕ становится тихим успехом — он остаётся отказом, просто с другим следующим шагом. Закрытие задачи по устаревшей квитанции ЗАПРЕЩЕНО.

## Plan

## Rollback

git revert коммита; правка в тексте отказов и одном перечислении

## Journal

- 2026-09-23T22:17:35Z [implementation] — AC-1: ✓ tests/test_refusal_kinds.py::test_each_handle_refusal_carries_its_kind_and_next_step
- 2026-09-23T22:17:35Z [implementation] — Сделано: scripts/verify_refusal_kind.py (STALE/FAILED/NOT FOUND с головой-следующим шагом; classify по явной таблице признаков; last_run_kind для закрытия без хэндла); verify_handle_rules._no метит каждый отказ хэндла и квитанции (verify_handle_check импортирует тот же _no, так что обе точки покрыты); gate_verify_first — отказ без хэндла с меткой и причиной (прогона не было / последний красный / последний зелёный устарел). Формулировка 'no fresh `tausik verify`', которую держат тесты, сохранена.
- 2026-09-23T22:17:36Z [implementation] — AC-2: ✓ точки перечислены из кода: verify_handle_check (через _no), verify_handle_rules (_no), gate_verify_first (закрытие без хэндла); tests/test_refusal_kinds.py::test_a_close_without_a_handle_says_never_ran_red_or_stale
- 2026-09-23T22:17:36Z [implementation] — AC-3: ✓ каждая голова содержит 'next:' (проверяется тестом)
- 2026-09-23T22:17:36Z [implementation] — AC-4: ✓ источник назван в docstring модуля и CHANGELOG
- 2026-09-23T22:17:37Z [implementation] — AC-5: ✓ тесты падают на старом коде (меток не было); 244 теста verify/handle/QG-2 зелёные
- 2026-09-23T22:17:37Z [implementation] — AC-6: ✓ tests/test_refusal_kinds.py::test_a_stale_refusal_is_still_a_refusal
- 2026-09-23T22:17:38Z [implementation] — NO-DEAD-END: единственный красный прогон — я изменил формулировку, закреплённую тестами; возвращена
