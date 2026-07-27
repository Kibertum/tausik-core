---
slug: dlya-md-pdf-konvertatsii-v-etom-repozitorii-windows
task: audit-tausik-senar-renar-2026-05-18
date: "2026-05-20"
edges: []
---

## Decision

Для md→pdf конвертации в этом репозитории (Windows) использовать Chrome headless `--print-to-pdf` (docs/audit/tools/md_to_pdf_chrome.py: markdown→HTML+CSS→Chrome). НЕ использовать weasyprint и xhtml2pdf.

## Rationale

weasyprint падает с OSError 'cannot load library libgobject-2.0-0' (нужен GTK3 runtime), xhtml2pdf — 'no library called cairo-2' (нужен Cairo). Оба требуют нативных GTK/Cairo DLL, которых нет на этой Windows-машине и которые требуют отдельной установки. Chrome (C:\Program Files\Google\Chrome\Application\chrome.exe) уже установлен, рендерит HTML+CSS с full Cyrillic, page-breaks, таблицами и monospace — даёт лучшее качество без доп. зависимостей. Проверено на аудит-отчёте (1.76 МБ PDF из 165 КБ markdown).
