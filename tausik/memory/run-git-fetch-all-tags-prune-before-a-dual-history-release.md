---
slug: run-git-fetch-all-tags-prune-before-a-dual-history-release
title: "Run `git fetch --all --tags --prune` before a dual-history release."
type: dead_end
tags: []
task: release-tausik-1-11-1
edges: []
---

Approach: Run `git fetch --all --tags --prune` before a dual-history release.
Reason: GitLab release tags and GitHub flattened-snapshot tags intentionally share names but point to different objects, so fetching all tags from GitHub rejects existing names as would-clobber. Fetch each remote with `--no-tags`; compare remote tags with `git ls-remote`.
