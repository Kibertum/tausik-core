[English](../en/agent-quickstart.md) | **Русский**

# Быстрый старт для агента: подключить TAUSIK и работать под ним

Ты — AI-агент. Эта страница написана для тебя и в том порядке, в каком она
понадобится: как подключить фреймворк к проекту на том хосте, в котором ты
работаешь, как убедиться, что он действительно подключён, и как делать работу
после этого — точными вызовами, с ответами и отказами, которые ты реально
увидишь. Каждая команда, имя инструмента и текст отказа здесь сняты с живого
прогона этой версии, а не вспомнены; тест держит их в согласии с кодом
(`tests/test_agent_quickstart.py`).

Человеческая версия того же пути — [quickstart.md](quickstart.md). Сами
правила — в [AGENTS.md](../../AGENTS.md); эта страница — процедура, которая из
них следует.

## 1. Подключить

TAUSIK — это git-сабмодуль плюс один bootstrap. Из корня проекта:

```bash
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init --ide <host>
```

`<host>` — один из хостов, которые bootstrap умеет разворачивать: **claude,
cursor, qwen, kilo, opencode, codex** — или `all`. Выбери тот, в котором
работаешь; `all` кладёт все профили рядом (у них одна база в `.tausik/`).

| Ты работаешь в | `--ide` | Что появляется | Что принуждает к правилам в реальном времени |
|---|---|---|---|
| Claude Code / VS Code Claude Extension | `claude` | `.claude/` (навыки, хуки, MCP), `.mcp.json`, `CLAUDE.md`, `AGENTS.md` | PreToolUse-хуки (`.claude/settings.json`) |
| Cursor / Composer | `cursor` | `.cursor/mcp.json`, `.cursorrules`, `AGENTS.md` | ничего на границе инструмента — Rule 1 исполняешь ты сам (см. §3) |
| Qwen Code | `qwen` | `.qwen/` (навыки, настройки), `QWEN.md`, `AGENTS.md` | хуки (подмножество хуков Claude) |
| Kilo Code | `kilo` | `.kilo/`, `.kilocode/mcp.json`, `AGENTS.md` | ничего на границе инструмента — только гейты MCP |
| OpenCode | `opencode` | `.opencode/` (один плагин QG-0), `opencode.json` | плагин QG-0 для Rule 1; для Rule 2 — ничего |
| Codex CLI | `codex` | `.codex/` (config.toml с MCP, навыки, агенты, hooks.json), `AGENTS.md` | `.codex/hooks.json` — **только после того, как пользователь доверил хуки проекта в Codex**; недоверенный профиль не принуждает ничего (замерено живьём) |

После bootstrap — **перезапусти хост** (MCP-серверы читаются при старте), затем
проверь. Две равнозначные проверки — инструмент MCP, если хост показывает
`tausik_*`, иначе CLI:

```
tausik_status                       ← MCP
.tausik/tausik status               ← CLI (Windows cmd/PowerShell: .tausik/tausik.cmd status)
```

Ожидаемо на свежем проекте:

```
Tasks: 0/0 done
Session: none active
```

Если после перезапуска инструментов MCP нет — `.tausik/tausik doctor` (или
`tausik_doctor`) назовёт недостающее; CLI работает в любом случае. У каждого
инструмента `tausik_*` есть CLI-двойник, поэтому ничего ниже от MCP не зависит.

