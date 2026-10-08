---
slug: kilo-posle-obnovleniya-otvergaet-tools-stroku-claude-stilya
title: "Kilo после обновления отвергает tools:-строку Claude-стиля в frontmatter агентов: нужна объектная форма"
type: gotcha
tags:
  - agents
  - config
  - frontmatter
  - kilo
  - redeploy
  - vendor_seo
task: null
edges: []
---

После обновления Kilo поле tools: в frontmatter агентов .kilo/agents стало строгим: строка в стиле Claude Code ("tools: Read, Bash, Write") — жёсткая ошибка валидации конфига, агент не грузится. Каноническая форма — объект с ключами инструментов Kilo: Read->read, Bash->bash, Write->edit (отдельного write нет), Grep->grep, Glob->glob, WebFetch->webfetch, значения true. Исправлено 2026-10-07 во всех 7 файлах .kilo/agents/vendor_seo/. ВАЖНО: новый вендорский шаблон (виден в HiddenVPNTools на 2026-10-06) убирает tools: целиком — следующая перепроверка вендора может либо снести правку обратно на строку, либо вылечить файл отсутствием поля; после каждого vendor redeploy проверять Select-String '^tools:' по .kilo/agents. Файлы .claude/agents/* со строкой НЕ трогать: для Claude Code строка — родной формат, Kilo их не читает. Легаси .kilocode Kilo тоже сканирует — проверять и его.
