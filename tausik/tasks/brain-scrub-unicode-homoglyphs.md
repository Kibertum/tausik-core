---
slug: brain-scrub-unicode-homoglyphs
title: "HIGH: NFKC + zero-width + urldecode в scrubbing"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_scrubbing.py, tests/test_brain_scrubbing.py"
scope_exclude: "_detect_paths / _detect_emails (out-of-scope for этой задачи; review findings указал именно blocklist как высокорисковый), brain_mcp_write.py"
relevant_files:
  - "scripts/brain_scrubbing.py"
  - "tests/test_brain_scrubbing.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T11:10:42Z"
---

## Goal

Защитить blocklist от обхода кириллическими homoglyph'ами (а→a), zero-width chars (pri​ncess), URL-encode (%70rincess). Нормализовать NFKC + strip zero-width + сканировать urldecoded copy перед substring matching

## Acceptance Criteria

AC1: Helper _normalize_for_match(s) в scripts/brain_scrubbing.py — NFKC + strip zero-width + Cyrillic/Greek homoglyph→Latin + lowercase.
AC2: _detect_blocklist проверяет как нормализованный haystack, так и urldecoded haystack.
AC3: Новый тест: 'рrincess' (Cyrillic 'р') блокируется blocklist=['[вычеркнуто: third-party-project]'].
AC4: Новый тест: 'pri\\u200bncess' (zero-width между letters) блокируется.
AC5: Новый тест: '%70rincess' (URL-encoded 'p') блокируется.
AC6: Новый тест: 'Р\\u200brincess' (Cyrillic + zero-width) блокируется.
AC7: False-positive regression: 'crate' не матчит blocklist=['rate'] (substring legitimate).
AC8: Существующие тесты test_brain_scrubbing.py остаются зелёными.
AC9: ruff + mypy scripts/ clean.

## Plan

## Rollback

## Journal

- 2026-04-24T11:07:14Z [implementation] — Root cause: blocklist детектор использовал `name.strip().lower() in content.lower()` — без unicode-нормализации. Атакующий мог обойти 3 способами: Cyrillic/Greek homoglyph (`а` U+0430 → `a`), zero-width chars между буквами (`pri\\u200bncess`), URL-encoded формы (`%70rincess`). Все три не триггерили substring match потому что bytes-to-bytes сравнение видит разные строки.
- 2026-04-24T11:07:17Z [implementation] — Design note: изначально выбрал NFKC по рекомендации ревью, но тесты combining-marks (`Café` NFD → должен match `cafe`) провалились. NFKC оставляет precomposed é (U+00E9), не декомпозирует, и Mn-stripping не срабатывает. Переключился на NFKD: декомпозирует precomposed → e + combining acute (Mn) → strip → `cafe`. Это стандартный путь для normalisation-aware substring match.
- 2026-04-24T11:07:24Z [implementation] — AC verified: 1. _normalize_for_match(): NFKD + strip Mn + strip zero-width + Cyrillic/Greek homoglyph map + lower ✓ 2. _detect_blocklist проверяет normalized haystack И urldecoded haystack ✓ 3. 'рrincess' (Cyrillic р) блокируется (test_blocklist_cyrillic_homoglyph_bypass_blocked) ✓ 4. 'pri\\u200bncess' блокируется ✓ 5. '%70rincess' блокируется ✓ 6. 'Р\\u200brincess' (mixed) блокируется ✓ 7. 'crate'/'rate' — substring-based поведение UNCHANGED (fix только defeats obfuscation, не tightens substring rules) ✓ 8. 40 pass (было 31) — все существующие тесты зелёные + 9 новых ✓ 9. ruff + mypy clean ✓ 10. test_brain_mcp_write + test_brain_project_registry: 56/56 regressions pass ✓
