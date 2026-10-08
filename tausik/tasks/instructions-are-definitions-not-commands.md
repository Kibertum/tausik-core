---
slug: instructions-are-definitions-not-commands
title: "Инструкции проекта написаны императивом и капсом — замена на описания"
status: done
epic: release-110-deferred-from-19
story: harness-costs-less-per-task
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
  - "tests/test_instruction_tone.py"
  - "tests/test_doctor_drift_baselines.py"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - "tests/test_instruction_tone.py"
  - "tests/test_doctor_drift_baselines.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-26T17:49:43Z"
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

ЗАМЕР, смена #275: CLAUDE.md 1587 токенов, AGENTS.md 3706. Оба построены на «ЖЁСТКИЕ», «ВСЕГДА», «НИКОГДА» и капсе. По опыту Cursor замена императива на плоское описание того, что делает инструмент, сократила системный промпт примерно на две трети и стала работать лучше на нескольких семействах моделей; капс и эмфаза вредят буквальным моделям особенно. ПРАВИЛО РАЗБОРА: каждую строку помечать одним из четырёх — оставить (знание о продукте и среде, которое модель не выведет; починка замеченной в стенограммах особенности), переписать (команду в описание, напоминание в ограничение, размытое количество в диапазон), удалить (то, что модель делает сама; повтор описания инструмента; строка, способная противоречить просьбе владельца), перенести (переменное — за границу кэша). НЕ ПРОСИТЬ МОДЕЛЬ ЭКОНОМИТЬ ТОКЕНЫ: оснастка, сказавшая это, получила модель, неохотно берущуюся за крупные задачи, и иногда бросавшую их.

## Acceptance Criteria

AC-1 Каждая удалённая или переписанная строка помечена причиной из четырёх — оставить, переписать, удалить, перенести; разметка приложена к задаче. AC-2 Ни одна строка не просит модель экономить токены или делать меньше. AC-3 Жёсткие правила, на которые опираются ГЕЙТЫ, остаются — они не просьба, а описание того, что откажет. AC-4 НЕГАТИВ: после правки те же гейты по-прежнему отклоняют запись без активной задачи и закрытие без verify — проверяется прогоном, а не чтением. AC-5 Замер токенов до и после по обоим файлам.

## Plan

## Rollback

Правка в оснастке; откат — git revert. Каждая правка отдельным коммитом, чтобы откатывалась по одной.

## Journal

- 2026-09-26T17:31:19Z [implementation] — ЗАМЕР ПОПРАВИЛ ПРЕМИССУ САМОЙ ЗАДАЧИ. Я завёл её словами «оба построены на ЖЁСТКИЕ, ВСЕГДА, НИКОГДА и капсе». Генерируемое тело — НЕ построено: 7 маркеров на 159 строк (один MUST, четыре Always/Never, один non-negotiable, один strictly), и оно целиком по-английски. Капс и «ЖЁСТКИЕ» — в рукописном CLAUDE.md ЭТОГО репозитория, который никому не поставляется. Заявление Cursor про «сократили системный промпт на две трети» к телу такой плотности не переносится.
- 2026-09-26T17:31:20Z [implementation] — AC-1 ✓ семь правок, каждая с помеченной причиной: delete «Follow these instructions strictly» (модель следует данному и без просьбы); rewrite «Hard Constraints (non-negotiable)» (Hard уже сказало); rewrite «Never raw SQLite» в последствие (обходит проекции и журнал аудита); delete «Always request user confirmation» (повтор первой фразы); rewrite «you MUST … FIRST» в место, где лежит записанный ответ; rewrite «Never your host's own memory» в факт, что её никто не читает обратно; rewrite «Always respond in the user's language» в утверждение.
- 2026-09-26T17:31:20Z [implementation] — AC-2 ✓ tests/test_instruction_tone.py::TestNothingAsksTheModelToSpendLess — двенадцать формулировок просьбы тратить меньше проверены и в теле, и в жёстких правилах
- 2026-09-26T17:31:20Z [implementation] — AC-3 ✓ TestTheRulesThemselvesSurvivedTheEdit — семь правил на месте; правило о БД теперь называет причину, а не запрет
- 2026-09-26T17:31:20Z [implementation] — AC-4 ✓ прогон полного набора после правки; правила, на которые опираются гейты, не размыты — проверено тестом, а не чтением
- 2026-09-26T17:31:21Z [implementation] — AC-5 ✓ 15 013 -> 14 998 символов, 159 строк без изменений: тише и не длиннее — единственное направление, в котором этой правке было позволено двигаться. Закреплено TestTheBodyStaysWithinItsBudget.
- 2026-09-26T17:31:21Z [implementation] — Domain: маркеры считаются регулярным выражением с ЗАГЛАВНОЙ буквы (Always/Never), потому что запрет на слово never в любом положении запрещал бы английский язык — проверено тестом test_ordinary_lowercase_prose_is_not_the_subject.
- 2026-09-26T17:31:21Z [implementation] — Negative: «Always respond in the user's language» НЕ удалено, хотя это было бы на строку дешевле. Доказать отсюда, что модель и без строки ответит на языке пользователя, нельзя, а цена ошибки — ответы не на том языке. Переписано утверждением, а не выброшено.
- 2026-09-26T17:47:27Z [implementation] — ПЛАВАЮЩИЙ ОТКАЗ, НЕ СВЯЗАННЫЙ С ПРАВКОЙ: test_verify_endpoint.py::TestNegatives::test_unknown_path_is_404 упал один раз в полном прогоне под xdist, прошёл в одиночку, повторный полный прогон зелёный (11 202). Заведён flaky-verify-endpoint-404-erodes-the-suite: плавающий тест обесценивает красное во всём наборе.
- 2026-09-26T17:47:27Z [implementation] — ЧЕТЫРЕ ОХРАНЫ СРАБОТАЛИ НА ПЕРЕИМЕНОВАНИЕ ЗАГОЛОВКА и все правы. tests/test_doctor_drift_baselines.py использует '## Hard Constraints (non-negotiable)' как СИГНАЛЬНЫЙ заголовок и проверяет, что он существует, — иначе тест прошёл бы вхолостую. Сплошная замена на новый заголовок сломала смысл ОДНОГО из пяти мест: test_trimmed_baseline_is_customisation_not_drift нарочно брал заголовок, которого в шаблоне НЕТ, чтобы проверить обрезанный файл как подмножество; с совпавшим заголовком он стал проверять расхождение содержимого, то есть обратное. Там возвращён отсутствующий в шаблоне заголовок.
