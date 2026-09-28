---
slug: our-conformance-claim-rests-on-a-mode-the-standard-removed
title: "Наша заявка RENAR-1 стоит на core-mode, которого в стандарте больше нет: §1.5.4 прямо запрещает её, замена (ADR-017) не принята"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: architect
stack: null
tier: substantial
call_budget: 70
defect_of: null
scope: null
scope_exclude: "../../standards/** (чужой корпус — не трогается ни байтом, доставка расхождений только тикетом, решение #290); схема БД (миграций нет)"
relevant_files:
  - "scripts/renar_conformance.py"
  - "scripts/renar_export.py"
  - "scripts/project_cli_renar.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
  - "renar/conformance.md"
  - "renar/adapts/adapt-renar-adoption.md"
scope_paths:
  - "scripts/renar_conformance.py"
  - "scripts/renar_export.py"
  - "scripts/project_cli_renar.py"
  - "renar/*"
  - "renar/**"
  - "tests/test_renar_conformance.py"
  - "tests/test_renar_export.py"
scope_tools: []
depends_on: []
completed_at: "2026-08-31T16:40:23Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО В #198 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-005. Самая тяжёлая находка смены: снята опора, на которой стоит ВСЯ наша заявка о соответствии, и снята она была больше двух месяцев назад.

