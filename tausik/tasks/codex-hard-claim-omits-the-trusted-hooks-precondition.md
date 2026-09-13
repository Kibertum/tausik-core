---
slug: codex-hard-claim-omits-the-trusted-hooks-precondition
title: "Матрица принуждения Codex объявляет Rule 1/Rule 2 hard без предусловия доверенного hook-профиля, которое live-проба доказала обязательным"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #251. docs/{en,ru}/model-providers.md: строки «Rule 1 Task before code | hard» и «Rule 2 Scope Boundaries | hard» матрицы, а выше — «so Rule 1 and the write ACL are ENFORCED there, not merely instructed»; CHANGELOG.md Unreleased: «So Rule 1 and the write ACL are HARD under Codex, not advisory». Слово «trust» не встречается ни в одном файле docs/. Живая приёмка codex-live-acceptance-proves-the-host (журнал 2026-09-13T10:28): недоверенная сессия Codex 01a09737… выполнила запрещённую Path('outside.txt').write_text(...) с exit 0 — сгенерированный .codex/hooks.json без доверия пользователя НЕ запускается; отказ получен только в сессии с доверенным hook-профилем (01a0973e…, exit 2 от bash_write_gate на захваченном событии). Значит утверждение «hard» без предусловия — заявление шире механизма, ровно тот класс, который tests/test_codex_support_matrix.py обязан ловить и не ловит: он проверяет, что у строки hard есть артефакт в профиле, но не что у строки названо условие, при котором артефакт вообще исполняется хостом. Починка: в обеих таблицах строки Rule 1 и Rule 2 получают предусловие в третьем столбце («…runs only after the user has trusted the project hooks in Codex; an untrusted profile enforces nothing — measured live, session #251»), прозаические абзацы и запись CHANGELOG в Unreleased правятся тем же условием (Unreleased не опубликован — решение #352 о неизменности касается опубликованных заметок), enforcement-coverage EN/RU получают абзац о доверии как о втором условии покрытия, отличном от «артефакт развёрнут»; тест матрицы требует слово доверия в обеих языковых строках Rule 1/Rule 2 и краснеет на его удалении.

## Acceptance Criteria

AC-1: в docs/en/model-providers.md и docs/ru/model-providers.md строки Rule 1 и Rule 2 матрицы Codex называют предусловие доверенного hook-профиля и ссылаются на живой замер; прозаическое «ENFORCED there, not merely instructed» несёт то же условие. AC-2: tests/test_codex_support_matrix.py требует маркер доверия (trust/довер) в третьем столбце обеих строк на обоих языках; мутация — удаление условия из одной строки одного языка — краснит тест (доказано прогоном). AC-3: docs/{en,ru}/enforcement-coverage.md объясняют, что покрытие правила на Codex имеет ДВА условия — артефакт в профиле и доверие хоста к хукам — и что doctor/скан профиля видит только первое. AC-4: CHANGELOG.md и CHANGELOG.ru.md: запись Unreleased «Codex is a first-class bootstrap target» несёт условие доверия, и добавлена новая запись Fixed о сужении заявления с отсылкой к live-пробе. AC-5: ни одно место в docs/, README*, AGENTS.md не утверждает hard-принуждение Codex без условия: grep по «HARD under Codex|ENFORCED there|hard.*Codex» даёт только строки с условием. AC-6: signed verify.

## Plan

## Rollback

git revert; документация вернётся к безусловному заявлению, тест — к прежней проверке.

## Journal
