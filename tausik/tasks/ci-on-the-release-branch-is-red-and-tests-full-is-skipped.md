---
slug: ci-on-the-release-branch-is-red-and-tests-full-is-skipped
title: "CI релизной ветки красен 17 часов, а медленная полоса не исполняется вовсе"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
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

НАЙДЕНО ЗАМЕРОМ в смене #277 при работе над the-lane-that-catches-slow-tests-has-no-reader. Релиз 1.10 нельзя выпускать над этим.

ЗАМЕР: из десяти последних пайплайнов на v1-10 ДЕВЯТЬ FAILED — #8473, #8466, #8464, #8463, #8462, #8460, #8458, #8457, #8456, то есть непрерывно последние 17 часов и каждый пуш смены #277. Job `tests` в #8473 (sha e5fdfcbe): 9 failed, 11118 passed, 198 skipped.

ВТОРАЯ ПОЛОВИНА ХУЖЕ ПЕРВОЙ: job `tests-full` в том же пайплайне — SKIPPED. Медленная полоса, единственная, что доходит до `-m ''`, на релизной ветке НЕ ИСПОЛНЯЕТСЯ. Именно поэтому два теста, сломанные детерминированно, прожили релиз: их не поймал ни локальный прогон (addopts отбрасывает), ни CI (стадия пропущена). Почему пропущена — первое, что надо выяснить: стадия test-full может не запускаться из-за того, что предыдущая стадия красная.

ЭТО И ЕСТЬ ГЛАВНАЯ ГИПОТЕЗА, И ОНА ПРОВЕРЯЕМА: стадии в GitLab последовательны, красная `test` не пускает `test-full`. Тогда девять красных тестов блокируют не только себя, но и всю медленную полосу — один дефект прячет целый класс.

СЕМЬ ИМЁН ИЗ ДЕВЯТИ ОТКАЗОВ:
  tests/test_config_trust.py::TestPaths::test_user_path_defaults_under_home
  tests/test_doctor_auto_verify_hint.py::test_a_recorded_reason_turns_the_warning_into_a_report
  tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks
  tests/test_mcp_list_cache_hint.py::test_a_scope_change_mid_session_is_never_served_from_a_cache
  tests/test_search_output_size.py (два теста)
  tests/test_usage_once_per_message.py::test_the_replay_transcript_of_session_263_meters_the_deduplicated_sum

РАЗДЕЛИТЬ ПО ПРИРОДЕ, а не чинить подряд. Часть — СРЕДА: test_user_path_defaults_under_home сравнивает путь под /home/gitlab-runner и падает на Linux, а локально на Windows зелен; такие тесты либо пишутся переносимо, либо объявляют платформу. Часть — НАСТОЯЩИЙ ДОЛГ: ruff_format.legacy_unformatted держит 9 файлов, которые с момента заморозки отформатированы (scripts/gate_outcome.py, scripts/symbol_index.py, tests/test_gate_test_resolver_crosscutting.py, tests/test_graph_is_framework_machinery.py, tests/test_memory_lint.py, tests/test_migration_v43_model_mismatch.py, tests/test_session_metrics_parse.py, tests/test_shell_roots.py, tests/test_wrapper_flags_hide_the_wrapped_command.py) — по решению #386 они должны были уйти из перечня той же правкой.

ПОЧЕМУ ЛОКАЛЬНО НЕ ВИДНО И ЭТО НЕ БАГ ПОЛИТИКИ: проверка соразмерна правке, scoped verify гоняет файлы задачи. Политика верная, но следствие — полнотелые проверки живут ТОЛЬКО в CI, и его невидимость обнуляет их все.

РЕЦЕПТ ЧТЕНИЯ: `glab ci list -r v1-10 -P 10`, `glab ci get -p <id>`, `glab ci trace tests -p <id>`. glab установлен локально.

## Acceptance Criteria

## Plan

## Rollback

## Journal
