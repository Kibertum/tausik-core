---
slug: tihiy-propusk-ne-schitaetsya-grepom-po-fraze-ischi-po
title: "Тихий пропуск не считается грепом по фразе — ищи по УСЛОВИЮ в AST"
type: gotcha
tags: []
task: db-gated-ratchets-never-run-in-ci
edges: []
---

В #203 греп 'project DB absent' нашёл 3 гейтящихся на базе контроля. Их было 10: группа в test_claudemd_state_gate.py формулировала причину как 'no .tausik/tausik.db in this checkout'. Считать надо СТРУКТУРУ: skipif, чьё УСЛОВИЕ упоминает предмет, и if с pytest.skip внутри. И именно условие, а не текст функции: первая версия сканера читала функцию целиком и дала 20 ложных — тесты со своей базой в tmp_path, тесты про сам пропуск, и тот тест, который только что починили, потому что КОММЕНТАРИЙ о починке упоминал оба слова.
