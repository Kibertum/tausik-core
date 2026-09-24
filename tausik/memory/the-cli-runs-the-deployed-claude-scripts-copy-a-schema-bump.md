---
slug: the-cli-runs-the-deployed-claude-scripts-copy-a-schema-bump
title: "The CLI runs the DEPLOYED .claude/scripts copy: a schema bump in scripts/ reaches the live DB only after bootstrap"
type: gotcha
tags: []
task: a-task-cannot-be-closed-as-obsolete
edges: []
---

Session #272: SCHEMA_VERSION 66->67 in scripts/backend_schema.py; tausik status still ran the deployed v66 code and did not migrate, so the claudemd_state gate (read-only, refuses to migrate) reported 'schema v66 older than code v67' from the test process. Order after a schema change: bootstrap.py --ide all, then any tausik command migrates the live DB.
