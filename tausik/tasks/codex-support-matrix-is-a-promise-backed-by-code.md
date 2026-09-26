---
slug: codex-support-matrix-is-a-promise-backed-by-code
title: "Документация и матрица поддержки для Codex: строка в матрице — обещание, а не намерение"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "docs/en/adding-new-ide.md"
  - "docs/ru/adding-new-ide.md"
  - "tests/test_codex_support_matrix.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "docs/en/adding-new-ide.md"
  - "docs/ru/adding-new-ide.md"
  - "tests/test_codex_support_matrix.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-10T06:57:47Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #241. Документация честно говорит, что Codex не scaffolded, и это придётся переписать после первых трёх задач истории. Но переписать надо ТОЧНО, а не оптимистично: матрица поддержки обязана называть, что у Codex ЖЁСТКОЕ, а что инструкция.

ЧТО УСТАНОВЛЕНО ЗАМЕРОМ и должно попасть в матрицу: у Codex есть API хуков (PreToolUse, PostToolUse, SessionStart, UserPromptSubmit, permissionDecision) - значит Rule 1 и ACL области жёсткие, наравне с Claude. QG-0, QG-2 и Verify-First жёсткие у любого хоста, потому что живут в сервисе и MCP, а не в хосте. Лимит сессии - там же.

ПОЧЕМУ ЭТО ОТДЕЛЬНАЯ ЗАДАЧА, А НЕ ХВОСТ ПРЕДЫДУЩИХ. Строка в матрице поддержки - это ОБЕЩАНИЕ. Ровно на этом обжёгся opencode: документация называла его поддержанным, пока генератора не было, и агент, заполнявший разрыв руками, уронил хост пользователя. Обещание пишется после того, как оно подкреплено кодом, и проверяется тем же тестом, что проверяет код.

## Acceptance Criteria

AC-1 docs/ru и docs/en описывают bootstrap --ide codex и получаемые артефакты; пара языков не расходится - проверяется существующим тестом парности документации. AC-2 Матрица поддержки называет режим КАЖДОГО правила у Codex словом hard или instruction, и ни одно правило не пропущено. AC-3 НЕГАТИВ, главный: тест сверяет заявленный в матрице режим с ФАКТОМ на диске - правило, объявленное hard, обязано иметь механизм, который его обеспечивает; строка без механизма краснеет. Это ровно то, чего не хватало opencode. AC-4 Упоминания о том, что Codex не scaffolded, удалены из обоих языков - иначе документация противоречит сама себе.

## Plan

