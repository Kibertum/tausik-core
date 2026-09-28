[English](../en/session-active-time.md) | **Русский**

# Session Active Time (v1.4)

<!-- doc-map: reader=user; zone=sessions -->

SENAR Foundation (10.2) требует установить максимум длительности сессии с основанием; SENAR Core, который заявляет TAUSIK, сессий не нормирует вовсе. В TAUSIK порог **180 минут** — с 1.10 **совет, а не ворота** (решение #376): выше него `task start`, `status` и Stop-хук печатают предупреждение, но в старте задачи не отказывают. Считается порог по **active time**, не wall-clock: длинные паузы клипуются до threshold'а вместо того, чтобы их выбрасывать. Эта страница объясняет алгоритм, semantics-выбор (clip vs exclude), основание порога и как тюнить threshold.

## Зачем active time

Wall clock наказывает за естественные перерывы. Сессия, которая стартует в 09:00, паузится на часовой митинг и продолжается в 11:00, упёрлась бы в "120 min" без того, чтобы агент сделал 120 min работы. v1.3+ это фиксит, считая **gap-based active time**: bounded sum интервалов между tool calls.

## Алгоритм

Каждый вызов инструмента, на который зарегистрирован хук, — запись, оболочка, чтение, поиск, веб и внешние MCP-инструменты записи, один набор на всех хостах с 1.10, — пишет строку в `events` (через PostToolUse-хук `activity_event.py`). Active time — сумма **bounded** интервалов между последовательными timestamps:

```
active_seconds = Σ min(t[i+1] − t[i], idle_threshold_seconds)
```

Каждый gap клипуется до `idle_threshold` (default **600 секунд / 10 минут**). Длинный AFK gap (например, 3 часа) добавляет ровно threshold к active — этого достаточно, чтобы кредитнуть "агент только что работал перед паузой", но не настолько много, чтобы съесть всё окно Rule 9.2.

```
events:    t1   t2   t3 ---(huge gap)--- t4   t5
intervals: Δ1   Δ2   Δ3(clipped→10m)     Δ4
active     = Δ1 + Δ2 + 10m + Δ4
wall       = t5 − t1
```

**v1.4-полишинг (v14b-session-active-time)** переключил semantics с "exclude" (gap≥threshold → 0) на "clip" (gap≥threshold → threshold). Clip консервативнее: длинная AFK всё равно тратит ~10 мин против лимита, и агент не получает "бесплатно" сессии длиной в дни.

## Конфигурация threshold

`.tausik/config.json`:

```json
{
  "session_idle_threshold_minutes": 10,
  "session_max_minutes": 180,
  "session_warn_threshold_minutes": 150,
  "session_capacity_calls": 200
}
```

| Knob | Default | Значение |
|------|---------|----------|
| `session_idle_threshold_minutes` | 10 | Gap'ы выше этого клипуются до threshold'а (длинная AFK добавляет ровно столько в active time, не ноль) |
| `session_max_minutes` | 180 | Порог совета — выше него `task_start`, `status` и Stop-хук печатают предупреждение, не отказ (`session extend` поднимает порог) |
| `session_warn_threshold_minutes` | 150 | Soft warning стартует здесь |
| `session_capacity_calls` | 200 | Ёмкость в **tool calls**, не минутах; бюджет задачи выше остатка — совет в выводе `task_start`, не отказ |

## Где это видно

`tausik status` показывает обе цифры, когда сессия открыта:

```
Session: 76m active / 145m wall
```

`tausik doctor` дублирует то же самое.

## Retro-вычисление

Если вы тюните idle threshold или хотите посмотреть, как прошлая сессия выглядела бы при другом значении, запустите:

```bash
.tausik/tausik session recompute
```

Это пройдёт по событиям `session_activity` для прошлых сессий и распечатает `wall vs active` для каждой. Recompute read-only — не мутирует сохранённые значения, если не передан `--write` (где поддерживается).

## Activity hook

`scripts/hooks/activity_event.py` — PostToolUse-хук, который штампует `(session_id, tool_name, timestamp)` в `session_activity`. Запускается на инструменты из его матчера, одинаковые у Claude, Qwen и Codex. Отключайте через `TAUSIK_SKIP_HOOKS=1` только для дебага — отключение его останавливает накопление active time до повторного включения.

## Override / Extend

Если действительно нужна более длинная сессия (например, день релиза):

```bash
.tausik/tausik session extend --minutes 60
```

`task_start --force` отозван в 1.10: ёмкость больше не гейт, обходить нечего; флаг отвечает отказом с причиной (решение #376).

## Основание порога (SENAR 1.5 §9.4(c))

Числа 180 / 150 / 200 унаследованы от ориентира SENAR 1.3 §9.2 («после 180 минут отдача падает») и до 1.10 держали ворота. Замер смены #266 по 70 сменам #196–#265 (`tausik session recompute --limit 70`): одна смена пересекла 180 активных минут (#241, 246 минут, без продления), медиана 73, p90 146; продление `session extend` не вызывалось ни разу, а итоги 13 смен упоминают ёмкость как причину остановки. Поэтому порог стал советом. Основание пересчитывается командой: `session recompute` печатает строку `SUMMARY` — медиану, p90, максимум активных минут и число смен выше порога (на 23.09.2026 по сменам #196–#265: медиана 73, p90 146, выше 180 — 1). Пересечение порога записывается событием `session_threshold_crossed` один раз на сессию (§9.4(d)). Любой порог — `session_max_minutes`, `session_capacity_calls`, `checkpoint_calls` (40), `journal_freshness_calls` (40) — выключается значением 0.

## Negative — что active time НЕ есть

- Это **не** wall clock — длинные паузы выбрасываются выше idle threshold'а.
- Это **не** оценка реального focused-work времени. Tool calls — proxy; если вы читаете код в голове без вызова tool'ов, таймер паузится.
- Порог **180** — на **active**, не wall. Сессия, открытая 12 часов с 30 min активности, всё ещё на 30 min и далеко под порогом.
- Это **не** ворота: пересечение порога печатает совет и ничему не отказывает (1.10, решение #376).

## См. также

- [Конфигурация](configuration.md) — полный список knobs в `.tausik/config.json`
- [CLI команды](cli.md) — `session start/extend/recompute`
- [Hooks](hooks.md) — activity hook и другие PostToolUse-хуки
