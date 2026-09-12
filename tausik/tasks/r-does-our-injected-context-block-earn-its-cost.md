---
slug: r-does-our-injected-context-block-earn-its-cost
title: "R: окупает ли себя наш собственный впрыск контекста — или мы платим 20% за минус к успеху"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/context_block_audit.py (cost of each generated part + usage proxies from transcripts), tests/test_context_block_audit.py, docs/ru/agent-contract.md section, CHANGELOG EN/RU. Reads CLAUDE.md/AGENTS.md, git history of CLAUDE.md and transcripts outside the repo — read-only, counts only."
scope_exclude: "No A/B success-rate experiment (needs controlled paired runs — owner's call, costed in the journal); no change to update_claudemd or CLAUDE.md content in this task — a cut, if the threshold triggers it, is filed with the measured figures as its own task."
relevant_files:
  - "scripts/context_block_audit.py"
  - "tests/test_context_block_audit.py"
scope_paths:
  - "scripts/context_block_audit.py"
  - "tests/test_context_block_audit.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/r-does-our-injected-context-block-earn-its-cost.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T16:20:00Z"
---

## Goal

ETH Zurich, arXiv 2602.11988, 438 задач и 4 агента: файлы контекста, СГЕНЕРИРОВАННЫЕ моделью, дают от -0.5% до -2% успеха при +20-23% стоимости и +2.45..+3.92 лишних шага; написанные ЧЕЛОВЕКОМ дают +4% успеха при накладных до +19%. Вывод авторов: пока обходиться без сгенерированных файлов и держать в человеческих только минимальные требования. Нас это бьёт прямо: CLAUDE.md и AGENTS.md у нас ГИБРИДНЫЕ — рукописные правила плюс блок Current State и хвост памяти, которые генерирует update_claudemd каждую сессию. Половина, попадающая под приговор исследования, у нас впрыскивается автоматически и НИКОГДА не измерялась. ПОРОГ ПРОВАЛА объявляется ДО замера: если сгенерированная половина не даёт измеримого выигрыша на нашем же наборе задач, она снимается или урезается до минимума, а не оставляется по привычке. Замерять раздельно: рукописные правила, блок состояния, хвост памяти — иначе непонятно, какая часть платит. Смежные задачи: memory-tail-by-relevance-not-recency (отбор хвоста) и v14b-rag-nudge-replay-benchmark (методика замера расхода уже опробована).

## Acceptance Criteria

