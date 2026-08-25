---
slug: v156-p5-ide-utils-qwen-kilo
title: "P5: ide_utils.IDE_REGISTRY не содержит qwen/kilo — skill-резолв под Kilo падает в .claude"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/ide_utils.py (IDE_REGISTRY + detect_ide), tests/test_ide_utils.py"
scope_exclude: "env-var auto-detect для kilo/qwen (нужна живая env-сигнатура — отложено до P3/live); bootstrap-генерация"
relevant_files:
  - "scripts/ide_utils.py"
  - "tests/test_ide_utils.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:43:07Z"
---

## Goal

scripts/ide_utils.py IDE_REGISTRY имеет только claude/cursor/windsurf/codex. Под Kilo detect_ide() не распознаёт kilo → DEFAULT_IDE=claude → get_skills_dir/get_ide_dir резолвят .claude вместо .kilo (skill install/activate + SessionStart profile-rebuild ломаются на Kilo-only установке). Добавить qwen+kilo в IDE_REGISTRY (config_dir/rules_file/skills_subdir) и распознавание в detect_ide. ВАЖНО: auto-detect kilo требует знания env-сигнатуры живого Kilo (какие env-vars ставит Kilo) — overlap с P3 (отложено). Статические записи реестра добавляемы сразу; авто-детект — после подтверждения на живом билде.

## Acceptance Criteria

1. IDE_REGISTRY содержит qwen (config_dir=.qwen, rules_file=QWEN.md, skills_subdir=skills) и kilo (config_dir=.kilo, rules_file=AGENTS.md, skills_subdir=skills); SUPPORTED_IDES автоматически включает оба. 2. detect_ide через project-structure находит kilo (.kilo) и qwen (.qwen); TAUSIK_IDE=kilo/qwen работает как явный override. 3. get_skills_dir/get_ide_dir/get_rules_file для kilo/qwen резолвят .kilo/.qwen, а НЕ .claude. 4. Тесты на новые IDE (registry, detect dir-based, override, path-resolve). 5. НЕГАТИВНЫЙ кейс: TAUSIK_IDE='несуществующий' выбрасывает Ошибку ValueError (не молча падает в claude); env-сигнатуры auto-detect для kilo/qwen помечены pending-live (не угадываем env-vars во избежание ложных срабатываний).

## Plan

[{"step": "IDE_REGISTRY: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c qwen (.qwen/QWEN.md) + kilo (.kilo/AGENTS.md)", "done": true}, {"step": "detect_ide: project-structure detection \u0432\u043a\u043b\u044e\u0447\u0430\u0435\u0442 kilo+qwen; docstring \u043f\u0440\u043e env-pending", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: dir-detect, override, registry values, kilo-only resolve\u2192.kilo", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043e\u043d tests/test_ide_utils.py (37 passed)", "done": true}]

## Rollback

git revert — аддитивные записи реестра + детект, без миграций.

## Journal

- 2026-06-19T19:43:06Z [implementation] — AC verified: AC-1: ✓ IDE_REGISTRY получил qwen(.qwen/QWEN.md/skills) + kilo(.kilo/AGENTS.md/skills); SUPPORTED_IDES автогенерится из ключей — test_kilo_and_qwen_registered, test_*_registry_values PASSED. AC-2: ✓ detect_ide project-structure loop включает kilo,qwen — test_project_dir_detection[.kilo/.qwen] PASSED; TAUSIK_IDE override — test_explicit_tausik_ide_override[kilo/qwen] PASSED. AC-3: ✓ kilo-only install резолвит get_skills_dir→.kilo/skills, get_ide_dir→.kilo (НЕ .claude) — test_kilo_only_install_resolves_to_kilo_not_claude PASSED. AC-4: ✓ tests/test_ide_utils.py 37 passed. AC-5: ✓ НЕГАТИВНЫЙ: TAUSIK_IDE='несуществующий'→ValueError (test_invalid_tausik_ide_raises, существующий); env-auto-detect kilo/qwen помечен pending-live в docstring (не угадываем env-vars). Domain: реальный Kilo-баг (skill-резолв под Kilo падал в .claude) закрыт надёжным путём — dir-detection + override, без рискованных env-догадок. Blind-режим по запросу юзера; rules_file kilo=AGENTS.md подтверждён по bootstrap (generate_agents_md для всех IDE).
