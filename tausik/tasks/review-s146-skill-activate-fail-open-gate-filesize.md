---
slug: review-s146-skill-activate-fail-open-gate-filesize
title: "Review-фиксы s146: skill_activate обходит контент-скан + fail-open декод + узкий охват + gate_filesize матч"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: l26-skill-supply-chain-threat
scope: null
scope_exclude: "Не менять ed25519-подпись (supply_verify_install); не трогать логику активации кроме вставки скана; не рефакторить copy_skill/skill_activate сверх общего helper'а; не менять max_lines/cap."
relevant_files:
  - "scripts/skill_content_scan.py"
  - "scripts/skill_manager.py"
  - "scripts/service_skills.py"
  - "scripts/gate_filesize.py"
scope_paths:
  - "scripts/skill_content_scan.py"
  - "scripts/skill_manager.py"
  - "scripts/service_skills.py"
  - "scripts/gate_filesize.py"
  - "tests/test_skill_content_scan.py"
  - "tests/test_skill_activate_supply_chain.py"
  - "tests/test_gates.py"
  - "docs/en/skill-supply-chain-threat-model.md"
  - "docs/ru/skill-supply-chain-threat-model.md"
  - "docs/en/security.md"
  - "docs/ru/security.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T17:57:30Z"
---

## Goal

Адверсариальное ревью кода сессии #146 (l26-skill-supply-chain-threat + l26-filesize-gate-revisit) нашло 3 critical + 2 medium, все подтверждены чтением кода. C1 (critical): service_skills.py:196 skill_activate копирует вендор-скилл в .claude/skills/ через свой shutil.copytree с ПОДПИСЬЮ, но БЕЗ контент-скана — обходит choke point copy_skill, что делает ложным заявление threat-model про «единственную узкую точку»; это рецидив install/activate дрейфа, о котором предупреждает докстринг skill_tree_ignore. C2 (critical): skill_content_scan._SCANNED_SUFFIXES只 .md/.markdown/.txt — payload в references/*.py, data/*.json, scripts/*.py, которые SKILL.md велит агенту открыть/запустить, проходит. C3 (critical, fail-open): scan_skill_tree except UnicodeError: continue молча пропускает файл, не прошедший strict UTF-8, но copytree копирует его байт-в-байт → payload с одним битым байтом + U+E0000 доезжает. M1: _committed_gates_config_path walk-up от cwd без .git-границы — может подхватить чужой tausik/gates.json в монорепо/CI. M2: exempt_dirs матчатся unanchored substring ('tests/' ловит 'unittests/') — рецидив-риск растёт с внешне-редактируемым конфигом.

## Acceptance Criteria

1. C1: skill_activate (service_skills.py) прогоняет тот же invisible-Unicode скан, что и copy_skill — общий helper, ни один путь в .claude/skills/ не минует скан; регресс-тест: активация отравленного SKILL.md блокируется.
2. C3: scan_skill_tree декодит errors='replace' (не strict), skip только на OSError — файл с битым байтом всё равно сканируется; тест с невалидным UTF-8 + U+E0000 ловится.
3. C2: охват скана расширен на текстовые файлы, которые скиллы поставляют (.py/.json/.yaml/.yml/.rst/.cfg/.toml/.ini/.html/.csv/.sh + прежние); тест: payload в references/*.py ловится.
4. M1: walk-up привязан к .git-границе (не поднимается выше корня репо). M2: exempt_dirs матчатся по границе path-сегмента, не подстрокой — тест: 'unittests/' НЕ исключён token'ом 'tests/', а 'tests/foo.py' и 'docs/ru/research/x.md' исключены.
5. threat-model doc + security.md обновлены: choke point теперь ДВА пути (install+activate) оба со сканом; охват файлов уточнён. CHANGELOG EN+RU.

## Plan

## Rollback

git revert коммита; все правки аддитивны/хирургичны (общий helper скана + errors=replace + расширенный suffix-список + .git-якорь + boundary-матч), реверт восстанавливает прежнее поведение; DB/схему не трогает

## Journal

- 2026-07-27T17:57:03Z [implementation] — AC verified (все 5 findings ревью закрыты): AC1/C1 ✓ общий guard assert_skill_tree_clean зовут ОБА пути (copy_skill+skill_activate); tests/test_skill_activate_supply_chain.py::TestContentScanEnforced (signed+poisoned блокируется, reference.py payload блокируется, ничего не приземляется). AC2/C3 ✓ errors=replace, skip только OSError; test_invalid_utf8_byte_does_not_hide_payload (битый байт+U+E0000 ловится). AC3/C2 ✓ _SCANNED_SUFFIXES расширен (.py/.json/.yaml/.rst/.toml/.ini/.html/.csv/.sh...); test_payload_in_reference_py/data_json_is_found. AC4/M1 ✓ walk-up стоп на .git (test_committed_config_lookup_stops_at_git_root); M2 ✓ _path_under_exempt_dir по границе сегмента (test: 'tests/' не ловит 'unittests/'/'backtests/'; bloated в unittests/ блокируется). AC5 ✓ docs EN+RU: choke point теперь ДВА пути, охват уточнён; security.md обновлён. 133 таргет-теста + 589 broad PASS, ruff+mypy clean, verify #1526 exit=0. Domain: реальная атака (signed-but-compromised publisher со скрытым U+E0000) теперь блокируется на ОБОИХ путях установки. Negative: отравленный скилл падает и на install, и на activate; битый-UTF8 файл сканируется а не пропускается. Closing via CLI.
- 2026-07-27T17:57:28Z [implementation] — Root cause (integration-mismatch): контроль безопасности (invisible-Unicode скан) добавили в ОДИН из ДВУХ путей в один и тот же sink (.claude/skills/) — install/copy_skill просканирован, activate/skill_activate имел свою копию shutil.copytree и остался без скана; это рецидив известного install/activate дрейфа (та же ошибка ранее была у проверки подписи). Сопутствующие: fail-open (strict-декод пропускал невалидный UTF-8, C3) и узкий охват (.md-only, C2) — оба класс 'проверка не покрывает весь вход, который доезжает до sink'. Prevention: контроль на sink оформлять ОДНИМ общим guard'ом (assert_skill_tree_clean), который зовут все пути, а не дублировать per-path; регресс-тест на КАЖДЫЙ путь; декод контента для security-скана всегда errors=replace, не strict.
