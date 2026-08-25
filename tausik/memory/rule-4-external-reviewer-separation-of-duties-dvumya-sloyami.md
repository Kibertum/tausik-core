---
slug: rule-4-external-reviewer-separation-of-duties-dvumya-sloyami
title: "Rule 4 external reviewer: separation of duties двумя слоями"
type: pattern
tags: []
task: v15s-rule4-external-reviewer
edges: []
---

Запрет на write у ревьюера — через tool-allowlist субагента (harness/claude/subagents, tools: Read,Grep,Bash без Write). Different model — через external_reviewer.recommend_reviewer_model (выбор семейства != автора, opus->fable fallback). НЕ добавлять колонку в reviews-таблицу: модель ревьюера пишется в notes, separation проверяется на уровне выбора модели, а не схемы. L3-триггер вызывает delegation-hint best-effort (никогда не падает).
