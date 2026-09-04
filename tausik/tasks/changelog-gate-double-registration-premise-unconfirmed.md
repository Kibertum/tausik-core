---
slug: changelog-gate-double-registration-premise-unconfirmed
title: "Гейт changelog зарегистрирован дважды: премиса из передачи #209 моим замером НЕ подтверждается"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
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

ПРЕМИСА ИЗ ПЕРЕДАЧИ #209: «Дубль changelog_gate в .tausik/config.json».
МОЙ ЗАМЕР В #210 ЕЁ НЕ ПОДТВЕРДИЛ. Обход всего дерева config.json по ключам, содержащим changelog, дал РОВНО ОДНО вхождение: /task_done/changelog_gate (строка 67). Grep по файлу — тоже одно.
ЗАДАЧА НАЧИНАЕТСЯ С УТОЧНЕНИЯ, А НЕ С ПОЧИНКИ. Развести замером три объяснения: (а) дубль был и устранён между #209 и #210 — тогда закрыть с записью и УБРАТЬ ПУНКТ ИЗ ПЕРЕДАЧ; (б) дубль не в config.json, а в РЕЕСТРЕ гейтов — регистрация размазана по четырём механизмам, о чём заведена gate-registry-single-source, и тогда это её предмет, а не отдельная задача; (в) мой замер смотрел не туда, и надо смотреть на слой конфигурации целиком (project/user/managed), а не на один файл.
ЗАВЕДЕНО ИМЕННО ТАК, А НЕ ВЫБРОШЕНО: пункт кочует по передачам с #209 и будет кочевать дальше, а невыясненный пункт дороже закрытого. Но ЧИНИТЬ НЕЧЕГО, пока субъект не предъявлен: гейт без субъекта есть тот самый вырожденный контроль, который мы в этом релизе и вычищаем.

## Acceptance Criteria

## Plan

## Rollback

## Journal
