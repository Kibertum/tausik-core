---
title: "TAUSIK 1.4 — token baseline для /start, /task, /ship"
subtitle: "Сколько токенов фреймворк тратит на холостой старт; что оптимизировать"
lang: ru
date: 2026-05-03
session: "#43"
status: baseline-v1
---

# TAUSIK 1.4 — token baseline

## TL;DR

**Холостой старт `/start` тратит ~3500 input tokens** до первого ответа агента (CLAUDE.md + AGENTS.md + Memory Block + 8 MCP-вызовов).
**`/task <slug>` добавляет ~600-1200 tokens** (task show + plan + notes).
**`/ship` — самый дорогой: ~5000-8000 input tokens** на иттерацию (review с 5 агентами + tests + commit).

Цель v1.4 polish — не превышать **5000 tokens на холостом /start**, **8000 tokens на /ship** при минимальной потере функциональности.

## Методология

Реальные measurements не сделаны — Claude Code harness не expose token counts через programmatic API на момент сессии #43. Числа ниже — **estimate** на базе:

1. **Lines × tokens/line factor**: для plain-text Markdown в Claude tokenizer ≈ 3.5 tokens/line average (короткие списки → 2.5, длинные параграфы → 5).
2. **wc -l** на ключевых файлах (см. ниже).
3. **MCP tool result sizes** — JSON-сериализованный вывод считается через JSON length / 4.
4. **Конверсия chars → tokens**: cl100k_base / claude-tokenizer ≈ 1 token / 3.5-4 chars для смешанного EN+RU.

Точное профилирование запланировано в Phase B — задача `v14b-token-profiling-instrument` через PostToolUse hook, который пишет реальные `usage_events` в БД.

## Baseline numbers (estimate, sentinel commit `b5ec2c6`)

### `/start` initial context inject

| Источник | Lines | Estimate tokens |
|---|---|---|
| `CLAUDE.md` (full body) | 172 | ~600 |
| `AGENTS.md` | 143 | ~500 |
| **Tool definitions** (system prompt от Claude Code, ~99 MCP tools — описания в tools.py) | — | **~12000-15000** |
| **Skill definitions** (13 core skills × ~20 lines = ~260 lines descriptions при `context_tier=standard`) | 260 | ~900 |
| Memory Block (recent decisions + conventions + dead ends) | ~30 | ~150 |
| MCP tool calls в `/start` (8 параллельных): session_start, status, last-handoff, task_list, metrics, explore_current, audit_check, memory_block | — | ~1500 (output JSON) |
| Brain primer (если включен) | — | ~300 |
| **Итого `/start`** | — | **~16000-18500 input tokens** |

⚠️ **Главный жировик** — tool definitions (~12-15k tokens) генерируются Claude Code из 99 MCP tools. Это `system prompt`, не controlled через TAUSIK.

### `/task <slug>` (resume)

| Источник | Estimate tokens |
|---|---|
| `tausik_task_show` JSON | ~300 |
| `tausik_task_logs` (если 5+ записей) | ~500-800 |
| Plan steps (если есть) | ~200 |
| **Итого `/task`** | **~600-1200** (поверх /start context) |

### `/ship` (полный pipeline)

| Источник | Estimate tokens |
|---|---|
| 5 параллельных `/review` agents (каждый читает diff + scope) | ~3000 (output) |
| `pytest` через verify | ~500 (output если PASS, до 5000 при FAIL) |
| Adversarial critic (6-й агент) | ~600 |
| `tausik_task_done_v2` JSON | ~400 |
| `commit` skill (read git diff + write message) | ~800 |
| **Итого `/ship`** | **~5000-8000 input tokens** |

## Где жирно (приоритеты оптимизации)

### P0 — `system prompt` MCP tools description (~12-15k tokens)

99 MCP tools = большой system prompt. Каждый tool ≈ 100-200 tokens (name + description + JSON schema).

**Опции:**
1. **Lazy tool loading**: MCP server возвращает только подмножество tools на основе `_meta` request. Не реализовано в Claude Code MCP protocol сейчас.
2. **Context tier**: при `context_tier=minimal` — оставлять только 30 core tools (task_*, session_*, status, doctor). Brain/cost/skill/team etc. — only on demand. **Кандидат для Phase B.**
3. **Tool grouping** через namespacing: `mcp__tausik__core` vs `mcp__tausik__brain` vs `mcp__tausik__cost`. Claude Code тогда может опционально загружать группы.

### P1 — Skill descriptions (~900 tokens)

13 core skills × ~70 tokens описание. Можно сократить до one-liner (~25 tokens / skill = ~325 итого, экономия 575).

### P2 — CLAUDE.md (~600 tokens)

172 lines включая SENAR compliance таблицу (40+ строк). **При `context_tier=minimal`** bootstrap уже рендерит short version (~80 lines). Включить minimal по умолчанию для агентов с маленьким context window.

### P3 — Tool result verbosity

`tausik_status` (default) выводит ~200 lines текста. Через `--compact` — 1 строку JSON (~50 tokens). Skills уже используют `--compact` в /start. Document это как best practice.

## Targets для v1.4 polish

| Команда | Current estimate | v1.4 target | Подход |
|---|---|---|---|
| `/start` cold | ~17k | **≤10k** | minimal CLAUDE.md + minimal skill descriptions + tool grouping (если protocol позволит) |
| `/task <slug>` | ~900 | ≤700 | task_show compact mode |
| `/ship` (happy path) | ~6k | ≤4k | review skill использует scoped diff; adversarial critic only on flagged changes |

## Как реально измерить (Phase B follow-up)

Задача `v14b-usage-events-auto-write`:
1. PostToolUse hook читает `tool_use_id` после каждого MCP/Bash вызова.
2. Записывает `usage_events` row: `tool_use_id`, `input_tokens`, `output_tokens`, `task_slug`, `model_id`.
3. `tausik metrics --cost --by tool` показывает топ-10 жадных tools.
4. После 1 недели использования — реальный baseline вместо estimate.

## Сводка

- Сейчас сессия `/start` стоит ≈ $0.12 на Opus 4.7 (15k input × $15/1M = $0.225, минус ~30% за prompt cache hit на second tool call).
- За день активной разработки (10× /start + 30× /task + 5× /ship) ≈ $5-8 если без cache hits, ≈ $2-3 с aggressive caching.
- Главные жировики — `system prompt` tools list. Это outside TAUSIK control, но `context_tier` + tool grouping минимизируют.

## Связанные документы

- [docs/en/skill-profiles.md](/docs/skill-profiles) — multi-model variants для ужать prompts на Haiku/Sonnet
- [docs/en/dev-doc-checks.md](/docs/dev-doc-checks) — drift checks
- Phase B follow-up: `v14b-usage-events-auto-write`, `v14b-tool-grouping-context-tier`

## Версионирование

| Версия | Дата | Изменения |
|---|---|---|
| 1.0 | 2026-05-03 | Первый baseline (estimate-only, без реальных измерений) |
