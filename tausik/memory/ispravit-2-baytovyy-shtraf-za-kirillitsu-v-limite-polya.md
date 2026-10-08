---
slug: ispravit-2-baytovyy-shtraf-za-kirillitsu-v-limite-polya
title: "Исправить «2× байтовый штраф за кириллицу» в лимите поля decision (tausik_decide)"
type: dead_end
tags: []
task: null
edges: []
---

Approach: Исправить «2× байтовый штраф за кириллицу» в лимите поля decision (tausik_decide)
Reason: Премиса задачи опровергнута эмпирически: validate_length() в tausik_utils.py считает len(str) = СИМВОЛЫ, не байты, с самого v1.0.0 (единственный коммит a158380). Тест: 300 кириллических символов (600 байт) → PASS; падает только 520 СИМВОЛОВ с «512 chars, max 512». Байтового штрафа нет ни в service_knowledge.decide, ни в MCP-схеме tausik_decide (нет maxLength), ни в handlers. rationale/memory content/goal — все через validate_length/validate_content, тоже char-based. Реальный остаток — лимит 512 СИМВОЛОВ иногда тесен для многословных decision-headline (пейнкат #139). Ре-скоуп: дать decision собственный лимит вместо общего MAX_TITLE.
