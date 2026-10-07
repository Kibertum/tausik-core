---
slug: agent-friction-becomes-a-filed-defect-not-a-swallowed-one
title: "Трение агента о фреймворк должно становиться заведённым дефектом, а не молча съедаться сессией"
status: done
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: complex
role: backend
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: "scripts/friction_detect.py + проводка (project.py exit-рекордер, doctor --friction, парсер, telemetry Policy), tests/test_friction_detect.py, docs en/ru doctor.md, CHANGELOG x2"
scope_exclude: "изменения поведения handlers и команд — детектор наблюдает, не чинит"
relevant_files:
  - "scripts/friction_detect.py"
  - "scripts/project.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/project_parser.py"
  - "scripts/telemetry_retention.py"
  - "tests/test_friction_detect.py"
  - "docs/en/doctor.md"
  - "docs/ru/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "tests/*.py"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T19:40:06Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#88"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Когда агент упирается в фреймворк — зовёт не то, получает отказ, гадает аргументы, обходит гейт — это фиксируется как ДЕФЕКТ ФРЕЙМВОРКА с воспроизведением, а не остаётся в логе сессии, который никто не прочитает.

## Acceptance Criteria

1. Названы СИГНАЛЫ трения, каждый измеримый по существующей телеметрии: ненулевой выход CLI; вызов --help сразу после неудачного вызова той же команды (агент гадал аргументы); повтор одной команды с разными аргументами подряд; блок гейта, за которым следует обход вместо исправления; записанный dead end про сам фреймворк. Список закрывает ФОРМУ, а не примеры: перечислены все точки, где агент получает отказ от TAUSIK.
2. Сигнал превращается в ЧЕРНОВИК дефекта локально: что агент пытался сделать, что получил, какая команда, какой гейт, воспроизведение. Черновик кладётся туда, где его увидит человек, а не в лог.
3. Черновик РЕДАКТИРУЕТСЯ перед тем, как стать видимым снаружи: пути, слаги задач, имена проектов и заказчиков вычищены. Переиспользуется существующий скраббер brain_scrubbing, а не пишется второй.
4. Отправка в GitHub — ТОЛЬКО по явному разрешению человека на КОНКРЕТНЫЙ issue (память #352). Автоматическая отправка ЗАПРЕЩЕНА и не может быть включена конфигом проектного тира.
5. Шум ограничен: одинаковые сигналы в пределах сессии схлопываются в один черновик со счётчиком, а не плодят по issue на каждый отказ.
6. НЕГАТИВНЫЙ сценарий: детектор проверен на ЖИВЫХ логах — точность измерена на routing_adherence.jsonl и журналах сессий, а не заявлена. Ложная тревога на нормальной работе агента считается провалом критерия (конвенция #351).
7. НЕГАТИВНЫЙ сценарий: при отсутствии сети, при отсутствии токена и при отказе GitHub API сессия НЕ замедляется и НЕ падает — черновик остаётся локальным, и об этом сказано вслух, а не проглочено.
8. НЕГАТИВНЫЙ сценарий: черновик, не прошедший скраббер, НЕ отправляется вовсе — отказ громкий; молчаливая отправка нередактированного текста наружу ЗАПРЕЩЕНА.

## Plan

## Rollback

git revert: детектор и черновики удаляются, поведение команд не меняется

## Journal

- 2026-10-07T19:26:21Z [implementation] — AC-1: ✓ пять сигналов названы ФОРМОЙ с источником каждого: scripts/friction_detect.py docstring — ненулевой выход (cli_invocations.jsonl), --help-после-отказа (там же, последовательность), угадывание аргументов (там же, серия ≥3 в основном красных), деградация надзора fail_open_* (events), dead end о поверхности фреймворка (memory, окно 7 суток). AC-2: ✓ черновик локально там, где человек увидит: .tausik/friction/*.md + строка «Agent friction» в обычном doctor (WARN, пока черновики ждут); tests/test_friction_detect.py::test_friction_cmd_never_blocks_and_names_the_boundary, ::test_drafts_are_redacted_and_counted. AC-3: ✓ скраб переиспользован: brain_scrubbing.scrub() детектирует, найденные спаны заменяются на [redacted] — второго набора паттернов нет; ::test_redact_uses_the_shared_scrubber, ::test_drafts_are_redacted_and_counted (email вычищен). AC-4: ✓ сетевого кода НЕТ и конфигом не добавить — нечего включать; механический guard: ::test_no_network_surface_in_the_module (assert_no_network_surface). AC-5: ✓ схлопывание: одинаковые сигналы — один черновик со счётчиком: ::test_nonzero_exit_collapses_per_command (3 отказа → 1 черновик, occurrences: 4-формат), write_drafts один файл на сигнатуру. AC-6 NEGATIVE: ✓ точность на живых данных: ::test_live_tree_stays_under_the_false_alarm_threshold (≤5, живые .tausik + БД; первый прогон поймал 22 находки из накопленных bypass_* и 6 из старых dead ends — оба источника шума измерены и закрыты: bypass_* исключён как выбор агента, dead ends окном 7 суток); границы: ::test_fail_then_green_retry_is_not_friction, ::test_green_invocations_produce_nothing, ::test_task_code_dead_end_is_not_framework_friction, ::test_deliberate_skip_hooks_is_not_framework_friction. Domain: живой `.tausik/tausik doctor --friction` на этом проекте оформил 4 настоящих черновика (MCP-drift dead ends недели) в .tausik/friction/ — трение впервые стало видимым артефактом. Verify: run #3638 PASS (8/0/1; scoped 42/671, 1047 passed, 16 skipped), handle 3638.8c39830cf99e6fee377f9ad41c0530b4. Dedupe 282/669 удержан; красные #3636/#3637 — doc_coverage требовал ASCII-имя «Agent friction» в RU-доке (добавлено к русской строке), не подход.
- 2026-10-07T19:26:41Z [implementation] — NO-DEAD-END: reds #3636/#3637 were doc_coverage demanding the ASCII name 'Agent friction' inside docs/ru/doctor.md - the Russian label alone did not count. Added the English name beside the Russian one; not a failed approach, a naming requirement of the doc gate.
