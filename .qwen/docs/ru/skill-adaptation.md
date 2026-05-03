[English](../en/skill-adaptation.md) | **Русский**

# Адаптация скиллов под TAUSIK

Это руководство объясняет, как сделать любой репозиторий скиллов совместимым с TAUSIK. Будь то Claude-native плагин, скилл для Cursor или разработка с нуля — следуйте этим шагам.

## Зачем адаптировать?

TAUSIK предоставляет:
- **Установка одной командой**: `tausik skill install <name>`
- **Кросс-IDE поддержка**: один скилл работает в Claude Code, Cursor, Windsurf, Codex
- **Управление зависимостями**: pip-пакеты устанавливаются в изолированный `.tausik/venv/`
- **Активация/деактивация**: загружайте только нужные скиллы — нулевая нагрузка на контекст для неактивных
- **Единый каталог**: `tausik skill list` показывает все доступные скиллы

Несовместимые репозитории получают чёткую ошибку:

```
Repository 'my-repo' is not TAUSIK-compatible (tausik-skills.json not found).
See docs/en/skill-adaptation.md for how to adapt a skill repo.
```

## Быстрый старт

1. Форкните репозиторий скилла
2. Добавьте `tausik-skills.json` в корень
3. Убедитесь, что у каждого скилла есть `SKILL.md` с frontmatter
4. Проверьте: `tausik skill repo add <url-вашего-форка>`

## Структура репозитория

Совместимый репозиторий скиллов выглядит так:

```
my-skills/
├── tausik-skills.json          # ОБЯЗАТЕЛЬНО — манифест (спецификация ниже)
├── jira/
│   ├── SKILL.md                # ОБЯЗАТЕЛЬНО — инструкции скилла
│   ├── references/             # опционально — дополнительная документация
│   │   └── api.md
│   ├── scripts/                # опционально — вспомогательные скрипты
│   │   └── create_issue.py
│   ├── data/                   # опционально — CSV, JSON данные
│   ├── templates/              # опционально — шаблоны кода
│   └── requirements.txt        # опционально — pip-зависимости (альтернатива "requires" в манифесте)
├── bitrix24/
│   ├── SKILL.md
│   └── ...
└── seo/
    ├── SKILL.md
    └── ...
```

## Спецификация tausik-skills.json

Это файл-манифест, делающий репозиторий совместимым с TAUSIK. Размещается в корне репозитория.

```json
{
  "format": "tausik-skills",
  "version": 1,
  "skills": {
    "jira": {
      "path": "jira/",
      "description": "Jira issue management — create, update, search issues",
      "triggers": ["jira", "sprint", "issues", "backlog"],
      "requires": ["jira-python>=3.0"]
    },
    "seo-audit": {
      "path": "seo/",
      "description": "SEO analysis and site audit",
      "triggers": ["SEO", "site audit", "meta tags"],
      "requires": []
    }
  }
}
```

### Поля верхнего уровня

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `format` | да | Должно быть `"tausik-skills"` |
| `version` | да | Версия манифеста, сейчас `1` |
| `skills` | да | Словарь определений скиллов |

### Поля записи скилла

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `path` | да | Относительный путь к директории скилла (должен заканчиваться на `/`) |
| `description` | да | Однострочное описание (показывается в `skill list`) |
| `triggers` | нет | Ключевые слова для автопредложений агента |
| `requires` | нет | pip-пакеты для установки (например `["httpx>=0.27", "jira-python"]`) |

## Формат SKILL.md

Каждый скилл должен иметь `SKILL.md` с YAML frontmatter:

```markdown
---
name: jira
description: "Jira issue management — create, update, search issues via REST API"
---

# /jira — Jira Integration

## Algorithm

1. Check if JIRA_URL and JIRA_TOKEN are set
2. ...

## Examples

...
```

### Поля frontmatter

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `name` | да | Идентификатор скилла (kebab-case, например `seo-audit`) |
| `description` | да | Однострочное описание |

Тело SKILL.md содержит инструкции для ИИ-агента. Пишите на английском для лучшего понимания всеми ИИ-моделями.

## Адаптация скриптов

Скиллы могут включать вспомогательные скрипты в директории `scripts/`.

### Python-скрипты

```
my-skill/
  scripts/
    fetch_data.py
    process.py
```

**Важно для кросс-IDE совместимости:**
- Используйте `#!/usr/bin/env python3` shebang
- Скрипты должны быть автономными — импорт только из stdlib или пакетов из `requires`
- Не используйте пути `.claude/` — используйте относительные пути от расположения скрипта
- Предпочитайте Python вместо Bash для кроссплатформенности (поддержка Windows)

### Bash-скрипты

Bash работает на macOS/Linux, но **не нативно на Windows**. Если скилл для всех платформ:
- Предоставьте Python-альтернативы, или
- Укажите в документации, что скилл требует WSL/Git Bash на Windows

## Адаптация хуков

Хуки Claude Code **специфичны для IDE** и **не устанавливаются автоматически** TAUSIK.

Если исходный репозиторий содержит хуки (например security-guardian):
- **Не включайте** их в директорию скилла
- Задокументируйте в SKILL.md в секции "Hooks"
- Пользователи могут установить хуки вручную, скопировав в `.claude/hooks/`

**Почему?** TAUSIK имеет свои хуки (task_gate, bash_firewall и др.). Сторонние хуки могут конфликтовать, вызывая блокировку операций.

### Если хотите предоставить хуки

Создайте отдельную директорию `hooks/` в корне репозитория (не внутри скилла) и задокументируйте установку:

