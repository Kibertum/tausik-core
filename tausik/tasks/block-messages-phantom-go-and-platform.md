---
slug: block-messages-phantom-go-and-platform
title: "Самое частое блок-сообщение фреймворка указывает на несуществующую команду /go и на POSIX-путь CLI"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/tausik_utils.py (хелпер), scripts/hooks/task_gate.py, scripts/hooks/bash_write_gate.py, scripts/hooks/keyword_detector.py, scripts/hooks/bash_firewall.py, scripts/hooks/scope_write_gate.py, scripts/gate_verify_first.py, scripts/gate_changelog.py, harness/skills/interview/SKILL.md, tests/ (линт скиллов + тесты хелпера), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "gate_filesize.py и secret_scan.py (их remediation — отдельная задача про качество сообщений гейтов), 60+ вхождений .tausik/tausik в доках/brain-модулях, создание нового скилла /go (решено: не плодить сущность, /plan уже покрывает), bash_firewall BLOCKED_PATTERNS (список паттернов не меняем)"
relevant_files:
  - "scripts/tausik_utils.py"
  - "scripts/hooks/_common.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/bash_write_gate.py"
  - "scripts/hooks/keyword_detector.py"
  - "scripts/hooks/bash_firewall.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "scripts/gate_verify_first.py"
  - "scripts/gate_changelog.py"
  - "harness/skills/interview/SKILL.md"
  - "harness/skills/start/SKILL.md"
  - "tests/test_block_message_quality.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T17:47:12Z"
---

## Goal

scripts/hooks/task_gate.py:162 — блок, который агент видит чаще любого другого, — советует «use /go». Скилла go не существует: ни в harness/skills/, ни в .claude/skills/ (brain, checkpoint, commit, debug, end, explore, interview, plan, reason, review, ship, start, task, test), и .claude/commands/ нет. Та же фантомная ссылка в interview/SKILL.md:84-89. Плюс сообщение предлагает русскую фразу в англоязычном тексте аудитории, к которой README обращается по-английски. Смежно, системно: ВСЕ ~30 remediation-строк хардкодят POSIX-форму `.tausik/tausik ...`, тогда как на Windows (машина разработки проекта) это `.tausik/tausik.cmd` — нужен один platform-aware хелпер, а не 30 правок. Также в этот же класс: bash_firewall.py:250 инструктирует «попроси подтверждения пользователя», но пути после подтверждения НЕ существует (в отличие от git_push_gate с одноразовым тикетом на 60с и brain_search_proactive с маркером) — сообщение описывает механизм, который не построен; bash_firewall.py:244 (SQL table drop) не даёт никакого remediation при задокументированных в самом файле ложных срабатываниях; gate_filesize.py:96 не упоминает ни gate.exempt_files, ни настраиваемый max_lines; secret_scan.py:105 — предупреждение, единственная опция которого делает его громче, без allowlist.

## Acceptance Criteria

AC1 (фантомная команда). Ни одно сообщение фреймворка не советует несуществующий скилл. `/go` заменён на реально существующие пути (`/plan` — создать задачу, `/task <slug>` — продолжить) в scripts/hooks/task_gate.py, bash_write_gate.py, keyword_detector.py и harness/skills/interview/SKILL.md. Тест-линт: каждый упомянутый в сообщениях хуков `/skill` обязан существовать в harness/skills/ — падает при появлении новой фантомной ссылки.
AC2 (язык). Англоязычное блок-сообщение не содержит русской фразы как ЕДИНСТВЕННОГО способа действия: инструкция даётся командой, а не фразой на языке, которого читатель может не знать.
AC3 (платформа — уточнено измерением). Исходная гипотеза аудита («нужен .cmd») ОПРОВЕРГНУТА: расширение ни при чём, PATHEXT резолвит его сам. Реальная причина — РАЗДЕЛИТЕЛЬ: в cmd.exe `.tausik/tausik` не распознаётся, в Git Bash не работает `.tausik\tausik`, PowerShell принимает обе. Универсальной строки нет, поэтому: хелпер выбирает форму по ОБОЛОЧКЕ (Windows + признаки MSYS/Git Bash → прямые слэши; Windows без них → обратные; POSIX → прямые). Тесты на все три ветки через подмену окружения.
AC4 (применение). Хелпер применён в remediation блокирующих сообщений (task_gate, bash_write_gate, scope_write_gate, gate_verify_first, gate_changelog); прочие 60+ вхождений в доках и brain-модулях в этой задаче НЕ трогаем — объём диффа против пользы, зафиксировать в заметках.
AC5 (сообщения без выхода). bash_firewall не инструктирует действие, которого не существует: ветка `git reset --hard` сейчас советует «спросить подтверждения у пользователя», хотя пути после подтверждения В КОДЕ НЕТ. Либо путь появляется, либо сообщение перестаёт его обещать. Тест.
AC6. Полный прогон pytest зелёный, без warnings. AC7. CHANGELOG.md + CHANGELOG.ru.md обновлены прозой.

## Plan

## Rollback

git revert коммита. Хелпер аддитивен — при откате строки возвращаются к литералам; поведение гейтов не меняется, только тексты сообщений, поэтому частичный откат безопасен пофайлово через git checkout --.

## Journal

