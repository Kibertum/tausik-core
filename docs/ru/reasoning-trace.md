[English](/docs/reasoning-trace) | **Русский**

# Трейс рассуждений (RENAR)

**Трейс рассуждений** — упорядоченная append-only цепочка типизированных шагов,
привязанная к задаче. Он фиксирует, *почему* агент что-то сделал — обоснование,
которое свежий агент не восстановит из одного диффа. Это «рассуждательная»
половина воспроизводимости RENAR (остальные — events, прогоны верификации и
receipts). Сам трейс читается через `tausik task show`; `tausik task replay <slug>`
собирает более полный хронологический таймлайн, сшивающий все четыре источника.

Скилл `/reason` — агентская поверхность; эта страница — справочник.

## Четыре вида (закрытый список)

Шаг относится к одному из закрытого списка видов. Четыре образуют канонический
цикл; `seq` автоинкрементируется в рамках задачи:

| вид | отвечает на вопрос |
|-----|--------------------|
| `intent` | Чего я сейчас пытаюсь достичь? |
| `premise` | Какое убеждение/допущение определяет выбор? |
| `action` | Что я для этого делаю |
| `verification` | Как я подтвердил, что сработало |

Неверный вид отклоняется дважды — сервисом (дружелюбная ошибка) и ограничением
БД `CHECK` (жёсткая гарантия), поэтому некорректный шаг не сохраняется тихо.

## Запись шагов

MCP-first (предпочтительно):

```
tausik_reason_step(slug="my-task", kind="intent", content="…")
```

CLI как fallback — аргументы позиционные `<slug> <kind> <content>`:

```bash
.tausik/tausik task reason-step my-task intent "…"
```

Прочитать трейс через CLI — `.tausik/tausik task show my-task` — или MCP —
`tausik_task_show(slug="my-task")`. Секция `Reasoning trace (N)` печатается
после плана и решений.

## Разобранный пример — полный трейс

Трейс ниже — из самой задачи `v16r-reason-skill`: выпуск скилла `/reason`,
nudge которого *не* должен стать новым гейтом.

```bash
.tausik/tausik task reason-step v16r-reason-skill intent \
  "Ship a /reason skill + a /task nudge that records reasoning at forks."

.tausik/tausik task reason-step v16r-reason-skill premise \
  "Reasoning capture is a discipline, not a gate — QG-2 must gain no new blocker."

.tausik/tausik task reason-step v16r-reason-skill action \
  "Add an escalating SOFT nudge to /task step 6; leave task_done gates untouched."

.tausik/tausik task reason-step v16r-reason-skill verification \
  "Closed a task with zero reasoning steps end-to-end — task done succeeded, no new gate fired."
```

Вывод `tausik task show v16r-reason-skill`:

```
Reasoning trace (4):
  1. (intent) Ship a /reason skill + a /task nudge that records reasoning at forks.
  2. (premise) Reasoning capture is a discipline, not a gate — QG-2 must gain no new blocker.
  3. (action) Add an escalating SOFT nudge to /task step 6; leave task_done gates untouched.
  4. (verification) Closed a task with zero reasoning steps end-to-end — task done succeeded, no new gate fired.
```

Цепочка читается как самодостаточный аргумент: **intent** задаёт цель,
**premise** называет ограничение, сформировавшее дизайн, **action** фиксирует
конкретный выбор, а **verification** замыкает петлю, проверяя ровно то
ограничение, что утверждал premise. Исправление никогда не редактирует прошлый
шаг — добавляется новый (часто свежий `premise`).

## Когда записывать — и когда нет

Записывайте шаг на **развилке**: выбор между подходами, принятие неочевидного
допущения, верификация утверждения, обоснование которого иначе потеряется.

**Не** используйте как журнал на каждую правку — для этого есть `task log`. Три
поверхности, три задачи:

| Поверхность | Форма | Для чего |
|-------------|-------|----------|
| `reason-step` | типизированный, упорядоченный, append-only | *рассуждение* за развилкой — воспроизводимо |
| `task log` | свободная строка с таймстампом | журнал прогресса, crash-safety |
| `tausik_decide` | зафиксированное проектное решение | выборы, связывающие будущую работу |

## Гарантии

- **Append-only.** Шаги не редактируются и не удаляются; трейс — аудит-запись.
  Неверный premise → новый шаг, не переписывание.
- **Advisory, не блокирует.** Ни QG-0 (`task start`), ни QG-2 (`task done`) не
  смотрят на трейс. Задача с **нулём** шагов рассуждений стартует и закрывается
  как обычно — nudge в `/task` лишь мягкое эскалирующее напоминание.
- **Один трейс на задачу.** Шаги привязаны к slug задачи; глобального трейса нет.

## См. также

- **[Скиллы](skills.md)** — `/reason` и остальная поверхность скиллов
- **[Рабочий процесс](workflow.md)** — как рассуждение встроено в жизненный цикл задачи
- **[CLI-команды](cli.md)** — `task reason-step`, `task replay`
- **[MCP-инструменты](mcp.md)** — `tausik_reason_step`, `tausik_task_replay`
