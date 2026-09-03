---
slug: review-207-open-spy-blind-and-doctor-at-cap
title: "Ревью #207: перехват open в таблице мутаций слеп к sqlite и subprocess, doctor встал ровно на 500 строк, абзац о мутациях без EN-зеркала"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: verify-a-gate-by-mutation-not-by-passing
scope: null
scope_exclude: "Реализации гейтов и билдеры COVERED не меняются; pyc_hygiene не трогается; новых гейтов нет"
relevant_files:
  - "tests/test_gates_catch_their_violation.py"
  - "tests/test_doctor_drift_row.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/service_doctor_drift.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_gates_catch_their_violation.py"
  - "tests/test_doctor_drift_row.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/service_doctor_drift.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T19:14:00Z"
---

## Goal

ЗАВЕДЕНО РЕВЬЮ L3 #207 (записи БД #10, #12) по пяти коммитам смены; долг по качеству работы той же смены, как в #206. (1) MEDIUM: test_the_table_leaves_the_repository_untouched патчит builtins.open и io.open и обещает в докстринге «запись куда-либо ещё ловится», но два из шести COVERED-билдеров пишут через sqlite3 (state_roundtrip) и через subprocess git (memory_route) — эти записи спай не видит; воспроизведено ревьюером пробником (written == [] при созданном файле БД). Утечки сегодня нет; ложно обещание. (2) MEDIUM: project_cli_doctor.py после подключения --fix-bytecode встал ровно на 500 строк (гейт filesize блокирует при > 500) — нулевой запас, следующая правка сорвёт закрытие. (3) LOW: абзац «Гейт проверяется мутацией» добавлен в docs/ru/architecture.md без EN-зеркала, хотя соседний абзац о трёх звеньях отзеркален.

## Acceptance Criteria

AC1 СПАЙ ВИДИТ ВСЕ ТРИ КАНАЛА ЗАПИСИ, КОТОРЫМИ ПОЛЬЗУЮТСЯ БИЛДЕРЫ: open/io.open (путь), sqlite3.connect (путь БД), subprocess.run/Popen (cwd и любой абсолютный аргумент-путь) — каждый записанный путь обязан лежать под tmp_path; докстринг называет три канала и то, что НЕ перехватывается (os.open, прямые syscalls, дочерний процесс, пишущий по своему усмотрению).
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ (мутации): билдер открывает sqlite вне tmp_path — тест краснеет и называет путь; билдер запускает git с cwd вне tmp_path — тест краснеет; ошибка при пустом списке перехваченных записей — тест краснеет («спай ничего не видит»).
AC3 DOCTOR ВОЗВРАЩАЕТ ЗАПАС: строка Bootstrap drift вынесена в service_doctor_drift.format_scripts_drift_line по образцу format_claudemd_drift_line; текст строк идентичен прежнему (тест на три состояния: None -> warn «could not compare», дрейф -> warn с именами и командой, чисто -> ok); project_cli_doctor.py <= 490 строк; все тесты, зовущие cmd_doctor, зелёные.
AC4 docs/en/architecture.md несёт EN-абзац о правиле мутаций, зеркальный docs/ru.
AC5 Ревью на починку (память #536) агентом; scoped verify зелёный; ruff/mypy чисто; CHANGELOG.md и CHANGELOG.ru.md — дополнены существующие записи смены, синхронно; bootstrap --ide all перед done (правится scripts/).

## Plan

## Rollback

git revert коммита: спай возвращается к open/io.open, строка Bootstrap drift — обратно в doctor, EN-абзац исчезает; поведения гейтов не меняется

## Journal

- 2026-09-03T16:53:09Z [implementation] — ПОЧИНКА ТРЁХ НАХОДОК. (1) Спай в test_the_table_leaves_the_repository_untouched патчит builtins.open, io.open, sqlite3.connect, subprocess.run и Popen; пишет путь БД, cwd и абсолютные аргументы процесса; требует, чтобы каждый канал был задействован. (2) Строка Bootstrap drift вынесена в service_doctor_drift.format_scripts_drift_line, три состояния закреплены tests/test_doctor_drift_row.py; project_cli_doctor.py 500 -> 489. (3) EN-абзац в docs/en/architecture.md; ru дополнен тремя каналами. МУТАЦИИ 5/5 УБИТЫ: sqlite вне tmp_path; subprocess с cwd вне tmp_path; спай sqlite не установлен; None как OK; текст строки изменён — каждая названным тестом. Root cause (missing-validation): обещание «любая запись ловится» покрывало один канал из трёх, которыми пользуются билдеры; doctor подключён без учёта предела размера. Prevention: перечислять каналы записи по ВЫЗОВАМ билдеров (память #527), утверждать в тесте, что каждый канал сработал; перед подключением к файлу у предела — выносить, а не втискивать. Ревью на починку запущено агентом (память #536).
- 2026-09-03T19:12:44Z [implementation] — Verification checklist: AC-1: ✓ tests/test_gates_catch_their_violation.py::test_the_table_leaves_the_repository_untouched. AC-2: ✓ мутации 5/5 в журнале (sqlite вне tmp_path, subprocess вне tmp_path, спай не установлен). AC-3: ✓ tests/test_doctor_drift_row.py::test_the_doctor_uses_the_moved_row_and_has_headroom_again (489 строк). AC-4: ✓ docs/en/architecture.md абзац добавлен. AC-5: ✓ review record L1 #15 (L3 оборван лимитом — долг), verification_run #2000 green, полная лента 8637 passed / 25 skipped / 0 failed (строка прочитана), ruff/mypy чисто, CHANGELOG.md + CHANGELOG.ru.md, bootstrap перед done. Domain: билдер, который уйдёт в sqlite или git вне tmp_path, теперь краснит ленту с именем пути; doctor снова принимает правки.
