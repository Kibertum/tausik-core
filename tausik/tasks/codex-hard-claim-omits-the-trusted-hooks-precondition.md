---
slug: codex-hard-claim-omits-the-trusted-hooks-precondition
title: "Матрица принуждения Codex объявляет Rule 1/Rule 2 hard без предусловия доверенного hook-профиля, которое live-проба доказала обязательным"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "docs/en/model-providers.md, docs/ru/model-providers.md, docs/en/enforcement-coverage.md, docs/ru/enforcement-coverage.md, tests/test_codex_support_matrix.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Не менять генератор хуков Codex и bootstrap; не расширять матрицу новыми правилами; не трогать .agents/."
relevant_files:
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "tests/test_codex_support_matrix.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T11:34:29Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #251. docs/{en,ru}/model-providers.md: строки «Rule 1 Task before code | hard» и «Rule 2 Scope Boundaries | hard» матрицы, а выше — «so Rule 1 and the write ACL are ENFORCED there, not merely instructed»; CHANGELOG.md Unreleased: «So Rule 1 and the write ACL are HARD under Codex, not advisory». Слово «trust» не встречается ни в одном файле docs/. Живая приёмка codex-live-acceptance-proves-the-host (журнал 2026-09-13T10:28): недоверенная сессия Codex 01a09737… выполнила запрещённую Path('outside.txt').write_text(...) с exit 0 — сгенерированный .codex/hooks.json без доверия пользователя НЕ запускается; отказ получен только в сессии с доверенным hook-профилем (01a0973e…, exit 2 от bash_write_gate на захваченном событии). Значит утверждение «hard» без предусловия — заявление шире механизма, ровно тот класс, который tests/test_codex_support_matrix.py обязан ловить и не ловит: он проверяет, что у строки hard есть артефакт в профиле, но не что у строки названо условие, при котором артефакт вообще исполняется хостом. Починка: в обеих таблицах строки Rule 1 и Rule 2 получают предусловие в третьем столбце («…runs only after the user has trusted the project hooks in Codex; an untrusted profile enforces nothing — measured live, session #251»), прозаические абзацы и запись CHANGELOG в Unreleased правятся тем же условием (Unreleased не опубликован — решение #352 о неизменности касается опубликованных заметок), enforcement-coverage EN/RU получают абзац о доверии как о втором условии покрытия, отличном от «артефакт развёрнут»; тест матрицы требует слово доверия в обеих языковых строках Rule 1/Rule 2 и краснеет на его удалении.

## Acceptance Criteria

AC-1: в docs/en/model-providers.md и docs/ru/model-providers.md строки Rule 1 и Rule 2 матрицы Codex называют предусловие доверенного hook-профиля и ссылаются на живой замер; прозаическое «ENFORCED there, not merely instructed» несёт то же условие. AC-2: НЕГАТИВ: tests/test_codex_support_matrix.py требует маркер доверия (trust/довер) в третьем столбце обеих строк на обоих языках; мутация — удаление условия из одной строки одного языка — даёт ошибку теста (доказано прогоном). AC-3: docs/{en,ru}/enforcement-coverage.md объясняют, что покрытие правила на Codex имеет ДВА условия — артефакт в профиле и доверие хоста к хукам — и что doctor/скан профиля видит только первое. AC-4: CHANGELOG.md и CHANGELOG.ru.md: запись Unreleased «Codex is a first-class bootstrap target» несёт условие доверия, и добавлена новая запись Fixed о сужении заявления с отсылкой к live-пробе. AC-5: ни одно место в docs/, README*, AGENTS.md не утверждает hard-принуждение Codex без условия: grep по «HARD under Codex|ENFORCED there|hard.*Codex» даёт только строки с условием. AC-6: signed verify.

## Plan

## Rollback

git revert; документация вернётся к безусловному заявлению, тест — к прежней проверке.

## Journal

- 2026-09-13T11:33:58Z [implementation] — Сделано: обе строки Rule 1/Rule 2 матрицы EN/RU несут «только после того, как пользователь доверил хуки проекта в Codex; недоверенный профиль не принуждает ничего (замерено живьём, смена #251)»; абзац «ENFORCED there / ПРИНУЖДАЮТСЯ» продолжен тем же условием с описанием обоих исходов пробы; enforcement-coverage EN/RU получили раздел «У перехвата два условия, а скан видит одно» со ссылкой на матрицу; CHANGELOG Unreleased: запись «Codex is a first-class bootstrap target» дополнена условием (Unreleased не опубликован — #352 не нарушено), добавлена запись Fixed EN/RU; счётчик whats-new 233→234. Тест: две новые проверки (строки матрицы по маркеру trusted/довери; абзац по ключевой фразе). МУТАЦИЯ: снятие условия из RU-строки Rule 1 → 1 failed, восстановление → 7 passed. AC-5 grep: все вхождения HARD/ENFORCED/ПРИНУЖДАЮТСЯ идут с условием; единственное «hard...Codex» без условия — историческая строка 1.7 про IDE-discovery, не о принуждении.
- 2026-09-13T11:34:16Z [implementation] — AC-1 ✓ docs/en/model-providers.md:97-98 и docs/ru/model-providers.md:98-99 — строки Rule 1/Rule 2 с условием доверия и ссылкой на замер смены #251; абзац :66 обоих языков несёт то же условие и оба исхода пробы. AC-2 ✓ (НЕГАТИВ) tests/test_codex_support_matrix.py::test_host_interception_rows_state_the_trust_precondition[en|ru], ::test_no_page_claims_codex_enforcement_without_the_precondition[en|ru]; мутация — удаление условия из RU-строки Rule 1 — 1 failed, восстановлено — 7 passed (журнал). AC-3 ✓ docs/{en,ru}/enforcement-coverage.md, раздел «Two conditions for an interception, and the scan sees one» / «У перехвата два условия, а скан видит одно». AC-4 ✓ CHANGELOG.md:318 и CHANGELOG.ru.md:303 — запись о first-class bootstrap дополнена условием; новая запись Fixed EN/RU в Unreleased; whats-new счётчик 234 (test_release_notes_1_9 зелёный). AC-5 ✓ grep по docs/, README*, AGENTS.md, CHANGELOG*: каждое HARD/ENFORCED/ПРИНУЖДАЮТСЯ идёт с условием (журнал). AC-6 ✓ verify #2574 подписан. Domain: читатель матрицы теперь узнаёт то же, что узнал живой Codex-хост: сгенерированный профиль без доверия пользователя не защищает, и «hard» истинно только под этим условием — заявление не шире механизма.
