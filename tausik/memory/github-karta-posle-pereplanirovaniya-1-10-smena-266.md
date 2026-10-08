---
slug: github-karta-posle-pereplanirovaniya-1-10-smena-266
title: "GitHub-карта после перепланирования 1.10 (смена #266): milestone v1.10.0 = 7 эпиков, v1.11.0 кандидаты, хосты в v2.0.0, Planning без версии"
type: context
tags:
  - "1.10"
  - "1.11"
  - epics
  - github
  - milestones
  - roadmap
task: null
edges: []
---

По указанию владельца (смена #266) карта приведена к решениям #376 (состав 1.10) и #377 (следующие версии). v1.10.0 (#1): эпики A #52, B #53, C #54, D #55, E #166 сессии не ворота, F #167 SENAR 1.5, G #168 RENAR 1.1; новые задачи #171–#185; из Planning в E перенесены #126, #137, #146, #148, #149; итого 53 открытых (7 эпиков + 46 задач). v1.11.0 (#4, кандидаты, описание milestone говорит это явно): эпики K #169 знание живёт дольше смены (22 sub-issue, история deferred-110-knowledge-lifecycle) и O #170 внешняя петля (14, история deferred-110-outward-loop-and-test-authorship, включая first-party RENAR #186); итого 38. v2.0.0: 17 issue паритета хостов перенесены под эпик #58 (теперь 21 sub-issue), итого 38. Planning: 50, в том числе новый дефект CLI #187. Метка area/standards заведена для SENAR/RENAR. Счётчики open_issues в API milestones отстают на минуты — считать через issue list --milestone. Каждая новая задача несёт tracker_refs github#N. Инструмент — скрипт gh_runner.py в scratchpad смены (gh CLI + GraphQL addSubIssue), в репозиторий не входит.
