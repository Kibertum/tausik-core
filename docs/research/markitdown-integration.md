# markitdown integration — opt-in document extraction

TAUSIK ships with **no manual document parsers** in its core (convention #19: zero external deps). For DOCX / PPTX / XLSX / HTML / EPUB / audio / image extraction, we provide an opt-in wrapper around [Microsoft markitdown](https://github.com/microsoft/markitdown).

## Why opt-in, not bundled?

- Convention #19 — TAUSIK core is stdlib-only. Bundling markitdown (~50 MB with `[all]`) breaks that for users who don't need DOCX/PPTX extraction.
- markitdown is MIT-licensed but pulls in heavy transitive deps (Azure SDKs, OCR libs). Forcing them on every TAUSIK install is wrong.
- Discovery during the `markitdown-integration` task: there were no manual parsers to replace. The task was reframed from "replace" to "add as opt-in capability".

## Install on demand

```bash
pip install 'markitdown[all]'             # everything (audio, image OCR, etc.)
pip install 'markitdown[docx,pptx,xlsx]'  # office-only, much smaller
```

The TAUSIK CLI reports a friendly error if markitdown isn't importable; nothing crashes.

## Usage

```bash
.tausik/tausik doc extract path/to/file.docx           # → markdown on stdout
.tausik/tausik doc extract slides.pptx --format=pptx   # format hint logged
```

In Python scripts:

```python
import doc_extract
md = doc_extract.extract_to_markdown("path/to/file.xlsx")
if md is None:
    # markitdown missing OR file missing OR extraction failed (diagnostic on stderr)
    ...
```

`extract_to_markdown()` never raises — graceful `None` return + stderr diagnostic.

## What about PDF?

Use Claude Code's built-in `Read` tool (the `/pdf` skill wraps it). Claude Code's PDF support is well-tuned (pages parameter, OCR fallback for scanned docs). markitdown's PDF path is OK but `Read` is the primary recommendation. The `/markitdown` skill explicitly redirects PDF requests to `/pdf`.

## When to disable

There's nothing to disable — markitdown is opt-in. To "uninstall":

```bash
pip uninstall markitdown
```

After that, `tausik doc extract` returns the friendly "not installed" error.

## Future integration (not implemented)

The `brain_post_webfetch` hook could eventually call `doc_extract` to convert WebFetch'd HTML pages to clean markdown before caching. Not in this task — flagged for follow-up if/when needed.

## Test coverage

`tests/test_doc_extract.py` (11 tests) — happy path, ImportError, missing file, malformed result shape, exception handling, format-hint logging. Plus 1 soft-integration test that runs only when markitdown is actually installed (skipped on CI by default).
