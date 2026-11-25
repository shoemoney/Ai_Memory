#!/usr/bin/env python3
"""Check that a prose-only edit left protected content alone.

Usage: check-protected.py <git-ref> [chapter.html ...]
Compares each chapter in build/chapters/ against the same file at <git-ref>.
Protected: <pre> blocks, inline <code>, <svg> diagrams, the sources list, link targets,
citation markers, element ids, and every number in the chapter text (a number of three
or more characters that the chapter repeats may appear fewer times, but not zero).
Prints one line per difference; exits 1 if any chapter differs.
"""
import re
import subprocess
import sys
from collections import Counter
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAPTERS = ROOT / "chapters"


def blocks(html, tag):
    return re.findall(rf"<{tag}\b[^>]*>.*?</{tag}>", html, flags=re.S)


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def strip_tags(html):
    return unescape(re.sub(r"<[^>]+>", " ", html))


def facets(html):
    out = {}
    out["pre"] = Counter(norm(b) for b in blocks(html, "pre"))
    out["svg"] = Counter(norm(b) for b in blocks(html, "svg"))
    rest = html
    for tag in ("pre", "svg"):
        rest = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", rest, flags=re.S)
    out["code"] = Counter(norm(b) for b in blocks(rest, "code"))
    m = re.search(r'<ol class="sources-list".*?</ol>', rest, flags=re.S)
    out["sources"] = Counter([norm(m.group(0))] if m else [])
    out["href"] = Counter(re.findall(r'href="([^"]*)"', rest))
    out["id"] = Counter(re.findall(r'\bid="([^"]*)"', rest))
    out["cite"] = Counter(norm(strip_tags(b)) for b in re.findall(r'<sup class="cite">.*?</sup>', rest, flags=re.S))
    text = strip_tags(re.sub(r'<sup class="cite">.*?</sup>', " ", rest, flags=re.S))
    out["number"] = Counter(re.findall(r"\d[\d,.]*\d|\d", text))
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ref = sys.argv[1]
    files = [Path(a) for a in sys.argv[2:]] or sorted(CHAPTERS.glob("*.html"))
    bad = 0
    for f in files:
        f = f if f.is_absolute() else (CHAPTERS / f.name)
        rel = f.relative_to(ROOT.parent)
        old = subprocess.run(["git", "show", f"{ref}:{rel}"], capture_output=True, text=True, cwd=ROOT.parent)
        if old.returncode != 0:
            print(f"{f.name}: not in {ref}, skipped")
            continue
        a, b = facets(old.stdout), facets(f.read_text())
        for key in a:
            gone, new = a[key] - b[key], b[key] - a[key]
            for item, n in gone.items():
                # A figure of three or more characters stated several times in a chapter
                # may be said fewer times, as long as it is still said at least once.
                if key == "number" and len(item) >= 3 and b[key][item] >= 1:
                    continue
                bad += 1
                print(f"{f.name}: {key} REMOVED x{n}: {item[:140]}")
            for item, n in new.items():
                bad += 1
                print(f"{f.name}: {key} ADDED x{n}: {item[:140]}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
