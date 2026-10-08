---
slug: roadmap-reads-an-additive-decision-as-the-whole-composition
title: "ROADMAP.md читает дополняющее решение #363 как полный состав и объявляет десять историй #360 «не входящими» в 1.9"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/release_roadmap.py, tests/test_release_roadmap.py, ROADMAP.md (перевыпуск), CHANGELOG.md, CHANGELOG.ru.md, tausik/ (проекция состояния)"
scope_exclude: "Не менять состав релиза по существу — только пересказать решения #360-#363 владельца; не трогать .agents/, не менять версию, не пушить."
relevant_files:
  - "scripts/release_roadmap.py"
  - "scripts/release_roadmap_composition.py"
  - "tests/test_release_roadmap.py"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T11:22:47Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР, смена #251: scripts/release_roadmap.py::composition берёт НОВЕЙШЕЕ решение, в тексте которого встречаются ≥2 слагов историй, за полный состав релиза. Решение #363 («три ответа владельца»: канал user-tier ВХОДИТ, kb-docs — 1.9, пять задач release19-effective-context — 1.9) дополняет состав, а не пересказывает его, но упоминает три слага — и генератор молча сузил границу 1.9 до трёх историй. Порождённый ROADMAP.md в разделе «Вопрос версии» цитирует #360, называющее десять историй релиза (codex-first-class-19, evidence-primitives, agent-output-discipline…), а разделом ниже перечисляет те же десять как «в релиз НЕ входит». `doc roadmap --check` зелёный: файл равен тому, что порождает генератор, — проверка свежести не ловит ложное содержание. Причина класса: состав ВЫВОДИТСЯ из прозы (любые два слага подряд), а не ЧИТАЕТСЯ из явного объявления. Починка: (1) явный маркер состава в решении — строка «Состав: slug, slug, …» (EN: «Composition:»), и явный маркер устава «Устав: #N» (EN: «Charter:»); когда хотя бы одно решение несёт маркер состава, действует НОВЕЙШЕЕ из маркированных, а немаркированные решения, упоминающие два слага, состав больше не переопределяют; неизвестный слаг в маркере — отказ (RoadmapUnreadable), не тихий пропуск; (2) прежняя эвристика остаётся только как fallback для базы без маркеров и названа в тексте карты; (3) раздел «не входит» разделяет ОТКРЫТЫЕ истории эпиков релиза (отложенная цена, с остатком) и ЗАКРЫТЫЕ, не названные составом (входят в дерево, цены нет) — сегодня закрытая kb-identity и открытая deferred-110-* стоят в одной таблице с одинаковой подписью «не в этой версии», и для закрытой это неправда; (4) решение-пересказ состава 1.9 по #360+#361+#362+#363 записывается в журнал с обоими маркерами, ROADMAP.md перевыпускается.

## Acceptance Criteria

AC-1: тест на синтетической базе: маркированное решение «Состав: alpha, beta» в силе, а ПОЗДНЕЕ немаркированное решение, упоминающее beta и gamma, состав не меняет — ровно случай #363. AC-2: новейшее из ДВУХ маркированных решений побеждает; порядок слагов — порядок владельца. AC-3: НЕГАТИВ: неизвестный слаг в строке «Состав:» даёт ошибку RoadmapUnreadable с именем слага, а не карту без него; пустая строка «Состав:» — тоже ошибка, не пустой релиз. AC-4: «Устав: #N» читается как устав; висячая ссылка (ошибка: решения #N нет) падает на прежнюю цепочку, а не на выдуманное решение. AC-5: база без единого маркера ведёт себя как прежде — существующие тесты TestCompositionIsRead/TestCharterIsFollowed зелёные без правок ожиданий. AC-6: раздел «не входит» показывает закрытые неназванные истории отдельно от открытых и не подписывает закрытую «не в этой версии». AC-7: в живой базе записано решение-пересказ состава 1.9 с маркерами; ROADMAP.md перевыпущен, `doc roadmap --check` зелёный, и в разделе «не входит» нет ни одной истории, которую цитируемый устав #360 называет историей релиза. AC-8: мутация — снятие ветки маркера возвращает состав к трём историям на живой базе (доказано прогоном до/после).

