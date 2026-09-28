---
slug: two-absoluteness-predicates-must-become-one
title: "Два предиката абсолютности пути живут в двух модулях и обязаны стать одним"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: backend
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_origin.py"
  - "tests/test_knowledge_origin.py"
scope_paths:
  - "scripts/path_glob.py"
  - "scripts/knowledge_origin.py"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:15:54Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#86"
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

Один предикат о форме пути на весь репозиторий: path_glob.is_absolute и knowledge_origin._ABSOLUTE_RE перестают быть двумя копиями одной идеи.

## Acceptance Criteria

1. knowledge_origin decides absoluteness with path_glob.is_absolute; its own _ABSOLUTE_RE is gone and no second copy of the rule remains in scripts/. 2. NEGATIVE: a table test pins that the unified predicate answers exactly as the removed regex did on every spelling both modules cared about — POSIX root, backslash root, UNC in both slashes, drive with either slash — and that the free-text values the migration must NOT touch (team/backend, C:x drive-relative, name@deadbeef, empty) stay non-absolute. 3. NEGATIVE: knowledge_origin's migration and relative_source_file keep their behaviour (existing tests green).

## Plan

## Rollback

git revert коммита

## Journal

- 2026-09-23T23:15:24Z [implementation] — AC-1: ✓ tests/test_knowledge_origin.py::test_no_second_copy_of_the_rule_lives_in_knowledge_origin — knowledge_origin imports path_glob.is_absolute and uses it at both sites (the origin migration, relative_source_file); _ABSOLUTE_RE is gone; grep over scripts/ finds no other absoluteness regex.
- 2026-09-23T23:15:24Z [implementation] — AC-2: ✓ tests/test_knowledge_origin.py::test_the_one_predicate_answers_as_the_removed_regex_did — negative, 11 spellings (POSIX, backslash root, UNC both slashes, drive either slash, C:x, team/backend, name@deadbeef, relative, empty) answer identically to the removed regex, which the test keeps as the historical reference.
- 2026-09-23T23:15:25Z [implementation] — AC-3: ✓ tests/test_knowledge_origin.py::TestTheRedactionReadsTheSpellingNotTheHost::test_the_predicate_reads_the_spelling_on_every_platform — negative: existing migration/redaction tests green, 51 passed.
- 2026-09-23T23:15:32Z [implementation] — AC-3: ✓ tests/test_knowledge_origin.py::TestAbsolutenessIsSpellingNotInterpreterOpinion::test_the_predicate_reads_the_spelling_on_every_platform — CORRECTION of the class name in the previous AC-3 line (written from memory, wrong); negative: the whole module green, 51 passed.
- 2026-09-26T18:44:30Z [done] — EVIDENCE-UNPROVEN: tests/test_knowledge_origin.py::TestTheRedactionReadsTheSpellingNotTheHost::test_the_predicate_reads_the_spelling_on_every_platform — git never carried this path or member under any directory
