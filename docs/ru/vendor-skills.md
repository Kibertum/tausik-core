[English](../en/vendor-skills.md) | **Русский**

# Пользовательские навыки

TAUSIK поддерживает внешние пакеты навыков из GitHub-репозиториев. Навыки клонируются один раз, кешируются в `.tausik/vendor/` и устанавливаются по запросу с автоматическим управлением зависимостями.

## Быстрый старт

```bash
# 1. Добавить репозиторий навыков
.tausik/tausik skill repo add https://github.com/Kibertum/tausik-skills

# 2. Установить навык (копирует файлы + ставит pip-зависимости)
.tausik/tausik skill install jira

# 3. Перезапустить IDE для загрузки нового навыка
```

Одна команда — один навык — один перезапуск.

## Управление репозиториями

### Добавление

```bash
# TAUSIK-совместимые репозитории (содержат tausik-skills.json)
.tausik/tausik skill repo add https://github.com/Kibertum/tausik-skills

# Посмотреть что доступно
.tausik/tausik skill repo list
```

### Удаление

```bash
.tausik/tausik skill repo remove tausik-skills
```

### Репозитории по умолчанию

TAUSIK поставляется с `Kibertum/tausik-skills` как предустановленным репозиторием. Используйте `skill repo list` для просмотра.

## Установка и удаление навыков

```bash
# Установить: клонировать репо (если нужно) → скопировать навык → установить pip-зависимости
.tausik/tausik skill install jira

# Удалить: убрать файлы и запись в конфигурации
.tausik/tausik skill uninstall jira

# Список: активные, установленные и доступные из репозиториев
.tausik/tausik skill list
```

### MCP-инструменты (для ИИ-агентов)

```
tausik_skill_repo_add     — добавить репозиторий
tausik_skill_repo_remove  — удалить репозиторий
tausik_skill_repo_list    — список репозиториев и их навыков
tausik_skill_install      — установить навык
tausik_skill_uninstall    — удалить навык
tausik_skill_list         — список всех навыков (активные + установленные + доступные)
tausik_skill_activate     — активировать установленный навык
tausik_skill_deactivate   — деактивировать (выгрузить из контекста)
```

## Трёхуровневая система навыков

Навыки живут на трёх уровнях — от «готов к использованию» до «ещё не скачан»:

| Уровень | Расположение | В контексте агента? | Как использовать |
|---------|-------------|---------------------|------------------|
| **Активный** | `.{ide}/skills/` | Да — загружается каждый разговор | Используется автоматически |
| **Установленный** | `.tausik/vendor/` | Нет — на диске, нулевая нагрузка | `skill activate <name>` |
| **Доступный** | В репо, ещё не скачан | Нет — не загружен | `skill repo add` + `skill install` |

**Зачем три уровня?** Активные навыки расходуют контекст агента. Если активировать 50 навыков, агенту останется меньше места для кода. Держите активными только ежедневные навыки; установленные — в одной команде от активации.

## Как это работает

```
skill repo add <url>
      ↓
git clone --depth 1 → .tausik/vendor/{repo}/
      ↓
skill install <name>
      ↓
копирование в .{ide}/skills/{name}/ + pip install зависимостей
      ↓
Активен (загружен в контекст агента)
```

### Активация / Деактивация (без переустановки)

```bash
# Убрать из контекста (файлы остаются в vendor)
.tausik/tausik skill deactivate jira

# Загрузить обратно в контекст
.tausik/tausik skill activate jira
```

## Формат tausik-skills.json

TAUSIK-совместимые репозитории должны содержать `tausik-skills.json` в корне:

```json
{
  "format": "tausik-skills",
  "version": 1,
  "skills": {
    "jira": {
      "path": "jira/",
      "description": "Jira issue management",
      "triggers": ["jira", "sprint", "issues"],
      "requires": ["jira-python>=3.0"]
    }
  }
}
```

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `format` | Да | Должно быть `"tausik-skills"` |
| `version` | Да | Версия манифеста (`1`) |
| `skills.{name}.path` | Да | Относительный путь к каталогу навыка |
| `skills.{name}.description` | Да | Однострочное описание |
| `skills.{name}.triggers` | Нет | Ключевые слова для автопредложений |
| `skills.{name}.requires` | Нет | pip-пакеты (устанавливаются в `.tausik/venv/`) |

Для репозиториев в другом формате см. [Руководство по адаптации](skill-adaptation.md).

## Зависимости

pip-зависимости из поля `requires` автоматически устанавливаются в `.tausik/venv/` при `skill install`. Системный Python не модифицируется.

```bash
# Пример: установка навыка с зависимостями
.tausik/tausik skill install jira
# → Копирует jira/ в .claude/skills/jira/
# → pip install jira-python>=3.0 в .tausik/venv/
```

## Безопасность

- Репозитории клонируются по HTTPS с валидацией URL
- Защита от обхода путей при копировании
- Предупреждение о pip-зависимостях из внешних манифестов
- Хуки из внешних репозиториев не устанавливаются автоматически
- Вендорные скрипты изолированы для предотвращения перезаписи ядра

## Legacy: skills.json + bootstrap

Старый механизм через `skills.json` + `bootstrap --update-deps` продолжает работать для обратной совместимости. Формат см. в `skills.example.json`. Для новых проектов рекомендуется `skill repo add` + `skill install`.
