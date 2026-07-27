---
slug: mcp-scope-tools-exposure
title: "MCP-поверхность по scope_tools задачи: экспонировать агенту только разрешённые инструменты (заимствование onyx)"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Усилить SENAR Rule 2 (scope) на уровне САМОЙ MCP-поверхности: onyx экспонирует агенту не все тулы сервера, а курируемое подмножество. У TAUSIK 150+ MCP-тулов и уже есть ACL scope_tools на задаче — но он энфорсится только на записи. Экспонировать активному агенту лишь тулы, разрешённые scope_tools активной задачи (+ всегда-безопасное ядро: status/search/task lifecycle), сокращая и surface атаки, и токен-стоимость определений. Reconcile/coordinate с l26-tool-token-cost (deferred loading). Fail-open при отсутствии активной задачи или пустом scope_tools (legacy-свобода, как write-gate).

## Acceptance Criteria

1. При активной задаче с непустым scope_tools MCP экспонирует агенту только объединение (scope_tools ∪ always-safe-core); прочие тулы скрыты из tool-list. 2. always-safe-core (status/search/task lifecycle/session/verify) экспонируется ВСЕГДА — агент не может залочить себя вне scope. 3. НЕГАТИВ fail-open: нет активной задачи ИЛИ scope_tools пуст/NULL → экспонируются ВСЕ тулы (legacy-свобода, симметрично scope_write_gate) — экономия не должна молча ломать проекты без объявленного scope_tools. 4. НЕГАТИВ безопасность: скрытый тул, вызванный напрямую, всё равно проходит существующий scope-энфорсмент — сокрытие это UX/токен-защита, а НЕ единственный барьер; гейт остаётся. 5. Токен-замер: сокращение размера tool-list при типичном scope зафиксировано числом. 6. Reconcile с l26-tool-token-cost (deferred loading) — механизмы не конфликтуют. 7. Полный scoped verify зелёный.

## Plan

## Rollback

Feature-flag config mcp.scope_tools_exposure=off → экспонируются все тулы (текущее поведение). Fail-open по построению. git revert коммита. Безопасность не зависит от этой фичи (гейт остаётся), поэтому откат не открывает дыр.

## Journal
