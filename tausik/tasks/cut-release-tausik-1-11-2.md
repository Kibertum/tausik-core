---
slug: cut-release-tausik-1-11-2
title: "Cut release TAUSIK 1.11.2"
status: done
epic: null
story: null
complexity: null
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "CHANGELOG.md, CHANGELOG.ru.md, pyproject.toml, scripts/tausik_version.py, docs/_generated/constants.json"
scope_exclude: "source code, bootstrap, tests"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - pyproject.toml
  - "scripts/tausik_version.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T20:24:52Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Ship the kilo-zai-host-parity patch as TAUSIK 1.11.2: date the Unreleased sections in both changelogs, bump the version, regenerate constants, release commit, tag v1.11.2, ff main.

## Acceptance Criteria

1) Version reads 1.11.2 in pyproject.toml and scripts/tausik_version.py, and docs/_generated/constants.json regenerated with it; the string 1.11.1 remains in none of the three. 2) Both changelogs carry the header for the dated release with the seven sections moved under it and an empty Unreleased kept on top, en and ru in sync. 3) Negative: gen_doc_constants --check fails while constants still say 1.11.1 after the version bump, then exits clean after --write.

## Plan

## Rollback

git revert the release commit; delete the v1.11.2 tag locally and on the remote; main falls back by resetting to the pre-release commit.

## Journal

- 2026-10-06T20:24:31Z [implementation] — AC-1: check - pyproject.toml, scripts/tausik_version.py, docs/_generated/constants.json each contain 1.11.2 and zero 1.11.1 (assertion script output above). AC-2: check - both changelogs carry exactly one header for release 1.11.2 dated 2026-10-06, empty Unreleased kept on top, sections ordered above the 1.11.1 header, en/ru in sync. AC-3: check - negative proven: gen_doc_constants --check exited 1 with drift expected tausik_version=1.11.2 while constants still said 1.11.1; after --write it exits 0; README badges (version + test count 13064) regenerated in both languages.
- 2026-10-06T20:24:47Z [implementation] — AC verified: 1. check three version files hold only 1.11.2 (assertion run green) 2. check both changelogs: single dated 1.11.2 header, empty Unreleased, en equals ru 3. check negative: gen_doc_constants --check exit 1 on stale constants, exit 0 after write; README badges regenerated both languages.
- 2026-10-06T20:25:09Z [done] — AC-1: check gen_doc_constants --check exit 0 after write. AC-2: check assertion over both changelogs, dated header once. AC-3: check gen_doc_constants --check exit 1 before write, recorded in verify run 3543.
