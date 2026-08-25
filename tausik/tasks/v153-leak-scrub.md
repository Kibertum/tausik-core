---
slug: v153-leak-scrub
title: "[security] Scrub internal leaks from public tree ([вычеркнуто: third-party-service] research, pyproject email, renar audit ref)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "docs/research/ (remove [вычеркнуто: third-party-service] file), .gitignore, pyproject.toml, renar/specs/renar-adoption.md + its source spec record"
scope_exclude: "scripts/ harness/ bootstrap/ tests/ (audited clean — do not touch), git history (rewrite is user's separate call)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T10:31:00Z"
---

## Goal

A 3-agent leak audit of the published (git-tracked) tree found internal/private references. Remove them from the public repo: (1) HIGH — docs/research/2026-06-12-[вычеркнуто: third-party-service]-ai-bookmarks-[вычеркнуто: unreleased-codename]-strategy.md leaks a prod DB host root@[вычеркнуто: internal-host], personal email + a user's bookmark profile, a d:/tmp path, the unreleased '[вычеркнуто: unreleased-codename]' codename + competitive strategy, and a docs/audit reference — delete from tree + gitignore (same treatment as docs/audit and site/_archive). (2) MED — pyproject.toml authors email is a personal gmail — drop the email (project uses GitHub Security Advisories, no personal contact). (3) LOW — renar/specs/renar-adoption.md content_ref points at private docs/audit/_findings/... — scrub the audit path from the source spec and re-export.

## Acceptance Criteria

AC1: docs/research/2026-06-12-[вычеркнуто: third-party-service]-ai-bookmarks-[вычеркнуто: unreleased-codename]-strategy.md is git-removed AND gitignored; `git ls-files | grep [вычеркнуто: third-party-service]` empty. AC2: pyproject.toml authors line has no personal email (gmail removed); package still builds (name retained). AC3: renar/specs/renar-adoption.md no longer references docs/audit/_findings (source spec scrubbed + re-exported, or file edited if not regenerated); `git grep docs/audit -- renar/` empty. AC4: full self-sweep `git grep -i -E "[вычеркнуто: third-party-service]|[вычеркнуто: unreleased-codename]|[вычеркнуто: internal-host]|jumashev|docs/audit"` over tracked files returns only legitimate CHANGELOG self-disclosure (no real leaks). AC5: ruff+mypy clean; gen_doc_constants --check green. Negative: no other tracked file references the prod IP, personal email, or [вычеркнуто: unreleased-codename] codename.

## Plan

## Rollback

git revert the scrub commit (restores files); the removed research file remains in prior history if needed.

## Journal

- 2026-06-15T10:30:51Z [implementation] — Root cause (config-error): internal research artifact ([вычеркнуто: third-party-service]/[вычеркнуто: unreleased-codename] strategy, prod DB host root@[вычеркнуто: internal-host], personal email, bookmark profile) + a personal gmail in pyproject + a docs/audit content_ref were committed to the public tree because docs/research/ holds both public and internal files and had no internal-only sink. Prevention: internal research now lives in gitignored docs/research/_internal/ (innocuous ignore rule — no codename in .gitignore); pyproject uses name-only authors (project contact = GitHub Security Advisories); renar content_ref scrubbed at source spec + re-exported. 3-agent audit confirmed scripts/harness/bootstrap/tests clean (all hits were the scrubber feature + intentional test fixtures). NOTE: removed files remain in prior git HISTORY — full purge = history rewrite, deferred to user (same standing caveat as docs/audit). Domain: a fresh public clone now contains zero references to the prod IP, personal email, or [вычеркнуто: unreleased-codename] codename (verified by git grep over tracked tree).
- 2026-06-15T10:30:59Z [implementation] — AC verified: 1. ✓ [вычеркнуто: third-party-service] research git rm --cached + moved to gitignored docs/research/_internal/; git ls-files|grep [вычеркнуто: third-party-service] empty; git check-ignore confirms ignored 2. ✓ pyproject.toml authors = [{name='Andrey Yumashev'}] — gmail removed; tomllib parses, version 1.5.3 intact 3. ✓ renar spec content_ref set to 'decisions#109' (dropped docs/audit path) + tausik renar export re-ran; git grep docs/audit -- renar/ empty 4. ✓ git grep -i '[вычеркнуто: third-party-service]|[вычеркнуто: unreleased-codename]|[вычеркнуто: internal-host]|jumashev' over tracked tree = ZERO HITS; .gitignore rule is innocuous (docs/research/_internal/, no codename) 5. ✓ ruff All checks passed; gen_doc_constants --check OK; targeted pytest 234 passed (renar/spec/doc/vendor); no test asserts the email
