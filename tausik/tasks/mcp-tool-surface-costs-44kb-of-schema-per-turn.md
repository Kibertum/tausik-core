---
slug: mcp-tool-surface-costs-44kb-of-schema-per-turn
title: "Поверхность MCP стоит 44 КБ схемы на каждом ходу: 117 инструментов, и цена никем не названа"
status: planning
epic: landscape-2026-h2
story: agent-output-discipline
complexity: null
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Замер, сессия #178: TOOLS сервера tausik-project содержит 117 определений, json.dumps даёт 44501 байт. Протокол MCP пересылает имя и схему КАЖДОГО инструмента на каждом ходу, если клиент не умеет откладывать схемы. Порядок величины — около одиннадцати тысяч токенов на ход только на описание поверхности, до единого полезного вызова. Claude Code этот удар смягчает отложенной загрузкой схем, но это свойство КЛИЕНТА, а не наша заслуга: у Cursor и Qwen такой защиты нет, и там счёт платится целиком. Задача: назвать цену числом в документации, а затем сократить её — разделением поверхности по областям, объединением команд одного семейства или отказом от инструментов, которые дублируют CLI без выигрыша. Смежное ограничение уже заведено задачей mcp-tools-list-caching-conflicts-with-scope-hiding: кэшируемый tools/list против скрытия по scope — решать вместе, иначе сокращение поверхности покажет клиенту то, чего уже нет.

## Acceptance Criteria

## Plan

## Rollback

## Journal
