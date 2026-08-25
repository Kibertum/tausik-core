---
slug: opencode-qg0-plugin
title: "OpenCode: QG-0-плагин (tool.execute.before) — принуждение без npm-зависимостей"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "bootstrap/bootstrap_opencode.py (добавить эмиссию плагина), шаблон JS плагина, tests/test_opencode_qg0_plugin.py"
scope_exclude: "scripts/hooks/task_gate.py — не трогать, плагин ЗЕРКАЛИТ его семантику, а не переиспользует код (разные рантаймы); правила QG-0 в scripts/ не дублировать — источник истины остаётся CLI"
relevant_files:
  - "harness/opencode/plugins/tausik-qg0.js"
  - "bootstrap/bootstrap_opencode.py"
  - "tests/test_opencode_qg0_plugin.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T13:13:20Z"
---

## Goal

Шаг 2 из 3 (после opencode-bootstrap-generator, перед opencode-ide-support). Дать OpenCode нативный аналог PreToolUse-хука Claude Code — плагин, блокирующий write/edit при отсутствии активной задачи TAUSIK. Это слой 2 из решения #131: без него «поддержка» OpenCode — просто markdown, который хост волен проигнорировать (и игнорирует: у AGENTS.md там first-matching-file-wins). Плагин пишется как JS-артефакт, ЭМИТИРУЕМЫЙ python-генератором bootstrap_opencode.py, поэтому stack=python.

## Acceptance Criteria

