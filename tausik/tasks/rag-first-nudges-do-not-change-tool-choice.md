---
slug: rag-first-nudges-do-not-change-tool-choice
title: "rag-first nudges do not change tool choice: 0 search_code calls in 62 with the nudges delivered, 0 in 76 without — decide whether the six injection sites earn their context"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "bootstrap/bootstrap_templates.py, harness/skills/, scripts/hooks/session_start.py, scripts/hooks/user_prompt_submit.py, scripts/hooks/tool_output_truncation_nudge.py, README*.md, docs/"
scope_exclude: null
relevant_files:
  - "scripts/hooks/user_prompt_submit.py"
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/tool_output_truncation_nudge.py"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_rag_first_nudges_removed.py"
  - "tests/test_user_prompt_submit_hook.py"
  - "tests/test_session_start_hook.py"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "harness/skills/**"
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "scripts/hooks/tool_output_truncation_nudge.py"
  - "tests/*.py"
  - "README*.md"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:18:51Z"
---

## Goal

Paired replay of docs/ru/research/rag-nudge-replay-protocol.md §7 (14.09.2026, claude-opus-5[1m], ten fixed read-only questions, same commit 396de834): with all rag-first texts delivered (SessionStart RAG line + reminder bullet, one UserPromptSubmit nudge) the agent made 0 search_code calls out of 62 tool calls; without them, 0 out of 76. The nudges changed the shape of exploration (Grep 37→21, Read 37→39 and larger) and cost +1.9% on Σ cache_creation + Σ output and +11.5% on exploration result bytes — while a repeat of the same condition varied by 13%, so the delta is noise and the only hard fact is the zero. Six sites carry the text today: bootstrap_templates.TOOL_ROUTING (inert for Claude in this repo), skills start/task/debug/explore, session_start.py, user_prompt_submit.py, tool_output_truncation_nudge.py. This task decides, with the owner: remove the texts (they are injected every session and never acted on), replace them with a mechanism that cannot be ignored (e.g. a PreToolUse gate that answers a Grep on an unfamiliar path with a search_code result), or keep them and say in the docs that no measured effect exists. Whatever is chosen, README/quickstart must not imply that RAG-first is what agents do.

## Acceptance Criteria

AC-1: an owner decision (tausik decide) names one of the three options — remove, replace with a mechanism, keep-and-disclose — citing §7 numbers. AC-2: the chosen option is implemented at every site an inventory finds by grepping the deployed .claude/ for search_code outside MCP tool definitions (six today), and a test freezes the inventory so a seventh cannot appear silently. AC-3: README/quickstart/whats-new say nothing that implies agents search RAG first unless a new paired replay shows search_code calls > 0 in condition A. AC-4 (negative): if "replace with a mechanism" is chosen, a paired replay per the protocol shows search_code > 0 in A before the mechanism is called effective.

## Plan

## Rollback

git revert of the implementing commit; the texts are static strings and return with the revert.

## Journal

- 2026-09-24T06:17:25Z [implementation] — AC-1: ✓ review — decision #390 names 'remove', citing §7: 0 search_code in 62 tool calls with all rag-first texts, 0 in 76 without, cost delta within the 13% repeat noise.
- 2026-09-24T06:17:25Z [implementation] — AC-2: ✓ tests/test_rag_first_nudges_removed.py::test_the_inventory_of_mentions_is_frozen and tests/test_rag_first_nudges_removed.py::test_no_mention_is_advice_to_search_rag_first — removed at every site: session_start RAG line + reminder bullet, user_prompt_submit nudge (constants, detector, emission), tool_output_truncation_nudge cure, skills debug/explore/start/task + variants gpt-5-5/gpt-5, bootstrap TOOL_ROUTING; the 9 files still naming search_code are frozen with a reason each; mutation (a 'Prefer search_code' line appended to skills/plan) -> 2 failed, 1 passed; restored.
- 2026-09-24T06:17:25Z [implementation] — AC-3: ✓ review — README/README.ru and whats-new-1.9 already state the zero; docs/*/hooks.md no longer list the nudge; no doc says agents search RAG first (git grep for prefer/first-choice near search_code finds only the removal records).
- 2026-09-24T06:17:26Z [implementation] — AC-4: ✓ review — not applicable: 'replace with a mechanism' was not chosen, so no effectiveness replay is owed.
- 2026-09-24T06:17:26Z [implementation] — Tests moved with the behaviour, named here: tests/test_user_prompt_submit_hook.py::TestRagFirstNudgeIsGone replaces TestRagFirstNudge (discovery prompts inject no search advice; a coding prompt gets only the task nudge); tests/test_session_start_hook.py::TestRagFirstReminder now requires the Reminders block NOT to mention search_code. 465 hook/skill/template tests green.
- 2026-09-26T18:41:51Z [done] — EVIDENCE-RETIRED: tests/test_rag_first_nudges_removed.py::test_no_mention_is_advice_to_search_rag_first — file deleted by accff299 (feat(1.10/D,J): RAG hits reach the agent after every Grep; answer budg)
- 2026-09-26T18:41:51Z [done] — EVIDENCE-RETIRED: tests/test_rag_first_nudges_removed.py::test_the_inventory_of_mentions_is_frozen — file deleted by accff299 (feat(1.10/D,J): RAG hits reach the agent after every Grep; answer budg)
