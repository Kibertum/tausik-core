---
slug: web-cache-otdelnaya-tablitsa-dlya-keshirovaniya-web
task: null
date: "2026-03-14"
edges: []
---

## Decision

Web-cache — отдельная таблица для кеширования web-research между сессиями.

## Rationale

AI-агент часто ищет одно и то же (доки API, best practices). Кеш экономит токены и время. FTS5 для поиска по кешу.
