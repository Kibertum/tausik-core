---
slug: kross-ide-claude-cursor-byte-identical-edinyy-source-v
task: null
date: "2026-03-14"
edges: []
---

## Decision

Кросс-IDE: claude + cursor byte-identical. Единый source в agents/claude/, копируется в agents/cursor/.

## Rationale

Один codebase — меньше дрифта. Тест parity гарантирует синхронность. Bootstrap копирует в .claude/ или .cursor/ целевого проекта.
