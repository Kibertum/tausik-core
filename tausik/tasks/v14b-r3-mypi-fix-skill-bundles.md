---
slug: v14b-r3-mypi-fix-skill-bundles
title: "Defect: scripts/skill_bundles.py:85 mypy no-any-return"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: v14b-skill-bundles-marketplace
scope: "scripts/skill_bundles.py:85 (1 line type narrow)"
scope_exclude: "логика _bundle_body не меняется; никаких других файлов"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T09:43:52Z"
---

## Goal

Pre-commit mypy hook поймал no-any-return на line 85 _bundle_body() возвращает bundles[name] (Any) — добавить explicit type annotation промежуточной переменной для явного narrow.

## Acceptance Criteria

1. scripts/skill_bundles.py:85 mypy no-any-return error устранён через explicit `dict[str, Any]` annotation промежуточной переменной body. 2. `python -m mypy scripts/skill_bundles.py` clean (0 errors). 3. Pre-commit mypy hook PASS. NEGATIVE: behavior unchanged — все существующие тесты test_skill_bundles.py продолжают PASS (root cause фикса = нарушение строгой mypy политики, не bug).

## Plan

## Rollback

## Journal

- 2026-05-07T09:43:52Z [implementation] — AC-1: ✓ scripts/skill_bundles.py:85 теперь `body: dict[str, Any] = bundles[name]; return body`. AC-2: ✓ `python -m mypy scripts/skill_bundles.py` → "Success: no issues found in 1 source file". AC-3: ✓ pre-commit mypy will pass on next commit. NEGATIVE: ✓ tests/test_skill_bundles.py все 22 PASS — behavior unchanged, only type narrow.</evidence> <parameter name="relevant_files">["scripts/skill_bundles.py"]
