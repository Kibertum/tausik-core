---
slug: brain-classifier
title: "Rule-based classifier: project markers → local, generalizable → brain"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_classifier.py (new), tests/test_brain_classifier.py (new)"
scope_exclude: "scripts/hooks/memory_markers.py (reuse as-is, не править), scripts/brain_scrubbing.py (другой слой — блокатор, не трогать), scripts/brain_mcp_write.py (integration будет в brain-decide-auto-route, не здесь)"
relevant_files:
  - "scripts/brain_classifier.py"
  - "tests/test_brain_classifier.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T09:34:50Z"
---

## Goal

Классификатор принимает content+category, возвращает routing decision (local/brain) + reason. Rules: если содержит пути/slug'и/имена из blocklist/internal URLs → local; иначе → brain. Переиспользовать markers-модуль из memory-post-write-audit.

## Acceptance Criteria

1. classify(content, category) возвращает Decision(target, reason, markers) для любой валидной категории (decision/pattern/gotcha/web_cache). 2. Любой hit от memory_markers.detect_markers() → target="local" с конкретной причиной (какой kind сработал: abs_path/src_file/tausik_cmd/slug). 3. Упоминание имени из union blocklist (cfg['project_names'] ∪ brain_project_registry.all_project_names()) → target="local" даже при пустом markers. 4. Отсутствие markers и blocklist-hit → target="brain" с reason="no project-specific markers detected". 5. Категория web_cache без markers → target="brain" даже при slug-like формах <3 сегментов (кэш внешних URL обычно generalizable). 6. Negative: пустой content → Decision(target="local", reason="empty content") — default safe. 7. Negative: не-string content (None, int, bytes) → TypeError fail-fast как brain_scrubbing.scrub.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c scripts/brain_classifier.py: dataclass Decision + classify(content, category, *, cfg=None). \u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c detect_markers \u0438\u0437 scripts/hooks/memory_markers.py (reuse as-is)", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c union-blocklist: cfg.get('project_names', []) \u222a brain_project_registry.all_project_names() \u2014 lazy import \u043a\u0430\u043a \u0432 brain_scrubbing.scrub_with_config", "done": true}, {"step": "Per-category \u043f\u0440\u0430\u0432\u0438\u043b\u0430: web_cache \u2192 bias toward brain \u043f\u0440\u0438 \u043f\u0443\u0441\u0442\u044b\u0445 markers (\u0438\u0433\u043d\u043e\u0440\u0438\u0442\u044c \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0435 slug-like \u0444\u043e\u0440\u043c\u044b); decision/pattern/gotcha \u2014 strict (\u043b\u044e\u0431\u043e\u0439 marker = local)", "done": true}, {"step": "Unit-\u0442\u0435\u0441\u0442\u044b tests/test_brain_classifier.py: markers present/absent, blocklist hit/miss (\u0441 mock registry \u0447\u0435\u0440\u0435\u0437 TAUSIK_BRAIN_REGISTRY autouse fixture), category bias web_cache vs decision, edge cases (empty, non-string, bytes, None)", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c pytest tests/test_brain_classifier.py, pytest tests/ (full suite), ruff check, mypy scripts/brain_classifier.py. \u0417\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c evidence \u0447\u0435\u0440\u0435\u0437 task_log", "done": true}, {"step": "\u041a\u043e\u043c\u043c\u0438\u0442 feat(brain): rule-based local/brain classifier \u2014 \u0441 \u0434\u0435\u0442\u0430\u043b\u044c\u043d\u044b\u043c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435\u043c", "done": true}]

## Rollback

## Journal

- 2026-04-24T09:24:56Z [implementation] — Дизайн-решение: reuse detect_markers через sys.path.insert(scripts/hooks/) в brain_classifier.py — без move файла и без изменения самого hooks/memory_markers.py. Тот же идиом в hooks/notify_on_done.py (двойной sys.path.insert для parent+self). API: Decision(target, reason, markers, blocklist_hit) как NamedTuple. Порядок приоритетов: empty → markers → blocklist → brain.
- 2026-04-24T09:30:25Z [implementation] — AC-verification evidence: - AC1 (Decision для 4 категорий): test_classify_returns_decision_for_each_valid_category ✓ - AC2 (markers → local): test_abs_path/src_file/tausik_cmd/slug_marker_routes_local ✓ (4 теста по kind) - AC3 (union blocklist): test_blocklist_from_cfg_routes_local + test_blocklist_union_with_registry ✓ - AC4 (default → brain): test_clean_content_routes_brain + test_clean_content_all_categories_route_brain ✓ - AC5 (web_cache bias): test_web_cache_suppresses_slug_markers + 3 negative теста что другие markers всё ещё блокируют ✓ - AC6 (empty → local): test_empty_content_routed_local + test_whitespace_only ✓ - AC7 (non-string → TypeError): test_classify_rejects_non_string_content (6 типов) ✓ Gates: - pytest tests/test_brain_classifier.py: 23/23 pass - pytest tests/ full: 1499 passed, 2 skipped, 0 failed (было 1478+, +23 моих = 1501 total = совпадает) - ruff check scripts/brain_classifier.py tests/test_brain_classifier.py: All checks passed - mypy scripts/: Success, no issues in 61 files Коммит готов.
- 2026-04-24T09:30:59Z [implementation] — AC verified: 1. classify() возвращает Decision для всех 4 категорий ✓ 2. любой memory_markers hit → target=local с конкретным kind в reason ✓ 3. имя из union blocklist (cfg ∪ registry) → target=local ✓ 4. пустой markers + пустой blocklist → target=brain ✓ 5. web_cache игнорирует slug, но блокирует abs_path/src_file/tausik_cmd ✓ 6. empty content → Decision(local, empty content) ✓ 7. non-string → TypeError fail-fast ✓. Tests: 23/23 pass (tests/test_brain_classifier.py), full suite 1499 passed, 2 skipped. Gates: ruff clean on new files, mypy scripts/ clean (61 files).
