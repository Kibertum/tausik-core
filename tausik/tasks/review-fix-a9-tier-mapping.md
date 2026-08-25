---
slug: review-fix-a9-tier-mapping
title: "[A9 HIGH] _run_quality_gates: complexity→tier вместо hardcoded lightweight"
status: done
epic: senar-verify-redesign
story: review-findings-fix
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_gates.py, tests/test_service_verification.py"
scope_exclude: "scripts/service_verification.py (helper интерфейс stays)"
relevant_files:
  - "scripts/service_gates.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:15:17Z"
---

## Goal

Multi-agent review: _run_quality_gates в service_gates.py:382 хардкодит scope='lightweight' для всех задач. Это нарушает SENAR Rule 5 дизайн (complex tasks с security должны попадать в critical tier). _determine_checklist_tier уже существует (service_gates:276) — надо использовать его + is_security_sensitive из service_verification для derivation. Без фикса verification_runs.scope всегда 'lightweight', аудит по scope='critical' вернёт 0 строк.

## Acceptance Criteria

1. _run_quality_gates получает task dict (через self._require_task(slug)) и резолвит scope через _determine_checklist_tier(task) вместо hardcoded 'lightweight'
2. Если is_security_sensitive(relevant_files) → scope='critical' (overrides tier)
3. Регрессия: simple task без security → scope='lightweight' как раньше
4. Регрессия: medium task без security → scope='standard' (раньше hardcoded 'lightweight' — это БЫЛО неправильно, теперь правильно)
5. Регрессия: complex task → scope='high' (или 'critical' если security)
6. verification_runs.scope теперь отражает реальный tier — auditable
7. Новый тест: test_run_quality_gates_uses_complexity_tier — monkeypatch fakegate, check scope в записанном run
8. Ошибка/граничный случай: task без поля complexity (None или отсутствует) → fallback scope='standard' (по дефолту в _determine_checklist_tier), не crash
9. Ошибка/граничный случай: relevant_files=None → нет security check, scope резолвится только из complexity
10. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:15:15Z [implementation] — AC verified: ✓1 _run_quality_gates: task = self.be.task_get(slug); scope = self._determine_checklist_tier(task) ✓2 is_security_sensitive(relevant_files) override → scope='critical' ✓3 simple→lightweight (regression, _determine_checklist_tier covers) ✓4 medium→standard (раньше hardcoded lightweight, теперь правильно) ✓5 complex→critical (через _determine_checklist_tier) ✓6 verification_runs.scope auditable — confirmed test_scope_recorded_as_passed assert row['scope']=='standard' и test_critical_scope_forwarded assert 'critical' ✓7 +2 теста в TestRunGatesWithCacheScopePropagation ✓8 task без complexity → _determine_checklist_tier дефолтит 'medium'→'standard' (existing behavior) ✓9 relevant_files=None → is_security_sensitive([])=False ✓10 pytest 110/110, ruff clean
