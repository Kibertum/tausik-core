---
slug: hook-bypass-telemetry-silent-miss
title: "bypass-строка молча теряется: хуки игнорируют landed/miss bool, счёт выключений не фальсифицируем"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/hooks/hook_supervision.py (fallback-сток + drain), tests/ (новый или существующий тест supervision telemetry). Возможно surfacing pending в doctor если дёшево."
scope_exclude: "4 хука (task_gate/scope_write_gate/bash_write_gate/memory_pretool_block) НЕ трогаем — fix центральный; backend metrics не меняем (реконсиляция даёт обычные events-строки)."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "docs/_generated/constants.json"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "scripts/hooks/bash_cmd_norm.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "scripts/hooks/hook_supervision.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "scripts/hooks/secret_scan.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_hooks.py"
  - "tests/test_secret_scan_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T16:17:13Z"
---

## Goal

Тезис релиза 1.8: любое ослабление надзора обязано оставлять СЧИТАЕМЫЙ след, иначе заявление о принуждении нефальсифицируемо. Сейчас след теряется молча. `emit_supervision_bypass` возвращает bool ровно затем, чтобы каллер мог отличить приземлившуюся строку от проглоченного промаха (memory #274), но task_gate.py, scope_write_gate.py, bash_write_gate.py и memory_pretool_block.py этот bool игнорируют. Промах реален в двух режимах: (а) окно между bootstrap и init — `.tausik/` есть, БД нет, юрисдикция ЕСТЬ, строка не пишется; (б) заблокированная/битая БД в обычной работе — WAL + одновременные MCP/CLI/хуки, это не редкость. Итог: TAUSIK_SKIP_HOOKS=1 срабатывает, надзор ослаблен, и НИКТО об этом не узнает. Обратная сторона находки ревью s128, чья исходная посылка опровергнута (dead end #290). Нужно решить и реализовать, куда девать промах: повтор, файловый fallback-сток рядом с БД с последующей сверкой, или явный вывод в stderr — но молчание недопустимо. Учесть потолок: сток и есть та БД, которая только что не ответила.

## Acceptance Criteria

1. Промах записи supervision-события (нет БД в окне bootstrap→init; заблокированная/битая БД) больше НЕ теряется молча: `_emit_supervision` при промахе пишет счётный след в файловый fallback-сток `.tausik/supervision_pending.jsonl` (сток ОТЛИЧНЫЙ от только что отказавшей БД). 2. Fix центральный (в эмиттере), а не в 4 хуках — игнорирование bool каллерами становится безвредным; все нынешние и будущие каллеры покрыты. 3. Реконсиляция: при СЛЕДУЮЩЕЙ успешной записи pending-записи вливаются в `events` с ИСХОДНЫМ timestamp'ом промаха → становятся countable в metrics (_supervision_by_action). 4. Никогда не блокирует и не бросает (best-effort, потолок: если и файл недоступен — last-resort stderr). 5. Конкурентность (WAL + одновременные MCP/CLI/хуки): drain через rename, чтобы не терять параллельные append. 6. Тесты: промах без БД пишет в pending; промах при битой БД пишет в pending; успешный emit вливает pending в events с сохранением времени; конкурентный append не теряется. 7. Полная суита зелёная, 0 warnings.

## Plan

## Rollback

git revert; изменение аддитивно в hook_supervision.py — откат возвращает прежний best-effort return False без стока.

## Journal

- 2026-07-26T16:17:11Z [implementation] — AC verified: 1. ✓ test_bypass_telemetry.py::TestFileFallbackSink::test_missing_db_writes_pending + test_broken_db_writes_pending — miss lands in .tausik/supervision_pending.jsonl 2. ✓ fix in _emit_supervision (emitter), 4 hooks untouched; scope_exclude honored 3. ✓ test_pending_reconciled_on_next_success — backlog folded into events, supervision_bypasses_summary counts bypass_skip_hooks=1 4. ✓ _append_pending/_drain_pending self-guarded (never raise); test_broken_db_never_raises still green; last-resort stderr path 5. ✓ os.replace atomic claim; test_orphaned_draining_file_recovered — crashed-drain leftover recovered 6. ✓ test_reconciliation_preserves_original_timestamp (2020 ts preserved); 6 new tests, telemetry suite 50 passed 7. ✓ tausik_verify high pytest PASS over 5 mapped files; profiles redeployed; filesize 246<400; constants matching 8. ✓ Domain: in a real bootstrap→init window or a locked-DB moment the skip-hooks weakening is now recorded to a file and later counted in metrics — falsifiable enforcement restored. Negative: test_no_tausik_dir_no_pending_file — no jurisdiction, no spurious file
