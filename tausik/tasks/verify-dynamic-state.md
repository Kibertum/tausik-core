---
slug: verify-dynamic-state
title: "Verify отличает dynamic state от правки инструкций"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
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
  - "tests/test_verify_commit_ownership.py"
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T12:31:29Z"
---

## Goal

Убрать ложный git-mismatch от framework-generated изменений только в DYNAMIC-блоках AGENTS.md/CLAUDE.md, не позволяя обычной правке инструкций или неизвестному файлу скрыться из declared scope.

## Acceptance Criteria

1. Поведенческий тест: commit, изменяющий только содержимое между DYNAMIC markers AGENTS.md/CLAUDE.md, не краснит unrelated scoped verify. 2. Негатив: изменение за marker-границей в том же файле остаётся undeclared git-mismatch. 3. Негатив: файл без валидной пары markers остаётся unknown. 4. Никакой другой путь и uncommitted dynamic change не исключаются. 5. Focused pytest, mypy, ruff, dedupe and signed verify; no release, tag or push.

## Plan

[{"step": "Trace the committed diff and define an exact dynamic-block-only predicate for AGENTS.md/CLAUDE.md.", "done": true}, {"step": "Add real-git behavioral tests for dynamic-only, outside-marker and malformed-marker commits.", "done": true}, {"step": "Implement the conservative dynamic projection exemption alongside task ownership.", "done": true}, {"step": "Run focused pytest, mypy, ruff and dedupe.", "done": true}, {"step": "Run signed verify and close only with a presentable receipt.", "done": true}]

## Rollback

git revert the dynamic-state provenance commit.

## Journal

- 2026-09-11T12:28:35Z [implementation] — Implemented a fail-closed dynamic-projection proof for committed AGENTS.md/CLAUDE.md: exactly one valid DYNAMIC block in both blobs and byte-identical static remainder. Real-git tests cover both files, static instruction edits, prior task ownership states and uncommitted negative path: 47 passed; mypy, ruff and dedupe baseline pass.
- 2026-09-11T12:36:23Z [implementation] — Шаги 1–4: воспроизвёл расхождение истории через default git runner. Причина не в runner: commit 69a4ac11 одновременно экспортирует две задачи, обе заявляющие scripts/verify_commit_ownership.py и tests/test_verify_commit_ownership.py; источник неразличим, поэтому fail-closed сохраняет mismatch. Для dynamic-only добавлен commit-local анализ: только AGENTS.md/CLAUDE.md, только пересечение с фактическим diff, ровно один корректный блок в обеих blob и полностью идентичный remainder. Тесты покрывают оба файла, static edit, malformed marker, staged/uncommitted dynamic и two-export same-commit ambiguity. Focused pytest 10 passed; ruff и mypy PASS; dedupe baseline 322/753.
- 2026-09-12T12:22:53Z [implementation] — AC verified: AC-1 ✓ test_committed_dynamic_block_only_is_not_charged_to_subject[AGENTS.md|CLAUDE.md] → complete. AC-2 ✓ Negative: test_static_instruction_edit_stays_undeclared → undeclared [AGENTS.md]. AC-3 ✓ Negative: test_malformed_dynamic_marker_stays_undeclared → undeclared. AC-4 ✓ Negative: test_uncommitted_dynamic_block_stays_undeclared; the predicate is confined to _DYNAMIC_FILES ∩ actual diff, no other path is touched. AC-5 ✓ 22/22 focused, mypy/ruff clean at commit 42a87f8d (mypy 453 files OK), dedupe 322 unchanged, signed verify below; no release/tag/push. Domain: chore(session) dynamic refreshes like a1e9eec2 no longer redden unrelated receipts; a hand edit to CLAUDE.md still does.
- 2026-09-12T12:22:53Z [implementation] — Unblocked: the receipt budget blocker is gone — scoped pytest now runs in bounded batches (e1043053) and keeps prior evidence across an empty tail batch (scoped-pytest-empty-late-batch, closed); the ownership residue is resolved by the tiered resolver (42a87f8d). Dynamic-block proofs are unchanged by the tiering (they sit in the projection tier, consulted only when no task claims the path).
- 2026-09-12T12:31:01Z [implementation] — relevant_files narrowed to the two files this task actually changed (git log since started_at shows no commit of this task touching scripts/verify_scope_honesty.py); the over-declaration mapped 36 test files through crosscutting scope and timed the gate out at 180s (run #2462) — that timeout is the subject of the separate scoped-pytest task, not of this one.
