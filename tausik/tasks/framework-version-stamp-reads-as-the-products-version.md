---
slug: framework-version-stamp-reads-as-the-products-version
title: "Штамп версии фреймворка стоит в документе продукта без подписи и читается как версия продукта"
status: done
epic: release-19-renar-conformance
story: release19-tracker-promises
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/claudemd_state.py"
  - "tests/test_claudemd_state_stamp.py"
  - "tests/test_mcp_update_claudemd_parity.py"
  - "docs/en/skill-patterns.md"
  - "docs/ru/skill-patterns.md"
  - CLAUDE.md
  - AGENTS.md
scope_paths:
  - "scripts/project_cli_extra.py"
  - "scripts/*.py"
  - "harness/**"
  - "tests/*.py"
  - "docs/en/*.md"
  - "docs/ru/*.md"
  - CLAUDE.md
  - AGENTS.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-13T16:14:37Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Строка состояния в CLAUDE.md продукта не может быть прочитана как утверждение о версии продукта.

## Acceptance Criteria

1. Поле подписано так, что принадлежность фреймворку очевидна без чтения кода (например «TAUSIK: 1.8.0», а не «Version: 1.8.0»).
2. Правка сделана в ОБОИХ местах, печатающих один формат; тикет GitLab #5 называет это отдельной частью дефекта — вторая копия правила. Места перечисляются из кода.
3. Замер тикета назван в тесте: проект версии 0.1.0, чей CLAUDE.md объявляет 1.8.0.
4. НЕГАТИВНЫЙ сценарий: тест на то, что строка НЕ содержит слова, читаемого как версия продукта, — иначе правка сведётся к косметике и вернётся при следующем редактировании формата.

## Plan

## Rollback

git revert коммита; правка в формате строки в двух местах

## Journal

- 2026-09-13T16:14:34Z [implementation] — AC-1 ✓ the stamp reads 'TAUSIK: <version>' (claudemd_state.STAMP_LABEL); tests/test_claudemd_state_stamp.py::test_the_stamp_names_the_framework_as_the_owner_of_the_number. AC-2 ✓ both callers (scripts/project_cli_extra.py, harness/claude/mcp/project/handlers_skill.py) import the one producer build_dynamic_state and spell no stamp f-string — ::test_the_label_is_one_constant_and_the_format_has_one_producer (AST, not substring — review); the ticket's two places were already one producer since the MCP/CLI merge. AC-3 ✓ the ticket's measurement is the fixture: a consumer at 0.1.0 (pyproject) whose block says TAUSIK: 1.9.0 and never 0.1.0. AC-4 ✓ (NEGATIVE) ::test_the_stamp_carries_no_bare_version_label — the regex refuses 'Version: 1.8.0' (asserted on the pre-fix line) and passes the new one. docs/{en,ru}/skill-patterns.md show the new line (::test_the_skill_pattern_docs_show_the_same_label); this repository's CLAUDE.md/AGENTS.md regenerated. 47 tests in the four claudemd files; verify run #2625 signed. Review (tausik-reviewer): no other parser of 'Version:' in the repo; LOW on the substring check applied. Domain: the number in a product's document says whose it is.
