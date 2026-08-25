---
slug: site-reasoning-trace-build
title: "[bug] Site build fails: split inline-code <slug> in docs/ru/reasoning-trace.md"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: trivial
call_budget: 8
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T10:46:31Z"
---

## Goal

vitepress build fails (ELIFECYCLE exit 1) on ru/docs/reasoning-trace.md:11 'Element is missing end tag'. Cause: the inline code span `tausik task replay <slug>` is broken across a line break (line ends after 'replay', '<slug>`' starts next line), so markdown-it doesn't treat it as code and <slug> is parsed as an unclosed HTML tag. EN version keeps it on one line and builds. Fix: reflow docs/ru/reasoning-trace.md so the code span is contiguous on one line; re-run vitepress build to green.

## Acceptance Criteria

AC1: docs/ru/reasoning-trace.md no longer splits the `tausik task replay <slug>` code span across a line break. AC2: `pnpm build` in site/ exits 0 (full vitepress build green). AC3: no content meaning changed — only line reflow. Negative: EN doc and other content untouched; no <slug>-style raw tag left outside code.

## Plan

## Rollback

## Journal

- 2026-06-15T10:46:19Z [implementation] — Root cause (edge-case): two independent pre-existing build blockers, both RU-only (EN files lacked the offending constructs). (1) docs/ru/reasoning-trace.md split the `tausik task replay <slug>` inline-code span across a line break → markdown-it didn't form a code span → <slug> parsed as an unclosed HTML tag. (2) docs/ru/research/model-routing-matrix.md linked Decision #112 to ../../../CHANGELOG.md, which doesn't exist under site/ → vitepress dead-link gate failed the build. Scope expanded from the single <slug> fix to 'get site build green' since both surfaced sequentially in the same build. Prevention: keep inline-code contiguous; link cross-repo files (CHANGELOG) by absolute GitHub URL, not relative paths that escape the site tree. The two .json links escaping to harness/ are NOT flagged (vitepress dead-link check only validates .md pages). Domain: full `pnpm build` now exits 0 (build complete in 6.81s).
- 2026-06-15T10:46:31Z [implementation] — AC verified: 1. ✓ docs/ru/reasoning-trace.md: `tausik task replay <slug>` now contiguous on one line (no break splitting the code span) 2. ✓ site/ pnpm build exits 0 — 'building client + server bundles ✓ ... build complete in 6.81s' (only benign chunk-size warnings) 3. ✓ reasoning-trace.md = pure line reflow; model-routing-matrix.md = single dead CHANGELOG link retargeted to absolute GitHub URL (scope expanded to build-green, logged). EN docs untouched; no raw <slug> tag left outside code
