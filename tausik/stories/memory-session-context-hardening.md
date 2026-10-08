---
slug: memory-session-context-hardening
title: "C: усилить SessionStart-инжект правилом о приоритете"
status: done
epic: memory-discipline-hardening
---

В TAUSIK Memory Block (инжектится на старте сессии) добавить явное ⚠-правило в заголовке: "TAUSIK memory = PRIMARY. Claude auto-memory = ONLY cross-project user preferences." Сейчас правило только в CLAUDE.md, который часто игнорируется в пользу auto-memory.
