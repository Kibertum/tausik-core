---
slug: the-full-lane-counts-only-tracked-files-for-the-publication
title: "The full lane counts only TRACKED files for the publication pins: an untracked projection passes the lane and reds the next commit"
type: gotcha
tags:
  - "publication,ratchet,git-ls-files,full-lane"
task: null
edges: []
---

Session #258: memory #699's body quoted the dev-machine path; the full lane before commit c8d7b2bd was green because tausik/memory/<slug>.md was still untracked (git ls-files does not list it), and the same lane at HEAD after the commit is red (23 > 22). Before calling a tree green, run git add -A -n or stage the projections first, so the lane sees what the commit will carry. Re-recorded as #702 without the path.
