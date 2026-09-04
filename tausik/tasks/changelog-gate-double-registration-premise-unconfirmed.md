---
slug: changelog-gate-double-registration-premise-unconfirmed
title: "Гейт changelog зарегистрирован дважды: премиса из передачи #209 моим замером НЕ подтверждается"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - ".tausik/config.json"
scope_paths:
  - ".tausik/config.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-04T21:36:51Z"
---

## Goal

ПРЕМИСА ИЗ ПЕРЕДАЧИ #209: «Дубль changelog_gate в .tausik/config.json».
МОЙ ЗАМЕР В #210 ЕЁ НЕ ПОДТВЕРДИЛ. Обход всего дерева config.json по ключам, содержащим changelog, дал РОВНО ОДНО вхождение: /task_done/changelog_gate (строка 67). Grep по файлу — тоже одно.
ЗАДАЧА НАЧИНАЕТСЯ С УТОЧНЕНИЯ, А НЕ С ПОЧИНКИ. Развести замером три объяснения: (а) дубль был и устранён между #209 и #210 — тогда закрыть с записью и УБРАТЬ ПУНКТ ИЗ ПЕРЕДАЧ; (б) дубль не в config.json, а в РЕЕСТРЕ гейтов — регистрация размазана по четырём механизмам, о чём заведена gate-registry-single-source, и тогда это её предмет, а не отдельная задача; (в) мой замер смотрел не туда, и надо смотреть на слой конфигурации целиком (project/user/managed), а не на один файл.
ЗАВЕДЕНО ИМЕННО ТАК, А НЕ ВЫБРОШЕНО: пункт кочует по передачам с #209 и будет кочевать дальше, а невыясненный пункт дороже закрытого. Но ЧИНИТЬ НЕЧЕГО, пока субъект не предъявлен: гейт без субъекта есть тот самый вырожденный контроль, который мы в этом релизе и вычищаем.

## Acceptance Criteria

AC-1: три объяснения из цели разведены замером, и в журнале задачи назван носитель дубля с путями и строками: обход слоя конфигурации ЦЕЛИКОМ (gitignored .tausik/config.json, закоммиченный tausik/policy.json, пользовательский ~/.tausik/config.json) плюс реестр gate_registry.py и tausik/gates.json.
AC-2: если дубль есть — сказано, чем он является по решению #287 (остаток после переезда ужесточений) и вреден ли он при композиции compose_project_tier; если его нет — премиса снята.
AC-3: исход записан: либо лишний носитель убран с замером «gates status печатает [ON] changelog до и после», либо задача закрыта с записью и пункт снят из передач. Правок кода нет; если нужна охрана от повторного расползания ключа по двум носителям — это предмет gate-registry-single-source, и туда ставится ссылка, а не новая задача.
AC-4 (negative): ошибка при удалении лишнего носителя — если после удаления ключа из .tausik/config.json `gates status` печатает [OFF] changelog или блокирующий гейт исчезает из списка, удаление ОТКАТЫВАЕТСЯ дословно и в журнале записывается, что композиция не восстанавливает ужесточение из policy.json; задача тогда НЕ закрывается, а переводится в дефект compose_project_tier.

## Plan

## Rollback

Вернуть блок task_done.changelog_gate в .tausik/config.json дословно (enabled true, files CHANGELOG.md и CHANGELOG.ru.md); файл gitignored, машинно-локальный, git не участвует.

## Journal

- 2026-09-04T21:36:31Z [implementation] — ИНВЕНТАРЬ СЛОЯ КОНФИГУРАЦИИ ЦЕЛИКОМ. (1) .tausik/config.json (gitignored, машинно-локальный): task_done.changelog_gate, строки 67–73, enabled true, files [CHANGELOG.md, CHANGELOG.ru.md]. (2) tausik/policy.json (закоммичен): task_done.changelog_gate, строка 10, те же значения плюс _reason; появился в коммите de9e027 от 2026-09-01 («свежий клон не был зелёным, а один блокирующий гейт в нём был выключен»). (3) ~/.tausik/config.json (пользовательский тир): ключа НЕТ (grep exit 1). (4) scripts/gate_registry.py: ОДНА GateSpec name=changelog, enabled по умолчанию False, enabled_resolver gate_changelog:changelog_gate_enabled. (5) tausik/gates.json:79 — классификация гейта (test/violation), не регистрация включения. ИТОГ: объяснение (в) — мой замер #210 смотрел в один файл, а ключ живёт в ДВУХ файлах одного проектного тира. Происхождение: de9e027 перевёз ужесточение в policy.json по решению #287, но остаток в config.json не убрал; пункт «дубль changelog_gate в .tausik/config.json» появился в передаче #206 ровно после этого. ВРЕД: нет — compose_project_tier делает deep_merge(policy, local), значения совпадают; при расхождении на охраняемом ключе побеждает строгий (restore_tightenings). ДЕЙСТВИЕ: остаток из .tausik/config.json убран, заметка _moved_to_policy дополнена (changelog_gate, de9e027, #213). ЗАМЕР ДО/ПОСЛЕ: `gates status` печатает «[ON] changelog (block) -> task-done» и до, и после — композиция восстанавливает ужесточение из policy.json; JSON валиден; doctor — единственный прежний WARN (семь внеисторийных задач, было восемь: powershell-channel закрыта). AC-4 не сработал, откат не потребовался; резервная копия файла лежала в scratchpad. Охрана от повторного расползания ключа по двум носителям — предмет gate-registry-single-source, отдельной задачи не завожу.
- 2026-09-04T21:36:51Z [implementation] — AC-1: ✓ инвентарь пяти носителей с путями и строками в журнале задачи (config.json:67, policy.json:10, ~/.tausik/config.json — нет, gate_registry.py — одна GateSpec, gates.json:79 — классификация). AC-2: ✓ дубль есть, объяснение (в): остаток после переезда de9e027 по решению #287; при композиции compose_project_tier безвреден (deep_merge, одинаковые значения, на охраняемом ключе побеждает строгий). AC-3: ✓ остаток убран из gitignored .tausik/config.json, заметка _moved_to_policy дополнена; замер gates status до и после — [ON] changelog (block) в обоих; пункт снимается из передач; охрана расползания — предмет gate-registry-single-source. AC-4 (negative): ✓ не сработал — после удаления гейт остался [ON], откат не потребовался; резервная копия в scratchpad. Domain: слой конфигурации проектного тира (config_policy, config_trust), вне нормы RENAR.
- 2026-09-04T21:47:16Z [done] — ПОПРАВКА ПО ВНЕШНЕМУ L3 #38 (после закрытия). Фраза «при расхождении на охраняемом ключе побеждает строгий (restore_tightenings)» к этому ключу НЕ ПРИМЕНИМА: GUARDS в config_trust.py не содержит task_done.changelog_gate.enabled. Проверено прогоном: compose_project_tier(policy enabled=True, local enabled=False) → False молча; контроль gates.changelog.enabled при тех же входах → True. Дубль был безвреден потому, что ЗНАЧЕНИЯ СОВПАДАЛИ, а не потому, что механизм защищал расхождение. Удаление остатка из config.json остаётся верным действием (оно убрало носитель, способный молча выключить блокирующий гейт на этой машине). Незащищённый выключатель заведён задачей changelog-gate-switch-is-outside-config-trust-guards (внеисторийная).
