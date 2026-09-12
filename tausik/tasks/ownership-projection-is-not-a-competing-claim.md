---
slug: ownership-projection-is-not-a-competing-claim
title: "Проекция экспорта не конкурирует с ACL-владельцем за путь в коммите"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: null
defect_of: ownership-commit-local-scope-paths
scope: "Только разрешение претендентов внутри foreign_completed_paths_since и его real-git тесты."
scope_exclude: "Не менять verify_scope_honesty, не доверять текущему worktree, не вводить временные границы по completed_at (замерено: 42→43, бесполезно), не переписывать историю, не релизить, не трогать .agents/."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
  - "tausik/tasks/ownership-projection-is-not-a-competing-claim.md"
  - "tausik/stories/release19-proof-integrity.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-12T12:06:36Z"
---

## Goal

Убрать ложную неоднозначность владения в verify_commit_ownership: в массовом backlog-коммите e2f55369 151 из 200 путей помечены ambiguous, потому что экспорт каждой задачи claim-ит сам себя (проекция) и одновременно на него claim-ит glob scope_paths активной задачи normalize. Это два независимых доказательства, что путь чужой, а не два конкурирующих исполнителя. Ввести ярусы доказательств: same-commit (relevant_files + scope_paths ACL) > parent-tree предобъявление > проекция (собственный экспорт, история). Путь решается на самом сильном непустом ярусе: один претендент — владелец, несколько — ambiguous. Претензия задачи на СОБСТВЕННЫЙ экспорт всегда проекция, из какого бы поля она ни пришла. Fail-closed для uncommitted, unknown и конкурирующих work-претензий сохраняется. Замер прототипом на реальной истории: undeclared для agents-skill-count-14 169→16, scoped-pytest-empty-late-batch 167→14, tree-subagent-reviewer 181→20.

## Acceptance Criteria

