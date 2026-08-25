---
slug: site-ignoredeadlinks-true-masks-103-broken-refs-in-docs-en
title: "site: ignoreDeadLinks=true masks 103 broken refs in docs/{en,ru}/*.md"
type: gotcha
tags: []
task: null
edges: []
---

site/.vitepress/config.ts ставит ignoreDeadLinks:true, потому что 103 ссылки в исходниках (docs/en/*.md, docs/ru/*.md) ломаются после переноса в site/{docs,ru/docs}/ через sync-docs.mjs. Два типа: (1) relative refs на код-файлы — например `./../../scripts/brain_schema.py` в shared-brain.md; (2) cross-language ссылки `./../en/stacks` в ru-файлах. Чинить нужно правкой исходников: либо удалить ссылки на код (заменить на github links), либо переписать cross-language через VitePress lang-aware paths. После чистки убрать ignoreDeadLinks из config.ts.</content>
<parameter name="tags">["site", "vitepress", "deadlinks", "docs"]
