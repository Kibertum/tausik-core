[English](../en/zero-defect.md) | **Русский**

# /zero-defect — Precision Mode

`/zero-defect` — session-scoped операционный режим, который ужесточает дисциплину агента для high-stakes работы. Не обещает bug-free вывод — снижает частоту небрежных ошибок, проскакивающих в финал.

Skill вдохновлён [Maestro `/zero-defect`](https://github.com/sharpdeveye/maestro), адаптирован к TAUSIK-модели QG-0 / QG-2.

## Когда использовать

Включайте явно для задач, где одна ошибка дорого стоит:

- **Security surface** — auth-флоу, JWT/session-handling, password reset, RBAC
- **Деньги** — payment intent creation, refund/void, ledger writes, subscription state
- **Миграции** — schema-rebuild, data-backfill, необратимые cleanup'ы
- **Bootstrap / packaging** — всё, что едет каждому пользователю
- **Defect fix на complex-задачах** — `complexity=complex` и `defect_of` non-empty

Активация: скажите `zero-defect`, `precision mode`, `high stakes` или `be careful`. Skill распознаёт триггеры и переключается.

## 8 правил

На остаток сессии агент обязуется:

1. **Read before write** — каждый `Edit` предварён `Read`'ом того же файла в том же ходе (или верифицированным предыдущим Read'ом).
2. **Verify before claim** — никаких заявлений "tests pass" / "feature works" без запуска теста или операции в этой сессии.
3. **Don't hallucinate APIs** — при неуверенности `grep`'ните кодбазу или прочитайте upstream-доки перед вызовом.
4. **Re-derive, don't recall** — для каверзной логики выводите заново из текущего кода; не доверяйте памяти о предыдущем чтении.
5. **Smaller edits** — много мелких `Edit`'ов с верификацией между, а не один большой rewrite.
6. **Атомарные коммиты** — группировка по concern; никогда не бандлить рефакторинг с фичей.
7. **Одна ответственность на задачу** — split, если scope расползается.
8. **Pre-commit gate** — запустите `/test` и `/review` (TAUSIK parallel review pipeline) перед "done".

## Поведение активации

Когда `/zero-defect` вызван:

1. Агент подтверждает precision mode и пере-озвучивает 8 правил.
2. На остаток сессии каждый substantive-ответ префиксится `[ZERO-DEFECT]`.
3. Агент отказывается вызывать `task done --ac-verified` без свежего test/operation evidence в notes.

## Цена — и почему это и есть смысл

- Velocity падает в ~2–3× по сравнению со стандартным режимом.
- Tool-call бюджеты должны быть пропорционально увеличены.
- Выигрыш — меньше escapees: дефекты, которые ушли бы в продакшн, заметив только после деплоя.

## Negative — что `/zero-defect` НЕ обещает

- **Не** обещает bug-free вывод. Обещает более жёсткий цикл, не идеальный.
- **Не** заменяет QG-2. Quality gates всё ещё запускаются; `/zero-defect` запускается дополнительно.
- **Не может** быть форсирован на framework-уровне для правила 1 (Read-before-Write). Дисциплина агента несёт это.
- Дефолтный режим для casual-задач быстрее. Не включайте `/zero-defect` безусловно — у него есть цена.

## Комбинировать с

- `/review` — запускает 5-агентный SENAR review pipeline; правило 8 `/zero-defect` его инвокит
- `/test` — явное выполнение тестов; правило 2 требует evidence
- QG-2 scoped pytest gate — `task done` уже запускает scoped-тесты; `/zero-defect` требует запускать их **до** вызова `task done`

## См. также

- [Skills](skills.md) — полный каталог skill'ов
- [Workflow](workflow.md) — когда precision mode вписывается в день
- [SENAR Compliance Matrix](senar-compliance-matrix.md) — как это композится с QG-0 / QG-2
