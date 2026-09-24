---
slug: hook-wall-clock-tax-per-bash-call-is-unmeasured
title: "Надбавка хуков на вызов Bash не измерена никем: восемь процессов, 578 мс при последовательном исполнении"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/memory_pretool_block.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/hooks/bash_firewall.py"
  - "scripts/hooks/bash_write_gate.py"
  - "scripts/hooks/git_push_gate.py"
  - "scripts/hooks/tool_choice_nudge.py"
  - "scripts/hooks/task_call_counter.py"
  - "scripts/hooks/posttool_usage.py"
  - "scripts/hooks/activity_event.py"
  - "scripts/hooks/tool_output_truncation_nudge.py"
  - "scripts/hooks/task_cost_budget_check.py"
  - "bootstrap/bootstrap_hooks.py"
scope_paths:
  - "scripts/hooks/"
  - "bootstrap/bootstrap_hooks.py"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:55:30Z"
---

## Goal

НАЙДЕНО РЕВЬЮ СМЕНЫ #229, ЗАМЕРОМ, А НЕ ЧТЕНИЕМ. На каждый вызов Bash в этом проекте срабатывает ВОСЕМЬ хуков, каждый отдельным процессом Python. Медианы по 9 прогонов каждого: memory_pretool_block 92 мс, bash_write_gate 86, tool_output_truncation_nudge 78, git_push_gate 77, bash_firewall 69, secret_scan 65, activity_event 62, task_call_counter 50. Сумма 578 мс на вызов.

МАСШТАБ. В корпусе этого проекта 9844 вызова Bash, то есть около 95 минут стенных часов, если хуки исполняются ПОСЛЕДОВАТЕЛЬНО.

ЧЕСТНАЯ ОГОВОРКА, БЕЗ КОТОРОЙ ЧИСЛО ЗАВЫШЕНО: последовательность НЕ НАБЛЮДАЛАСЬ. Замер запускал хуки по одному; если харнесс запускает совпавшие хуки параллельно, настоящая цена ближе к максимуму (92 мс), а не к сумме. Поведение харнесса здесь не проверялось, и первым делом задачи должно быть именно это — иначе будет исправляться выдуманная величина.

ПОЛ ЦЕНЫ ИЗМЕРЕН ОТДЕЛЬНО: пустой интерпретатор Python стартует за 29 мс, значит примерно половина цены каждого хука есть запуск процесса, а не работа. Импорты добавляют ещё около 30 мс: read_ledger_gate при ВЫКЛЮЧЕННОМ рычаге тратит 58 мс, из них 29 на интерпретатор и 30 на импорт _common и read_ledger ДО проверки, включён ли он вообще.

ПОЧЕМУ ЭТО НЕ В 1.9. Ни одно из двух обещаний релиза на этом не держится: обещана экономия ТОКЕНОВ, а здесь стенные часы, и обещано качество на любой модели, а задержка хука качества не меняет. Задача заведена, чтобы число не потерялось, а не чтобы расширить объём.

ЧТО ДЕЛАЕТСЯ, ЕСЛИ БРАТЬ: сперва выяснить, последовательно ли харнесс исполняет совпавшие хуки; затем решить, что дешевле — отложенный импорт (перенести тяжёлые импорты ЗА проверку включённости), объединение нескольких хуков в один процесс, или ничего. Отложенный импорт у read_ledger_gate осложнён тем, что дешёвая проверка конфига в обход load_effective_config воспроизвела бы уже известный дефект обхода трастовых тиров.

## Acceptance Criteria

1. Whether the harness runs the hooks matched by one Bash call sequentially or in parallel is MEASURED on this machine (process creation timestamps of the hook interpreters), not assumed.
2. Each of the eleven hooks matched by Bash is timed standalone (median of 7) next to the bare interpreter floor, so the per-call cost is stated as a number with its formula.
3. The decision (deferred imports, merging hooks into one process, or nothing) is recorded with those numbers; the answer 'nothing' closes the task with the reason and changes no hook.
4. NEGATIVE: the probe changes no hook and no gate; git shows the hook sources untouched at close.

## Plan

## Rollback

git revert <commit>. Правки такого рода касаются порядка импортов и состава хуков; поведение гейтов не меняется, и откат возвращает прежнюю задержку.

## Journal

- 2026-09-23T22:55:22Z [implementation] — AC-1: ✓ measurement — ctypes poller (Toolhelp snapshot + GetProcessTimes, 2 ms period, 40 s) during two Bash calls: PreToolUse burst = 5 python.exe created within 14.3 ms (7378685.6..7378699.9), PostToolUse burst ~212 ms later = 6 created within 11.6 ms; the second call repeats it (5 within 11.8 ms, then 6 within 14.8 ms). The harness runs matched hooks IN PARALLEL; the 578 ms 'sum' premise of the task does not hold.
- 2026-09-23T22:55:23Z [implementation] — AC-2: ✓ measurement — standalone medians of 7 (session #269): pre memory_pretool_block 55, bash_write_gate 49, git_push_gate 47, bash_firewall 46, secret_scan 45; post tool_output_truncation_nudge 67, posttool_usage 55, task_call_counter 45, task_cost_budget_check 45, activity_event 44, tool_choice_nudge 42; bare interpreter 22. Per call = max(pre) + max(post) ~ 55 + 67 = ~120 ms, not 578. Eleven hooks match Bash, not eight.
- 2026-09-23T22:55:23Z [implementation] — AC-3: ✓ measurement — decision: NOTHING. Headroom = (55-22) + (67-22) ~ 78 ms per call even if every hook were cut to a bare interpreter; x 9844 Bash calls in the corpus ~ 13 min over the project's whole history. Deferred imports would have to be done in ALL hooks of a phase to move the max, and read_ledger_gate's cheap-config path reintroduces the trust-tier bypass. Merging hooks into one process trades isolation (one crash disables all) for the same ~78 ms. Not worth a change in 1.10.
- 2026-09-23T22:55:23Z [implementation] — AC-4: ✓ measurement — negative: git status over the 11 hook sources and bootstrap/bootstrap_hooks.py is empty; the probes lived in the session scratchpad only. Caveat logged: the standalone probe fed PostToolUse hooks a synthetic payload (session_id 'probe'), so activity_event may have recorded up to 7 probe events.
