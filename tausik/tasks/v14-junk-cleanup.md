---
slug: v14-junk-cleanup
title: "Cleanup: удалить PDF и historical research docs"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "root *.pdf, docs/ru/research/*.pdf, docs/ru/research/tausik-1.4-{readiness-audit*,epics-master-plan-*}.md, IDE shadow PDF copies"
scope_exclude: "любой код, активные research, docs/{en,ru}/*.md (вне research)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T09:30:17Z"
---

## Goal

Удалить 9 PDF файлов (root summary + 2 research + 6 IDE shadow copies) и 3 historical research markdown'а (v1.4 audit drafts + epics master plan). Это снижает размер репозитория и убирает stale historical snapshots.

## Acceptance Criteria

1. Удалены 9 PDF: tausik-v1.3-summary.pdf (root), 2 в docs/ru/research/, 6 в .claude/.cursor/.qwen/ shadow copies.
2. Удалены 3 historical research .md: tausik-1.4-readiness-audit-2026-05-01.md (15K draft), tausik-1.4-readiness-audit-v2-2026-05-01.md (44K), tausik-1.4-epics-master-plan-2026-05-01.md (25K).
3. Оставлены 3 active research: tausik-1.5-strategic-review-2026-05-02.md, tausik-1.4-pytest-dedupe-2026-05-02.md, tausik-1.4-composer-retro-2026-05-02.md.
4. Negative: никакие .py / docs/ru/*.md / docs/en/*.md (вне research/) не тронуты.
5. Verify: find *.pdf не возвращает удалённых файлов.
6. Verify: композер retro сохранён (важная история).
relevant_files: tausik-v1.3-summary.pdf, docs/ru/research/*.pdf, docs/ru/research/tausik-1.4-readiness-audit*.md, docs/ru/research/tausik-1.4-epics-master-plan-2026-05-01.md

## Plan

## Rollback

## Journal

- 2026-05-03T09:30:17Z [implementation] — AC verified: 1. ✓ 9 PDF удалены (1 root + 2 research + 6 IDE shadow). 2. ✓ 3 historical research md удалены (audit-v1, audit-v2, epics-master-plan). 3. ✓ 3 active research остались (strategic-review, pytest-dedupe, composer-retro). 4. ✓ Negative: только targeted files удалены, никакой код не тронут. 5. ✓ Verify: find *.pdf чистый. 6. ✓ Composer-retro сохранён + ссылки на удалённые master-plan/audit обновлены в CHANGELOG.md/ru.md и composer-retro frontmatter+links.
