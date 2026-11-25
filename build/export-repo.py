#!/usr/bin/env python3
"""Export the companion repository tree from the built PDF.

Usage: export-repo.py <out-dir>
Writes: <out-dir>/ai-memory-guide.pdf, <out-dir>/chNN/<file> for every code file attached
to the PDF, <out-dir>/maps/<name>.png, and <out-dir>/README.md with a per-chapter index.
The PDF is the single source: whatever is attached to it is what gets exported.
"""
import re
import shutil
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
PDF = ROOT / "ai-memory-guide.pdf"
REPO = "https://github.com/shoemoney/Ai_Memory"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(PDF)
    titles = {}
    for f in sorted((ROOT / "chapters").glob("[0-9][0-9]-*.html")):
        num = f.name[:2]
        m = re.search(r"<h1[^>]*>(.*?)</h1>", f.read_text(), flags=re.S)
        if m and "part-" not in f.name and "glossary" not in f.name and "appendix" not in f.name:
            titles.setdefault(num, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip())
    by_dir = {}
    for name in sorted(doc.embfile_names()):
        target = (out / name).resolve()
        if out not in target.parents:
            sys.exit(f"refusing to write outside the export folder: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(doc.embfile_get(name))
        if target.suffix in (".sh", "") and target.read_bytes()[:2] == b"#!":
            target.chmod(0o755)
        by_dir.setdefault(name.split("/")[0], []).append(name)
    shutil.copy2(PDF, out / PDF.name)

    lines = [
        "# AI Memory: Building an LLM brain",
        "",
        "By Jeremy Schoemaker.",
        "",
        f"The book is [`{PDF.name}`]({PDF.name}) in this folder. Every code file the book prints or",
        "points to is here, one folder per chapter, under the same name the book uses.",
        "",
        "```bash",
        f"git clone {REPO}.git",
        "```",
        "",
        "Each chapter's walkthrough says which versions it was tested with and how to clean up",
        "afterwards. Blocks the book marks \"From docs, not run\" were not executed.",
        "",
        "## Files by chapter",
        "",
    ]
    for d in sorted(by_dir):
        num = d[2:] if d.startswith("ch") else None
        heading = f"Chapter {num}: {titles[num]}" if num in titles else ("Maps" if d == "maps" else d)
        lines += [f"### {heading}", ""]
        lines += [f"- [`{n}`]({n})" for n in by_dir[d]]
        lines.append("")
    (out / "README.md").write_text("\n".join(lines))
    print(f"exported {sum(len(v) for v in by_dir.values())} files in {len(by_dir)} folders to {out}")


if __name__ == "__main__":
    main()
