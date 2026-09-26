---
slug: test-ref-detector-recognises-only-python-paths
title: "GitLab #16: гейт QG-2 требует ссылку на существующий тест, но TEST_REF_RE распознаёт только .py — в Rust/Go/TS проекте требование невыполнимо, а текст ошибки говорит «path does not resolve»"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "scripts/ac_evidence_detectors.py, scripts/ac_evidence*.py (гейт и сообщение), tests/, docs/ru/, docs/en/, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Правило «substantial требует test-ref или verification_run» не ослаблять; не принимать голую галочку."
relevant_files:
  - "scripts/ac_evidence_detectors.py"
  - "scripts/service_ac_evidence.py"
  - "scripts/gate_test_citation.py"
  - "scripts/gate_ac_check.py"
  - "tests/test_test_ref_beyond_python.py"
  - "tests/test_gate_test_citation.py"
  - "tests/test_checklist_hardgate.py"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T13:15:48Z"
resolution: null
resolution_reason: null
---

## Goal

Тикет GitLab #16 (владелец, Rust/tauri проект на 1.8.0): на тире substantial закрытие с журналом «✓ src-tauri/src/commands/project_extras_tests.rs::a_project_copy_of_an_inherited_label_shadows_it» (файл существует, cargo test зелёный) отбивается: «requires at least one acceptance criterion backed by a test that EXISTS … a path that does not resolve is treated as no evidence». ЗАМЕР, смена #251: scripts/ac_evidence_detectors.py:73 TEST_REF_RE = `(tests?/[\w/.\-]+\.py(?:::[\w_]+)?|test_[\w_]+\.py(?:::[\w_]+)?)` — обе ветки требуют .py. Три следствия из тикета: обход через «✓ verification_run #N» слабее (говорит «набор был зелёный», а не «этот критерий проверяется этим тестом»); предупреждение «requires test-ref evidence (e.g. 'tests/test_foo.py::test_bar')» печатается при УСПЕШНОМ закрытии как вечный шум; агент, следуя тексту буквально, пишет питоновские пути в Rust-проекте — гейт подталкивает к лжи в доказательствах. Починка: TEST_REF_RE принимает `<путь>::<имя>` и типовые формы тестов экосистем — расширения .py .rs .go .ts .tsx .js .mjs .java .kt .rb .php .cs .swift .dart и имена вида *_test.go, *.test.ts, *_tests.rs, *Test.java, *_spec.rb; проверка существования пути остаётся прежней (резолв от корня проекта); текст ошибки различает «путь не резолвится» и «форма не распознана» и приводит пример в языке проекта; предупреждение о test-ref не печатается, когда закрытие принято по verification_run.

## Acceptance Criteria

AC-1: параметризованный тест: ссылки src-tauri/src/commands/project_extras_tests.rs::name, pkg/foo_test.go::TestBar, src/foo.test.ts, src/test/FooTest.java::bar, spec/foo_spec.rb распознаются как test-ref; README.md::x и scripts/foo.py (не тест) — нет. AC-2: существующий .py-путь распознаётся как прежде (все существующие тесты ac_evidence зелёные). AC-3: НЕГАТИВ: проверка существования: .rs-ссылка на существующий файл во временном проекте засчитывается гейтом QG-2 substantial; на несуществующий — отбивается с текстом «path does not resolve» (ошибка); ссылка непризнанной формы отбивается с текстом «form not recognised» и примером. AC-4: при закрытии, принятом по verification_run, предупреждение «requires test-ref evidence» не печатается (тест на вывод). AC-5: signed verify; CHANGELOG EN/RU; docs/{ru,en}/verify-glossary.md или testing-principles называют признаваемые формы.

## Plan

## Rollback

git revert; детектор снова только .py.

## Journal

