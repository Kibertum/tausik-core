---
slug: s130-review-fixes
title: "Ревью-фиксы батча #130: дыры в собственных гейтах (лит-линт мимо mid-string, гейт цен судит дефолт а не конфиг, roles/profile_dir/phantom-lint)"
status: done
epic: null
story: null
complexity: complex
role: null
stack: null
tier: null
call_budget: null
defect_of: block-messages-phantom-go-and-platform
scope: "scripts/cost_pricing.py, scripts/model_profiles.py (чтение load_families), scripts/model_routing_matrix.py (чтение override-поверхности), scripts/service_roles.py, scripts/hooks/session_start.py, tests/test_doctor_multi_ide.py, tests/test_cost_pricing.py, tests/test_block_message_quality.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Рантайм-оценка стоимости не-Claude моделей (cost-pricing-non-claude-families-silent-zero), реестр гейтов, changelog-гейт runtime-логика, схема БД"
relevant_files:
  - "scripts/cost_pricing.py"
  - "scripts/service_roles.py"
  - "scripts/hooks/session_start.py"
  - "tests/test_doctor_multi_ide.py"
  - "tests/test_cost_pricing.py"
  - "tests/test_block_message_quality.py"
  - "tests/test_service_roles.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T18:36:08Z"
---

## Goal

Adversarial-ревью трёх закрытых задач #130 нашло, что механизмы, построенные ради неповторимости дефектов, сами дырявы (класс #266 «гейт судит свою копию, а не производителя»). HIGH-1: cost_pricing.routed_claude_model_ids читает model_profiles.DEFAULT_FAMILIES (хардкод-дефолты), а НЕ эффективный конфиг (load_families(config) + model_routing.* overrides), поэтому проект, легально перенаправивший ранг opus на неоценённый id через .tausik/config.json, снова метрит $0.00 при зелёном гейте; тест test_the_guard_reads_the_real_routing_tables доказывает лишь, что гейт достаёт ДЕФОЛТЫ, а его докстринг обещает «таблицы, которые реально решают роутинг». HIGH-2: линт .claude в test_doctor_multi_ide матчит .claude только как ПЕРВЫЙ символ строкового литерала — 'harness/.claude/foo' и 'some/path/.claude' проходят мимо, то есть у самого линта, закрывающего doctor-дефект, дыра в детекторе. MEDIUM-1: service_roles._profile_path_deployed получил параметр project_dir, но единственный вызыватель _read_profile его не передаёт — всё ещё падает в os.getcwd() (класс mcp-config-read-paths / #265), IDE-awareness докстринга не исполняется. MEDIUM-2: session_start._profile_dir двумя dirname возвращает КОРЕНЬ ПРОЕКТА (в нём тоже есть scripts/), когда хук запущен из исходников, а не из профиля; fail-safe только по случайности (нет project_root/mcp и /skills). MEDIUM-3: phantom-skill линт покрывает только hooks/*.py и SKILL.md, а /skill-ссылки есть в gate_ac_check, gate_qg0_check, project_cli_ops и др. — большинство CLI-текста мимо линта.

## Acceptance Criteria

AC1 (HIGH-2, дыра линта .claude). Регекс ловит .claude в ЛЮБОЙ позиции строкового литерала: регресс-кейсы 'harness/.claude/foo' и 'some/path/.claude' ЛОВЯТСЯ. Новые найденные литералы либо на ide_utils, либо в _ALLOWED с причиной.
AC2 (HIGH-1, гейт цен судит конфиг). routed_claude_model_ids читает ЭФФЕКТИВНЫЙ конфиг через model_profiles.load_families(cfg) + сканирует model_routing.* на claude-подобные id, а не только DEFAULT_FAMILIES; докстринг в соответствие. Fail-then-pass: конфиг-override на неоценённый claude-id → models_missing_pricing его репортит. Рантайм-оценка не-Claude — НЕ здесь.
AC3 (MEDIUM-1, roles cwd). project_dir протянут role_show → _read_profile → _profile_path_deployed, либо параметр удалён как не подключённый. Тест на резолв из чужого cwd.
AC4 (MEDIUM-2, profile_dir из исходников). _profile_dir требует ПОЗИТИВНЫЙ маркер профиля (mcp/project/server.py или skills/start), а не отсутствие mcp//skills/; регресс: запуск из scripts/hooks/ → None.
AC5 (MEDIUM-3, узкий phantom-линт). Линт /skill покрывает scripts/**/*.py; найденные фантомы исправлены.
AC6. Полный pytest зелёный, без warnings. AC7. Оба CHANGELOG обновлены прозой.

