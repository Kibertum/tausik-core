[English](../en/assurance.md) | **Русский**

# Контракт остаточной уверенности

<!-- doc-map: reader=user; zone=core-surface -->

TAUSIK выводит глубину review из остаточной неопределённости после доступных
доказательств, а не из названия технологии, расширения файла, роли или имени
гейта. Канонический review dispatcher превращает решение в маршрут, который
используют package задачи, CLI, MCP и сгенерированные skills всех хостов.

## Декларации

Задача хранит `assurance_profiles` как JSON-список и `assurance_impact` как
JSON-объект. Декларация стека задаёт те же поля по умолчанию. Профили задачи
добавляются к профилям стека, а impact задачи переопределяет значения стека.

| Профиль | Обязательные evidence capabilities |
|---|---|
| `declarative` | `behavior`, `idempotence`, `rollback`, `postconditions` |
| `executable` | `behavior`, `rollback`, `postconditions` |
| `migration` | `behavior`, `rollback`, `postconditions` |
| `research` | `reproducibility`, `provenance` |

Оси impact: `level` (`low`, `medium`, `high`), `blast_radius` (`local`,
`bounded`, `broad`), `reversibility` (`reversible`, `conditional`,
`irreversible`), `security_boundary`, `governance_boundary`, `privileged`,
`data_change` (`none`, `non_destructive`, `destructive`) и `owner_escalation`.
Отсутствующие главные оси остаются `unknown`; неизвестные метаданные дают L2.

## Возможности доказательств

Гейт объявляет `evidence_capabilities` в `stack.json`: `syntax`, `schema`,
`policy`, `behavior`, `idempotence`, `rollback`, `postconditions`,
`reproducibility` или `provenance`. Возможность учитывается только у прошедшего
гейта из последнего подписанного receipt. Само имя гейта ничего не доказывает.

Поэтому lint и schema validation не доказывают поведение, идемпотентность,
rollback, postconditions или соблюдение policy. Для каждого свойства нужен
гейт, который действительно его проверяет.

## Выбор глубины

Чистая policy-функция возвращает профили, impact, обязательные и наблюдённые
доказательства, остаточные пробелы, глубину, детерминированные причины и
жёсткий порог.

- L1 требует полного evidence и impact `low` + `local` + `reversible`.
- L2 служит fallback при неполных метаданных, обычных остаточных пробелах или
  полностью доказанном, но повышенном контекстном impact.
- L3 выбирается, когда при повышенном impact остаются непокрытые свойства.
- L3 нельзя понизить для security/governance boundaries, privileged-изменений,
  необратимых изменений, разрушительных миграций данных и явной эскалации
  владельца.

## Выполнение review

Package задачи содержит `review_route` и список недостающих входов. L1
выполняет чек-листы выбранных профилей и детерминированные гейты с нулём
reviewer-вызовов. L2 запускает одного сфокусированного reviewer в свежем
контексте. Обычный L3 запускает одного внешнего reviewer из другого семейства
моделей. Отдельный контекст на модели автора остаётся L2, а не L3. Multi-agent
L3-deep разрешён только для явного `/review` или настроенного
`review.extreme_hard_floor` у задачи с жёстким L3.

Review-запись сохраняет фактический уровень, профили, причины, hard floor,
модели автора и reviewer, контекст, число вызовов, маршрут и доступный usage.
HIGH или CRITICAL не удовлетворяют проходному L3-гейту закрытия. После
существенного ремонта нужна свежая детерминированная проверка.

## Расширение и совместимость

Пользовательский стек добавляется в `.tausik/stacks/<name>/stack.json` и сам
объявляет профили, impact по умолчанию и возможности гейтов. Puppet-подобный
стек с профилем `declarative` получает ту же policy, что встроенный
декларативный стек; центральный allowlist и ветка маршрутизации не нужны.

Изменение базы аддитивно. Старые задачи и стеки без деклараций получают
консервативный L2, а не выдуманный L1 или поголовный L3. Свежая и обновлённая
базы содержат одинаковые nullable-поля задачи.
