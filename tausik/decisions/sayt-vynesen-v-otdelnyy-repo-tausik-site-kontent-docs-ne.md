---
slug: sayt-vynesen-v-otdelnyy-repo-tausik-site-kontent-docs-ne
task: site-followup-exec
date: "2026-06-28"
edges: []
---

## Decision

Сайт вынесен в отдельный репо tausik/site; контент (docs) НЕ вендорится — CI клонирует tausik/core read-only deploy-токеном и кладёт docs/{en,ru,_generated} в .docs-src при сборке. Сайт стал самостоятельным TAUSIK-проектом.

## Rationale

Единый source-of-truth доков остаётся в core (вариант «CI клонирует core» выбран против submodule/snapshot/mirror — минимум движущихся частей, без дублирования и дрейфа доков). GitHub держит только фреймворк (сайт туда не тащим).
