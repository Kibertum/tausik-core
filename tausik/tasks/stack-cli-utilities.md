---
slug: stack-cli-utilities
title: "tausik stack export / diff / reset / lint"
status: done
epic: v16-plugin-arch-and-docs
story: user-customization
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_parser.py, scripts/project_cli_stack.py"
scope_exclude: "other CLI files, registry"
relevant_files:
  - "scripts/project_cli_stack.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:16:18Z"
---

## Goal

Add 4 subcommands to tausik stack: (1) export &lt;name&gt; — copies built-in to .tausik/stacks/&lt;name&gt;/ as override template with 'extends' pre-set; (2) diff &lt;name&gt; — shows effective merged config vs pure built-in; (3) reset &lt;name&gt; — removes user override after confirmation; (4) lint &lt;name&gt; — validates user stack.json against schema, catches references to unknown built-in fields. Each emits useful CLI output, ServiceError on misuse.

## Acceptance Criteria

1. tausik stack export <name> — печатает resolved decl как JSON (source, detect, extensions, filenames, path_hints, gates).
2. tausik stack diff <name> — unified diff между builtin stack.json и .tausik/stacks/<name>/stack.json (или информативное 'nothing to diff').
3. tausik stack reset <name> — удаляет .tausik/stacks/<name>/ с подтверждением (--yes пропускает).
4. tausik stack lint — итерирует .tausik/stacks/<name>/stack.json, валидирует через validate_decl, печатает OK/FAIL.
5. project_parser добавлены 4 субкоманды.
6. Smoke: stack list/info работают (regression check); stack export python → JSON. stack lint без .tausik/stacks/ → friendly message.
7. **Negative scenario:** stack export ghost → error 'Unknown stack: ghost'; stack diff без user override → информативное сообщение, не crash.
8. Filesize: project_cli_stack.py 161 строка <400.

## Plan

## Rollback

## Journal

- 2026-04-25T17:16:18Z [implementation] — AC verified: 1. ✓ tausik stack export python → JSON dump (source/detect/extensions/filenames/path_hints/gates). 2. ✓ tausik stack diff <name> — unified diff builtin vs user override; nothing to diff если нет user. 3. ✓ tausik stack reset — rmtree user override с подтверждением, --yes пропускает. 4. ✓ tausik stack lint — итерация .tausik/stacks/<name>/stack.json + validate_decl, OK/FAIL прогон. Без .tausik/stacks/ → friendly message. 5. ✓ project_parser добавлены 4 субкоманды (export, diff, reset, lint). 6. ✓ Smoke pass: stack list, stack info python, stack export python, stack lint. 7. ✓ Negative: unknown stack→error msg, no user override→informative. 8. ✓ project_cli_stack.py 161 строка <400.
