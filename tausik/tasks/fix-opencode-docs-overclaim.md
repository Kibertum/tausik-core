---
slug: fix-opencode-docs-overclaim
title: "Убрать over-claim про OpenCode и неверный npm-пакет из model-providers.md"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "docs/ru/model-providers.md, docs/en/model-providers.md, docs/ru/adding-new-ide.md, docs/en/adding-new-ide.md"
scope_exclude: "bootstrap/, scripts/, harness/ — реализация поддержки opencode идёт отдельной задачей opencode-ide-support"
relevant_files:
  - "docs/ru/model-providers.md"
  - "docs/en/model-providers.md"
  - "docs/ru/adding-new-ide.md"
  - "docs/en/adding-new-ide.md"
  - "tests/test_docs_no_fake_npm_packages.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T12:15:08Z"
---

## Goal

Устранить первопричину инцидента у пользователя: дока объявляет OpenCode поддерживаемой платформой (skills в .claude/skills/, конфиг opencode.json), хотя ветки bootstrap для opencode нет. Агент в opencode увидел разрыв «поддерживается, но не настроено» и дописал интеграцию сам — выдумал tools.qg0 (opencode принимает в tools только boolean) и .opencode/tools/qg0.ts с импортом @opencode-ai/plugin, что уронило конфиг (ConfigInvalidError) и загрузку модулей (ERR_MODULE_NOT_FOUND). Плюс дока учит ставить несуществующий npm-пакет @anthropic-ai/opencode (реальный — opencode-ai от SST).

## Acceptance Criteria

1. В docs/ru/model-providers.md и docs/en/model-providers.md строка установки больше не содержит `@anthropic-ai/opencode`; указан реальный пакет `opencode-ai`. 2. Таблица платформ больше не утверждает, что skills OpenCode лежат в `.claude/skills/` — статус OpenCode помечен честно относительно фактического состояния bootstrap. 3. docs/ru|en/adding-new-ide.md больше не смешивает Codex и OpenCode в одну строку «Codex/OpenCode → .codex» (разные хосты, разные конфиги). 4. НЕГАТИВНЫЙ СЦЕНАРИЙ: если дока снова начнёт рекламировать несуществующий npm-пакет или необеспеченную кодом поддержку IDE — это должно ловиться, а не проходить молча. Тест tests/test_docs_no_fake_npm_packages.py падает (exit!=0) на подсунутой строке `npm i -g @anthropic-ai/opencode` и на упоминании IDE в таблице model-providers.md, отсутствующей в bootstrap_config.SCAFFOLD_IDES без явной пометки статуса. 5. Gates зелёные: tausik verify --task fix-opencode-docs-overclaim.

## Plan

## Rollback

git revert коммита с правкой доки — изменения затрагивают только markdown, кода не касаются.

## Journal

- 2026-07-14T12:15:07Z [implementation] — AC verified: 1. ✓ `npm i -g opencode-ai` в docs/{ru,en}/model-providers.md; `@anthropic-ai/opencode` остался только в предупреждающей прозе («пакета не существует»). 2. ✓ Таблица платформ переписана: колонка Scaffolded, OpenCode/Codex/Windsurf = нет, добавлены реально поддержанные Qwen/Kilo; убрано ложное «skills OpenCode в .claude/skills/». 3. ✓ docs/{ru,en}/adding-new-ide.md: строка «Codex/OpenCode» расщеплена, OpenCode описан как отдельный хост (opencode.json, .opencode/plugins/, ключ instructions). 4. ✓ НЕГАТИВНЫЙ СЦЕНАРИЙ: tests/test_docs_no_fake_npm_packages.py — 7 passed; гарды доказанно кусаются на подсунутом входе (test_fake_package_guard_actually_bites, test_scaffolded_column_guard_actually_bites, test_unreadable_scaffolded_cell_is_rejected). Таблица сверяется с bootstrap_config.SCAFFOLD_IDES динамически. Гард поймал ошибку в моей же правке (запрет строки vs запрет install-команды) — правило сужено до install-контекста. 5. ✓ tausik verify --task fix-opencode-docs-overclaim: passed=True, gates=[hadolint, pytest].
