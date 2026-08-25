---
slug: task-update-notes-overwrites-the-journal-task-log-appends
title: "task_update notes= OVERWRITES the journal; task_log appends"
type: gotcha
tags:
  - cli
  - dogfooding
  - qg2
  - task-log
  - task-update
task: ac-evidence-parser-credit-bare-numbered-single-lin
edges: []
---

tausik_task_update(notes=...) REPLACES the whole notes field — it silently clobbers everything accumulated via task_log (which appends). Hit live in #89: a task_update(notes='relevant_files set') wiped a freshly-logged AC-evidence block, making QG-2 fail with 'no verification evidence'. Always use task_log for incremental journal/evidence; reserve task_update notes= for a deliberate full rewrite. Relatedly, relevant_files is NOT settable via task_update — it is set at task_done time (relevant_files param).
