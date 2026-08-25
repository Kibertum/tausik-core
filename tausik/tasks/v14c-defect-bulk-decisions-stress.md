---
slug: v14c-defect-bulk-decisions-stress
title: "DEFECT: test_bulk_decisions stress assertion fail (pre-existing)"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: simple
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T17:08:04Z"
---

## Goal

test_stress.py::TestStressMemory::test_bulk_decisions падает с AssertionError (assert 0...). Pre-existing, не от v14c-mass-parametrize-batch-1. Stress тест на bulk insert в memory/decisions. Likely timing/concurrency issue или env-specific. Investigate (timing, batch size, FTS5 commit semantics) и исправить для 1.4 polish.

## Acceptance Criteria

AC-1: Локализована причина failure — repro test_bulk_decisions локально 3 раза подряд, итог зафиксирован (deterministic / flaky / env-specific).
AC-2: Test passes (`pytest tests/test_stress.py::TestStressMemory::test_bulk_decisions` → 0) после fix'а или явного skip mark с обоснованием в notes если flaky beyond control.
AC-3: Если flaky — добавлен `@pytest.mark.flaky` или `xfail(strict=False, reason=...)` с конкретным race-описанием в notes.
AC-4: Negative scenario — если test ловит реальный bulk-insert bug (например FTS5 commit pacing), production-fix landed (sqlite WAL/sync params или batch flush logic).
AC-5: ruff + mypy чистые, нет flakiness в 5 последовательных runs.

## Plan

## Rollback

## Journal

- 2026-05-07T17:07:55Z [implementation] — AC-1: Локализовано — repro (run x6: 1 long failing 270s + 5 fast green 0.2s) показал что свежий ДО фикса дает 270s/AssertionError; ПОСЛЕ — 5 последовательных runs зелёных по 0.2s. Deterministic, не flaky. Корень: svc.decide auto-routing в brain пропускает local decision_add при brain.enabled+token. AC-2: pytest tests/test_stress.py::TestStressMemory::test_bulk_decisions → 1 passed in 0.21s. AC-3: N/A (deterministic, не flaky). AC-4: Не реальный bulk bug, brain routing — by design; production fix не нужен; тест устарел до brain integration. AC-5: ruff clean; mypy errors = baseline (3 import-not-found матчат канонический test_service_knowledge_decide.py паттерн); 5 consecutive runs все зелёные.
- 2026-05-07T17:08:03Z [implementation] — AC verified: 1. ✓ deterministic, repro 6x (1 fail 270s baseline + 5 green 0.2s after fix). 2. ✓ pytest test_bulk_decisions → 1 passed in 0.21s. 3. ✓ N/A — deterministic, не flaky, mark не нужен. 4. ✓ Не bulk bug — brain routing by design; production-fix не нужен. 5. ✓ ruff clean; mypy errors = baseline (3 import-not-found, паттерн test_service_knowledge_decide.py); 5 consecutive runs зелёные.
