---
slug: polzovatelskiy-tir-tausik-config-json-neset-obhody-chuzhih
title: "Пользовательский тир ~/.tausik/config.json несёт обходы ЧУЖИХ проектов — баг 1.8, который 1.9 не имеет права повторить"
type: gotcha
tags:
  - config-trust
  - regression-1.8
  - release-1.9
  - user-tier
task: normalize-release-backlog-19-110-20
edges: []
---

ЗАМЕР на машине владельца, смена #243 (2026-09-12): ~/.tausik/config.json содержит ровно две записи, и обе — обходы дефектов конкретных потребительских проектов: gates.bootstrap_drift.enabled=false с _disabled_reason про RENAR (layout submodule, дедэнд #126, тикеты GitHub #7 / GitLab #3) и task_done.auto_verify=true с _reason про vaflower (security_pattern считает весь код о деньгах чувствительным, сессия #11). Обе записи сами предупреждают: «тир общий для всех проектов». Следствие видно живьём: в новом проекте tceh-x (TAUSIK 1.8) агент обнаружил чужой auto_verify=true и был вынужден гасить его project-level auto_verify=false — а doctor 1.8 при этом печатал OK «no project-scope key weakens enforcement». МЕХАНИЗМ: config_trust отвергает ослабление из тира проекта, поэтому единственный канал для обхода — глобальный тир, и обход одного проекта молча становится политикой машины. ЧТО УЖЕ ДЕРЖИТ 1.9: find_tausik_dir не выдаёт ~/.tausik за проект (tests/test_the_home_tier_is_not_a_project.py); config set пишет только в .tausik/config.json проекта; doctor через config_trust_weakening называет ослабления user-тира и предупреждает, когда они в силе (здесь: «tightened back here»); сам фреймворк в ~/.tausik ничего проектного не пишет (аудит grep expanduser по scripts/, hooks/, bootstrap/). ЧЕГО НЕТ: канала ослабления, ограниченного проектом, — задача a-user-tier-workaround-leaks-into-every-project (сейчас 1.10) делает утечку видимой, но не устраняет. Правило для 1.9: ни одна новая настройка фреймворка не пишется в ~/.tausik автоматически, и ни один обход не заводится в user-тире без имени проекта в _reason.
