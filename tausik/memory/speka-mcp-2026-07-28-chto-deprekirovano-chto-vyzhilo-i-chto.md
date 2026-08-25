---
slug: speka-mcp-2026-07-28-chto-deprekirovano-chto-vyzhilo-i-chto
title: "Спека MCP 2026-07-28: что депрекировано, что выжило и что это значит для TAUSIK"
type: context
tags:
  - deprecation
  - mcp
  - roadmap-2.0
  - spec
task: l26-mcp-deprecation-audit
edges: []
---

Спека MCP от 2026-07-28 (RC зафиксирован 2026-05-21). Факты, на которые опирается планирование 2.0.

ДЕПРЕКИРОВАНО (SEP-2577), annotation-only, гарантия не менее 12 месяцев до удаления — это не пожар:
- sampling (sampling/createMessage) — сервер занимал модель клиента;
- logging (logging/setLevel, notifications/message) — заменяется на stderr либо OpenTelemetry;
- roots (roots/list) — заменяются параметрами тулов, resource URI или конфигом сервера.

ВЫЖИЛО И ИЗМЕНИЛОСЬ:
- elicitation выживает ТОЛЬКО через Multi Round-Trip Requests (SEP-2322);
- новый цикл спеки НЕ добавляет официальных транспортов;
- Tasks понижен из экспериментального ядра в РАСШИРЕНИЕ;
- ядро стало stateless: убраны initialize-хендшейк (SEP-2575) и заголовок Mcp-Session-Id (SEP-2567). Это играет НА РУКУ мульти-тенантному серверу — любой запрос может прийти в любой инстанс.

НАГРУЗКА НА TAUSIK: РОВНО НУЛЕВАЯ, замерено, а не предположено (сессия #121). 19 файлов MCP-треда, три сервера (project, brain, codebase-rag), 0 обращений к депрекируемому API, 0 строк протокола, 0 объявляемых возможностей — Server.get_capabilities() возвращает logging=None. Серверы регистрируют ровно четыре хендлера: list_tools, list_prompts, list_resources, call_tool.

СЛЕДСТВИЕ ДЛЯ РОАДМАПА. Два P0-пункта 2.0 построены на Roots — gmcp-spike-roots (Roots-capability и launch-модель) и gmcp-project-resolver (цепочка roots -> pointer -> cwd/env). Мигрировать нечего: существующего кода на Roots НЕТ. Значит l26-roots-premise-fix — это переписывание ТЗ БУДУЩИХ задач до вложения человеко-недель, а не миграция.

Закреплено гейтом tests/test_mcp_no_deprecated_primitives.py: вывод «не затронуто» иначе протух бы на следующем коммите.
