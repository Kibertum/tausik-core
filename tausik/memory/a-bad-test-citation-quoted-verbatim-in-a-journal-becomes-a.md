---
slug: a-bad-test-citation-quoted-verbatim-in-a-journal-becomes-a
title: "A bad test citation quoted VERBATIM in a journal becomes a citation of that task"
type: gotcha
tags:
  - "closure-evidence,journal,citation,auditor"
task: null
edges: []
---

Session #257: while fixing the closure auditor, the task's own log quoted a wrong Class::method chain as an EXAMPLE. The extractor (parse_evidence_lines) reads it as this task's citation; journals are append-only; the declared never_existed remainder had to be raised from 35 to 36 for it. Name a bad reference by its TASK slug or by a paraphrase (the class the file never had), never by its verbatim node id. Same trap as the publication-lines pin: a journal quoting the dev-machine path moved that pin from 22 to 23 — and this memory's first version quoted that path too, and moved it again.
