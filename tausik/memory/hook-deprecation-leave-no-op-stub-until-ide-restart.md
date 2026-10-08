---
slug: hook-deprecation-leave-no-op-stub-until-ide-restart
title: "Hook deprecation: leave no-op stub until IDE restart"
type: pattern
tags:
  - bootstrap
  - hooks
  - ide-restart
  - migration
task: v14b-defect-token-metrics-no-realworld-write
edges: []
---

When removing a hook script that was registered in .claude/settings.json (or .cursor/.qwen equivalents), the running IDE keeps the old hook config in memory until restart and will spam command-not-found errors on every tool call after the file is deleted. Mitigation: replace the deleted script with a 5-line no-op stub (`import sys; sys.exit(0)` + a docstring explaining why it's a stub and which task to look at). Bootstrap regen drops the registration from settings.json so that after the user restarts the IDE, the stub becomes unreachable and can be deleted in a follow-up. This avoids a noisy bridge state where every Edit/Bash/Read action throws a hook error visible to the agent.
