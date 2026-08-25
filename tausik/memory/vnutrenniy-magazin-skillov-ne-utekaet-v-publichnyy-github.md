---
slug: vnutrenniy-magazin-skillov-ne-utekaet-v-publichnyy-github
title: "Внутренний магазин скиллов не утекает в публичный github.com/Kibertum/tausik-skills"
type: convention
tags:
  - boundary
  - github
  - gitlab
  - publishing
  - skills
task: null
edges: []
---

Два разных репозитория скиллов, и они не смешиваются:

- Внутренний: [вычеркнуто: internal-host]/kibertum/clients/kibertum/tausik/skills — здесь живут наработки (noslop, deck и прочее). Остаётся внутри.
- Публичный: github.com/Kibertum/tausik-skills — не должен содержать ничего из внутреннего. Публичные push'и под мораторием.

Перед любым push'ем в публичный репозиторий скиллов проверять, что в дереве нет внутренних скиллов. Это не относится к ядру: github.com/Kibertum/tausik-core — публичное зеркало ядра, туда релизы идут (через ff-child по орфанной линии, см. [[decision-124]]), и внутренних скиллов ядро не содержит.

Ошибка тут необратима: опубликованное нельзя развидеть, даже если удалить коммит — оно попадает в кэши и индексы.
