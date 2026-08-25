---
slug: brain-web-cache-otdelnoe-pole-content-hash-sha256-content
task: brain-db-schema
date: "2026-04-22"
edges: []
---

## Decision

Brain web_cache: отдельное поле Content Hash = SHA256(content)[:16] для dedup

## Rationale

Один URL может возвращать разный контент в разное время (SPA, A/B). Хэш по содержимому надёжнее для pull-sync dedup, чем URL.
