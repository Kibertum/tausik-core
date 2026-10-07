---
slug: fix-pooled-verify-recovery-ss4-widening-inputs
title: "Fix pooled-verify recovery: SS4 widening, inputs digest, member recording"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: r1112-cohort-receipts-and-incremental-rerun
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_cohort.py"
  - "scripts/service_gates.py"
  - "scripts/verify_hierarchy.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v76.py"
  - "scripts/backend_migrations_postseed.py"
  - "docs/en/verification-cohort-contract.md"
  - "docs/ru/verification-cohort-contract.md"
  - "tests/test_verify_cohort.py"
  - "tests/test_migrations_v76_cohort_state.py"
  - "tests/test_schema_upgrade_parity.py"
  - "tests/test_cli_verify_guards.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/mcp_cli_parity.py"
  - "tausik/memory/kilo-posle-obnovleniya-otvergaet-tools-stroku-claude-stilya.md"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T16:39:12Z"
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

Make the pooled-verify RECOVERY path real: contract SS4 widening is unimplemented (refusal loop permanently bricks a membership after post-green drift), production records inputs_digest='unavailable' (no files_hash in the report), the pooled run is recorded under members[0] only making the SPEC SS5 task-done clause dead text, and identity binds placeholder strings instead of content hashes.

## Acceptance Criteria

AC-1: after a green cohort + any named invalidator, the next pooled run EXECUTES the full lane and records a new cohort row (contract SS4 widening), instead of refusing forever; the output names the refused reuse. AC-2: verification_cohort_results.inputs_digest is a real digest in production (files_hash surfaced in the run_verify_for_task report or read from the recorded run row), never 'unavailable'. AC-3: SPEC SS5 'task done --verify-handle accepts either' either works for pooled handles on every member or the clause is removed from the SPEC and CHANGELOG. AC-4: decision recorded: per-test provenance granularity either wired or the v75 schema/AC wording narrowed; identity placeholders 'declared-at-run'/'selection-evidence-of-run' either fed real values or dropped from SPEC SS1. AC-5 negative: a red cohort with drifted identity still proceeds (regression test for the existing green-only rule).

## Plan

## Rollback

## Journal

