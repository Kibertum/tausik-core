---
slug: filesize-gate-evaluates-relevant-files-not-modified-files
title: "filesize gate evaluates relevant_files, not modified files"
type: gotcha
tags:
  - filesize
  - gates
  - relevant_files
  - task_done
task: null
edges: []
---

`task done --ac-verified` runs the filesize gate against the task's `relevant_files` list. If the list contains a pre-existing-debt file (e.g. bootstrap/bootstrap.py at 529 lines while we're working on a different file), the gate blocks task done even though the task didn't modify that file.

Workaround: drop unmodified pre-existing-debt files from --relevant-files. Verify scope is "files whose tests should run", not "files mentioned in AC."

Hit this in session #57 on `bootstrap-apply-after-start-trim` task — listed bootstrap/bootstrap.py because the AC mentioned bootstrap, but the actual smoke-test only depends on harness/skills/start/SKILL.md. Drop, re-verify, re-done worked cleanly.
