---
slug: state-git-export
title: "Экспорт БД → git-native файлы: детерминированный сериализатор состояния проекта"
status: done
epic: team-state-in-git
story: state-in-branch-mvp
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/state_export.py (новый сериализатор), scripts/state_serialize.py (общий frontmatter+body рендер, если нужен для <400 строк), scripts/project_parser.py + scripts/project_cli_*.py (CLI 'state export'), tests/test_state_export.py (новый)"
scope_exclude: "state-git-import (обратная сторона, отдельная задача); memory_edges схема; verify_runs/events/telemetry (не едут); .tausik/ приватный тренажёр"
relevant_files:
  - "scripts/state_export.py"
  - "scripts/state_serialize.py"
  - "scripts/project_cli_state.py"
  - "scripts/project_parser_state.py"
  - "tests/test_state_export.py"
scope_paths:
  - "scripts/state_export.py"
  - "scripts/state_serialize.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_state.py"
  - "scripts/project_cli_state.py"
  - "scripts/project.py"
  - "tests/test_state_export.py"
  - "docs/ru/team-state-in-git.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-25T17:14:17Z"
---

## Goal

Реализовать сериализатор: состояние TAUSIK (в объёме из state-git-spec — tasks, task_logs, epics, stories, decisions, memory, memory_edges) → дерево текстовых файлов по контракту state-git-spec (по файлу на сущность, md+frontmatter).

Требования: (1) ДЕТЕРМИНИРОВАННОСТЬ — один и тот же стейт БД даёт байт-идентичный файл на любой машине и при повторном экспорте (стабильный порядок полей, сортировка списков, нормализация переводов строк/дат). Иначе diff шумит и мержи ложно конфликтуют. (2) Полнота — ни одно поле сущности из объёма не теряется (то, что нужно для обратной пересборки в state-git-import). (3) Идемпотентность — повторный экспорт без изменений в БД не меняет ни одного файла (git status чист). (4) Использует стабильные id из state-git-stable-ids как имена файлов/ключи связей. CLI: `tausik state export` (имя уточнить). Кода импорта здесь нет — только БД→файлы.

## Acceptance Criteria

1. ДЕТЕРМИНИЗМ: export(db) дважды подряд даёт байт-идентичные файлы; правила нормализации соблюдены — только LF + один завершающий \n, фиксированный порядок ключей frontmatter (по спеке), tags по алфавиту, edges по (relation,target_type,target), relevant_files/scope_paths в объявленном порядке с удалением дублей, даты ISO-8601 UTC Z без микросекунд, null явно, неоднозначные строки (слаг '2026-01', 'on') в кавычках. 2. ПОЛНОТА: каждое durable-поле сущностей в объёме (tasks, task_logs->Journal, epics, stories, decisions, memory, memory_edges) сериализовано; рантайм/телеметрия-поля из спеки НЕ едут. 3. ИДЕМПОТЕНТНОСТЬ: повторный export без изменений в БД не меняет ни байта (git status по tausik/ чист). 4. Имена файлов и ключи рёбер — стабильные слаги из state-git-stable-ids; раскладка tausik/{epics,stories,tasks,decisions,memory}/<slug>.md. 5. НЕГАТИВ: сущность без слага -> export ОТКАЗЫВАЕТ с явной ошибкой 'нужна миграция', не молча пропускает и не генерит эфемерный слаг. 6. НЕГАТИВ/граница: каждое множественное поле имеет детерминированный порядок — тест на два прогона на 'разных машинах' (перемешанный порядок строк из БД) даёт тот же файл. 7. CLI 'tausik state export' пишет дерево под tausik/. 8. Полный scoped verify зелёный.

## Plan

## Rollback

Экспорт — чистое чтение БД + запись в tausik/ (новый каталог, ещё в .gitignore до state-git-roundtrip-gate). Откат: git revert коммита + rm -rf tausik/. Не трогает БД, схему, миграции — читает только. Ничего необратимого.

## Journal

