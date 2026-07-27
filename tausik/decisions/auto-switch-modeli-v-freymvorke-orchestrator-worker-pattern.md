---
slug: auto-switch-modeli-v-freymvorke-orchestrator-worker-pattern
task: null
date: "2026-05-07"
edges: []
---

## Decision

Auto-switch модели в фреймворке = orchestrator-worker pattern, не platform fight. Главный агент (Opus) — координатор; задачи complexity≤medium auto-spawn как sub-agents через Agent tool с model=recommended. Это единственный программный механизм model selection доступный платформе Claude Code.

## Rationale

Hooks/extensions НЕ могут переключить модель главной сессии mid-session — это ограничение Claude Code/LLM API. Sub-agent invocation — единственный лом. Aligned с Anthropic orchestrator-workers pattern. /fast НЕ делает downgrade на Sonnet (это Opus 4.6 fast mode — banner текст был неверный, fix landed как separate task v14c-banner-fix-model-recommendation). Архитектурный эпик v15-orchestrator-worker-pattern зафиксирован в backlog.