ЧТО МЫ ОБЪЯВИЛИ. renar/adapts/adapt-renar-adoption.md стр.65: «TAUSIK is a solo project — there is no separate client». Стр.67: «Resolution: Declare core-mode explicitly (Decision #109: "say so, don't fake a client")». Решение #109 было честным: лучше объявить облегчённый режим, чем выдумать клиента.

ЧТО СТАЛО С ЭТИМ РЕЖИМОМ. ADR-005 (accepted) снял его. Цитата, стр.85: «§1.5.4 переписывается: internal product без external client → §1.5 negative scope без core-mode escape hatch». Стр.83: «Middle ground «internal product с одним лицом за обе стороны» — нарушение §5.5.3 ...; не подменяется core-mode». Правка ИСПОЛНЕНА: грep по всему нормативному корпусу (standard/, guide/, reference/) на core-mode / core_mode / mode: core даёт НОЛЬ вхождений.

ЧТО СТОИТ НА ЕГО МЕСТЕ. §1.5.4 стр.121: реализация «может локально применять подмножество практик RENAR ..., но не имеет права заявлять соответствие RENAR-N. Манифест либо не существует, либо явно декларирует «несоответствие»». Стр.123, негативный сценарий: «попытка объявить RENAR-N для internal product без независимого представителя клиента — несоответствующий». §5.5.3 стр.147: тот же сценарий «вне основной области применения».

При этом renar/conformance.md стр.44 продолжает печатать «Level: **RENAR-1**». Мы одновременно внутренний продукт без независимого клиента — по нашему же тексту — и заявитель уровня RENAR-N.

ЗАКОННОГО ВЫХОДА СЕГОДНЯ НЕТ, ПРОВЕРЕНО. Односторонняя приёмка разбирается в ADR-017, но его frontmatter стр.4 — `status: proposed`, в affects «ПРЕДЛОЖЕНИЕ — нормативные правки НЕ внесены», тикет #33 в состоянии «В работе». Ссылаться на неё как на основание нельзя.

ЧТО ДЕЛАТЬ — РЕШЕНИЕ ВЛАДЕЛЬЦА, НЕ АГЕНТА. Развилки три, и они не равноценны: (1) перестать заявлять уровень и печатать честное «несоответствие» по §1.5.4, сохранив практики локально; (2) найти независимого представителя клиента и выйти в §1.4.2; (3) дождаться ADR-017 и заявиться по односторонней приёмке, объявив нынешнее состояние временно несоответствующим. Молча оставить RENAR-1 нельзя ни в одном сценарии.

СВЯЗЬ С ОТПРАВЛЕННЫМ НАРУЖУ: тикет renar#47 (та же смена) сообщил корпусу факт «pre-adoption: false, level RENAR-1». По §1.5.4 мы не имеем права заявлять RENAR-N вовсе. Тикет требует поправки, и её содержание зависит от выбранной здесь развилки.

## Acceptance Criteria

РАЗВИЛКА ЗАКРЫТА ПУТЁМ 1: снять заявку уровня, объявить несоответствие по §1.5.4, практики сохранить локально. Пути 2 и 3 отвергнуты доказуемо (см. rationale решения). Ниже — что обязано стать правдой.

AC-1 (машина структурно НЕ СПОСОБНА напечатать RENAR-N, пока держится исключение §1.5.4): в scripts/renar_conformance.py перед лестницей уровней вычисляется ПРЕДУСЛОВИЕ ПРИМЕНИМОСТИ (§1.5 negative scope). Пока исключение §1.5.4 держится, вердикт возвращает level=None и НИ ОДНО состояние сигналов не даёт RENAR-N. Проверяется тестом, который перебирает ВСЕ сигналы = True и требует level is None.

AC-2 (объявление несоответствия в канонической форме стандарта): манифест из build_manifest() несёт явную декларацию несоответствия — sentinel replaced-by "<unknown-state>" (§13.8.2 шаг 2) и поле, называющее статью исключения §1.5.4. Поле level = null. Проверяется тестом на форму манифеста.

AC-3 (производный вид перестал печатать уровень): renar/conformance.md после перегенерации НЕ содержит "RENAR-1" ни во frontmatter (level:), ни в теле (Level:). Вместо уровня печатается декларация несоответствия со ссылкой на §1.5.4. Проверяется тестом на renar_export + грепом по файлу.

AC-4 (снятый механизм больше не выдаётся за действующее основание): в renar/adapts/adapt-renar-adoption.md резолюция "Declare core-mode explicitly" помечена отозванной с указанием ADR-005 и настоящего решения. Грep core-mode по renar/ даёт ТОЛЬКО исторические упоминания, каждое из которых явно помечено как снятое. Проверяется грепом.

AC-5 (журнал аудита §13.3.1 несёт запись о снятии заявки): создана запись о снятии недействительной заявки с указанием: что было заявлено, каким положением заявка запрещена, почему это СНЯТИЕ, а не downgrade по §13.8, и при каком условии возможен возврат (выход в §1.4.2). Машинерия §13.8.2 объявлена ЗАИМСТВОВАННОЙ как кодировка, а не исполненной как норма.

AC-6 (обещание, стоящее в чужом трекере, исполнено): в renar#47 отправлен результат развилки. Отправляется ПОСЛЕ того, как AC-1..AC-5 стали правдой в дереве — сообщаем состоявшийся факт, а не намерение (память #470).

AC-7 (регрессий нет): полная лента pytest зелёная, mypy OK, tausik verify зелёный. Ни один из существующих тестов на renar_conformance/renar_export не ослаблен и не удалён; изменение поведения покрыто НОВЫМИ тестами.

RED-PROOF НА КАЖДОЕ ИСПРАВЛЕННОЕ МЕСТО (память #449, #457): мутация отдельно на предусловие применимости (снять исключение -> уровень обязан вернуться, тест AC-1 обязан покраснеть), на sentinel (подменить значение -> тест AC-2 краснеет), на печать уровня (вернуть Level -> тест AC-3 краснеет). Якорь мутации в ОДНУ строку, count != 1 -> SETUP-FAIL.

## Plan

## Rollback

git revert одним коммитом. Изменения затрагивают ТОЛЬКО наши артефакты и наш код: scripts/renar_conformance.py, scripts/renar_export.py, renar/conformance.md, renar/adapts/adapt-renar-adoption.md, новые тесты, запись журнала аудита. Миграций схемы БД НЕТ — предусловие применимости вычисляется, а не хранится. Чужой корпус (../../standards/renar) не изменяется НИ БАЙТОМ; проверяется sha256 до/после. Единственное необратимое действие — комментарий в renar#47 (AC-6); он выполняется ПОСЛЕДНИМ, после того как остальное уже в дереве, и откатывается встречным комментарием, а не удалением.

## Journal

- 2026-08-31T16:07:21Z [planning] — [#198] ПОПРАВКА В КОРПУС ОТПРАВЛЕНА В ТОТ ЖЕ ДЕНЬ, ЧТО И ИСХОДНОЕ СООБЩЕНИЕ. Тикет renar#47, комментарий note_4852: https://[вычеркнуто: internal-host]/kibertum/clients/kibertum/standards/renar/-/work_items/47#note_4852 ЧТО ОТОЗВАНО И ЧТО ОСТАВЛЕНО, РАЗДЕЛЬНО. Дефект 1 (путь `.tausik-lib/` против `renar/`) оставлен в силе без изменений — он ни от чего из найденного не зависит. Дефект 2 (состояние) отозван В ЧАСТИ ФАКТА НА ЗАМЕНУ: «pre-adoption: false, level RENAR-1» предложен неверно не потому, что поле читается иначе, а потому, что права печатать уровень у нас по §1.5.4 нет. ТОЧНАЯ ФОРМУЛИРОВКА НА ЗАМЕНУ СОЗНАТЕЛЬНО НЕ ПРЕДЛОЖЕНА. Предлагать её, не закрыв развилку у себя, значило бы второй раз за день отправить наружу факт, который через час придётся отзывать. В комментарии сказано прямо: формулировка за владельцем корпуса, результат нашей развилки сообщим сюда же. ЧТО ЕЩЁ СКАЗАНО НАРУЖУ, ХОТЯ МОГЛИ БЫ ПРОМОЛЧАТЬ. Названа причина, по которой §3 вообще описал нашу заявку по устаревшим данным: §13.4.1 требует RENAR-CONFORMANCE.yaml в корне носителя, у нас его нет ни в дереве, ни в истории — читать автору ADR было нечего. Это снимает с корпуса половину вины и кладёт её туда, где она есть. ДЛЯ СЛЕДУЮЩЕЙ СМЕНЫ: при закрытии этой задачи ОБЯЗАТЕЛЬНО вернуться в #47 с результатом развилки. Тикет открыт, в нём стоит наше обещание, и невыполненное обещание в чужом трекере хуже, чем несделанная поправка.
- 2026-08-31T16:29:36Z [implementation] — [AC-1..AC-5 в дереве] Развилка закрыта путём 1 (решение #292), различение снятия и downgrade — #293. СДЕЛАНО: предусловие применимости SCOPE_EXCLUSION впереди лестницы уровней (renar_conformance.py); level=null + conformance-declaration + scope-exclusion + sentinel replaced-by в манифесте; производный вид печатает декларацию ВПЕРЕДИ строки уровня; CLI и status-строка перестали говорить pre-adoption на исключении; regulatory-finding в ADAPT об отзыве резолюции core-mode; баннер рендерера ПЕРЕД телом ADAPT с regulatory-находкой. ЗАМЕР ЖИВЬЁМ, ГОДИТСЯ ДЛЯ ЗАДАЧИ bootstrap-drift-gate-off-source-edits-never-reach-the-cli: правка в scripts/ НЕ доехала до CLI — tausik renar export продолжал печатать RENAR-1, потому что лаунчер берёт .claude/scripts. Гейт УВИДЕЛ расхождение: doctor WARN «15 deployed file(s) differ», gates status [ON] bootstrap_drift (block) -> task-done. Вопрос задачи «ловит ли гейт правку, не доехавшую до исполняемой копии» отвечен ДА, замер снят не чтением. ОТКЛОНЕНИЕ ОТ AC-4 БУКВАЛЬНО, ОБЪЯВЛЯЮ: пометить строки 42/65/67 в МЕСТЕ чтения нельзя — тело ADAPT append-only (V1) и производно от БД, команды update у находок нет. Вместо приписки к случаю сделано ОБЩЕЕ правило рендерера: любой ADAPT с regulatory-находкой получает баннер ДО тела. Это сильнее приписки — работает на все будущие случаи, а не на этот.
- 2026-08-31T16:37:55Z [implementation] — [AC-6 ИСПОЛНЕН, AC-7 ЗЕЛЁНЫЙ] Обещание в чужом трекере закрыто: renar#47 комментарий note_4855, прочитан обратно (комментариев в тикете стало 2). Сообщён СОСТОЯВШИЙСЯ факт, не намерение — отправлено ПОСЛЕ зелёной ленты. ЛЕНТА: 7557 passed, 24 skipped, 0 failed (было 7547 — ровно +10 моих). mypy: Success, no issues in 3 files. КРАСНЫЕ КОНТРОЛИ 4/4 УБИТЫ, RESTORE-FAIL 0, SETUP-FAIL 0: M1 снятие предусловия, M2 подмена sentinel, M3 снятие декларации, M4 снятие баннера. M2 СНАЧАЛА ВЫЖИЛА, И ЭТО БЫЛ НАСТОЯЩИЙ ДЕФЕКТ ТЕСТА: утверждение сверяло поле манифеста с той же константой UNKNOWN_STATE_SENTINEL, которая его и порождает — тавтология, переживающая любое изменение константы. Заменено на дословный литерал "<unknown-state>", который называет §13.8.2. Мутация нашла дыру в проверке, а не в коде — ровно то, ради чего она гоняется. ЧУЖОЙ КОРПУС НЕ ТРОНУТ, ДОКАЗАНО ВРЕМЕНЕМ: git status по standard/ guide/ reference/ adr/ core/ audit/ — пусто. Все 313 изменённых файлов в ../../standards/renar лежат под их СОБСТВЕННЫМ .claude/ развёртыванием и CLAUDE.md; самая свежая правка во всём корпусе — 2026-08-20 21:10 UTC, за одиннадцать дней до старта этой сессии (16:14 UTC 31.08). Поправка к передаче #198: каталог ../../standards НЕ является рабочим деревом, а ../../standards/renar — ЯВЛЯЕТСЯ, git status там работает. ПОБОЧНАЯ НАХОДКА, НЕ МОЯ ПРАВКА: экспорт вынес renar/specs/sec-config-trust-tiers.md и renar/specs/team-state-in-git-format.md как НОВЫЕ untracked — производное дерево отставало от БД на два SPEC, то есть renar/ в git был несвежим ещё до этой смены. Поставлены под git.
- 2026-08-31T16:38:53Z [implementation] — AC-1 (машина структурно не способна напечатать RENAR-N, пока держится исключение §1.5.4): ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_every_signal_true_still_yields_no_level ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_lifting_the_exclusion_restores_the_ladder ✓ verification_run #1912 AC-2 (объявление несоответствия в канонической форме: sentinel §13.8.2, level=null, статья исключения): ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_manifest_declares_non_conformance ✓ verification_run #1912 AC-3 (производный вид перестал печатать уровень, декларация стоит ВЫШЕ строки уровня): ✓ tests/test_renar_export.py::TestDerivedViewDeclaresNonConformance::test_no_renar_n_level_in_frontmatter_or_body ✓ tests/test_renar_export.py::TestDerivedViewDeclaresNonConformance::test_declaration_precedes_the_level_line ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_status_line_never_says_pre_adoption ✓ verification_run #1912 AC-4 (снятый механизм не выдаётся за действующее основание): ✓ tests/test_renar_export.py::TestRegulatoryFindingBanner::test_banner_precedes_the_findings_it_qualifies ✓ tests/test_renar_export.py::TestRegulatoryFindingBanner::test_no_banner_without_a_regulatory_finding ✓ verification_run #1912 AC-5 (журнал аудита несёт запись о снятии заявки): ✓ verification_run #1912 AC-6 (обещание в чужом трекере исполнено): ✓ verification_run #1912 AC-7 (регрессий нет): ✓ verification_run #1912 ГДЕ ДОКАЗАТЕЛЬСТВО НЕ ТЕСТ — ЧЕМ ИМЕННО ОНО ЯВЛЯЕТСЯ. AC-5: решения #292 (снятие заявки, выбор пути) и #293 (снятие — не downgrade по §13.8; sentinel заимствован как кодировка). Записаны в БД, а не файлом в renar/: renar/ производно, write_tree сверяет удаления и стёр бы всякий *.md вне проекции (renar_export.py:311-328). Носитель — sqlite с V1 (hash-chain v34) и V6. AC-6: renar#47 комментарий note_4855, прочитан обратно через glab issue view — в тикете стало 2 комментария. Отправлен ПОСЛЕ зелёной ленты: сообщён состоявшийся факт, не намерение. AC-7: полная лента 7557 passed, 24 skipped, 0 failed (было 7547 — ровно +10 моих). mypy Success по трём изменённым файлам. Ни один существующий тест не удалён и не ослаблен: семь тестов лестницы перенацелены на фикстуру in_scope, потому что они проверяют ЗНАЧЕНИЕ уровня, а этот вопрос возникает только внутри области применимости; ПРАВО проверяется отдельным классом. КРАСНЫЕ КОНТРОЛИ 4/4 УБИТЫ (RESTORE-FAIL 0, SETUP-FAIL 0). M2 выжила с первого раза и вскрыла тавтологию в моём же тесте: поле сверялось с порождающей его константой. Заменено на литерал "<unknown-state>" из §13.8.2. ЧУЖОЙ КОРПУС НЕ ТРОНУТ: git status по standard/ guide/ reference/ adr/ core/ audit/ пуст; самая свежая правка во всём ../../standards/renar — 2026-08-20, за 11 дней до старта сессии.
- 2026-08-31T16:40:19Z [implementation] — AC-1 (машина структурно не способна напечатать RENAR-N, пока держится исключение §1.5.4): ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_every_signal_true_still_yields_no_level ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_lifting_the_exclusion_restores_the_ladder ✓ verification_run #1914 AC-2 (объявление несоответствия в канонической форме: sentinel §13.8.2, level=null, статья исключения): ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_manifest_declares_non_conformance ✓ verification_run #1914 AC-3 (производный вид перестал печатать уровень, декларация стоит ВЫШЕ строки уровня): ✓ tests/test_renar_export.py::TestDerivedViewDeclaresNonConformance::test_no_renar_n_level_in_frontmatter_or_body ✓ tests/test_renar_export.py::TestDerivedViewDeclaresNonConformance::test_declaration_precedes_the_level_line ✓ tests/test_renar_conformance.py::TestScopeApplicability::test_status_line_never_says_pre_adoption ✓ verification_run #1914 AC-4 (снятый механизм не выдаётся за действующее основание): ✓ tests/test_renar_export.py::TestRegulatoryFindingBanner::test_banner_precedes_the_findings_it_qualifies ✓ tests/test_renar_export.py::TestRegulatoryFindingBanner::test_no_banner_without_a_regulatory_finding ✓ verification_run #1914 AC-5 (журнал аудита несёт запись о снятии заявки): ✓ verification_run #1914 AC-6 (обещание в чужом трекере исполнено): ✓ verification_run #1914 AC-7 (регрессий нет): ✓ verification_run #1914 ГДЕ ДОКАЗАТЕЛЬСТВО НЕ ТЕСТ — ЧЕМ ИМЕННО ОНО ЯВЛЯЕТСЯ. AC-5: решения #292 (снятие заявки, выбор пути) и #293 (снятие — не downgrade по §13.8; sentinel заимствован как кодировка). Записаны в БД, а не файлом в renar/: renar/ производно, write_tree сверяет удаления и стёр бы всякий *.md вне проекции (renar_export.py:311-328). Носитель — sqlite с V1 (hash-chain v34) и V6. AC-6: renar#47 комментарий note_4855, прочитан обратно через glab issue view — в тикете стало 2 комментария. Отправлен ПОСЛЕ зелёной ленты: сообщён состоявшийся факт, не намерение. AC-7: полная лента 7557 passed, 24 skipped, 0 failed (было 7547 — ровно +10 моих). mypy Success по трём изменённым файлам. Ни один существующий тест не удалён и не ослаблен: семь тестов лестницы перенацелены на фикстуру in_scope, потому что они проверяют ЗНАЧЕНИЕ уровня, а этот вопрос возникает только внутри области применимости; ПРАВО проверяется отдельным классом. КРАСНЫЕ КОНТРОЛИ 4/4 УБИТЫ (RESTORE-FAIL 0, SETUP-FAIL 0). M2 выжила с первого раза и вскрыла тавтологию в моём же тесте: поле сверялось с порождающей его константой. Заменено на литерал "<unknown-state>" из §13.8.2. ЧУЖОЙ КОРПУС НЕ ТРОНУТ: git status по standard/ guide/ reference/ adr/ core/ audit/ пуст; самая свежая правка во всём ../../standards/renar — 2026-08-20, за 11 дней до старта сессии.
