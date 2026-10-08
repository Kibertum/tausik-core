---
slug: bootstrap-system
title: "Bootstrap system"
type: context
tags:
  - bootstrap
  - system
task: null
edges: []
---

bootstrap.py generates .claude/ from root sources. Modes: --smart (auto-detect stacks + skills), --interactive (prompt), default (use existing config). Detects: stacks (python, react, etc.), extension skills (diff, test, commit, review), Ollama (for RAG). Config stored in .claude/.frai-bootstrap.json. Supports multiple IDEs: claude, cursor.