## Plan

## Rollback

git revert коммита; записанное решение-пересказ остаётся в журнале и вреда не несёт (без ветки маркера генератор вернётся к прежней эвристике).

## Journal

- 2026-09-13T11:11:43Z [implementation] — Реализовано: чтение состава вынесено в scripts/release_roadmap_composition.py (генератор ушёл бы за 500 строк); маркеры «Состав:»/«Composition:» (список до конца строки, точки или точки с запятой — слаг kebab-case таких знаков не несёт) и «Устав:»/«Charter:»; _declared → _inferred fallback; comp['declared'] печатается в карте («ОБЪЯВИВШЕГО его строкой» vs «вывод из прозы»); раздел «не входит» разделён на открытые (с остатком) и закрытые (с числом закрытых). Решение #367 пересказывает состав 1.9 обеими строками. ЛОВУШКА: .tausik/tausik исполняет .claude/scripts — правка в scripts/ не действует, пока не доехала через bootstrap --ide all; первый перевыпуск карты прошёл старым кодом. МУТАЦИЯ на копии живой базы: без ветки маркера одно позднее решение, упомянувшее kb-docs и release19-proof-integrity, сузило состав до ДВУХ историй (basis #368-копия); с веткой — 14 историй, basis #367, устав #360. Второй вариант мутации «на живой базе как есть» не показателен: #367 сам упоминает все 14 слагов, и вывод из прозы совпал бы случайно — записано, чтобы не принять совпадение за доказательство.
- 2026-09-13T11:22:28Z [implementation] — AC-1 ✓ tests/test_release_roadmap.py::TestDeclaredCompositionIsRead::test_a_later_mention_does_not_displace_a_declared_composition (падает на старом коде — проверено ревьюером против git show HEAD). AC-2 ✓ ::test_the_newest_declaration_wins_and_keeps_the_owner_s_order, ::test_the_english_spelling_of_the_line_is_the_same_line. AC-3 ✓ (негатив) ::test_an_unknown_slug_on_the_line_is_refused_by_name, ::test_an_empty_line_is_a_refusal_not_an_empty_release, ::test_the_list_ends_at_the_sentence_and_prose_inside_it_is_loud, ::test_the_line_is_read_in_any_case_and_a_repeat_is_refused. AC-4 ✓ ::test_the_named_charter_is_followed, ::test_the_named_charter_wins_where_the_chain_would_disagree, ::test_a_dangling_charter_falls_back_to_the_chain. AC-5 ✓ TestCompositionIsRead и TestCharterIsFollowed без правок ожиданий зелёные; ::test_a_journal_without_the_line_is_read_as_before_and_says_so. AC-6 ✓ TestOutsideTheReleaseOpenIsApartFromDone (2 теста). AC-7 ✓ решение #367 с «Устав: #360» и «Состав: …14 историй»; `tausik doc roadmap --check` → current; в ROADMAP.md устав #360, состав из #367, раздел «не входит» не содержит ни одной из десяти историй #360 (открытых вне состава — нет). AC-8 ✓ мутация на КОПИИ живой базы: без ветки _declared одно позднее решение с двумя упоминаниями даёт состав из 2 историй (basis #368-копия); с веткой — 14, basis #367 (журнал задачи). Ревью tausik-reviewer: 2 high (регистр маркера, дубль слага), 2 medium (тест часов не покрывал новый модуль, override устава без теста), 2 low — все шесть устранены, 45 тестов файла зелёные. Verify #2571 подписан.
- 2026-09-13T11:22:56Z [done] — Domain: карта, которую читает человек перед тегом, теперь совпадает с тем, что владелец решил: устав #360 и состав #367 из одного и того же набора историй, десять историй #360 больше не значатся «не входящими» в релиз, чью работу они составляют; закрытые истории вне состава названы закрытыми, а не «не в этой версии». Закрытие через CLI, потому что MCP-сервер исполнял копию scripts/ старше правки (bootstrap_drift: stale process) — это ожидаемое поведение по решению #189, не дефект.
