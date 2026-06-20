# Спецификация скилла

Формальный контракт для файлов SKILL.md во фреймворке TAUSIK.

## Структура файла

Каждый скилл — это директория `skills/{name}/`, содержащая `SKILL.md`.

### Обязательный формат

```markdown
---
name: skill-name
description: "Trigger description for Claude Code skill discovery."
---

# /skill-name — Human Title

Brief description. Always respond in the user's language.

## Algorithm

### 1. First Step
Instructions...

### 2. Second Step
Instructions...
```

### Frontmatter (обязательно)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Kebab-case slug, совпадающий с именем директории |
| `description` | string | Список trigger-фраз для матчера скиллов Claude Code |

Поле `description` критично — Claude Code использует его, чтобы решить, когда вызывать скилл.
Включай trigger-фразы: "Use when user says 'X', 'Y', 'Z'."

### Секции тела

| Section | Required | Purpose |
|---------|----------|---------|
| `# /name — Title` | Yes | H1-заголовок со слэш-командой и человекочитаемым названием |
| `## Algorithm` | Yes | Пошаговые инструкции исполнения |
| `## Rules` | No | Ограничения и инварианты |
| `## Context` | No | Авто-загружаемые shell-данные (через префикс `!`) |

## Категории скиллов

Канонический список живёт в `.tausik/config.json` под `bootstrap.core_skills`
и `bootstrap.extension_skills`. По состоянию на v1.4:

| Category | Skills | Bootstrap Handling |
|----------|--------|--------------------|
| Core (11) | start, end, task, plan, checkpoint, commit, explore, review, test, ship, debug | Всегда копируются, не выбираемы |
| Core (условный) | brain | Копируется, когда настроен Notion (`brain.enabled = true`) |
| Extension | docs (и любые имена, добавленные под `bootstrap.extension_skills`) | Выбирается через `--include-official` или `tausik skill install <name>` |
| Vendor / bundle | 20 скиллов под `skills-official/registry.json`, сгруппированы в 6 бандлов | Подтягиваются per-skill или per-bundle через `tausik skill bundle install <name>` |

`init` был удалён в v1.4 (заменён на `python bootstrap/bootstrap.py --init`).
Пять legacy-скиллов `/go`, `/next`, `/diff`, `/onboard`, `/init` были удалены
в том же релизе — см. `skill-bundles-migration.md`.

## Соглашения

1. **Ссылки вместо инлайна**: большие таблицы и протоколы → выноси в соседний reference-файл внутри директории скилла и ссылайся на него
2. **Общие паттерны**: используй `skill-patterns.md` для кросс-скилловых паттернов (handoff, обновление CLAUDE.md и т.п.)
3. **CLI-справочник**: всегда ссылайся на `docs/en/cli.md` (или `docs/ru/cli.md`), никогда не дублируй CLI-синтаксис
4. **Параллельный батчинг**: явно помечай независимые tool calls для параллельного исполнения
5. **Бюджет токенов**: держи SKILL.md под 300 строк; выноси справочные данные в отдельные файлы
6. **Язык**: скиллы отвечают на языке пользователя (определяй из диалога)

## Создание нового скилла

1. Создай `harness/skills/my-skill/SKILL.md` по формату выше
2. Добавь slug в `.tausik/config.json` под `bootstrap.extension_skills`
   (или `bootstrap.core_skills` для всегда-разворачиваемых)
3. Запусти `python bootstrap/bootstrap.py`, чтобы скопировать в `.claude/skills/`
4. Claude Code обнаруживает его автоматически по наличию SKILL.md

### Шаблон

```markdown
---
name: my-skill
description: "Brief purpose. Use when user says 'trigger1', 'trigger2'."
---

# /my-skill — My Skill Title

One-line description. Always respond in the user's language.

**CLI Reference:** [`docs/ru/cli.md`](cli.md)

## Algorithm

### 1. Gather Context
Describe what to read/search before acting.

### 2. Execute
Core logic steps.

### 3. Output
What to show the user.

## Rules
- Rule 1
- Rule 2
```
