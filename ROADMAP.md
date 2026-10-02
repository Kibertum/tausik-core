# Дорожная карта TAUSIK 1.11

<!-- ПОРОЖДЁННЫЙ ФАЙЛ. Руками не редактируется: перевыпуск —
     `tausik doc roadmap`, проверка свежести — `tausik doc roadmap --check`.
     Состав релиза читается из решений владельца, счётчики — из живой БД. -->

## Вопрос версии

Задано решением #410 от 2026-10-01:

> 1.11 APPROVED by owner, 2026-10-01: urgent measured economy without quality loss. Main hosts: Claude Code, Kilo/GLM, Codex; Codex-first savings. Optional Cursor/OpenRouter: +25 calls maximum, not a release blocker.
>
> Composition: release111-measurement, release111-context-and-workflow, release111-release-proof
>
> 13 product tasks. Minimal contract and native Codex baseline first, then context/workflow savings without waiting for GLM; all three hosts pass live checks before release. Preserve QG-0/QG-2. 30% is a fixed-model token target, not promised quota savings. Approved version map/report: docs/ru/research/release-111-economy-plan-2026-10-01.md. Apply its GitHub roadmap changes; 1.12/1.13 remain candidates, 2.0 global install. Admin work outside product scope. GitLab #10 messages/closure and git commit/push not authorized. #409 stays in force.

## Что входит в 1.11

Состав — из последнего решения, ОБЪЯВИВШЕГО его строкой «Состав:»: #411 от 2026-10-01; решения после него, которые лишь упоминают истории, состав не меняют. Счётчики сняты с живой базы в момент перевыпуска этого файла.

| История | Статус | Осталось | Заблокировано | Закрыто |
|---|---|---|---|---|
| `release111-measurement`<br>1.11: real usage, host identity and provider adapters | done | 0 | 0 | 4 |
| `release111-context-and-workflow`<br>1.11: bounded context and fewer model round trips | done | 0 | 0 | 8 |
| `release111-release-proof`<br>1.11: independent quality and economy proof | done | 0 | 0 | 7 |
| **Итого** | | **0** | **0** | **19** |

## Что в релиз НЕ входит

Истории эпиков (release-111-economy-draft), которых решение о составе не называет.

**Открытые — отложенная цена.** Они не отменены — они не в этой версии, и их остаток здесь для того, чтобы граница релиза была видна вместе с ценой, которую она отложила.

| История | Статус | Осталось |
|---|---|---|
| `release111-economy-hardening` | active | 2 |

**Закрытые, составом не названные.** Их работа в дереве релиза, но обещанием релиза она не объявлена; отложенной цены у них нет.

| История | Закрыто |
|---|---|
| `release111-administration` | 2 |

## Траектория объёма

Решение #411 траекторию не записало — не «ноль точек», а не записало. Ряд восстанавливается по журналу решений об объёме.

## TAUSIK-roadmap.pdf — снимок, который сознательно не переиздаётся

PDF собран 2026-08-12 и на стр. 4 объявляет вопросом 1.11 «Работает ли у чужих?». Решение о переопределении версии принято позже и этот вопрос с версии сняло, так что снимок разошёлся с релизом по существу, а не по формулировке.

Снимок НЕ переиздаётся и НЕ удаляется: он — датированная запись того, чем релиз считался в момент сборки, и переписать её значило бы стереть историю решения. Под git он не ставится (правило в `.gitignore`) — бинарник со своей копией тех же утверждений есть второе место, где им расходиться, и ничего за ним не следит.

Действующая карта — этот файл. Он порождается из живой базы, и тест перегенерирует его при каждом прогоне: разойтись с состоянием незаметно, как разошёлся PDF, он не может.
