---
slug: vynesti-jira-bitrix24-i-drugie-vneshnie-integratsii-v
task: null
date: "2026-04-06"
edges: []
---

## Decision

Вынести jira, bitrix24 и другие внешние интеграции в отдельный репозиторий TAUSIK-addons. В core-репозитории хранить только project и codebase-rag MCP серверы.

## Rationale

Core-репозиторий не должен содержать мусор внешних интеграций. Jira, Bitrix24, Confluence — опциональные аддоны, не нужные большинству пользователей. Их наличие усложняет bootstrap, cross-IDE parity и тестирование. Vendor skills уже управляются через skills.json — аддоны MCP серверов должны работать аналогично.