1. bootstrap_opencode.py эмитит .opencode/plugins/tausik-qg0.js. КАТАЛОГ — plugins/ ВО МНОЖЕСТВЕННОМ ЧИСЛЕ. Singular .opencode/plugin/ приводит к тому, что плагин МОЛЧА не грузится (на этом уже горели: github.com/steveyegge/gastown issue #1614). Тихая ошибка = прямое нарушение принципа TAUSIK, поэтому имя каталога покрыть тестом явно. 2. НОЛЬ npm-зависимостей: в файле нет ни одного import/require (в частности НЕ импортировать `@opencode-ai/plugin` — даже за типами). Именно этот импорт в самодельном qg0.ts у пользователя дал ERR_MODULE_NOT_FOUND (opencode пытался тянуть несуществующую версию @local) и убил обработку промптов целиком. Типы — только через JSDoc-комментарии. Тест: регексп по эмитированному файлу не находит import/require/from '...'. 3. Экспорт соответствует контракту OpenCode: `export const TausikQG0 = async ({ project, client, $, directory, worktree }) => ({ "tool.execute.before": async (input, output) => {...} })`. 4. СЕМАНТИКА: если имя тула — пишущий (write/edit/patch — уточнить фактические имена тулов OpenCode перед реализацией, НЕ УГАДЫВАТЬ) и активной задачи TAUSIK нет — бросить ошибку с внятным текстом («QG-0: нет активной задачи. Выполни `tausik task start <slug>`»), чтобы хост не выполнил запись. Read-only тулы не трогать. 5. ИСТОЧНИК ИСТИНЫ ПРО АКТИВНУЮ ЗАДАЧУ: `.tausik/tausik status --compact` (однострочный JSON, поле tasks_active) через Bun-shell `$` из контекста плагина. НЕ читать SQLite напрямую из JS: правило «нет прямого доступа к БД, только MCP/CLI» + bun:sqlite недоступен вне Bun. 6. FAIL-OPEN ПО УМОЛЧАНИЮ (зеркалит scripts/hooks/task_gate.py): если CLI недоступен/упал/таймаут — пропускать запись, а не блокировать (иначе сломанный doctor кирпичит чужой проект). При TAUSIK_HOOK_FAIL_SECURE=1 — наоборот, блокировать. При TAUSIK_SKIP_HOOKS=1 — не вмешиваться вовсе. Все три ветки покрыть тестами. 7. ПРОИЗВОДИТЕЛЬНОСТЬ: вызов CLI на КАЖДЫЙ write — это python-субпроцесс (100-300мс на Windows; именно из-за этого task_gate.py в v1.4 ушёл с субпроцесса на прямой SQLite). Замерить и, если больно, ввести короткий кэш (напр. 2с) — но ТОЛЬКО в сторону строгости: устаревший ответ не должен ПРОПУСКАТЬ запись, которую надо было блокировать. Решение зафиксировать в tausik decide. 8. НЕГАТИВНЫЕ СЦЕНАРИИ (tests/test_opencode_qg0_plugin.py): (а) нет активной задачи + write → блок; (б) есть активная задача + write → пропуск; (в) read-only тул без задачи → пропуск; (г) CLI недоступен → пропуск (fail-open); (д) CLI недоступен + TAUSIK_HOOK_FAIL_SECURE=1 → блок; (е) в эмитированном JS нет import/require; (ж) каталог именно plugins/, не plugin/. 9. Gates зелёные: tausik verify --task opencode-qg0-plugin.

## Plan

## Rollback

git revert. Плагин — отдельный эмитируемый файл; его удаление возвращает OpenCode в состояние «правила только в промпте» без поломки конфига (opencode.json остаётся валидным, mcp-стансы не зависят от плагина).

## Journal

- 2026-07-14T13:13:19Z [implementation] — AC verified прогоном tests/test_opencode_qg0_plugin.py (23 passed; семантика хука исполняется под Node с подставными $ и Bun, а не проверяется чтением): 1. ✓ generate_opencode_plugin() кладёт .opencode/plugins/tausik-qg0.js — TestEmission::test_lands_in_plugins_plural_not_singular (проверяет и что каталога plugin/ в единственном числе НЕТ). Имя каталога вынесено в константу _PLUGINS_SUBDIR с объяснением, почему singular = тихая потеря принуждения. 2. ✓ Ноль npm-зависимостей — test_no_import_or_require_anywhere: регексп по коду (с вычетом комментариев) на static import, dynamic import(), require(), bare `from '...'`, плюс отдельная проверка на подстроку @opencode-ai/plugin. Типы — JSDoc. 3. ✓ Контракт экспорта — test_exports_the_opencode_contract: `export const TausikQG0 = async ({...})` + ключ "tool.execute.before". 4. ✓ Семантика на РЕАЛЬНЫХ именах тулов, взятых из opencode.ai/docs/tools, не угаданных (gotcha #202): write/edit/apply_patch гейтятся (test_every_write_tool_is_gated), read/grep/glob/bash/webfetch/todowrite проходят без задачи и даже не платят за вызов CLI (test_read_only_tools_pass_without_a_task, assert calls == 0). Блок — через throw с текстом «QG-0: нет активной задачи. Выполни `tausik task start <slug>`» (официальный способ отмены вызова в OpenCode). 5. ✓ Источник истины — `.tausik/tausik status --compact` через Bun-shell $; прямого SQLite из JS нет. На Windows берётся tausik.cmd (голый tausik — bash-скрипт, шеллу Bun его нечем исполнить). 6. ✓ Fail-open по умолчанию — test_cli_unavailable_fails_open; TAUSIK_HOOK_FAIL_SECURE=1 → блок (test_cli_unavailable_fails_secure_when_flagged); TAUSIK_SKIP_HOOKS=1 → не вмешивается и не зовёт CLI (test_skip_hooks_disables_the_gate). Зеркалит scripts/hooks/task_gate.py. 7. ✓ Производительность ЗАМЕРЕНА, не угадана: `status --compact` = 320 мс прогретым, 1132 мс вхолодную (Windows). Введён кэш, привязанный к подписи БД (size+mtime tausik.db и tausik.db-wal), TTL 2с сверху. Решение #133. Строгость доказана тестом test_task_done_invalidates_a_cached_allow: после закрытия задачи (сдвиг WAL) кэшированное разрешение умирает, запись блокируется. Без подписи (нет Bun) кэшируется только блок — test_without_a_signature_an_allow_is_never_reused (3 записи = 3 вызова CLI), test_without_a_signature_a_block_may_be_reused (3 записи = 1 вызов). Выигрыш: 3 записи при неизменной БД = 1 вызов CLI вместо 3. 8. ✓ Негативные (а)-(ж) — все семь покрыты, см. выше; плюс test_missing_source_raises_loudly: отсутствие исходника плагина роняет bootstrap с OpenCodePluginMissing, а не пропускает проект без принуждения молча. 9. ✓ Gates: tausik verify --task opencode-qg0-plugin passed=True (hadolint, pytest). Domain: вне тестов плагин загружается OpenCode без единой npm-установки (нулевые импорты — то самое, чего не хватило самодельному qg0.ts пользователя), а запись без активной задачи отменяется тем же способом, каким это делает официальный пример защиты .env — throw из tool.execute.before.
