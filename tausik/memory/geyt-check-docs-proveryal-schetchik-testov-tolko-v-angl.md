---
slug: geyt-check-docs-proveryal-schetchik-testov-tolko-v-angl
title: "Гейт check_docs проверял счётчик тестов только в англ. формах; ru и badge-URL дрейфовали молча"
type: gotcha
tags:
  - check_docs
  - doc-drift
  - gates
  - i18n
  - meta-testing
task: gen-doc-constants-does-not-fix-readme-counts
edges: []
---

До этой правки _TEST_COUNT_PATTERNS матчил только: '![N tests]', '**N tests**', 'tests-N%20passed'. Реальные бейджи у нас формата 'tests-N-brightgreen' (shields color) — не матчились вообще. Русские формы ('![N тестов]', '**N тестов**', 'покрыто N тестами') — тоже. Отсюда '4341 тестов' висел в README.ru.md через несколько релизов, а --check молчал: он не смотрел на эти места.

Класс ошибки: гейт выглядит покрывающим («проверяет счётчик тестов»), но покрывает подмножество форм. Хуже отсутствия гейта, потому что создаёт ложную уверенность.

Что теперь покрыто (scripts/doc_drift_scanners.py::_TEST_COUNT_PATTERNS): badge-URL 'tests-N-<color>', badge-label EN+RU, bold EN+RU, проза 'covered by N tests' / 'покрыто N тестами'. Все узкие, по структурным якорям (внутри ![], **, shields-URL, или конкретной фразы) — не ловят числа в примерах кода (fenced-блоки исключены) и в произвольной прозе.

Инструмент починки: 'gen_doc_constants.py --write' регенерит constants.json И правит все cross-file места (write_cross_file_fixes), затем сам себя перепроверяет через --check. Идемпотентен. Совет гейта переписан на --write.

Мета-правило, выведенное отсюда и закреплённое в tests/test_gate_advice_is_actionable.py: гейт, печатающий 'run X', обязан иметь тест, что X действительно делает состояние валидным. check_docs советовал команду, которая не чинила README, месяцами.
