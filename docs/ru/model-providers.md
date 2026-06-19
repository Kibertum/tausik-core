# Провайдеры моделей

TAUSIK не привязан к конкретной модели. Skills работают с любой LLM, поддерживающей tool use.

## Поддерживаемые платформы

| Платформа | Файл конфигурации | Расположение skills | Файл инструкций |
|-----------|-------------------|---------------------|-----------------|
| Claude Code | `.claude/settings.json` | `.claude/skills/` | `CLAUDE.md` |
| Cursor | `.cursor/settings.json` | `.cursor/skills/` | `.cursorrules` |
| OpenCode | `opencode.json` | `.claude/skills/` (общая) | `AGENTS.md` |
| Codex | `.codex/config.toml` | `.codex/agents/` | `AGENTS.md` |

## Использование GigaChat (Сбер)

Модели GigaChat доступны через OpenCode с помощью liteLLM:

1. Получите API-доступ на https://developers.sber.ru/
2. Установите OpenCode: `npm i -g @anthropic-ai/opencode` (или через brew)
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
