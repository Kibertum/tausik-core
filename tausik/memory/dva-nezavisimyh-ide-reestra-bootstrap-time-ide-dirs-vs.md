---
slug: dva-nezavisimyh-ide-reestra-bootstrap-time-ide-dirs-vs
title: "Два независимых IDE-реестра: bootstrap-time (IDE_DIRS) vs runtime (ide_utils.IDE_REGISTRY)"
type: context
tags:
  - detect
  - ide
  - ide_utils
  - kilo
  - qwen
  - runtime
  - v156
task: v156-p5-ide-utils-qwen-kilo
edges: []
---

В TAUSIK ДВА разных IDE-реестра, не путать (v156):
1. bootstrap_config.IDE_DIRS / SCAFFOLD_IDES — BOOTSTRAP-time: какие .{ide}/ каталоги генерить/сканировать. См. [[ide-spisok-dva-istochnika-pravdy-ide-dirs-discovery-vs-scaffold-ides-generation]] (memory #182).
2. scripts/ide_utils.py IDE_REGISTRY / detect_ide — RUNTIME: под каким IDE сейчас работает агент, чтобы резолвить skill/rules-пути (get_skills_dir/get_ide_dir/get_rules_file). Потребители: project_cli_skill, handlers_skill (MCP), skill_profile_session (SessionStart profile rebuild).
Это РАЗНЫЕ структуры (IDE_REGISTRY хранит config_dir+rules_file+skills_subdir на IDE, IDE_DIRS — только dir). Добавляя новый IDE — НАДО обновить ОБА. В v156 P5 добавлены qwen(.qwen/QWEN.md) и kilo(.kilo/AGENTS.md) в IDE_REGISTRY + project-structure detection в detect_ide. Env-var авто-детект для kilo/qwen НЕ сделан (нужна живая env-сигнатура Kilo/Qwen — помечено pending-live в docstring; детект работает через .kilo/.qwen dir + TAUSIK_IDE override). rules_file для kilo = AGENTS.md (bootstrap генерит generate_agents_md для всех IDE; Kilo читает AGENTS.md).
