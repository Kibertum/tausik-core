---
slug: huki-geyty-komand-tokenizirovat-shlex-ne-matchit-podstroku
title: "Хуки-гейты команд: токенизировать (shlex), не матчить подстроку"
type: convention
tags: []
task: null
edges: []
---

PreToolUse-хуки, распознающие git-команды (git_push_gate и подобные), ДОЛЖНЫ токенизировать команду через shlex.split и искать подкоманду в позиции команды, а не regex по сырой строке. Иначе биграмма (напр. в git-публикации) в ТЕКСТЕ кавычечного аргумента (tausik task log/memory add с описанием процедуры) ложно матчится и блокирует легитимную команду. Кавычки-строка в shlex = один токен, поэтому упоминание внутри кавычек не распадается на токены-подкоманды. Fallback на regex при shlex ValueError (несбалансированные кавычки) — консервативно (блокировать). Реализация: scripts/hooks/git_push_gate.py::_command_invokes_git_push (сессия 2026-07-18). Тот же принцип применять к любому будущему command-matching гейту.
