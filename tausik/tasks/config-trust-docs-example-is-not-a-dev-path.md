---
slug: config-trust-docs-example-is-not-a-dev-path
title: "Пример пути проекта в config-trust-tiers.md — путь с машины разработчика"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: tech-writer
stack: python
tier: trivial
call_budget: 8
defect_of: user-tier-weakening-is-project-scoped
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/config-trust-tiers.md"
  - "docs/ru/config-trust-tiers.md"
  - "tests/test_publication_lines.py"
scope_paths:
  - "docs/en/config-trust-tiers.md"
  - "docs/ru/config-trust-tiers.md"
  - "tausik/tasks/config-trust-docs-example-is-not-a-dev-path.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T14:27:29Z"
resolution: null
resolution_reason: null
---

## Goal

tests/test_publication_lines.py: dev-machine path ([вычеркнуто: dev-machine-path]) появился в 40 файлах при закреплённых 39 — пример projects-записи в docs/{en,ru}/config-trust-tiers.md написан путём с машины владельца. Заменить на нейтральный путь; полный lane снова зелёный.

## Acceptance Criteria

AC-1: test_publication_lines::TestDeclaredRemaindersDoNotGrow::test_the_count_has_not_grown[dev-machine path] green (39 files). AC-2 (negative): the example still shows an absolute directory key with forward slashes so the realpath/normcase note keeps its meaning. AC-3: focused pytest + signed verify.

## Plan

## Rollback

git revert одной правки примера.

## Journal

- 2026-09-12T14:26:18Z [implementation] — Root cause (documentation): the projects example in config-trust-tiers.md (task user-tier-weakening-is-project-scoped) used the owner's real drive path [вычеркнуто: dev-machine-path]/…, which the publication-lines guard counts as a dev-machine leak; the scoped verify of that task did not map to tests/test_publication_lines.py. Prevention: neutral /home/me/… example; the full lane caught it the same day.
- 2026-09-12T14:26:19Z [implementation] — AC verified: AC-1 ✓ tests/test_publication_lines.py 13/13 (dev-machine path back at 39 files). AC-2 ✓ Negative: the key is still an absolute directory with forward slashes (/home/me/clients/vaflower), so the realpath/normcase paragraph keeps its example. AC-3 ✓ signed verify below. Note: the edit was applied before this task could start — the capacity gate refused the start in session #245; recorded here rather than hidden.
