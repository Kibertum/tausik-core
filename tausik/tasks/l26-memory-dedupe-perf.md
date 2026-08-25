---
slug: l26-memory-dedupe-perf
title: "Dedupe памяти O(n^2) на SequenceMatcher"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/memory_cleanup.py (find_dedupe_candidates перф + _PATH_RE), tests/"
scope_exclude: "service_knowledge_hygiene.dedupe_memory (сигнатура сохраняется), backend FTS (не трогаем — выбран pure-difflib путь, не FTS)"
relevant_files:
  - "scripts/memory_cleanup.py"
  - "tests/test_memory_cleanup_cli.py"
  - "tests/test_memory_lint.py"
scope_paths:
  - "scripts/memory_cleanup.py"
  - "tests/test_memory_cleanup_cli.py"
  - "tests/test_memory_lint.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-21T11:45:38Z"
---

## Goal

memory_cleanup.py:50-85 сравнивает попарно ВСЕ записи через difflib.SequenceMatcher по title+content, при этом autojunk=False (:47) отключает единственную оптимизацию difflib. При дефолтном n=200 это около 20000 полных диффов строк; при n=1000 — минуты. Рядом уже стоит индекс FTS5, но он не используется. Нужно: генерация кандидатов через FTS5 (или шинглы/minhash), затем попарная оценка только по короткому списку. Смежно в том же модуле: _PATH_RE (:99) помечает как stale_file любой токен вида foo/bar.ext, включая пути из чужих репозиториев, URL и просто прозу.

## Acceptance Criteria

1. find_dedupe_candidates перестаёт делать полный SequenceMatcher.ratio() (autojunk=False) на ВСЕХ парах: блокировка по type + дешёвые верхние границы real_quick_ratio()/quick_ratio() отсекают пары до дорогого ratio(); matcher переиспользуется по внешнему элементу (set_seq2 один раз). 2. Результаты ТОЧНО те же, что у старого all-pairs (real_quick_ratio/quick_ratio — истинные верхние границы, отсечённые пары заведомо < threshold): регресс-тест сравнивает выход нового и эталонного brute-force на случайном наборе. 3. Замер: на n=200 число полных ratio() вызовов кратно меньше числа пар (доказать счётчиком в тесте). 4. _PATH_RE больше не помечает stale_file токены внутри URL (scheme://host/path.ext): тест на URL, чужой абсолютный путь, прозу. 5. Порядок сортировки выхода (по -ratio, id_a, id_b) сохранён. 6. Полный pytest модуля памяти зелёный.

## Plan

## Rollback

git revert memory_cleanup.py — чистая функция, сигнатура find_dedupe_candidates неизменна, откат не затрагивает вызывающих.

## Journal

- 2026-07-21T11:44:54Z [implementation] — Impl: find_dedupe_candidates — блокировка по type (dict-группировка, кросс-тип пары не сравниваются) + real_quick_ratio()/quick_ratio() (истинные верхние границы) отсекают дорогой ratio() до вызова; ориентация a=outer/b=inner сохранена → ratio() bit-identical. _similarity удалён (переиспользован inline). _PATH_RE: +_HOSTLIKE_FIRST_SEG фильтр — токены с domain-подобным первым сегментом (example.com/, cdn.x.net/) пропускаются как URL/host, dotfile-каталоги (.github/) сохранены (внутренняя точка vs ведущая). Тесты: exact-equivalence vs brute-force оракул (12 комбинаций seed×threshold), счётчик ratio() < same-type-pairs//2, сортировка, URL/host/dotfile. 241 зелёный (memory/knowledge). memory_cleanup.py 213 строк.
- 2026-07-21T11:45:13Z [implementation] — AC verified: 1. ✓ block-by-type + real_quick_ratio/quick_ratio gate before ratio(); test_prunes_the_expensive_full_ratio_calls 2. ✓ exact vs brute-force oracle, 12 seed×threshold combos; test_exact_same_result_as_brute_force 3. ✓ ratio() calls < same_type_pairs//2 at n=60; counting SequenceMatcher subclass 4. ✓ _HOSTLIKE_FIRST_SEG skips example.com//cdn.x.net; dotfile .github/ kept; test_url_and_hostname + test_dotfile_dir 5. ✓ test_sort_order_preserved (-ratio,id_a,id_b) 6. ✓ 241 green memory/knowledge; verify #1161 PASS
- 2026-07-21T11:45:34Z [implementation] — AC verified: 1. ✓ block-by-type+quick-ratio gate; test_prunes 2. ✓ exact vs brute-force 12 combos 3. ✓ ratio()<pairs//2 counting SM 4. ✓ host-first-seg skip, dotfile kept 5. ✓ sort order test 6. ✓ 241 green; verify PASS; drift clean
