"""md->pdf via Chrome headless (best quality, no extra deps).
Usage: python md_to_pdf_chrome.py <input.md> <output.pdf>
"""
import sys
import re
import subprocess
import tempfile
from pathlib import Path
import markdown

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

CSS_STR = """
@page {
    size: A4;
    margin: 2cm 2cm 2.5cm 2cm;
}
body {
    font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, "Noto Sans", sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #222;
    max-width: 100%;
}
h1 {
    font-size: 22pt;
    color: #1a1a1a;
    border-bottom: 3px solid #c33;
    padding-bottom: 0.3em;
    margin-top: 2em;
    page-break-before: always;
    page-break-after: avoid;
}
h1:first-of-type { page-break-before: avoid; margin-top: 0; }
h2 {
    font-size: 16pt;
    color: #333;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.2em;
    margin-top: 1.5em;
    page-break-after: avoid;
}
h3 {
    font-size: 13pt;
    color: #444;
    margin-top: 1.2em;
    page-break-after: avoid;
}
h4 {
    font-size: 11.5pt;
    color: #555;
    margin-top: 1em;
    page-break-after: avoid;
}
h5 { font-size: 10.5pt; color: #666; font-weight: bold; }
p { text-align: justify; margin: 0.5em 0; }
code {
    font-family: Consolas, "Courier New", monospace;
    font-size: 9.5pt;
    background: #f4f4f4;
    padding: 1px 4px;
    border-radius: 3px;
    color: #c33;
}
pre {
    background: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.8em;
    font-size: 9pt;
    overflow-x: auto;
    page-break-inside: avoid;
    white-space: pre-wrap;
    word-wrap: break-word;
}
pre code { background: transparent; color: #222; padding: 0; }
blockquote {
    border-left: 4px solid #c33;
    background: #fafafa;
    padding: 0.5em 1em;
    margin: 1em 0;
    color: #555;
    font-style: italic;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #ccc;
    padding: 0.4em 0.6em;
    text-align: left;
    vertical-align: top;
}
th { background: #f0f0f0; font-weight: bold; }
tr:nth-child(even) { background: #fafafa; }
ul, ol { margin: 0.5em 0; padding-left: 1.6em; }
li { margin: 0.2em 0; }
a { color: #c33; text-decoration: none; }
hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
strong { color: #1a1a1a; }
.cover {
    text-align: center;
    page-break-after: always;
    padding-top: 6em;
}
.cover .title { font-size: 28pt; font-weight: bold; color: #1a1a1a; margin-bottom: 0.5em; }
.cover .subtitle { font-size: 14pt; color: #666; margin-bottom: 2em; }
.cover .meta { font-size: 11pt; color: #888; margin-top: 4em; }
"""

def main():
    if len(sys.argv) < 3:
        print("Usage: python md_to_pdf_chrome.py <input.md> <output.pdf>")
        sys.exit(1)
    src = Path(sys.argv[1]).resolve()
    dst = Path(sys.argv[2]).resolve()

    text = src.read_text(encoding="utf-8")
    # strip YAML frontmatter
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)

    html_body = markdown.markdown(
        text,
        extensions=["extra", "toc", "tables", "fenced_code", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-4"}},
    )
    html_full = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Audit Report</title>
<style>{CSS_STR}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # write to temp html
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_full)
        html_path = Path(f.name)

    file_url = "file:///" + str(html_path).replace("\\", "/")

    # Run Chrome headless
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",  # we'll add via CSS if needed
        f"--print-to-pdf={dst}",
        "--print-to-pdf-no-header",
        "--virtual-time-budget=10000",
        file_url,
    ]
    print(f"Converting {src.name} -> {dst.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if dst.exists() and dst.stat().st_size > 1000:
        print(f"OK: {dst} ({dst.stat().st_size:,} bytes)")
    else:
        print(f"FAILED. stdout: {result.stdout[:300]}")
        print(f"stderr: {result.stderr[:300]}")
        sys.exit(1)

    html_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
