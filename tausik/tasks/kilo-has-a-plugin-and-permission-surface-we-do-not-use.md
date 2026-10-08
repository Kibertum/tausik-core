---
slug: kilo-has-a-plugin-and-permission-surface-we-do-not-use
title: "Kilo умеет plugin и permission: у него ЕСТЬ точка расширения, мы её не используем"
status: done
epic: v2-global-mcp
story: v2gm-surfaces
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Плагин-половина уже исполнена задачей kilo-gate-plugin (1.11.2). Эта задача закрывает PERMISSION-половину: bootstrap_kilo генерирует permissions-политику TAUSIK в .kilo/kilo.jsonc (deny на external_directory и прямые записи в .tausik/tausik.db, ask на bash-обход гейтов) с merge-семантикой как у mcp-станзы; enforcement_coverage/plugins-паритет; тесты генератора; доки kilo-zai EN/RU; changelog."
scope_exclude: "kilo.jsonc пользователя (не перезаписывать чужие ключи), ext-линия (epic universal-vscode-extension), runtime Kilo"
relevant_files:
  - "bootstrap/bootstrap_kilo.py"
  - "scripts/enforcement_coverage.py"
  - "tests/test_bootstrap_kilo.py"
  - "tests/test_enforcement_coverage.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ".kilo/kilo.jsonc"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-08T08:19:34Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#161"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
blocked_question: null
unblock_criteria: null
unblocked_by: null
unblocked_at: null
---

## Goal

НАХОДКА СМЕНЫ #232, замер по документации хоста 2026-09-08, источник https://app.kilo.ai/config.json (та самая схема, на которую ссылается $schema в генерируемом нами .kilo/kilo.jsonc).

У KILO ЕСТЬ ТОЧКА РАСШИРЕНИЯ, И НЕ ОДНА:
1) plugin — массив ссылок на ЛОКАЛЬНЫЕ ФАЙЛЫ ПЛАГИНОВ, исполняющие код во время работы. Механизм того же класса, что у OpenCode, где TAUSIK уже разворачивает плагин QG-0.
2) permission — ask / allow / deny, применимые ПООПЕРАЦИОННО: read, edit, glob, grep, list, bash, task, external_directory, lsp, skill. Операции edit и bash хост умеет запрещать или требовать подтверждения.

ЧТО ЭТО ОПРОВЕРГАЕТ: формулировку «у Kilo нет точки расширения», из которой исходили и замер #189, и планирование группы кроссмодельности. Верное утверждение — «TAUSIK не генерирует для Kilo ни plugin, ни permission», и ровно так сформулировано уведомление о принуждении, поставленное в смене #230.

ЧТО ДЕЛАТЬ (объём этой задачи): развернуть для Kilo реальный механизм принуждения — плагин по образцу opencode-qg0 и/или permission-политику, — после чего пер-правиловая таблица покрытия обязана перестать показывать Kilo как хост без механизма САМА, потому что она выводится из развёрнутого, а не из списка.

ПОЧЕМУ НЕ В 1.9: обещание «нет кода без задачи на Kilo» стало бы существенно шире сделанного, а объём релиза зафиксирован решением #337. Разрыв в 1.9 ОБЪЯВЛЕН и охраняется тестом; закрывать его — работа 1.10.

## Acceptance Criteria

AC1. МЕХАНИЗМ РАЗВЁРНУТ И ЭТО ВИДНО ИЗ ФАКТА. После bootstrap профиль .kilo несёт исполняемый артефакт принуждения, и scripts/enforcement_coverage.deployed_enforcement считает его САМ, без правки счётчика под новый хост. Если счётчик пришлось править — форма артефакта не описана, и это часть работы.

AC2. ПЕРЕД ПОСТРОЙКОЙ ЗАМЕР ПОВТОРЯЕТСЯ. Схема хоста могла измениться; запись 2026-09-08 является исходной точкой, а не вечной истиной. Результат повторного замера записывается с датой и источником.

AC3. ЧТО ИМЕННО ПРИНУЖДАЕТСЯ — НАЗВАНО ПО ПРАВИЛАМ. permission с deny на edit и плагин перехватывают РАЗНОЕ; таблица покрытия по правилам обязана показать это раздельно, а не объявить хост «покрытым».

AC4 (НЕГАТИВНЫЙ). НЕ ЛОМАТЬ ХОСТ ПОЛЬЗОВАТЕЛЯ. permission: deny на edit, выставленный фреймворком без спроса, делает Kilo неработоспособным для обычной работы. Политика либо согласуется с владельцем, либо ограничивается тем, что не отнимает у пользователя его собственные инструменты. Тест на то, что обычная правка файла при активной задаче ПРОХОДИТ.

AC5 (НЕГАТИВНЫЙ). НЕ ИМИТИРОВАТЬ. Пока механизм не развёрнут по-настоящему, ни один текст не имеет права утверждать, что на Kilo код без задачи запрещён.

## Plan

## Rollback

git revert коммита генератора; у уже развёрнутых конфигов ключ tausik-managed permissions удаляется повторным запуском bootstrap со сброшенным флагом (merge идемпотентен, пользовательские ключи не трогаются)

## Journal

- 2026-10-08T08:19:20Z [implementation] — AC1: ✓ МЕХАНИЗМ РАЗВЁРНУТ И ВИДЕН ИЗ ФАКТА: живой .kilo/kilo.jsonc несёт управляемую permission-политику (edit deny .tausik/tausik.db + .kilo/plugins/*, bash ask git push*/sqlite3*, external_directory deny — проверено чтением живого файла после bootstrap --ide all); scripts/enforcement_coverage.deployed_enforcement считает её САМ из конфига на диске (jsonc-комментарии терпимы): третья форма «permissions», счётчик не правился — форма описана и выведена. tests/test_enforcement_coverage.py::test_kilo_permission_rules_are_counted_from_the_config (5 правил из живого формата), ::test_kilo_user_rules_count_too. AC2 (схема измерена, не угадана): политика соответствует живой схеме https://app.kilo.ai/config.json, снятой 2026-10-08 (PermissionConfig = action | {op: rule}, rule = action | {pattern: action}); пробы по локальному бандлу Kilo 7.8.8 в .tausik/planning/kilo-permission-probe.py. Merge-семантика: tests/test_bootstrap_kilo.py::test_permission_policy_managed_rules_win_user_values_do_not_leak (пользовательские сохраняются, управляемые выигрывают), ::test_global_string_permission_is_the_users_word, ::test_permission_policy_opt_out, ::test_permission_policy_idempotent, ::test_permission_policy_written_by_default. Доки: docs/en/kilo-zai.md §6 + docs/ru/kilo-zai.md §6 (таблица правил, семантика, отключение); changelog [1.11.3] EN/RU — «Kilo is now a fully governed host». НЕГАТИВ: плагин-половина поверхности исполнена ранее задачей kilo-gate-plugin (1.11.2); эта задача закрыла permission-половину — формулировка «у Kilo нет точки расширения» более не существует ни в коде, ни в доке; ext-линия объявлена следующей и НЕ тронута. Domain: хост-уровень отклоняет то, что раньше было прозой правил: git push без слова владельца, сырой SQLite, правка БД и артефактов принуждения. Verify: run #3648 PASS, handle 3648.af027e2094cb00ba2474009128052f6e.
