---
slug: scoped-verify-ne-vidit-testy-svyazannye-s-pravkoy-cherez-bd
title: "Scoped verify не видит тесты, связанные с правкой через БД (content_ref SPEC → docs), — полный прогон перед КАЖДЫМ пушем, а не в конце смены"
type: gotcha
tags:
  - ci
  - docs
  - spec
  - verify
task: guarded-key-added-without-its-spec-entry
edges: []
---

#213: добавил Guard в config_trust.GUARDS, scoped verify (23 файла по импортам) прошёл, задача закрыта и запушена (ca6ca34) — а полный прогон позже показал красный tests/test_spec_completeness.py: аудит полноты сверяет тело SPEC sec-config-trust-tiers (docs/ru/config-trust-tiers.md по content_ref из БД) с живым перечнем GUARDS (enumerator config_trust_guarded_keys). Связь GUARDS → SPEC идёт через строку в БД, а не через импорт, и резолвер scoped-набора её не видит. CI это тоже не поймал: аудит читает живую БД, которой в CI нет (пайплайн 6779 зелёный при красном локальном). Правило: (1) полный прогон ленты перед каждым пушем; (2) правя перечень, у которого есть SPEC с enumerator (tausik/spec_coverage.json), правь тело SPEC в том же коммите; (3) для docs-правки в relevant-files объявляй сам охранный тест — иначе scoped verify говорит «No tests mapped».
