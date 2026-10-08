---
slug: two-slow-lane-tests-are-red-and-unseen
title: "Две slow-ленты красные, и их никто не видит: -m slow не входит в обычный прогон"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_mcp_integration.py"
  - "tests/test_tausik_cli.py"
  - "tests/conftest.py"
  - "changelog.d/two-slow-lane-tests-are-red-and-unseen.md"
scope_paths:
  - "tests/"
  - "scripts/"
  - "changelog.d/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:02:10Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
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

- 2026-09-29T20:38:32Z [implementation] — Root causes by git bisect, NOT pre-#278: (1) test_server_rejects_missing_project red since a4219bdf (2026-09-29, gmcp-server-multitenant, #278): --project became optional by decision #403, expectation stale. Parent green. (2) test_full_lifecycle red since 2d192942 (2026-09-29, cheap-gates-first, #278): verify trigger added to 5 static gates, so gate_verify_first no longer takes the 'no verify gates' early return and QG-2 applies to every project; fixture disabled verify gates by name and broke on each new one. The handoff claim 'predates #278, checked by stash' was wrong: stash cannot see committed work.
- 2026-09-29T20:47:46Z [implementation] — Fixed both: MCP test replaced by end-to-end check of the per-request contract; CLI lifecycle closes via --relevant-files --verify, asserts fileless close refused, fixture no longer disables filesize. -m slow lane: 142 passed. Default lane: 10 failed, 9 of them introduced by 214cb678 (adhd task, mine in #278) + answer_budget ratchet. AC-2 finding: under xdist the summary prints no 'deselected' count at all.
- 2026-09-29T21:07:25Z [implementation] — State: AC-1 ✓ AC-3 ✓ AC-4 ✓ (bisect: a4219bdf, 2d192942). AC-2 ✓ tests/conftest.py prints 'N deselected (not run)' under xdist (seen: 142 deselected). AC-5: -m slow 142 passed standalone; default lane red ONLY on test_answer_budget_ratchet (p90 of answers) — not closing past the ratchet.
- 2026-09-29T22:01:54Z [implementation] — AC-1: ✓ tests/test_mcp_integration.py::TestMCPServerStartup::test_server_without_project_still_answers_the_host (withdrawn contract replaced, a4219bdf); tests/test_tausik_cli.py::TestTaskCLI::test_full_lifecycle (QG-2 applies to every project since 2d192942). AC-2 Negative: ✓ tests/conftest.py prints '<N> deselected (not run)' under xdist; seen '143 deselected (not run) -- markexpr not slow'. AC-3 Negative: ✓ neither was environmental; both are intentional behaviour changes, expectation rewritten to the new contract with a negative assert, not loosened. AC-4: ✓ git bisect: a4219bdf and 2d192942, both session #278. AC-5: ✓ full lane 12573 passed (+1 CLAUDE.md pin fixed), -m slow 143 passed.
