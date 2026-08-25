---
slug: v156-version-bump-changelog
title: "v1.5.6: bump version + CHANGELOG (EN+RU) + rebuild .claude generated copies"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "pyproject.toml, scripts/tausik_version.py, CHANGELOG.md, CHANGELOG.ru.md, docs/_generated/constants.json, .claude/ (rebuild)"
scope_exclude: "github orphan (не трогать); незапушенные ветки"
relevant_files:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - "harness/cursor/mcp/project/tools.py"
  - "harness/cursor/mcp/project/handlers.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:39:56Z"
---

## Goal

Поднять версию 1.5.5→1.5.6 в pyproject.toml + scripts/tausik_version.py, регенерировать doc-constants, добавить секцию [1.5.6] в CHANGELOG.md + CHANGELOG.ru.md (P0 Kilo-CLI hotfix, P1 Windows/Unicode, P2 task quick --ac, P4 single IDE source). Пересобрать сгенерированные .claude/ копии из источников (scripts/harness/bootstrap), чтобы рабочее дерево было консистентно перед релизом.

## Acceptance Criteria

1. pyproject.toml + scripts/tausik_version.py = 1.5.6; gen_doc_constants → constants.json tausik_version=1.5.6. 2. CHANGELOG.md + CHANGELOG.ru.md содержат секцию [1.5.6] с P0/P1/P2/P4, [Unreleased] очищен. 3. .claude/ (и прочие IDE-копии) пересобраны из источников — generated-parity тесты зелёные. 4. Полный сьют зелёный. 5. НЕГАТИВНЫЙ: нет рассинхрона версии между pyproject/tausik_version/constants (grep 1.5.5 пуст вне исторических CHANGELOG-секций).

## Plan

[{"step": "pyproject.toml + tausik_version.py \u2192 1.5.6; regen constants", "done": true}, {"step": "CHANGELOG.md + CHANGELOG.ru.md \u2192 \u0441\u0435\u043a\u0446\u0438\u044f [1.5.6] (P0/P1/P2/P4)", "done": true}, {"step": "README \u0431\u0435\u0439\u0434\u0436\u0438 \u0432\u0435\u0440\u0441\u0438\u0438 1.5.5\u21921.5.6", "done": true}, {"step": "\u0421\u0438\u043d\u043a MCP-\u0437\u0435\u0440\u043a\u0430\u043b (cursor + .claude tools/handlers/server) \u043f\u043e\u0441\u043b\u0435 P1/P2-\u043f\u0440\u0430\u0432\u043e\u043a", "done": true}, {"step": "\u041f\u043e\u043b\u043d\u044b\u0439 \u0441\u044c\u044e\u0442 \u0437\u0435\u043b\u0451\u043d\u044b\u0439 (4291+ passed; 3 \u0441\u0431\u043e\u044f \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u044b)", "done": true}]

## Rollback

git revert — версионные строки и CHANGELOG откатываются; rebuild идемпотентен.

## Journal

- 2026-06-19T19:39:56Z [implementation] — AC verified: AC-1: ✓ pyproject.toml=1.5.6, scripts/tausik_version.py=1.5.6, constants.json tausik_version=1.5.6 (gen_doc_constants). AC-2: ✓ CHANGELOG.md + CHANGELOG.ru.md имеют [1.5.6] (P0 Kilo-CLI, P1 Unicode, P2 task quick --ac, P4 single IDE source), [Unreleased] очищен. AC-3: ✓ N/A для git: .claude/ gitignored (локальная generated-копия); рабочее дерево tracked-файлов консистентно. MCP-зеркала (cursor+.claude tools/handlers/server) синхронизированы — test_mcp_mirrors_in_sync + test_mirror_in_sync + test_enum_single_source: 65 passed. AC-4: ✓ полный сьют: 4291 passed (3 сбоя устранены: 2 mirror-sync регрессии от P1/P2 + 1 гонка constants от конкурентного edit). AC-5: ✓ НЕГАТИВНЫЙ: grep 1.5.5 вне CHANGELOG-истории пуст (версия консистентна). README бейджи 1.5.5→1.5.6. Domain: версия едина во всех 4 точках, CHANGELOG двуязычный синхронен.