- 2026-07-23T17:37:25Z [implementation] — Реализовано. cli_invocation в tausik_utils выбирает форму CLI по ОБОЛОЧКЕ (замерено: cmd.exe не понимает .tausik/tausik, Git Bash не понимает .tausik\\tausik, PowerShell принимает обе — расширение .cmd ни при чём, PATHEXT его резолвит, решает РАЗДЕЛИТЕЛЬ). Гипотеза аудита про .cmd опровергнута замером и зафиксирована в докстринге таблицей. Мост _common.cli_invocation для хуков (одна реализация, не копия — чтобы не расползлась как четыре копии root_from_service). Фантомный /go убран из task_gate, bash_write_gate, keyword_detector, user_prompt_submit и interview/SKILL.md; линт test_block_message_quality требует, чтобы каждый /skill в сообщениях хуков и в SKILL.md существовал в harness/skills/. Линт нашёл СВЕРХ заявленного аудитом ещё три фантома: /go в user_prompt_submit (аудит указал только task_gate+interview) и /metrics + /next в start/SKILL.md — заменены на реальные tausik metrics / tausik task next. bash_firewall: ветка git reset --hard больше не обещает «спросить подтверждения» (пути после подтверждения в коде нет — user says yes, хук блокирует так же), теперь называет реальный выход TAUSIK_SKIP_HOOKS=1 с записью supervision-события; тест проверяет, что обещанный механизм реально существует в хуке. Точки применения хелпера: task_gate, bash_write_gate, gate_verify_first (_CLI), gate_changelog (_CLI). Осознанно НЕ трогал 60+ вхождений .tausik/tausik в доках и brain-модулях (объём диффа против пользы) и remediation gate_filesize/secret_scan (отдельная задача про качество сообщений гейтов). Мета-гейт test_hook_encoding поймал мой em-dash в print-строке firewall (хук не форсирует UTF-8) — вернул ASCII-дефис, сообщение снова ASCII-only.
- 2026-07-23T17:47:10Z [implementation] — AC1 ✓ /go убран из task_gate, bash_write_gate, keyword_detector, user_prompt_submit, interview/SKILL.md; заменён на /plan и tausik task start. Линт test_hooks_reference_only_existing_skills + test_skill_docs_reference_only_existing_skills требуют существования каждого /skill; fail-then-pass test_the_lint_would_catch_a_phantom проверяет, что матчер ловит именно /go. Линт нашёл СВЕРХ аудита: /go в user_prompt_submit, /metrics + /next в start/SKILL.md — тоже исправлены. AC2 ✓ англ. блок-сообщение task_gate даёт команду (/plan, task start), а не только русскую фразу (test_task_gate_offers_a_command_not_only_a_russian_phrase). AC3 ✓ Domain+Negative: гипотеза аудита про .cmd ОПРОВЕРГНУТА замером на реальной машине — cmd.exe отвергает .tausik/tausik (WinWright 255), Git Bash отвергает .tausik\tausik, PowerShell принимает обе; расширение резолвит PATHEXT. cli_invocation выбирает по ОБОЛОЧКЕ: posix→/, nt без MSYS→\, nt+MSYSTEM/MSYS/POSIX-SHELL→/; 7 тестов TestCliInvocation, включая negative (SHELL=cmd.exe не флипает ответ). AC4 ✓ хелпер применён в task_gate, bash_write_gate, gate_verify_first (_CLI), gate_changelog (_CLI); тесты TestGatesUseTheHelper проверяют, что литерала .tausik/tausik в этих гейтах не осталось. 60+ вхождений в доках/brain НЕ трогал — зафиксировано в заметках. AC5 ✓ bash_firewall не обещает несуществующий путь подтверждения; test_warn_branch_does_not_promise_a_confirmation_path (по коду без комментариев) + test_warn_branch_names_the_escape_that_exists проверяют, что советуемый TAUSIK_SKIP_HOOKS реально читается хуком. AC6 ✓ полный прогон 5427 passed / 23 skipped, без warnings; мета-гейт test_hook_encoding поймал мой em-dash в print-строке firewall — вернул ASCII. AC7 ✓ проза в обоих CHANGELOG. Negative: проверено, что линт ПАДАЕТ на фантоме (/go ∉ skills) и что cli_invocation НЕ флипается на не-POSIX SHELL — обе защиты активны, не пусты.
- 2026-07-23T17:47:10Z [implementation] — Root cause (documentation): remediation-строки писались как ПРОЗА, а не как проверяемый факт — ни фантомный /go, ни POSIX-путь CLI ничем не были связаны с реальностью (списком скиллов, оболочкой запуска), поэтому расходились с ней молча; тот же класс, что у cost-pricing (число без источника) и doctor (литерал вместо абстракции): 'правило/текст есть, механизма связи с истиной нет'. /go пережил месяцы, потому что сообщение никто не исполнял до конца — читатель видел строку и уходил. Prevention: (1) линт test_block_message_quality связывает каждый /skill в сообщениях с harness/skills/ — сразу нашёл 3 фантома сверх заявленного; (2) факт про оболочку получен ЗАМЕРОМ (таблица cmd/PowerShell/Git Bash), а не предположением — гипотеза аудита про .cmd опровергнута; (3) обещанный механизм обязан существовать: тест firewall проверяет, что TAUSIK_SKIP_HOOKS реально читается хуком, прежде чем сообщение его советует; (4) урок: сообщение-инструкция — это код, а не текст, и подлежит тем же проверкам «делает ли то, что говорит».
