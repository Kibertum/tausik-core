[English](../en/configuration.md) | **Русский**

# Справочник конфигурации TAUSIK

Все настройки в `.tausik/config.json` в корне проекта. Что не указано — берёт документированный дефолт. Override — добавь ключ в top-level объект (НЕ под `bootstrap` — там bootstrap управляет).

См. также: [environment.md](environment.md) — env-переменные, [permissions.md](../en/permissions.md) — режимы permissions.

## Лимиты сессии (SENAR Rule 9.2)

| Ключ | Дефолт | Назначение |
|---|---|---|
| `session_max_minutes` | `180` | Жёсткий лимит АКТИВНЫХ минут сессии до блокировки `task start`. Продление: `tausik session extend --minutes N`. |
| `session_idle_threshold_minutes` | `10` | Промежуток (в минутах), после которого пауза считается AFK и исключается из active-time. |
| `session_warn_threshold_minutes` | `150` | Порог напоминания stop-хука в `session_cleanup_check.py`. Должен быть < `session_max_minutes`. |
| `session_capacity_calls` | `200` | Бюджет tool-calls на сессию. `task start` блокируется если remaining < task `call_budget`. |

## Кэш верификации (SENAR Rule 5)

| Ключ | Дефолт | Назначение |
|---|---|---|
| `verify_cache_ttl_seconds` | `600` | Сколько секунд зелёный verify-run переиспользуется до перезапуска gates. Уменьши для security-critical проектов. |

## Стеки

| Ключ | Дефолт | Назначение |
|---|---|---|
| `custom_stacks` | `[]` | Список custom stack slug'ов, принимаемых `task add --stack X`. |

## Gates

| Ключ | Дефолт | Назначение |
|---|---|---|
| `gates` | `{}` | Per-gate overrides: `{ "pytest": { "enabled": true }, "filesize": { "max_lines": 600 } }`. Мержится поверх `default_gates.py`. |

## Brain (общая база знаний)

| Ключ | Дефолт | Назначение |
|---|---|---|
| `brain.enabled` | `false` | Master switch для cross-project Notion brain. |
| `brain.local_mirror_path` | `~/.tausik-brain/mirror.db` | Локальный SQLite mirror Notion-баз. Тильда + `$ENV` раскрываются. |
| `brain.notion_integration_token_env` | `TAUSIK_BRAIN_TOKEN` | Имя env-переменной с Notion integration token. |
| `brain.database_ids` | `{}` | Notion DB ID'ы. Заполняются wizard'ом `tausik brain init`. |
| `brain.private_url_patterns` | `[]` | Regex-паттерны URL для scrub'инга перед записью в brain. |
| `brain.project_names_blocklist` | `[]` | Подстроки имён проектов для scrub'инга. |

## Пример

```json
{
  "session_max_minutes": 240,
  "session_idle_threshold_minutes": 15,
  "verify_cache_ttl_seconds": 1200,
  "custom_stacks": ["ruby", "elixir"],
  "gates": {
    "filesize": { "max_lines": 500 },
    "ruff": { "enabled": false }
  },
  "brain": {
    "enabled": true,
    "notion_integration_token_env": "TAUSIK_BRAIN_TOKEN"
  }
}
```

## Health check

`tausik doctor` (v1.3+) проверяет согласованность config + venv + DB + skills и выдаёт actionable next steps.
