---
slug: issue4-pyyaml-test-guard
title: "Issue #4: clean-checkout без pyyaml не должен падать на RENAR-тестах + документировать dep"
status: done
epic: null
story: null
complexity: simple
role: null
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "tests/test_renar_conformance.py, tests/test_renar_export.py, CONTRIBUTING.md"
scope_exclude: null
relevant_files:
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
  - CONTRIBUTING.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-30T14:05:06Z"
---

## Goal

Свежий чекаут без PyYAML: RENAR-тесты (test_renar_conformance, test_renar_export) скипаются через pytest.importorskip вместо collection-error; CONTRIBUTING.md (RU+EN) документирует pyyaml как опциональную dev-зависимость для RENAR-тестов. Консистентно с гард-тестом test_no_hard_yaml_import (yaml — опциональная dep).

## Acceptance Criteria

1. test_renar_conformance.py и test_renar_export.py используют pytest.importorskip("yaml") вместо top-level import yaml. 2. Негативный кейс: при ОТСУТСТВИИ pyyaml эти два модуля СКИПАЮТСЯ (pytest skipped), а НЕ падают с collection-error/ImportError. 3. test_no_hard_yaml_import.py остаётся зелёным. 4. Полный прогон tests/ зелёный когда pyyaml установлен. 5. CONTRIBUTING.md RU и EN секции упоминают pyyaml как опциональную dev-dep для RENAR-тестов рядом с pytest/ruff.

## Plan

## Rollback

## Journal

- 2026-06-30T13:59:56Z [implementation] — Заменил top-level `import yaml` на `pytest.importorskip("yaml")` в test_renar_conformance.py и test_renar_export.py. CONTRIBUTING.md RU+EN: pyyaml добавлен в pip install + note про опциональность. Verify: 39 passed (affected+guard) при наличии yaml; негативный кейс с meta-path блокатором yaml → 2 SKIPPED (не error). test_no_hard_yaml_import зелёный.
- 2026-06-30T14:05:05Z [implementation] — AC verified: 1. ✓ test_renar_conformance.py:18 + test_renar_export.py:18 используют pytest.importorskip("yaml"). 2. ✓ Негативный кейс — meta-path блокатор yaml → оба модуля SKIPPED (не error/ImportError). 3. ✓ test_no_hard_yaml_import зелёный (в общем прогоне). 4. ✓ Полный tests/ зелёный с pyyaml: 4313 passed, 12 skipped, exit 0 (262s). 5. ✓ CONTRIBUTING.md RU+EN: pyyaml в pip install + note про опциональность RENAR-тестов.
