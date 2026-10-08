---
slug: a-gate-module-must-find-the-project-root-by-walking-to-git
title: "A gate module must find the project root by walking to .git, never dirname(dirname(__file__))"
type: gotcha
tags: []
task: full-suite-red-on-the-110-change-set
edges: []
---

Gates execute from the DEPLOYED copy .claude/scripts/, where dirname-twice lands on .claude/ — no tausik/gates.json, no tests/, and every task path comes out as ../scripts/x.py. Bitten three times: class_surface, test_dedupe, and ruff_format (session #269: its frozen legacy list was never read in real use, so a listed file was refused). Unit tests run from scripts/ and stay green, so pin it with a test that passes a fake .claude/scripts 'here' under a tmp dir holding .git (tests/test_gate_ruff_format.py::test_the_deployed_copy_finds_the_project_root_not_claude_dir).
