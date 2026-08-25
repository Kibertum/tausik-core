---
slug: skills-repo-license-file-zakryvaetsya-won-t-do-pravka-v
task: null
date: "2026-07-23"
edges: []
---

## Decision

skills-repo-license-file закрывается won't-do: правка в чужом репо + выбор владельца; проверка лицензии ядра пройдена (Apache-2.0 консистентен)

## Rationale

Первичная правка — в репозитории магазина скиллов ([вычеркнуто: internal-host]/.../skills), не в ядре; лицензию выбирает владелец. Как тикет бэклога ЯДРА неисполнима (подтверждает decision #153, сессия #120). Actionable-срез — проверка ядра — выполнен и чист: LICENSE = настоящий Apache License Version 2.0 (10956 байт), совпадает с README.md/README.ru.md (бейдж + секция License) и pyproject.toml (license='Apache-2.0' + OSI-классификатор). Ядро НЕ заявляет лицензию, которой у него нет.
