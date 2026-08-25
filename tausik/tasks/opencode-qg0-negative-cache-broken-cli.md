---
slug: opencode-qg0-negative-cache-broken-cli
title: "opencode QG-0 плагин: negative-cache для недостижимого CLI — 2 медленных subprocess на КАЖДУЮ запись при отказе"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: l26-bypass-telemetry-opencode-parity
scope: "harness/opencode/plugins/tausik-qg0.js (_verdict + tool.execute.before fail-open ветка), tests/test_opencode_qg0_plugin.py (новый класс TestUnreachableCliIsThrottled), .opencode/plugins/tausik-qg0.js (регенерация bootstrap), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/hooks/task_gate.py и Python-сторона супервизии (паритет уже есть, не трогаем); контракт events emit-supervision (единый producer, не дублировать); active-вердикт кэш семантика (не менять существующее поведение sig-binding для active)"
relevant_files:
  - "harness/opencode/plugins/tausik-qg0.js"
  - "tests/test_opencode_qg0_plugin.py"
  - ".opencode/plugins/tausik-qg0.js"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T09:18:00Z"
---

## Goal

Ревью s128 (MEDIUM). harness/opencode/plugins/tausik-qg0.js: _verdict() не кэширует деградированное состояние — при выбросе _queryActive() исключение уходит ДО присвоения _cache, поэтому при отказе CLI каждая Write/Edit/apply_patch заново спавнит _queryActive (300ms warm/1.1s cold Windows) И на fail-open ветке ещё await _recordSupervision, который шеллит ТОТ ЖЕ сломанный CLI (events emit-supervision) и обычно тоже падает. Два медленных subprocess без троттлинга на каждую запись пока CLI сломан — ровно та тормознутость, ради устранения которой построен CACHE_TTL/db-signature. Фикс: кэшировать недостижимое состояние с коротким TTL/backoff — один медленный проб на окно вместо двух spawn на запись. Учесть: деградация должна оставаться countable (не терять запись полностью), но не спамить subprocess. Тесты node-драйвером (multi-step scenario с cliFails).

## Acceptance Criteria

AC1. Кэш недостижимого CLI: на withBun-пути при недостижимом CLI серия из N write-операций с НЕИЗМЕННОЙ сигнатурой БД стоит РОВНО ОДИН probe `status --compact` за TTL-окно, а не N. Тест node-драйвером: 3 write, cliFails, calls==1, queried=[True,False,False].

AC2. Деградация остаётся countable, но не спамит subprocess: та же серия эмитит РОВНО ОДНУ supervision-запись (degradation/cli_unreachable), привязанную к РЕАЛЬНОМУ probe, а не к каждой записи (fresh-probe throttle). Тест: emits length==1; при этом fail-open остаётся ГРОМКИМ — warning DEGRADED печатается на КАЖДУЮ запись (warnings length==3), т.к. это дешёвый console.warn, не subprocess.

AC3. Инвалидация по сигнатуре: сдвиг сигнатуры БД (dbMtime) между шагами заставляет заново пробовать И заново эмитить (recovery-detection) — calls==2, emits==2.

AC4. Без сигнатуры (нет Bun) недостижимое состояние НЕ переиспользуется — зеркалит правило «active-true без сигнатуры не кэшируется» (мягкое направление): каждая запись пробует заново, calls==N, emits==N.

AC5. Fail-secure: при недостижимом CLI серия записей блокируется, probe при этом кэшируется (calls==1 на 3 шага), degradation НЕ эмитится (guard срабатывает раньше пути телеметрии).

AC6. Регрессий нет: все существующие TestFailurePolicy / TestCacheErrsTowardStrictness / TestSupervisionTelemetryParity зелёные. Сгенерированная копия .opencode/plugins/tausik-qg0.js пересобрана bootstrap --ide all (source→artifact parity).

CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита: изменения изолированы в tausik-qg0.js (source + generated copy) и тестовом файле + CHANGELOG. Нет миграций БД, нет изменения схемы событий. Откат восстанавливает прежнее (buggy, но безопасное — fail-open/secure логика неизменна) поведение без потери данных.

## Journal

- 2026-07-27T09:15:51Z [implementation] — Root cause: _verdict let _queryActive() exception escape ДО присвоения _cache — недостижимое состояние не кэшировалось, каждая запись re-spawn probe + fail-open await _recordSupervision (шеллит тот же сломанный CLI). Фикс: (1) кэш недостижимого вердикта под тем же sig+TTL стражем, reuse только при sig!=null && match; (2) _unreachableError(reason, freshProbe) — throw несёт freshProbe; caller пропускает _recordSupervision при freshProbe===false (reused). Warning остаётся per-write (дешёвый console.warn). TDD: 5 тестов TestUnreachableCliIsThrottled (2 red→green: calls==1). Все 43 теста зелёные. bootstrap --ide all: source==generated parity OK. CHANGELOG ×2.
- 2026-07-27T09:17:58Z [implementation] — AC verified: 1. ✓ tests/test_opencode_qg0_plugin.py::TestUnreachableCliIsThrottled::test_repeated_writes_while_cli_broken_probe_and_emit_once — 3 write, cliFails, sig неизменна: calls==1, queried=[True,False,False]. Кэш недостижимого вердикта под sig+TTL стражем. 2. ✓ тот же тест: emits length==1 (fresh-probe throttle через freshProbe===false в caller), warnings length==3 (per-write console.warn, не subprocess). Деградация countable, но не спамит. 3. ✓ test_db_signature_move_reprobes_and_reemits (calls==2, emits==2) + test_broken_cli_recovers_within_window_is_seen_on_signature_move (sig-move → повторный проб, recovery виден, blocked=[False,False]). 4. ✓ test_without_signature_broken_cli_reprobes_every_write — with_bun=False: calls==3, emits==3. Без sig недостижимое не переиспользуется (мягкое направление), зеркалит active-true правило. 5. ✓ test_fail_secure_broken_cli_probes_once_and_never_emits — FAIL_SECURE: all blocked, calls==1 (probe кэшируется), emits==[] (guard раньше пути телеметрии). 6. ✓ Регрессий нет: 43/43 test_opencode_qg0_plugin + 58 (bootstrap+doctor opencode) + 119 (changelog/check_docs/gen_doc_constants/bootstrap_hooks_parity/mcp_single_canonical_tree/doc_drift) зелёные. bootstrap --ide all: diff source vs .opencode/plugins → PARITY OK. doc-constants test_count lower-bound подтверждён (+5 тестов не тронули). 7. ✓ CHANGELOG.md + CHANGELOG.ru.md [Unreleased] — прозаическая запись про устранение двух медленных subprocess на запись при сломанном CLI.
- 2026-07-27T09:18:13Z [done] — Root cause (performance): _verdict позволял исключению _queryActive() уйти ДО присвоения _cache, поэтому недостижимое состояние CLI никогда не кэшировалось — каждая запись re-spawn probe + fail-open await эмита супервизии (шеллит тот же сломанный CLI) = два медленных subprocess на запись. Prevention: кэшировать И деградированный вердикт под тем же sig+TTL стражем; тесты node-драйвером пинят calls==1 на серию (burst throttle), чтобы регрессия «проб на запись» падала. Domain: реальный сломанный CLI (missing .cmd / syntax error) на Windows — 1.1с cold spawn ×2 на каждый Write/Edit; фикс сводит к 1 пробу + 1 эмиту на TTL-окно, политика fail-open/secure неизменна.
