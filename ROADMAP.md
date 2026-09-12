# Дорожная карта TAUSIK 1.9

<!-- ПОРОЖДЁННЫЙ ФАЙЛ. Руками не редактируется: перевыпуск —
     `tausik doc roadmap`, проверка свежести — `tausik doc roadmap --check`.
     Состав релиза читается из решений владельца, счётчики — из живой БД. -->

## Вопрос версии

Задано решением #360 от 2026-09-10:

> 1.9 scope is restated and supersedes decision #337: agent-output-discipline, context-carries-over-between-sessions, guarantees-are-not-claude-only, verification-off-the-critical-path, the-loop-closes-outward, evidence-primitives, gates-declare-what-they-prevent, renar-contract-contour, test-evidence-not-test-volume, and codex-first-class-19 are the release stories. Codex support is a release promise only after a live acceptance run proves MCP registration, deployed skills, named agents, and native enforcement hooks; the unrelated qwen-hooks-are-a-second-copy-of-the-declaration remains outside 1.9.

## Что входит в 1.9

Состав — из последнего решения, называющего истории релиза: #363 от 2026-09-12. Счётчики сняты с живой базы в момент перевыпуска этого файла.

| История | Статус | Осталось | Заблокировано | Закрыто |
|---|---|---|---|---|
| `release19-proof-integrity`<br>1.9: квитанция и hard-гарантии не могут лгать | active | 2 | 1 | 18 |
| `kb-docs`<br>Роевое комплексное обновление документации | done | 0 | 0 | 1 |
| `release19-effective-context`<br>1.9: эффективный контекст и измеренная дисциплина ответа | active | 5 | 1 | 5 |
| **Итого** | | **7** | **2** | **24** |

## Что в релиз НЕ входит

Истории эпика (release-19-agent-effectiveness, release-19-renar-conformance, shared-knowledge), которых решение о составе не называет. Они не отменены — они не в этой версии, и их счётчики здесь для того, чтобы граница релиза была видна вместе с ценой, которую она отложила.

| История | Статус | Осталось |
|---|---|---|
| `codex-first-class-19` | active | 1 |
| `codex-is-a-first-class-host` | done | 0 |
| `context-carries-over-between-sessions` | done | 0 |
| `evidence-and-hygiene-debt-paid-in-19` | done | 0 |
| `evidence-is-durable` | done | 0 |
| `evidence-is-substance-not-keywords` | done | 0 |
| `evidence-primitives` | done | 0 |
| `external-proof-and-open-axes` | done | 0 |
| `gates-declare-what-they-prevent` | done | 0 |
| `github-primary-gitlab-mirror` | done | 0 |
| `guarantees-are-not-claude-only` | done | 0 |
| `kb-git-sync` | done | 0 |
| `kb-global` | done | 0 |
| `kb-identity` | done | 0 |
| `kb-notion` | done | 0 |
| `km-knowledge-layer` | done | 0 |
| `knowledge-records-what-failed-19` | done | 0 |
| `knowledge-sheds-notion-and-its-hygiene` | done | 0 |
| `memory-retrieves-by-relevance` | done | 0 |
| `obligations-to-people-are-settled` | done | 0 |
| `parallel-work-runs-without-collisions` | done | 0 |
| `proof-and-positioning-outward` | done | 0 |
| `renar-contract-contour` | done | 0 |
| `renar-debt-implemented-wrong` | done | 0 |
| `standards-drift-detection` | done | 0 |
| `surfaces-do-not-diverge` | done | 0 |
| `test-evidence-not-test-volume` | done | 0 |
| `the-loop-closes-outward` | done | 0 |
| `verification-off-the-critical-path` | done | 0 |

## Траектория объёма

Решение #363 траекторию не записало — не «ноль точек», а не записало. Ряд восстанавливается по журналу решений об объёме.

## TAUSIK-roadmap.pdf — снимок, который сознательно не переиздаётся

PDF собран 2026-08-12 и на стр. 4 объявляет вопросом 1.9 «Работает ли у чужих?». Решение о переопределении версии принято позже и этот вопрос с версии сняло, так что снимок разошёлся с релизом по существу, а не по формулировке.

Снимок НЕ переиздаётся и НЕ удаляется: он — датированная запись того, чем релиз считался в момент сборки, и переписать её значило бы стереть историю решения. Под git он не ставится (правило в `.gitignore`) — бинарник со своей копией тех же утверждений есть второе место, где им расходиться, и ничего за ним не следит.

Действующая карта — этот файл. Он порождается из живой базы, и тест перегенерирует его при каждом прогоне: разойтись с состоянием незаметно, как разошёлся PDF, он не может.
