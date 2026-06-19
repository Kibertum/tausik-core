# Стратегии разрешений

## Расположение файлов разрешений

```
~/.claude/settings.json           # Глобальные настройки по умолчанию
.claude/settings.local.json       # Настройки проекта (gitignored)
```

## Структура разрешений

```json
{
  "permissions": {
    "allow": [],
    "deny": [],
    "ask": [],
    "defaultMode": "ask"
  }
}
```

## Режимы по умолчанию

| Режим | Поведение |
|------|----------|
| `"ask"` | Запрашивать подтверждение для всего, чего нет в allow/deny |
| `"acceptEdits"` | Автоматически одобрять правки файлов, спрашивать про bash |
| `"full"` | Полное доверие (используйте с осторожностью) |

## Синтаксис паттернов разрешений

```
Tool(command:args)
Tool(pattern:*)      # Wildcard
```

Примеры:
```json
"Bash(npm install:*)"        // Любой npm install
"Bash(git status:*)"         // Только git status
"Read(./.env)"               // Конкретный файл
"Read(**/*.md)"              // Glob-паттерн
```

## Рекомендуемая конфигурация

```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(npm:*)",
      "Bash(pnpm:*)",
      "Bash(pip:*)",
      "Bash(pytest:*)",
      "Bash(ls:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(rm -r:*)",
      "Bash(sudo:*)",
      "Bash(git push --force:*)",
      "Bash(git reset --hard:*)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(~/.ssh/**)"
    ],
    "ask": [
      "Bash(git commit:*)",
      "Bash(git push:*)",
      "Bash(docker:*)",
      "Bash(rm:*)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

## Категории разрешений

### Безопасно разрешать

```json
[
  "Edit",
  "Write",
  "Bash(git status:*)",
  "Bash(git diff:*)",
  "Bash(git log:*)",
  "Bash(npm:*)",
  "Bash(pip:*)",
  "Bash(ls:*)",
  "Bash(cat:*)"
]
```

### Всегда запрещать

```json
[
  "Bash(rm -rf:*)",
  "Bash(rm -r:*)",
  "Bash(sudo:*)",
  "Bash(git push --force:*)",
  "Bash(git reset --hard:*)",
  "Read(./.env)",
  "Read(~/.ssh/**)",
  "Read(~/.aws/**)"
]
```

### Требуют подтверждения

```json
[
  "Bash(git commit:*)",
  "Bash(git push:*)",
  "Bash(docker:*)",
  "Bash(rm:*)"
]
```

## Лучшие практики

1. **Начинайте со строгих ограничений** — добавляйте разрешения по мере необходимости
2. **Запрещайте секреты** — никогда не разрешайте автоматическое чтение чувствительных файлов
3. **Спрашивайте про git-записи** — проверяйте коммиты до их создания
4. **Аккуратно используйте wildcards** — `Bash(*)` слишком широкий
5. **Gitignore локальные настройки** — держите `.claude/settings.local.json` вне репозитория
