---
slug: a-new-harness-skills-directory-silently-becomes-a-counted
title: "A new harness/skills/*/ directory silently becomes a counted \"core skill\" everywhere"
type: gotcha
tags: []
task: null
edges: []
---

scripts/code_counts.py::_NON_CORE_SKILL_DIRS excludes only "_profile-demo" and "review" — any OTHER directory created under harness/skills/ is automatically counted as a "core skill" by gen_doc_constants.py, which drives literal "13 core skills" / "14 core skills" text in AGENTS.md, README.md, README.ru.md and elsewhere. Creating a new skill-shaped directory for something that is really a one-off procedure (not a routine slash-command every session might invoke, like /review or /commit) triggers the exact same doc-count cascade as adding an MCP tool. Before adding a new harness/skills/<name>/SKILL.md, ask whether it's genuinely a general-purpose, routinely-invoked slash-command. If not (e.g. a rare, high-stakes procedure tied to one RENAR clause), it likely belongs as a normative reference doc instead — see renar/specs (below) for TAUSIK's actual mechanism for that.
