---
slug: site-lastupdated-false-because-docker-build-stage-has-no
title: "site: lastUpdated=false because Docker build stage has no git/.git"
type: gotcha
tags: []
task: null
edges: []
---

VitePress lastUpdated:true вызывает `git log` per page → 'spawn git ENOENT' в Docker build (node:22.14.0-alpine + COPY без .git). Текущее: lastUpdated:false в config.ts. Чтобы включить нужно: (a) `apk add --no-cache git` в Dockerfile build stage; (b) убрать .git из .dockerignore (или копировать его специально: `COPY .git .git`); (c) build stage всё равно multi-stage, prod image (nginx:alpine) останется компактным. Альтернатива — в .gitlab-ci.yml на этапе build передавать timestamp через --build-arg из git log на runner (избегает git внутри Docker).</content>
<parameter name="tags">["site", "vitepress", "docker", "git", "lastupdated"]
