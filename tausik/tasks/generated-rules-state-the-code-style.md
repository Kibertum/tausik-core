---
slug: generated-rules-state-the-code-style
title: "Правила, которые получает потребитель, о стиле кода не говорят вовсе"
status: done
epic: release-110-deferred-from-19
story: generated-code-is-lean-and-ascii
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_generated_rules_code_style.py"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - "tests/test_generated_rules_code_style.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-26T16:37:40Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР НУЖЕН И НАЧИНАЕТ ЗАДАЧУ, смена #277: в том, что bootstrap генерирует потребителю (CLAUDE.md, AGENTS.md, правила профилей), про язык имён и про то, куда девать записки, не сказано ничего — отсюда и наблюдение владельца про русские переменные в чужих проектах. ЧТО ДЕЛАЕТСЯ: два правила добавляются в генерируемые инструкции ОПИСАНИЕМ, а не императивом — по уроку смены #275: имена латиницей, потому что их читают инструменты; записка о событии идёт в `memory add`, потому что в комментарии её никто не найдёт. ЗАПРЕТ, повторённый из решения #396: не просить модель экономить токены и не просить писать меньше комментариев числом — просьба такого рода даёт модель, неохотно берущуюся за крупные задачи. Правило называет, ГДЕ место записке, а не сколько строк позволено.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРВЫМ: показано цитатой, что в генерируемых инструкциях правил о стиле имён и о месте записки сейчас нет. AC-2 Оба правила есть в генерируемых инструкциях, сформулированы описанием (что и почему), без капса и без слова «запрещено». AC-3 Ни одно добавленное слово не просит модель экономить токены или писать меньше. AC-4 НЕГАТИВ: существующие жёсткие правила, на которые опираются гейты, не размыты — проверяется прогоном гейтов, а не чтением. AC-5 Правила доходят до РАЗВЁРНУТОГО профиля, а не только в шаблон: проверяется на свежем проекте.

## Plan

## Rollback

Правка добавляет проверку и правило; откат — git revert. Проверка не блокирует до объявления порога, поэтому откат не меняет поведения у потребителя.

## Journal

- 2026-09-26T16:22:25Z [implementation] — AC-1 ЗАМЕР ВЫПОЛНЕН: grep по bootstrap_templates.py и bootstrap_templates_tiers.py даёт НОЛЬ совпадений на ascii, identifier, naming, латиниц, имена. О месте записки — тоже ничего. Наблюдению владельца про русские переменные в чужих проектах в поставляемых инструкциях нечего было противопоставить.
- 2026-09-26T16:22:26Z [implementation] — AC-2: ✓ tests/test_generated_rules_code_style.py::TestBothRulesAreStated — оба правила описанием с причиной; секция CODE_STYLE отдельная, а не под Hard Constraints, потому что ни одно из них ничего не отклоняет: первое строка doctor, второе строка при закрытии
- 2026-09-26T16:22:27Z [implementation] — AC-3: ✓ TestNothingAsksTheModelToDoLess — десять формулировок просьбы экономить проверены и в новой секции, и во ВСЁМ собранном наборе инструкций; плюс отсутствие капса MUST/NEVER/IMPORTANT
- 2026-09-26T16:22:27Z [implementation] — AC-4: ✓ TestHardConstraintsAreNotBlurred — пять жёстких правил на месте, и стилевые в их список НЕ попали
- 2026-09-26T16:22:27Z [implementation] — AC-5: ✓ TestTheRulesReachTheGeneratedFile::test_a_freshly_generated_project_carries_it — настоящий generate_claude_md в чистый каталог, оба правила в файле
- 2026-09-26T16:22:28Z [implementation] — Domain: секция 273 токена и впрыскивается в каждую смену, поэтому её длина — статья расхода. Потолок объявлен тестом TestTheSectionStaysCheap: причина живёт на странице документации, правило — здесь.
- 2026-09-26T16:22:28Z [implementation] — Negative: собственный CLAUDE.md этого репозитория написан РУКАМИ и сгенерированной секции не содержит — это замер, закреплённый тестом test_this_repository_uses_a_hand_written_claude_md, а не пропуск. Пропущенный тест читается как несделанная работа; сказать вслух дешевле.
- 2026-09-26T16:35:34Z [implementation] — СЕКЦИЯ ОПЛАЧЕНА, А НЕ ДОПИСАНА. Охрана бюджета test_bootstrap_generate::test_line_count_in_range сработала: у генерируемого тела потолок 80-180 строк, и оно стояло РОВНО на 180 — моя секция дала 197. По прецеденту 1.9 (контракт компакции добавили, сжав прозу, не подняв границу) строки взяты сжатием: три абзаца склеены в Quality Gates и Tool Routing, секция переписана в 4 строки вместо 16. Ни одно правило не выброшено. Тело 179.
- 2026-09-26T16:37:52Z [done] — AC-1: ✓ замер зафиксирован выше — grep по bootstrap_templates.py и bootstrap_templates_tiers.py даёт 0 совпадений на ascii/identifier/naming/латиниц/имена, и о месте записки тоже ничего. Проверяемо повторным grep.
