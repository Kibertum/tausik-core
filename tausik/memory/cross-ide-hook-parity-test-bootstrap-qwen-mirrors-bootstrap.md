---
slug: cross-ide-hook-parity-test-bootstrap-qwen-mirrors-bootstrap
title: "Cross-IDE hook parity test: bootstrap_qwen mirrors bootstrap_hooks"
type: convention
tags:
  - "bootstrap,hooks,parity,cross-ide"
task: v14b-baseline-token-metrics
edges: []
---

tests/test_bootstrap_hooks_parity.py::test_qwen_has_every_claude_hook enforces that every PostToolUse/PreToolUse/SessionEnd hook registered in bootstrap_hooks.py has a counterpart in bootstrap_qwen.py. Adding a new Claude hook without updating Qwen breaks this test. Apply: when registering a new hook in bootstrap_hooks.py, immediately mirror to bootstrap_qwen.py.
