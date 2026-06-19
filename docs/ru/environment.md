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

Сжатая выжимка. Полный список с описаниями — в [EN-версии (environment.md)](/docs/environment#tausik-environment-variables).

### Workflow control

| Переменная | Эффект |
|---|---|
| `TAUSIK_SKIP_HOOKS=1` | Полный bypass хуков TAUSIK (debug). |
| `TAUSIK_HOOK_FAIL_SECURE=1` | Если хук падает — трактовать как блок (по умолчанию fail-open). |
| `TAUSIK_QUIET=1` | Глушит `[gates]` / `[rag]` прогресс в stderr. |
| `TAUSIK_VERIFY_FULL=1` | Полный pytest без `-m 'not slow'`. |
| `TAUSIK_DISABLE_SESSION_METRICS=1` | SessionEnd не пишет `session_usage_metrics`. |
| `TAUSIK_DISABLE_TASK_RECOMMENDATION=1` | Глушит банер model recommendation в `task_start`. |
| `TAUSIK_OUTPUT_TRUNCATION_THRESHOLD=<int>` | Порог строк для nudge о слишком большом tool output (default 250). |
| `TAUSIK_SECRET_SCAN_STRICT=1` | `secret_scan.py` блокирует (а не warning'ит). |
| `TAUSIK_SCOPED_SKIP__<gate>=1` | Скип одного именованного гейта в текущем verify/task_done. |

### Push-ticket и memory

| Переменная | Эффект |
|---|---|
| `TAUSIK_SKIP_PUSH_HOOK=1` | git_push_gate becomes no-op (debug-only). |
| `TAUSIK_PUSH_TICKET_PATH` | Override пути к single-use ticket (тесты). |
| `TAUSIK_ALLOW_PUSH=1` | **No-op с v1.4** — env-bypass удалён, заменён ticket-файлом от `tausik push-ok`. |
| `TAUSIK_SKIP_MEMORY_HOOK=1` | Bypass `memory_pretool_block.py` (или использовать `confirm: cross-project` в промпте). |
| `TAUSIK_BRAIN_HOOK_DEBUG=1` | Brain-хуки пишут в stderr. |
| `TAUSIK_E2E=1` | Маркер end-to-end тестов. |

### Project + IDE detection

Обычно ставятся IDE-хостом, не пользователем.

| Переменная | Эффект |
|---|---|
| `TAUSIK_DIR` / `TAUSIK_PROJECT_DIR` / `TAUSIK_PROJECT_NAME` | Override discovery `.tausik/` / project root / project name. |
| `TAUSIK_MANIFEST` | Альтернативный bootstrap-manifest (advanced/testing). |
| `TAUSIK_BRAIN_REGISTRY` | Override `~/.tausik-brain/projects/`. |
| `CLAUDE_PROJECT_DIR` | Корень проекта (Claude Code). |
| `CLAUDE_PLUGIN_DATA`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SSE_PORT` | Внутренние сигналы Claude Code. |
| `CURSOR_DIR` / `CURSOR_TRACE_DIR` / `CURSOR_TRACE_ID` | Set by Cursor. |
| `WINDSURF_DIR` / `WINDSURF_SESSION` | Set by Windsurf. |
| `CODEX_HOME` / `CODEX_SANDBOX_DIR` | Set by Codex. |
| `QWEN_CODE` / `QWEN_HOME` | Set by Qwen Code. |

### Model selection

| Переменная | Эффект |
|---|---|
| `TAUSIK_IDE` / `TAUSIK_IDE_PROFILE` | Принудительный IDE-профиль. |
| `TAUSIK_MODEL` / `TAUSIK_MODEL_PROFILE` | Принудительный model-профиль (opus / sonnet / haiku / gpt-4 / gpt-5 / gpt-5-5 / qwen). |
| `TAUSIK_AGENT_MODEL` / `TAUSIK_AGENT_MODEL_VERSION` | Логируются в `usage_events` если хост не сообщает активную модель. |
| `CLAUDE_MODEL` / `CLAUDE_CODE_MODEL` | Если хост — Claude Code. |
| `CURSOR_MODEL` | Если хост — Cursor. |
| `ANTHROPIC_MODEL` / `OPENAI_MODEL` / `OPENAI_API_MODEL` / `QWEN_MODEL` | Provider-flavoured fallbacks. |

### Brain / Notion

| Переменная | Эффект |
|---|---|
| `NOTION_TAUSIK_TOKEN` | Notion integration token (default; имя override'ится `brain.notion_integration_token_env`). |
| `NOTION_TOKEN` | Generic fallback. |
| `NOTION_RICH_TEXT_CHUNK` | Размер rich-text чанка для Notion-writer (default 1800). |

### Windows-specifics

| Переменная | Эффект |
|---|---|
| `PYTHONIOENCODING=utf-8` | Предотвращает crash на Unicode выводе. |
| `PYTHONUTF8=1` | UTF-8 mode для всего Python процесса. |
