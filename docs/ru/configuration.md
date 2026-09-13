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

## Файлы инструкций агента (блок DYNAMIC)

`tausik update-claudemd` переписывает блок между `<!-- DYNAMIC:START -->` и
`<!-- DYNAMIC:END -->` в CLAUDE.md и, если он лежит рядом, в AGENTS.md.
AGENTS.md в большинстве проектов версионируется, поэтому его содержимое —
политика, а не случайность (GitLab #14):

| Ключ | Умолчание | Назначение |
|---|---|---|
| `claudemd.sibling_dynamic` | `true` | `true`: AGENTS.md обновляется блоком **без** «Shared knowledge — from other projects» — знания чужих проектов не попадают в историю этого репозитория, а хвост памяти, под которым ничего не осталось, опускается. `false`: AGENTS.md не пишется вовсе; CLAUDE.md обновляется как раньше. Выключает только JSON-булево `false` — строка `"false"` или `0` читаются как «включено». Ключ читается из `.tausik/` рядом с записываемым файлом. |

Гейт коммита `claudemd_state` судит каждый файл по тому же плану, которому
следует писатель: сиблинг, который политика не пишет, не судится, а сиблинг,
чьё единственное знание было бы чужим, хвоста не должен.

## Публикация (что скрывает вычищенный экспорт)

Общее хранилище (`~/.tausik-knowledge`) не требует настройки: `--global` у
`decide` / `memory add` пишет в него, `$TAUSIK_HOME` переносит. Эти ключи читает
только `knowledge export --redacted` (см. [knowledge-store.md](knowledge-store.md)).

| Ключ | Дефолт | Назначение |
|---|---|---|
| `publication.project_names` | `[]` | Имена проектов, заменяемые на `[REDACTED:project]`, в дополнение к имени каталога этого проекта. |
| `publication.private_url_patterns` | `[]` | Regex-строки; URL, подходящий под одну из них, становится `[REDACTED:url]`. |
| `brain.local_mirror_path` | `~/.tausik-brain/brain.db` | Читается только разовым `knowledge import-brain`: где отставленный транспорт Notion оставил локальное зеркало. |

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
  "publication": {
    "project_names": ["acme"],
    "private_url_patterns": ["acme\\.internal"]
  },
  "claudemd": { "sibling_dynamic": false }
}
```

## Health check

`tausik doctor` (v1.3+) проверяет согласованность config + venv + DB + skills и выдаёт actionable next steps.
