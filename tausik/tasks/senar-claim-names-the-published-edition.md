---
slug: senar-claim-names-the-published-edition
title: "Заявление о соответствии SENAR называет редакцию 1.5 в формате 13.1, раскрывает несоответствия (13.1(e)), а релизный гейт проверяет, что заявленная редакция опубликована"
status: done
epic: release-110-deferred-from-19
story: release110-senar-15-claimed-honestly
complexity: medium
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/senar_claim.py"
  - "scripts/project_cli_publish.py"
  - "scripts/project_parser_publish.py"
  - "tests/test_senar_claim.py"
  - "docs/en/publishing.md"
  - "docs/ru/publishing.md"
scope_paths:
  - README.md
  - README.ru.md
  - CLAUDE.md
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "scripts/senar_*.py"
  - "scripts/project_cli_publish.py"
  - "scripts/project_parser_publish.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - compliance-matrix-is-rewritten-against-senar-15-core
  - direct-modification-has-one-recognized-case
  - metrics-disclose-method-and-thresholds-carry-a-basis
  - severity-scale-is-documented-and-used-by-review
completed_at: "2026-09-23T19:17:44Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#182"
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

Владелец (смена #266): SENAR 1.5 заявляем сразу, публикацию стандарта он сделает позже, состав редакции не изменится (только декоративная полировка). Сегодня README: «TAUSIK claims SENAR v1.3 Core — that edition and no other»; публичный GitHub Kibertum/SENAR — v1.3 (27.03.2026), senar.tech — 1.4, 1.5 — ветка docs/senar-15 (сабмодуль standard-src). SENAR 1.5 §13.1 задаёт формат заявления и (e) — раскрытие несоответствий с заявлением везде, где оно опубликовано. Цель: заявление в README/CLAUDE.md/agent-contract в формате 13.1 с датой и редакцией 1.5; редакция читается из корпуса, на который указывает senar_standard_corpus (ветка 1.5), а не набирается; список несоответствий и невнедрённых SHOULD (13.1(c),(e)) порождается из реестра; релизная процедура (publishing.md, push-ok) получает проверку «заявленная редакция опубликована» — тег 1.10 не ставится, пока GitHub Kibertum/SENAR не несёт тег заявленной редакции; это защищает от ссылки на неопубликованный стандарт без блокировки разработки.

## Acceptance Criteria

1. Заявление в формате 13.1: «[Organization] conforms to SENAR v1.5 Core, self-declared, as of [date]» — в README (EN/RU), CLAUDE.md, agent-contract; тест на единую формулировку в трёх местах; версия в заявлении = версия корпуса по senar_standard_corpus (тест читает баннер), корпуса нет → skip с причиной.
2. Раздел «Несоответствия и невнедрённые SHOULD» порождается из реестра (записи с обоснованием, планом, одобрением — 13.5) и опубликован рядом с заявлением; НЕГАТИВНЫЙ: запись в реестре без публикации рядом с заявлением — красный тест.
3. Релизный гейт: push-ok / процедура publishing.md отказывает тегу релиза, если GitHub Kibertum/SENAR не несёт тег заявленной редакции; НЕГАТИВНЫЙ: при отсутствии сети отказ говорит «не проверено», а не «опубликовано» (fail-closed, §8.6(e)); обычная разработка и CI этим гейтом не трогаются.
4. Отказ гейта печатает обе версии (заявленная, опубликованная) и ссылку на релизы SENAR; текст снят живым вызовом в тест (конвенция #698).
5. CHANGELOG EN+RU; docs/ru+en publishing.md.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-23T19:12:31Z [implementation] — Сделано: scripts/senar_claim.py (claim_sentence из DECLARED_SENAR_VERSION, реестры NONCONFORMITIES/UNIMPLEMENTED_SHOULD пусты с объявленным основанием, missing_disclosures, published() через git ls-remote --tags GitHub Kibertum/SENAR, check_message); tausik publish senar-check (exit 1 нет тега, 2 не удалось спросить); фраза §13.1 в README en/ru, CLAUDE.md (статическая часть 4091/4096 байт), docs/ru/agent-contract.md; раскрытие §13.1(c),(e) в README; шаг 4 в publishing.md en/ru. Живой вызов: 'REFUSED … Claimed: v1.5. Published: tags on GitHub: v1.3' exit=1. Замечание: Core не называет конфигурацию §11, форма §13.1 несёт 'Core' на её месте — это сказано в README. AC verified: 1. ✓ test_the_claim_is_stated_verbatim_in_every_place (4 места), test_the_claimed_edition_is_what_the_corpus_released (skip без корпуса) 2. ✓ test_the_readme_discloses_with_the_claim; НЕГАТИВНЫЙ test_a_record_the_readme_does_not_carry_is_a_finding 3. ✓ test_published_needs_the_tag_of_the_claimed_edition, test_the_release_step_exits_by_the_answer; НЕГАТИВНЫЙ test_no_network_is_not_verified_never_published 4. ✓ test_the_refusal_names_both_versions_and_the_releases_link; текст совпадает с живым выводом 5. ✓ CHANGELOG EN+RU, publishing.md en/ru. 17 новых тестов, 94 соседних зелёные.
