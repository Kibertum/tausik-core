---
slug: section-inheritance-opens-on-any-leading-digit
title: "Наследование секции открывается ЛЮБОЙ строкой, начинающейся с цифры: проза кредитует чужой тест реальному критерию"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: verification-checklist-detector-misses-the-form-it-asked-for
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_ac_evidence.py"
  - "scripts/ac_evidence_detectors.py"
  - "scripts/gate_ac_check.py"
  - "scripts/knowledge_origin.py"
  - "scripts/knowledge_tags.py"
scope_paths:
  - "scripts/service_ac_evidence.py"
  - "scripts/ac_evidence_detectors.py"
  - "scripts/knowledge_origin.py"
  - "scripts/knowledge_tags.py"
  - "tests/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-03T21:20:52Z"
---

## Goal

НАЙДЕНО ФИНАЛЬНЫМ ПРЕД-ТЕГОВЫМ РЕВЬЮ (агент) и ВОСПРОИЗВЕДЕНО мной запуском. Это МОЯ регрессия, внесённая в #163 вместе с многострочным чек-листом.

ЗАМЕР, воспроизведён дословно: AC = '1. Auth works. 2. Config valid. 3. Staging deploy succeeds.'; заметки = 'Ran the full suite locally.' + 'ЗАМЕЧАНИЕ: 3 retries were added to the flaky network client during cleanup.' + строка с галочкой и ссылкой на СОВЕРШЕННО ПОСТОРОННИЙ тест. Результат: covered=1, AC-3 получает has_test_ref=True, checklist_missing=False, checklist_hard_block=False.

ПРИЧИНА: AC_NUMBER_PREFIX_RE делает токен 'AC' НЕОБЯЗАТЕЛЬНЫМ — она писалась для разбора ПОЛЯ acceptance_criteria, где строки нумерованы по построению, и применена к свободному тексту заметок. Обычное предложение, начинающееся с цифры, открывает секцию, а следующая строка с галочкой и ссылкой наследует её индекс.

ПОЧЕМУ ЭТО БЛОКИРУЕТ ТЕГ: _evidence_strength агрегирует real_test ПО ЗАДАЧЕ, а checklist_hard_block снимается при real_test>=1. Значит случайное предложение с цифры снимает ЖЁСТКИЙ гейт Rule 5 у задачи, у которой настоящего покрытия нет. Это ровно тот отказ 'расширение превратилось в принимать что угодно', который я объявил предотвращённым, и он в выпускаемом коде.

МОЙ ДОКСТРИНГ УТВЕРЖДАЕТ ОБРАТНОЕ: 'A section starts at a heading carrying AC-N'. Код literal 'AC' не проверяет. То есть это ещё и нарратив против кода, внесённый той же правкой.

## Acceptance Criteria

1. Секцию открывает ТОЛЬКО строка с явным токеном AC. Тест: строка «3 retries were added to the flaky network client» секцию НЕ открывает, и следующая за ней строка с галочкой и ссылкой остаётся неприкреплённой.
2. Обе рабочие формы сохранены. Тест: однострочная «AC-1: ✓ tests/x.py::test_y» и многострочная «AC-1 (что проверяется):» с ✓-строками ниже по-прежнему дают покрытие; сегментация упакованной строки «1. ✓ a 2. ✓ b» не сломана (её единицы несут свой индекс И доказательство в одной строке, наследование им не нужно).
3. Жёсткий гейт восстановлен. Тест: задача из замера (проза с цифры + посторонний тест) снова даёт checklist_hard_block=True.
4. Докстринг приведён в соответствие с кодом, а не наоборот: утверждение про «heading carrying AC-N» становится правдой.
5. HIGH из ревью: os.path.realpath НЕ вызывается на СОХРАНЁННЫХ строках origin_project при миграции. Недоступная сетевая шара в старой записи не должна вешать миграцию, которая идёт при КАЖДОМ открытии общей базы во всех проектах. Тест: канонизация сохранённой строки не обращается к файловой системе.
6. MEDIUM из ревью: канонизация детерминирована МЕЖДУ платформами. Тест: один и тот же путь даёт один отпечаток независимо от того, разбирает ли его Windows- или POSIX-семантика; выбранный компромисс назван в докстринге.
7. MEDIUM из ревью: JSON-список НЕ строк не считается каноническим. Тест: [1, 2] и [null, "tag"] нормализуются, а не остаются навсегда; ["a","b"] по-прежнему не переписывается.
8. НЕГАТИВ ЦЕЛИКОМ: все шесть отрицательных проверок из test_ac_evidence_multiline_sections остаются зелёными без правки ожиданий; задача без чек-листа по-прежнему предупреждается.
9. Полный pytest зелёный, mypy и ruff чистые; сходимость ломающих изменений остаётся 6 = 6 = 6 = 6 = 6.

