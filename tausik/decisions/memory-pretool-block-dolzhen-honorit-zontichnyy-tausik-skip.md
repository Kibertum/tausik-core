---
slug: memory-pretool-block-dolzhen-honorit-zontichnyy-tausik-skip
task: memory-pretool-block-skip-toggle-and-docstring
date: "2026-07-21"
edges: []
---

## Decision

memory_pretool_block ДОЛЖЕН honorить зонтичный TAUSIK_SKIP_HOOKS в дополнение к специфичному TAUSIK_SKIP_MEMORY_HOOK, а не игнорировать его.

## Rationale

«Защита» кросс-проектной памяти через игнор зонтичного флага иллюзорна: агент, способный выставить env TAUSIK_SKIP_HOOKS, точно так же выставит TAUSIK_SKIP_MEMORY_HOOK — специфичный флаг уже был необлагаемым обходом. Реальная защита по тезису релиза 1.8 — не выбор флага, а НАБЛЮДАЕМОСТЬ каждого обхода. Игнор зонтика также ломал контракт suite: все прочие хуки (task_gate, scope_write_gate, task_done_verify, git_push_gate, task_cost_budget_check) honorят TAUSIK_SKIP_HOOKS — memory-хук был единственным исключением, что нарушает принцип наименьшего удивления и делал docstring ложным. Решение: honor оба флага, каждый эмитит различимый supervision-vector (skip_hooks / skip_memory_hook), docstring приводится к правде.
