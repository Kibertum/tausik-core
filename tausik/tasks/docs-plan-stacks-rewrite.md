---
slug: docs-plan-stacks-rewrite
title: "Plan-stacks table rewrite — drop 18 phantom stacks, add 13 missing"
status: done
epic: null
story: null
complexity: medium
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
completed_at: "2026-05-15T13:38:51Z"
---

## Goal

plan-stacks.md File Detection table (line 7-38): убрать 18 phantom rows (symfony, node, elixir, sveltekit, ios, unity, android, react-native, devops, db, security, sre, ux, lead, game-designer, narrative, pixel-artist, sound-designer). Добавить 13 real-but-missing: blade, docker, ansible, helm, kubernetes, terraform, flask, java, javascript, kotlin, swift, typescript, vue. Обновить Reference paths: harness/stacks/<n>.md → stacks/<n>/guide.md. КРИТИЧНО — /plan skill принимает решения из этой таблицы.

## Acceptance Criteria

(1) Phantom rows (18 несуществующих стеков) удалены. (2) Real-but-missing 13 стеков добавлены. (3) Reference paths harness/stacks/X.md → stacks/X/guide.md. (4) pnpm build clean. (5) Ошибка: после фикса /plan skill должен видеть только реальные stacks.

## Plan

## Rollback

## Journal

- 2026-05-15T13:38:51Z [implementation] — AC verified: rewrote File Detection table — dropped 18 phantom rows (symfony/node/elixir/sveltekit/ios/unity/android/react-native/devops/db/security/sre/ux/lead/game-designer/narrative/pixel-artist/sound-designer), added 13 real stacks (blade/docker/ansible/terraform/helm/kubernetes/flask/java/javascript/kotlin/swift/typescript/vue). Reference paths fixed to stacks/<n>/guide.md. Keyword Mapping переписан. Roles теперь явно отделены (security/sre/lead/ux — это roles, не stacks).
