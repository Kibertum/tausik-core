---
slug: filesize-gate-forces-architectural-splits-embrace-it
title: "Filesize gate forces architectural splits — embrace it"
type: pattern
tags:
  - architecture
  - filesize
  - qg-2
  - refactor
task: null
edges: []
---

When the 400-line filesize gate fires on a touched file, the right move is almost always to extract a cohesive sub-module rather than fight it. Patterns that worked across v1.3.4: (1) extract a NEW module for a logical sub-domain (`gate_negative_scenario.py` from service_gates, `verify_files_hash.py` from service_verification, `verify_git_diff.py` from service_verification, `gate_qg0_score.py` from service_gates) and re-export from the original via `from foo import bar  # noqa: F401, E402` so callers don't need to change. (2) For class methods, create a sibling Mixin (`TaskTeamMixin` in service_task_team.py) and add to the multi-mixin composition in project_service.py. The re-export pattern preserves API stability while shrinking files; the Mixin pattern lets you split a class without breaking `self.method` calls between the parts. Estimate: each meaningful extract drops ~50-100 lines, comfortably below 400 limit. Don't try to save lines by collapsing docstrings/comments — formatter (ruff/black) often re-expands and you regress.
