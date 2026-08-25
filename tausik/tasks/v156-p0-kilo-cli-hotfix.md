---
slug: v156-p0-kilo-cli-hotfix
title: "P0: Kilo-only установка ломает CLI «no scripts dir found» — добавить kilo в враппер + инжект IDE-списка из _IDE_DIRS"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "bootstrap/tausik_wrapper.sh, bootstrap/tausik_wrapper.cmd, bootstrap/bootstrap_venv.py (install_cli_wrapper), bootstrap/bootstrap.py (_IDE_DIRS, --ide all @254)"
scope_exclude: ".claude/ и прочие сгенерированные копии (правим только источники в bootstrap/); scripts/, docs/, harness/"
relevant_files:
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_modes.py"
  - "bootstrap/bootstrap_venv.py"
  - "bootstrap/tausik_wrapper.sh"
  - "bootstrap/tausik_wrapper.cmd"
  - "tests/test_wrapper_smoke.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:10:34Z"
---

## Goal

Kilo-only установка (bootstrap --ide kilo) должна давать рабочий .tausik/tausik CLI: status exit 0. Корень — wrapper-цикл (.sh:12 / .cmd:11) перебирает claude cursor qwen windsurf codex, БЕЗ kilo, поэтому не находит .kilo/scripts. Глубже: список IDE в враппере должен инжектиться из _IDE_DIRS (bootstrap.py:83) при копировании (install_cli_wrapper в bootstrap_venv.py), чтобы стать единым источником правды. Также свести --ide all (bootstrap.py:254) к ключам _IDE_DIRS.

## Acceptance Criteria

1. tausik_wrapper.sh и tausik_wrapper.cmd содержат kilo в цикле перебора IDE (через инжект, не хардкод). 2. install_cli_wrapper (bootstrap_venv.py) подставляет список IDE из ключей _IDE_DIRS в плейсхолдер шаблона враппера при копировании. 3. --ide all (bootstrap.py:254) выводится из ключей _IDE_DIRS, а не хардкод-списка. 4. Smoke: bootstrap --ide kilo в temp-каталог → .tausik/tausik status exit 0 (и .tausik/tausik.cmd на Windows). 5. Регрессия: bootstrap --ide claude по-прежнему даёт рабочий CLI (status exit 0). 6. НЕГАТИВНЫЙ: установка без единого .{ide}/scripts (или после инжекта с пустым списком) → враппер печатает «no scripts dir found» в stderr и завершается exit 1, не падая с синтаксической ошибкой/тихим успехом.

## Plan

