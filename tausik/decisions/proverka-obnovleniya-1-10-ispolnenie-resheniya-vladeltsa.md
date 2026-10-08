---
slug: proverka-obnovleniya-1-10-ispolnenie-resheniya-vladeltsa
task: session-update-check-collides-with-the-zero-phone-home-claim
date: "2026-09-23"
edges: []
---

## Decision

ПРОВЕРКА ОБНОВЛЕНИЯ (1.10, исполнение решения владельца #372): источник — GitHub REST releases/latest (вариант b), анонимный GET с постоянным User-Agent, без имени проекта, пути, версии схемы и версии TAUSIK. Замер 23.09.2026: REST ~1,1 с, git ls-remote --tags ~1,4 с — оба близко к бюджету 2 с, поэтому запрос НЕ стоит на пути SessionStart: хук запускает tausik update-check отсоединённо, ответ кэшируется в .tausik/update_check.json не чаще раза в сутки, status печатает строку, если вышла новая версия. Включено по умолчанию, выключается updates.check=false; README EN/RU переписан с «0 обращений наружу» на точное описание запроса. Выбор варианта и умолчания — агента в смене #267; владельцу — на подтверждение.

## Rationale

Владелец в #372 сделал проверку обязательной и назвал источником GitHub; вариант (c) — сабмодульный remote консумента — может указывать на GitLab и не отвечает 'источник GitHub'. REST даёт имя и ссылку релиза одним запросом и быстрее ls-remote.