AC-1: scripts/context_block_audit.py splits the rules file into its parts — handwritten rules, Current State block, memory tail, shared-knowledge block — and reports bytes and approximate tokens per part and their share of the median per-call context (276,702, measurement #230); the split is by the generator's own markers, not by line counts. AC-2: usage proxy A (state block): per transcript, whether a status / session_current / session_open call occurs among the first 8 tool calls — a re-fetch of what the block already carries; reported as sessions re-fetching / sessions. AC-3: usage proxy B (memory tail): per transcript, memory ids cited by the agent (assistant text or tool input) that no earlier tool result or human message in that transcript contained — the only remaining source is the injected tail; cross-checked against the union of ids the tail carried across CLAUDE.md's git history so a hallucinated id is not credited; reported as sessions with >=1 tail-sourced citation / sessions and the id count. AC-4: thresholds declared in the journal BEFORE the run: the tail earns its place at >= 25% of sessions with a tail-sourced citation; the state block earns its place at < 75% of sessions re-fetching; a part under its threshold is filed for a cut with the figures, not cut silently and not kept by habit. AC-5 (negative): a transcript where every cited id was first returned by a tool result credits nothing to the tail; an empty transcript set is named, never reported as 0% usage; tests prove both. AC-6: figures in the journal and docs/ru/agent-contract.md, CHANGELOG EN/RU, ruff, signed verify; what is NOT measured (task success, the paper's metric) is written next to the figures.

## Plan

[{"step": "Declare thresholds; scripts/context_block_audit.py: parts split + cost, proxy A (state re-fetch), proxy B (tail-sourced citations vs git-history union)", "done": true}, {"step": "tests/test_context_block_audit.py: split by markers, proxy A/B positives and negatives, empty set named", "done": true}, {"step": "Run on this machine, record figures, docs + CHANGELOG, verify; file the cut task if a threshold triggers", "done": true}]

## Rollback

git revert of the one commit; the audit script has no callers.

## Journal

- 2026-09-12T16:14:14Z [implementation] — THRESHOLDS DECLARED BEFORE MEASURING. Cost side: bytes/tokens per part of CLAUDE.md (handwritten | Current State | memory tail | shared knowledge) as a share of the median per-call context 276,702 (#230). Usage side, from this machine's transcripts of this project: proxy A (state block) = share of sessions where a status/session_current/session_open call occurs in the first 8 tool calls (re-fetch); proxy B (memory tail) = share of sessions where the agent cites at least one memory id that no earlier tool result or human message in that transcript contained AND that the tail carried at some point in CLAUDE.md's git history. Rules: tail earns its place at >= 25% of sessions with a tail-sourced citation; state block earns its place at < 75% re-fetch. Under threshold → a cut task is filed with the figures. NOT measured: task success (the paper's metric) — a paired A/B needs controlled runs and is the owner's call.
- 2026-09-12T16:19:21Z [implementation] — FIGURES, session #249, this machine: cost per request — handwritten 4067 B / 0.368%, Current State 246 B / 0.022%, memory tail 2750 B / 0.249%, shared knowledge 1518 B / 0.137%; generated half 0.41% of the median context, not the paper's +20%. Usage over 94 transcripts (42 top-level sessions + 52 subagent transcripts): proxy A state re-fetch 41/94 = 43.6% (< 75% → block stays); proxy B tail-sourced citation 35/94 = 37.2%, 58 distinct ids (>= 25% → tail stays); 68 cited ids never in the tail uncredited. Shared-knowledge block: no ids, unmeasured. NOT measured: task success — paired A/B is the owner's call. Per the declared rules no cut task is filed.
- 2026-09-12T16:19:21Z [implementation] — Steps 1-2: scripts/context_block_audit.py (split at DYNAMIC/heading markers, cost per part vs 276,702, proxy A re-fetch in first 8 calls via Bash or MCP, proxy B tail-sourced citations checked against the union of tail ids over CLAUDE.md's git history — 338 ids in 198 commits) + tests/test_context_block_audit.py (11 tests). Root cause (measurement): the first cut credited session numbers ('Передача #226', '#228 открыта') to the tail — caught by a spot-check of eight credited citations; now a bare number under SESSION_CEILING=300 needs a memory/decision word before it, and session/run/verify/receipt words before any number exclude it. Figures moved 38.3% → 37.2%.
- 2026-09-12T16:19:43Z [implementation] — AC-1 ✓ tests/test_context_block_audit.py::test_parts_are_cut_at_the_generators_markers, ::test_a_pre_marker_file_splits_at_the_state_heading, ::test_cost_share_is_against_the_measured_median_context. AC-2 ✓ ::test_proxy_a_counts_a_status_refetch_only_within_the_first_calls (Bash and MCP forms; the ninth call does not count). AC-3 ✓ ::test_proxy_b_credits_the_tail_only_when_nothing_earlier_carried_the_id, ::test_the_tail_ids_are_read_by_construction_and_prose_ids_need_a_reason, ::test_a_second_mention_is_not_a_second_sourcing; history cross-check ::test_history_outside_a_repo_is_empty_not_an_error. AC-4 ✓ thresholds in the journal entry 'THRESHOLDS DECLARED BEFORE MEASURING' precede the run; both parts above threshold → no cut task, and none kept by habit: the figures are in the journal and in docs/ru/agent-contract.md 'Окупает ли себя сгенерированная половина CLAUDE.md (замер #249)'. AC-5 ✓ ::test_proxy_b_credits_the_tail_only_when_nothing_earlier_carried_the_id (tool result first → nothing), ::test_an_empty_set_is_named_not_reported_as_zero_usage. AC-6 ✓ docs section, CHANGELOG.md, CHANGELOG.ru.md, 'not measured: task success' next to every figure (script output, docs, changelog); ruff clean; verify run #2528 signed. Domain: eight credited citations were read by eye — 'норма #628', 'решение #344', 'конвенция #291', 'convention #624' are real references to rows the tail carried; the false ones the first cut produced are now excluded by rule and by test.
