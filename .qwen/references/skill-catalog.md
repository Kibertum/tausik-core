# External Skill Catalog

This file is NOT loaded into every message. Agent reads it on-demand
when user request doesn't match installed skills.

## Activation
To activate a VENDORED skill: copy from `.tausik/vendor/{name}/{skill}/`
to `.qwen/skills/{skill}/` — it becomes available immediately.
To deactivate: delete from `.qwen/skills/{skill}/`.

## seo [VENDORED]
SEO analysis: site audits, technical SEO, schema markup, E-E-A-T, Core Web Vitals, AI Overviews optimization
Source: AgriciDaniel/claude-seo@v1.5.0
Triggers: SEO, аудит сайта, поисковая оптимизация, structured data, schema markup, sitemap, robots.txt, метатеги, индексация, Core Web Vitals, E-E-A-T
Activate: `cp -r .tausik/vendor/seo/{skill}/ .qwen/skills/{skill}/`

## ui-ux-pro-max [VENDORED]
UI/UX design: 50+ styles, 161 palettes, 57 font pairings, components, accessibility, responsive design
Source: nextlevelbuilder/ui-ux-pro-max-skill@main
Triggers: дизайн, UI, UX, макет, wireframe, landing page, компоненты, палитра, типографика, Tailwind, стили, тема, dark mode, адаптивный
Activate: `cp -r .tausik/vendor/ui-ux-pro-max/{skill}/ .qwen/skills/{skill}/`

## trailofbits [VENDORED]
Security: static analysis, supply chain audit, semgrep rules, YARA, property-based testing, code review
Source: trailofbits/skills@main
Triggers: security, безопасность, vulnerability, уязвимость, audit, pentest, static analysis, semgrep, SAST, supply chain
Activate: `cp -r .tausik/vendor/trailofbits/{skill}/ .qwen/skills/{skill}/`

## anthropic-official [VENDORED]
Official Anthropic: PDF, Word, Excel, PowerPoint, MCP builder, webapp testing, skill creator
Source: anthropics/skills@main
Triggers: PDF, Word, DOCX, Excel, XLSX, PowerPoint, PPTX, документ, презентация, таблица, MCP, тестирование веб
Activate: `cp -r .tausik/vendor/anthropic-official/{skill}/ .qwen/skills/{skill}/`

## polyakov [VENDORED]
Yandex tools (Webmaster, Wordstat, Metrika, Search API), agent orchestration, codex review, docx contracts, image generation
Source: artwist-polyakov/polyakov-claude-skills@main
Triggers: Яндекс, Yandex, Вебмастер, Wordstat, Метрика, поисковая выдача, агент, sub-agent, codex review, договор, контракт, Word шаблон, генерация изображений, fal.ai
Activate: `cp -r .tausik/vendor/polyakov/{skill}/ .qwen/skills/{skill}/`

---
Agent: when user request matches triggers for a non-ACTIVE skill,
suggest activation. If VENDORED — copy to .qwen/skills/. If AVAILABLE — run bootstrap.
On /end or /checkpoint — remove vendor skills from .qwen/skills/ to keep context clean.
