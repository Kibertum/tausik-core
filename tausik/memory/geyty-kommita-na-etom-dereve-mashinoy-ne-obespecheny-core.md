---
slug: geyty-kommita-na-etom-dereve-mashinoy-ne-obespecheny-core
title: "Гейты коммита на этом дереве машиной НЕ обеспечены: core.hooksPath ведёт в несуществующий репозиторий, git молчит"
type: gotcha
tags:
  - gates
  - git
  - hooks
  - security
  - silent-failure
task: commit-hooks-are-dead-hookspath-points-at-a-missing-repo
edges: []
---

ЗАМЕРЕНО в сессии #191, не предположено. `git config --show-origin core.hooksPath` -> file:.git/config, значение D:\Work\Personal\claude\.git\hooks. Ни каталога, ни репозитория на машине нет. Глобальный core.hooksPath НЕ задан — настройка локальна для этого репозитория.

ДОКАЗАТЕЛЬСТВО ДВУМЯ ПРОГОНАМИ:
  git hook run pre-commit                                  -> "error: cannot find a hook named pre-commit", exit 1
  git -c core.hooksPath=scripts/hooks hook run pre-commit   -> хук отработал целиком, exit 0

`git commit` при этом НЕ ГОВОРИТ НИЧЕГО: ненайденный хук трактуется как отсутствие хука, а не как ошибка. Коммит 550326e создан обычным `git commit` и прошёл без единого хука — молча.

ЧТО ИМЕННО МЁРТВО НА КАЖДОМ КОММИТЕ: (1) gate_memory_route — БЛОКИРУЮЩИЙ контроль безопасности, про который docs/en/security.md обещает защиту рабочего дерева от утечки проектного знания в чужую память агента; (2) mypy; (3) инкрементальный переиндекс RAG. Собственный .git/hooks/pre-commit в репозитории есть (2026-03-04), но при заданном hooksPath git на него не смотрит вовсе.

ПОЧЕМУ ЭТО НЕ ЗАМЕЧАЛОСЬ: гейты триггера `commit` (ruff, mypy, filesize, class_surface, memory_route, state_roundtrip, claudemd_state_drift, skill_spec_conformance — шесть из восьми блокирующие) исполняет scripts/gate_runner.py, а его на коммите зовёт ровно один потребитель — git-хук. Мёртв хук — мёртв весь триггер. Ограничение CLAUDE.md «нет коммита без gates» держится на дисциплине агента, зовущего gate_runner руками, и ни на чём больше.

ЧТО ДЕЛАТЬ ДО ПОЧИНКИ: после `git commit` вручную
  python .claude/scripts/gate_runner.py commit --files <файлы коммита>
Задокументированное значение для dev-репозитория — `git config core.hooksPath scripts/hooks` (docs/ru/hooks.md:86).

СКОЛЬКО КОММИТОВ ПРОШЛО МИМО — НЕИЗВЕСТНО и выдумывать нельзя: .git/config не версионируется, mtime 2026-08-26 08:54 есть лишь ВЕРХНЯЯ граница даты порчи.

Задача: [[commit-hooks-are-dead-hookspath-points-at-a-missing-repo]].
