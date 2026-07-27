---
slug: sostoyanie-proekta-chitaetsya-cherez-self-tausik-dir
title: "Состояние проекта читается через self.tausik_dir()/переданный каталог, НИКОГДА от cwd"
type: convention
tags:
  - config
  - cwd
  - project-handle
  - tausik_dir
  - v2-global-mcp
task: mcp-config-read-paths-ignore-project-handle
edges: []
---

Экземплярный метод сервиса, отвечающего за КОНКРЕТНЫЙ проект (ProjectService, backend по db_path), обязан резолвить конфиг/гейты/пути через self.tausik_dir() (= dirname(be.db_path)), а функции слоя конфига — принимать параметр tausik_dir. Резолвинг от os.getcwd() (find_tausik_dir без аргумента) описывает проект, В КОТОРОМ СТОИТ ПРОЦЕСС, а не запрошенный. Дефект невидим пока cwd совпадает с корнем проекта (одиночный CLI/MCP) и молча ломается на мульти-проектном сервере (эпик v2-global-mcp), где svc станет носителем идентичности.

ДВАЖДЫ: путь ЗАПИСИ — mcp-gate-toggle-mutates-real-project-config (#125, писал в чужой config.json), путь ЧТЕНИЯ — mcp-config-read-paths-ignore-project-handle (#126, gates_status/status описывали чужой проект). Природа одна, вес разный (запись рушит состояние, чтение врёт).

ГРАНИЦА: параметризуется ТОЛЬКО проектный тир (load_project_config). Тиры user (~/.tausik) и managed ($TAUSIK_MANAGED_CONFIG) — ПЕР-МАШИННЫЕ, от каталога проекта зависеть НЕ ДОЛЖНЫ, иначе новый дефект вместо старого (config_trust.resolve читает их из env/home).

ТЕСТ, ловящий класс: svc на tmp_path с ОТЛИЧНЫМ составом (unguarded-сигнал типа bootstrap.stacks-маркера, т.к. enabled/severity/trigger переписываются config_trust) — метод обязан вернуть состав ЭТОГО каталога, а не cwd-проекта. autouse _guard_live_project_config ловит только запись, не чтение.
