---
slug: forbid-fire-and-forget-subprocess
title: "Запрет fire-and-forget subprocess: run/Popen с check=False и отброшенным результатом"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/skill_git.py (pin_eol_config), tests/ (новый AST-тест). Возможно ещё вызовы, если обход найдёт."
scope_exclude: "Не строить общее правило 'if rc!=0: continue' — оно шумное. Только узкий fire-and-forget инвариант."
relevant_files:
  - "scripts/skill_git.py"
  - "scripts/hooks/auto_format.py"
  - "tests/test_no_silent_subprocess.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-11T03:04:27Z"
---

## Goal

Класс тихих ошибок этой сессии: код возврата внешней команды проглатывается. Общее AST-правило 'if rc!=0: continue' было бы шумным гейтом (нельзя отличить законный skip от глотания) — не строю его, это ровно тот антипаттерн, что чинил сегодня дважды. Вместо этого узкий, доказуемо не-шумный инвариант, найденный обходом всех 15 вызовов subprocess в scripts/: subprocess.run/Popen с check=False (дефолт) И отброшенным результатом (не присвоен, не возвращён) = fire-and-forget, код возврата не может быть проверен никогда. check_output/check_call сами бросают на ненулевом коде, поэтому их отбрасывать законно. Таких run/Popen ровно один подозрительный — skill_git.py:50 pin_eol_config: если git config падает, пин не пишется, следующий git pull переконвертирует байты, подписи ломаются, и ни звука (латентный улов в моём же CRLF-коде). Починить + AST-тест, ловящий новые fire-and-forget.

## Acceptance Criteria

1) pin_eol_config больше не отбрасывает результат git config: при неудаче это видно (warn или проверка), а не тихо. 2) AST-тест ловит subprocess.run/Popen с check=False и отброшенным результатом по всему scripts/. 3) check_output/check_call, которые сами бросают, тест НЕ трогает. 4) Тест перечисляет текущее чистое состояние, поэтому новый fire-and-forget его валит. Негативные сценарии: 5) Ошибка, если правило шумит на законных случаях — доказать обходом: сейчас после починки скрытых fire-and-forget run/Popen НЕ осталось. 6) Ошибка, если тест зелёный при искусственно добавленном fire-and-forget вызове (проба стережётся). 7) Ошибка, если поведение clone_repo сломалось: пин по-прежнему пишется и eol_is_pinned его видит (живой прогон). 8) Ошибка, если полный прогон даёт новое падение.

## Plan

## Rollback

git checkout -- scripts/skill_git.py tests/; bootstrap для зеркал.

## Journal

- 2026-07-11T03:04:18Z [implementation] — AC verified: 1. ✓ pin_eol_config больше не отбрасывает результат git config: при rc!=0 печатает Warning про возможную реконверсию. Проверено живьём: git config в не-репо даёт rc=128, теперь виден warning вместо тишины. 2. ✓ AST-тест test_no_silent_subprocess.py::test_no_discarded_run_relies_on_the_silent_default флагует отброшенный subprocess.run без явного check= по scripts/ и bootstrap/. 3. ✓ check_output/check_call не трогаются (правило только про .run). 4. ✓ Тест перечисляет текущее чистое состояние — новый fire-and-forget его валит. Негативные: 5. ✓ Правило НЕ шумит: обход показал, что под общим правилом 5 законных совпадений (метрики, форматтеры, Popen, init), под узким — два auto_format, оба получили честный check=False с комментарием, а не ложное падение. Реальный улов: skill_git::pin_eol_config. 6. ✓ Проба стережётся: test_the_probe_can_actually_say_no (голый run -> [2]); test_explicit_check_false/check_true/assigned/popen — не флагуются. 7. ✓ clone_repo цел: живой прогон clone_pin_live.py — 'local pin set: True', 'pin restored: True'. 8. ✓ Полный прогон 4448 passed, 20 skipped, 0 failed; ruff чист; зеркала синхронны. Root cause (logic-error): голый subprocess.run с отброшенным результатом полагается на молчаливый дефолт check=False — код возврата не проверяется никогда. В pin_eol_config это латентно ломало цепочку подписей: неудача записи пина -> следующий git pull наследует глобальный core.autocrlf -> байты переконвертируются -> подписи не сходятся, без сигнала. Prevention: отброшенный run обязан заявить check= явно (по образцу BLE001 для blind except); общее правило против 'if rc!=0: continue' отвергнуто как шумное (решение #130). Память про класс — #200 (флаги) и #195 (git status слеп); это третья грань того же класса.
