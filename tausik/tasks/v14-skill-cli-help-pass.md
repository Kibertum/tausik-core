---
slug: v14-skill-cli-help-pass
title: "Выравнивание --help для skill команд"
status: done
epic: v14-skill-store
story: v14-skill-store-ux
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_skill_cli_help.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:08:48Z"
---

## Goal

Единообразные сообщения и коды выхода.

## Acceptance Criteria

1. Ревью подсказок. 2. Чеклист. 3. Negative: неизвестный repo URL даёт ошибку с подсказкой.

## Plan

## Rollback

## Journal

- 2026-05-02T10:54:18Z [implementation] — Implementation: (1) main() catches SkillManagerError → friendly Error: prefix + exit 1 (раньше traceback). (2) Help text унифицирован: noun phrases, в name args ссылка "see: tausik skill list", в repo add url показано example github URL. (3) Тест tests/test_skill_cli_help.py — 2 help consistency + 3 negative exit code (install/repo add/activate). 5/5 passed.
- 2026-05-02T10:54:28Z [implementation] — AC verified: 1. ✓ Ревью: scripts/project_parser.py — все skill subparsers переписаны под единый стиль (noun phrase в help, hint "see: tausik skill list" на name args). 2. ✓ Чеклист: smoke-тест в tests/test_skill_cli_help.py фиксирует список subcommands в `skill --help` и `skill repo --help`. 3. ✓ Negative: scripts/project.py main() ловит SkillManagerError → "Error: ...\\n" + exit 1; tests/test_skill_cli_help.py 3 теста на нон-zero exit code и отсутствие Traceback (install/repo add/activate с unknown аргументом).
- 2026-05-02T11:03:54Z [implementation] — AC verified: 1. ✓ Ревью: scripts/project_parser.py — все skill subparsers переписаны под единый стиль (noun phrase в help, hint "see: tausik skill list" на name args). 2. ✓ Чеклист: smoke-тест в tests/test_skill_cli_help.py фиксирует список subcommands в `skill --help` и `skill repo --help`. 3. ✓ Negative: scripts/project.py main() ловит SkillManagerError → "Error: ..." + exit 1; 3 теста на non-zero exit и отсутствие Traceback.
- 2026-05-02T11:07:09Z [implementation] — AC verified: 1. Ревью --help - все skill subparsers единый стиль (noun phrase, hint see tausik skill list). 2. Чеклист - tests/test_skill_cli_help.py 5 тестов фиксируют subcommands и exit code. 3. Negative - main() ловит SkillManagerError, friendly Error: prefix exit 1, 3 теста проверяют отсутствие Traceback при unknown skill/repo URL. Refactor: вынес add_skill add_metrics в project_parser_ops для filesize gate.
- 2026-05-02T11:08:48Z [implementation] — AC verified: 1. Ревью --help - все skill subparsers единый стиль (noun phrase, hint see tausik skill list). 2. Чеклист - tests/test_skill_cli_help.py 5 тестов фиксируют subcommands и exit code. 3. Negative - main() ловит SkillManagerError, friendly Error: prefix exit 1, 3 теста проверяют отсутствие Traceback при unknown skill/repo URL. Refactor: вынес add_skill add_metrics в project_parser_ops для filesize gate.
