---
slug: dva-puti-zapisi-v-verification-runs-s-raznymi-pravilami-cli
title: "Два пути записи в verification_runs с разными правилами: CLI verify обходит защиты run_gates_with_cache"
type: gotcha
tags: []
task: null
edges: []
---

Записать строку кэша можно ДВУМЯ путями, и правила у них не совпадают.

1. service_verification.run_gates_with_cache — путь task_done и MCP-verify. Защиты: has_real_pass (все гейты пропущены -> noncacheable|), no-test-mapped (files объявлены, но ни один тест не смапился -> синтетический блокирующий отказ), запрет кэша при пустой области.
2. project_cli_verify.py — путь CLI `tausik verify`. Зовёт run_gates и record_run НАПРЯМУЮ. Ни одной из этих защит.

Живое доказательство (сессия #118, прогон #1054): verify по задаче с relevant_files=[CHANGELOG.md, CHANGELOG.ru.md] дал [SKIP] hadolint, [SKIP] pytest — не выполнилось ничего, — и записал строку exit_code=0 БЕЗ префикса noncacheable| с summary «hadolint=PASS, pytest=PASS». Пропущенный гейт рапортует passed=True, поэтому сводка выглядит как успех. Через сервисный путь тот же вход дал бы блокировку.

Практический вывод для агента: зелёный `tausik verify` с [SKIP] у всех гейтов НЕ является доказательством. Смотри на строку [SKIP]/[PASS], а не на слово Recorded. Для задач, чьи файлы не мапятся на тесты (документация, конфиги), доказательством должен быть прямой прогон релевантной проверки, а не кэш-хит.

Более общий урок: правило, записанное в одном из двух путей, не является правилом системы. Дыру пустой области спасла только эшелонированность (отказ на ЧТЕНИИ в has_fresh_verify_run независим от стороны записи) — если бы правку сделали только на записи, CLI-путь оставил бы её открытой целиком.

Задача на устранение: cli-verify-bypasses-cache-guards. Связано: verify-cache-empty-scope-hit, конвенция #236 (разовую находку закрывать механическим гейтом).</content>
<parameter name="task_slug">cli-verify-bypasses-cache-guards
