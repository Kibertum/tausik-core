---
slug: reconcile-udalenie-po-lyubomu-md-pod-root-smetaet
title: "Reconcile-удаление по «любому *.md под root» сметает рукописные файлы в git-native проекции"
type: gotcha
tags:
  - data-loss
  - export
  - git-native
  - reconciliation
  - safety
task: state-git-export
edges: []
---

Экспортёр DB→дерево, который реконсилит удаления (сносит managed-файлы на диске, отсутствующие в сгенерированном дереве), НЕ должен считать managed «любой *.md под root» через голый os.walk. Контракт git-native проекции прямо приглашает человекочитаемые файлы (README, заметки, «открывать Obsidian'ом как vault») — и первый же прогон `state export` без --check молча os.remove()'ит их, потому что build_tree возвращает только ключи-сущности (tasks/<slug>.md), а всё прочее невидимо. assert_export_target защищает лишь от НЕВЕРНОГО каталога, но не от чужих файлов в ВЕРНОМ. Решение: (1) экспортёр владеет только известными подкаталогами сущностей ({epics,stories,tasks,decisions,memory}) — managed-скан скоупится по первому сегменту пути, файлы вне этих каталогов неприкосновенны; (2) удаления не молчаливые — write_tree возвращает deleted_paths, CLI печатает каждое. Тихая потеря данных на каноническом источнике правды — худший класс. Поймано адверсариальным ревью state-git-export. Тот же паттерн живёт в renar_export.py (скоуп renar/, риск теоретический).
