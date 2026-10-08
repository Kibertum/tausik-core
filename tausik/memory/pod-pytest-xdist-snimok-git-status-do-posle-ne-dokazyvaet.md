---
slug: pod-pytest-xdist-snimok-git-status-do-posle-ne-dokazyvaet
title: "Под pytest-xdist снимок git status «до/после» не доказывает чистоту дерева: соседний воркер успевает оставить след ДО снимка"
type: gotcha
tags: []
task: verify-a-gate-by-mutation-not-by-passing
edges: []
---

Замер #207 в verify-a-gate-by-mutation-not-by-passing: мутация «билдер пишет файл в tests/» ВЫЖИЛА при проверке before==after по git status --porcelain, потому что тот же билдер уже выполнился в другом воркере и подкидыш вошёл в оба снимка. Порядково-зависимое доказательство под параллельным раннером пусто. Работает перехват записи в самом тесте: monkeypatch builtins.open И io.open (Path.write_text идёт через io.open, патч только builtins его не видит), любой путь на запись вне tmp_path — нарушение. Это ловит и повторяемо, и независимо от расписания воркеров.
