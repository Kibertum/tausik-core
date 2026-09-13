---
slug: trekery-pered-tegom-1-9-smena-255-14-gitlab-2-github-pr-5
title: "Трекеры перед тегом 1.9 (смена #255): 14 GitLab + 2 GitHub + PR #5 — каждому тикету назначено состояние, всем отвечено, ни один не закрыт"
type: context
tags:
  - github
  - gitlab
  - release-1.9
  - trackers
task: tracker-sweep-before-the-19-tag
edges: []
---

Заменяет #684. Тикет → задача → релиз (ответы опубликованы 13.09, закрытие — по публикации 1.9):
ПОЧИНЕНО В 1.9: GL #3 (056818b), #4 (b487f87), #7 (3de2528), #12 (session-capacity-counts-a-tasks-whole-life-not-this-shift; ответ 13.09), #13 (relevant-files-swallows-a-comma-joined-list-as-one-path, 8dac7a4c), #15 (verify-prints-a-handle-the-close-is-bound-to-refuse, 46161e24), #16 (test-ref-detector-recognises-only-python-paths, 46161e24), #17 (codex-first-class-19 + живая приёмка; матрица с условием доверия); GH #7 (056818b), #8 (3de2528+b487f87); GL #10 — патчи 0002/0003 сняты в 1.9.
ОТЛОЖЕНО В 1.10 решениями #362/#366 (автору сказано): GL #5 (framework-version-stamp-reads-as-the-products-version), #6 (claudemd-template-names-two-memory-stores-of-three), #8 (capacity-counts-the-task-window-not-the-session-work), #11 (rag-language-list-is-hardcoded-while-stacks-are-user-extensible), #14 (update-claudemd-writes-session-state-into-a-tracked-agents-md), GL #10 патч 0004 (scope-gate-baseline-never-moves-after-first-start — решение владельца о безопасности гейта).
GH PR #5 (Okianiwa): fail-secure flip вошёл в 1.9 с кредитом в CHANGELOG; шесть остальных правок — 1.10 (port-external-pr5-hook-coverage, pr5-was-promised-a-merge-…); автору отписано 13.09 с извинением, PR открыт и MERGEABLE против release/1.9.
Форма закрытия: тикет закрывается ссылкой на релиз, не на SHA линии разработки (SHA не разрешается из публичного репозитория).
