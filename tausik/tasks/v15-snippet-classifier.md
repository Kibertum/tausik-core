---
slug: v15-snippet-classifier
title: "Heuristic snippet classifier — detect_artifact_kind() + advisory wire"
status: done
epic: v15-snippet-system
story: v15-snippet-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_snippet_detect.py (new), scripts/brain_config.py (knob default), scripts/brain_mcp_write.py (store_record wire), scripts/brain_publish_flow.py (draft_artifact_publish surface), tests/test_brain_snippet_detect.py (new)"
scope_exclude: "no new tables, no AST, no MCP search tool, no Notion property sync (deferred per brain_artifact_taxonomy.py); does not touch snippets DB table from v15-snippet-table"
relevant_files:
  - "scripts/brain_snippet_detect.py"
  - "scripts/brain_config.py"
  - "scripts/brain_mcp_write.py"
  - "scripts/brain_publish_flow.py"
  - "tests/test_brain_snippet_detect.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T23:01:05Z"
---

## Goal

Закрыть пустой stub в brain_artifact_taxonomy.py:7-8 ('v1 stored as a pattern row… until a dedicated DB exists'). Новый модуль scripts/brain_snippet_detect.py с функцией detect_artifact_kind(fields) → 'snippet' | 'pattern' | None на эвристиках (code-fence presence, line count ≤20, YAML/JSON/CLI cues, low natural-prose ratio, description length). Advisory wire в brain_mcp_write.store_record ПЕРЕД validate_artifact_taxonomy_for_store: когда caller не указал artifact_taxonomy_kind И детектор сработал 'snippet' — auto-fill. Новый config knob brain.auto_detect_snippet_kind (default True). Surface в draft_artifact_publish как out['taxonomy_inferred']. Tests по образцу test_brain_universality.py (per-cue positives, false-positive guards, multi-cue dedup, integration на store_record + draft_artifact_publish). Прямой клон паттерна brain_universality.py (B3). Никаких новых таблиц, никакого AST, никакого MCP search — только классификатор. Это (1/5) фундамент v15 snippet system.

## Acceptance Criteria

1. New scripts/brain_snippet_detect.py: detect_artifact_kind(fields)->'snippet'|'pattern'|None on stdlib heuristics (code-fence, line-count<=20, YAML/JSON/CLI cues, symbol/prose ratio); never raises on bad input. 2. Advisory wire maybe_autofill_snippet_kind(category,work,cfg) called in brain_mcp_write.store_record BEFORE validate_artifact_taxonomy_for_store: auto-fills artifact_taxonomy_kind='snippet' ONLY when category in patterns/gotchas, caller omitted the key, knob on, and detector=='snippet'. 3. config knob brain.auto_detect_snippet_kind default True. 4. draft_artifact_publish exposes out['taxonomy_inferred']. 5. NEGATIVE: plain-prose pattern (no code) -> detector None, NO auto-fill, validation path unchanged; caller-supplied kind is never overwritten; knob=False disables auto-fill. 6. tests/test_brain_snippet_detect.py: per-cue positives, false-positive guards (prose, long code), caller-override + knob-off + integration on store_record & draft_artifact_publish; full pytest green.

## Plan

## Rollback

git revert single commit. Purely additive + advisory: auto-fill only triggers when knob on AND caller omitted kind; setting brain.auto_detect_snippet_kind=false fully disables at runtime without revert. No schema/state change.

## Journal

- 2026-06-13T23:00:54Z [implementation] — Verification-checklist (QG-2, medium): scope=brain classifier+advisory wire only (no tables/AST/MCP-search/Notion-sync). tests=tests/test_brain_snippet_detect.py 27 passed (per-cue positives fence/yaml/json/cli/prompt, false-positive guards prose/colon-lines/tool-sentence/long-code/bare-word-metadata, autofill overwrite+knob+category guards, draft integration incl strict-mode mirror + report render); brain regression 693 passed; ruff+mypy clean. security=no injection/secrets/auth; pure-stdlib regex, advisory-only, never overwrites caller value. edge-cases=empty/non-dict/blank->None, never-raises (whole body try-wrapped), YAML precision (>=3 lines OR config-ish value so 'scope: global/author: john' doesn't fire), draft validates enriched copy (no caller mutation). Domain: a brain pattern write with a code/config example now auto-tags taxonomy_kind='snippet' so future snippet tooling can find it; plain-prose knowledge stays untagged.
- 2026-06-13T23:01:05Z [implementation] — AC verified: 1.✓ detect_artifact_kind heuristics (fence/yaml/json/cli, <=20 lines, symbol ratio), never-raises (whole body try-wrapped). 2.✓ maybe_autofill wired in store_record BEFORE validate; fills only when category patterns/gotchas + caller omitted + knob on + detector=='snippet'. 3.✓ config brain.auto_detect_snippet_kind default True. 4.✓ draft_artifact_publish out['taxonomy_inferred'] (+ rendered in format_draft_report). 5.✓ NEGATIVE prose->None no-fill, caller value never overwritten, knob=False disables (tests cover all). 6.✓ tests/test_brain_snippet_detect.py 27 passed; brain regression 693; ruff+mypy+check_docs green; constants/README=4002. Reviewer round-2: 2 HIGH fixed (never-raises hole; draft strict-mode divergence -> validates enriched copy) + 3 MEDIUM (YAML false-positive precision, report render, test fix).
