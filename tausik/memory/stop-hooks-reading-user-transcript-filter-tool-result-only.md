---
slug: stop-hooks-reading-user-transcript-filter-tool-result-only
title: "Stop hooks reading user transcript: filter tool_result-only role=user messages"
type: gotcha
tags:
  - false-positive
  - hooks
  - stop-hook
  - transcript
  - v1.4-polish
task: v14b-defect-keyword-detector-search-loop
edges: []
---

Claude Code transcripts represent tool outputs as `role=user` JSONL entries whose `content` is `[{"type":"tool_result", ...}]`. Walking the transcript backwards looking for "the user's last message" will hit those tool_result entries first and treat their text as user input. In v14b-defect-keyword-detector-search-loop this caused the rag-first nudge to fire on /review output that contained "where is X" anywhere in its findings, looping every Stop until the agent defensively echoed `search_code`.

Fix shape: in `_read_last_message(target_role="user")`, skip entries whose content is a list where every block has `type=tool_result`. Plain-string content always counts as a real user prompt. Implementation: `_is_tool_result_only(content)` helper at scripts/hooks/keyword_detector.py:94.

Apply to any future Stop/PostToolUse hook that reads user-side context.
