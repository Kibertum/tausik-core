---
slug: four-ide-registries-collapse-into-one
title: "Четыре несинхронизированных реестра хостов сводятся в один с гейт-тестом"
status: done
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: medium
role: developer
stack: python
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
completed_at: "2026-10-07T08:19:12Z"
resolution: obsolete
resolution_reason: "Duplicate of ide-registries-collapse, closed in session #292 with commit e4279117 (pushed, in main and v1-11-2): IDE_DIRS derives from IDE_REGISTRY, VALID_IDES derives from SCAFFOLD_IDES, ide_single_source gate test with derivation+negative cases. Re-doing it would re-implement a landed ratchet. Found by cross-checking Track B against session #292 handoff before starting work."
tracker_refs:
  - "github#154"
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

РАСЩЕПЛЕНИЕ ext-p1-provider-refactor (цель G4), выполнено в #189.
ЗАМЕР ИЗ ИСХОДНОЙ ЗАДАЧИ: существуют ЧЕТЫРЕ несинхронизированных реестра хостов — IDE_DIRS, ide_utils.IDE_REGISTRY, skill_profile_detect.VALID_IDES и каталог providers/. Четыре списка одного и того же множества расходятся молча.
ПОЧЕМУ ЭТО КРИТИЧНО ИМЕННО СЕЙЧАС: на этих реестрах стоят две новые задачи релиза — честная таблица покрытия механизмами по хостам и гейт паритета кроссмодельности. Гейт, сверяющий покрытие с ОДНИМ из четырёх списков, разойдётся с остальными тремя, то есть воспроизведёт ровно тот дефект, против которого заведён.
ЧТО ДЕЛАЕТСЯ: один источник правды о множестве хостов плюс ГЕЙТ-ТЕСТ, краснеющий при появлении второго списка. Провайдер становится этим источником, остальные три читают его.
НЕГАТИВНОЕ: тест обязан ловить не расхождение СОДЕРЖИМОГО, а сам факт появления второго перечня — иначе следующий список заведут синхронизированным и он разойдётся через месяц.

## Acceptance Criteria

## Plan

## Rollback

Сведение реестров плюс тест; откат git revert, реестры возвращаются к нынешнему виду.

## Journal

- 2026-08-29T14:22:54Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