```markdown
## Опциональные хуки

Репозиторий включает опциональные хуки для Claude Code в `hooks/`.
Для ручной установки:

1. Скопируйте `hooks/my-hook/` в `.claude/hooks/` вашего проекта
2. Добавьте конфигурацию хука в `.claude/settings.json`
3. Проверьте, что нет конфликтов с существующими хуками
```

## Адаптация MCP-серверов

Если исходный скилл имеет свой MCP-сервер:

1. Разместите код сервера в `scripts/` или `mcp/` поддиректории скилла
2. Задокументируйте настройку в SKILL.md
3. Добавьте pip-зависимости в `requires` манифеста
4. Пользователям нужно будет вручную добавить сервер в `.mcp.json`

**Пример секции в SKILL.md:**

```markdown
## Настройка MCP-сервера

Скилл включает MCP-сервер для доступа к данным в реальном времени.
После установки добавьте в `.mcp.json`:

\```json
{
  "mcpServers": {
    "my-skill-mcp": {
      "command": ".tausik/venv/bin/python",
      "args": [".claude/skills/my-skill/mcp/server.py"]
    }
  }
}
\```
```

## Управление зависимостями

### pip-пакеты

Укажите зависимости в поле `requires` файла `tausik-skills.json`:

```json
{
  "requires": ["httpx>=0.27", "beautifulsoup4>=4.12"]
}
```

TAUSIK автоматически устанавливает их в `.tausik/venv/` при `skill install`. Системный Python пользователя не модифицируется.

### npm и другие пакетные менеджеры

TAUSIK управляет только pip-зависимостями. Для npm или других менеджеров:
- Задокументируйте требование в SKILL.md
- Предоставьте скрипт настройки в `scripts/setup.sh` или `scripts/setup.py`

### Переменные окружения

Если скилл требует API-ключи или конфигурацию:
- Включите файл `config/.env.example` с описанием необходимых переменных
- Задокументируйте настройку в SKILL.md
- **Никогда** не включайте реальные учётные данные в репозиторий

## Адаптация файлов данных

Скиллы могут включать файлы данных (CSV, JSON и т.д.) в директориях `data/` или `templates/`:

```
my-skill/
  data/
    styles.csv
    palettes.json
  templates/
    component.tsx.template
```

Они копируются как есть при установке. Ссылайтесь на них в SKILL.md по относительным путям.

## Примеры адаптации

### Пример 1: Claude-Native плагин (ui-ux-pro-max)

**Исходная структура:**
```
.claude/skills/design/SKILL.md
.claude/skills/ui-styling/SKILL.md
.claude-plugin/plugin.json
```

**Адаптированная структура:**
```
tausik-skills.json
design/SKILL.md
ui-styling/SKILL.md
```

**Шаги:**
1. Перенесите скиллы из `.claude/skills/` на корневой уровень
2. Создайте `tausik-skills.json` с перечнем скиллов
3. Удалите `.claude-plugin/` (специфично для Claude, не нужно)
4. Удалите `CLAUDE.md` (TAUSIK генерирует свой)

### Пример 2: Монорепозиторий плагинов (polyakov-claude-skills)

**Исходная структура:**
```
plugins/jira/skills/jira/SKILL.md
plugins/seo/skills/seo/SKILL.md
plugins/telegram/.claude-plugin/plugin.json
```

**Адаптированная структура:**
```
tausik-skills.json
jira/SKILL.md
seo/SKILL.md
telegram/SKILL.md
```

**Шаги:**
1. Выровняйте: скопируйте `plugins/{name}/skills/{name}/` в `{name}/`
2. Включите `scripts/`, `references/`, `data/` из каждого плагина
3. Создайте `tausik-skills.json` со всеми скиллами
4. Пропустите `hooks/` и `.claude-plugin/`
5. Добавьте pip-зависимости каждого плагина в `requires`

### Пример 3: Простой одиночный скилл

**Исходная структура:**
```
SKILL.md
scripts/run.py
```

**Адаптированная:**
```
tausik-skills.json
my-skill/
  SKILL.md
  scripts/run.py
```

Оберните скилл в именованную директорию и создайте манифест.

## Тестирование адаптированного репозитория

```bash
# 1. Запушьте форк на GitHub
git push origin main

# 2. В любом проекте с TAUSIK добавьте репозиторий
.tausik/tausik skill repo add https://github.com/you/my-adapted-skills

# 3. Проверьте распознавание
.tausik/tausik skill repo list

# 4. Установите скилл
.tausik/tausik skill install my-skill

# 5. Проверьте наличие
.tausik/tausik skill list

# 6. Активируйте и проверьте в IDE
# Перезапустите IDE для загрузки нового скилла
```

## Чек-лист

- [ ] `tausik-skills.json` в корне репозитория с `"format": "tausik-skills"`
- [ ] У каждого скилла своя директория с `SKILL.md`
- [ ] `SKILL.md` содержит YAML frontmatter (`name`, `description`)
- [ ] Тело `SKILL.md` на английском (лучшее понимание агентами)
- [ ] Скрипты используют `#!/usr/bin/env python3` shebang
- [ ] pip-зависимости указаны в массиве `requires`
- [ ] Нет хуков в директориях скиллов (документируйте отдельно)
- [ ] Нет `.claude-plugin/`, `CLAUDE.md` или IDE-специфичных файлов в директориях скиллов
- [ ] API-ключи задокументированы в `.env.example`, не захардкожены
- [ ] Проверено через `tausik skill repo add` + `tausik skill install`
