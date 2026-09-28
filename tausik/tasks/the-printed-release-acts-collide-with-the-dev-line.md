---
slug: the-printed-release-acts-collide-with-the-dev-line
title: "The printed release acts collide with the dev-line tag: GitHub's tag is a refspec push of the snapshot"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_publish.py"
  - "tests/test_publish_cli.py"
  - "docs/en/publishing.md"
  - "docs/ru/publishing.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T14:45:29Z"
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

The procedure in docs/{en,ru}/publishing.md and the acts printed by 'tausik publish snapshot' must be executable in the order written: the release tag on the development line (GitLab) names the release commit, the snapshot is built --from that tag, and GitHub receives the same tag NAME on the snapshot commit through a refspec push — without a local tag of the same name being created twice. Today the docs say '--from v1.9.0' and then 'git tag -a v1.9.0 <snapshot>' — the second fails with 'tag already exists' (measured: local v1.8.0 = 3866702f on the history, github v1.8.0 = 623fb4ee snapshot; the same name on two objects is the model, but nothing says how it is reached).

## Acceptance Criteria

AC-1: scripts/project_cli_publish.py prints, after a successful snapshot, the tag act as 'git push github <sha>:refs/tags/v<version>' and never 'git tag -a v<version> <sha>'; a test reads the printed block. AC-2 (negative, the finding reproduced): in a temporary repository with tag v1.0.0 on the source line, 'git tag -a v1.0.0 <snapshot>' fails with 'already exists' — the test asserts the failure, then runs the PRINTED acts against a bare 'github' remote and asserts ls-remote shows refs/heads/main and refs/tags/v1.0.0 at the snapshot commit while the local v1.0.0 still names the source commit. AC-3: docs/en/publishing.md and docs/ru/publishing.md step 3 state the two-object reality by name (the name on the development line names the release commit; on GitHub it names the snapshot; the trees agree under the filter, and publish verify is the proof) and give the refspec push; tests/test_docs_links_resolve.py and doc scanners stay green. AC-4: tests/test_publish_cli.py passes, dedupe ratchet stays at 290/686, verify signed.

## Plan

## Rollback

## Journal

- 2026-09-13T14:31:48Z [implementation] — Finding measured: local tag v1.8.0 -> 3866702f (history, on origin/main); github v1.8.0 -> annotated 36f3a101 -> 623fb4ee (snapshot). Docs step 2 says --from v1.9.0, step 3 says git tag -a v1.9.0 <snapshot> — the second cannot succeed after the first. Fix: GitHub's tag is a refspec push of the snapshot commit; the local name stays on the history.
- 2026-09-13T14:35:22Z [implementation] — Fix in: project_cli_publish prints 'git push github <sha>:refs/tags/<tag>' with the tag name read from --from when it is a tag (placeholder v<version> otherwise), and never 'git tag -a'. Tests: negative reproduction (second local tag of the same name refused by git: 'already exists'), the printed acts executed against a bare github remote land main and the tag on the snapshot while the local name stays on the history, placeholder case. Docs EN/RU step 3 and 'the publication step added in 1.9' restated: one name, two objects, one filtered tree; published_tags.json updated on the dev line right after the push, the snapshot's copy one release behind by construction. 231 affected tests pass; ruff clean.
- 2026-09-13T14:44:07Z [implementation] — Review (tausik-reviewer): 0 critical/high, 3 medium, 3 low — all applied: _tag_named_by resolves --from <sha>/branch through git tag --points-at (one tag = its name; two = placeholder, not a guess); the LIGHTWEIGHT trade-off stated in the banner and in docs EN/RU step 3 (release notes = CHANGELOG + GitHub Release; published_tags.json records the commit either way, confirmed against publication_scope.remote_tag_map peel fallback); test extraction guarded (_printed_acts asserts the banner and len==2, never a vacuous empty list); verbless sentence fixed EN/RU. Reviewer confirmed: consumer clone has no remote 'github' so the promise test skips with reason; refs/tags/<name> resolution order matches _tag_named_by. 218 tests in the affected files pass, ruff clean, bootstrap redeployed.
- 2026-09-13T14:44:37Z [implementation] — AC-1 ✓ scripts/project_cli_publish.py prints `git push github <sha>:refs/tags/<tag>` (tag read from --from: the name itself, or the single tag pointing at the resolved commit; placeholder v<version> otherwise) and never `git tag -a`; tests/test_publish_cli.py::TestTheTagActIsARefspecPushNotASecondLocalTag::test_the_printed_acts_carry_the_tag_name_and_no_git_tag_a (asserts the refspec line, len(acts)==2, no act starts with git tag, LIGHTWEIGHT stated), ::test_a_sha_that_one_tag_points_at_carries_that_name, ::test_two_tags_on_the_commit_is_an_ambiguity_not_a_guess, ::test_a_source_that_is_not_a_tag_prints_a_placeholder. AC-2 ✓ (НЕГАТИВ) ::test_a_second_local_tag_of_the_same_name_is_what_git_refuses — after `--from v1.0.0` the old instruction `git tag -a v1.0.0 <snapshot>` exits non-zero with 'already exists'; ::test_the_printed_acts_executed_against_a_bare_remote_land_the_snapshot — the two PRINTED acts run verbatim against a bare 'github' remote: ls-remote refs/heads/main == snapshot, refs/tags/v1.0.0 == snapshot, local v1.0.0^{commit} == HEAD != snapshot. AC-3 ✓ docs/en/publishing.md and docs/ru/publishing.md step 3 (refspec push; one name, two objects, one filtered tree; LIGHTWEIGHT trade-off) and 'The publication step added in 1.9' (the two objects are the model from v1.9.0; published_tags.json updated on the dev line as the commit after the push; the snapshot's copy one release behind by construction; consumer clone skips the promise test — confirmed by reviewer against publication_scope.remote_tag_map); tests/test_docs_links_resolve.py green, gen_doc_constants --check OK, audit_stale_docs 'No stale docs detected'. AC-4 ✓ tests/test_publish_cli.py 16 passed; tests/test_gate_test_dedupe.py 7 passed (baseline 290/686 unchanged); verify run #2611 signed (key 103a83a212851018). Review: tausik-reviewer 0 critical/high, 3 medium + 3 low, all applied. Push/tag/release not executed. Domain: the release procedure is executable in the order written — the owner's tag act cannot fail on 'already exists' because it is a refspec push, and the model of one name on two objects is stated, not stumbled into.
