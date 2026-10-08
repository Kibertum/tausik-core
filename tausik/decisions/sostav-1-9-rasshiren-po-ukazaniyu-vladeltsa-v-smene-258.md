---
slug: sostav-1-9-rasshiren-po-ukazaniyu-vladeltsa-v-smene-258
task: null
date: "2026-09-13"
edges: []
---

## Decision

Состав 1.9 расширен по указанию владельца в смене #258 историей release19-tracker-promises: GitLab #5 (штамп версии), #6 (три хранилища памяти в шаблоне), #14 (DYNAMIC-блок не пишется в версионируемый сиблинг: ручка claudemd.sibling_dynamic, умолчание как сейчас, усечённый блок без чужих знаний) и перенос hook-coverage из GitHub PR #5 с Co-Authored-By автора вместо merge 65 коммитов. GitLab #8, #11 и #10-патч-0004 остаются в 1.10 (#362/#366). Пересказ по протоколу #367. Устав: #360. Состав: agent-output-discipline, context-carries-over-between-sessions, guarantees-are-not-claude-only, verification-off-the-critical-path, the-loop-closes-outward, evidence-primitives, gates-declare-what-they-prevent, renar-contract-contour, test-evidence-not-test-volume, codex-first-class-19, release19-proof-integrity, release19-effective-context, knowledge-sheds-notion-and-its-hygiene, kb-docs, release19-clean-publication-and-onboarding, release19-tracker-promises

## Rationale

Владелец спросил, почему отложенное не делаем и почему PR #5 не мержим. Дешёвые тикеты и публичные обещания (тикет #14 потребителю, merge внешнему контрибьютору) дешевле исполнить до тега, чем извиняться после; PR #5 вырос в форк с подсистемой autoloop на 20 тысяч строк — переносится только hook-coverage, авторство сохраняется через Co-Authored-By. Остальное требует проектных решений, не рук.
