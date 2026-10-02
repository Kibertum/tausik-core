---
slug: declare-deleted-python-tests-in-relevant-files-for-scoped
title: "Declare deleted Python tests in relevant_files for scoped verify"
type: dead_end
tags: []
task: reduce-the-official-skill-catalog-to-three
edges: []
---

Approach: Declare deleted Python tests in relevant_files for scoped verify
Reason: verify preparation sends deleted paths to ruff format, which exits 2 because the files no longer exist; keep deletion evidence in git diff and declare only existing Python files until formatter handles deletions
