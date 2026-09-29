---
slug: two-slow-lane-tests-are-red-and-unseen
title: "Две slow-ленты красные, и их никто не видит: -m slow не входит в обычный прогон"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "tests/"
  - "scripts/"
  - "changelog.d/"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Замер смены #278: pytest -q исключает -m slow (addopts = -m 'not slow'), поэтому полный прогон, которым закрываются задачи, эти тесты НЕ гоняет. Прогон -m slow даёт два красных: tests/test_mcp_integration.py::TestMCPServerStartup::test_server_rejects_missing_project и tests/test_tausik_cli.py::TestTaskCLI::test_full_lifecycle. Оба воспроизводятся с убранными правками смены, то есть предшествуют ей — и неизвестно, как давно. Зелёная лента при этом рапортует 12 500+ passed, и читатель принимает её за полную.

## Acceptance Criteria

AC-1 Причина каждого из двух падений названа и исправлена, либо объявлена намеренной с датой пересмотра.
AC-2 НЕГАТИВНЫЙ: отчёт о прогоне называет число DESELECTED, а не только passed — иначе 12 500 passed скрывает выключенную ленту (конвенция #776).
AC-3 НЕГАТИВНЫЙ: тест, красневший из-за окружения, а не из-за кода, объявляется таким явно и не чинится подгонкой ожидания.
AC-4 Известно, с какого коммита каждый из двух красный; если неизвестно — это сказано, а не угадано.
AC-5 Полная лента и -m slow обе зелёные.

## Plan

## Rollback

git revert

## Journal
