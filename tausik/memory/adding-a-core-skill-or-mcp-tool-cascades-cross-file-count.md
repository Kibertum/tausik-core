---
slug: adding-a-core-skill-or-mcp-tool-cascades-cross-file-count
title: "Adding a core skill or MCP tool cascades cross-file count bumps"
type: gotcha
tags:
  - constants
  - docs-drift
  - mcp
  - skills
  - workflow
task: v16r-reason-skill
edges: []
---

Adding ONE core skill (harness/skills/<name>) or ONE MCP tool changes several tracked counts at once. Required workflow after such an add:
1. Run `python scripts/gen_doc_constants.py` (regenerates constants.json: skills_core_count / mcp_main_tools / mcp_project_tools / mcp_tools_with_optional_rag / mcp_descriptions_hash / test_count — adding a skill ALSO bumps test_count via skill-parametrized tests).
2. Run `gen_doc_constants.py --check` and fix EVERY cross-file ref it flags. Cross-file scan targets: README.md, README.ru.md, AGENTS.md, CLAUDE.md, docs/{en,ru}/architecture.md, docs/{en,ru}/mcp.md.
3. The scanner does NOT catch prose like mcp.md line 7 ("main 105 count … 112 total") or line 11 ("project-scoped tools (98)") or docs/skills.md "12 core" or skill-ecosystem.md — bump these by hand for accuracy.
4. AGENTS.md needs the canonical "N project + M brain = MAIN" string AND the with-RAG total (MAIN+rag) AND the repo-tree "tausik-project (N) + tausik-brain (M) = MAIN main" line (test_mcp_doc_tool_counts asserts all three).
5. Skill SKILL.md `description` must be ≤60 chars (test_skill_descriptions_length) and frontmatter context∈{inline,fork}/effort∈{fast,medium,slow}.
Seen in v16r-reason-skill (+1 skill) and v16r-task-replay (+1 MCP tool).
