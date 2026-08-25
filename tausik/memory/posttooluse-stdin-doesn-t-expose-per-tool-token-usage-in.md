---
slug: posttooluse-stdin-doesn-t-expose-per-tool-token-usage-in
title: "PostToolUse stdin doesn't expose per-tool token usage in Claude Code"
type: gotcha
tags:
  - hooks
  - telemetry
  - tokens
task: v14b-usage-events-auto-write
edges: []
---

PostToolUse hook payload contains tool_name + tool_input + tool_response, но per-tool token counts (input_tokens/output_tokens) НЕ передаются harness'ом для большинства инструментов. Anthropic-style schema иногда содержит usage в tool_response.usage или tool_response.message.usage — это best-effort.\n\nСледствие: hook должен корректно работать с tokens=0. Не считай "no usage = skip insert" — пиши строку с tokens=0/tool_calls=1, чтобы сохранить call count для SENAR Rule 7 calibration drift. Cost rollup (`metrics cost`) уже фильтрует NULL slugs, так что non-attributable events остаются в ledger для аудита.
