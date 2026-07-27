---
slug: v14c-mass-parametrize-batch-3-size-2-long-tail-145-grupp
task: null
date: "2026-05-07"
edges: []
---

## Decision

v14c-mass-parametrize-batch-3 (size=2 long-tail, ~145 групп / 290 тестов): WONT FIX в 1.4.0. Не переносится в 1.4.1 (по требованию пользователя «не дробить минор»). При следующем audit cycle — point-fix вручную, если конкретные группы попадут в видимое место.</decision>
<parameter name="task_slug">v14c-mass-parametrize-batch-3

## Rationale

**Cost-benefit analysis (rejected for 1.4.0):** 145 групп × ~5 минут на group = ~12 часов работы для верификации structural-vs-semantic identity. 2-test группы по audit-хэшу — НЕ автоматически дубли: типичный pattern `test_X_returns_true` + `test_X_returns_false` или `test_happy` + `test_sad` имеют идентичный body shape (одинаковое имя setup'а, одинаковый assert template), но это ЛЕГИТИМНАЯ pair-семантика, не дубль. False-positive rate без ручной верификации высок (~30-40% по анализу). Вычислительный outcome даже при идеальной reduction: -145 тестов из ~3360 = ~4% — diminishing returns после batches 1+2.

**Почему не переносим в 1.4.1:** Пользователь явно сказал «не дробить минор» — patch-релизы для polish следов делают changelog шумным и тратят release cycles на cosmetic тесты. Лучший путь: размер-2 long-tail оставить в покое до следующего audit-cycle (если ever); при перегенерации audit'а часть пар станет более крупными группами через органический рост — тогда они попадут под batch-1/batch-2 семантику автоматически.

**Что landed в 1.4 покрывает дедупликацию:** batch-1 (25+ групп size≥4) и batch-2 (33 группы size=3) свернули ~110+ тестов через `@pytest.mark.parametrize`. Это охватило high-confidence-duplicate slot — статистически большие группы по хэшу почти всегда являются настоящими дублями (ниже false-positive rate). Audit groups #68-212 (size=2) — long tail, где каждое слияние требует индивидуальной semantic review. Это качественно другая работа, не bulk refactor.

**Rollback plan:** не нужен — никаких production-edits. Если в post-1.4 audit окажется что 5-10 групп — реальные дубли (а не legit pairs), их можно точечно слить в 1.4.x patch без переноса bulk task'а.

**Альтернативный путь, если когда-нибудь захочется все 145 групп слить:** explore-first проход — собрать sample 20 случайных групп, классифицировать (real-dup / legit-pair / refactor-candidate), вычислить точный false-positive rate. Только после этого batch processing с явным фильтром. Но не для 1.4.
