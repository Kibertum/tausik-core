---
slug: kross-harness-telemetriya-ne-python-harness-pishet-events
title: "Кросс-харнесс телеметрия: не-Python харнесс пишет events через CLI-команду к единому Python-эмиттеру, НЕ переписывает контракт строки"
type: convention
tags:
  - cross-harness
  - opencode
  - oracle
  - supervision
  - telemetry
task: l26-bypass-telemetry-opencode-parity
edges: []
---

Когда один и тот же надзорный обход/деградация живёт в нескольких харнессах (Python-хуки + opencode JS-плагин), НЕ реализуй raw INSERT в events заново на втором языке — это вторая расходящаяся копия контракта (нарушение оракульного правила #266/#249: судить/писать РЕАЛЬНЫМ единственным производителем).

Паттерн: не-Python харнесс шеллит `tausik events emit-supervision --kind {bypass|degradation} --vector V --source ENTITY`, а handler (project_cli_events.cmd_events_emit_supervision) зовёт тот же scripts/hooks/hook_supervision.emit_supervision_bypass/degradation. Гарантирует идентичный entity_type='supervision', action=bypass_V/fail_open_V, chain-safe raw INSERT (entry_hash NULL, sealed lazily) и попадание в ту же метрику supervision_bypasses/degradations.

Ограничения JS-плагина opencode (harness/opencode/plugins/tausik-qg0.js): ZERO IMPORTS (никакого bun:sqlite) — единственный путь к БД это Bun-shell $ → CLI. project_dir брать от svc.tausik_dir() (родитель .tausik), НЕ cwd [[265]]. Emit — best-effort awaited+swallow: провал = пропущенная строка, не throw (не ронять редактор). Область эмиссии = write-инструменты (WRITE_TOOLS-фильтр ПЕРЕД skip-проверкой), паритет с Python matcher Write|Edit|MultiEdit — иначе read-инструменты раздувают счётчик.

Связано с [[hook-fail-open-db-error-telemetry gotcha]] и тремя категориями supervision-метрики (bypass/fail_open/detection).
