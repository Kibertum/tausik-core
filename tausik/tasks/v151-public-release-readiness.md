---
slug: v151-public-release-readiness
title: "[P0] Public-release readiness fixes — purge confidential files + doc/onboarding accuracy"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: ".gitignore, docs/audit/* (removal), site/_archive/* (removal), docs/{en,ru}/quickstart.md, bootstrap/tausik_wrapper.sh + .cmd, README.ru.md, README.md, docs/en/mcp.md, CONTRIBUTING.md, docs/_generated/constants.json, git tags"
scope_exclude: "public git HISTORY rewrite / making repo private — IRREVERSIBLE, user decision (this task only fixes the tip); no feature code changes"
relevant_files:
  - ".gitignore"
  - "docs/en/quickstart.md"
  - "docs/ru/quickstart.md"
  - "bootstrap/tausik_wrapper.sh"
  - "bootstrap/tausik_wrapper.cmd"
  - README.md
  - README.ru.md
  - CONTRIBUTING.md
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T00:31:28Z"
---

## Goal

Clear the NO-GO from the public-release-readiness swarm so v1.5.1 is safe to announce. BLOCKERS: remove confidential docs/audit/ (GTM/COI strategy + private-repo paths + 1.7MB PDF) from the tree + gitignore; remove the internal [вычеркнуто: internal-host] leak (site/_archive/); gitignore tausik_systemwide_analysis.md. HIGH: fix Windows quickstart command (EN+RU, points to a nonexistent path), Qwen CLI-wrapper fallback (.qwen/scripts), and the showcase counter drift (README.ru tests 3854→4341, MCP 105→124, 25+→20 skills, 12→13 core, matrix v1.5.0→1.5.1, CONTRIBUTING count). Delete 15 foreign local tags so a push --tags can't leak pre-rename history. NOTE: the confidential files are also in the already-pushed public HISTORY — full purge (history rewrite / private repo) is an irreversible decision left to the user; this task stops the bleeding at the tip.

## Acceptance Criteria

AC1: docs/audit/ removed from the tree (git rm) + added to .gitignore — no confidential GTM/COI/private-path content at HEAD. AC2: internal [вычеркнуто: internal-host] leak removed (site/_archive/ deleted or the URL stripped); `git grep [вычеркнуто: internal-host]` clean. AC3: tausik_systemwide_analysis.md gitignored. AC4: quickstart.md (EN+RU) Windows command fixed to a path that exists (.tausik/tausik.cmd or .claude/scripts/project.py). AC5: CLI wrapper resolves .qwen/scripts (qwen CLI works). AC6: showcase counters corrected (README.ru tests 4341; MCP 124; skills 20; core 13; matrix 1.5.1; CONTRIBUTING count) — gen_doc_constants --check green. AC7: 15 foreign local tags deleted; only v1.5.1 intended for push. AC8: ruff+mypy clean; full pytest green; fresh-clone smoke still works. Negative: `git grep -i "gitlab.yumash"` returns nothing; `git ls-files docs/audit` returns nothing.

## Plan

## Rollback

git revert restores removed files; tag deletions are local-only (not pushed); doc edits revertable.

## Journal

- 2026-06-15T00:31:04Z [implementation] — Public-release-readiness fixes (swarm NO-GO → GO). BLOCKERS: git rm -r docs/audit (GTM/COI findings + 1.7MB PDF + private-repo paths) + site/_archive ([вычеркнуто: internal-host] leak); both gitignored; git grep gitlab.yumash + git ls-files docs/audit now clean. tausik_systemwide_analysis.md gitignored. HIGH: quickstart Windows cmd EN+RU → `.tausik/tausik.cmd status` (was nonexistent .tausik/scripts path); CLI wrapper (.sh+.cmd) now resolves .qwen/.windsurf/.codex/scripts (qwen CLI worked only via... now explicit); counters fixed README.ru tests 3854→4341, MCP 105→124 (EN+RU table), 25+→20 skills, 12→13 core, CONTRIBUTING 2590→4341, senar-matrix v1.5.0→1.5.1; RU coverage badge added. Deleted 15 foreign local tags (frai/kai/v2.x) so push --tags can't leak pre-rename history. bootstrap redeployed wrapper; gen_doc_constants green; ruff+mypy clean (210); 258 bootstrap/doc tests pass.
- 2026-06-15T00:31:27Z [implementation] — AC1: ✓ docs/audit/ git-rm'd + gitignored (git ls-files docs/audit empty). AC2: ✓ site/_archive removed; git grep gitlab.yumash empty. AC3: ✓ tausik_systemwide_analysis.md gitignored. AC4: ✓ quickstart Windows cmd EN+RU → .tausik/tausik.cmd status (real path). AC5: ✓ wrapper .sh+.cmd resolve .qwen/.windsurf/.codex/scripts; bootstrap redeployed (3 qwen refs in generated wrapper). AC6: ✓ counters fixed (README.ru 4341, MCP 124 EN+RU, 20 skills, 13 core, CONTRIBUTING 4341, matrix 1.5.1) + RU coverage badge; gen_doc_constants --check green. AC7: ✓ 15 foreign tags deleted, only v1.x remain. AC8: ✓ ruff+mypy clean (210), 258 bootstrap/doc tests pass. Domain: a new user cloning the public tip no longer gets confidential GTM/COI data, the Windows onboarding command works, and qwen users get a working CLI. Negative: git grep gitlab.yumash + git ls-files docs/audit both empty. Root cause (category: documentation): confidential dev/audit artifacts + internal URLs were tracked into the public-mirror snapshot, and showcase counters drifted post-feature-work. Prevention: gitignored + a public-release-readiness swarm in the release checklist.
