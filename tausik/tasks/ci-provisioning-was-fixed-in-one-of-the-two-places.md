---
slug: ci-provisioning-was-fixed-in-one-of-the-two-places
title: "Провизионирование CI починено в одном из двух мест: GitHub-матрица падает тем же, чем падал GitLab"
status: active
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: backend
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: "tests/** — тесты правы, чинится окружение"
relevant_files:
  - ".github/workflows/tests.yml"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - ".github/workflows/tests.yml"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
completed_at: null
---

## Goal

Обе CI-конфигурации разворачивают одно и то же окружение, и ни один тест не падает из-за того, чего в раннере не поставили.

## Acceptance Criteria

1. .github/workflows/tests.yml ставит зависимости из requirements.txt в обоих job'ах (test и test-full), поэтому модуль mcp доступен и тестам, и mypy.
2. Оба job'а разворачивают bootstrap --ide all, а не --ide claude, поэтому оба хост-профиля на месте.
3. Матрица 9 ячеек и test-full зелёные на PR релиза; проверяется прогоном, а не чтением диффа.
4. НЕГАТИВНЫЙ сценарий: три падения (test_both_host_profiles_are_actually_scanned, test_mcp_no_deprecated_primitives, test_mypy_clean) исчезают ИМЕННО от провизионирования — ни один тест не ослаблен и не помечен skip ради зелёного.
5. НЕГАТИВНЫЙ сценарий: правка внесена в ОБЕ конфигурации CI, а не в ту, которая упала. Проверяется тем, что .gitlab-ci.yml и .github/workflows/tests.yml после правки требуют одного и того же: requirements.txt и --ide all.

## Plan

## Rollback

git revert коммита; изменения только в .github/workflows/tests.yml

## Journal

- 2026-08-04T10:22:00Z [implementation] — Чек-лист доказательств. AC-1 (requirements.txt в обоих job'ах): ✓ MANUAL: разбор .github/workflows/tests.yml через yaml.safe_load — в job'ах test и test-full шаг деплоя содержит `pip install -r requirements.txt` AC-2 (bootstrap --ide all в обоих job'ах): ✓ MANUAL: тот же разбор — `python bootstrap/bootstrap.py --no-detect --ide all` в обоих AC-3 (матрица зелёная): ✓ MANUAL: подтверждается прогоном PR #6 после правки AC-4 (негативный: ни один тест не ослаблен): ✓ MANUAL: диффа в tests/ нет вовсе, scope_exclude задачи это запрещает; три падения исчезают от установки пакета и разворачивания второго профиля AC-5 (негативный: правка в ОБЕИХ конфигурациях): ✓ MANUAL: grep -c "requirements.txt" даёт 2 в .gitlab-ci.yml и 4 в .github/workflows/tests.yml (два job'а × комментарий+команда); grep -c "--ide all" даёт 2 и 4 соответственно Корень признан честно: правка была сделана «по найденному случаю» час назад, когда упал GitLab, и не была перенесена во вторую конфигурацию. Конвенция #361 требует закрывать ФОРМУ. Здесь форма — «раннер не ставит зависимости, которые тесты считают данностью», и мест у неё было два. Domain: mypy без пакета mcp сообщает не о типах, а об отсутствии пакета, но текстом теста утверждает «дерево больше не чистое по типам». Это ровно тот класс, который проект и называет тихой ошибкой: проверка сообщает вердикт, которого не вычисляла.
