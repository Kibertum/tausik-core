---
slug: testy-dlya-hukov-i-services-dolzhny-uchityvat-chto-mcp
title: "Тесты для хуков и services должны учитывать что MCP server cached модули — нужен либо restart сессии, либо CLI fallback после правок scripts/"
type: gotcha
tags: []
task: null
edges: []
---

Re-bootstrap пишет .claude/scripts/ свежие, но running MCP server держит ссылки на старые модули. Хелпер для MCP-driven flows: после правки scripts — либо просить юзера restart, либо использовать CLI (.tausik/tausik <cmd>) который перечитывает каждый раз.
