---
slug: memory-post-write-audit
title: "D: PostToolUse-hook аудит записей в Claude auto-memory"
status: done
epic: memory-discipline-hardening
---

После Write в memory/ — парсить содержимое, искать project markers (пути C:\Work\, имена проектов из blocklist, slug'и вида task-xxx, упоминания проектного контекста). При detection — warning "эта запись проектная, перенеси в tausik memory add". Гибрид A и C: не блокирует, но ловит промахи.
