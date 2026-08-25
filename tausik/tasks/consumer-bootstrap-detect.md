---
slug: consumer-bootstrap-detect
title: "bootstrap_config.detect_stacks consumes registry"
status: done
epic: v16-plugin-arch-and-docs
story: refactor-consumers
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap_config.py"
scope_exclude: "scripts/stack_registry.py, остальные consumers"
relevant_files:
  - "bootstrap/bootstrap_config.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:59:58Z"
---

## Goal

Drop hardcoded STACK_SIGNATURES dict. detect_stacks() now iterates registry.all_stacks() and uses registry.signatures_for(name) for matching. _signature_match logic preserved (3-form pattern matching). Signatures format consistent with stack.json detect: array.

## Acceptance Criteria

1. bootstrap/bootstrap_config.detect_stacks читает signatures из stack_registry (default_registry().signatures_for(stack) over all_stacks()) вместо хардкод-STACK_SIGNATURES.
2. STACK_SIGNATURES оставлен как fallback (для случаев когда registry недоступен) или удалён, если безопасно.
3. _signature_match сохраняет 3 формы (exact / glob / dir-marker) и keyword-фильтр.
4. После рефакторинга detect_stacks в проекте с pyproject.toml возвращает ['python'] (как раньше).
5. detect_stacks с проектом без pyproject.toml но с *.tf файлами возвращает ['terraform'].
6. Тесты test_iac_bootstrap_detection.py — все проходят.
7. pytest tests/ -q (все stack-related): 0 регрессий.
8. **Negative scenario:** registry import fails → fallback на хардкод STACK_SIGNATURES (или логирование + empty list, не crash).

## Plan

## Rollback

## Journal

- 2026-04-25T16:59:58Z [implementation] — AC verified: 1. ✓ STACK_SIGNATURES вычисляется через _load_stack_signatures() из default_registry().signatures_for() — 25 стэков. 2. ✓ _FALLBACK_STACK_SIGNATURES оставлен (сужена до 17 legacy стэков) для случая когда registry-load падает. 3. ✓ _signature_match не тронут (3 формы + keyword). 4. ✓ detect_stacks('.') в этом проекте → ['python'] (pyproject.toml). 5. ✓ docker→[Dockerfile,Containerfile], terraform→[*.tf,*.tfvars] — корректно собираются из registry. 6. ✓ test_iac_bootstrap_detection.py: 18/18 проходят. 7. ✓ pytest stack-related: 307 passed, 0 регрессий. 8. ✓ Negative scenario: try/except → fallback на _FALLBACK_STACK_SIGNATURES, log.warning. bootstrap_config.py 276 строк <400.
