---
slug: istoriyu-fayla-po-vsem-ssylkam-chitay-dvumya-protsessami
title: "Историю файла по всем ссылкам читай двумя процессами: rev-list --all плюс cat-file --batch, а не show на каждый коммит"
type: pattern
tags:
  - cost
  - git
  - manifest
  - renar
task: next-version-reads-the-journal-tip-not-its-history
edges: []
---

Замер на 10 коммитах манифеста: rev-list --all 28 мс, cat-file --batch по всем перечисленным объектам 27 мс (один процесс, 60 КБ), тогда как show на каждый коммит — ~25 мс × n. Форма «n+1» из заголовка задачи была страхом, а не замером. Правила чтения: pathspec rev-list относителен cwd, имя объекта в batch — с якорем ./ (иначе резолв от верхнего уровня worktree, память #576); коммит удаления файла попадает в rev-list и отвечает «<name> missing» — это факт, не отказ; размеры в заголовках batch — БАЙТЫ, читать в binary и резать по размеру, а не по декодированному тексту. Читатель обязан отдавать три ответа: None (нечитаемо: rc≠0, поток не разобрался), 0 (ответил и пусто), N.
