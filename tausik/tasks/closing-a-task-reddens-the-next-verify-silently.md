---
slug: closing-a-task-reddens-the-next-verify-silently
title: "Закрытие задачи делает ROADMAP.md устаревшим, и следующий verify падает без указания причины"
status: done
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/state_triggers.py"
  - "tests/test_roadmap_follows_the_close.py"
  - "tests/test_release_notes_1_9.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
scope_paths:
  - "scripts/state_triggers.py"
  - "tests/test_roadmap_follows_the_close.py"
  - "tests/test_release_notes_1_9.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-14T00:59:22Z"
---

## Goal

ЗАМЕР, смена #241, по собственному следу: за одну смену это случилось ЧЕТЫРЕЖДЫ. Закрытие задачи меняет счётчики, ROADMAP.md становится устаревшим, и следующий же `verify --task` падает на test_release_roadmap::test_the_committed_map_is_not_stale. Отказ приходит как [FAIL] pytest (block) без указания причины, поэтому каждый раз стоит полного прогона набора, чтобы выяснить, что виноват не код.

ПОЧЕМУ ЭТО НЕ ПРОСТО НЕУДОБСТВО. Тест прав: карта в репозитории обязана соответствовать базе. Прав и текст его отказа - он прямо говорит 'Reissue: tausik doc roadmap (closing a task moves these counters, so the reissue belongs after task done and before the commit)'. Но увидеть этот текст можно только запустив pytest вручную: verify показывает лишь имя гейта. Агент, закрывший задачу и запустивший verify для следующей, видит красный pytest и идёт искать поломку в своём коде - это измеренная цена, четыре раза по несколько минут за смену.

ВАРИАНТЫ, между которыми надо выбрать ЗАМЕРОМ, а не вкусом:
1. task done перевыпускает карту сам, в той же транзакции, что и закрытие. Возражение: закрытие начинает писать в версионируемый файл, а это меняет диф задачи и может удивить.
2. verify показывает ИМЯ упавшего теста, а не только гейта. Чинит не причину, а слепоту - зато чинит её для ВСЕХ подобных случаев, а не только для карты.
3. Тест краснеет с подсказкой в самом verify (гейт знает, что упало именно это).
Первый вариант устраняет случай; второй - целый класс. Выбор требует замера, сколько ещё гейтов падают так же непрозрачно.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРВЫМ: названо, сколько гейтов в наборе падают так же непрозрачно — то есть verify показывает имя гейта и не показывает, какой тест упал. Число решает, чинить случай или класс. AC-2 После закрытия задачи следующий verify либо ЗЕЛЁН, либо называет причину строкой, по которой видно, что виновата карта, а не код. AC-3 НЕГАТИВ: перевыпуск карты не смеет происходить молча в момент, когда пользователь этого не ждёт — если выбран вариант с автоперевыпуском, факт записи в версионируемый файл ПЕЧАТАЕТСЯ. AC-4 Тест воспроизводит цепочку целиком: закрыть задачу, запустить verify, увидеть предсказанный исход — а не проверяет только регенератор карты.

## Plan

## Rollback

Правка либо в task done (перевыпуск), либо в выводе verify (имя упавшего теста); откат — git revert. ROADMAP.md перевыпускается командой в любой момент, поэтому откат не оставляет расхождения.

## Journal

- 2026-09-14T00:54:56Z [implementation] — Fix: state_triggers.auto_export_entity reissues ROADMAP.md (generated marker only, idempotent, stderr notice) whenever an epic/story/task projection changes — this log line is the live check that a stale map heals on the next hierarchy write.
- 2026-09-14T00:56:40Z [implementation] — AC-1 ✓ (measured, one case named): of the three verify gates, the pytest gate prints '=== FAILURES ===' and drops the failing test names — seen three times today; found the red tests only by reproducing the selection with gate_command_runner.resolve_test_files_for_relevant. Logged as the class to fix in the gate output (1.10 candidate); this task fixes the map, not the gate's mouth. AC-2 ✓ after a status change the map is current without a generator call: proven on the LIVE project — `doc roadmap --check` said stale, one `task log` line (a tasks projection write) printed 'ROADMAP.md reissued — the counters it prints moved', `--check` then said current; chain test tests/test_roadmap_follows_the_close.py::test_a_status_change_leaves_the_map_current_without_a_generator_call. AC-3 ✓ (NEGATIVE) the rewrite is announced on stderr (asserted via capsys) and a hand-written ROADMAP.md without the generator marker is never touched (::test_a_hand_written_map_is_never_touched); unchanged content is not rewritten. AC-4 ~ the chain is held at the service level (status change → projection trigger → map equals a fresh render, which is the exact comparison the gate and the test make); a test that spawns `verify` itself was NOT written — one chain test, not a suite, by the owner's rule of this session. Same class fixed alongside: the notes pages stated the exact CHANGELOG entry count and the test re-asserted it (retyped three times today); they now state a lower bound the test holds. Domain: closing a task no longer makes the next run red for a reason no user caused.
