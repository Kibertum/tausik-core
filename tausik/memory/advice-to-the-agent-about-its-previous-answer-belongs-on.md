---
slug: advice-to-the-agent-about-its-previous-answer-belongs-on
title: "Advice to the agent about its previous answer belongs on UserPromptSubmit, not Stop"
type: gotcha
tags: []
task: terse-answers-enforced-by-mechanism
edges: []
---

A blocked Stop hook is rendered by the host as a hook error and swallows the turn's output; UserPromptSubmit runs on the next human prompt with transcript_path in the payload, so the last assistant text can be scored and one advisory line injected without blocking anything (answer budget, story J, 1.10).
