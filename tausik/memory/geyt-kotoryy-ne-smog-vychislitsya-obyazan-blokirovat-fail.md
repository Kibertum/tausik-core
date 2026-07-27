---
slug: geyt-kotoryy-ne-smog-vychislitsya-obyazan-blokirovat-fail
title: "Гейт, который не смог вычислиться, ОБЯЗАН блокировать (fail-closed), а не молчать"
type: convention
tags: []
task: l26-config-trust-tiers
edges: []
---

Найдено adversarial-ревью в сессии #112. service_gates._enforce_verify_first ловил любую ошибку загрузки конфига в bare except и продолжал с `verify_gates = []`. Это НЕОТЛИЧИМО от «в этом проекте не настроено ни одного verify-гейта», поэтому одна битая запись в объекте gates пропускала весь Verify-First Contract молча — без записи в задачу, без лога, а `tausik doctor` при этом рапортовал чистый конфиг.

Правило: пустой результат и ошибка вычисления — РАЗНЫЕ состояния, и путать их в защитном коде нельзя. «Гейтов не настроено» → можно продолжать. «Не смог определить, какие гейты применять» → блокировать с внятной remediation. CLAUDE.md заявляет fail-closed («a gate that can't evaluate blocks rather than waves the task through») — это был прямой разрыв между заявленным и фактическим.

Сопутствующее правило проверки типов: `cfg.get("ключ", {})` возвращает None, когда ключ ПРИСУТСТВУЕТ и явно равен null — дефолт не применяется. Проверяй тип ЗНАЧЕНИЯ, а не тип контейнера: `v = cfg.get("k"); v = v if isinstance(v, dict) else {}`. Паттерн `cfg.get("k", {}) if isinstance(cfg, dict) else {}` проверяет не то и роняет AttributeError.

И третье: проверка здоровья обязана вычислять то же, что вычисляет продакшн-путь. doctor считал len(DEFAULT_GATES) — счётчик, который не может упасть, — поэтому не ловил этот класс дефекта в принципе. Теперь резолвит реальные гейты, ошибка = FAIL.</content>
<parameter name="tags">["gates", "fail-closed", "doctor", "type-confusion", "security"]
