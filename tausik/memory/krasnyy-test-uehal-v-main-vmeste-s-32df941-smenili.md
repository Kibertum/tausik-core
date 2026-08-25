---
slug: krasnyy-test-uehal-v-main-vmeste-s-32df941-smenili
title: "Красный тест уехал в main вместе с 32df941 — сменили семантику, не тронув старый тест"
type: gotcha
tags: []
task: token-metrics-append-name-lies
edges: []
---

Обнаружено в сессии #112 при регрессе чужой задачи. Коммит 32df941 (l26-token-metrics-rotation) правильно сменил семантику append_token_rows с «дописать» на «заменить строки сессии», написал новый файл тестов test_token_metrics_rotation.py — и НЕ тронул старый test_token_metrics.py::TestAppendTokenRows::test_appends_rows_idempotent_across_calls, кодировавший прежний контракт. Тест остался красным в main.

Два урока:

1. МЕХАНИКА ЗАЩИТЫ: имя функции осталось append_*, хотя она replace_*. Имя, расходящееся с поведением, — ровно тот путь, которым баг возвращают обратно. Переименовано в replace_session_token_rows.

2. МЕХАНИКА ОБНАРУЖЕНИЯ: при смене семантики функции grep по её имени по ВСЕМУ дереву тестов обязателен — новый тест-файл не отменяет старый. Отличать «мой регресс» от «было до меня» дешевле всего через `git stash -u` + прогон подозрительного файла (30 секунд), а не рассуждением.

3. ЗЕРКАЛА IDE ОТСТАЮТ МОЛЧА: .cursor/.kilo/.opencode/.qwen/scripts/hooks/session_metrics.py оставались на ДОРЕЛИЗНОЙ версии функции (без max_bytes) — bootstrap для этих IDE не перезапускали после 32df941. Правь только scripts/, затем `python bootstrap/bootstrap.py --no-detect --ide all` и проверь grep-ом, что все пять зеркал подхватили.

Связано: [[konvenciya-215]] о формате evidence и [[216]] о том, что зелёная сьюта не доказывает целостность контроля.</content>
<parameter name="tags">["tests", "regression", "mirrors", "bootstrap", "defect-escape"]
