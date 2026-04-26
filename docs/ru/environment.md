[English](../en/environment.md) | **Русский**

# Правила окружения

> Полный гайд по shell, virtualenv и Docker — на английском в [environment.md](../en/environment.md).

## Ключевые принципы

- **venv обязателен** — все зависимости TAUSIK ставятся в `.tausik/venv/` через bootstrap
- **Никогда не активируй venv shell-командой** — используй `.tausik/tausik` wrapper, он сам находит правильный python
- **Docker** — `.tausik/` нужен writable mount, остальное может быть read-only
- **CLAUDE_PROJECT_DIR** — env var, который должен указывать на корень проекта (Claude Code устанавливает автоматически)

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `CLAUDE_PROJECT_DIR` | Корень проекта (Claude Code) |
| `TAUSIK_BRAIN_TOKEN` | Notion integration token (или другой env по `notion_integration_token_env`) |
| `TAUSIK_ALLOW_PUSH=1` | Бypass git_push_gate (set by `/ship`/`/commit` после подтверждения) |
| `TAUSIK_SKIP_PUSH_HOOK=1` | Полный bypass push gate (debug) |
| `TAUSIK_SKIP_MEMORY_HOOK=1` | Bypass memory pretool block |
| `TAUSIK_E2E=1` | Включить тяжёлые e2e тесты |
| `PYTHONIOENCODING=utf-8` | Windows: предотвращает crash на Unicode выводе |
| `PYTHONUTF8=1` | Windows: UTF-8 mode для всего Python процесса |
