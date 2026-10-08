---
slug: answer-length-has-no-ratchet
title: "Длина ответа измеряется, но ничто не краснеет на её росте"
status: done
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/answer_budget_ratchet.py"
  - "tests/test_answer_budget_ratchet.py"
  - "scripts/project_cli_doctor.py"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
scope_paths:
  - "scripts/answer_budget_ratchet.py"
  - "tests/test_answer_budget_ratchet.py"
  - "tausik/gates.json"
  - "scripts/project_cli_doctor.py"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T12:01:10Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Рост длины ответа краснеет. tausik metrics answers даёт число с 1.10, но ничто на него не смотрит — ровно так история J закрылась как сделанная, пока медиана росла с 396 до 522. Храповик читает ЛОКАЛЬНЫЕ транскрипты, поэтому отсутствие данных — это отсутствие, а не ноль, и не отказ.

## Acceptance Criteria

1. Базовая линия записана в tausik/gates.json из ЗАМЕРА, не из желаемого; может только уменьшаться. 2. Тест краснеет, когда локальная медиана или p90 превысили базовую линию. 3. НЕГАТИВНЫЙ: транскриптов нет — тест пропускается с названной причиной, а не считает это нулём и не падает; число не переносится между машинами, как red_history. 4. НЕГАТИВНЫЙ: улучшение НЕ роняет тест, но печатает новое меньшее число, чтобы его записали. 5. Строка в doctor: текущая медиана против базовой линии. 6. Полная лента зелёная.

## Plan

## Rollback

git revert; храповик читает транскрипты и ничего не пишет, кроме строки doctor. Откат возвращает состояние «измеряем и забываем».

## Journal

- 2026-09-29T12:00:03Z [implementation] — AC-1: ✓ базовая линия в tausik/gates.json[answer_shape] из замера — медиана 522,5, p90 923 по 10 транскриптам и 52 ответам; комментарий называет дату, объём и «может только уменьшаться». ::TestTheBaselineIsAMeasurementNotAWish проверяет, что линия НЕ равна бюджету 200. AC-2: ✓ ::TestGrowthIsTheSignal — три формы роста, каждая называет, какая именно величина выросла. AC-4 НЕГАТИВНЫЙ: ✓ ::TestShrinkingIsNotAFailure — улучшение проходит и печатает меньшее число для записи.
- 2026-09-29T12:00:16Z [implementation] — AC-3 НЕГАТИВНЫЙ: ✓ ::TestAbsenceIsReportedAsAbsence — четыре теста на три разных факта (транскриптов нет; ответов меньше MIN_ANSWERS=20; линии ещё нет; gates.json нечитаем), ни один не отказ. Живой тест ::test_the_live_machine_is_not_above_its_own_baseline пропускается с названной причиной там, где читать нечего: число не ездит между машинами, как red_history. AC-5: ✓ строка doctor «Answer shape: answers at the baseline (52 measured)», задокументирована в docs/{ru,en}/doctor.md — гейт покрытия документации поймал её отсутствие и был прав. AC-6: ✓ полная лента 12249 прошли, 34 пропущены. Domain: храповик прогнан на живых транскриптах этой машины, не только на фикстуре.
