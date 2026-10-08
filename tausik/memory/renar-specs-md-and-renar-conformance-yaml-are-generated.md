---
slug: renar-specs-md-and-renar-conformance-yaml-are-generated
title: "renar/specs/*.md and RENAR-CONFORMANCE.yaml are generated — write a SPEC record, then `tausik renar export`"
type: convention
tags: []
task: null
edges: []
---

Files under renar/specs/ carry "Derived view — do not hand-edit. Regenerate: `tausik renar export`" in their own header — they are projections of rows in the `specs` DB table (type ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS/TEST/DOC), not hand-authored docs. To add a new normative procedure/reference doc that should live alongside them: (1) write the real content as a normal doc file (e.g. docs/en/<name>.md — check docs/README.md's "Internal agent specs (EN only)" convention if it's agent-facing, not user-facing, RU mirror not required); (2) `tausik spec add <slug> <TYPE> "<title>" --version v1 --content-ref docs/en/<name>.md --status active`; (3) `tausik renar export` to regenerate renar/specs/<slug>.md automatically. Adding a SPEC also makes it linkable to a task (`tausik spec link <task> <slug>`), which satisfies the RENAR QG-0 advisory that nudges "link a requirement" on task start. After adding/changing any SPEC/ADAPT/ACTZ data, also re-run `tausik renar conformance --write` to refresh RENAR-CONFORMANCE.yaml, or its own staleness test fails.
