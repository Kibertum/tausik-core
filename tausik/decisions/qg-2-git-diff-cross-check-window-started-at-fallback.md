---
slug: qg-2-git-diff-cross-check-window-started-at-fallback
task: p0-defect-qg-2-git-diff-cross-check-created-at-sta
date: "2026-06-11"
edges: []
---

## Decision

QG-2 git-diff cross-check window = started_at (fallback created_at)

## Rationale

created_at у backlog-задач опережает работу на сессии; git log --since=created_at затягивает чужие промежуточные коммиты в actual и даёт перманентный git-mismatch (verify-run не записывается вовсе). Окно от started_at соответствует семантике 'files changed since task start' из docstring verify_git_diff.
