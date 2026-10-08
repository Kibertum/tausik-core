---
slug: extract-site-gitlab
title: "Создание standalone-репо tausik/site + CI/CD"
status: done
epic: site-standalone-agent-ready
---

Создать GitLab-репо tausik/site, наполнить файлами сайта (чистый старт), настроить пайплайн: fetch-docs (клон core через deploy token) → build (Dockerfile/nginx) → deploy (контейнер tausik-site:8900). Проверить standalone-сборку и деплой.
