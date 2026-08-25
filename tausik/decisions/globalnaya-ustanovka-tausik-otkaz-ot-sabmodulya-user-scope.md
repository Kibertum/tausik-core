---
slug: globalnaya-ustanovka-tausik-otkaz-ot-sabmodulya-user-scope
task: null
date: "2026-06-13"
edges: []
---

## Decision

Глобальная установка TAUSIK (отказ от сабмодуля, user-scope MCP) отложена из v1.5 в major-веху 2.0

## Rationale

Ломающее изменение: меняет install, убирает per-project копии .claude/scripts|mcp, требует gate-спайка на roots-capability Claude Code и контракта version-skew. Не помещается в аддитивный v1.5; правильный носитель — major bump 2.0. Эпик v2-global-mcp, 10 задач, старт с gmcp-spike-roots.
