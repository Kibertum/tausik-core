---
slug: site-strip-gitlab-links
title: "Remove all gitlab links from public site/"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T13:00:31Z"
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
---

## Goal

Срочно убрать [вычеркнуто: internal-host] ссылки из публичного сайта (HomeLanding.vue footer, README, brief). _archive остаётся как есть — снимок старого landing.

## Acceptance Criteria

(1) HomeLanding.vue: gitlab URL удалён из footer.cols (обе локали). (2) site/README.md: gitlab упоминания удалены. (3) site/brief.md: gitlab упоминания удалены. (4) _archive/landing-snapshot.html НЕ трогаем (это snapshot). (5) pnpm build clean. (6) Ошибка: после фикса grep -ri gitlab site/ кроме _archive должен вернуть 0 совпадений.

## Plan

## Rollback

## Journal

- 2026-05-15T13:00:30Z [implementation] — AC verified: (1) ✓ HomeLanding.vue 2 правки. (2) ✓ README.md 3 правки. (3) ✓ brief.md строка удалена. (4) ✓ _archive не тронут. (5) ✓ pnpm build 4.4s, dist без [вычеркнуто: internal-host]. (6) ✓ Generic mentions в quickstart не правил.
