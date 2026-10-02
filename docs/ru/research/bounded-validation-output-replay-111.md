# Replay ограниченного вывода проверок 1.11

Дата: 2026-10-02. Проверялся реальный scoped verify задачи
`bound-agent-validation-output-to-durable-artifacts`, без синтетического
модельного прогона.

| Run | Вердикт | Видимый результат | Долговечное evidence |
|---|---|---|---|
| #3348 | FAIL | Один итог: `gate_runner.py` — 501 строка при лимите 500; pytest не запускался после статического отказа | `.tausik/verification/verify-3348.log` (1240 Б) и `.json` (2395 Б) |
| #3349 | PASS | Один итог: 9 гейтов, 1591 passed, 12 skipped | `.tausik/verification/verify-3349.log` (5038 Б) и `.json` (2827 Б) |

До изменения CLI и MCP `task done` передавали callback, который выдавал
`gate_start` и `gate_done` для каждого гейта. Теперь обе agent-facing обёртки
передают `progress_fn=None`: на поверхность модели возвращается один финальный
результат. Поведенческий тест
`tests/test_project_mcp.py::TestTaskCRUD::test_task_done_does_not_stream_gate_progress_to_model_context`
отклоняет возврат callback. Полный красный вывод не потерян: тест
`test_task_done_persists_full_gate_output_but_returns_a_bounded_failure`
проверяет ограниченный ответ и полное тело по адресу артефакта.

Это устраняет промежуточные TAUSIK progress-сообщения. Polling, который сам
хост применяет из-за собственного transport timeout, TAUSIK не контролирует и
в экономию не засчитывает.
