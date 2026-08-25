---
slug: mcp-scope-tools-exposure
title: "MCP-поверхность по scope_tools задачи: экспонировать агенту только разрешённые инструменты (заимствование onyx)"
status: done
epic: landscape-2026-h2
story: borrow-cubest-onyx
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "Слой регистрации/листинга MCP-тулов (mcp/project handlers + tool registry) + чтение scope_tools ACL (scope_acl.py) + tests. Конфиг-флаг включения."
scope_exclude: "Изменение самих тулов/их логики; scope_write_gate (не трогать существующий энфорсмент записи); l26-tool-token-cost (координировать, но отдельная задача)"
relevant_files:
  - "scripts/mcp_tool_scope.py"
  - "harness/claude/mcp/project/server.py"
  - "tests/test_mcp_tool_scope.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T12:38:02Z"
---

## Goal

Усилить SENAR Rule 2 (scope) на уровне САМОЙ MCP-поверхности: onyx экспонирует агенту не все тулы сервера, а курируемое подмножество. У TAUSIK 150+ MCP-тулов и уже есть ACL scope_tools на задаче — но он энфорсится только на записи. Экспонировать активному агенту лишь тулы, разрешённые scope_tools активной задачи (+ всегда-безопасное ядро: status/search/task lifecycle), сокращая и surface атаки, и токен-стоимость определений. Reconcile/coordinate с l26-tool-token-cost (deferred loading). Fail-open при отсутствии активной задачи или пустом scope_tools (legacy-свобода, как write-gate).

## Acceptance Criteria

1. При активной задаче с непустым scope_tools MCP экспонирует агенту только объединение (scope_tools ∪ always-safe-core); прочие тулы скрыты из tool-list. 2. always-safe-core (status/search/task lifecycle/session/verify) экспонируется ВСЕГДА — агент не может залочить себя вне scope. 3. НЕГАТИВ fail-open: нет активной задачи ИЛИ scope_tools пуст/NULL → экспонируются ВСЕ тулы (legacy-свобода, симметрично scope_write_gate) — экономия не должна молча ломать проекты без объявленного scope_tools. 4. НЕГАТИВ безопасность: скрытый тул, вызванный напрямую, всё равно проходит существующий scope-энфорсмент — сокрытие это UX/токен-защита, а НЕ единственный барьер; гейт остаётся. 5. Токен-замер: сокращение размера tool-list при типичном scope зафиксировано числом. 6. Reconcile с l26-tool-token-cost (deferred loading) — механизмы не конфликтуют. 7. Полный scoped verify зелёный.

## Plan

## Rollback

Feature-flag config mcp.scope_tools_exposure=off → экспонируются все тулы (текущее поведение). Fail-open по построению. git revert коммита. Безопасность не зависит от этой фичи (гейт остаётся), поэтому откат не открывает дыр.

## Journal

- 2026-07-27T12:30:55Z [implementation] — Plan: (1) new scripts/mcp_tool_scope.py — pure fail-open filter: feature flag mcp.scope_tools_exposure (default OFF), union of active tasks' declared scope_tools ∪ always-safe-core (task_/session_ prefixes + status/search/verify/health/doctor/self_check/update_claudemd). Symmetric to scope_write_gate: legacy freedom (all tools) only when NO active task declared scope_tools. (2) wire into harness/claude/mcp/project/server.py list_tools(). (3) tests/test_mcp_tool_scope.py incl token-size measurement (AC5) + safe-core existence ratchet + fail-open negatives (AC3) + hidden-tool-still-callable note (AC4 = gate unchanged). (4) CHANGELOG EN+RU. (5) bootstrap --ide all (conv #321). AC4: hiding is UX/token only; call_tool + write-gate unchanged = security barrier remains. AC6: list_tools filter is orthogonal to l26-tool-token-cost deferred-loading; document boundary (mid-session task-change re-scoping via tools/list_changed deferred).
- 2026-07-27T12:38:01Z [implementation] — AC verified: 1. ✓ tests/test_mcp_tool_scope.py::TestExposeScoped::test_declared_scope_narrows_to_union_plus_core — active task with non-empty scope_tools → only (declared ∪ safe-core) exposed; others hidden. 2. ✓ TestSafeCore + TestExposeScoped: tausik_task_*/session_* + status/search/verify/doctor/self_check/update_claudemd always exposed; test_safe_core_names_exist_in_real_tools ratchets against renames. 3. ✓ NEGATIVE fail-open: TestExposeFailOpen::{test_feature_off_returns_all,test_no_active_task_returns_all,test_undeclared_active_task_returns_all,test_resolver_error_fails_open,test_never_returns_empty} — feature off / no active task / NULL scope_tools / error → ALL tools. 4. ✓ NEGATIVE security: hiding is list-shaping only; call_tool + scope_write_gate untouched (server.py list_tools filters TOOLS, call_tool path unchanged). Documented in module docstring + CHANGELOG + mcp.md. Ratchet test guards safe-core validity. 5. ✓ TestTokenMeasurement::test_scoped_surface_is_strictly_smaller — measured on real TOOLS: full=117 tools/43668B → scoped=40 tools/19281B = 56% reduction for a typical single-extra-tool scope. 6. ✓ Reconciled with l26-tool-token-cost: expose_tools is a pure list-shaper at list_tools time, orthogonal to WHEN the host loads the list (deferred-loading). Boundary documented in module docstring + CHANGELOG (mid-session tools/list_changed re-scoping left to that track); no conflict. 7. ✓ tausik verify --task standard: pytest PASS scoped over 12 mapped MCP test files (incl test_mcp_integration, test_mcp_doc_tool_counts). ruff + mypy clean on new module.
