---
slug: make-the-agent-use-a-tool-by-delivering-its-result-not-by
title: "Make the agent use a tool by delivering its result, not by telling it to"
type: pattern
tags: []
task: rag-first-by-mechanism-not-text
edges: []
---

Session #272: text nudges to use search_code got 0 calls in 62 (paired replay). A PostToolUse hook on Grep that runs the RAG query and injects the top chunks as additionalContext makes the index reach the agent every time, with no behaviour change required. Same lesson as the answer budget (story J): measure, then deliver the effect by mechanism.