- 2026-07-25T16:06:22Z [implementation] — Started. Прочитал контракт team-state-in-git.md (раскладка tausik/{epics,stories,tasks,decisions,memory,specs}/<slug>.md; frontmatter key order + нормализация: LF-only, 1 trailing \n, tags alpha, edges by (relation,target_type,target), relevant_files/scope_paths preserve-order+dedup, ISO-8601 Z no micros, null explicit, YAML-quote ambiguous). Прочитал slug_util (slugify/make_slug/first_line) и backend_crud_knowledge (decisions: id,decision,task_slug,rationale,created_at,slug; memory: id,type,title,content,tags,task_slug,created_at,updated_at,slug,archived_at). Explore-агент картирует полную схему tasks/epics/stories/memory_edges/task_logs/specs + CLI-wiring.
- 2026-07-25T16:49:52Z [implementation] — Реализация завершена. 3 модуля + parser: state_serialize.py (269, stdlib frontmatter-эмиттер с фикс. порядком ключей/кавычками неоднозначных/null-explicit/LF + FS write/check/assert), state_export.py (277, рендереры 5 сущностей + build_tree + slug-резолв story→epic + edge id→slug + slug-less refusal + dangling-edge warning), project_cli_state.py (97) + project_parser_state.py (28, вынесен чтобы project_parser.py=397<400). Решения: stdlib-only (не PyYAML — ядро флагмана); экспорт только ЖИВОГО стейта (non-archived memory, valid_to IS NULL edges); specs вне scope этой задачи; journal-tiebreak по контенту (created_at,message,phase) не по машинно-локальному id (AC-6); даты в кавычках (контракт п.6, PyYAML не коагулирует в datetime). Верификация: живой экспорт 1953 файла + --check идемпотентно чист; 25 тестов (8 AC + адверсариальные YAML-инъекция/coercion под настоящим PyYAML: newline-в-title экранируется, ambiguous→строки, встроенный --- не рвёт структуру); scoped verify pytest PASS; ruff чист; 73 CLI-guard теста зелёные после рефактора parser. Адверсариальный tausik-reviewer запускался, но фоновый агент не вернул вывод (0 байт, вероятно ECONNRESET как ранее) — критическую часть его scope (детерминизм+YAML) покрыл сам конкретными тестами.
- 2026-07-25T17:07:43Z [implementation] — AC verified: 1. ✓ Детерминизм+нормализация: tests/test_state_export.py::test_export_is_deterministic_across_two_builds, ::test_lf_only_and_single_trailing_newline, ::test_fixed_frontmatter_key_order_for_task, ::test_tags_sorted_alphabetically, ::test_edges_sorted_and_target_is_slug, ::test_dates_normalized_to_z_without_micros, ::test_null_fields_explicit, ::test_ambiguous_scalars_quoted, ::test_ordered_list_dedup_preserves_declared_order, ::test_yaml11_reserved_tokens_quoted, ::test_frontmatter_always_valid_yaml (парсинг вывода настоящим PyYAML), ::test_ambiguous_values_stay_strings_under_real_yaml 2. ✓ Полнота (durable сериализовано, runtime исключён): ::test_all_durable_fields_serialized_runtime_excluded (проверяет присутствие goal/plan/ac/rollback/scope/scope_tools/call_budget/tier И отсутствие risk_score/attempts/claimed_by/started_at), ::test_journal_line_format, ::test_memory_title_serialized_and_roundtrippable (закрытый ревью-дефект: title NOT NULL durable) 3. ✓ Идемпотентность: ::test_export_idempotent_write_then_check_clean (write→check==[]→re-write байт-в-байт); ::test_check_tree_detects_crlf_corruption (доказывает что --check реально ловит байтовую разницу, не слеп к CRLF); живой прогон: export 1953 файла затем --check = OK 4. ✓ Стабильные слаги + раскладка tausik/{epics,stories,tasks,decisions,memory}/<slug>.md: ::test_layout_paths_use_slugs; edge target = слаг: ::test_edges_sorted_and_target_is_slug 5. ✓ НЕГАТИВ slug-less refuses с указанием на миграцию: ::test_slugless_decision_refuses_with_migration_hint (проверяет текст 'state-git-stable-ids'), ::test_slugless_memory_refuses 6. ✓ НЕГАТИВ/граница машинно-независимость: ::test_shuffled_row_order_yields_identical_bytes (две БД, обратный порядок вставки memory+logs с одинаковым created_at → байт-идентичные деревья; journal-tiebreak по контенту не по autoincrement id) 7. ✓ CLI 'tausik state export' пишет дерево под tausik/: ::test_cli_state_export_writes_tree (subprocess end-to-end); живой прогон: 1953 файла записаны, --check идемпотентно чист, рукописный README пережил ре-экспорт, deleted громко печатаются 8. ✓ Scoped verify зелёный: tausik verify --task state-git-export → pytest PASS (31 тест), hadolint SKIP (нет Dockerfile); ruff чист; все файлы под filesize cap 400
- 2026-07-25T17:13:16Z [implementation] — AC verified: 1. ✓ Детерминизм+нормализация: test_state_export.py::test_export_is_deterministic_across_two_builds, ::test_lf_only_and_single_trailing_newline, ::test_fixed_frontmatter_key_order_for_task, ::test_tags_sorted_alphabetically, ::test_edges_sorted_and_target_is_slug, ::test_dates_normalized_to_z_without_micros, ::test_null_fields_explicit, ::test_ambiguous_scalars_quoted, ::test_ordered_list_dedup_preserves_declared_order, ::test_yaml11_reserved_tokens_quoted, ::test_frontmatter_always_valid_yaml, ::test_ambiguous_values_stay_strings_under_real_yaml 2. ✓ Полнота: ::test_all_durable_fields_serialized_runtime_excluded (durable присутствуют, risk_score/attempts/claimed_by/started_at отсутствуют), ::test_journal_line_format, ::test_memory_title_serialized_and_roundtrippable 3. ✓ Идемпотентность: ::test_export_idempotent_write_then_check_clean, ::test_check_tree_detects_crlf_corruption; живой прогон 1953 файла + --check OK 4. ✓ Слаги+раскладка: ::test_layout_paths_use_slugs, ::test_edges_sorted_and_target_is_slug 5. ✓ НЕГАТИВ slug-less refusal: ::test_slugless_decision_refuses_with_migration_hint, ::test_slugless_memory_refuses 6. ✓ НЕГАТИВ машинно-независимость: ::test_shuffled_row_order_yields_identical_bytes 7. ✓ CLI пишет дерево: ::test_cli_state_export_writes_tree; живой прогон 1953 файла, README сохранён, deleted печатаются 8. ✓ Scoped verify: pytest PASS (31 тест), ruff чист, filesize под cap; bootstrap redeploy --ide all выполнен
- 2026-07-25T17:14:15Z [implementation] — AC 1-8 верифицированы (evidence_json приложен в предыдущем прогоне task_done): детерминизм/нормализация, полнота, идемпотентность, слаги+раскладка, slug-less refusal, машинно-независимость, CLI-дерево, scoped verify — 31 тест PASS. Ревью-фиксы (CRLF-детекция, deletion-scoping, memory.title, YAML-1.1) покрыты регрессионными тестами.
- 2026-07-25T17:14:58Z [done] — Negative: сущность без стабильного слага → ExportError с текстом 'state-git-stable-ids' (test_slugless_decision_refuses_with_migration_hint/test_slugless_memory_refuses); dangling valid-edge → drop + warning не молча (test_dangling_edge_dropped_with_warning_not_silently); CRLF-пересохранение → --check ловит 'changed' (test_check_tree_detects_crlf_corruption); чужой tausik/README.md → не сметается (test_write_tree_preserves_non_entity_files). Domain: на ЖИВОЙ БД экспортированы 1953 файла (99 epics/231 stories/1146 tasks/173 decisions/304 memory), кириллица/двоеточия/тире корректно квотятся и парсятся настоящим PyYAML, --check идемпотентно чист повторно — вывод семантически валиден вне юнит-тестов. Задача закрыта: risk 0.11 low, 31 тест PASS, bootstrap redeploy --ide all, спека team-state-in-git.md синхронизирована с эмиттером.
