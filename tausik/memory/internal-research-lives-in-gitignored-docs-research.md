---
slug: internal-research-lives-in-gitignored-docs-research
title: "Internal research lives in gitignored docs/research/_internal/ (never name codenames in .gitignore)"
type: convention
tags:
  - badges
  - docs
  - gitignore
  - leak
  - public-release
task: v153-leak-scrub
edges: []
---

docs/research/ holds BOTH public technical notes and internal strategy. Internal/personal-data research (prod hosts, bookmark profiles, unreleased codenames, competitive strategy) goes in the gitignored sink docs/research/_internal/ — kept locally, never published. Do NOT gitignore such files by their exact filename: the filename itself can leak codenames (e.g. '...[вычеркнуто: third-party-service]-...-[вычеркнуто: unreleased-codename]-...'), and a descriptive comment that enumerates the secrets is itself a meta-leak in the public .gitignore. Use a neutral directory rule (docs/research/_internal/) like site/_archive/ and docs/audit/. Also: site landing version derives from constants.tausik_version, and README version/test badges are governed by gen_doc_constants --check (scan_version_refs needs alt-text 'vX.Y.Z' to validate) — keep them in sync there, not by hand-editing in isolation.
