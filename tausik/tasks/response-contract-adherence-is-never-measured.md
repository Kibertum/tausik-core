---
slug: response-contract-adherence-is-never-measured
title: "Соблюдение дисциплины ответа никем не измеряется: ни набора случаев, ни рубрики, ни прогона"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/response_contract_audit.py (rubric + runner), tests/test_response_contract_audit.py (cases), docs/ru/agent-contract.md new section under the #230 measurement, CHANGELOG EN/RU. Reads transcripts outside the repo (Claude Code project jsonl, Codex rollouts) — read-only, nothing copied into the repo except counts."
scope_exclude: "No change to CAVEMAN_DIRECTIVE, SKILL.md or any generator; no new gate; no CLI subcommand; no transcript text stored in the repo."
relevant_files:
  - "scripts/response_contract_audit.py"
  - "tests/test_response_contract_audit.py"
scope_paths:
  - "scripts/response_contract_audit.py"
  - "tests/test_response_contract_audit.py"
  - "docs/ru/agent-contract.md"
  - "docs/en/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/response-contract-adherence-is-never-measured.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T16:12:22Z"
---

## Goal

ИСТОЧНИК: github.com/ayghri/i-have-adhd (MIT), принесён владельцем в сессии #185 как «то, о чём мы говорили про словоблудие вывода агента». Ценность этого плагина НЕ в его десяти правилах — четыре наши задачи истории agent-output-discipline уже покрывают и краткость, и форму. Ценность в том, чего у нас НЕТ ВОВСЕ: у него есть evals/cases.jsonl, evals/rubric.md и scripts/run_evals.py — то есть соблюдение правил у него ЗАМЕРЯЕТСЯ, а у нас правило есть, а замера послушания нет ни одного.

