---
slug: strogost-etogo-repozitoriya-pereezzhaet-v-zakommichennyy
task: this-repos-strictness-lives-in-a-gitignored-file
date: "2026-08-31"
edges: []
---

## Decision

СТРОГОСТЬ ЭТОГО РЕПОЗИТОРИЯ ПЕРЕЕЗЖАЕТ В ЗАКОММИЧЕННЫЙ tausik/policy.json — ВТОРУЮ ПОЛОВИНУ ПРОЕКТНОГО ТИРА, А НЕ В НОВЫЙ ТИР И НЕ В ДЕФОЛТЫ

## Rationale

Вариант (а) из трёх. Замер: свежий worktree при пользовательском тире auto_verify=true даёт auto_verify=True и bootstrap_drift=False — оба ужесточения исчезают, отклонений ноль (проектный тир пуст). Вариант (в) НЕВОЗМОЖЕН МЕХАНИЧЕСКИ: auto_verify=False УЖЕ фреймворковый дефолт (GUARDS), а дефолт проигрывает доверенному тиру — перебить пользовательский тир может только ПРОЕКТНЫЙ. Вариант (б) снял бы .tausik/config.json из-под .gitignore, но файл генерируемый: _meta.generated_at/lib_commit, installed_skills, brain.database_ids — каждый bootstrap пачкал бы дерево машинными данными. Прецедент уже в дереве: tausik/gates.json, закоммиченный branch-coupled носитель, его _comment прямо говорит «so a fresh clone carries it»; обобщается загрузчиком, а не копией правила. Новой власти не появляется: policy.json — тот же НЕДОВЕРЕННЫЙ проектный тир, только ужесточать.
