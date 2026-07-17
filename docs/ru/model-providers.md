# Провайдеры моделей

TAUSIK не привязан к конкретной модели. Skills работают с любой LLM, поддерживающей tool use.

## Поддерживаемые платформы

«Scaffolded» = у `bootstrap.py --ide <name>` есть ветка-генератор: он пишет конфиг,
подключает MCP-серверы и раскладывает скиллы. Всё, что не scaffolded, TAUSIK не
настраивает — хост придётся конфигурировать руками. Единственный источник правды по
этому списку — `bootstrap/bootstrap_config.py::SCAFFOLD_IDES`; таблицу держать
синхронной с ним.

| Платформа | Scaffolded | Файл конфигурации | Расположение skills | Файл инструкций |
|-----------|-----------|-------------------|---------------------|-----------------|
| Claude Code | да | `.claude/settings.json` | `.claude/skills/` | `CLAUDE.md` |
| Cursor | да | `.cursor/settings.json` | `.cursor/skills/` | `.cursorrules` |
| Qwen Code | да | `.qwen/settings.json` | `.qwen/skills/` | `QWEN.md` |
| Kilo Code | да | `.kilo/` | `.kilo/skills/` | `AGENTS.md` |
| OpenCode | да | `opencode.json` | `.opencode/skills/` | `.opencode/tausik-rules.md` |
| Codex | нет | `.codex/config.toml` | — | `AGENTS.md` |
| Windsurf | нет | `.windsurf/` | — | `.windsurfrules` |

> **OpenCode (с v1.7.0).** `bootstrap.py --ide opencode` пишет `opencode.json`
> (MCP-серверы + ключ `instructions`), кладёт правила в `.opencode/tausik-rules.md`
> и ставит плагин принуждения QG-0 в `.opencode/plugins/tausik-qg0.js` — запись без
> активной задачи отклоняется, как и в Claude Code.
>
> Три вещи, на которых легко обжечься, если конфигурировать OpenCode руками:
> 1. Секция `tools` принимает **только boolean** (`"bash": false`). Объект вида
>    `tools.qg0` валит старт хоста с `ConfigInvalidError` — TAUSIK этот ключ не пишет
>    вообще и ваш boolean не трогает.
> 2. Плагины лежат в `.opencode/plugins/` (**мн. ч.**). Каталог `plugin/` не ошибка —
>    он просто молча не грузится.
> 3. Правила доставляются ключом `instructions`, а **не** через `AGENTS.md`: у OpenCode
>    побеждает первый найденный `AGENTS.md`, то есть ваш, а не наш. `instructions`
>    OpenCode мерджит с вашим `AGENTS.md`, поэтому для `--ide opencode` TAUSIK свой
>    `AGENTS.md` не генерирует — иначе те же правила попали бы в контекст дважды.
>
> **Codex пока не scaffolded** — TAUSIK кладёт для него только `AGENTS.md`.
> См. [добавление новой IDE](/docs/ru/adding-new-ide).

## Использование GigaChat (Сбер)

Модели GigaChat доступны через OpenCode с помощью liteLLM:

1. Получите API-доступ на https://developers.sber.ru/
2. Установите OpenCode: `npm i -g opencode-ai` (или через brew) — OpenCode делает
   [SST](https://opencode.ai); пакета `@anthropic-ai/opencode` не существует.
3. Настройте `opencode.json`:
```json
{
  "model": "gigachat/GigaChat-2-Max"
}
```
4. Задайте переменную окружения: `export GIGACHAT_API_KEY=your_client_secret`
5. Запустите: `opencode` — использует модель GigaChat вместе со всеми skills TAUSIK

Доступные модели: GigaChat-2-Max, GigaChat-2-Lite, GigaChat 3 Ultra (702B)

## Другие провайдеры

OpenCode поддерживает 75+ провайдеров через liteLLM. Типичные примеры:
- `openai/gpt-4o` — OpenAI GPT-4o
- `anthropic/claude-sonnet-4-5` — Anthropic Claude
- `google/gemini-2.5-pro` — Google Gemini
- `ollama/llama3` — локальные модели Ollama (бесплатно)
