---
slug: verify-dynamic-state
title: "Verify отличает dynamic state от правки инструкций"
status: active
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/verify_commit_ownership.py; scripts/verify_scope_honesty.py; tests/test_verify_commit_ownership.py; task metadata only"
scope_exclude: "Do not exclude arbitrary AGENTS.md/CLAUDE.md edits, uncommitted files, markerless files or ordinary instruction changes; do not release, tag, push or touch user .agents/."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Убрать ложный git-mismatch от framework-generated изменений только в DYNAMIC-блоках AGENTS.md/CLAUDE.md, не позволяя обычной правке инструкций или неизвестному файлу скрыться из declared scope.

## Acceptance Criteria

1. Поведенческий тест: commit, изменяющий только содержимое между DYNAMIC markers AGENTS.md/CLAUDE.md, не краснит unrelated scoped verify. 2. Негатив: изменение за marker-границей в том же файле остаётся undeclared git-mismatch. 3. Негатив: файл без валидной пары markers остаётся unknown. 4. Никакой другой путь и uncommitted dynamic change не исключаются. 5. Focused pytest, mypy, ruff, dedupe and signed verify; no release, tag or push.

## Plan

[{"step": "Trace the committed diff and define an exact dynamic-block-only predicate for AGENTS.md/CLAUDE.md.", "done": true}, {"step": "Add real-git behavioral tests for dynamic-only, outside-marker and malformed-marker commits.", "done": true}, {"step": "Implement the conservative dynamic projection exemption alongside task ownership.", "done": true}, {"step": "Run focused pytest, mypy, ruff and dedupe.", "done": true}, {"step": "Run signed verify and close only with a presentable receipt.", "done": false}]

## Rollback

git revert the dynamic-state provenance commit.

## Journal

- 2026-09-11T12:28:35Z [implementation] — Implemented a fail-closed dynamic-projection proof for committed AGENTS.md/CLAUDE.md: exactly one valid DYNAMIC block in both blobs and byte-identical static remainder. Real-git tests cover both files, static instruction edits, prior task ownership states and uncommitted negative path: 47 passed; mypy, ruff and dedupe baseline pass.