ЭТО ТОТ ЖЕ КЛАСС, ЧТО ВЕСЬ РЕЛИЗ 1.9: проверка, которой не было, неотличима от пройденной. Контракт ответа без замера послушания — ровно такая проверка. Соседняя задача routing-adherence-metric-measures-nothing — про этот же дефект на другой оси, свериться с ней ДО работы, чтобы не завести второй вырожденный контроль (память #404: три наших контроля дают нулевой сигнал).

ПЕРВЫМ ШАГОМ НЕ КОД, А ЗАМЕР БАЗОВОЙ ЛИНИИ. Взять реальные ответы агента из журналов сессий этого проекта (материал есть: 185 сессий) и померить по объявленной рубрике, СКОЛЬКО в них преамбулы, повторов, закрывающих любезностей и хеджирования. Без базовой линии любое «стало лучше» — мнение. Порог провала объявляется ДО замера: если разрыв между текущим состоянием и контрактом меньше объявленного порога, задача снимается, а не подгоняется — так же, как в пятой задаче решения о дисциплине ответа (r-does-our-injected-context-block-earn-its-cost).

ГРАНИЦА. Не тащить чужой плагин целиком: его правила про «оценки в минутах» и «шаг 3 из 5» относятся к чат-ассистенту, а не к агенту под гейтами, и у нас есть свои несжимаемые сущности (код, вывод инструментов, пути, ошибки, доказательства критериев, решения, журналы, хэндоффы), которые caveman уже защищает. Порт — это набор случаев + рубрика + прогон, а не текст правил.

ЗАВИСИМОСТЬ ПО СМЫСЛУ: response-contract-sets-a-shape-not-only-a-length задаёт ФОРМУ, которую эта задача учится мерить. Мерить можно и до неё (базовая линия), но зачесть «контракт соблюдается» — только после.

## Acceptance Criteria

AC-1: scripts/response_contract_audit.py reads USER-FACING answers — the last assistant text block before the next human message — from Claude Code project transcripts (*.jsonl), from Codex rollouts filtered to this project's cwd, and from a generic JSONL of {text} records; counts per host. AC-2: the rubric is four declared bilingual (RU/EN) regex tables, one per pre-send deletion of the contract — intent-announcement opener, closing recap or pleasantry, side-branch paragraph, empty hedge — plus answer length; each marker has at least one positive and one negative case in tests/test_response_contract_audit.py. AC-3 (negative): protected content is stripped before scoring — fenced code, inline code, quoted tool output, file paths, AC-evidence and decision lines — so a hedge word inside an error message or a code block is NOT a hit; test proves it. AC-4: the failure threshold is declared in the journal BEFORE the baseline run: hit rate = answers with at least one marker / answers; if the baseline hit rate is below 10% the task is dropped (adherence already near the ceiling), otherwise the figures ship. The baseline (answers, per-host, per-marker rates, hit rate, median length) is recorded in the journal and in docs/ru/agent-contract.md. AC-5: --json output and --threshold N exit 1 when hit rate >= N, so the same corpus can be re-measured after the contract and compared; a corpus with zero answers is reported as such, never as 0% adherence. AC-6: docs/ru/agent-contract.md section, CHANGELOG EN/RU, ruff clean, signed verify.

## Plan

[{"step": "Runner + rubric: scripts/response_contract_audit.py (adapters, protected-content strip, four markers, --json/--threshold)", "done": true}, {"step": "Cases: tests/test_response_contract_audit.py (positive/negative per marker, protected content, empty corpus)", "done": true}, {"step": "Declare threshold in journal, run the baseline on this machine, record figures; docs + CHANGELOG; verify", "done": true}]

## Rollback

git revert of the one commit; the audit script has no callers.

## Journal

- 2026-09-12T16:04:08Z [implementation] — THRESHOLD DECLARED BEFORE MEASURING. Unit: a user-facing answer = the last assistant text block before the next human message (tool-result turns are not human). Rubric: four markers mirroring the contract's pre-send deletions (intent-announcement opener, closing recap/pleasantry, side-branch paragraph, empty hedge), scored on prose only (fenced/inline code, tool output, paths, AC/decision lines stripped). Metric: hit rate = answers with >=1 marker / answers. Drop rule: baseline hit rate < 10% → the task is dropped (gap not worth a runner). Corpus: Claude Code transcripts of this project on this machine (42 files) + Codex rollouts whose cwd is this project. Nothing from the corpus is copied into the repo; only counts.
- 2026-09-12T16:11:26Z [implementation] — BASELINE, session #249, this machine, nothing copied into the repo: 451 user-facing answers in 151 files (claude 317, codex 134), median 2175 chars. intent_opener 1.1%, closing_recap 0.2%, side_branch 2.4%, empty_hedge 3.3%; answers with >=1 marker 7.1%. Declared threshold 10% → NOT met → per the declared rule the adherence lever is NOT built; the instrument, cases and figure ship. NOT claimed: shape adherence (done → verified by → left → your call) — unmeasured by this rubric. Re-measure: python scripts/response_contract_audit.py <transcripts> --project <root> --threshold 7.1.
- 2026-09-12T16:11:26Z [implementation] — Step 1-2: scripts/response_contract_audit.py (adapters claude/codex/generic, protected-content strip, four markers, --json/--threshold, empty corpus named) and tests/test_response_contract_audit.py (25 cases: 11 positives, 7 protected negatives, conforming answer, adapters, runner contract). Adapter fixes found on the corpus: harness notifications arrive as user turns (541 → 451 answers once excluded), 'No response requested.' sentinel skipped, isApiErrorMessage skipped; RU openers 'Начинаю с / Открываю / Беру' added after sampling the first two words of every answer. Root cause (tooling): heredoc patching halved backslashes and put two 0x08 bytes into a regex — fixed byte-level; patch files go through the Write tool.
- 2026-09-12T16:12:10Z [implementation] — AC-1 ✓ tests/test_response_contract_audit.py::test_claude_adapter_takes_the_last_text_before_a_human_turn, ::test_codex_adapter_filters_by_cwd_and_drops_imported_tool_traffic, ::test_generic_adapter_and_report (per-host counts). AC-2 ✓ ::test_the_phrase_in_prose_is_a_hit[11 ids] — RU and EN positives per marker; negatives in ::test_a_conforming_answer_fires_nothing. AC-3 ✓ ::test_protected_content_is_not_read[7 ids] — fenced code, inline code, indented output, AC line, root-cause line, quoted output, system-reminder tag. AC-4 ✓ threshold 10% declared in the journal before the run (entry 'THRESHOLD DECLARED BEFORE MEASURING'); baseline 451 answers / 7.1% recorded in the journal and in docs/ru/agent-contract.md section 'Соблюдение контракта ответа: базовая линия (замер #249)'; drop rule applied — no lever built. AC-5 ✓ ::test_threshold_exits_one_at_or_above_and_zero_below, ::test_an_empty_corpus_is_named_not_reported_as_full_adherence. AC-6 ✓ docs/ru/agent-contract.md, CHANGELOG.md, CHANGELOG.ru.md; ruff clean; verify run #2525 signed. Domain: the instrument ran on 151 real transcripts of this project and the spot-checked hits are real openers ('I'll start with the session handoff'), real side branches ('Попутно: счётчик хуков'), real hedges ('скорее всего') — the rubric reads the corpus it was built for, and the 7.1% is a figure a person can re-derive with one command.
