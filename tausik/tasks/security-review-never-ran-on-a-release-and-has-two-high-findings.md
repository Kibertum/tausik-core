---
slug: security-review-never-ran-on-a-release-and-has-two-high-findings
title: "Гейт безопасности релиза не запускался ни на одном релизе, и на первом же дал две HIGH-находки"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: ".github/workflows/** — гейт не смягчаем и не отключаем; чиним то, на что он показал"
relevant_files:
  - "scripts/audit_pytest_dedupe.py"
  - "scripts/brain_scrubbing.py"
  - "tests/test_brain_scrubbing.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/audit_pytest_dedupe.py"
  - "scripts/brain_scrubbing.py"
  - "tests/test_brain_scrubbing.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T09:19:13Z"
---

## Goal

PR релиза проходит security-review: обе HIGH-находки bandit устранены по существу, а не подавлены.

## Acceptance Criteria

1. `bandit -r scripts/` даёт НОЛЬ находок уровня HIGH; проверяется запуском, а не чтением диффа.
2. B324 в audit_pytest_dedupe: sha1 используется для дедупликации, а не для защиты, и это сказано в коде через usedforsecurity=False — подавление правила через nosec ЗАПРЕЩЕНО, потому что оно скрывает намерение вместо того, чтобы его назвать.
3. B613 в brain_scrubbing: класс символов в _ZERO_WIDTH_RE записан escape-последовательностями, а не литеральными невидимыми символами. Множество символов, которое он матчит, ДО и ПОСЛЕ правки совпадает — проверяется тестом, перебирающим все кодовые точки диапазонов.
4. НЕГАТИВНЫЙ сценарий: тест доказывает, что скраббер продолжает ловить невидимые символы — если правка сузила класс, тест краснеет. Модуль, который ищет невидимые символы, не имеет права перестать их находить ради тишины сканера.
5. НЕГАТИВНЫЙ сценарий: PR релиза на GitHub красный по security-review ЗАПРЕЩАЕТ мерж; зелёный security-review плюс зелёная матрица — условие мержа.

## Plan

## Rollback

git revert коммита; обе правки локальны и независимы

## Journal

- 2026-08-04T09:18:38Z [implementation] — Чек-лист доказательств. AC-1 (ноль HIGH): ✓ MANUAL: bandit 1.9.4, `bandit -r scripts/` — по важности {'LOW': 131, 'MEDIUM': 45}, HIGH отсутствуют. До правки было 2 HIGH. AC-2 (sha1 назван, а не подавлен): ✓ MANUAL: scripts/audit_pytest_dedupe.py::_signature — hashlib.sha1(..., usedforsecurity=False); строки `# nosec` в файле нет AC-3 (класс переписан escape'ами, множество совпадает): ✓ tests/test_brain_scrubbing.py::test_zero_width_class_matches_exactly_the_documented_ranges ✓ MANUAL: перебор кодовых точек 0x0..0x11000 — множество из 16 точек совпадает с документированными диапазонами, потерянных нет, лишних нет AC-4 (негативный: скраббер не перестал ловить): ✓ tests/test_brain_scrubbing.py::test_zero_width_class_matches_exactly_the_documented_ranges — если правка сузит класс, тест краснеет перечнем потерянных точек ✓ tests/test_brain_scrubbing.py::test_the_source_carries_no_invisible_characters_of_its_own ✓ MANUAL: 53 теста модуля зелёные AC-5 (негативный: красный security-review запрещает мерж): ✓ MANUAL: критерий исполняется ходом работы — PR #6 красный по security-review, мерж НЕ выполнен, работа ушла в эту задачу. Мерж состоится только после зелёного. Корень, стоящий отдельного упоминания: гейт не «сломался» — он ни разу не запускался. Событие, на которое он подписан (pull_request в main), не наступало, потому что релизы выкладывались прямым push в main. Вариант выкладки через PR, выбранный владельцем, и включил его впервые. Domain: обе находки — про реальные свойства файлов, а не про стиль. Невидимые bidi-символы в исходнике — ровно то, что цепочка поставок скиллов этого же проекта считает признаком атаки; модуль, который их ищет, нёс их сам.
