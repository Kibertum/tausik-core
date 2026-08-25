---
slug: memory-discipline-hardening
title: "Memory Discipline Hardening: enforce TAUSIK-memory priority"
status: done
---

Усилить использование TAUSIK memory и ограничить бездумные записи в Claude auto-memory. Три уровня: PreToolUse-hook-блок (A), SessionStart-инжект-правило (C), PostToolUse-hook-аудит (D).
