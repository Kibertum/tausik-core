---
slug: migrate-python-family
title: "Migrate python/fastapi/django/flask to stack.json"
status: done
epic: v16-plugin-arch-and-docs
story: migrate-builtins
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "stacks/{python,fastapi,django,flask}/* (NEW), agents/stacks/{python,fastapi,django,flask}.md (DELETE/move)"
scope_exclude: "scripts/* (consumers refactored в Story 3), bootstrap_config.py (Story 3), default_gates.py (Story 3)"
relevant_files:
  - "stacks/python/stack.json"
  - "stacks/python/guide.md"
  - "stacks/fastapi/stack.json"
  - "stacks/fastapi/guide.md"
  - "stacks/django/stack.json"
  - "stacks/django/guide.md"
  - "stacks/flask/stack.json"
  - "stacks/flask/guide.md"
  - "bootstrap/bootstrap_copy.py"
  - "bootstrap/bootstrap_stacks.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:44:44Z"
---

## Goal

Create stacks/{python,fastapi,django,flask}/stack.json + guide.md per stack. Migrate signatures from STACK_SIGNATURES, gates (pytest/ruff/mypy/bandit) from DEFAULT_GATES with their stacks: ['python',...] filter. Move agents/stacks/{python,fastapi,django,flask}.md → stacks/<name>/guide.md. Tests must pass.

## Acceptance Criteria

1. stacks/python/stack.json + guide.md созданы. detect=[pyproject.toml exact, requirements.txt exact, setup.py exact]; extensions=[.py]; gates с pytest/ruff/mypy/bandit из DEFAULT_GATES (только те что фильтруются по 'python').
2. stacks/fastapi/stack.json + guide.md. detect=[requirements.txt+fastapi keyword, pyproject.toml+fastapi keyword]; extensions=[.py]; гейты наследует от python (или дублирует — выберу подход в коде).
3. stacks/django/stack.json + guide.md. detect=[manage.py exact, requirements.txt+django keyword]; extensions=[.py]; гейты как у python.
4. stacks/flask/stack.json + guide.md. detect=[requirements.txt+flask keyword, pyproject.toml+flask keyword]; extensions=[.py]; гейты как у python.
5. agents/stacks/{python,fastapi,django,flask}.md перемещены в stacks/<name>/guide.md (или скопированы и удалены из agents/stacks/).
6. StackRegistry().load_builtin(stacks/) — все 4 загружаются, errors=[]; проверочный smoke-тест в bash.
7. pytest tests/test_stack_registry.py + tests/test_gates.py → 0 регрессий.
8. Все JSON-файлы валидны (json.load), schema-валидны (validate_decl возвращает []).

## Plan

## Rollback

## Journal

- 2026-04-25T16:43:44Z [implementation] — Расширил scope: bootstrap_copy.copy_stacks обновлён под новый layout (stacks/<name>/{stack.json, guide.md}) с fallback на legacy agents/stacks/<name>.md для незамигрированных стэков. Так бутстрап работает с partial-migration состоянием. Также копирует stacks/_schema.json для validate_decl. AC verified: 1. ✓ stacks/python/{stack.json, guide.md} созданы, гейт pytest со stacks=[python,fastapi,django,flask] под python (single source of truth). 2. ✓ stacks/fastapi/{stack.json, guide.md}; detect=requirements.txt+fastapi keyword; ext=[.py]; gates наследует через 'stacks' field на pytest. 3. ✓ stacks/django/* idem (detect=manage.py + requirements.txt+django). 4. ✓ stacks/flask/* idem (detect=requirements.txt+flask + pyproject.toml+flask). 5. ✓ agents/stacks/{python,fastapi,django,flask}.md перемещены в stacks/<name>/guide.md (mv). 6. ✓ StackRegistry.load_builtin('stacks') → all 4 загружаются errors=[]. 7. ✓ pytest tests/test_stack_registry.py + test_gates.py: 107 passed, 0 регрессий. 8. ✓ JSON-валидны, validate_decl возвращает [] для всех 4.
