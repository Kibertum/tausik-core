---
slug: session-update-check-collides-with-the-zero-phone-home-claim
title: "The update check from GitHub: a consumer learns of the next version at the start of the next session — and the README's outbound-calls sentence tells the truth"
status: done
epic: release-110-deferred-from-19
story: release110-the-update-reaches-the-user
complexity: medium
role: developer
stack: null
tier: substantial
call_budget: 80
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/update_check.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/status_view.py"
  - "scripts/hooks/session_start.py"
  - "tests/test_update_check.py"
scope_paths:
  - "scripts/update_check.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/status_view.py"
  - "scripts/hooks/session_start.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - README.md
  - README.ru.md
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:18:07Z"
resolution: null
resolution_reason: null
---

## Goal

Owner, session #264, after learning that no update notifier exists (none shipped in 1.8 either — the only outbound call in the product is push-ok reading the CI lane): the update check is MANDATORY in 1.10 and its source is GitHub. A consumer on 1.8 learns that 1.9 exists no later than the start of their next session — today they learn only by visiting github.com. Constraints that survive: README ×2 promise "0 phone-home calls / 0 обращений наружу", so the promise is restated to the truth of the mechanism (what goes out, to whom, how often, how to turn it off) in the same change — a check that the README denies is worse than no check. Source candidates, each measured before the pick: (a) `git ls-remote --tags https://github.com/Kibertum/tausik-core.git` — anonymous, no API quota, ~1 round trip, sends nothing but the URL; (b) GitHub REST releases/latest — anonymous 60 req/h, returns the release name and notes URL; (c) the consumer's own submodule remote (`.tausik-lib`), which may point at GitLab. The message names the CURRENT and the AVAILABLE version and links the release; cached beside the DB, at most one request per day across sessions; no network / no GitHub / garbage answer → the session starts within the hard timeout, the failure is logged, never faked as "up to date". Sends nothing about the project — no name, no path, no schema version — proven by intercepting the outgoing request in a test.

## Acceptance Criteria

AC-1: an owner decision records the mechanism: GitHub is the source (decision of session #264), which of (a)/(b)/(c) was picked and why, with the measured latency and what leaves the machine; and whether it is on by default with an opt-out (`updates.check = false` in .tausik/config.json) or opt-in — the README ×2 sentence about outbound calls is rewritten in the same change to state exactly that (a test holds README and config default in agreement). AC-2: at session start a consumer whose __version__ is older than the newest published tag sees one line naming both versions and the release URL; the same or a newer version prints nothing. AC-3: the answer is cached beside the DB with a timestamp; a second session within 24 h makes no request (asserted by counting requests through the intercept). AC-4 (negative): with the network unreachable, a 5xx, or a non-version answer, session start finishes within the hard timeout (≤ 2 s budgeted for the check), prints nothing about updates, logs the reason, and the cache is not poisoned. AC-5 (negative): the outgoing request carries no project name, path, DB schema version or user identifier — asserted on the intercepted request, not by reading the code. AC-6: `tausik doctor` shows the check's state (on/off, last checked, last answer) so a silent failure is visible on demand.

## Plan

## Rollback

git revert коммита; проверка выключается ключом конфига и по умолчанию выключена

## Journal

- 2026-09-23T19:15:19Z [implementation] — Сделано: scripts/update_check.py (build_request, fetch_latest, refresh с суточным кэшем .tausik/update_check.json, notice, doctor_line, cmd_update_check); команда tausik update-check [--now]; SessionStart запускает её отсоединённо (_spawn_update_check); status_view печатает строку из кэша; строка doctor 'Update check'; README en/ru: '1 outbound call' вместо '0 phone-home'; docs configuration/doctor/cli en+ru. Живой прогон: 'on, last checked 2026-09-23T19:14:28Z; latest 1.9.0'. AC verified: AC-1 ✓ частично: решение #383 записывает источник (GitHub REST, вариант b), замеры REST ~1,1 с / ls-remote ~1,4 с, что уходит, умолчание (включено, opt-out updates.check=false); принято агентом по #372 и ждёт подтверждения владельца — формально не 'решение владельца' AC-2 ✓ test_a_newer_release_is_announced_with_both_versions_and_the_link; строка приходит в контекст через status из кэша, т.е. в той же или следующей сессии после выпуска — запрос не стоит на пути SessionStart AC-3 ✓ test_at_most_one_request_a_day (счёт запросов через перехват) AC-4 ✓ НЕГАТИВНЫЙ test_no_network_keeps_the_last_answer_and_never_claims_up_to_date, test_a_garbage_answer_is_an_error_not_a_version, test_session_start_only_spawns_detached_and_never_raises AC-5 ✓ НЕГАТИВНЫЙ test_the_request_carries_nothing_about_the_project (на перехваченном запросе) AC-6 ✓ doctor 'Update check' on/off, время, ответ; test_it_can_be_switched_off. README: test_the_readme_says_what_leaves_the_machine. 12 тестов зелёные.
- 2026-09-23T19:18:03Z [implementation] — AC-3: ✓ tests/test_update_check.py::test_at_most_one_request_a_day
- 2026-09-23T19:18:03Z [implementation] — AC-4: ✓ tests/test_update_check.py::test_no_network_keeps_the_last_answer_and_never_claims_up_to_date
- 2026-09-23T19:18:03Z [implementation] — AC-5: ✓ tests/test_update_check.py::test_the_request_carries_nothing_about_the_project
