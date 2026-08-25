---
slug: v14b-tools-extra-preempt-split-split-tools-extra-p
title: "v14b-tools-extra-preempt-split: split tools_extra.py 399→2 files (admin tools out)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "harness/claude/mcp/project/tools_extra.py (удалить stack+roles), harness/claude/mcp/project/tools_extra_admin.py (новый), harness/claude/mcp/project/tools.py (импорт+extend), zerkalo для cursor/, CHANGELOG.{md,ru.md}."
scope_exclude: "scripts/ (не трогать), bootstrap/ (не трогать — bootstrap читает harness/* и копирует в .claude/), handlers.py (не трогать — schema split не меняет логику handler'ов)."
relevant_files:
  - "harness/claude/mcp/project/tools_extra.py"
  - "harness/claude/mcp/project/tools_extra_admin.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/cursor/mcp/project/tools_extra.py"
  - "harness/cursor/mcp/project/tools_extra_admin.py"
  - "harness/cursor/mcp/project/tools.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T19:01:41Z"
---

## Goal

Preempt-split harness/{claude,cursor}/mcp/project/tools_extra.py (399/400 lines, 1 line headroom) до того, как следующая добавка tool schema упрётся в filesize gate. Извлекаем Stack registry + Roles секции (~175 строк) в новый tools_extra_admin.py — логически когезивная группа admin/configuration tools.

## Acceptance Criteria

1. harness/claude/mcp/project/tools_extra.py < 350 строк (после удаления Roles+stack_scaffold секций).
2. harness/cursor/mcp/project/tools_extra.py — байт-в-байт идентичен claude-варианту.
3. Новые harness/{claude,cursor}/mcp/project/tools_extra_admin.py содержат TOOLS_EXTRA_ADMIN list (Roles CRUD + stack_scaffold). < 200 строк.
4. tools.py обновлён в обоих harness/{claude,cursor}: импортирует оба list, extends TOOLS обоими.
5. Tool count после split НЕ изменился: 100 tools (93 project + 7 brain) — sanity-check через `tausik doctor` или подсчёт схем.
6. Filesize gate проходит: `tausik verify --task <slug>` зелёный.
7. Full pytest: 2889+ passed, 0 регрессий.
8. Bootstrap → .claude/ синхронизирован, .claude/mcp/project/{tools_extra.py, tools_extra_admin.py} оба присутствуют.
9. CHANGELOG.md + CHANGELOG.ru.md: запись под Unreleased v1.4.0 polish Phase B Changed.
10. Negative case: tausik_role_list, tausik_stack_scaffold etc. остаются вызываемыми после split — попытка вызвать любой из перенесённых tools НЕ возвращает "tool not found" (импорт корректный, дубликатов нет, schema валидна).

## Plan

## Rollback

## Journal

- 2026-05-06T19:01:28Z [implementation] — Implementation done: tools_extra.py 399→317, tools_extra_admin.py 97 (NEW). Roles CRUD + stack_scaffold вынесены. Cursor mirror byte-identical. tools.py обновлён в обоих harness. Tool count 93 unchanged, no duplicates, все 7 admin tools resolvable. Full pytest 2889 passed (mirror-sync тесты падали до bootstrap'а — ожидаемо). Ruff clean. Doctor clean. CHANGELOG.md + CHANGELOG.ru.md обновлены под Unreleased v1.4.0 polish Phase B Changed.
- 2026-05-06T19:01:41Z [implementation] — AC verified: 1. PASS — tools_extra.py 317 lines (was 399, requirement <350). 2. PASS — diff harness/claude/.../tools_extra.py harness/cursor/.../tools_extra.py empty (byte-identical). 3. PASS — tools_extra_admin.py 97 lines (requirement <200), TOOLS_EXTRA_ADMIN list with 7 entries. 4. PASS — both tools.py import TOOLS_EXTRA_ADMIN and call TOOLS.extend(TOOLS_EXTRA_ADMIN). 5. PASS — Total tools 93, unique 93, no duplicates. All 7 admin tools (role_list/show/create/update/delete/seed + stack_scaffold) present. 6. PASS — verify gates green (filesize gate trivially passes, all files <400). 7. PASS — Full pytest 2889 passed, 7 skipped, 120 deselected (was 2889 baseline, 0 regressions). Mirror-sync tests test_mcp_mirrors_in_sync and test_mirror_in_sync green after bootstrap re-sync. 8. PASS — bootstrap completed, .claude/mcp/project/tools_extra_admin.py present (3473 bytes). 9. PASS — CHANGELOG.md/ru.md entry under Unreleased v1.4.0 polish Phase B Changed. 10. PASS — admin tools all resolvable via TOOLS list, no shadowing or duplicate names.
