---
slug: zayavka-renar-1-snyata-tausik-pechataet-nesootvetstvie-po-1
title: "Заявка RENAR-1 снята: TAUSIK печатает несоответствие по §1.5.4, право держит машина"
type: context
tags:
  - conformance
  - decisions-292
  - decisions-293
  - renar
task: our-conformance-claim-rests-on-a-mode-the-standard-removed
edges:
  - relation: caused_by
    target_type: memory
    target: soobschaya-naruzhu-fakt-o-sebe-proveryay-pravo-ego
  - relation: relates_to
    target_type: decision
    target: zayavka-renar-1-snimaetsya-tausik-internal-product-bez
---

СОСТОЯНИЕ ПОСЛЕ #199: TAUSIK НЕ ЗАЯВЛЯЕТ уровень RENAR. renar/conformance.md печатает conformance-declaration: non-conformant, level: null, scope-exclusion §1.5.4. Решения #292 (снятие, выбор пути 1 из трёх) и #293 (снятие — НЕ downgrade по §13.8; sentinel <unknown-state> заимствован как кодировка, потому что схема §13.4.2 представления для «уровень не удерживается» не предлагает).
МАШИНА ТЕПЕРЬ ДЕРЖИТ ПРАВО, А НЕ ПАМЯТЬ АГЕНТА: renar_conformance.SCOPE_EXCLUSION вычисляется ВПЕРЕДИ лестницы уровней; пока держится, никакое состояние сигналов §12.9 не даёт RENAR-N. Красный контроль: все сигналы True -> level всё равно None.
УСЛОВИЕ ВОЗВРАТА, ЕДИНСТВЕННОЕ: появление ACTZ, подписанного ДВУМЯ независимыми лицами (§5.5.3) -> §1.5.4 сам маршрутизирует в §1.4.2. Тогда SCOPE_EXCLUSION ставится в None, и лестница оживает. Иных способов снять исключение НЕТ — §13.9.2 запрещает заявлять уровень выше фактического, а уровень вне §1.5 стандартом не признаётся вовсе.
НАРУЖУ СООБЩЕНО: renar#47 комментарий note_4855 (31.08.2026). Обещание, стоявшее в тикете с #198, закрыто.
ЧТО ЭТО НЕ ОТМЕНЯЕТ: практики RENAR остаются в силе целиком — §1.5.4 разрешает применять подмножество локально. Обязанности по ADR-023 и прочим принятым ADR не сняты. Ушло ТОЛЬКО заявление уровня.