AC-1 (real git): один коммит содержит экспорт задачи X (active, scope_paths [tausik/tasks/*.md]) и экспорт задачи Y (любой статус) — путь tausik/tasks/Y.md для стороннего верифицируемого T получает status complete (владелец X, проекция Y не конкурирует). AC-2 (negative, real git): экспорт Y объявляет в relevant_files путь foreign.py, а X — glob, покрывающий foreign.py, в том же коммите — foreign.py остаётся undeclared (две work-претензии same-commit). AC-3 (negative boundary, real git): same-commit экспорт X с relevant_files foreign.py плюс предобъявленная в parent-tree active-задача Z с тем же relevant_files — foreign.py принадлежит X (same-commit сильнее parent-tree), а без экспорта X в коммите тот же foreign.py при Z и W в parent-tree остаётся undeclared. AC-4: задача, перечислившая свой собственный экспорт в scope_paths, не получает work-претензии на него: коммит с её экспортом и glob-владельцем X даёт complete. AC-5 (negative): все существующие тесты test_verify_commit_ownership.py остаются зелёными без ослабления; uncommitted/unknown/malformed остаются undeclared. AC-6: focused pytest, ruff, mypy, dedupe без новых групп и signed verify проходят; CHANGELOG EN/RU получают запись.

## Plan

[{"step": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c \u043f\u0440\u0435\u0442\u0435\u043d\u0437\u0438\u0438 \u043d\u0430 \u0442\u0440\u0438 \u044f\u0440\u0443\u0441\u0430 (same-commit work, parent-tree, \u043f\u0440\u043e\u0435\u043a\u0446\u0438\u044f) \u0438 \u0440\u0435\u0448\u0430\u0442\u044c \u043f\u0443\u0442\u044c \u043d\u0430 \u0441\u0438\u043b\u044c\u043d\u0435\u0439\u0448\u0435\u043c \u043d\u0435\u043f\u0443\u0441\u0442\u043e\u043c \u044f\u0440\u0443\u0441\u0435", "done": true}, {"step": "\u0421\u043e\u0431\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0439 \u044d\u043a\u0441\u043f\u043e\u0440\u0442 \u0437\u0430\u0434\u0430\u0447\u0438 \u2014 \u0432\u0441\u0435\u0433\u0434\u0430 \u043f\u0440\u043e\u0435\u043a\u0446\u0438\u044f, \u0438\u0437 \u043a\u0430\u043a\u043e\u0433\u043e \u0431\u044b \u043f\u043e\u043b\u044f (relevant_files/scope_paths) \u043d\u0438 \u043f\u0440\u0438\u0448\u043b\u0430 \u043f\u0440\u0435\u0442\u0435\u043d\u0437\u0438\u044f", "done": true}, {"step": "Real-git \u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\u0438 AC-1..AC-4, \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0435 \u0442\u0435\u0441\u0442\u044b \u0431\u0435\u0437 \u043e\u0441\u043b\u0430\u0431\u043b\u0435\u043d\u0438\u044f", "done": true}, {"step": "Focused pytest, ruff, mypy, dedupe, signed verify; CHANGELOG EN/RU", "done": true}]

## Rollback

git revert одного коммита задачи; поведение возвращается к плоскому объединению претензий.

## Journal

- 2026-09-12T12:01:19Z [implementation] — Диагноз замером: в e2f55369 (200 путей) плоское объединение претензий даёт 151 ambiguous, из них подавляющее большинство — пара (<свой slug через проекцию экспорта>, normalize через glob scope_paths). Прототип ярусов в scratchpad: undeclared 169→16 / 167→14 / 165→15 / 181→20 / 212→42 для пяти задач 1.9. Остаток — README/constants.json из 6013fb2e без экспорта владельца с relevant_files и код из безэкспортных коммитов fbcbf0b7/8c63c76c; он честно останется в квитанции.
- 2026-09-12T12:04:24Z [implementation] — Ярусы реализованы: same-commit (relevant_files + scope_paths ACL, собственный экспорт исключён) > parent-tree (собственный экспорт исключён, читается только когда commit молчит) > проекция (экспорт, история, dynamic-block). 3 новых real-git регрессии красные на старом коде и зелёные на новом; AC-2 добавлен параметром к существующему негативу; 21 passed, ruff, mypy чистые, dedupe 322 групп без роста. Реальная функция на истории: agents-skill-count-14 undeclared 166→12. CHANGELOG EN/RU записаны.
- 2026-09-12T12:05:55Z [implementation] — AC verified: AC-1 ✓ test_moved_export_belongs_to_the_acl_owner_not_to_itself[projection-only] (red on old code, green now). AC-2 ✓ test_two_sibling_exports_in_one_commit_remain_ambiguous[relevant-files-versus-acl-glob] — foreign.py stays undeclared. AC-3 ✓ test_same_commit_export_outranks_a_predeclared_parent_tree_claim (red on old, green now) + existing test_ambiguous_predeclared_sibling_scopes_remain_undeclared for the parent-tree-only negative. AC-4 ✓ test_moved_export_belongs_to_the_acl_owner_not_to_itself[own-export-listed-in-acl]. AC-5 ✓ 21/21 ownership tests, 154/154 across the six modules importing ownership/scope-honesty; uncommitted/unknown/malformed negatives unchanged. AC-6 ✓ ruff, mypy clean; dedupe 322 groups unchanged; signed verify #2440 PASS; CHANGELOG EN/RU entries written.
- 2026-09-12T12:06:35Z [implementation] — Root cause (logic-error): foreign_completed_paths_since flattened three kinds of claim (same-commit declaration, parent-tree predeclaration, framework projection of an export/story) into one set per path, so a moved export was 'claimed' by itself via projection and by the ACL owner via scope_paths glob — two proofs that the path is foreign cancelled each other as 'ambiguous' (151/200 paths in e2f55369). Prevention: claims are resolved on the strongest non-empty tier only, a task never work-claims its own export, and the measured residue is logged in the task journal before any resolver change is accepted.
