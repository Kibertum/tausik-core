---
slug: version-bump
title: "Обновить версию фреймворка до 3.0.0"
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
relevant_files:
  - "scripts/frai_version.py"
  - README.md
  - README.en.md
  - LICENSE
  - CHANGELOG.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T20:10:48Z"
---

## Goal

Версия 3.0.0 во всех файлах: frai_version.py, README, LICENSE, CLAUDE.md, CHANGELOG.

## Acceptance Criteria

1. frai_version.py = 3.0.0. 2. README.md/README.en.md = 3.0.0. 3. LICENSE = Frai 3.0.0. 4. CHANGELOG.md содержит v3.0.0 секцию. 5. Ошибка если grep 2.9.0 находит stale версии в ключевых файлах.

## Plan

## Rollback

## Journal

- 2026-04-05T20:10:42Z [implementation] — AC verified: frai_version.py=3.0.0 ✓ README.md/en=3.0.0 ✓ LICENSE=3.0.0 ✓ CHANGELOG v3.0.0 section ✓