[{"step": "\u0418\u0437\u0443\u0447\u0438\u0442\u044c \u0438\u043c\u043f\u043e\u0440\u0442\u044b bootstrap_venv.py \u0438 \u0442\u043e\u0447\u043a\u0443 \u0432\u044b\u0437\u043e\u0432\u0430 install_cli_wrapper \u2014 \u043a\u0430\u043a \u0434\u043e\u0441\u0442\u0430\u0442\u044c _IDE_DIRS \u0431\u0435\u0437 \u0446\u0438\u043a\u043b\u0438\u0447\u0435\u0441\u043a\u043e\u0433\u043e \u0438\u043c\u043f\u043e\u0440\u0442\u0430", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043b\u0435\u0439\u0441\u0445\u043e\u043b\u0434\u0435\u0440 __IDE_LIST__ \u0432 tausik_wrapper.sh (\u0441\u0442\u0440\u043e\u043a\u0430 12) \u0438 .cmd (\u0441\u0442\u0440\u043e\u043a\u0430 11)", "done": true}, {"step": "install_cli_wrapper: \u0447\u0438\u0442\u0430\u0442\u044c \u0448\u0430\u0431\u043b\u043e\u043d, \u043f\u043e\u0434\u0441\u0442\u0430\u0432\u043b\u044f\u0442\u044c \u043a\u043b\u044e\u0447\u0438 _IDE_DIRS \u0432 \u043f\u043b\u0435\u0439\u0441\u0445\u043e\u043b\u0434\u0435\u0440, \u043f\u0438\u0441\u0430\u0442\u044c \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 (\u0430 \u043d\u0435 shutil.copy2)", "done": true}, {"step": "\u0421\u0432\u0435\u0441\u0442\u0438 --ide all (bootstrap.py:254) \u043a list(_IDE_DIRS)", "done": true}, {"step": "Smoke: bootstrap --ide kilo \u0432 temp \u2192 .tausik/tausik(.cmd) status exit 0; \u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\u044f --ide claude", "done": true}, {"step": "\u041d\u0435\u0433\u0430\u0442\u0438\u0432\u043d\u044b\u0439 \u0442\u0435\u0441\u0442: \u043f\u0443\u0441\u0442\u043e\u0439/\u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0439 scripts dir \u2192 exit 1 + \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435", "done": true}, {"step": "verify --task + task done --ac-verified", "done": true}]

## Rollback

git revert коммита — враперы статичны, изменения изолированы в bootstrap/. Старые установки не затрагиваются до следующего bootstrap.

## Journal

- 2026-06-19T19:07:45Z [implementation] — Реализация: (1) перенёс IDE_DIRS (6) в bootstrap_config.py как единый источник; добавил SCAFFOLD_IDES (4) для --ide all + argparse choices (решение юзера — две константы). (2) bootstrap.py: _IDE_DIRS=alias, --ide all → SCAFFOLD_IDES. (3) bootstrap_modes.py: choices=[*SCAFFOLD_IDES,"all"]. (4) Враперы .sh/.cmd: хардкод-список → плейсхолдер __IDE_LIST__ (и в error-сообщении). (5) install_cli_wrapper: читает шаблон, подставляет " ".join(IDE_DIRS), пишет с нормализацией EOL (.sh→LF, .cmd→CRLF). Kilo теперь в списке сканирования.
- 2026-06-19T19:10:12Z [implementation] — AC verified: 1.✓ Враперы .sh/.cmd содержат kilo через инжект — rendered IDE_LIST="claude cursor windsurf codex qwen kilo" (grep на отрендеренном .sh; .cmd аналогично). 2.✓ install_cli_wrapper подставляет " ".join(IDE_DIRS) в __IDE_LIST__ — test_rendered_wrapper_contains_kilo PASSED, плейсхолдер заменён в обоих. 3.✓ --ide all → SCAFFOLD_IDES (4: claude,cursor,qwen,kilo); argparse choices=[*SCAFFOLD_IDES,'all'] — подтверждено импорт-смоком (choices=['claude','cursor','qwen','kilo','all']). 4.✓ Kilo-only discovery: .cmd test_passthrough[.kilo] PASSED; .sh kilo-only вручную в git-bash → STUB_OK status, exit 0 (LF EOL). 5.✓ Регрессия .claude: .cmd test_passthrough[.claude] PASSED. 6.✓ НЕГАТИВНЫЙ: нет scripts dir → ровно одна строка 'no scripts dir found', exit 1 (.cmd test + .sh вручную). Полный прогон tests/-k bootstrap/wrapper/ide: 375 passed, 4 skipped. Примечание: тест покрывает реальный путь install_cli_wrapper+discovery (корень бага), а не полный venv-bootstrap (venv/pip ортогональны фиксу).
- 2026-06-19T19:10:34Z [implementation] — AC verified: 1.✓ Враперы .sh/.cmd содержат kilo через инжект — rendered IDE_LIST="claude cursor windsurf codex qwen kilo". 2.✓ install_cli_wrapper подставляет " ".join(IDE_DIRS) в __IDE_LIST__ — test_rendered_wrapper_contains_kilo PASSED. 3.✓ --ide all → SCAFFOLD_IDES(4); choices=[*SCAFFOLD_IDES,'all'] подтв. импорт-смоком. 4.✓ Kilo-only: .cmd test_passthrough[.kilo] PASSED; .sh kilo-only в git-bash → STUB_OK status exit 0 (LF EOL). 5.✓ Регрессия .claude PASSED. 6.✓ НЕГАТИВНЫЙ: нет scripts dir → одна строка 'no scripts dir found', exit 1. Прогон tests/ -k bootstrap/wrapper/ide: 375 passed, 4 skipped. Примечание: покрыт реальный путь install_cli_wrapper+discovery (корень бага), не полный venv-bootstrap.
