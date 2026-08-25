---
slug: skills-repo-ci-verify-signatures
title: "CI магазина скиллов: клон на Linux, проверка всех 39 подписей"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "Репозиторий скиллов (отдельный клон): ci/verify_signatures.py, .gitlab-ci.yml. Плюс задача-трекинг в tausik-core."
scope_exclude: "Приватный ключ .tausik/keys/project.key не читать и не коммитить. Не пушить в github.com/Kibertum/tausik-skills (мораторий). Не менять сами скиллы и подписи."
relevant_files:
  - "(skills repo id 62) ci/verify_signatures.py"
  - "(skills repo id 62) .gitlab-ci.yml"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-11T04:35:51Z"
---

## Goal

CRLF-баг ловится ровно тем, чего в магазине нет — прогоном на Linux. Подпись воспроизводится не там, где поставлена, значит 'не там' обязано прогоняться. Сейчас магазин знает, что подписи валидны, только потому что я переподписал руками после .gitattributes; это знание не переживёт следующего скилла. Репозиторий [вычеркнуто: internal-host]/kibertum/clients/kibertum/tausik/skills (id 62, private, main): 39 скиллов, 39 подписей, .gitattributes '* -text' на месте, CI нет. Добавить .gitlab-ci.yml + ci/verify_signatures.py: (1) сверка манифеста — пересчёт байт каждого скилла vs подписанный манифест, ловит CRLF/дрейф, чистый stdlib, без ключа; (2) полная ed25519-проверка публичным ключом (ed25519:1a2d26ab..., fp 103a83a2) через клон tausik-core (crypto чистый python). Провал любой подписи = красный пайплайн. Публичный ключ безопасен; приватный .tausik/keys/project.key НЕ трогать.

## Acceptance Criteria

1) ci/verify_signatures.py сверяет манифест каждого скилла (пересчёт vs подписанный) — ловит CRLF без ключа, чистый stdlib. 2) Полная ed25519-проверка публичным ключом проходит для всех 39 подписей. 3) .gitlab-ci.yml гоняет проверку на Linux при push/MR. 4) Пайплайн реально зелёный — проверено через glab, не предположено. Негативные: 5) Ошибка, если проверка зелёная на сконвертированном скилле — репро: подсунуть CRLF в один скилл, verify_signatures должен упасть. 6) Ошибка, если приватный ключ понадобился/утёк — проверка только публичным. 7) Ошибка, если скрипт молча пропускает скилл без подписи — неподписанный скилл это провал, а не skip. 8) Ошибка, если объявить пайплайн рабочим, не посмотрев статус.

## Plan

## Rollback

git revert коммита в репозитории скиллов; либо rm ci/ .gitlab-ci.yml. Скиллы и подписи не трогались.

## Journal

- 2026-07-11T04:35:38Z [implementation] — AC verified (код в репозитории магазина, id 62, коммит 0438c42): 1. ✓ ci/verify_signatures.py сверяет манифест каждого скилла (пересчёт sha256+size vs receipt.files в .tausik-signature.json) — чистый stdlib, реплика supply_sign._iter_files/build_artifact_manifest (те же _EXCLUDED_DIRS, исключение подписи, sorted rel-пути). 2. ✓ Полная ed25519 публичным ключом прошла для всех 39 — трейс пайплайна 3637: '39 skills checked [manifest + ed25519], 0 failed'. 3. ✓ .gitlab-ci.yml гоняет на Linux при push/MR/tag, shell-раннер tags:[common], без image. 4. ✓ Пайплайн реально зелёный — glab api projects/62/pipelines/3637 status=success, джоб 20600 прогнал верификацию. Негативные: 5. ✓ CRLF ловится: подсунул CRLF в noslop/SKILL.md локально -> 'FAIL noslop / byte drift (CRLF?)', rc=1; чистое дерево rc=0. Плюс CI гоняет на ВРАЖДЕБНОМ клоне (git -c core.autocrlf=true -c core.eol=crlf clone) — доказательство, что .gitattributes '* -text' нейтрализует конверсию: 0 failed. 6. ✓ Только публичный ключ (ed25519:1a2d26ab..., fp 103a83a2); приватный .tausik/keys/project.key не читался. 7. ✓ Неподписанный скилл = провал: подсунул _probe_unsigned/SKILL.md без подписи -> FAIL, не skip. 8. ✓ Статус смотрел через glab, не предполагал. Domain: подписи воспроизводятся на машине, которая их НЕ ставила (Linux-раннер), под самой враждебной конфигурацией потребителя (autocrlf=true) — ровно то, чего не было, когда магазин ломался на Linux. ed25519 через клон публичного зеркала tausik-core (crypto чистый RFC8032 stdlib), при недоступности зеркала манифест-проверка ловит CRLF сама. Пуш только во внутренний GitLab (8a1bb55..0438c42), не в github (мораторий, память #196).
