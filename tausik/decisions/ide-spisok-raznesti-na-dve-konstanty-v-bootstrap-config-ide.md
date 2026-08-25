---
slug: ide-spisok-raznesti-na-dve-konstanty-v-bootstrap-config-ide
task: v156-p0-kilo-cli-hotfix
date: "2026-06-20"
edges: []
---

## Decision

IDE-список разнести на ДВЕ константы в bootstrap_config: IDE_DIRS (6, wrapper-discovery) и SCAFFOLD_IDES (4, --ide all + argparse choices), а не сводить всё к одному списку.

## Rationale

Три рассинхронизированных списка кодировали ДВА разных концепта: где могут лежать scripts (wrapper сканирует все 6 включая windsurf/codex) vs какие IDE реально скаффолдятся (только 4 имеют generate_*_config). windsurf/codex есть в IDE_DIRS, но без ветки генерации — сведение --ide all к полному IDE_DIRS дало бы полу-битые установки. Решено с юзером (AskUserQuestion). Каждый концепт — один источник; добавление IDE: в IDE_DIRS всегда, в SCAFFOLD_IDES только когда есть генератор.
