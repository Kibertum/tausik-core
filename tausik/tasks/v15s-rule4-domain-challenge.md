---
slug: v15s-rule4-domain-challenge
title: "[P1] T8: Domain challenge — доменный вопрос в QG-2 checklist"
status: done
epic: v15-senar-hardening
story: v15s-rules
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/service_ac_evidence.py (DOMAIN_RE + is_domain + has_domain_evidence + domain-тег в evidence_json). scripts/gate_ac_check.py (пункт domain-challenge в check_verification_checklist, skip для trivial). docs/ru/agent-contract.md (примеры). tests/test_ac_evidence*.py / test_domain_challenge.py."
scope_exclude: "существующие AC/test-ref/negative warnings, determine_checklist_tier"
relevant_files:
  - "scripts/service_ac_evidence.py"
  - "scripts/gate_ac_check.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T10:06:28Z"
---

## Goal

Дешёвое частичное покрытие Rule 4 (источник: arXiv 2605.30353 — агент прошёл тесты с физически бессмысленным результатом; отчёт T8). В QG-2 checklist добавить обязательный пункт «доменный вопрос: имеет ли результат смысл вне тестов?» + поле в evidence. AC: пункт в checklist всех тиров кроме trivial; evidence-парсер распознаёт ответ; примеры в docs.

## Acceptance Criteria

1. service_ac_evidence распознаёт domain-challenge ответ (DOMAIN_RE, EvidenceLine.is_domain, report.has_domain_evidence) + поддержка domain-тега в evidence_json_to_prose. 2. check_verification_checklist выдаёт пункт «доменный вопрос: имеет ли результат смысл вне тестов?» для всех тиров кроме planning-tier trivial, если ответа нет. 3. Примеры domain-evidence в docs (agent-contract или ac-evidence доке). 4. Ошибка/boundary: trivial-tier не получает пункт; пустые notes -> has_domain_evidence False без исключения. 5. pytest: распознавание ответа + warning при отсутствии + skip для trivial.

## Plan

## Rollback

git revert коммита; domain-пункт исчезает из checklist, парсер игнорирует domain-теги. Без миграций/конфига.

## Journal

- 2026-06-13T10:06:12Z [implementation] — DOMAIN_RE + EvidenceLine.is_domain + report.has_domain_evidence; domain-тег в evidence_json_to_prose. check_verification_checklist: пункт domain-challenge для всех тиров кроме planning-tier trivial. Примеры в agent-contract.md. Распознаёт domain/sanity/makes sense/имеет смысл/доменн/real-world. Domain: парсер видит результат как осмысленный вне тестов. 7 новых + 24 qg2/domain зелёные. test_count 3795->3803.
- 2026-06-13T10:06:27Z [implementation] — AC verified: 1. ✓ парсер+evidence_json domain (TestParserRecognition, TestEvidenceJsonDomainTag). 2. ✓ warning для non-trivial без ответа (test_warns_when_domain_missing_non_trivial). 3. ✓ примеры в agent-contract.md. 4. ✓ negative: trivial skip, пустые notes без краха (test_skipped_for_trivial_tier, test_empty_notes_no_crash). 5. ✓ pytest 7 + 24 regression. Domain: фича осмысленна — реальные агенты пишут Domain-строку, проверка ловит test-passing-но-бессмысленные выводы.
