---
slug: bootstrap-ide-all-v-seredine-sessii-otravlyaet
title: "bootstrap --ide all в середине сессии отравляет работающий MCP-сервер; закрытие — только CLI"
type: gotcha
tags:
  - bootstrap
  - cli
  - drift
  - mcp
  - qg-2
  - verify-first
task: engine-claude-literals-followup
edges: []
---

Если `bootstrap.py` перезаписывает .claude/scripts|mcp (redeploy для устранения bootstrap_drift) ПОКА MCP-сервер запущен, его in-memory модули (verify_cache, service_verification) рассинхронизируются с диском. Симптом: tausik_verify(MCP) возвращает passed=True, но tausik_task_done(MCP) падает verify-first с cache_status='hit'/'git-mismatch' — кэш пишется одной логикой, читается другой. Лечение: после bootstrap переходить на `.tausik/tausik` CLI (перечитывает диск каждый вызов) до рестарта IDE.

ВАЖНО про пустой relevant_files: `verify --task` БЕЗ записанных в БД relevant_files скипает pytest (scope в task-done берётся из complexity, но scoped pytest мапит relevant_files→тесты; пусто→SKIP; `verify` без --task гонит ПОЛНЫЙ suite но не кэширует). Каноническая цепочка закрытия (gate_verify_first.py:208): `tausik task update <slug> --relevant-files <ВСЕ изменённые с task start, включая CLAUDE.md/CHANGELOG> && tausik verify --task <slug> && tausik task done <slug> --ac-verified`. MCP task_update НЕ имеет поля relevant_files — только CLI. Scope-honesty guard требует, чтобы declared ⊇ git-diff (иначе 'Undeclared: CLAUDE.md').
