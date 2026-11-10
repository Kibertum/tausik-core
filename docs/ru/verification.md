# Проверка соблюдения контракта

[English](../en/verification.md) | **Русский**

<!-- doc-map: reader=maintainer; zone=quality -->

TAUSIK 1.11.8 сначала фиксирует машиночитаемый контракт соблюдения правил, а
затем добавляет enforcement для Codex. Исходный baseline намеренно красный:
он доказывает, что evaluator отклоняет отсутствие identity, неполный контекст,
пропуск памяти, разрыв непрерывности и преждевременное завершение. Красный
baseline не означает, что runtime enforcement уже реализован.

Публичный фасад контракта находится в `scripts/adherence_contract.py`. Policy,
живой реестр, runtime recorder и evidence evaluator разделены между соседними
модулями `adherence_policy.py`, `adherence_registry.py`,
`adherence_runtime.py` и `adherence_evidence.py`. Hash evaluator охватывает все
пять исходных файлов. Замороженные policy, event cohorts, manifest и baseline
evidence находятся в
`tests/fixtures/adherence/`. Реестр маршрутов строится из действующих service,
CLI, MCP и hook dispatch surfaces. Manifest фиксирует его канонический hash,
поэтому изменение поверхности ломает проверку.

## Зафиксированные пороги

| Метрика | Порог релиза |
|---|---:|
| Валидные execution leases | 100% |
| Полные task packages | 100% |
| Обязательные continuity events | 100% |
| Protected memory preflights | 100% |
| Повторы активного dead end без override | 0 |
| Преждевременные Stop | 0 |
| Корректные resume после hard ceiling | 100% |

Метрика доли с нулевым знаменателем не проходит. Ноль собранных событий не
может дать релизное доказательство.

## Контракт событий и маршрутов

События используют закрытый allowlist полей. Они содержат непрозрачные
хешированные идентификаторы, маршрут, границу, тип, закрытый результат, версию
policy и порядковый номер. Сообщения, details, prompts, тела команд и
произвольный текст запрещены.

Сгенерированный реестр классифицирует управляемые service, CLI, MCP и hook
entry points как `read`, `mutation`, `protected` или `stop`. Read routes входят
в закрытый точный allowlist; любой неизвестный route считается mutation. Для
каждого маршрута реестр задаёт обязательные и условные события. Валидатор
группирует события по действию и требует точный порядок его обязательств. Неизвестный маршрут,
несовпадающая граница, пропущенное или лишнее обязательство, смешение identity
между действиями, повтор идентификатора или нарушение порядка делает cohort
невалидным.

Изменение policy требует новой версии policy и L3 review. Manifest фиксирует
канонические SHA-256 hashes policy и сгенерированного реестра.

## Две независимые фазы

Negative-control исполняет шестнадцать sentinels: плохой результат для каждой
метрики, отсутствие каждого типа события, повтор события и нарушение порядка.
Evidence создаётся только после исполнения и отклонения всех sentinels.
Принятый или неисполненный sentinel делает фазу красной.

Acceptance использует события, созданные через `AdherenceRecorder` — публичный
producer для TAUSIK entry points. Красный pre-enforcement baseline вызывает
настоящие service, CLI, MCP и hook entry points, отклоняет неуспешный native
call и записывает census вызовов. Если текущие entry points ничего не эмитируют,
probe намеренно записывает ноль events; несовпадение census и events даёт
красный результат. Frozen red event baseline — отдельный детерминированный
арифметический cohort и сам по себе не доказывает provenance probe. Ручные
события разрешены только в изолированных тестах мутаций контракта.

Boundary-specific probe adapters выводят routes из bound service methods,
parsed CLI commands, MCP tool names и hook matcher metadata. Каждая строка
census хранит количество и digest эмитированных events. Contract bundle в
evidence связывает frozen census hash. Hook probes используют временный JSONL
sink через subprocess boundary. Acceptance требует сверки каждой строки census
с соответствующими action events; зелёный арифметический cohort не может
перекрыть нулевую реальную эмиссию.

Evidence содержит заявленный base commit и hashes evaluator, contract bundle,
policy, реестра и fixture. Base commit обозначает исходную точку; baseline не
утверждает, что незакоммиченный контракт уже присутствует в этом Git tree. Количества
collected, passed, failed и deselected; вердикт каждой метрики и hash самого
evidence.

## Проверка приватности

Baseline проверяет scanner четырёх sink. Релизный gate 1.11.8 должен собрать и
передать реальные database, stdout, stderr и JSON evidence sinks; один baseline
не доказывает покрытие release pipeline. Для scanner обязательны все четыре
input. Добавить свободное текстовое поле без изменения версии policy невозможно.

Фокусный прогон:

```text
pytest -q tests/test_adherence_contract.py
```
