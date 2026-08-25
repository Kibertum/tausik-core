---
slug: destructive-export-sync-paths-need-an-out-containment-guard
title: "Destructive export/sync paths need an --out containment guard"
type: gotcha
tags:
  - deletion-guard
  - export
  - renar
  - review
  - safety
task: renar-export-review-fixes
edges: []
---

Any command that reconciles deletions against a user-supplied output dir (e.g. `tausik renar export --out`) MUST validate the target is strictly inside the project root before walking+deleting. renar_export.assert_export_target(out, project_root) is the reusable guard: abspath both, require os.path.commonpath([out,root])==root AND out != root (rejecting the root itself prevents nuking every *.md in the repo; rejecting outside paths prevents `--out /` or `--out $HOME` deleting markdown filesystem-wide). commonpath raises ValueError across drives on Windows → treat as outside. Caught by adversarial separate-model review (SENAR Rule 4) on the destructive primitive, not by the happy-path tests. Lesson: threat-model the hostile argument value for any new delete/overwrite primitive BEFORE close.
