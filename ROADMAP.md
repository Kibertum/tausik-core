# Дорожная карта TAUSIK 1.9

<!-- ПОРОЖДЁННЫЙ ФАЙЛ. Руками не редактируется: перевыпуск —
     `tausik doc roadmap`, проверка свежести — `tausik doc roadmap --check`.
     Состав релиза читается из решений владельца, счётчики — из живой БД. -->

## Вопрос версии

Задано решением #360 от 2026-09-10:

> 1.9 scope is restated and supersedes decision #337: agent-output-discipline, context-carries-over-between-sessions, guarantees-are-not-claude-only, verification-off-the-critical-path, the-loop-closes-outward, evidence-primitives, gates-declare-what-they-prevent, renar-contract-contour, test-evidence-not-test-volume, and codex-first-class-19 are the release stories. Codex support is a release promise only after a live acceptance run proves MCP registration, deployed skills, named agents, and native enforcement hooks; the unrelated qwen-hooks-are-a-second-copy-of-the-declaration remains outside 1.9.

## Что входит в 1.9

Состав — из последнего решения, ОБЪЯВИВШЕГО его строкой «Состав:»: #370 от 2026-09-13; решения после него, которые лишь упоминают истории, состав не меняют. Счётчики сняты с живой базы в момент перевыпуска этого файла.

| История | Статус | Осталось | Заблокировано | Закрыто |
|---|---|---|---|---|
| `agent-output-discipline`<br>Дисциплина ответа агента: форма, крышки вывода и измеренная цена инъекции | done | 0 | 0 | 10 |
| `context-carries-over-between-sessions`<br>Контекст переживает границу сессии: ядро памяти, релевантное извлечение, инструктированная компакция, учение с холодным стартом | done | 0 | 0 | 3 |
| `guarantees-are-not-claude-only`<br>Гарантии кроссмодельны или объявлены отсутствующими: хост без механизма не имеет права выглядеть как хост с механизмом | done | 0 | 0 | 7 |
| `verification-off-the-critical-path`<br>A. Проверка уходит с критического пути: CI на рабочей ветке, лента параллельна, ничего не исключено молча | done | 0 | 0 | 17 |
| `the-loop-closes-outward`<br>D. Петля замыкается наружу: связь задача-тикет и заметки к релизу | done | 0 | 0 | 4 |
| `evidence-primitives`<br>Примитивы доказательства: один вердикт, три исхода, одна реализация | done | 0 | 0 | 27 |
| `gates-declare-what-they-prevent`<br>Гейт объявляет предотвращаемый эффект и проверяется мутацией (SENAR 1.4) | done | 0 | 0 | 42 |
| `renar-contract-contour`<br>Контрактный контур: ACTZ, итоговое ТЗ и приёмка от контракта | done | 0 | 0 | 11 |
| `test-evidence-not-test-volume`<br>Доказательность теста вместо количества тестов | done | 0 | 0 | 6 |
| `codex-first-class-19`<br>Codex — полноценный хост: живые MCP, хуки, навыки, агенты и доказуемая матрица гарантий | done | 0 | 0 | 10 |
| `release19-proof-integrity`<br>1.9: квитанция и hard-гарантии не могут лгать | done | 0 | 0 | 29 |
| `release19-effective-context`<br>1.9: эффективный контекст и измеренная дисциплина ответа | done | 0 | 0 | 14 |
| `knowledge-sheds-notion-and-its-hygiene`<br>Знание расстаётся с Notion: одна граница публикации, один путь наружу, документация сведена | done | 0 | 0 | 5 |
| `kb-docs`<br>Роевое комплексное обновление документации | done | 0 | 0 | 1 |
| `release19-clean-publication-and-onboarding`<br>1.9: публикация чистого дерева тегом и вход нового агента — по указанию владельца в смене #251 | done | 1 | 0 | 13 |
| `release19-tracker-promises`<br>1.9: обещания трекерам исполнены до тега — GitLab #5, #6, #14 и перенос hook-coverage из GitHub PR #5 (по указанию владельца в смене #258) | done | 0 | 0 | 4 |
| **Итого** | | **1** | **0** | **203** |

## Что в релиз НЕ входит

Истории эпиков (landscape-2026-h2, release-19-agent-effectiveness, release-19-renar-conformance, shared-knowledge), которых решение о составе не называет.

**Открытые — отложенная цена.** Они не отменены — они не в этой версии, и их остаток здесь для того, чтобы граница релиза была видна вместе с ценой, которую она отложила.

Открытых историй вне состава нет.

**Закрытые, составом не названные.** Их работа в дереве релиза, но обещанием релиза она не объявлена; отложенной цены у них нет.

| История | Закрыто |
|---|---|
| `bookmarks-2026-08` | 0 |
| `borrow-cubest-onyx` | 4 |
| `borrow-kaeru` | 0 |
| `codex-is-a-first-class-host` | 0 |
| `evidence-and-hygiene-debt-paid-in-19` | 1 |
| `evidence-is-durable` | 0 |
| `evidence-is-substance-not-keywords` | 0 |
| `external-proof-and-open-axes` | 2 |
| `github-primary-gitlab-mirror` | 3 |
| `kb-git-sync` | 3 |
| `kb-global` | 8 |
| `kb-identity` | 0 |
| `kb-notion` | 5 |
| `km-knowledge-layer` | 1 |
| `knowledge-records-what-failed-19` | 1 |
| `l26-arch-debt` | 30 |
| `l26-ecosystem` | 4 |
| `l26-hygiene` | 8 |
| `l26-mcp-spec` | 3 |
| `l26-narrative` | 32 |
| `l26-provable` | 10 |
| `l26-silent-failures-in-shipped-commands` | 12 |
| `l26-trust-boundary` | 14 |
| `memory-retrieves-by-relevance` | 0 |
| `obligations-to-people-are-settled` | 1 |
| `parallel-work-runs-without-collisions` | 1 |
| `proof-and-positioning-outward` | 0 |
| `release-18-audit` | 1 |
| `renar-debt-implemented-wrong` | 23 |
| `repo-hygiene-19` | 1 |
| `standards-drift-detection` | 7 |
| `surfaces-do-not-diverge` | 0 |

## Траектория объёма

Решение #370 траекторию не записало — не «ноль точек», а не записало. Ряд восстанавливается по журналу решений об объёме.

## TAUSIK-roadmap.pdf — снимок, который сознательно не переиздаётся

PDF собран 2026-08-12 и на стр. 4 объявляет вопросом 1.9 «Работает ли у чужих?». Решение о переопределении версии принято позже и этот вопрос с версии сняло, так что снимок разошёлся с релизом по существу, а не по формулировке.

Снимок НЕ переиздаётся и НЕ удаляется: он — датированная запись того, чем релиз считался в момент сборки, и переписать её значило бы стереть историю решения. Под git он не ставится (правило в `.gitignore`) — бинарник со своей копией тех же утверждений есть второе место, где им расходиться, и ничего за ним не следит.

Действующая карта — этот файл. Он порождается из живой базы, и тест перегенерирует его при каждом прогоне: разойтись с состоянием незаметно, как разошёлся PDF, он не может.
