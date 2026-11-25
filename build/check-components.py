#!/usr/bin/env python3
"""Render every ```html snippet in COMPONENTS.md as one test chapter and run the real build on it.

Fails (non-zero) if any snippet breaks a lint rule or the render checks.
Use --keep to leave build/_components-test.pdf in place for inspection.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
md = (HERE / "COMPONENTS.md").read_text(encoding="utf-8")
blocks = re.findall(r"^```html\n(.*?)^```", md, re.S | re.M)
if not blocks:
    sys.exit("no html snippets found in COMPONENTS.md")

body = "\n".join(blocks)
chapter = (
    '<article class="chapter" data-ch="07" data-part="d" data-running="Component test">\n'
    + body
    + "\n</article>\n"
)
tmp = Path(tempfile.mkdtemp(prefix="guide-components-"))
try:
    shutil.copy(HERE / "chapters" / "00-front.html", tmp / "00-front.html")
    shutil.copy(HERE / "chapters" / "01-0-part-a.html", tmp / "01-0-part-a.html")
    (tmp / "07-components-test.html").write_text(chapter, encoding="utf-8")
    env = dict(os.environ)
    env["GUIDE_CHAPTERS"] = str(tmp)
    env["GUIDE_HTML"] = str(HERE / "_components-test.html")
    env["GUIDE_PDF"] = str(HERE / "_components-test.pdf")
    r = subprocess.run([sys.executable, str(HERE / "build.py")], env=env)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    (HERE / "_components-test.html").unlink(missing_ok=True)
    if "--keep" not in sys.argv and r.returncode == 0:
        (HERE / "_components-test.pdf").unlink(missing_ok=True)
sys.exit(r.returncode)
