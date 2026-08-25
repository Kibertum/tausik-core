---
slug: skill-profile-auto-detect-runs-in-sessionstart-hook-scripts
task: b8-pre-model-profile-auto-detect-interactive-promp
date: "2026-05-07"
edges: []
---

## Decision

Skill profile auto-detect runs in SessionStart hook (scripts/hooks/session_start.py::_auto_rebuild_skills), not in tausik init. Detect IDE+model from env on every session start, compare with .tausik/.session.json, lazy-rebuild только при mismatch.

## Rationale

init runs once but проект может открываться в разных IDE/моделях между сессиями. Hook видит свежий env каждый раз. Cache hit = микросекунды (one fs stat). Cache miss = одна перезапись skill-файлов на диск, которые затем читаются Claude Code напрямую — runtime overhead = 0, prompt caching survives.
