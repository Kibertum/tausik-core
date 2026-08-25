---
slug: rule7-rootcause-nag-inline-template
title: "Rule-7 root-cause nag: show canonical template + valid categories inline (stop dogfooding friction)"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/root_cause.py (_RC_RE + parse), scripts/service_task_done.py (nag/block messages), tests/test_root_cause_structured.py (new label-form cases)"
scope_exclude: "scripts/nudge_escalation.py (escalation mechanics unchanged), docs/*"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T12:30:37Z"
---

## Goal

Stop the Rule-7 root-cause nag friction (fired 9× in session #90) by making it self-actionable: the nudge + hard-block messages must QUOTE the canonical template and the closed-list categories inline instead of pointing to a doc. Also loosen the parser to accept the label form 'Root cause — <category>: ...' so reasonable phrasing isn't silently rejected.

## Acceptance Criteria

AC-1: service_task_done.py root-cause nudge message quotes the canonical template 'Root cause (<category>): … Prevention: …' AND the closed-list categories inline (sourced from ROOT_CAUSE_CATEGORIES, not hardcoded). AC-2: the keyword-floor hard-block message also steers to the structured template + categories (write-it-right-once). AC-3: root_cause._RC_RE additionally accepts the bracket-less label form 'Root cause — <category>: <desc>. Prevention: <prev>.' where <category> is a closed-list token; bracket form + RU keywords still parse. Negative: 'Root cause (banana): x. Prevention: y.' still returns None (unknown category); 'Root cause: off-by-one in pagination' still returns None (no prevention/category); all existing test_root_cause_structured.py cases stay green. AC-4: new tests cover the label form (accept) and a label-form with unknown category (reject). AC-5: full root-cause + nudge test files green via .tausik/tausik (fresh modules).

## Plan

## Rollback

git checkout -- scripts/root_cause.py scripts/service_task_done.py tests/test_root_cause_structured.py; pure logic+message change, no migrations/flags. Nudge is advisory (never blocks) so a regex regression cannot block closes.

## Journal

- 2026-06-14T12:30:12Z [implementation] — Implemented inline-template nag + label-form parser. service_task_done.py: nudge & hard-block messages now quote canonical template + ROOT_CAUSE_CATEGORIES inline (moved builders to root_cause.missing_root_cause_message/structured_nudge_message — keeps file at 399<400 after the audit-flagged 400-line cap). root_cause._RC_RE: added bracket-less label branch (cat_l constrained to closed-list alternation; cat_b bracket form still free-text validated in Py). 4 new label-form tests. Tests: 50 passed (root_cause+failclosed+nudge+task_done_v1). filesize gate clean. Security warning on start = false positive (message/regex change, no threat surface).
- 2026-06-14T12:30:28Z [implementation] — AC-1 pass: structured_nudge_message() quotes template + categories_str() inline (root_cause.py:147). AC-2 pass: missing_root_cause_message() steers to structured template+categories (root_cause.py:130). AC-3 pass: _RC_RE label branch accepts 'Root cause — logic-error: ...'; tested test_label_form_dash_accepted/colon_then_dash/all_categories. AC-4 pass: test_label_form_unknown_category_rejected + existing banana/keyword-only stay None. AC-5 pass: 50 passed (test_root_cause_structured+failclosed+nudge+task_done_v1). Negative: unknown category & no-prevention still return None; filesize gate clean (399<400). Domain: a fresh agent reading only the nag can now comply without opening any doc — the exact friction (9x in #90) is removed.
- 2026-06-14T12:30:37Z [implementation] — AC verified: 1. ✓ structured_nudge_message() quotes template + categories inline (root_cause.py). 2. ✓ missing_root_cause_message() steers to structured template+categories. 3. ✓ _RC_RE label branch accepts 'Root cause — logic-error: ...' (test_label_form_dash_accepted/colon_then_dash/all_categories_parse). 4. ✓ test_label_form_unknown_category_rejected + banana/keyword-only stay None. 5. ✓ 50 passed (test_root_cause_structured+failclosed+nudge+task_done_v1). Negative: unknown category & missing prevention still return None; filesize gate clean 399<400. Domain: a fresh agent reading only the nag complies without opening any doc — removes the 9x/#90 friction.
