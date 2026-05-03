[English](../en/roles.md) | **Русский**

# Роли

Роли описывают **кто** делает работу. Они влияют на маршрутизацию задач, рекомендации skill'ов и профиль агента, который инжектится при старте задачи.

В TAUSIK роли — **свободный текст** в задачах (`task add ... --role developer`), опционально подкреплённый **реестром**, который связывает SQLite-метаданные с markdown-профилем.

## Модель хранения — гибридная

| Слой | Где | Что |
|------|-----|-----|
| Метаданные | таблица `roles` в `.tausik/tausik.db` | slug, title, description, base/extends |
| Профиль | `agents/roles/{slug}.md` | Behavioural-промпт, который агент читает при claim'е задачи с этой ролью |

Роль может существовать в каждом слое независимо. `role list` мерджит обе view, помечая записи как **registered** (DB), **profile-only** (markdown без DB-row), или **db-only** (DB-row без профиля).

Не нужно регистрировать роль перед назначением — `--role qa-lead` работает независимо от того, есть ли `qa-lead` в реестре. Реестр существует, чтобы централизовать профили и сидить дефолты по командам.

## Дефолтные профили

После bootstrap в `agents/roles/` есть пять дефолтных профилей:

- `architect.md` — системный дизайн, trade-off'ы, ADR
- `developer.md` — реализация, рефакторинг, дебаг
- `qa.md` — тест-дизайн, coverage, fake-test detection
- `tech-writer.md` — документация, parity, примеры
- `ui-ux.md` — interaction design, accessibility, microcopy

Запустите `tausik role seed`, чтобы сидить строки в БД из этих markdown-файлов плюс из имён ролей, уже использованных на задачах.

## CLI

```bash
role list                                    # список ролей (DB + profile-only)
role show <slug>                             # запись + путь к профилю
role create <slug> <title> [--description T] [--extends BASE_ROLE]
role update <slug> [--title T] [--description D]
role delete <slug>
role seed                                    # bootstrap из agents/roles/*.md + использования в задачах
```

`--extends` клонирует профиль из базовой роли. Например:

```bash
.tausik/tausik role create senior-dev "Senior Developer" --extends developer
```

Это копирует `agents/roles/developer.md` в `agents/roles/senior-dev.md`, чтобы вы могли его доработать. DB-row отслеживает связь `extends`.

## MCP

| Инструмент | Описание |
|------|---------|
| `tausik_role_list` | Список ролей |
| `tausik_role_show` | Запись + путь к профилю |
| `tausik_role_create` | Создать роль (опционально extends базовую) |
| `tausik_role_update` | Обновить title/description |
| `tausik_role_delete` | Удалить DB-row (файл профиля сохраняется) |
| `tausik_role_seed` | Bootstrap из `agents/roles/*.md` + значений `role` в задачах |

## Типичные паттерны

**Добавить domain-specific роль для вертикали**

```bash
.tausik/tausik role create payment-engineer "Payment Engineer" \
  --description "PCI-DSS-aware backend dev with strong audit/security instincts" \
  --extends developer
```

**Использовать роль в задаче**

```bash
.tausik/tausik task add "Refund flow webhook" --story payments \
  --slug refund-webhook --role payment-engineer --stack go --complexity medium
```

**Фильтровать backlog**

```bash
.tausik/tausik task list --role qa --status active
```

## Negative cases

- Роли **не** ограничены фиксированным enum'ом. Любая строка принимается на `--role`. Валидатор не отвергает незарегистрированные роли.
- `role delete` **не** удаляет `agents/roles/{slug}.md`. Профиль сохраняется, чтобы можно было пересидить позже. Чтобы удалить файл — удалите вручную.
- `role seed` **идемпотентна**: повторный запуск не дублирует строки.

## См. также

- [CLI команды](cli.md) — `task add --role`, `task list --role`
- [MCP инструменты](mcp.md) — программный surface для управления ролями
- [Skills](skills.md) — skill'ы могут читать профили ролей для адаптации поведения
