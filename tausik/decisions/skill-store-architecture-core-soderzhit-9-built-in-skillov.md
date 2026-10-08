---
slug: skill-store-architecture-core-soderzhit-9-built-in-skillov
task: null
date: "2026-04-06"
edges: []
---

## Decision

Skill Store Architecture: core содержит ~9 built-in скиллов. Остальные скиллы живут в отдельном GitLab репо ([вычеркнуто: internal-host]/tausik/skills). Skills загружаются on-demand через skills.json + bootstrap. MCP серверы скиллов (jira, bitrix24) хранятся рядом со скиллом в skills repo. Версионирование по ref repo. Adjacent dir convention (../skills/) для local dev.

## Rationale

1) Core не должен содержать мусор опциональных интеграций. 2) Скиллы тратят токены контекста — загрузка on-demand экономит бюджет. 3) Отдельный repo позволяет независимый цикл релизов скиллов. 4) Adjacent dir даёт удобную кросс-проектную разработку без submodules. 5) GitLab only (без GitHub) для skills repo.
