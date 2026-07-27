---
slug: translation-drift-audit-needs-skip-marker-code-fence
title: "translation-drift audit needs skip-marker + code-fence awareness"
type: pattern
tags: []
task: null
edges: []
---

Translation-drift audit для bilingual docs должен поддерживать (a) skip-marker для intentionally-abbreviated mirrors и (b) учёт fenced-code-block контекста при подсчёте заголовков. Без этих двух фич regex-based audit генерирует false-positive drift на (a) RU-зеркалах, которые специально являются краткими обзорами и явно ссылаются на полный EN, и (b) markdown examples внутри triple-backtick блоков, где '# BAD'/'# GOOD' выглядят как заголовки. См. v14b-audit-translation-skip-marker.
