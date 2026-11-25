#!/usr/bin/env python3
"""Generate part dividers and explicit back-matter ordering without writing chapters.

Imported by build.py. Standalone invocation prints the generated divider markup.
"""
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CH = HERE / "chapters"

PARTS = {
    "a": ("Part A", "Files and text",
          "The simplest memory is a folder of text files. This part covers files the agent reads directly, "
          "task memory for coding agents, and wikis and context databases that a model keeps tidy."),
    "b": ("Part B", "Vectors and retrieval",
          "Search by meaning turns text and images into vectors. This part covers the embedding models "
          "and the retrieval techniques that decide what the agent finds."),
    "c": ("Part C", "Models that remember",
          "A second model can read, write and tidy memory for the agent. This part covers small local "
          "models and uncensored ones, and where each fits."),
    "d": ("Part D", "Stores",
          "Where memories actually live. This part covers PostgreSQL, Redis and Valkey, caches, "
          "dedicated vector stores, and SQLite with other embedded stores."),
    "e": ("Part E", "Frameworks and graphs",
          "Frameworks and managed services package the read and write loop so you do not build it "
          "yourself. This part covers them, and graph-based memory with a sense of time."),
    "f": ("Part F", "History, research and practice",
          "How the field got here, where research is heading, and how to run it safely. It ends with a "
          "way to choose a stack and a field report."),
    "g": ("Part G", "Case studies: local models only",
          "Four complete builds that use only models you run yourself: one assistant built in six memory "
          "stages, then a painter, a doctor's office and an international homebuilder. The last three each "
          "have a one-page map."),
}


def ordered_files(files):
    """Generate dividers in memory; never write or delete chapter files."""
    front, chapters, glossary = [], [], []
    for name, text in files:
        if re.search(r'class=[\"\'][^\"\']*\bpart-divider\b', text):
            continue  # Old on-disk generated dividers are ignored.
        if 'glossary' in name.lower():
            text = re.sub(r'data-ch="[^"]*"', 'data-ch="A"', text, count=1)
            text = re.sub(r'data-part="[^"]*"', 'data-part="ref"', text, count=1)
            glossary.append((name, text))
        elif re.search(r'data-ch="(?!00)\d+"', text):
            ch = re.search(r'data-ch="(\d+)"', text).group(1)
            if 20 <= int(ch) <= 23:
                text = re.sub(r'data-part="[^"]*"', 'data-part="g"', text, count=1)
            chapters.append((name, text))
        else:
            front.append((name, text))
    chapters.sort(key=lambda item: (int(re.search(r'data-ch="(\d+)"', item[1]).group(1)), item[0]))
    groups = {}
    for name, text in chapters:
        part = re.search(r'data-part="([^"]+)"', text).group(1)
        ch = re.search(r'data-ch="(\d+)"', text).group(1)
        title = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S).group(1)
        groups.setdefault(part, []).append((ch, title))
    out, seen = sorted(front), set()
    for name, text in chapters:
        part = re.search(r'data-part="([^"]+)"', text).group(1)
        if part not in seen:
            out.append((f'part-{part}.html', divider(part, groups[part])))
            seen.add(part)
        out.append((name, text))
    out.extend(sorted(glossary))
    return out


def divider(part, items):
    eyebrow, title, intro = PARTS[part]
    appendix = ''
    letter = part.upper()
    lis = ''.join(f'<li><b>{c}</b>{h}</li>' for c, h in items)
    return (f'<section class="part-divider" data-part="{part}"{appendix}>'
            f'<div class="part-letter" aria-hidden="true">{letter}</div><div class="part-body">'
            f'<p class="part-eyebrow">{eyebrow}</p><h1 class="part-title">{title}</h1>'
            f'<p class="part-intro">{intro}</p><ul class="part-chapters">{lis}</ul></div></section>')


def main():
    files = [(p.name, p.read_text(encoding='utf-8')) for p in CH.glob('*.html')]
    for name, text in ordered_files(files):
        if name.startswith('part-'):
            print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
