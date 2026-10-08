---
slug: cq-mozilla-plan-integratsii
title: "cq (Mozilla) — план интеграции"
type: context
tags:
  - cq
  - future
  - knowledge-sharing
  - mozilla
task: null
edges: []
---

Mozilla cq (github.com/mozilla-ai/cq) — "Stack Overflow для AI-агентов". Self-hosted, Docker.

Текущее состояние в Frai:
- cq_client.py — готовый HTTP-клиент (query/propose/confirm/health)
- service_knowledge.py — memory_search подмешивает cq, dead_end предлагает публикацию
- MCP tools frai_cq_query / frai_cq_publish — зарегистрированы
- НЕ настроен: нет "cq" секции в .frai/config.json, сервер не поднят
- Всё gracefully деградирует — работает без cq

План на будущее:
1. docker-compose: cq-team-api (port 8742) + cq-team-ui (port 3000), volume cq-data
2. Нужен CQ_JWT_SECRET env var
3. Прописать "cq": {"endpoint": "http://localhost:8742"} в .frai/config.json
4. Все проекты ([вычеркнуто: third-party-project], [вычеркнуто: third-party-project], [вычеркнуто: third-party-project]) смогут шарить dead ends и паттерны
5. Ждать когда cq станет production-ready (сейчас proof-of-concept)

Не делать пока: cq ещё сырой, нет global commons, есть risk data poisoning.