[{"step": "\u0418\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0442\u0435\u043a\u0443\u0449\u0443\u044e EN/RU \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044e, \u043c\u0430\u0442\u0440\u0438\u0446\u044b \u0438 \u0442\u0435\u0441\u0442\u044b \u043f\u0430\u0440\u043d\u043e\u0441\u0442\u0438; \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0442\u043e\u0447\u043d\u044b\u0439 \u0437\u0430\u043a\u0440\u044b\u0442\u044b\u0439 \u043f\u0435\u0440\u0435\u0447\u0435\u043d\u044c \u043f\u0440\u0430\u0432\u0438\u043b Codex.", "done": true}, {"step": "\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043f\u0440\u0430\u0432\u0438\u043b\u0430 hard \u0438\u043b\u0438 instruction \u0438 \u0435\u0433\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c\u044b\u0439 \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c, \u043d\u0435 \u0437\u0430\u044f\u0432\u043b\u044f\u044f \u043d\u0435\u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043d\u043e\u0435.", "done": true}, {"step": "\u0412\u043d\u0435\u0441\u0442\u0438 \u043f\u0430\u0440\u043d\u044b\u0435 EN/RU \u043c\u0430\u0442\u0440\u0438\u0446\u0443 \u0438 \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 bootstrap-\u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u043e\u0432, \u0443\u0431\u0440\u0430\u0442\u044c \u043f\u0440\u043e\u0442\u0438\u0432\u043e\u0440\u0435\u0447\u0438\u0432\u0448\u0438\u0435 \u0444\u043e\u0440\u043c\u0443\u043b\u0438\u0440\u043e\u0432\u043a\u0438.", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043e\u0432\u0435\u0434\u0435\u043d\u0447\u0435\u0441\u043a\u0438\u0439 \u0442\u0435\u0441\u0442: \u043a\u0430\u0436\u0434\u0430\u044f hard-\u0441\u0442\u0440\u043e\u043a\u0430 \u0438\u043c\u0435\u0435\u0442 \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c \u043d\u0430 \u0434\u0438\u0441\u043a\u0435, \u043f\u0440\u043e\u043f\u0443\u0441\u043a \u0438\u043b\u0438 \u043b\u043e\u0436\u043d\u044b\u0439 hard \u043a\u0440\u0430\u0441\u043d\u0435\u0435\u0442.", "done": true}, {"step": "\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0446\u0435\u043b\u0435\u0432\u044b\u0435 \u0442\u0435\u0441\u0442\u044b, \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043d\u0443\u044e \u043f\u0430\u0440\u043d\u043e\u0441\u0442\u044c, dedupe \u0438 verify; \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c AC evidence.", "done": true}]

## Rollback

Правка документации и матрицы; откат - git revert. Код при откате не меняется, расходится только описание, и это ловит тест парности.

## Journal

- 2026-09-09T16:19:55Z [planning] — ЧАСТЬ РАБОТЫ СДЕЛАНА В СМЕНЕ #241 вместе с генератором, потому что охраны краснели: таблица платформ в docs/{ru,en}/model-providers.md больше не говорит 'нет' про Codex и называет фактические артефакты (.codex/config.toml + .codex/hooks.json, .codex/skills/, AGENTS.md); проза 'Codex пока не scaffolded' удалена в обоих языках и заменена описанием с ЦЕНОЙ абсолютных путей; test_ide_single_source переведён с 'codex не scaffolded' на параметризованный scaffold-capable. ОСТАЁТСЯ главное и несделанное: AC-2 и AC-3 — матрица режимов ПОПРАВИЛУ (hard/instruction) и тест, сверяющий заявленный режим с наличием механизма на диске.
- 2026-09-10T06:57:04Z [implementation] — Measured documentation drift: docs/{en,ru}/model-providers.md already says Codex scaffolded, but docs/{en,ru}/adding-new-ide.md still said Codex has no generator. Added paired five-contract Codex hard matrix: QG-0, QG-2/Verify-First, session limit, Rule 1, Rule 2. Matrix deliberately excludes secret-scan policy because its warn/strict choice is not an unconditional block. New test generates .codex/hooks.json, requires each hard claim to resolve to surface/realtime coverage, and proves deleting hooks removes realtime coverage for Rule 1/2. Targeted tests: 38 passed; ruff and dedupe audit passed.
- 2026-09-10T06:57:44Z [implementation] — AC verified: 1. ✓ docs/en and docs/ru now document bootstrap --ide codex artifacts, while test_codex_matrix_is_complete_and_language_paired requires both language matrices to match. 2. ✓ Both matrices contain exactly the closed five-contract list and label every row hard. 3. ✓ test_every_hard_codex_row_has_a_mechanism_in_the_generated_profile creates .codex/hooks.json and requires every hard contract to resolve to a surface or realtime mechanism; test_removing_the_generated_hooks_rejects_host_operation_hard_claims proves the red branch for Rule 1 and Rule 2. 4. ✓ EN/RU adding-new-ide no longer says Codex is unscaffolded. Evidence: python -m pytest tests/test_codex_support_matrix.py tests/test_rule_coverage.py tests/test_ide_single_source.py tests/test_audit_stale_docs.py -q => 38 passed in 3.87s; ruff and dedupe passed; signed verify #2386 passed ruff + scoped pytest. Domain: the published promise is directly derived from the profile bootstrap writes, and a missing host hook fails instead of merely leaving a stale claim. The git-mismatch receipt warning identifies adjacent pre-existing Codex work outside this task's declared relevant files.
