---
slug: pytest-module-name-collisions-when-two-handlers-py-files
title: "pytest module-name collisions when two handlers.py files are on sys.path"
type: gotcha
tags:
  - imports
  - mcp
  - pytest
  - testing
task: brain-mcp-tools-read
edges: []
---

agents/claude/mcp/project/handlers.py and agents/claude/mcp/brain/handlers.py share the module name `handlers`. If both dirs get added to sys.path in the same pytest session, `import handlers` resolves whichever was added first and caches it in sys.modules. Tests pass individually but fail in the full suite. Fix: load the specific handlers.py via importlib.util.spec_from_file_location with a unique module name (e.g. `tausik_brain_handlers`). See tests/test_brain_mcp_handlers.py._load_brain_handlers for the canonical form.
