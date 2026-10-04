---
slug: add-cli-version-flag-and-block-session-start-on-a
title: "Add CLI version flag and block session start on a newer TAUSIK release"
status: done
epic: release-1111-proportional-assurance
story: release1111-adaptive-assurance
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "CLI version output; update_check freshness/ordering contract; public CLI/MCP/session hook start gates; EN/RU privacy and update documentation; focused tests."
scope_exclude: "Do not add telemetry, send project/user/path/schema identity, remove updates.check opt-out, block on network/timeout/malformed unknown state, publish a release, commit or push."
relevant_files:
  - "scripts/project_parser.py"
  - "scripts/project_parser_errors.py"
  - "scripts/update_check.py"
  - "scripts/project_cli.py"
  - "scripts/hooks/session_start.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "tests/test_update_check.py"
  - "tests/test_session_open_handler.py"
  - "tests/test_session_host_binding.py"
  - README.md
  - README.ru.md
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles:
  - executable
assurance_impact: "{\"blast_radius\":\"broad\",\"data_change\":\"none\",\"governance_boundary\":true,\"level\":\"medium\",\"owner_escalation\":false,\"privileged\":false,\"reversibility\":\"reversible\",\"security_boundary\":false}"
depends_on: []
completed_at: "2026-10-04T09:32:08Z"
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

Expose the installed TAUSIK version and prevent a session from starting when the authoritative release source reports a newer compatible version, with a direct upgrade instruction.

## Acceptance Criteria

AC-1 `tausik --version` prints the installed release version and exits successfully without opening the database. AC-2 Every session-start attempt performs or consumes an explicitly fresh authoritative version check before opening work; when latest > installed it refuses to open/resume the session and names both versions plus the upgrade command. AC-3 Same/older latest versions allow start unchanged. AC-4 Negative: network failure, timeout, malformed responses and prerelease/version-order edge cases are explicit and tested; unknown is never reported as current. AC-5 Existing opt-out/privacy/config behavior is reconciled in EN/RU docs, and scoped tests plus canonical verify pass.

## Plan

[{"step": "Define fresh-check, opt-out, failure, prerelease and upgrade-message semantics against existing update_check.", "done": true}, {"step": "Add database-free --version and a shared session-start release guard across CLI, MCP compound/open and host hook paths.", "done": true}, {"step": "Add negative, privacy and ordering tests without network access and reconcile EN/RU/README/changelog claims.", "done": true}, {"step": "Run focused tests, dedupe audit, bootstrap, canonical verify; record full AC, Domain and Negative evidence and close QG-2.", "done": true}]

## Rollback

Revert the version parser/guard wiring and documentation together; the existing cache remains backward-compatible and session rows require no migration.

## Journal

