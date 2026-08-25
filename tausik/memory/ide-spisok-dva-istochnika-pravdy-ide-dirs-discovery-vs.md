---
slug: ide-spisok-dva-istochnika-pravdy-ide-dirs-discovery-vs
title: "IDE-список: два источника правды — IDE_DIRS (discovery) vs SCAFFOLD_IDES (generation)"
type: convention
tags:
  - bootstrap
  - ide
  - single-source
  - v156
  - wrapper
task: v156-p0-kilo-cli-hotfix
edges: []
---

bootstrap_config.py держит ДВЕ канонические IDE-константы, не путать:
- IDE_DIRS (6: claude,cursor,windsurf,codex,qwen,kilo) = все каталоги .{ide}/, где могут лежать scripts. Потребители: bootstrap.get_ide_target, wrapper-цикл поиска scripts (инжектится в __IDE_LIST__ через install_cli_wrapper). bootstrap._IDE_DIRS — это alias на IDE_DIRS (обратная совместимость).
- SCAFFOLD_IDES (4: claude,cursor,qwen,kilo) = IDE с реальной веткой генерации в bootstrap.run_for_ide (generate_*_config). Потребители: argparse --ide choices ([*SCAFFOLD_IDES,'all']) и расширение --ide all.
windsurf/codex есть в IDE_DIRS (wrapper их найдёт), но НЕ в SCAFFOLD_IDES (нет генератора MCP-конфига), поэтому не выбираются через --ide и не входят в --ide all. Добавляя IDE: в IDE_DIRS — всегда; в SCAFFOLD_IDES — только когда написана ветка generate_*_config. НЕ хардкодить IDE-списки больше нигде.
Враппер .sh/.cmd содержит плейсхолдер __IDE_LIST__ (НЕ хардкод); install_cli_wrapper (bootstrap_venv.py) рендерит его через " ".join(IDE_DIRS) при копировании в .tausik/, с нормализацией EOL (.sh→LF, .cmd→CRLF). Тест-страж: tests/test_wrapper_smoke.py (test_template_has_placeholder_not_hardcoded_list).
