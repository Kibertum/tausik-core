# Model Providers

TAUSIK is model-agnostic. Skills work with any LLM that supports tool use.

## Supported Platforms

| Platform | Config file | Skills location | Instructions file |
|----------|------------|-----------------|-------------------|
| Claude Code | `.claude/settings.json` | `.claude/skills/` | `CLAUDE.md` |
| Cursor | `.cursor/settings.json` | `.cursor/skills/` | `.cursorrules` |
| OpenCode | `opencode.json` | `.claude/skills/` (shared) | `AGENTS.md` |
| Codex | `.codex/config.toml` | `.codex/agents/` | `AGENTS.md` |

## Using GigaChat (Sber)

GigaChat models can be used via OpenCode with liteLLM:

1. Get API credentials at https://developers.sber.ru/
2. Install OpenCode: `npm i -g @anthropic-ai/opencode` (or via brew)
3. Configure `opencode.json`:
```json
{
  "model": "gigachat/GigaChat-2-Max"
}
```
4. Set environment: `export GIGACHAT_API_KEY=your_client_secret`
5. Run: `opencode` — uses GigaChat model with all TAUSIK skills

Available models: GigaChat-2-Max, GigaChat-2-Lite, GigaChat 3 Ultra (702B)

## Using Other Providers

OpenCode supports 75+ providers via liteLLM. Common examples:
- `openai/gpt-4o` — OpenAI GPT-4o
- `anthropic/claude-sonnet-4-5` — Anthropic Claude
- `google/gemini-2.5-pro` — Google Gemini
- `ollama/llama3` — Local Ollama models (free)
