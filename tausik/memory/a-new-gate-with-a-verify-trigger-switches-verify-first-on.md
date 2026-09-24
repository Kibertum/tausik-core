---
slug: a-new-gate-with-a-verify-trigger-switches-verify-first-on
title: "A new gate with a verify trigger switches Verify-First ON wherever verify gates were empty"
type: gotcha
tags: []
task: qg0-accepts-a-placeholder-as-an-acceptance-criterion
edges: []
---

enforce_verify_first returns early when get_gates_for_trigger('verify') is empty. Adding ruff_format (trigger commit+verify, enabled by default) made test_tausik_cli::tausik_env — which disabled only pytest/ruff/filesize — hit 'declares no relevant_files' at task done. Same holds for any user project that had turned its verify gates off. When adding a verify-trigger gate: grep tests for fixtures that disable the heavy gates and extend them; name the behaviour change in CHANGELOG.
