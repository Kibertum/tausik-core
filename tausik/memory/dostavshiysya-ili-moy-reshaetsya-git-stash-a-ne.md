---
slug: dostavshiysya-ili-moy-reshaetsya-git-stash-a-ne
title: "«Доставшийся или мой» решается git stash, а не рассуждением"
type: pattern
tags: []
task: "683-structurally-identical-tests-in-294-groups"
edges: []
---

Два отказа под параллелью выглядели следствием моих правок. Проверка заняла один прогон: `git stash push -- scripts/ tests/ tausik/gates.json docs/`, тот же набор файлов, `git stash pop`. Те же два отказа без моих правок — значит доставшиеся. Приём дешевле поиска причины и отвечает на вопрос, который иначе решают по памяти: 42 секунды против часа чтения. Работает, только если набор файлов в stash совпадает с объёмом правок.
