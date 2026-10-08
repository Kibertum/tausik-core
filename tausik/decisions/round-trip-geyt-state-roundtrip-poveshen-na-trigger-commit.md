---
slug: round-trip-geyt-state-roundtrip-poveshen-na-trigger-commit
task: state-git-roundtrip-gate
date: "2026-07-26"
edges: []
---

## Decision

Round-trip гейт state_roundtrip повешен на trigger COMMIT, не task-done; свежие гейт-модули обязаны проходить адверсариальное ревью до закрытия.

## Rationale

task-done мутирует БД и может auto-close родителя (story/epic), поэтому task-done-проверка флагала бы собственную in-flight запись как дрейф. Граница коммита — где 'файлы в git == БД' реально важно. Ревью нашло 2 HIGH в гейте (fail-open дыра импорта + worktree-vs-staged), которые тихо подорвали бы его гарантию — гейт защищает коммиты, его дыра невидима без адверсариального прохода.