- 2026-09-13T13:14:36Z [implementation] — Сделано: TEST_REF_RE — один объявленный перечень форм (каталог tests/test/__tests__/spec + расширения; имя-конвенция test_x.py, x_test(s).rs/go/ex, x.test|spec.ts/js, x_spec.rb, XTest.java/kt/cs/swift/php/dart; ::сегменты с [id]); find_test_refs/find_unrecognised_refs — ПОТОКЕННО с anchored fullmatch (было findall по строке: 42 с на 40 КБ 'deep/…', стало 3 мс; 160 КБ — 13 мс). Резолвер: файл, названный тестом, принимается вне корня tests/ по НОРМАЛИЗОВАННОМУ относительному пути (tests/../src/x.py остаётся исходником), не в каталогах _discovery_skip (node_modules, venv, профили IDE), и без ::name обязан нести маркер теста (#[test], func Test, it(, @Test, def test_ …); ::name для не-.py — после ключевого слова объявления (fn/func/def/function/void, с Go-receiver) или как строковый аргумент it/test/describe — после вырезания строчных комментариев. Гейт: диагноз CITED BUT FORM NOT RECOGNISED vs CITED BUT NOT RESOLVED; пометка «requires test-ref evidence» молчит только при ПРОВЕРЕННОМ verification_run (_measurement_verified). МУТАЦИЯ: старый .py-only regex → 11 из 18 новых тестов красные. Ревью tausik-reviewer: 1 critical (обход test_roots для vendored/любого файла по имени) + 3 high (.py в суффиксной форме; комментарий/строка как объявление; O(n²) regex) + 2 medium — все шесть закрыты, каждый с негативным тестом (TestTheWideningDoesNotCheapenACitation, 6 тестов). Dedupe 290/686.
- 2026-09-13T13:15:45Z [implementation] — AC-1 ✓ tests/test_test_ref_beyond_python.py::TestTheDetectorReadsEcosystemForms::test_a_test_form_is_read_whole[8 форм: .rs::name, _test.go::TestBar, .test.ts, __tests__/…tsx, FooTest.java::bar, _spec.rb, FooTest.php::testBar, pytest node id с [case-3]]; ::test_a_non_test_is_not_read_as_one[README.md::x, scripts/foo.py, docs/en/hooks.md]. AC-2 ✓ tests/test_gate_test_citation.py (18), tests/test_checklist_hardgate.py, tests/test_ac_evidence*.py, tests/test_audit_closure_evidence.py — 155 passed без правок ожиданий; .py-путь читается как прежде. AC-3 ✓ (НЕГАТИВ) ::TestTheResolverAcceptsATestNamedAsOneBesideTheCode::test_rust_go_and_ts_citations_resolve (существующий .rs/.go/.test.ts засчитан гейтом), ::test_a_missing_file_or_an_undeclared_name_still_fails_closed; ::TestTheRefusalNamesTheRightCause::test_the_refusal_names_one_cause_and_not_the_other[unrecognised-form → CITED BUT FORM NOT RECOGNISED; recognised-but-missing → CITED BUT NOT RESOLVED], ::test_a_rust_citation_that_exists_clears_the_substantial_gate. AC-4 ✓ ::TestTheTierNoteIsSilentOnAMeasuredClose (verified run → пометки нет) и ::TestTheWideningDoesNotCheapenACitation::test_the_tier_note_stays_when_the_run_is_not_verified_for_this_task (непроверенный run → пометка остаётся). AC-5 ✓ verify #2589 подписан; CHANGELOG EN/RU; docs/{en,ru}/testing-principles.md — абзац «Citing a test as AC evidence / Ссылка на тест как доказательство AC». Domain: Rust/Go/TS-проект может честно сослаться на свой зелёный тест и закрыть substantial-задачу, а цена выдуманной ссылки не упала: vendored tests/, файл-однофамилец без маркера, имя в комментарии — по-прежнему отказ; замер производительности 42 с → 3 мс на 40 КБ заметок.
- 2026-09-26T18:44:26Z [done] — EVIDENCE-UNPROVEN: FooTest.php::testBar — git never carried this path or member under any directory
- 2026-09-26T18:44:32Z [done] — EVIDENCE-UNPROVEN: x_spec.rb — git never carried this path or member under any directory
