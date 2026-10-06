---
slug: ide-registries-collapse
title: "Свёртка четырёх реестров хостов в один"
status: planning
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

IDE_DIRS, ide_utils.IDE_REGISTRY, skill_profile_detect.VALID_IDES и providers знают разные множества хостов: tausik config set ide_profile kilo отказывает как unknown для полностью scaffolded хоста (deferred как four-ide-registries-collapse-into-one). Свести в один источник истины, расхождения удержать тестом на переходный период.

## Acceptance Criteria

1) tausik config set ide_profile kilo и opencode проходят. 2) Все четыре реестра читают один источник; тест ловит любое расхождение. 3) Негативный: действительно неизвестный ide отвергается одинаково на всех поверхностях. 4) Doctor/coverage отчёты не меняют смысловых выводов по покрытию.

## Plan

## Rollback

## Journal
