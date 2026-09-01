---
slug: provizionirovanie-lenty-sveryay-poparnym-perechnem-dvuh-ci
title: "Провизионирование ленты сверяй ПОПАРНЫМ перечнем двух CI, а не чтением одного"
type: convention
tags: []
task: ci-does-not-run-on-the-release-branch
edges: []
---

GitLab ставил pytest pytest-xdist PyYAML ruff; GitHub — pytest pytest-xdist ruff mypy bandit. Потерянный в одном из списков mypy валил два теста, которые гоняют ГЕЙТ mypy подпроцессом: без бинарника они не пропускаются, а краснеют 'Gate command not runnable', errno 13. Список пакетов пишется по инвентарю и теряет строку молча. Тот же класс, что 'починено в одном из двух мест'. Пакет, которого не требует ни один тест этой ленты, не добавляй — неизмеренный пакет есть догадка.
