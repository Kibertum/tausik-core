---
slug: atomic-config-write-pattern
title: "Atomic config write pattern"
type: pattern
tags: []
task: null
edges: []
---

All config-file writes use temp+os.replace to be SIGINT-safe. Pattern: write to path+'.tmp', then os.replace(tmp, path). On Windows, wrap os.replace in retry loop (4×100ms) for PermissionError. Used in: bootstrap_config.save_tausik_config, service_stack_ops._atomic_write_*, brain_project_registry.save_registry. Critical for any user-data file.
