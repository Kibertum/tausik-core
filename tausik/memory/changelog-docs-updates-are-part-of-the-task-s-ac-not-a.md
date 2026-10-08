---
slug: changelog-docs-updates-are-part-of-the-task-s-ac-not-a
title: "CHANGELOG + docs updates are part of the task's AC, not a follow-up"
type: convention
tags:
  - documentation
  - quality-gates
  - workflow
task: null
edges: []
---

Every feature/fix task must bundle CHANGELOG.md entry + impacted `references/*.md` / skill doc updates in the same commit. Not deferred to a "docs pass" task.

User's literal framing: "не забывай changelog обновлять и документацию при работе".

How to apply:
- QG-0: include AC like "CHANGELOG entry added under [Unreleased]; relevant references/*.md updated".
- QG-2: verify CHANGELOG + docs in evidence before `task done --ac-verified`.
- New hooks → `references/architecture.md` + any hook-related doc.
- New skills → skill's own SKILL.md.
- Schema/CLI changes → `references/project-cli.md` + migration note if breaking.
- Single commit = code + tests + docs + CHANGELOG — coherent history.
