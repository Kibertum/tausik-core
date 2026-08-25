---
slug: site-standalone-agent-ready
title: "Вынос сайта в tausik/site + agent-readiness"
status: done
---

Извлечь VitePress-сайт tausik.tech из core в отдельный GitLab-репо tausik/site (чистый старт), настроить CI/CD (сборка клонирует docs из core через deploy token), вычистить сайт из core и GitHub, реализовать полный пакет agent-readiness доработок по чек-листу isitagentready.com (robots.txt, sitemap, llms.txt, MCP Server Card, Agent Skills manifest, JSON-LD, markdown content negotiation).
