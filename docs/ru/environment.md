[English](/docs/environment) | **Русский**

<!-- audit-translation-drift: skip -->

# Правила окружения

> Полный гайд по shell, virtualenv и Docker — на английском в [environment.md](/docs/environment).

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
| `TAUSIK_SKIP_PUSH_HOOK=1` | Полный bypass git_push_gate (debug-only). Production-bypass — single-use ticket-файл от `tausik push-ok` (TTL 60s, привязан к SHA HEAD); env `TAUSIK_ALLOW_PUSH` удалён в v1.4 как broken-by-design. |
| `TAUSIK_PUSH_TICKET_PATH` | Override пути к ticket-файлу для git_push_gate (тесты) |
| `TAUSIK_SKIP_MEMORY_HOOK=1` | Bypass memory pretool block |
| `TAUSIK_E2E=1` | Включить тяжёлые e2e тесты |
| `PYTHONIOENCODING=utf-8` | Windows: предотвращает crash на Unicode выводе |
| `PYTHONUTF8=1` | Windows: UTF-8 mode для всего Python процесса |
