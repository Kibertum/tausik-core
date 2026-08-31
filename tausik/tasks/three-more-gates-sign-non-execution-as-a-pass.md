---
slug: three-more-gates-sign-non-execution-as-a-pass
title: "Ещё три гейта пишут проход, когда исполниться не смогли — два из них блокирующие"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: claudemd-state-gate-reports-passed-when-it-could-not-run
scope: "scripts/gate_bootstrap_drift.py; scripts/gate_state_roundtrip.py; scripts/gate_renar_drift.py; tests/ (тесты этих трёх гейтов). При необходимости — новые NOT_APPLICABLE-коды в scripts/gate_outcome.py, там же, где их объявляют остальные."
scope_exclude: "scripts/gate_runner.py и scripts/gate_run_record.py — механизм замерен исправным в #193, править нечего. scripts/gate_claudemd_state.py — уже починен, это образец, а не цель. Три fail-CLOSED сайта (gate_qg0_check.py, gate_qg0_renar.py, gate_registry.py) — трогать запрещено, см. AC7. Схема: полей outcome/reason_code от v47 достаточно, новой миграции НЕ нужно."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР #193, ПРЯМОЙ, из пересчёта AC6 задачи claudemd-state-gate-reports-passed-when-it-could-not-run. Тот дефект починен в одном файле; ТРИ вердиктных места того же вида остались, и они перечислены поимённо, а не предположены:
  gate_bootstrap_drift.py:84  — гейт bootstrap_drift, severity=BLOCK, trigger task-done;
  gate_state_roundtrip.py:62 и :88 — гейт state_roundtrip, severity=BLOCK, trigger commit;
  gate_renar_drift.py:53 — гейты renar_drift_provenance и renar_drift_schema (общий impl), severity=WARN.
Все возвращают `except Exception as e: return True, "... unavailable (...)"`, то есть проверка, объявившая своё невыполнение, засчитывается пройденной. Для двух BLOCK-гейтов это ровно то, что дало ложную квитанцию #192: любой сбой окружения — устаревший процесс, битый импорт, недоступная БД — красит их зелёным.
МЕХАНИЗМ УЖЕ СТОИТ, ЗАМЕРЕНО В #193: gate_outcome.py даёт COULD_NOT_RUN/NOT_APPLICABLE с обязательным reason_code, gate_runner пропускает результат через coerce() и пишет outcome/reason_code в gate_runs. Правки runner НЕ нужно, новой миграции НЕ нужно. Нужно, чтобы импл возвращал GateOutcome вместо легаси-пары — образец правки целиком лежит в scripts/gate_claudemd_state.py.
ЧЕГО ДЕЛАТЬ НЕЛЬЗЯ, ЗАМЕРЕНО: gate_qg0_check.py:101, gate_qg0_renar.py:28 и gate_registry.py:482 выглядят так же, но их `return True` означает «проверка ОСТАЁТСЯ ВКЛЮЧЕНА» — это fail-CLOSED. Разворот сделал бы fail-open там, где сегодня безопасно. Не трогать; в gate_registry.py:468-482 это прямо объяснено в докстринге.

## Acceptance Criteria

AC1. ДВА BLOCK-ГЕЙТА ПЕРВЫМИ И ОБЯЗАТЕЛЬНО. bootstrap_drift (gate_bootstrap_drift.py:84) и state_roundtrip (gate_state_roundtrip.py:62, :88) записывают невыполнение через could_not_run(REASON_RUNNER_ERROR, ..., remedy=...), а не (True, "unavailable"). Три исхода вместо двух: прошёл, не прошёл, НЕ СМОГ.
AC2. WARN-ГЕЙТ РАЗБИРАЕТСЯ ОТДЕЛЬНО И С ОБОСНОВАНИЕМ. renar_drift (gate_renar_drift.py:53) — severity=warn, и цена fail-open там иная. Решить ЯВНО и записать в журнал: приводить к COULD_NOT_RUN (warn-гейт не заблокирует, но квитанция перестанет врать) или оставить с объяснением. Молчаливое «сделал как у block» и молчаливое «не трогал» одинаково не годятся.
AC3. Честные пропуски каждого гейта остаются НЕ блокирующими и получают СВОИ reason_code через not_applicable — как в gate_claudemd_state.py. Пустой проект не виноват. Один общий код на разные пустые состояния не принимается: он переносит неразличимость, а не снимает её.
AC4. Гейты по-прежнему не роняют коммит и не роняют task-done: исключение перехватывается, меняется только КАК оно записано.
AC5. Замер повторяем, по строке gate_runs, а не по возврату функции: для КАЖДОГО из трёх гейтов тест поднимает сбой, прогоняет настоящий run_gates и предъявляет outcome=COULD_NOT_RUN в строке, которую пишет record_gate_runs. ВНИМАНИЕ, оплачено в #193: conftest держит autouse-фикстуру _mock_run_gates, подменяющую gate_runner.run_gates на (True, []) — имя run_gates связывать на ИМПОРТЕ модуля, иначе тест меряет мок. DDL брать из backend_schema_gate_runs.GATE_RUNS_SQL, не перепечатывать.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ: возврат прежнего `return True` на месте КАЖДОГО из четырёх мест обязан красить тест. Мутация по РЕАЛЬНЫМ БАЙТАМ (файлы scripts/ в дереве LF-only), возврат побайтовой копией со сверкой sha256, git checkout запрещён. В #193 именно эта мутация нашла НЕПОКРЫТОЕ место, которое чтением глазами не находилось — считать её обязательной, а не формальностью.
AC7. Ни один из трёх fail-CLOSED сайтов (gate_qg0_check.py:101, gate_qg0_renar.py:28, gate_registry.py:482) не изменён. Проверить и подтвердить в журнале явно: это защита от «постричь под одну гребёнку», ради которой задача и заведена отдельно.

## Plan

## Rollback

git revert коммита. Правка меняет только КАК записывается исход уже перехваченного исключения; ни схемы, ни данных, ни продуктового поведения она не трогает, обратной миграции не требует (run_migrations односторонний) и откатывается в любой момент без потерь. Промежуточный откат тоже безопасен: гейты независимы, и revert одного файла оставляет остальные в рабочем состоянии.

## Journal
