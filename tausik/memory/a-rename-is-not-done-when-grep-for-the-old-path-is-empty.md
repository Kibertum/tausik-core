---
slug: a-rename-is-not-done-when-grep-for-the-old-path-is-empty
title: "A rename is not done when grep for the old PATH is empty — search for the old FILE NAME in globs too"
type: gotcha
tags: []
task: second-full-run-red-after-rename-and-format
edges: []
---

Session #269: renaming codebase-rag/server.py -> rag_server.py passed a repo-wide grep for 'codebase-rag/server', yet tests/test_mcp_answers_prompts_list.py discovered servers by glob('harness/*/mcp/*/server.py') — a pattern naming neither the package nor the path — and silently lost one server. Only the full run caught it. After a rename, grep for the bare file name inside glob/fnmatch patterns as well.
