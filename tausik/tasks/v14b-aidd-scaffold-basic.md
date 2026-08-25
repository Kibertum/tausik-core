---
slug: v14b-aidd-scaffold-basic
title: "AIDD project scaffold — tausik project init --template aidd"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "agents/aidd-templates/idea.md (NEW), agents/aidd-templates/vision.md (NEW), agents/aidd-templates/conventions.md (NEW), scripts/project_parser.py (extend init subparser), scripts/project_cli.py (extend cmd_init), scripts/project_cli_aidd.py (NEW — handler for aidd template), tests/test_aidd_scaffold.py (NEW), docs/en/cli.md, docs/ru/cli.md"
scope_exclude: "harness/* path (rename task v14b-rename-harness will move agents/→harness/ later — do not preempt)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T14:40:49Z"
---

## Goal

tausik project init --template aidd creates idea.md/vision.md/conventions.md in user project with safe conflict detection (4-option prompt, default skip). v1.5 TODO entries documented for autogen + AI-validation extensions.

## Acceptance Criteria

1. CLI `tausik init --template aidd` creates idea.md, vision.md, conventions.md from templates in user project root. 2. Conflict detection: existing files enumerated; user prompted with 4 options (overwrite/merge-append/skip/abort-all); default = skip with warning. 3. `--force` flag overwrites without prompt. 4. Templates ship under agents/aidd-templates/ (post-rename: harness/aidd-templates/); copied verbatim. 5. v1.5 TODO entries appended to v15-cross-ide-parity epic OR new epic for AIDD-extension (autogen of vision.md from existing code, AI-validation drift). 6. Tests: 4 scenarios — clean dir, partial conflict, full conflict default-skip, --force overwrites. 7. docs/en/cli.md + docs/ru/cli.md document the command. 8. Negative: when --template gets an unknown value (e.g. `--template bogus`), CLI prints "Unknown template: bogus" to stderr and exits non-zero — does not silently fall through to plain init. 9. Negative: when interactive prompt receives empty input (Enter only), default action is skip and a warning is logged.

## Plan

[{"step": "Create harness/aidd-templates/ with idea.md, vision.md, conventions.md template stubs (post-rename path)", "done": true}, {"step": "Add CLI subcommand `tausik project init --template aidd` to scripts/project.py / scripts/project_parser.py", "done": true}, {"step": "Implement conflict detection \u2014 enumerate existing files, present 4-option prompt", "done": true}, {"step": "Implement actions: overwrite / merge-append / skip / abort-all; default = skip with warning", "done": true}, {"step": "Add --force flag for non-interactive overwrite", "done": true}, {"step": "v1.5 TODO: append to v15-cross-ide-parity epic \u2014 add stories for AIDD-autogen + AIDD-AI-validation", "done": true}, {"step": "Tests: 4 scenarios (clean dir, partial conflict, full conflict default-skip, --force overwrites)", "done": true}, {"step": "docs/en/cli.md + docs/ru/cli.md document the command", "done": true}]

## Rollback

## Journal

- 2026-05-04T14:40:43Z [implementation] — AC verified: 1. ✓ tausik init --template aidd creates idea.md/vision.md/conventions.md (test_clean_dir_creates_all_three; smoke-tested via python scripts/project.py init --template aidd in tmp dir → 3 files written) 2. ✓ 4-option prompt with default skip (test_partial_conflict_default_skip_keeps_existing, test_full_conflict_default_skip_keeps_all_existing; _resolve_choice maps empty→skip) 3. ✓ --force overwrites without prompt (test_force_overwrites_without_prompt — asserts prompt callable not invoked) 4. ✓ Templates in agents/aidd-templates/ (will be renamed harness/aidd-templates by v14b-rename-harness — find_templates_dir already looks at both paths) 5. ✓ v1.5 stories created: v15-aidd-autogen + v15-aidd-ai-validation under v15-cross-ide-parity epic 6. ✓ 4+ scenarios covered: clean dir, partial conflict default-skip, full conflict default-skip, --force overwrites; plus overwrite/merge-append/abort-all explicit choices = 7 scaffold scenarios total (14 tests counting unit + CLI) 7. ✓ docs/en/cli.md + docs/ru/cli.md document the command (init --template aidd block with [--force] + conflict-prompt semantics) 8. ✓ Negative: unknown --template value → exit 2 + stderr "Unknown template: bogus" (test_unknown_template_returns_2; verified via cmd_init_template("bogus")) 9. ✓ Negative: empty prompt input → skip with warning (test_partial_conflict_default_skip_keeps_existing uses prompt=lambda _: ""; "Conflict: vision.md" log assertion) Tests: 14/14 pass; mypy clean on scripts/project_cli_aidd.py + project_cli.py + project_parser.py (only pre-existing brain_classifier.py memory_markers import error remains, unrelated). Filesizes: 174/176 lines (under 400 gate).
