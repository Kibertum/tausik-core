---
slug: host-dobavlyaemyy-v-scaffold-ides-proveryaetsya-zamerom
title: "Хост, добавляемый в SCAFFOLD_IDES, проверяется ЗАМЕРОМ БИНАРЯ, а не документацией"
type: convention
tags: []
task: claude-and-codex-coexist-and-it-is-pinned
edges: []
---

Строки в исполняемом файле хоста отвечают на вопросы, на которые документация отвечает устаревше. Замер Codex в смене #241: grep по codex.exe дал hooks.json, .codex/hooks, .codex/config.toml, .codex/skills, .codex/agents, AGENTS.md, SKILL.md, PreToolUse, PostToolUse, SessionStart, SessionEnd, UserPromptSubmit, Stop, PreCompact, Notification, SubagentStop, hook_event_name, hookSpecificOutput, permissionDecision — и НЕ дал CLAUDE_PROJECT_DIR, CODEX_PROJECT_ROOT, workspaceFolder, CODEX_WORKSPACE. Первый список опроверг тикет, утверждавший, что у Codex нет API хуков; второй объяснил, почему лежавший в проекте .codex/hooks.json был мёртв. ОТРИЦАТЕЛЬНЫЙ результат тут ценнее положительного: отсутствие переменной определяет ФОРМУ пути в каждой команде, а узнать о нём иначе можно только по тому, что гейты молча не срабатывают.
