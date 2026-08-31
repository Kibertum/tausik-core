---
slug: clause-evidence-string-still-says-nine-spec-types
title: "Свидетельство клаузы §13.3.4 всё ещё говорит «9 closed SPEC types», а детектор ловил одну фразировку"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО САМОРЕВЬЮ В #200 ПОСЛЕ ЗАКРЫТИЯ spec-closed-list-is-nine-while-the-standard-has-eleven, ЗАМЕРЕНО, НЕ ПРЕДПОЛОЖЕНО.
scripts/renar_conformance.py:223 — строка свидетельства клаузы §13.3.4 по-прежнему гласит «9 closed SPEC types enforced (service + DB CHECK)», хотя закрытый список доведён до одиннадцати и CHECK в БД тоже. Это РОВНО ТА САМАЯ строка, которую снятая в #200 оговорка measurer-caveats цитировала как доказательство незаслуженности подтверждения: «the evidence string says 9 and the confirmation says true». Оговорку сняли, измеритель починили, а лгущую строку оставили.
СЕРЬЁЗНОСТЬ ОГРАНИЧЕНА, И ЭТО ПРОВЕРЕНО, А НЕ ПРЕДПОЛОЖЕНО: свидетельства клауз НАРУЖУ НЕ ПУБЛИКУЮТСЯ. В RENAR-CONFORMANCE.yaml и в производном renar/conformance.md уходят только булевы mandatory-clauses-confirmed — grep по обоим артефактам на «9 closed» даёт ноль. То есть внешнее утверждение не испорчено; испорчено ВНУТРЕННЕЕ обоснование, на которое смотрит следующий агент и по которому выносился вердикт о вырожденности.
ПОЧЕМУ ДЕТЕКТОР ЭТОГО НЕ ПОЙМАЛ, И ЭТО ВТОРАЯ ПОЛОВИНА ЗАДАЧИ. tests/test_spec_types_closed_list.py::test_no_hand_written_count_beside_the_list ищет форму «closed list of N», а здесь форма другая: «9 closed SPEC types». Детектор проверял ОДНУ ФРАЗИРОВКУ, а не свойство «число написано рядом со списком». Чинить надо ОБА: и строку, и детектор — иначе следующая перефразировка снова пройдёт.
ЧТО ДЕЛАЕТСЯ: (1) свидетельство §13.3.4 форматируется из len(SPEC_TYPES), как это уже сделано для справки CLI и схемы MCP; (2) детектор обобщается с «конкретной фразы» на «десятичное число в непосредственном соседстве с упоминанием типов SPEC», и обобщение проверяется тем, что он ловит ОБЕ формы — и «closed list of 9», и «9 closed SPEC types».
НЕГАТИВНЫЙ СЦЕНАРИЙ ДЛЯ AC: обобщённый детектор ОБЯЗАН покраснеть на строке «9 closed SPEC types enforced», подложенной в исходник, И на «closed list of 11» при списке длиной одиннадцать — то есть при СОВПАДАЮЩЕМ числе. Тест, зелёный при совпадении, не отличает выведенное число от написанного.
СМЕЖНОЕ: задача adapt-finding-categories-count-is-written-not-derived требует обобщения ТОГО ЖЕ детектора на другие закрытые списки. Разумно закрывать их вместе — детектор один, и вторая его копия была бы тем же дефектом уровнем выше.

## Acceptance Criteria

## Plan

## Rollback

## Journal
