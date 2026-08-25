---
slug: l26-narrative-honesty
title: "Привести нарратив README и доков в соответствие с кодом"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/receipts.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/architecture.md"
  - "docs/ru/receipts.md"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "tests/conftest.py"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_tausik_service.py"
  - "scripts/gate_changelog.py"
  - "tests/test_changelog_gate.py"
scope_paths:
  - README.md
  - README.ru.md
  - "docs/ru/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-22T19:29:33Z"
---

## Goal

РАЗРЫВ МЕЖДУ ОБЕЩАНИЕМ И КОДОМ. README заявляет hard gates it physically cannot skip и enforcement, а собственные докстринги честны: git_push_gate.py:16-19 говорит discipline rail, not a malicious-agent firewall, renar_conformance.py:186-189 помечает свой же сигнал вакуумно-истинным. Архитектурный разбор 2026-07-18 показал таблицу обходов, где каждая строка тривиальна: запись через Bash, объявление complexity=simple, сужение relevant_files, самозапись L3-ревью, чтение приватного ключа. Контекст, делающий это важным: индустрия в 2026 отказалась от веры в модельный слой и сошлась на детерминированном контейнменте, а обязательства EU AI Act по логированию для high-risk вступают в силу в августе 2026, что делает подобные заявления юридически значимыми. ЗАВИСИМОСТЬ: делать ПОСЛЕ l26-config-trust-tiers и l26-hook-contract-review, иначе переписывать дважды. Цель не отступление, а точность: дисциплинарный рельс с tamper-evidence против внешних правок — сильная и защитимая позиция.

## Acceptance Criteria

AC1. Завышающие заявления README («hard gates it physically cannot skip», «enforcement») переписаны в точные формулировки (дисциплинарный рельс + tamper-evidence против внешних правок), согласованные с докстрингами git_push_gate.py:16-19 и renar_conformance.py:186-189.
AC2. Зеркало README.ru.md и docs приведены в соответствие: grep по спорным формулировкам не находит утверждений о защите от того, что тривиально обходится (Bash-запись, complexity=simple, сужение relevant_files, самозапись L3-ревью, чтение приватного ключа).
AC3. Позиция изложена как точность, а не отступление: доки честно описывают сильную сторону — дисциплинарный рельс с tamper-evidence — без ложных обещаний непробиваемого enforcement.
AC4. Соблюдена зависимость: задача выполнена ПОСЛЕ l26-config-trust-tiers и l26-hook-contract-review (оба done).
AC5 (негативный/граничный сценарий). grep -niE 'physically cannot skip|cannot be skipped|unbreakable|непробива' по README.md и README.ru.md возвращает ПУСТО (0 совпадений) — ни одно утверждение о защите от тривиально обходимого не выживает; иначе задача НЕ считается закрытой (ошибка проверки, а не вакуумный проход).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; формулировки возвращаются к прежним

## Journal

- 2026-07-22T19:29:32Z [implementation] — AC1 ✓ README.md: «hard gates it physically cannot skip»→«дисциплинарный рельс + tamper-evidence против внешних правок, не firewall против целеустремлённого агента»; «enforcement»→«evidence»; согласовано с git_push_gate.py:16-19 (discipline rail, not malicious-agent firewall) и renar_conformance.py:186-189. AC2 ✓ README.ru.md зеркалирован + docs/ru/architecture.md выровнен; grep по спорным формулировкам пуст. AC3 ✓ позиция как точность: threat model = тихий дрейф честного агента, не determined; сильная сторона (рельс+tamper-evidence) названа без ложных обещаний непробиваемости. AC4 ✓ выполнено после l26-config-trust-tiers + l26-hook-contract-review (оба done). AC5 (негативный) ✓ grep -niE 'physically cannot skip|cannot be skipped|unbreakable|непробива' README.md README.ru.md → 0 совпадений (проверено). Negative: grep возвращает ПУСТО — ни один overclaim не выжил. CHANGELOG.md+ru обновлены прозой. Domain: тексты README отражают реальное поведение кода (docstrings-oracle), не тесты.
