---
slug: memory-pre-write-block
title: "A: PreToolUse-hook блок на Write в Claude auto-memory"
status: done
epic: memory-discipline-hardening
---

Жёсткий PreToolUse-hook на Write к ~/.claude/projects/*/memory/ — блокирует запись с сообщением-подсказкой "проектное → tausik memory add; cross-project → явно подтверди в ответе". Bypass через маркер confirm: cross-project в промпте.
