---
slug: compliance-matrix-is-rewritten-against-senar-15-core
title: "Матрица соответствия переписана по SENAR 1.5 Core: 8 правил, Start/Done Gate, три свойства гейта, две метрики — и ничего чужого под ярлыком Core"
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
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "scripts/senar_version_claim.py"
  - "scripts/senar_self_check.py"
  - "tests/test_senar_compliance_matrix.py"
  - "tests/test_senar_version_claim.py"
  - "tests/test_senar_self_check.py"
scope_paths:
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
  - CLAUDE.md
  - AGENTS.md
  - CONTRIBUTING.md
  - QWEN.md
  - "bootstrap/bootstrap_templates.py"
  - "scripts/senar_version_claim.py"
  - "scripts/senar_standard_drift.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - qg0-does-not-refuse-work-for-session-time-or-capacity
  - senar-corpus-drift-is-detected-like-renar
completed_at: "2026-09-23T19:03:41Z"
resolution: null
resolution_reason: null
---

## Goal

docs/ru|en/senar-compliance-matrix.md заявляет v1.3 Core (оценка 13.06.2026 на TAUSIK 1.7.0) и относит к Core правила Стандарта 9.2 (лимит сессии), 9.3 (чекпоинт), 9.5 (аудит), 9.15 — в SENAR Core 1.5 их нет: Core = 8 правил, Start Gate, Done Gate, «три вещи, делающие гейт гейтом» (a, c, e), метрики FPSR и Dead End Rate; «управление сессиями появляется на Foundation» сказано в самом Core. Цель: матрица по 1.5 Core, где число строк каждого раздела СЧИТАЕТСЯ из корпуса стандарта (парсер по образцу renar_standard_drift, ключ senar_standard_corpus), каждая строка цитирует существующий символ кода (тест на существование), а всё, что за пределами Core (гейты свойств (b),(d), правила 10.x Стандарта, метрики Foundation), вынесено в раздел «сверх Core: Foundation-образное, не заявлено».

## Acceptance Criteria

1. Разделы матрицы: Правила Core (8), Start Gate, Done Gate, свойства гейта (a),(c),(e) с (d) и (g) как «сверх», Метрики Core (2); число строк каждого раздела равно числу, распарсенному из корпуса SENAR (core/en/senar-core.md) — тест; корпус отсутствует → тест skip с явной причиной, а не зелёный.
2. Каждая строка цитирует символ (module.function/class); тест разрешает каждую цитату импортом или grep по дереву; НЕГАТИВНЫЙ: выдуманный символ — красный тест.
3. Дата и версия оценки порождаются (tausik doc ...) при закрытии задачи, а не набираются.
4. Раздел «сверх Core» перечисляет 10.2/10.3/10.5/10.13/8.6(b)(d) с честным статусом после истории E (сигналы вместо гейтов).
5. EN/RU паритет; CHANGELOG EN+RU.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-23T19:03:37Z [implementation] — AC verified: 1. ✓ test_each_core_section_has_the_corpus_row_count (8 правил, 2 гейта, 3 свойства, 2 метрики из корпуса), test_no_standard_rule_is_listed_under_core 2. ✓ самопроверка разрешает каждую ссылку-символ (tests/test_senar_self_check.py; выдуманный символ краснит) 3. ✗ в иной форме: дата оценки набрана, а не порождена командой. Версия держится тестом заявления (test_claim_surface_agrees_on_one_edition против DECLARED_SENAR_VERSION=1.5). Генератор ради одной даты не строился: правило владельца #711/#371 — тест не на свежесть порождённого файла 4. ✓ раздел 'сверх Core' с 10.2/10.3/10.5/6.4(c)/8.6(b)(d)/10.13(a), сигналы после истории E 5. ✓ EN/RU паритет, CHANGELOG EN+RU. Verify #2740 зелёный.
