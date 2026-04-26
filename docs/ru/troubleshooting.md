[English](../en/troubleshooting.md) | **Русский**

# Troubleshooting

> Машино-читаемый гайд: ошибка → диагноз → фикс.

## Bootstrap

| Симптом | Диагноз | Фикс |
|---|---|---|
| `python: command not found` | Python не в PATH | Установи Python 3.11+, проверь `python --version` |
| `Bootstrap halts on .claude/ write` | Read-only FS | Mount `.tausik/` writable; bootstrap пишет и в `.claude/` |
| Bootstrap "Skills: 0 copied" | `agents/skills/` пуст | Pull актуальный source, проверь `ls agents/skills/` |
| Bootstrap занимает >60s на Windows | Antivirus сканирует каждый файл | Исключи `.claude/` и `.tausik/` из real-time scan |

## CLI / MCP

| Симптом | Диагноз | Фикс |
|---|---|---|
| `tausik task done` зависает >10s | Quality gate гонит full pytest без relevant_files | Передай `--relevant-files <path>` или Story 4 fix уже применён |
| MCP tool returns stale data | MCP server cached старые scripts/* модули | Restart Claude Code session (re-bootstrap не помогает) |
| `tausik doctor` reports drift | Source `scripts/` отличается от `.claude/scripts/` | Re-run `python bootstrap/bootstrap.py --ide claude` |
| `Memory #N not found` | Не указано в какой DB | Сейчас всегда project DB; brain — отдельная команда `tausik brain show` |

## Brain

| Симптом | Диагноз | Фикс |
|---|---|---|
| `brain disabled` warning | `brain.enabled=false` в config | `tausik brain init` для wizard setup |
| `Notion auth failed` | Token env var не установлена | Проверь имя env-переменной в `brain.notion_integration_token_env` |
| Brain mirror огромный | WAL не checkpoint'ится | `PRAGMA wal_checkpoint(TRUNCATE)` или удали `.tausik-brain/mirror.db-wal` |

## Hooks

| Симптом | Диагноз | Фикс |
|---|---|---|
| Hook не срабатывает | TAUSIK_SKIP_HOOKS установлено | Проверь env, удали переменную |
| `git push` blocked | Защитный gate сработал — это нормально | Используй `/ship` или `/commit` skills, либо `TAUSIK_ALLOW_PUSH=1` единоразово |
| Memory write blocked | Попытка записи в `~/.claude/projects/*/memory/` | Если действительно нужен cross-project memory — добавь маркер `confirm: cross-project` |
