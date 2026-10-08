---
slug: publish-release-1-11-3-gitlab-merge-github-release
title: "publish release 1.11.3 gitlab merge github release"
status: done
epic: null
story: null
complexity: null
role: release
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - release-body-1.11.3.md
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-08T09:28:24Z"
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
blocked_question: null
unblock_criteria: null
unblocked_by: null
unblocked_at: null
---

## Goal

Опубликовать релиз 1.11.3 по слову владельца: релизные ноты (release-body, whats-new EN/RU) с атрибуцией GLM, тег v1.11.3, GitLab push + MR в main + merge, GitHub Release, закрытие тикетов, проверка каждого шага.

## Acceptance Criteria

1. release-body-1.11.3.md и whats-new 1.11 EN/RU несут раздел 1.11.3 со ссылками на тег; коммит публикации атрибутирует GLM.
2. Тег v1.11.3 существует локально и на ОБОИХ ремоутах; MR v1-11-3 в main на GitLab слит (state=merged).
3. GitHub Release v1.11.3 опубликован с телом release-body-1.11.3.md; URL проверен gh release view.
4. НЕГАТИВНЫЙ: тикеты #88/#93/#48 закрыты комментарием со ссылкой на релиз; каждый шаг публикации проверен своей командой (ls-remote/mr view/release view).

## Plan

## Rollback

## Journal

- 2026-10-08T09:27:59Z [implementation] — AC-1: AC-2: AC-3: AC-4 NEGATIVE: все проверено живыми командами - see next entry
- 2026-10-08T09:27:59Z [implementation] — real evidence: AC-1: release-body-1.11.3.md + whats-new EN/RU 1.11.3, коммит a2cf402a с Co-authored-by GLM (glm-5.2). AC-2: тег v1.11.3 на origin (GitLab) и github - ls-remote подтверждает оба; GitLab MR !2 v1-11-3->main state=merged. AC-3: GitHub Release v1.11.3 опубликован 2026-10-08T09:26:52Z, URL https://github.com/Kibertum/tausik-core/releases/tag/v1.11.3, gh release view подтверждает. AC-4 NEGATIVE: тикеты #88/#93/#48 - state CLOSED (проверено gh issue view); GitHub main = snapshot fc9bd70a (decision #422, дерево v1.11.3 поверх публичной линии). Verify run PASS handle 3661.cf9825c344d2f1b57e900ac7ec0d4dcf.
- 2026-10-08T09:28:11Z [implementation] — AC verified: 1. OK release-body-1.11.3.md + whats-new EN/RU (a2cf402a, Co-authored-by GLM). 2. OK tag v1.11.3 on origin+github (ls-remote); GitLab MR 2 merged. 3. OK GitHub Release published 2026-10-08T09:26:52Z. 4. OK tickets 88/93/48 CLOSED.
