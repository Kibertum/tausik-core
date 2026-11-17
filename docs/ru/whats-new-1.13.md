[English](../en/whats-new-1.13.md) | [Русский](../ru/whats-new-1.13.md)

# TAUSIK 1.13: живая работа следует реальному контексту

<!-- doc-map: reader=user; zone=release-notes -->

## 1.13.4 — 2026-11-17

TAUSIK 1.13.4 смягчает freshness package у execution lease для обычных Write/MCP
(advisory `PACKAGE_STALE`), оставляет fail-closed только для commit/push и
отклоняет неполный `complexity=complex` update до записи, чтобы агент не
застревал.

- [Точный changelog 1.13.4](https://github.com/Kibertum/tausik-core/blob/v1.13.4/CHANGELOG.ru.md)
- [Руководство по обновлению](upgrade.md)

## 1.13.3 — 2026-11-17

TAUSIK 1.13.3 делает protected memory preflight пригодным из skills без чтения
`memory_preflight.py` и держит тела GitHub Release в
`docs/release/body-<version>.md`, чтобы корень репозитория оставался чистым.

- [Точный changelog 1.13.3](https://github.com/Kibertum/tausik-core/blob/v1.13.3/CHANGELOG.ru.md)
- [Руководство по обновлению](upgrade.md)

## 1.13.2 — 2026-11-15

TAUSIK 1.13.2 — стабилизационный выпуск для существующих проектов Cursor и
Codex. Матрица обновления начинается с опубликованной v1.11.7, сохраняет задачи,
зависимости, сессии, lease, turn, Stop и continuity на соответствующих границах
схемы и выполняет реально установленные команды хоста в жизненном цикле от
SessionStart до Stop.

Обновление bootstrap теперь закрывается при ошибке и выдаёт ограниченную
диагностику. Оно обновляет все существующие проекции хостов и удаляет старый
`.cursorrules` только тогда, когда ownership digest доказывает авторство TAUSIK
и уже существует заменяющее правило MDC. Руководство по обновлению использует
онлайн-резервную копию SQLite, поэтому зафиксированные WAL-кадры входят в
восстанавливаемый комплект.

После успешного защищённого activation dry run официальная публикация будет
требовать квалификацию точного SHA. Linux создаёт изолированные доверенные
доказательства, нативный Windows остаётся обязательным canary для Cursor и
Codex, а защищённый verifier связывает успешный Windows job, не выдавая
доступный кандидату JUnit за подписанное доказательство.

Lock контроллера квалификации теперь содержит все опубликованные хэши
wheel-артефактов для каждого точного pin зависимости. Нативные lanes Windows, macOS
и Linux сохраняют строгий `--require-hashes`, не наследуя выбор wheel с
платформы сопровождающего.

- [Точный changelog 1.13.2](https://github.com/Kibertum/tausik-core/blob/v1.13.2/CHANGELOG.ru.md)
- [Руководство по обновлению](upgrade.md)

## 1.13.0 — 2026-11-11

TAUSIK 1.13.0 больше не считает оценочное число вызовов инструментов причиной
заморозить живую задачу. `call_budget` и `checkpoint_calls` остаются полезными
сигналами для планирования и checkpoint, но никогда не требуют нового чата и
не ограничивают текущую задачу recovery-списком. Только нативная телеметрия
контекста хоста может потребовать новый поток.

Обновление также удаляет сохранённые состояния `call_budget_exhausted` и
`checkpoint_required` от старых версий, включая автономный режим. Поэтому
`CONTINUITY_BLOCKED` больше не требует recovery, которое одновременно запрещал
устаревший context package. `task start <slug> --package` по-прежнему может
перепривязать package, а обычные защищённые мутации по-прежнему закрыты при
устаревшем package.

У явно запущенной автономной композиции остаётся отдельная `2×`-проверка
бюджета между задачами через `TAUSIK_AUTONOMOUS_BUDGET_BLOCK`. Она не прерывает
уже начатую задачу.

- [Точный changelog 1.13.0](https://github.com/Kibertum/tausik-core/blob/v1.13.0/CHANGELOG.ru.md)
- [Руководство по обновлению](upgrade.md)
