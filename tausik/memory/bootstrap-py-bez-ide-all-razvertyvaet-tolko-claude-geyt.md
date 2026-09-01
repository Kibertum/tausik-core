---
slug: bootstrap-py-bez-ide-all-razvertyvaet-tolko-claude-geyt
title: "bootstrap.py без --ide all развёртывает ТОЛЬКО claude; гейт дрейфа краснеет на четырёх остальных профилях"
type: gotcha
tags:
  - bootstrap
  - drift
  - gates
  - task-done
task: write-gate-takes-a-file-descriptor-number-as-a-write-target
edges: []
---

Память #499 велит прогонять bootstrap перед командой CLI, читающей свежую правку в scripts/. Этого НЕДОСТАТОЧНО для закрытия задачи.

`python bootstrap/bootstrap.py` без аргументов разворачивает один профиль — .claude/. Установлено же пять: .claude, .cursor, .kilo, .opencode, .qwen. Гейт bootstrap_drift на `task done` проверяет ВСЕ и валит закрытие: «8 deployed file(s) do NOT match source», по два файла на каждый из четырёх непрогретых профилей.

ЛЕЧЕНИЕ: `python bootstrap/bootstrap.py --ide all`. Голый `--update` обновляет только claude и тоже НЕ спасает — это сказано в самом тексте отказа гейта.

ПОРЯДОК, ЧТОБЫ НЕ ПЛАТИТЬ ДВАЖДЫ: обычный bootstrap — во время работы, как только правка в scripts/ должна доехать до выполняющегося хука; `--ide all` — один раз перед `task done`. Прогон занимает секунды, но verify после него надо ПЕРЕЗАПУСТИТЬ: handle протухает, потому что файлы изменились.

Гейт покрывает не всё: skills/, stacks/ и references/ не проверяются (задача bootstrap-drift-harness-tree-ungated).
