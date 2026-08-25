---
slug: v15s-rule4-external-reviewer
title: "[P0] SENAR Rule 4: tausik-external-reviewer на другой модели"
status: done
epic: v15-senar-hardening
story: v15s-rules
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "harness/claude/subagents/tausik-external-reviewer.md (новый субагент, read-only tools, model override). scripts/external_reviewer.py (новый: выбор ревьюер-модели другого семейства). scripts/risk_l3_trigger.py (обогатить L3-сообщение делегированием). docs/ru/agent-contract.md (секция Rule 4). tests/test_external_reviewer.py (новый) + правка test_risk_l3_trigger.py при необходимости."
scope_exclude: "backend_schema.py/миграции (БЕЗ новых колонок reviews), service_task_done.py логика блокировки (только сообщение через trigger), reviews-таблица"
relevant_files:
  - "scripts/external_reviewer.py"
  - "scripts/risk_l3_trigger.py"
  - "harness/claude/subagents/tausik-external-reviewer.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:24:48Z"
---

## Goal

Закрыть Rule 4 External Validation (1.5/5 в аудите §4.3): именованный субагент tausik-external-reviewer на ДРУГОЙ модели (не та, что писала код — separation of duties), встроенный в QG-2 для high-risk задач (связка с v15-l3-risk-trigger из evidence-attestation). AC: subagent definition + model override; вызов автоматически предлагается/требуется при high-risk; вердикт пишется в evidence; reviewer не имеет write-доступа (SENAR: Reviewer SHALL NOT have write access); docs/ru/agent-contract.md обновлён.

## Acceptance Criteria

1. Субагент tausik-external-reviewer определён в harness/claude/subagents/ с model override и tools без Write/Edit (read-only). 2. external_reviewer.recommend_reviewer_model(author) возвращает семейство, отличное от автора (separation of duties); is_separate_duty=False при совпадении/неизвестном ревьюере. 3. При high-risk closure L3-сообщение называет @tausik-external-reviewer и рекомендует другую модель (вызов предлагается/требуется). 4. Ошибка/boundary: автор-модель неизвестна (нет транскрипта) -> hint не падает, рекомендует opus. 5. docs/ru/agent-contract.md содержит секцию Rule 4 External Validation. 6. pytest: external_reviewer + L3-trigger зелёные.

## Plan

## Rollback

git revert коммита; удалить новый субагент/модуль; L3-сообщение возвращается к прежнему тексту. Миграций/схемы нет — откат чистый.

## Journal

- 2026-06-13T09:24:18Z [implementation] — Rule 4 External Validation: субагент tausik-external-reviewer (read-only tools, model:opus, separation-of-duties протокол + review record команда). external_reviewer.py: recommend_reviewer_model (другое семейство, opus->fable fallback), is_separate_duty, reviewer_hint. risk_l3_trigger обогащает L3-сообщение @tausik-external-reviewer + рекомендованной моделью. docs/ru/agent-contract.md: строка таблицы Rule 4 + развёрнутая секция. 29 unit + 39 integration зелёные. bootstrap: 3 субагента.
- 2026-06-13T09:24:26Z [implementation] — AC verified: 1. ✓ субагент с read-only tools (test_subagent_reviewer 8 passed, bootstrap copies 3). 2. ✓ recommend_reviewer_model/is_separate_duty (TestRecommendReviewerModel, TestIsSeparateDuty). 3. ✓ L3 note делегирует (test_high_risk_note_delegates_to_external_reviewer). 4. ✓ unknown author->opus, no crash (test_*unknown*). 5. ✓ agent-contract.md секция Rule 4. 6. ✓ pytest 29+39 зелёные.