**Отдельно про Codex.** Codex исполняет хуки проекта только после того, как
пользователь им доверил. До этого `bootstrap --check` чист, файл хуков
перечисляет все гейты — и ни один не срабатывает. Не сообщай Rule 1/Rule 2 как
принуждаемые на Codex, пока доверенное состояние не подтверждено; [матрица
принуждения](model-providers.md#матрица-принуждения-codex) несёт то же условие.

## 2. Цикл вызовами

Одна задача за раз, каждый шаг записан. Слева инструмент MCP, справа
CLI-двойник; ответ — то, что ты увидишь.

**Открыть смену.**

```
tausik_session_start                 .tausik/tausik session start
→ Session #1 started.
```

**Создать задачу с целью И критериями приёмки.** QG-0 отказывает в старте
без них, и один критерий обязан быть негативным (ошибка или граница).

```
tausik_task_quick(title="Demo feature", goal="Show the gate",
  acceptance="AC-1: the feature returns the answer. AC-2: an empty input is refused with an error.")
.tausik/tausik task quick "Demo feature" --goal "Show the gate" --ac "AC-1: … AC-2: an empty input is refused with an error."
→ Task 'demo-feature' created.
```

**Стартовать.** С этого момента гейты записи для тебя открыты.

```
tausik_task_start(slug="demo-feature")      .tausik/tausik task start demo-feature
→ Task 'demo-feature' started (attempt #1).
```

Если критерий пропущен, отказ точен и называет починку:

```
Error: QG-0 Context Gate: 'demo-feature' cannot start — missing acceptance_criteria. Fix: .tausik/tausik task update demo-feature --goal '...' --acceptance-criteria '...'
Error: QG-0 Start Gate: 'demo-feature' AC has no negative scenario. SENAR requires at least one error/boundary case in acceptance criteria.
```

**Объявить, что будешь трогать, затем править.** `relevant_files` — область,
которую читают гейты; пути через пробел.

```
tausik_task_update(slug="demo-feature", …)   .tausik/tausik task update demo-feature --relevant-files src/feature.py tests/test_feature.py
```

**Журналировать по ходу.** Каждый значимый шаг и доказательство по каждому
критерию — закрытие читает эти строки.

```
tausik_task_log(slug, message)      .tausik/tausik task log demo-feature "AC-1: ✓ tests/test_feature.py::test_answer  AC-2: ✓ tests/test_feature.py::test_empty_is_refused (negative: empty input raises)"
```

**Проверить.** Тяжёлые гейты (линтеры, scoped-тесты) бегут один раз, здесь, и
зелёное записывается для закрытия.

```
tausik_verify(task_slug="demo-feature")       .tausik/tausik verify --task demo-feature
→ [PASS] ruff
  [PASS] pytest  SCOPE: scoped run over 1 of 1 test file(s) mapped from relevant_files …
  Recorded verification_run #8 (task_slug=demo-feature, exit=0).
```

В проекте с ключом подписи ответ кончается **verify handle** — передай его в
закрытие. Без ключа он так и говорит и даёт рабочее закрытие:

```
Verify handle: none — no project key, so no signed receipt (`tausik key init` enables them). Close without --verify-handle: `.tausik/tausik task done demo-feature --ac-verified` uses the freshness lookup.
```

**Закрыть.** `--ac-verified` — твоё утверждение; проверяет гейт записанное
доказательство.

```
tausik_task_done(slug="demo-feature", ac_verified=true, verify_handle="<из verify>")
.tausik/tausik task done demo-feature --ac-verified [--verify-handle <handle>]
→ Task 'demo-feature' completed.
```

Два отказа, которые встретишь, если поспешить, — оба точные:

```
Error: QG-2: 'demo-feature' cannot complete — acceptance criteria not verified. Verify each criterion, then: .tausik/tausik task done demo-feature --ac-verified
Error: QG-2: 'demo-feature' has 2 acceptance criteria but no verification evidence in task notes. Log verification: .tausik/tausik task log demo-feature "AC verified: 1. ✓ 2. ✓ ..."
```

**Передать и закончить.** Handoff — то, с чего начнёт следующая смена.

```
tausik_session_handoff(handoff={...})    .tausik/tausik session handoff '<json>'
tausik_session_end                        .tausik/tausik session end
→ Session #1 ended.
```

## 3. Что принуждает хост, а что — ты

Два рода правил, два рода принуждения — граница проходит по тому, КТО
совершает действие, а не по хосту:

* **Правила, которые держит наша поверхность, везде.** QG-0 (нет старта без
  цели и AC), QG-2 (нет закрытия без доказательства и свежего verify), лимит
  смены, маршрут памяти. Они отказывают внутри `tausik_*` / CLI и держатся на
  хосте вовсе без хуков.
* **Правила, перехватывающие ТВОЁ действие.** Rule 1 (нет записи файла без
  активной задачи), Rule 2 (нет записи вне объявленной области), shell-файрвол,
  push-гейт. Они есть только там, где хук бежит перед инструментом: Claude
  Code, Qwen Code, Codex (после доверия), и один Rule 1 на OpenCode. На Cursor
  и Kilo между тобой и файлом никого нет — хук это ты: стартуй задачу до первой
  правки.

Там, где хук бежит, запись без активной задачи отклоняется до изменения файла:

```
BLOCKED: No active task. TAUSIK requires a task before code changes (SENAR Rule 1).
  Create one:   /plan   (or describe the task and ask to start it)
  Resume one:   .tausik/tausik task list --status planning
                .tausik/tausik task start <slug>
```

`docs/ru/enforcement-coverage.md` — таблица по правилам, а
`.tausik/tausik doctor` печатает, что развёрнуто для ЭТОГО хоста.

## 4. Память: что писать и куда не писать

* `tausik_memory_add` / `.tausik/tausik memory add` — паттерн, ловушка или
  конвенция ЭТОГО проекта, когда узнал то, что следующий агент не должен
  узнавать заново.
* `tausik_dead_end` / `.tausik/tausik dead-end "подход" "причина"` — подход,
  который не сработал, и почему. Дешевле, чем следующий агент попробует снова.
* `tausik_decide` / `.tausik/tausik decide` — решение с обоснованием.
* **Не пиши в `~/.claude/`** с не-Claude хоста и не клади туда правила самого
  TAUSIK ни с какого хоста: это профиль Claude, а не память проекта. Знание
  проекта идёт через инструменты выше.

## 5. Если у хоста нет slash-команд

`/start`, `/plan`, `/ship` и остальные — процедуры, записанные Markdown-ом.
Когда хост их не разворачивает, открой `harness/skills/<name>/SKILL.md`
(развёрнуто в `.claude/skills/`, `.qwen/skills/`, `.codex/skills/`) и выполни
нумерованные шаги сам. Инструменты, которые они зовут, — те же, что в §2.

## См. также

* [AGENTS.md](../../AGENTS.md) — правила и матрица хостов
* [quickstart.md](quickstart.md) — тот же путь для человека
* [mcp.md](mcp.md) — каждый инструмент `tausik_*` и его параметры
* [cli.md](cli.md) — каждая команда CLI
* [enforcement-coverage.md](enforcement-coverage.md) — что принуждается где, по правилам
* [model-providers.md](model-providers.md) — заметки по хостам, включая условие доверия Codex
