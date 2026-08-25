---
slug: ne-pishi-rationale-kommentarii-v-kode-tausik-tolko-agenty
title: "Не пиши rationale-комментарии в коде TAUSIK — только агенты их читают"
type: convention
tags: []
task: null
edges: []
---

User feedback session #36: 'мы теряем много времени на комментирование кода. никто эти комментарии кроме агентов читать не будет'. CLAUDE.md уже это требует ('Default to writing no comments. Only WHY when non-obvious'). Я нарушал — писал 5-line module docstrings + inline 'v1.3 fix' / 'extracted from X' / 'WAS: ... NOW: ...' рассуждения. Запрет: rationale-комментарии в коде. Можно: 1-line WHY если действительно non-obvious и спасает агента от ошибки. Ускоряет работу заметно.
