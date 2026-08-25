---
slug: senar-window-is-one-to-two-years-institutions-are-coming
title: "Окно SENAR оценено в год-два: институции идут в агентные стандарты"
status: planning
epic: release-110-proof-outward
story: proof-outward
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "docs/ru/research/*.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Принято и записано решение, что делать с окном: подавать, участвовать в чужом или ждать, — с обоснованием и датой пересмотра.

## Acceptance Criteria

1. Замер зафиксирован: Agentic AI Foundation при Linux Foundation (декабрь 2025, 170+ членов) и NIST CAISI AI Agent Standards Initiative (анонс февраль 2026) целятся в агентные стандарты. Пока предмет — безопасность, identity и протоколы, но критерии приёмки работы агента — очевидный следующий шаг.
2. Второй риск назван: spec-kit со 126 208 звёздами задаёт артефакты без критериев готовности. Если GitHub добавит слой готовности, ниша SENAR схлопывается.
3. Из трёх путей выбран один и обоснован: подать свой Internet-Draft; прийти в чужой драфт со своей находкой; внести предикат в in-toto (барьер — pull request, а не рабочая группа).
4. Записана ДАТА ПЕРЕСМОТРА решения, а не только само решение: окно оценено в год-два, и оценка обязана перепроверяться, а не устаревать молча.
5. НЕГАТИВНЫЙ сценарий: подача наружу НЕ делается раньше закрытия offline-checkable-is-claimed-but-only-a-service-is-shipped. Публиковать спецификацию, ссылаясь на README, обещающий офлайн-проверку без работающего офлайн-пути, — ровно то, что наш продукт запрещает делать агенту.
6. НЕГАТИВНЫЙ сценарий: SENAR и RENAR в IETF не подаются как методологии — там стандартизуют форматы и протоколы. Попытка подать методологию в IETF считается ошибкой адресата.

## Plan

## Rollback

решение отменяется новым решением; кода не касается

## Journal
