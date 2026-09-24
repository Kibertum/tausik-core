---
slug: polzovatelskiy-tir-s-1-10-config-tausik-config-json-staryy
task: user-tier-config-recreates-the-directory-18-removed
date: "2026-09-24"
edges: []
---

## Decision

Пользовательский тир с 1.10 — ~/.config/tausik/config.json. Старый ~/.tausik/config.json читается, только если он единственный (настройки не теряются), doctor просит перенести; при обоих побеждает новый. Причина: каталог ~/.tausik делает домашнюю папку похожей на проект — ловушка, из которой 1.8 уводила общую базу.

## Rationale
