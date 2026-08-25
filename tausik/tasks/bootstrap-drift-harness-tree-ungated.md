---
slug: bootstrap-drift-harness-tree-ungated
title: "Дрейф дерева harness/ (не scripts/) не гейтится: правка harness/claude/mcp/* может не доехать до .claude/mcp/*"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: bootstrap-drift-not-gated-stale-runtime
scope: "bootstrap/bootstrap_check.py (новый — scaffold в temp + сравнение), bootstrap/bootstrap.py + bootstrap_modes.py (--check флаг), scripts/gate_bootstrap_drift.py (зов нового check для harness+scripts), tests/ (внесённый дрейф, инертность, генерируемые не ложат)"
scope_exclude: "НЕ менять copy-функции bootstrap_copy.py (temp-подход не требует). НЕ покрывать skills/ (config-зависимая генерация стабов + rmtree), stacks/references (config-зависимо/крупно) — задокументировать как известную границу в сообщении гейта. НЕ трогать self_check (протухшие живые модули — задача #77/#79/#80)."
relevant_files:
  - "bootstrap/bootstrap_check.py"
  - "bootstrap/bootstrap_modes.py"
  - "bootstrap/bootstrap.py"
  - "scripts/gate_bootstrap_drift.py"
  - "tests/test_bootstrap_check.py"
  - "tests/test_bootstrap_drift_gate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-20T23:34:44Z"
---

## Goal