- 2026-10-04T09:04:36Z [implementation] — QG-0 refinement: medium scope now names CLI/parser, update_check, public session entry points, privacy docs and tests; excludes telemetry, identity leakage, removal of opt-out, blocking on unknown network state, publishing, commit and push. Rollback is code/docs reversion with no schema migration.
- 2026-10-04T09:06:17Z [implementation] — Architecture premise: public session entry points perform a synchronous forced GitHub releases/latest check before opening or reusing a TAUSIK session. A proven newer stable/prerelease ordering blocks with installed/latest versions and the submodule upgrade command. Network, timeout or malformed answers allow start but return UNKNOWN, never current. updates.check=false remains a privacy opt-out: it sends no request, allows start with DISABLED/unknown status, and is documented as the explicit exception. Non-installed-layout ProjectService fixtures do not make outbound calls.
- 2026-10-04T09:14:30Z [implementation] — Implemented database-free --version and the shared fresh release guard across CLI, direct MCP, compound MCP and host SessionStart before session creation. Newer SemVer blocks with versions and upgrade command; same/older pass; network, timeout, malformed and opt-out are explicit unverified states.
- 2026-10-04T09:15:33Z [implementation] — Added offline behavioral coverage for SemVer numeric/prerelease/build ordering, database-free --version, forced freshness, same/older allow, newer refusal before rows across CLI/direct MCP/compound MCP, network and timeout unknown, malformed answers, opt-out no-request, and host-hook refusal context. Reconciled README, EN/RU configuration, CLI reference and changelogs. Ruff passed; focused suites passed: 51 release/session tests plus 105 hook/bootstrap/parser/MCP/doctor tests.
- 2026-10-04T09:25:21Z [implementation] — Verification: audit_pytest_dedupe.py reports 0 COPY groups, 282 PARALLEL groups and all 7829 test functions able to fail. Bootstrap redeployed all IDE mirrors. Canonical verify #3435 passed 8 applicable gates with 1438 passed, 16 skipped across 59/658 scoped test files and 34 direct subject tests; hadolint was not applicable to the Python scope. Signed handle 3435.238fcfa6071f7d531dbead8be71d92ff remains unredeemed pending mandatory different-model L3 review.
- 2026-10-04T09:28:55Z [implementation] — L3 review #53 requested changes: strict SemVer rejection for numeric core/prerelease leading zeros and empty build identifiers. Hardened the parser and added parametrized malformed authoritative tag tests; each must return explicit unknown and must not refuse session start.
- 2026-10-04T09:32:02Z [implementation] — AC-1: PASS — tests/test_update_check.py::test_version_flag_needs_no_project_or_database ran scripts/project.py --version outside a project, returned TAUSIK 1.11.0 with exit 0 and created no .tausik directory; the deployed .tausik/tausik --version also returned TAUSIK 1.11.0. AC-2: PASS — tests/test_update_check.py::test_every_enabled_start_check_is_forced_and_uses_the_short_timeout proves two start attempts make two authoritative requests with the two-second boundary; test_newer_release_blocks_cli_before_a_session_row_opens proves refusal before a row and checks installed/latest plus .tausik-lib upgrade command; tests/test_session_open_handler.py proves the same no-row refusal for direct and compound MCP; test_hook_surfaces_a_cli_release_refusal_as_a_work_block proves the host hook returns Do not begin project work. AC-3: PASS — test_same_or_older_release_allows_cli_session_start parametrizes exact installed and older 0.0.1 releases and observes an active session. AC-4: PASS — test_version_order_handles_numeric_prerelease_and_unknown covers numeric precedence, prereleases, build metadata and malformed SemVer; test_unknown_start_check_allows_work_but_never_claims_current covers offline, TimeoutError, nightly, leading-zero core, leading-zero numeric prerelease and empty build identifiers, all as status unknown with fresh=false and unverified warning; newer cases leave session_current None. AC-5: PASS — README.md, README.ru.md, docs/en/configuration.md, docs/ru/configuration.md, docs/en/cli-tasks.md, docs/ru/cli-tasks.md and both changelogs disclose per-start anonymous GET, two-second timeout, opt-out and unknown behavior. Ruff passed. audit_pytest_dedupe.py reported 0 COPY, 282 PARALLEL and 7829/7829 tests able to fail. Canonical verify #3436 passed 8 applicable gates with 1444 passed, 16 skipped over 59/658 scoped files and 34 direct subject tests; hadolint was not applicable. Different-model L3 review #54 approved with zero critical/high/warnings after review #53's malformed-SemVer HIGH was fixed. Domain: the shared release guard executes before session creation on public CLI, direct MCP, compound MCP and host SessionStart paths; the request contains only the fixed GitHub releases/latest endpoint and fixed User-Agent, while the installed version remains local. The daily update-check cache still serves status/doctor independently. Negative: updates.check=false calls no opener and remains explicitly unverified; network, timeout and malformed responses never claim current and do not block work; only a fresh successfully ordered newer SemVer blocks; non-installed-layout service fixtures make no outbound request. Rollback: revert these code/docs/tests to restore the detached daily check; there is no schema or data migration.
- 2026-10-04T09:32:02Z [implementation] — Completed dedupe audit, bootstrap redeploy, canonical verify #3436 and independent different-model L3 review #54; recorded full AC, Domain and Negative evidence and closed through QG-2.
- 2026-10-04T09:32:19Z [done] — AC-1: ✓ tests/test_update_check.py::test_version_flag_needs_no_project_or_database plus deployed .tausik/tausik --version returned TAUSIK 1.11.0 without a project DB. AC-2: ✓ forced-freshness, CLI no-row refusal, direct/compound MCP no-row refusal and host-hook blocker tests prove every public start checks before opening and names versions plus upgrade command. AC-3: ✓ test_same_or_older_release_allows_cli_session_start parametrized installed and 0.0.1 and opened the session. AC-4: ✓ ordering and unknown tests cover offline, timeout, nightly, leading-zero core/prerelease and empty build; all malformed/failure states are unverified unknown, not current or blockers. AC-5: ✓ EN/RU README, configuration, CLI reference and changelogs match; dedupe 0 COPY; verify #3436 passed 1444 with 16 skipped; L3 review #54 approved. Domain: shared guard precedes session creation on CLI, direct MCP, compound MCP and host hook; fixed GitHub endpoint leaks no project/user/path/schema/version. Negative: opt-out makes zero requests; unknown allows work; only a fresh ordered newer release blocks; no schema/data migration.
