---
slug: tree-says-1-9-while-releasing-1-10
title: "Дерево говорит 1.9.0, выпуская 1.10: версию поднять в единственном источнике"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - README.md
  - README.ru.md
  - "tests/test_repo_coherence.py"
scope_paths:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - README.md
  - README.ru.md
  - AGENTS.md
  - "docs/_generated/constants.json"
  - "tests/test_repo_coherence.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T10:45:02Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

pyproject.toml и scripts/tausik_version.py говорят 1.10.0, и всё порождённое из них следует. Срез CHANGELOG и тег НЕ делаются: они парные и датированные, их ставит владелец. Прецедент 1.9 (коммит 6de7eac7) держал подъём и срез РАЗНЫМИ коммитами с пятью днями между ними.

## Acceptance Criteria

1. pyproject.toml и scripts/tausik_version.py несут 1.10.0; иных литералов версии в живом коде нет (проверено поиском). 2. Порождённое из них пересобрано: docs/_generated/constants.json и всё, что его читает. 3. Каждое покрасневшее упоминание версии в README на двух языках разобрано ПО СУЩЕСТВУ, ни одно не заглушено: историческое остаётся историческим, текущее становится 1.10. 4. НЕГАТИВНЫЙ: срез CHANGELOG НЕ делается и тег НЕ ставится — [Unreleased] остаётся, потому что дата среза принадлежит тегу, а тег ставит владелец. 5. Полная лента зелёная.

## Plan

## Rollback

git revert одного коммита; версия — литерал в двух файлах и порождённое из них, поведения за собой не несёт. Тег этой задачей не ставится, поэтому откат не затрагивает ни один выпуск.

## Journal

- 2026-09-29T10:43:20Z [implementation] — AC-1: ✓ pyproject.toml и scripts/tausik_version.py несут 1.10.0; иных литералов версии в живом коде нет — поиск по scripts/ bootstrap/ harness/ пуст. AC-2: ✓ gen_doc_constants --write перегенерировал constants.json и поправил перекрёстные ссылки в AGENTS.md, README.md, README.ru.md; --check зелёный. AC-3: ✓ каждое оставшееся упоминание 1.9 разобрано: Codex first-class с 1.9 (историческое), арка 1.8→1.9 (историческая), «отсчёт 1.9 остаётся последним словом» (намеренное), +1,9% (процент, не версия), ссылка на заметки 1.9 (верная). Повествовательный раздел переписан под 1.10 на двух языках. AC-4 НЕГАТИВНЫЙ: ✓ [Unreleased] на месте, тега нет, git tag не вызывался.
- 2026-09-29T10:43:35Z [implementation] — AC-5: ✓ полная лента 12232 прошли, 34 пропущены. Domain: живой CLI после подъёма отвечает 1.10.0, не только константы. ДВА СТРАЖА СРАБОТАЛИ НА МОЕЙ ПРОЗЕ И ОБА ПО ДЕЛУ: (1) утверждение об экономии обязано стоять в 120 символах от «на этой паре» — написал «на той паре», обобщение не прошло; (2) голое число ломающих изменений в README столкнулось со стражем согласованности ЭТОГО числа для 1.8 — число живёт на странице заметок, README на неё указывает. Третий отказ мой по существу: калибровочный тест линзы утверждал, что класс сгнивших цитат ВИДЕН, и покраснел ровно тогда, когда регистр довели до нуля; теперь он сажает цитату сам, а парный тест сажает иллюстративную и требует тишины.
