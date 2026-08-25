---
slug: p0-foundation-rewrite
title: "P0: Переписать фундамент (CLAUDE.md шаблон + синки + SessionStart hook)"
status: done
epic: claude-hardening
---

Основа против drift: генерируемый CLAUDE.md должен быть "load-bearing" (prompt-master), AGENTS.md/.cursorrules синхронизированы, SessionStart hook инжектит состояние автоматически.
