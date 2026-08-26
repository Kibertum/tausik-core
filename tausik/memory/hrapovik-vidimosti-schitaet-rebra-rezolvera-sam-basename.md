---
slug: hrapovik-vidimosti-schitaet-rebra-rezolvera-sam-basename
title: "Храповик видимости считает рёбра резолвера САМ (basename_reachable_tests + top_level_imports + read_"
type: dead_end
tags:
  - mutation-testing
  - ratchet
  - single-source-of-truth
task: invariant-guards-are-invisible-to-the-visibility-ratchet
edges: []
---

Approach: Храповик видимости считает рёбра резолвера САМ (basename_reachable_tests + top_level_imports + read_crosscutting_scope), а не спрашивает резолвер
Reason: Мутация опровергла за один прогон: вырываю импортное ребро из resolve_test_files_for_relevant — храповик остаётся ЗЕЛЁНЫМ, потому что продолжает считать импорты по своей копии правил. Докстринга при этом утверждала обратное («вызывает резолвер и потому не разойдётся с ним»). Страж, МОДЕЛИРУЮЩИЙ охраняемое, разойдётся с ним при первом же изменении охраняемого — и разойдётся молча, оставаясь зелёным. Замена: ОДИН вызов resolve_test_files_for_relevant по всей вселенной отслеживаемых исходников, 1.2 с, тот же ответ (18 невидимых), но теперь это ответ резолвера, а не совпадающее мнение.
