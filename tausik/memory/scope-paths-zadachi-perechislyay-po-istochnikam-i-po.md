---
slug: scope-paths-zadachi-perechislyay-po-istochnikam-i-po
title: "scope_paths задачи перечисляй по ИСТОЧНИКАМ и по обязательным для закрытия артефактам — иначе задача становится незакрываемой"
type: convention
tags:
  - acl
  - gates
  - scope
task: nobody-asks-whether-the-repository-is-still-coherent
edges: []
---

Заполняя scope_paths, перечисляй (1) ИСТОЧНИКИ, а не развёрнутые копии, и (2) артефакты, без которых закрытие невозможно — прежде всего оба CHANGELOG. Иначе ACL противоречит гейтам: один запрещает писать, другой запрещает закрыться без записи.

Замер, смена #223 (nobody-asks-whether-the-repository-is-still-coherent): ACL, написанный автором задачи, дважды указывал не на тот носитель. (а) '.claude/agents/*.md' — это РАЗВЁРНУТАЯ копия, править её запрещено CLAUDE.md, а источник определений субагентов лежит в harness/claude/subagents/ (переносит bootstrap_copy.copy_subagents). (б) CHANGELOG.md/CHANGELOG.ru.md отсутствовали вовсе, при том что гейт changelog требует записи в оба для task done — то есть задача в исходных рамках не закрывалась в принципе.

Как применять: (1) для любого артефакта, у которого есть развёрнутая копия (скиллы, субагенты, хуки, MCP), в ACL идёт путь в harness/ или scripts/, а не в .claude/.cursor/.kilo/.opencode/.qwen; (2) в ACL всегда включай CHANGELOG.md и CHANGELOG.ru.md, если задача вообще меняет поведение; (3) гейт рамок сам печатает готовую команду расширения — расширять с ЗАПИСАННОЙ причиной в журнале, а не молча, чтобы расширение ACL не превратилось в рефлекс.
