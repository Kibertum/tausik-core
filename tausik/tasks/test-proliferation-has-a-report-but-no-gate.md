---
slug: test-proliferation-has-a-report-but-no-gate
title: "Размножение тестов ловится отчётом, а не гейтом — и tests/ освобождён от единственного размерного правила"
status: planning
epic: release-19-renar-conformance
story: test-evidence-not-test-volume
complexity: null
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, сессия #178: 403 файла тестов, 5722 функции, 92429 строк. Детектор дублей УЖЕ ЕСТЬ — scripts/audit_pytest_dedupe.py, у него есть флаг --check, и он задокументирован как «Static audit reports (review-only)». То есть проверка реализована и не блокирует НИЧЕГО — тот же узор, что у memory lint. Вторая половина: tests/ входит в _FILESIZE_EXEMPT_DIRS (gate_filesize.py), поэтому тесты суть единственное место в дереве вообще без размерной дисциплины. Задача: сделать детектор гейтом с ХРАПОВИКОМ — не хуже, чем сейчас, а известные 683 структурно одинаковых теста в 294 группах фиксируются как долг с числом, а не блокируют работу разом. Освобождение tests/ от гейта размера пересмотреть отдельным решением: оно могло быть верным, когда тестов было мало. НЕГАТИВНОЕ ограничение: гейт не имеет права поощрять удаление тестов ради зелёного счётчика — предмет проверки есть РАЗЛИЧИМОСТЬ, а не количество, и это ловится вместе с p9-a-test-never-observed-red-is-not-evidence.

## Acceptance Criteria

## Plan

## Rollback

## Journal
