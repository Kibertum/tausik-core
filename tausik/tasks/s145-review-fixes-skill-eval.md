---
slug: s145-review-fixes-skill-eval
title: "Review-фиксы #145: skill-gate dirname на ненормализованном пути (POSIX) + eval substring/top_k/typo-db"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: l26-skill-spec-conformance
scope: "scripts/skill_spec_conformance.py (gate path normalization); scripts/eval_memory_retrieval.py (_hit boundary match, top_k passthrough, db-exists check); tests/test_skill_spec_conformance.py + tests/test_eval_memory_retrieval.py; CHANGELOG if baseline number changes."
scope_exclude: null
relevant_files:
  - "scripts/skill_spec_conformance.py"
  - "scripts/eval_memory_retrieval.py"
  - "tests/test_skill_spec_conformance.py"
  - "tests/test_eval_memory_retrieval.py"
scope_paths:
  - "scripts/skill_spec_conformance.py"
  - "scripts/eval_memory_retrieval.py"
  - "tests/test_skill_spec_conformance.py"
  - "tests/test_eval_memory_retrieval.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T14:44:33Z"
---

## Goal

Адверсариальное ревью сессии #145 нашло: (HIGH) run_skill_conformance_gate нормализует разделители только для basename-проверки, но берёт os.path.dirname от НЕнормализованного пути — на POSIX (ubuntu/macos CI) posixpath.dirname('..\\SKILL.md')='' → валидируется НЕ ТА директория ('.'), ломает собственный тест test_gate_recognises_backslash_paths и может пропустить битый скилл/зафейлить валидный при backslash-путях. (MED) eval _hit — подстрочное совпадение маркера: '400' матчит внутри '24000' → ложные попадания завышают базовую линию. (MED) evaluate не передаёт top_k в memory_search (backend n=20), при --top-k>20 молча кап на 20. (LOW) _open_backend авто-создаёт свежую БД для опечатанного --db вместо fail-safe сообщения. Фикс всех четырёх + перезамер базовой линии со словограничным матчингом.

## Acceptance Criteria

1. run_skill_conformance_gate normalizes each path ONCE and uses the normalized form for BOTH the SKILL.md basename check AND os.path.dirname — so a backslash path on POSIX resolves the correct skill directory; test_gate_recognises_backslash_paths passes on POSIX semantics (assert dirname is the skill dir, not '.'). 2. eval _hit uses word/token-boundary marker matching (regex with lookarounds), so a numeric/short marker like '400' does NOT match inside '24000'; a regression test proves the spurious match is rejected. 3. evaluate passes n=top_k to memory_search so --top-k>20 genuinely bounds backend results. 4. NEGATIVE/boundary: a typo'd/missing --db path hits the fail-safe (prints 0.0 'DB unavailable', does NOT auto-create a fresh store) — test asserts a missing path is reported, not silently created. 5. Baseline re-measured with the corrected boundary matcher; new number recorded (may differ from 100%). Full scoped verify green; ruff+mypy clean.

## Plan

## Rollback

git revert — localized fixes to two modules + tests; no schema/data change.

## Journal

- 2026-07-27T14:44:11Z [implementation] — Root cause (logic-error): (1) skill gate — normalization was applied to a COPY used only for the basename test while os.path.dirname ran on the original path; on POSIX, posixpath.dirname of a backslash path returns '' → wrong dir validated. Fix: normalize once, reuse for both. Prevention: never normalize a path for one predicate and use the raw form for a sibling predicate — normalize at the boundary, thread the normalized value. (2) eval — substring marker match ('400' in '24000') could inflate the baseline; fixed with a token-start anchor (kept prefix-stem matching for Russian). (3) top_k not passed to memory_search (backend n=20 cap); (4) _open_backend auto-created a store for a missing path, bypassing the AC4 fail-safe. AC-1: ✓ tests/test_skill_spec_conformance.py::TestGate::test_gate_validates_the_right_dir_from_a_backslash_path. AC-2: ✓ tests/test_eval_memory_retrieval.py::test_marker_boundary_rejects_substring_in_number + test_marker_prefix_still_matches_inflected_word. AC-4: ✓ test_missing_db_is_failsafe. Negative: missing --db path reported, not auto-created (test_missing_db_is_failsafe). AC-5: baseline re-measured with boundary matcher = 100% top-5 unchanged (confirms it was not a substring artifact).
- 2026-07-27T14:44:31Z [implementation] — AC-1 ✓ test_gate_validates_the_right_dir_from_a_backslash_path (dirname from normalized path); AC-2 ✓ test_marker_boundary_rejects_substring_in_number + test_marker_prefix_still_matches_inflected_word; AC-3 ✓ memory_search(query, n=max(top_k,1)); AC-4 ✓ test_missing_db_is_failsafe (missing --db reported, not auto-created); AC-5 ✓ baseline re-measured = 100% top-5 unchanged (not a substring artifact). ruff+mypy clean; 25 tests pass. Root cause logged (logic-error).
