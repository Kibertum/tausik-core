---
slug: posle-pravki-source-scripts-harness-docs-bootstrap-py-ide
title: "После правки source (scripts/harness/docs) — bootstrap.py --ide all перед task_done, НЕ ручной cp зеркал"
type: convention
tags:
  - bootstrap
  - gates
  - mirrors
  - qg-2
task: status-cli-mcp-divergence
edges: []
---

bootstrap_drift — БЛОКИРУЮЩИЙ QG-2 гейт: deployed-профили (.claude/.cursor/.kilo/.opencode/.qwen) обязаны байт-в-байт совпадать с source. hooks/MCP грузятся из ПРОФИЛЯ, не из scripts/harness. Ручной cp зеркал ненадёжен: раскладка отличается — root harness/claude/mcp/project/handlers.py → зеркало .claude/mcp/project/handlers.py (без harness/), а root scripts/x.py → .claude/scripts/x.py. Новый файл в scripts/ вообще не попадёт в зеркала ручным cp с guard-проверкой существования. Правильно: `python bootstrap/bootstrap.py --ide all` (--update обновляет только claude). Профильные дирректории filesystem-only (не в git — .gitignore шире, чем заявленный '.tausik/'), поэтому git status их не покажет, но гейт проверяет ФС. Док-файлы docs/*.md с идентичной раскладкой ручной cp переживают, но проще всегда гонять bootstrap. Не гонять bootstrap одновременно с полной суитой (memory #316).
