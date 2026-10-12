---
name: Bug report
about: Something in TAUSIK doesn't work as documented
title: "[bug] "
labels: bug
---

**Version**
Output of `tausik --version` (or `pyproject.toml` version) + IDE (Claude Code / Qwen / Cursor) + OS.

**What happened**
A clear description of the bug.

**Repro steps**
1. …
2. …
3. …

**Expected vs actual**
What you expected, and what happened instead (paste the exact CLI/MCP output).

**Gate/hook involved (if any)**
e.g. QG-0 / QG-2 / scope gate / push gate / bootstrap.

**Notes**
- Did you run a full `python bootstrap/bootstrap.py` after editing `scripts/`?
- Is PyYAML installed? (optional dep — only needed for `renar conformance/export`)
