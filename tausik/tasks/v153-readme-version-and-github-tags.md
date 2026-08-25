---
slug: v153-readme-version-and-github-tags
title: "[release] README version badge + purge leaked github tags, cut v1.5.3 release"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: null
tier: light
call_budget: 15
defect_of: null
scope: "README.md, README.ru.md (version badge); github remote tags/releases via git+gh"
scope_exclude: "gitlab origin tags (keep full history), source code, local main branch"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T11:03:42Z"
---

## Goal

Two things: (1) README.md + README.ru.md show the current version via a governed v1.5.3 badge (alt text vX.Y.Z so scan_version_refs keeps it synced). (2) Fix github tags: all 8 legacy tags (v1.1.0..v1.5.2) pin pre-orphan history; v1.5.2 still contains the full [вычеркнуто: third-party-service] prod-IP/email leak. Delete every legacy tag + the v1.5.2 GitHub Release, create+push v1.5.3 on the orphan commit 12c7e49, and cut a v1.5.3 Release. After this no leak is reachable from ANY github ref (closes the gap left by github-publish-v153 which only checked main).

## Acceptance Criteria

AC1: README.md + README.ru.md have a version badge with alt text 'v1.5.3'; gen_doc_constants --check stays green (scan_version_refs validates it == 1.5.3). AC2: every legacy github tag (v1.1.0, v1.1.1, v1.2.0, v1.3.0, v1.3.2, v1.3.7, v1.4.0, v1.5.2) is deleted from github; git ls-remote --tags github shows only v1.5.3. AC3: v1.5.3 annotated tag points at orphan 12c7e49 and is pushed; a v1.5.3 GitHub Release exists and is Latest; v1.5.2 Release deleted. AC4: leak audit — git grep over github v1.5.3 tag shows ZERO [вычеркнуто: third-party-service]/prod-IP/email; no other github ref exposes the leak. AC5: ruff+mypy clean; bootstrap re-run. Negative: gitlab origin tags untouched; local main intact.

## Plan

## Rollback

Old tag SHAs recorded in task log before deletion — recreate via git push github <sha>:refs/tags/<tag>. README badge revert via git revert.

## Journal

- 2026-06-15T11:00:10Z [implementation] — Rollback record — github legacy tag SHAs before deletion: v1.1.0=1bc8052, v1.1.1=ec88714, v1.2.0=e92d3d2, v1.3.0=8891301, v1.3.2=5528583, v1.3.7=f296686, v1.4.0=c127fd2, v1.5.2=fc41846. Recreate via: git push github <sha>:refs/tags/<tag>.
- 2026-06-15T11:03:42Z [implementation] — AC verified: 1. ✓ README.md + README.ru.md line 9 carry [![v1.5.3](.../version-v1.5.3...)]; gen_doc_constants --check green (scan_version_refs validates alt 'v1.5.3' == 1.5.3). RU test badge also fixed 4341->4348 2. ✓ single push deleted all 8 legacy tags (v1.1.0..v1.5.2); git ls-remote --tags github now shows ONLY v1.5.3 3. ✓ annotated v1.5.3 tag at orphan 4adb765 pushed; gh release list shows 'TAUSIK v1.5.3 Latest'; v1.5.2 release deleted 4. ✓ git grep over github v1.5.3 tag (FETCH_HEAD): ZERO [вычеркнуто: third-party-service]/prod-IP/email; version badge present in tag README; no other github ref exists besides main+v1.5.3 5. ✓ ruff All checks passed; mypy clean (pre-commit hook); gitlab origin main f57efe5 + tags untouched; local main f57efe5 intact; temp orphan branch + local tag cleaned
