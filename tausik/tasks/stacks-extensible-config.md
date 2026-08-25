---
slug: stacks-extensible-config
title: "VALID_STACKS extensibility via cfg.custom_stacks merge"
status: done
epic: v131-review-fixes
story: stack-extensibility
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_types.py (DEFAULT_STACKS + get_valid_stacks helper)\nscripts/service_task.py (use get_valid_stacks for validation)\nscripts/project_parser.py (drop choices= for --stack, rely on service)\nscripts/project_cli.py / scripts/project_cli_extra.py (cmd_stack list shows (custom))\nscripts/project_service.py (stack_list читает cfg.custom_stacks)\nCLAUDE.md (docs)\ntests/test_stacks_extensible.py (новый)"
scope_exclude: "scripts/default_gates.py (gates остаются default-only)\nscripts/gate_stack_dispatch.py (extension mapping остаётся captured — custom stacks без extension hint будут универсальными gates only)\nagents/claude/mcp/project/tools.py (MCP enum остаётся advisory)\nreferences/* — отдельная задача документации"
relevant_files:
  - "scripts/project_types.py"
  - "scripts/service_task.py"
  - "scripts/service_validation.py"
  - "scripts/project_service.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_stack.py"
  - CLAUDE.md
  - "tests/test_stacks_extensible.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T14:27:50Z"
---

## Goal

Make VALID_STACKS open for extension without source edit. Replace the frozenset constant with a get_valid_stacks(cfg) function that unions DEFAULT_STACKS + cfg.get('custom_stacks', []). argparse choices становится callable; MCP enum остаётся списком (advisory) но service layer валидирует через get_valid_stacks. STACK_GATE_MAP остаётся building только default+config-defined gates. Документировать в CLAUDE.md и references/project-cli.md как добавить custom stack.

## Acceptance Criteria

- [ ] project_types: VALID_STACKS остаётся как DEFAULT_STACKS (the default frozenset). Добавлен helper get_valid_stacks(cfg=None) -> frozenset, который возвращает union(DEFAULT_STACKS, cfg.get('custom_stacks', []))
- [ ] service_task: task_add/task_update валидация stack использует get_valid_stacks() с loaded config. Custom stack типа 'ruby' принимается если есть в cfg.custom_stacks
- [ ] argparse: --stack choices теперь callable / dynamic — параметр валидируется в service layer (не argparse choices=); error message содержит и default и custom stacks
- [ ] STACK_GATE_MAP: остаётся building только из DEFAULT_GATES (custom stacks без gates — universal-only через filesize, что норм)
- [ ] tausik stack list показывает custom stacks с marker '(custom)' рядом со стэком
- [ ] CLAUDE.md секция "Стеки" обновлена: упоминает что добавление через config.json под 'custom_stacks' возможно; counter "20" исправлен на актуальный
- [ ] references/project-cli.md (если относится) — короткая инструкция как добавить custom stack
- [ ] Backwards compat: все 251+ существующих тестов проходят без изменений (default stacks работают как раньше)
- [ ] MCP tools.py enum stack — оставляем как есть (advisory, custom stacks через MCP проходят validation в service layer; enum в JSON Schema служит как hint)
- [ ] Negative scenarios: cfg.custom_stacks с пустой строкой/None/non-string — graceful skip; stack который ни в default ни в custom — ServiceError с suggestion
- [ ] Tests test_stacks_extensible.py: (a) DEFAULT_STACKS unchanged; (b) get_valid_stacks без cfg = defaults; (c) cfg.custom_stacks = ['ruby','elixir'] добавляет к valid; (d) service.task_add с custom stack ОК после cfg merge; (e) service.task_add с unknown stack rejection; (f) tausik stack list показывает (custom); (g) malformed cfg.custom_stacks (не list, dict) graceful

## Plan

## Rollback

## Journal

- 2026-04-25T14:27:38Z [implementation] — AC verified: 1. project_types: DEFAULT_STACKS frozenset (renamed); VALID_STACKS = DEFAULT_STACKS alias; get_valid_stacks(cfg) merge с custom_stacks ✓ (TestDefaultStacks 3 + TestGetValidStacks 5 PASSED) 2. service_task validates через _load_stacks() (config-driven); custom stack принят ✓ (TestServiceTaskAdd 3 + TestServiceTaskUpdate 2 PASSED) 3. CLI parser: --stack без choices=, validation в service ✓ (parser updated) 4. STACK_GATE_MAP остаётся building только из DEFAULT_GATES (custom stacks → universal-only) ✓ 5. tausik stack list показывает is_custom marker; CLI рендерит '(custom)' ✓ (TestStackVisibility 3 + TestCliStackOutput PASSED) 6. CLAUDE.md: '20 значений' → актуально (25 default + custom_stacks инструкция) ✓ (test_claude_md_no_stale_count PASSED) 7. Backwards compat: 2079/2080 tests PASS (1 MCP cross-IDE parity test был broken — починен sync agents/cursor/mcp/) 8. MCP enum stack остаётся (advisory) — не блокирует custom stacks через service layer ✓ 9. Negative scenarios: malformed cfg.custom_stacks (str, dict, non-string entries) → graceful skip ✓ (TestGetValidStacks 3 PASSED); unknown stack → ServiceError с suggestion ✓ (test_unknown_stack_rejected_with_suggestion, test_stack_info_rejects_unknown PASSED) 10. service_validation.py extracted (load_stacks + update_enums) для filesize gate ✓ 11. Tests test_stacks_extensible.py 18/18 PASSED
