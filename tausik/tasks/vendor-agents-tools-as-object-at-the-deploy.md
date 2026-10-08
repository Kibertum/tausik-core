---
slug: vendor-agents-tools-as-object-at-the-deploy
title: "vendor agents tools-as-object at the deploy boundary"
status: done
epic: null
story: null
complexity: null
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap_vendor.py (нормализация tools при копировании агентов), tests/test_bootstrap_vendor*.py; источник .tausik/vendor НЕ трогаем — он upstream"
scope_exclude: "файлы вендора, генераторы других хостов"
relevant_files:
  - "bootstrap/bootstrap_vendor.py"
  - "tests/test_bootstrap_vendor.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-08T09:00:41Z"
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
blocked_question: null
unblock_criteria: null
unblocked_by: null
unblocked_at: null
---

## Goal

Хост после рестарта показывает невалидный агент: .kilo/agents/vendor_seo/seo-visual.md tools - строка, а схема Kilo требует объект. Фикс 1.11.2 правил развёрнутые копии и стирался каждым редеплоем (вендор-источник не тронут). Починить на границе: нормализация в copy_vendor_assets.

## Acceptance Criteria

1. copy_vendor_assets нормализует tools-строку в объект при копировании: `tools: Read, Bash, Write` становится YAML-маппингом `Read: true` и т.д.; deployed .kilo/agents/vendor_seo/*.md парсится схемой Kilo (tools: object|undefined).
2. НЕГАТИВНЫЙ: файл-вендор с уже-объектным tools и без tools вовсе проходят без искажения; тело агента не меняется.
3. Тест с подсаженным вендором доказывает трансформацию; после bootstrap --ide all живой .kilo-файл несёт объект.

## Plan

## Rollback

git revert коммита адаптера; вендор-файлы сами по себе не меняются (источник не трогаем)

## Journal

- 2026-10-08T09:00:22Z [implementation] — AC-1: ✓ normalize_agent_tools + copy_vendor_assets: скалярная строка tools становится YAML-объектом при копировании; живой .kilo/agents/vendor_seo/seo-visual.md после redeploy несет tools: Read/Bash/Write: true (проверено чтением). AC-2 NEGATIVE: tests/test_bootstrap_vendor.py::test_object_and_absent_tools_pass_through_untouched (байт-в-байт), ::test_body_tools_line_is_prose_not_schema (тело не трогается). AC-3: ::test_copy_vendor_assets_normalizes_on_the_way_into_the_profile (подсаженный вендор), ::test_live_seo_agents_are_object_after_the_boundary (все 7 живых seo-агентов объектны после границы). Domain: рестарт хоста владельца 2026-10-08 показал невалидный агент - рецидив закрыт на границе, источник-вендор не тронут. Verify run PASS.