## Plan

## Rollback

git revert коммита; изменения — ужесточение проверок и протяжка параметра, откат пофайлово через git checkout --.

## Journal

- 2026-07-23T18:36:06Z [implementation] — AC1 (HIGH-2) ✓ _LITERAL ловит .claude в любой позиции литерала; регресс test_lint_catches_claude_anywhere_in_the_literal на 'harness/.claude/foo' и 'some/path/.claude', негатив на obj.claude; 3 новых ~/.claude (HOME auto-memory) внесены в _ALLOWED по существу, тест на протухшие исключения активен. AC2 (HIGH-1) ✓ routed_claude_model_ids(config) через model_profiles.load_families + скан model_routing.*; докстринг исправлен; fail-then-pass test_guard_reads_the_effective_config_not_only_defaults (override на claude-opus-99-0) + test_guard_reads_per_phase_routing_overrides. AC3 (MEDIUM-1) ✓ project_dir выведен из be.db_path (_project_dir_from_be, только каноничная <root>/.tausik/), протянут role_show→_read_profile→_profile_path_deployed/user; тесты test_deployed_profile_resolves_against_the_project_not_cwd (из чужого cwd находит развёрнутый профиль, без pd — None) + test_project_dir_from_be_ignores_noncanonical_db_path. AC4 (MEDIUM-2) ✓ _profile_dir требует маркер mcp/project/server.py или skills/start; проверено — из scripts/hooks исходников возвращает None. AC5 (MEDIUM-3) ✓ линт /skill покрывает scripts/**/*.py, но через _user_facing_strings (AST: аргументы print + тексты raise), docstring/URL/word-pair исключены; test_user_facing_extractor_excludes_docstrings_and_urls; /run и /fast (реальные команды Claude Code) в _BUILTINS. AC6 ✓ полный прогон 5433 passed / 23 skipped, без warnings. AC7 ✓ проза в обоих CHANGELOG. Domain: все резолвы проверены на реальной ФС (фикстуры создают настоящие .cursor/.claude каталоги и БД, не моки); _profile_dir подтверждён запуском из исходников. Negative: каждый гейт проверен на СРАБАТЫВАНИЕ (fail-then-pass), а не только на зелёный проход — оба HIGH имеют тест, что защита реально ловит внесённую дыру.
- 2026-07-23T18:36:06Z [implementation] — Root cause (missing-validation): гейт/линт, построенный ради неповторимости дефекта, сам судил СВОЮ КОПИЮ данных, а не производителя (#266) — тот же класс, что чинил исходный батч. Гейт цен читал DEFAULT_FAMILIES вместо load_families(config); линт .claude якорил на кавычке; roles-параметр не был подключён; profile_dir искал общий маркер scripts/. Prevention: (1) гейт покрытия читает ЭФФЕКТИВНЫЙ конфиг (load_families + model_routing overrides), fail-then-pass на конфиг-override; (2) регекс линта ловит сегмент в любой позиции + fail-then-pass на mid-string; (3) резолв каталога проекта выведен из be.db_path и ТОЛЬКО из каноничной раскладки — нестандартный путь даёт None, а не кривой guess; (4) profile_dir требует ПОЗИТИВНЫЙ маркер, а не отсутствие чужого; (5) расширение phantom-линта на scripts/ упёрлось в 12 ложняков (URL-пути, word/word) — вместо allowlist сужен AST-проходом до строк в print/raise, то есть до реальных user-facing сообщений. Урок: adversarial-review ОБЯЗАН идти на фиксы (#276), и первый же проход по собственным гейтам нашёл в них ровно тот антипаттерн, который они призваны ловить.
