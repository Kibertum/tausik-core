---
slug: mypy-hooks-excluded-rather-than-restructured-into-a-package
task: clean-tausik-doctor-warnings-brain-enabled-false-c
date: "2026-05-06"
edges: []
---

## Decision

Mypy hooks/ excluded rather than restructured into a package

## Rationale

scripts/hooks/*.py is reachable as <name> (via pythonpath=scripts at runtime) AND hooks.<name> (via scripts/hooks/). Adding __init__.py to make hooks a real package would break the runtime sys.path injection used by hook scripts. Excluding the dir from default mypy keeps both the runtime model and the type-checker happy. Hooks are exercised via tests/ subprocess-based tests.
