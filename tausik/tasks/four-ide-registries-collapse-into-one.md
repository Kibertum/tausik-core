---
slug: four-ide-registries-collapse-into-one
title: "Четыре несинхронизированных реестра хостов сводятся в один с гейт-тестом"
status: planning
epic: release-19-renar-conformance
story: guarantees-are-not-claude-only
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
depends_on: []
completed_at: null
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
