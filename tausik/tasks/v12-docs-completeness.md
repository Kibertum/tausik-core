---
slug: v12-docs-completeness
title: "Доделать v1.2: RU-README, docs/ обновление, skill interconnection, mirror sync"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "README.ru.md, docs/en/{cli,hooks,mcp,skills}.md, docs/ru/{cli,hooks,mcp,skills}.md, references/QUICKSTART.{en,}md, agents/skills/plan/SKILL.md, agents/skills/ship/SKILL.md"
scope_exclude: "CHANGELOG.md (уже обновлён), README.md (EN, уже обновлён), references/project-cli.md и references/architecture.md (уже обновлены), scripts/ и bootstrap/ — только docs + skills"
relevant_files:
  - README.ru.md
  - "docs/en/cli.md"
  - "docs/en/hooks.md"
  - "docs/en/mcp.md"
  - "docs/en/skills.md"
  - "docs/ru/cli.md"
  - "docs/ru/hooks.md"
  - "docs/ru/mcp.md"
  - "docs/ru/skills.md"
  - "references/QUICKSTART.en.md"
  - "references/QUICKSTART.md"
  - "agents/skills/plan/SKILL.md"
  - "agents/skills/ship/SKILL.md"
  - "scripts/tausik_utils.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-17T08:14:12Z"
---

## Goal

Закрыть реальные пробелы предыдущего прохода: README.ru.md, docs/en+ru (cli/hooks/mcp/skills), QUICKSTART, .claude/ mirror sync, /plan+/go→/interview связь, /ship adversarial mode

## Acceptance Criteria

1) Re-bootstrap: .claude/scripts/hooks/ содержит _common.py + notify_on_done.py. 2) README.ru.md: секция "Anti-Drift (v1.2.0)" + tests badge 918→1095. 3) docs/en/cli.md +memory block/compact, hud, suggest-model. 4) docs/en/hooks.md секция про новые hooks. 5) docs/en/mcp.md +tausik_memory_block, tausik_memory_compact. 6) docs/en/skills.md +/interview. 7) Все 4 реплицированы в docs/ru/. 8) references/QUICKSTART.en.md и references/QUICKSTART.md: anti-drift 1-2 параграфа. 9) agents/skills/plan/SKILL.md: complex complexity рекомендует /interview. 10) agents/skills/ship/SKILL.md: critical/security → /review deep-mode. 11) pytest existing lint passed. 12) ruff clean. Negative: (a) docs/ файлы с '1.1' или '918 tests' → обновить. (b) ссылки на отсутствующие файлы — проверить. (c) markdown таблицы не сломать.

## Plan

[{"step": "Re-bootstrap \u2192 sync .claude/ mirror", "done": true}, {"step": "README.ru.md: \u0437\u0435\u0440\u043a\u0430\u043b\u044c\u043d\u044b\u0439 v1.2 \u0431\u043b\u043e\u043a", "done": true}, {"step": "docs/en/{cli,hooks,mcp,skills}.md \u2014 4 \u0444\u0430\u0439\u043b\u0430", "done": true}, {"step": "docs/ru/{cli,hooks,mcp,skills}.md \u2014 4 \u0444\u0430\u0439\u043b\u0430", "done": true}, {"step": "references/QUICKSTART.{en,}md \u2014 anti-drift \u043f\u0430\u0440\u0430\u0433\u0440\u0430\u0444", "done": true}, {"step": "agents/skills/plan + ship \u2014 \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f /interview + deep-mode", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-17T08:11:03Z [implementation] — AC verified: AC1 (.claude/ mirror) ✓ — re-bootstrap скопировал _common.py + notify_on_done.py. AC2 (README.ru.md) ✓ — Anti-Drift секция + badge 918→1095 + 34→35/80→82. AC3-6 (docs/en/*.md) ✓ — cli.md +memory block/compact/hud/suggest-model; hooks.md +7 новых hooks таблица; mcp.md +memory_block/memory_compact (80→82 tools); skills.md +/interview. AC7 (docs/ru/*.md) ✓ — все 4 файла синхронизированы. AC8 (QUICKSTART.{en,ru}.md) ✓ — anti-drift параграф добавлен в оба. AC9 (/plan→/interview) ✓ — Interview phase теперь упоминает /interview skill для complex запросов. AC10 (/ship→deep mode) ✓ — Review Changes секция добавила auto-escalate для security/auth/payment/crypto/>5 files. AC11 (pytest) ✓ — 1095/1095 passed in 201s (lint tests 44/44 отдельно). AC12 (ruff clean) ✓. Negative: (a) все '918 tests' заменены на '1095' (README.md/README.ru.md). (b) ссылки проверены (docs/en/hooks.md, docs/ru/hooks.md — оба существуют).