- 2026-10-07T14:24:43Z [implementation] — HANDOFF STATE (session #297 end). CODE ~90% IN WORKING TREE, NOT COMMITTED, on branch v1-11-3 (created from v1-11-2; commits on top of 71b313a6: 6 Track A/C + A=296-leftovers + B=de2ca844 close-path fix; nothing pushed). DONE THIS SESSION: AC-1 SS4 widening EXECUTES (verify_cohort.py: prior marked invalidated, 'Widened to the full lane: reuse of prior green cohort #N refused (<reason>)' in out['widened'], rendered by cohort_summary+hierarchy_summary; missing-evidence:<slug> stays a hard refusal); AC-2 files_hash surfaced in run_verify_for_task report (service_gates.py reads verification_runs row by details.run_id OR cache_hit id) and record_results stamps report.files_hash or content-digest, never 'unavailable'; AC-4 content_hashes = real content-only digest (_content_digest: sorted path+full-content sha256, NO mtime - close-time recompute must survive checkout), selected_tests DROPPED from identity inputs, per-test provenance = declared non-goal; AC-3 SPEC SS5 'task done accepts either' REMOVED from docs/en+ru/verification-cohort-contract.md (pooled handle redeems via story/epic done ONLY; single-use handle on N members is a trap); RU mirror also fixed 21.4x -> 34x/4.7x. Tests rewritten: GREEN_REPORT carries files_hash, NOHASH_REPORT pins fallback, TestProvenanceDigest x4, widening execute-not-refuse + prior invalidated + new row, AC-5 red-prior-drift no widened, missing-evidence pin. STOPPING POINT: pytest cohort+hierarchy 43 passed 1 FAILED - sqlite3.IntegrityError CHECK constraint failed: state IN ('open','green','red') at verify_cohort.py:233 (_set_state 'invalidated'); DDL lives in backend_schema.py:325 and backend_migrations_v75.py:14 (CHECK inside CREATE TABLE). NEXT STEPS IN ORDER: (1) add 'invalidated' to the state CHECK in backend_schema.py AND a new backend_migrations_v76.py table-rebuild migration (SQLite cannot ALTER a CHECK - CREATE new/INSERT SELECT/DROP/RENAME pattern; register in backend_migrations.py; DDL-parity pins will check), run pytest tests/test_verify_cohort.py tests/test_verify_hierarchy.py + backend DDL tests to green; (2) declare relevant_files (scripts/verify_cohort.py scripts/service_gates.py scripts/verify_hierarchy.py scripts/backend_schema.py scripts/backend_migrations_v76.py scripts/backend_migrations.py docs/en/verification-cohort-contract.md docs/ru/verification-cohort-contract.md tests/test_verify_cohort.py); (3) python bootstrap/bootstrap.py --ide all (+--check zero drift); (4) .tausik/tausik verify --task fix-pooled-verify-recovery-ss4-widening-inputs (REAL gates), AC evidence per AC-1..AC-5, Root cause line (defect task!), tausik_decide for per-test provenance non-goal + selected_tests removal, task done --ac-verified --verify-handle; (5) commit. THEN: fix-1-11-3-published-claims-spec-code-parity-21 (EN surfaces of 21.4x: CHANGELOG.md line ~42 '21.4x fewer executions' -> 34x, SPEC EN Rollout proof '21.4x' -> 34x/4.7x, README cells if any; RU already done; REPORT THE RESTATEMENT TO OWNER - his standing order; mcp.md rows for tausik_verify_cohort/tausik_verify_hierarchy; cli-quality verify --tasks/--story/--epic flags; cli-tasks story/epic done --verify-handle; configuration.md memory_tail_by_relevance; stale 152/62KB; verify_baseline.py per-slug dup windows + sizes 3-4 dropped); release archaeology (epic release-1-11-2 mislabeled-done under pooled-verification title - retitle to actual content, create cut-release-tausik-1-11-3); Track B 5 tasks (blocked-is-a-status-without-a-question-to-unblock-it; nothing-scans-the-installed-harness-state; four-ide-registries medium; ratchet-for-mcp-cli-surface-parity complex; agent-friction complex); r111-economy-hardening-acceptance (blocked, MEASUREMENTS ONLY: AC-1 byte stdio probe vs frozen 63333B per prefix-original-journal-20261002.json, AC-2 frozen replays 3 cycles, AC-3 median rounds >=3 natural accepted tasks threshold <=40 baseline 89, AC-5 no synthetics no baseline reconstruction; close on measurements); release 1.11.3 (scripts/tausik_version.py, [Unreleased]->[1.11.3]+date BOTH changelogs, gen_doc_constants --write + README cells, full release verify lane WITH denominators naming deselected, commit, STOP - publication only on owner word). HARD RULES unchanged: no push without owner word; publication only after explicit approval; gates bite by design, never disable; MCP-first, CLI fallback on drift; bootstrap redeploy after scripts/ changes.
- 2026-10-07T16:13:18Z [implementation] — HANDOFF STATE (session #298 end). v76 MIGRATION DONE, NOT COMMITTED, NOT CLOSED. Working tree on v1-11-3 now ALSO carries: scripts/backend_migrations_v76.py (NEW: empty MIGRATION_V76 marker + guarded post-step maybe_widen_cohort_state_v76, CREATE new/INSERT SELECT/DROP/RENAME, frozen DDL snapshot conv #646); scripts/backend_schema.py (SCHEMA_VERSION 75->76, CHECK state += 'invalidated' + comment); scripts/backend_migrations.py (import + registry 76); scripts/backend_migrations_postseed.py (call under current_version>=76); tests/test_schema_upgrade_parity.py ('verification_cohorts' added to rebuilt-DDL parametrize); tests/test_migrations_v76_cohort_state.py (NEW, 8 tests on the v49 pattern: registered / invalidated accepted after real chain / closed-list param negative / defect pinned pre-v76 / rows survive column-for-column / results CASCADE survives / fresh-vs-migrated state CHECK converge / guard no-op on fresh); tests/test_cli_verify_guards.py (_FakeBackend += _q1 returning dict|None like project_backend — service_gates.py working-tree code reads files_hash via be._q1, the fake lacked it). VERIFIED: 234 passed (cohort+hierarchy+migrations+v49+v76+schema-upgrade-parity+index-parity+fresh-install+ddl-fixture-parity). NOT YET RE-RUN: tests/test_cli_verify_guards.py after the _q1 fake fix (was 17 failed / 66 passed across the adjacent lane, all one cause). NEXT IN ORDER: (1) pytest tests/test_cli_verify_guards.py -q -> green; (2) task_update relevant_files = scripts/verify_cohort.py scripts/service_gates.py scripts/verify_hierarchy.py scripts/backend_schema.py scripts/backend_migrations.py scripts/backend_migrations_v76.py scripts/backend_migrations_postseed.py docs/en/verification-cohort-contract.md docs/ru/verification-cohort-contract.md tests/test_verify_cohort.py tests/test_migrations_v76_cohort_state.py tests/test_schema_upgrade_parity.py tests/test_cli_verify_guards.py; (3) python bootstrap/bootstrap.py --ide all + --check zero drift; (4) .tausik/tausik verify --task <slug> (LIVE project DB is v75 -> migrates to v76, writes .bak.v75); (5) task log AC-evidence AC-1..AC-5 + Root cause (defect task), task done --ac-verified --verify-handle via CLI; (6) tausik_decide: per-test provenance = declared non-goal + selected_tests dropped from identity inputs; (7) commit. THEN the queue from the owner briefing of 2026-10-07: fix-1-11-3-published-claims-spec-code-parity-21 (EN 21.4x->34x/4.7x surfaces + REPORT RESTATEMENT TO OWNER standing order; mcp.md verify_cohort/verify_hierarchy rows; cli-quality verify --tasks/--story/--epic; cli-tasks story/epic done --verify-handle; configuration.md memory_tail_by_relevance; stale 152/62KB; verify_baseline.py per-slug dup windows + sizes 3-4 dropped); release archaeology (retitle epic release-1-11-2, create cut-release-tausik-1-11-3); Track B 5 tasks; r111-economy-hardening-acceptance measurements only; release 1.11.3 (version, BOTH changelogs, gen_doc_constants --write, full verify lane WITH denominators, commit, STOP - publication only on owner word).
- 2026-10-07T16:38:38Z [implementation] — AC EVIDENCE (session #299, verify run #3610 PASS: 2815 passed / 19 skipped / 1 deselected, scoped 123/668 files). AC-1 VERIFIED: SS4 widening EXECUTES — verify_cohort.py marks the prior green cohort 'invalidated' and records out['widened']='Widened to the full lane: reuse of prior green cohort #N refused (<reason>)', rendered by cohort_summary+hierarchy_summary; a new cohort row is recorded; tests/test_verify_cohort.py pins execute-not-refuse + prior-invalidated + new-row; missing-evidence:<slug> stays a hard refusal (pinned). AC-2 VERIFIED: inputs_digest never 'unavailable' in production — service_gates.py surfaces files_hash by reading the verification_runs row (details.run_id OR cache_hit id via be._q1); record_results stamps report.files_hash or the content digest; tests pin GREEN_REPORT carries files_hash + NOHASH_REPORT fallback. AC-3 VERIFIED: SPEC SS5 'task done --verify-handle accepts either' REMOVED from docs/en+ru/verification-cohort-contract.md — pooled receipts redeem via story/epic done ONLY (single-use handle on N members is a trap); CHANGELOG EN+RU record the removal. AC-4 VERIFIED: content_hashes = real content-only digest (_content_digest: sorted path+full-content sha256, NO mtime — close-time recompute survives checkout; TestProvenanceDigest x4); selected_tests DROPPED from identity inputs; per-test provenance = declared non-goal (decision recorded via tausik_decide this session). AC-5 NEGATIVE VERIFIED: red cohort with drifted identity still proceeds — regression test red-prior-drift-no-widened pins the green-only rule. v76 MIGRATION: SCHEMA_VERSION 76, CHECK state += 'invalidated' via guarded rebuild maybe_widen_cohort_state_v76 (CREATE new/INSERT SELECT/DROP/RENAME), registered in backend_migrations.py + backend_migrations_postseed.py, DDL-parity pin added; tests/test_migrations_v76_cohort_state.py 11 passed (registered/accepted/closed-list-negative/defect-pinned-pre-v76/column-survival/CASCADE/fresh-vs-migrated-converge/guard-no-op); LIVE project DB migrated v75->v76 (.bak.v75 written 19:18 local). ROOT CAUSE (defect of r1112-cohort-receipts-and-incremental-rerun): the v75 CHECK admitted only ('open','green','red') while the widening's own UPDATE sets 'invalidated' — the recovery path was UNIMPLEMENTED: the code refused reuse forever instead of widening, and the first widening attempt died as sqlite3.IntegrityError; additionally the pooled report carried no files_hash so inputs_digest recorded 'unavailable', identity bound placeholder strings, and the pooled run was recorded under members[0] only — all fixed above.
- 2026-10-07T16:39:22Z [done] — Root cause (logic-error): the v75 CHECK admitted only ('open','green','red') while the SS4 widening's UPDATE sets 'invalidated', and the widening branch itself was unimplemented — the recovery path refused reuse forever, and its first real execution died as sqlite3.IntegrityError. Prevention: a new state in a CHECK constraint requires a guarded table-rebuild migration (conv #445) plus a shape-distinguished registered-test; contract clauses that name a recovery behavior need their execute-path test before the refusal tests. Domain: live project DB migrated v75->v76 during verify #3609/.bak.v75 preserved; a real green cohort followed by an invalidator now executes the full lane and names the refused reuse — observed outside unit tests on this repo's own verification history.
