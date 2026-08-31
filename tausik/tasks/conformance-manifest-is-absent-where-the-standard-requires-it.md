---
slug: conformance-manifest-is-absent-where-the-standard-requires-it
title: "Манифест соответствия у нас не лежит нигде: §13.4.1 требует RENAR-CONFORMANCE.yaml в корне носителя, в дереве его нет"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 50
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО В #198 ПРИ РАЗБОРЕ adr-020-states-a-stale-fact-about-our-conformance-claim. Задача сообщает стандарту, что наша заявка вышла из pre-adoption. Проверяя, чем именно мы это докажем СНАРУЖИ, обнаружено: доказать нечем.

§13.4.1 «Расположение и формат»: «Манифест соответствия хранится в корне носителя требований проекта под именем RENAR-CONFORMANCE.yaml». §13.9.2 таблица запретов: «Заявление о соответствии без манифеста — запрещено, §13.4 обязательно».

У НАС: файла RENAR-CONFORMANCE.yaml в дереве НЕТ — проверено find по всему репозиторию, ноль совпадений. В git его тоже никогда не было. Есть только date-free производный вид renar/conformance.md, и его собственная прошивка обещает читателю обратное: «The date-stamped manifest lives at RENAR-CONFORMANCE.yaml (write-time metadata)» (scripts/renar_export.py:194). Обещание указывает на файл, которого не существует.

Манифест ГЕНЕРИРУЕТСЯ по требованию: `tausik renar conformance` печатает его в stdout, `--write` кладёт в корень (scripts/project_cli_renar.py:99). Живой прогон 31.08.2026 даёт корректный документ — manifest-id CFM-2026-08-31-tausik, assessment-date 2026-08-31, level RENAR-1, pre-adoption false, unmet-clauses пуст. То есть содержимое у нас есть, а артефакта нет.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА, ДВА ОСНОВАНИЯ.
ПЕРВОЕ: §13.4.1 объявляет манифест НЕИЗМЕНЯЕМЫМ в смысле V1 — «каждое заявление создаёт новую версию (manifest-version инкрементируется); предыдущие версии не удаляются, остаются в носителе как журнал аудита». Генерация по требованию этого дать не может ПРИНЦИПИАЛЬНО: у неё нет истории, manifest-version всегда 1, журнала аудита нет. Дефект не в отсутствующем файле, а в отсутствующем СПОСОБЕ вести версии.
ВТОРОЕ: снаружи нашу заявку прочитать нельзя ни в каком виде — а ADR-020 §3 строит рассуждение именно на «известной заявке», то есть читатель стандарта уже пытался её прочесть и описал неверно. Часть вины за устаревший факт в чужом ADR лежит на нас.

НЕ СЛИВАТЬ с our-conformance-generator-cites-the-wrong-chapter: там неверные ССЫЛКИ в содержимом, здесь отсутствующий АРТЕФАКТ и отсутствующее версионирование. Чинятся по-разному.

## Acceptance Criteria

## Plan

## Rollback

## Journal
