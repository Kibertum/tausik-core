---
slug: memory-lint-stale-file-mostly-false-positives
title: "memory lint: stale_file — почти сплошь ложные срабатывания, отчёт приучают игнорировать"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/memory_cleanup.py (_extract_paths / find_lint_candidates stale_file precision: parent-dir anchor + placeholder denylist), tests/"
scope_exclude: "Не трогать contradicts/superseded детекторы; не блокировать (это отчёт, km-memory-lint-report отдельно); не менять сигнатуру file_exists"
relevant_files:
  - "scripts/memory_cleanup.py"
  - "tests/test_memory_lint.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T23:11:47Z"
---

## Goal

Аудит сессии #132. `tausik memory lint` выдаёт 20+ строк `stale_file`, и подавляющее большинство — не пути вовсе: `lru_cache/functools.cache` (#233), `release/1.8` (#279 — имя ветки), `HEAD/v1.6.1` (#208), `ru/senar.md` и `en/senar.md` (#279 — обрывки от `docs/{ru,en}/senar.md`), `tests/test_file.py` и `tests/test_x.py` (#215 — ПЛЕЙСХОЛДЕРЫ в описании формата evidence), `.cursor/rules/caveman.mdc` (#206 — цитата чужого проекта, которую мы сознательно не применяли). Детектор путей срабатывает на любую пару сегментов через слэш, а память написана прозой, где слэш чаще разделитель альтернатив, чем путь. Итог: отчёт, который на 90% шум, — это отчёт, который перестают читать, и настоящий устаревший путь в нём утонет. Нужно: поднять точность детектора (требовать расширение файла И существование каталога-предка, либо якорь вида `scripts/`, `docs/`, `tests/`), плюс явный синтаксис «это плейсхолдер». Смежная задача km-memory-lint-report решает, что лишь ОТЧЁТ и ничто не блокирует; эта — про то, что отчёт должен быть правдой.

## Acceptance Criteria

AC1. Точность stale_file: путь флагается ТОЛЬКО если (а) есть расширение [как сейчас], (б) каталог-предок СУЩЕСТВУЕТ в репо (через тот же resolver, os.path.exists истинен для директорий). Это убирает альтернатива-через-слэш и обрывки: lru_cache/functools.cache, release/1.8, HEAD/v1.6.1, ru/senar.md, en/senar.md, .cursor/rules/caveman.mdc.
AC2. Плейсхолдеры: известные примеры-имена (test_file.py, test_x.py, test_foo.py и т.п.) не флагаются — денилист базовых имён. Убирает tests/test_file.py, tests/test_x.py.
AC3. Дифф-прогон на РЕАЛЬНОЙ памяти (#298): показать число stale_file до/после; ложные из списка задачи исчезли; НАСТОЯЩИЕ устаревшие пути (если есть) сохранены (0 false-negative на реальных путях в существующих каталогах).
AC4. НЕГАТИВ: реальный устаревший путь в СУЩЕСТВУЮЩЕМ каталоге (scripts/deleted_module.py, каталог scripts/ есть) ПО-ПРЕЖНЕМУ флагается (не переужесточили). Тест.
AC5. Существующие тесты memory_cleanup/lint зелёные; добавлены тесты на каждый класс ложных + сохранение настоящих.

## Plan

## Rollback

git revert; изменение — ужесточение фильтра (аддитивные условия), откат возвращает шумный детектор. Дифф-прогон на реальной памяти покажет 0 потерь настоящих stale-путей.

## Journal

- 2026-07-26T23:11:45Z [implementation] — AC-1: ✓ Якорь каталога-предка — _parent_dir_exists (тот же resolver, os.path.exists истинен для dir). tests/test_memory_lint.py::TestStaleFilePrecision::test_slash_as_alternation_separator_not_flagged + test_path_fragment_without_anchor_not_flagged убирают lru_cache/functools.cache, release/1.8, HEAD/v1.6.1, ru/senar.md, en/senar.md, .cursor/rules/caveman.mdc. AC-2: ✓ Плейсхолдер-денилист _PLACEHOLDER_BASENAME_RE — test_placeholder_basenames_not_flagged_even_in_real_dir (tests/test_x.py, tests/test_file.py, scripts/x.py не флагаются даже когда tests/scripts существуют). AC-3: ✓ Дифф-прогон на РЕАЛЬНОЙ памяти: stale_file 53→6 (89% шума убрано); все 8 перечисленных ложных исчезли (проверено скриптом: 'listed FPs still present: []'). Остаток 6 — пути в СУЩЕСТВУЮЩИХ каталогах (настоящие/пограничные stale). verification_run #1462 (свой зелёный). AC-4: ✓ НЕГАТИВ (не переужесточили) — test_real_deletion_in_live_dir_is_still_flagged (scripts/deleted_module.py при существующем scripts/ → ПО-ПРЕЖНЕМУ флагается). test_stale_file_flagged_when_missing / test_dotfile_dir_path_still_flagged сохранены (обновлены под dir-resolver). AC-5: ✓ tests/test_memory_lint.py + test_memory_cleanup_cli.py 57 passed. mypy Success. Domain: отчёт из 90%-шума стал правдой (53→6) — отчёт, который читают. Класс #298 (дифф-прогон старой/новой на реальных данных). CHANGELOG EN+RU.
