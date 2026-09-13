---
slug: test-ref-detector-recognises-only-python-paths
title: "GitLab #16: гейт QG-2 требует ссылку на существующий тест, но TEST_REF_RE распознаёт только .py — в Rust/Go/TS проекте требование невыполнимо, а текст ошибки говорит «path does not resolve»"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Тикет GitLab #16 (владелец, Rust/tauri проект на 1.8.0): на тире substantial закрытие с журналом «✓ src-tauri/src/commands/project_extras_tests.rs::a_project_copy_of_an_inherited_label_shadows_it» (файл существует, cargo test зелёный) отбивается: «requires at least one acceptance criterion backed by a test that EXISTS … a path that does not resolve is treated as no evidence». ЗАМЕР, смена #251: scripts/ac_evidence_detectors.py:73 TEST_REF_RE = `(tests?/[\w/.\-]+\.py(?:::[\w_]+)?|test_[\w_]+\.py(?:::[\w_]+)?)` — обе ветки требуют .py. Три следствия из тикета: обход через «✓ verification_run #N» слабее (говорит «набор был зелёный», а не «этот критерий проверяется этим тестом»); предупреждение «requires test-ref evidence (e.g. 'tests/test_foo.py::test_bar')» печатается при УСПЕШНОМ закрытии как вечный шум; агент, следуя тексту буквально, пишет питоновские пути в Rust-проекте — гейт подталкивает к лжи в доказательствах. Починка: TEST_REF_RE принимает `<путь>::<имя>` и типовые формы тестов экосистем — расширения .py .rs .go .ts .tsx .js .mjs .java .kt .rb .php .cs .swift .dart и имена вида *_test.go, *.test.ts, *_tests.rs, *Test.java, *_spec.rb; проверка существования пути остаётся прежней (резолв от корня проекта); текст ошибки различает «путь не резолвится» и «форма не распознана» и приводит пример в языке проекта; предупреждение о test-ref не печатается, когда закрытие принято по verification_run.

## Acceptance Criteria

AC-1: параметризованный тест: ссылки `src-tauri/src/commands/project_extras_tests.rs::name`, `pkg/foo_test.go::TestBar`, `src/foo.test.ts`, `src/test/FooTest.java::bar`, `spec/foo_spec.rb` распознаются как test-ref; `README.md::x`, `scripts/foo.py` (не тест) — нет. AC-2: существующий .py-путь распознаётся как прежде (все существующие тесты ac_evidence зелёные). AC-3: проверка существования: `.rs`-ссылка на существующий файл во временном проекте засчитывается гейтом QG-2 substantial; на несуществующий — отбивается с текстом «path does not resolve»; ссылка непризнанной формы отбивается с текстом «form not recognised» и примером. AC-4: при закрытии, принятом по verification_run, предупреждение «requires test-ref evidence» не печатается (тест на вывод). AC-5: signed verify; CHANGELOG EN/RU; docs/{ru,en}/verify-glossary.md или testing-principles называют признаваемые формы.

## Plan

## Rollback

git revert; детектор снова только .py.

## Journal