ВЫНЕСЕНО ИЗ bootstrap-drift-not-gated-stale-runtime (сессия #125) ОСОЗНАННО. Та задача закрыла дрейф дерева scripts/ по всем профилям гейтом bootstrap_drift. Дерево harness/ осталось НЕ покрыто, и это отдельная задача по трём причинам, а не по забывчивости.

ПОЧЕМУ ОТДЕЛЬНО. harness/ раскладывается в профиль НЕ вербатим: harness/claude/* распределяется в .claude/{mcp,skills,references,roles,...}, harness/opencode/* в .opencode/... и т.д. Сравниватель по именам (как для scripts/, где scripts/foo.py -> {profile}/scripts/foo.py один-к-одному) для harness НЕ РАБОТАЕТ: пришлось бы воспроизвести логику раскладки bootstrap второй формулой, а она разъедется молча (конвенция #249) — ровно то, чего гейт и должен избегать.

ПОЧЕМУ ЭТО РЕАЛЬНО. В этой же сессии я правил harness/claude/mcp/project/handlers.py и проверял доезд до .claude/mcp/project/handlers.py ВРУЧНУЮ через diff. Класс тот же, что у scripts/: правка source может не вступить в силу при зелёном прогоне, потому что MCP грузится из .claude/mcp/, а тесты импортируют из harness/ или scripts/. Смежный self_check (гичи #77/#79/#80) следит за 11 модулями в ЖИВОМ процессе — другая задача (протухший модуль), не доезд правки.

ЧТО СДЕЛАТЬ — варианты к решению внутри задачи. (1) НЕ писать второй сравниватель, а сделать bootstrap САМ сообщать расхождения: добавить bootstrap режим --check (или расширить --dry-run), который проходит ту же раскладку, но вместо записи СРАВНИВАЕТ и возвращает список несходящихся путей. Тогда оракул — сам код раскладки, одна формула. Гейт зовёт этот режим. Это чище варианта (2) и закрывает разом и scripts/, и harness/. (2) Если (1) дорого — байтовое дерево-сравнение .claude/harness/ vs harness/ (там, где harness кладётся вербатим как подкаталог), но это покрывает не весь доезд.

НЕГАТИВНЫЕ, ОБЯЗАТЕЛЬНЫЕ: (а) проверить ВНЕСЁННЫМ дрейфом (правка harness/claude/mcp/*.py без пересборки роняет проверку); (б) инертность без профилей (свежий клон/CI, harness-профили в .gitignore); (в) не падать на файлах, которые bootstrap ГЕНЕРИРУЕТ (settings.json, CLAUDE.md, .mcp.json) — они не копии source, а генерируются, и сравнивать их с source бессмысленно. Именно поэтому наивное дерево-сравнение профиля целиком даст ложные срабатывания — отсюда предпочтение варианту (1).

## Acceptance Criteria

AC1. bootstrap_check.check_deployed_trees(lib_dir, project_dir, ides=None): для каждого ПРИСУТСТВУЮЩЕГО профиля раскладывает copy-деревья (scripts, mcp, roles, subagents, aidd) во ВРЕМЕННЫЙ каталог ТЕМИ ЖЕ copy-функциями bootstrap (одна формула, конвенция #249), байтово (CRLF-норм, игнор __pycache__/.pyc) сравнивает с установленным профилем, возвращает отсортированный список несходящихся .{ide}/{rel}.
AC2. bootstrap --check: печатает дрейф и exit 1 при наличии, exit 0 при чистоте; не пишет в проект.
AC3. gate_bootstrap_drift зовёт новый check и БЛОКИРУЕТ закрытие при дрейфе harness/mcp — с именами файлов и командой bootstrap --ide all.
AC4. Край (внесённый дрейф): правка harness/claude/mcp/*.py без пересборки → check возвращает этот путь; доказано тестом.
AC5. Инертность: нет профилей (.{ide} отсутствуют, свежий клон/CI) ИЛИ bootstrap/ не импортируется → пустой список и гейт пропускает без ошибки.
AC6. Генерируемые файлы (settings.json, CLAUDE.md, .mcp.json) не дают ложных срабатываний — они не раскладываются в temp, поэтому не сравниваются.
AC7. Временный каталог удаляется гарантированно, в т.ч. при исключении.
AC8. Регресс: полный suite зелёный; существующий scripts-дрейф гейт продолжает ловить scripts/.

## Plan

## Rollback

git revert коммита. Аддитивно: новый модуль bootstrap_check.py + флаг --check + расширение гейта; copy-функции bootstrap_copy.py НЕ меняются (temp-подход), откат не затрагивает путь развёртывания.

## Journal

- 2026-07-20T23:32:14Z [implementation] — Реализовано (вариант 1 — одна формула): bootstrap_check.check_deployed_trees раскладывает harness copy-деревья (mcp, roles, subagents, aidd) во ВРЕМЕННЫЙ каталог ТЕМИ ЖЕ copy-функциями bootstrap и байтово (CRLF-норм) сравнивает с установленным профилем. scripts/ остаётся на быстром scripts_drift_names (1:1). bootstrap --check зовёт оба компаратора (0.98с vs 8.2с при включённом scripts-scaffold — исключён). gate_bootstrap_drift зовёт оба, блокирует при дрейфе harness/mcp с именами+командой, называет границу (skills/stacks/references не покрыты). Генерируемые файлы не раскладываются → не ложат. temp удаляется в finally. 11 новых тестов (внесённый дрейф, инертность без профилей/harness, генерируемые не ложат, temp cleanup, gate wiring) + 12 существующих gate-тестов зелёные. Полный suite 5173 passed. Догфуд: --check поймал бы ручные diff-проверки этой сессии.
- 2026-07-20T23:32:35Z [implementation] — AC1-8 verified: AC1 ✓ check_deployed_trees через реальные copy-функции в temp — TestHarnessDrift. AC2 ✓ bootstrap --check exit1 при дрейфе, 0.98с (измерено). AC3 ✓ gate блокирует harness-дрейф с именами+командой — TestGateWiring. AC4 ✓ внесённый дрейф (v2 source vs v1 deployed) → test_stale_deployed_copy_is_named. AC5 ✓ инертность: нет профиля/harness → [] (TestInertness). AC6 ✓ генерируемые (settings.json) не ложат — TestGeneratedFilesNotFlagged. AC7 ✓ temp удаляется — test_no_temp_dirs_left_behind. AC8 ✓ scripts-гейт цел (12 тестов), полный suite 5173 passed. Domain: --check на живом репо поймал scripts-дрейф всех 5 профилей за 0.98с; harness fan-out судится реальной раскладкой bootstrap (одна формула, #249), не второй копией. Negative: инертность на свежем клоне и отсутствии bootstrap/ доказана.
- 2026-07-20T23:34:12Z [implementation] — AC1-8 verified (детали в предыдущем логе). bootstrap.py ужат до 400 строк (filesize) сжатием комментариев — без изменения логики. Полный suite 5173 passed, verify #1119 PASS, --check exit0.
- 2026-07-20T23:34:29Z [implementation] — AC1-8 verified (детали в логе). bootstrap.py=400 строк. suite 5173 passed, --check exit0.
- 2026-07-20T23:34:42Z [implementation] — Root cause (missing-validation): гейт bootstrap_drift покрывал дрейф ТОЛЬКО дерева scripts/ (1:1 раскладка), а дерево harness/ (фан-аут harness/claude/mcp/* -> .claude/mcp/*) осталось без проверки — правка source MCP могла не доехать до исполняемой копии при зелёном прогоне, потому что MCP грузится из .claude/mcp/, а тесты импортируют из scripts/harness. Вынесено осознанно из #125 (там закрыт scripts/). Prevention: harness судится РЕАЛЬНОЙ раскладкой bootstrap (copy-функции в temp + байт-сравнение), а не второй копией логики раскладки (конвенция #249); добавлен bootstrap --check + расширен гейт. Догфуд: --check поймал бы ручные diff-проверки этой сессии.
- 2026-07-20T23:34:43Z [implementation] — AC1-8 verified + root cause logged. suite 5173 passed, --check exit0, bootstrap.py=400.
