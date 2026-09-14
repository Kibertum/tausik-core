---
slug: rag-first-nudges-do-not-change-tool-choice
title: "rag-first nudges do not change tool choice: 0 search_code calls in 62 with the nudges delivered, 0 in 76 without — decide whether the six injection sites earn their context"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-host-parity-refactors
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "bootstrap/bootstrap_templates.py, harness/skills/, scripts/hooks/session_start.py, scripts/hooks/user_prompt_submit.py, scripts/hooks/tool_output_truncation_nudge.py, README*.md, docs/"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Paired replay of docs/ru/research/rag-nudge-replay-protocol.md §7 (14.09.2026, claude-opus-5[1m], ten fixed read-only questions, same commit 396de834): with all rag-first texts delivered (SessionStart RAG line + reminder bullet, one UserPromptSubmit nudge) the agent made 0 search_code calls out of 62 tool calls; without them, 0 out of 76. The nudges changed the shape of exploration (Grep 37→21, Read 37→39 and larger) and cost +1.9% on Σ cache_creation + Σ output and +11.5% on exploration result bytes — while a repeat of the same condition varied by 13%, so the delta is noise and the only hard fact is the zero. Six sites carry the text today: bootstrap_templates.TOOL_ROUTING (inert for Claude in this repo), skills start/task/debug/explore, session_start.py, user_prompt_submit.py, tool_output_truncation_nudge.py. This task decides, with the owner: remove the texts (they are injected every session and never acted on), replace them with a mechanism that cannot be ignored (e.g. a PreToolUse gate that answers a Grep on an unfamiliar path with a search_code result), or keep them and say in the docs that no measured effect exists. Whatever is chosen, README/quickstart must not imply that RAG-first is what agents do.

## Acceptance Criteria

AC-1: an owner decision (tausik decide) names one of the three options — remove, replace with a mechanism, keep-and-disclose — citing §7 numbers. AC-2: the chosen option is implemented at every site an inventory finds by grepping the deployed .claude/ for search_code outside MCP tool definitions (six today), and a test freezes the inventory so a seventh cannot appear silently. AC-3: README/quickstart/whats-new say nothing that implies agents search RAG first unless a new paired replay shows search_code calls > 0 in condition A. AC-4 (negative): if "replace with a mechanism" is chosen, a paired replay per the protocol shows search_code > 0 in A before the mechanism is called effective.

## Plan

## Rollback

git revert of the implementing commit; the texts are static strings and return with the revert.

## Journal
