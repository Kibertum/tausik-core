---
slug: ac-evidence-parity-asymmetry-review-domain
title: "REVIEW_RE and DOMAIN_RE break the module's own looseness-parity invariant, in opposite directions"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 16
defect_of: null
scope: "scripts/ac_evidence_detectors.py, tests/test_ac_evidence_language_parity.py"
scope_exclude: "The accepted keyword-theater weakness itself (matching a word not a fact) — that is a separate, disclosed follow-up in gate_ac_check.checklist_missing, not this task; NEGATIVE_RE/MANUAL_RE (already symmetric)"
relevant_files:
  - "scripts/ac_evidence_detectors.py"
  - "tests/test_ac_evidence_language_parity.py"
  - "tests/test_ac_evidence.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T06:33:51Z"
---

## Goal

ac_evidence_detectors claims (docstring + convention #170) that each prose detector is equally loose in Russian and English. Two violate it. REVIEW_RE: English requires a structural phrase (/review, 'review record') while Russian credits the bare word 'ревью' — so 'code review completed' is HARD-blocked (checklist_missing, high/critical) where 'код прошёл ревью' passes. DOMAIN_RE: reversed — English '\\bdomain\\b' is bounded but Russian 'доменн' is an unbounded stem that credits 'поддоменное' (subdomain), a false positive English never had (#301: port the false-positive list). Restore symmetry: make REVIEW_RE bare-word in English too (\\breview\\w*, aligning with NEGATIVE_RE/MANUAL_RE which are already bare both sides), and bound the Russian domain stem (\\bдоменн\\w*) so it stops crediting compounds. Both languages then credit the same KINDS of things.

## Acceptance Criteria

1. REVIEW_RE credits a bare English 'review' stem: REVIEW_RE.search('code review completed') and 'reviewed by senior' both True, so English is as loose as the Russian bare 'ревью' — and 'ревью' stays True. 2. REVIEW_RE keeps its prior English coverage (adversarial, 'review record', '/review') and Russian 'состязательн'. 3. Negative/false-positive boundary — DOMAIN_RE no longer credits a compound: DOMAIN_RE.search('поддоменное имя проверено') is False AND the English analogue 'subdomain check' is False (symmetric), while 'доменная проверка' stays True. 4. Negative — an unrelated word does not falsely credit: 'previewing data' does NOT match REVIEW_RE. 5. The existing parity suite (test_ac_evidence_language_parity.py) stays green, including TestNoFalseCreditFromUnrelatedProse and both English+Russian sample tests. 6. New cross-language symmetry tests assert REVIEW ('code review' EN == 'ревью' RU) and DOMAIN ('subdomain' EN == 'поддоменное' RU) return the SAME boolean. 7. Module docstring updated so its 'both bare stem' claim is now true for REVIEW_RE. 8. Full scoped verify green.

## Plan

## Rollback

## Journal

- 2026-07-25T06:33:22Z [implementation] — Fixed both parity asymmetries. REVIEW_RE: English now bare \breview\w* (subsumes /review, review record; adds reviewed/reviewer) — symmetric with Russian bare ревью. DOMAIN_RE: Russian stem bounded \bдоменн\w* — no longer credits compound поддоменное (subdomain), matching English \bdomain\b. Docstring made raw (r\"\"\") to kill an invalid-escape DeprecationWarning from the literal \w/\b, and rewritten to describe the two-directional realignment. Added TestTheTwoLanguagesAreEquallyLoose (same-boolean invariants for review/domain across languages). Rippled fixture: tests/test_ac_evidence.py used 'Reviewed code' as a supposedly keyword-free line — now correctly a review keyword — changed to 'Refactored the parser'. Suites: parity 14 passed; AC/checklist/verification consumers 221 passed; no escape/deprecation warning on import.
- 2026-07-25T06:33:49Z [implementation] — AC verified: 1. ✓ tests/test_ac_evidence_language_parity.py::TestTheTwoLanguagesAreEquallyLoose::test_review_credits_a_bare_stem_in_both_languages — 'code review completed' and 'ревью' both True, same boolean 2. ✓ test_review_keeps_its_old_english_forms_and_rejects_lookalikes — 'review record'/'/review'/'состязательн' still match 3. ✓ Negative/false-positive: test_domain_rejects_a_compound_in_both_languages — 'subdomain check' and 'поддоменное имя проверено' both None; test_domain_still_credits... keeps 'доменная' True 4. ✓ Negative: 'previewing the data' returns None from REVIEW_RE (lookalike rejected) 5. ✓ tests/test_ac_evidence_language_parity.py 14 passed incl. TestNoFalseCreditFromUnrelatedProse; AC/checklist/verification consumers 221 passed 6. ✓ same-boolean symmetry pins added for REVIEW (EN code review == RU ревью) and DOMAIN (EN subdomain == RU поддоменное) 7. ✓ module docstring made raw (r-string) — no invalid-escape DeprecationWarning on import — and rewritten to state the realignment 8. ✓ verify run #1304 exit=0, pytest scoped over 2 test files PASS
