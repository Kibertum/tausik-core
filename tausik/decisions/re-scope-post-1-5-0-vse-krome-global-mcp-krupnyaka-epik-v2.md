---
slug: re-scope-post-1-5-0-vse-krome-global-mcp-krupnyaka-epik-v2
task: null
date: "2026-06-13"
edges: []
---

## Decision

Re-scope post-1.5.0: всё кроме global-MCP-крупняка (эпик v2-global-mcp / gmcp-* / v2-*) тянем на 1.x-линию (1.5.x/1.6) как приоритет pre-2.0. v16r/RENAR (эпик v16-renar-core) БОЛЬШЕ НЕ откладывается в 1.6-деферрал — гоним сейчас. Также активны для 1.x: v15-polish (v15p), v15-model-routing (v15mr), v15-snippet-system, brain-hardening (brainh). 2.0 = ТОЛЬКО breaking global-MCP (request-time DB routing, standalone pip-пакет, stale-MCP reaping).

## Rationale

Решение пользователя (session #83): 1.5.0 уже зарелизен, но pre-2.0 backlog был размазан по «будущим» эпикам с разными версиями, из-за чего ценный функционал (RENAR reasoning-trace, model-routing, snippets, polish) откладывался. Чтобы релизная линия 1.x была богаче и сильнее перед breaking 2.0, переносим всё нетяжёлое на 1.x. В 2.0 уходит только то, что реально требует breaking-изменений установки/архитектуры (global-MCP). Отменяет деферрал-часть decision #97 (v16r→1.6) и уточняет decision #94 (что именно остаётся в 2.0).
