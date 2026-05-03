[English](../en/session-active-time.md) | **Русский**

# Session Active Time (v1.3)

SENAR Rule 9.2 ограничивает сессию **180 минутами**. В v1.3 эти 180 — **active time**, не wall-clock: паузы не учитываются. Эта страница объясняет, как измеряется active time, почему изменилось, и как тюнить threshold.

## Зачем active time

Wall clock наказывает за естественные перерывы. Сессия, которая стартует в 09:00, паузится на часовой митинг и продолжается в 11:00, упёрлась бы в "120 min" без того, чтобы агент сделал 120 min работы. v1.3 это фиксит, считая **gap-based active time**: время, когда агент реально что-то делал.

## Алгоритм

Каждый tool call пишет строку в `session_activity` (через PostToolUse-хук `activity_event.py`). Active time — сумма интервалов между последовательными activity-таймстемпами, где gap **меньше idle threshold'а**.

```
events:    t1   t2   t3 ----- (gap ≥ idle) ----- t4   t5
intervals: [t1..t2] + [t2..t3] + [t4..t5]
active     = sum of those intervals
wall       = last_event - first_event
```

Если gap между двумя последовательными событиями ≥ `session_idle_threshold_minutes` (default **10 min**), gap трактуется как **AFK** и выбрасывается из суммы.

## Конфигурация threshold

`.tausik/config.json`:

```json
{
  "session_idle_threshold_minutes": 10,
  "session_max_minutes": 180,
  "session_warn_threshold_minutes": 150,
  "session_capacity_minutes": 200
}
```

| Knob | Default | Значение |
|------|---------|----------|
| `session_idle_threshold_minutes` | 10 | Gap выше этого — AFK, выбрасывается из active time |
| `session_max_minutes` | 180 | Hard limit — `task_start` блокируется выше (`session extend` для override) |
| `session_warn_threshold_minutes` | 150 | Soft warning стартует здесь |
| `session_capacity_minutes` | 200 | Capacity gate, который QG-0 проверяет на `task_start` |

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

`scripts/hooks/activity_event.py` — PostToolUse-хук, который штампует `(session_id, tool_name, timestamp)` в `session_activity`. Запускается на каждый tool call. Отключайте через `TAUSIK_SKIP_HOOKS=1` только для дебага — отключение его останавливает накопление active time до повторного включения.

## Override / Extend

Если действительно нужна более длинная сессия (например, день релиза):

```bash
.tausik/tausik session extend --minutes 60
```

`task_start --force` — отдельный escape hatch, который байпасит **capacity gate** с audit-event trail; он не заменяет `session extend`.

## Negative — что active time НЕ есть

- Это **не** wall clock — длинные паузы выбрасываются выше idle threshold'а.
- Это **не** оценка реального focused-work времени. Tool calls — proxy; если вы читаете код в голове без вызова tool'ов, таймер паузится.
- Лимит **180** — на **active**, не wall. Сессия, открытая 12 часов с 30 min активности, всё ещё на 30 min и далеко под лимитом.

## См. также

- [Конфигурация](configuration.md) — полный список knobs в `.tausik/config.json`
- [CLI команды](cli.md) — `session start/extend/recompute`
- [Hooks](hooks.md) — activity hook и другие PostToolUse-хуки