## Plan

## Rollback

git revert. Правки в парсере доказательств и в канонизации метки origin; поведение продукта сужается обратно к текущему, данные не трогаются.

## Journal

- 2026-08-03T21:20:14Z [implementation] — Root cause (logic-error): я применил AC_NUMBER_PREFIX_RE — шаблон, написанный для ПОЛЯ acceptance_criteria, где строки нумерованы по построению и ведущая цифра означает индекс, — к свободному тексту ЗАМЕТОК, где ведущая цифра означает обычное предложение. В этом шаблоне токен AC необязателен, и это верно для его исходного входа. Ошибка не в шаблоне, а в том, что я взял ГОТОВЫЙ распознаватель для нового вопроса, не проверив, на каком входе он писался. Узнать заголовок и прочитать индекс — разные вопросы, и теперь у них разные шаблоны. ПОЧЕМУ МОИ ЖЕ ШЕСТЬ НЕГАТИВНЫХ ТЕСТОВ ЭТОГО НЕ ПОЙМАЛИ: все шесть проверяли строку, которая НАСЛЕДУЕТ (голая галочка, проза со ссылкой, ссылка до заголовка). Ни один не проверял строку, которая ОТКРЫВАЕТ секцию. Я закрыл одну сторону механизма и не заметил, что у него две. Prevention: добавлены четыре теста именно на открывающую сторону, включая параметризованный набор из трёх видов прозы с ведущей цифрой и КОНТРОЛЬНЫЙ тест, что явный токен AC секцию по-прежнему открывает — иначе набор мог бы стать зелёным просто оттого, что наследование перестало работать вообще. Также по итогам ревью, не связано с этим дефектом, но в той же партии: (HIGH) os.path.realpath убран с пути МИГРАЦИИ — сохранённая строка может называть недоступную шару, а миграция идёт при каждом открытии общей базы во всех проектах, и зависание было бы неотменяемым; тест утверждает НОЛЬ обращений к файловой системе. (MEDIUM) канонизация переведена с os.path.normcase на явный lower(), потому что normcase на POSIX ничего не делает и одна и та же строка получала два отпечатка в зависимости от того, кто её открыл; компромисс (два корня, различающиеся регистром на чувствительной ФС, схлопываются в одну метку) назван в докстринге. (MEDIUM) JSON-список НЕ строк больше не считается каноническим: [1,2] и [null,'tag'] нормализуются, иначе они читались бы через str(item) вечно и никогда не помечались бы как требующие починки.
- 2026-08-03T21:20:49Z [implementation] — AC-1 (секцию открывает только явный токен AC): ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_prose_starting_with_a_digit_does_not_open_a_section ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_no_digit_led_sentence_opens_a_section ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_but_an_explicit_AC_token_still_does AC-2 (обе рабочие формы сохранены): ✓ tests/test_ac_evidence_multiline_sections.py::test_the_fuller_form_is_recognised ✓ tests/test_ac_evidence_multiline_sections.py::test_the_single_line_form_still_works ✓ tests/test_ac_evidence_multiline_sections.py::test_a_heading_covered_by_four_tests_is_the_point AC-3 (жёсткий гейт восстановлен): ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_prose_starting_with_a_digit_does_not_open_a_section AC-4 (докстринг приведён к коду): ✓ verification_run #1715 AC-5 (миграция не трогает файловую систему): ✓ tests/test_knowledge_origin.py::TestWhatCountsAsAlreadyDone::test_the_migration_never_touches_the_filesystem AC-6 (канонизация детерминирована между платформами): ✓ tests/test_knowledge_origin.py::TestWhatCountsAsAlreadyDone::test_a_stored_path_fingerprints_the_same_on_any_platform AC-7 (JSON-список не строк не канонический): ✓ tests/test_knowledge_tags.py::TestTheMigration::test_a_json_list_of_NON_strings_is_not_canonical ✓ tests/test_knowledge_tags.py::TestTheMigration::test_an_already_canonical_row_is_not_rewritten AC-8 (весь прежний негатив цел): ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_task_with_no_checklist_is_still_warned ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_bare_tick_does_not_inherit_a_section ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_prose_naming_a_path_is_not_evidence_even_inside_a_section AC-9 (чистота и сходимость): ✓ tests/test_breaking_change_count_converges.py::test_all_four_documents_state_the_same_number ✓ verification_run #1715 Домен: дефект был ВОСПРОИЗВЕДЁН запуском до правки (AC-3 получал has_test_ref=True от постороннего smoke-теста, hard_block=False) и перепроверен после (covered=0, orphans=1, hard_block=True). Реальная общая база проверена после смены канонизации: 0 записей ждут переписывания, doctor All clean. Эксклюзивный полный прогон 6949 passed / 0 failed / 0 errors.
