---
slug: detektor-dreyfa-renar-chitaet-repozitoriy-sayta-standards
title: "Детектор дрейфа RENAR читает репозиторий САЙТА (standards/renar), а стандарт с сентября живёт в standards/renar-standart — тест живого корпуса красный и слеп к SPEC-UC"
type: gotcha
tags:
  - config
  - corpus
  - drift
  - gotcha
  - renar
task: null
edges: []
---

Замер смены #266: ключ .tausik/config.json renar_standard_corpus = d:/Work/Kibertum/clients/kibertum/standards/renar (mkdocs-сайт); главы стандарта (standard/00..15-*.md, баннер версии) лежат в standards/renar-standart. tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us падает с четырьмя corpus-unreadable (13-conformance.md без баннера, 08-specifications.md и 07-adapt.md не в корпусе) плюс repo-unreadable: половина по принятым ADR не запустилась, потому что git grep на этом хосте нечитаем. Состояние «не прочитан» и «дрейфа нет» — разные ответы (конвенция #574): с верным путём детектор находит ровно одну находку spec-types-drift: корпус закрывает список на 12, у нас 11, нет UC. Задача: renar-drift-detector-reads-the-site-repo-not-the-standard (история release110-renar-11-first-party-and-spec-uc).
