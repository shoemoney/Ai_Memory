#!/usr/bin/env python3
"""Build a reflowable EPUB 3 edition of the book: build/ai-memory.epub.

    python3 build/make-epub.py            build the EPUB and check it against its own navigation
    python3 build/make-epub.py -o FILE    write somewhere else

Content, order and edition text come from the ebook edition of build.py (chapters, generated part dividers,
glossary, code-file relocation), so the EPUB and the ebook PDF stay in step. The styling is build/epub.css.

Run-time needs: Python 3 with beautifulsoup4 and soupsieve (the same packages build.py already uses; lxml is not
needed). If missing:  pip install beautifulsoup4 soupsieve

The output is deterministic: the same inputs give the same bytes. The modification date in the package is the
newest modification time of the inputs, so it only changes when an input changes.

Code files: a named code file longer than eight lines is not printed in its chapter. The PDF attaches those files;
the EPUB carries every one of them as a listing in Appendix B (one document per chapter) and each chapter pointer links to its listing.
"""
import argparse
import html
import importlib.util
import os
import re
import runpy
import sys
import uuid
import zipfile
from pathlib import Path

import warnings

from bs4 import BeautifulSoup, Comment, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COVER_SRC = ROOT / "covers" / "ebook" / "AI-Memory-Kindle-and-EPUB-cover.jpg"
CSS_SRC = HERE / "epub.css"
DEFAULT_OUT = HERE / "ai-memory.epub"

SUBTITLE = "Building an LLM brain"
AUTHOR = "Jeremy Schoemaker"
AUTHOR_SORT = "Schoemaker, Jeremy"
ID_NAMESPACE = uuid.UUID("6d1f3a52-8c47-4f2e-9a63-2b7d0e5c1a94")
XHTML_NS = "http://www.w3.org/1999/xhtml"
SVG_NS = "http://www.w3.org/2000/svg"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
SVG_CAMEL = {
    "viewbox": "viewBox", "markerwidth": "markerWidth", "markerheight": "markerHeight", "markerunits": "markerUnits",
    "refx": "refX", "refy": "refY", "textlength": "textLength", "lengthadjust": "lengthAdjust",
    "preserveaspectratio": "preserveAspectRatio", "patternunits": "patternUnits", "gradientunits": "gradientUnits",
}
ARROW = "#39414f"
PART_COLOR = {"a": "#1f4bd8", "b": "#0a7c78", "c": "#6a3fd1", "d": "#d23b1c", "e": "#9a6200", "f": "#2c7a3a",
              "g": "#a13568", "ref": "#3f4d66"}


def load_build():
    os.environ["EDITION"] = "ebook"
    spec = importlib.util.spec_from_file_location("guide_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def esc(s):
    return html.escape(s, quote=True)


# --------------------------------------------------------------------------
# Source text: same content as the ebook edition, with the PDF-only wording replaced
# --------------------------------------------------------------------------
APPX_B_FRONT = re.compile(r"<strong>Appendix B, Attached files\.</strong>.*?under sources/\.", re.S)
APPX_B_TEXT = (
    "<strong>Appendix B, Code files.</strong> An index of every code file, with a listing of each long one. Code is "
    "linked, not printed: a named file longer than eight lines leaves the chapter, and the chapter shows a one-line "
    "pointer that links to its listing in Appendix B. The same files are in the companion repository. Each file has a "
    "label such as ch09-code05, meaning Chapter 09, fifth named file. Every source link, by chapter and number, is "
    "also listed in the companion repository under sources/."
)


def adapt_text(text):
    text = APPX_B_FRONT.sub(lambda _m: APPX_B_TEXT, text)
    text = re.sub(r"\s*A large version is attached to the PDF as maps/[\w.-]+\.png\.", "", text)
    for old, new in (("Dark dots:", "Square marks (■):"), ("Colored dots:", "Round dots (●):"),
                     ("colored dots.", "round dots (●)."), ("dark dots.", "square marks (■).")):
        text = text.replace(old, new)
    return text


def load_book(b):
    files = [(p.name, b.pick_edition(p.read_text(encoding="utf-8"))) for p in sorted(b.CHAPTERS.glob("*.html"), key=lambda x: x.name)]
    if not files:
        sys.exit(f"no chapters in {b.CHAPTERS}")
    files = runpy.run_path(str(HERE / "make-dividers.py"))["ordered_files"](files)
    files, attachments, listings = b.relocate(files, enabled=True, edition="ebook")
    files = [(n, adapt_text(b.link_sources(t))) for n, t in files if n != "attached-files.html"]
    return files, dict(attachments), listings


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------
class Doc:
    def __init__(self, stem, title, body, kind="body", part=None, epub_type=None, folder="text"):
        self.stem, self.title, self.body, self.kind, self.part = stem, title, body, kind, part
        self.epub_type = epub_type
        self.file = f"{stem}.xhtml"
        self.ids = set()


def section_html(soup_section):
    return str(soup_section)


def split_front(text):
    """00-front.html holds the cover, the reading guide and the contents page as three sections."""
    soup = BeautifulSoup(text, "html.parser")
    secs = {}
    for sec in soup.find_all("section", recursive=False):
        cls = sec.get("class", [])
        key = "cover" if "cover" in cls else "howto" if "howto" in cls else "toc" if "toc-page" in cls else None
        if key:
            secs[key] = sec
    if len(secs) != 3:
        sys.exit("00-front.html: expected a cover, a howto and a toc-page section")
    return secs


def cover_facts(cover):
    top = [s.get_text(strip=True) for s in cover.select(".cover-top span")]
    by = cover.select_one(".cover-author .by").get_text(strip=True)
    note = cover.select_one(".cover-author em").get_text(strip=True)
    asof = cover.select_one(".cover-foot div").get_text(" ", strip=True)
    sub = cover.select_one(".cover-sub").get_text(strip=True)
    return dict(kind=top[0], date=top[1], author=by.removeprefix("Written By ").strip(), note=note, asof=asof, sub=sub)


def pub_date(date_text):
    month, year = date_text.split()
    return f"{year}-{MONTHS.index(month) + 1:02d}"


def title_page(facts):
    return (
        '<section class="titlepage">'
        f'<p class="tp-eyebrow">{esc(facts["kind"])} · {esc(facts["date"])}</p>'
        '<h1 class="tp-title"><span class="ai">AI</span> Memory</h1>'
        f'<p class="tp-sub">{esc(facts["sub"])}</p>'
        f'<p class="tp-by">{esc(facts["author"])}</p>'
        f'<p class="tp-note">{esc(facts["note"])}</p>'
        f'<p class="tp-asof">{esc(facts["asof"])}</p>'
        "</section>"
    )


# --------------------------------------------------------------------------
# Navigation tree
# --------------------------------------------------------------------------
class Node:
    def __init__(self, title, doc, frag=None, cls=""):
        self.title, self.doc, self.frag, self.cls = title, doc, frag, cls
        self.children = []

    def href(self, prefix=""):
        return f"{prefix}{self.doc}" + (f"#{self.frag}" if self.frag else "")


def render_ol(nodes, prefix, indent=0):
    pad = "  " * indent
    out = [f"{pad}<ol>"]
    for n in nodes:
        cls = f' class="{n.cls}"' if n.cls else ""
        out.append(f'{pad}  <li{cls}><a href="{esc(n.href(prefix))}">{esc(n.title)}</a>')
        if n.children:
            out.append(render_ol(n.children, prefix, indent + 2))
        out.append(f"{pad}  </li>")
    out.append(f"{pad}</ol>")
    return "\n".join(out)


def flatten(nodes):
    for n in nodes:
        yield n
        yield from flatten(n.children)


def depth(nodes):
    return 1 + max((depth(n.children) for n in nodes if n.children), default=0)


# --------------------------------------------------------------------------
# Conversion of one document to XHTML
# --------------------------------------------------------------------------
def sprite(part):
    color = PART_COLOR.get(part or "a", ARROW)
    def marker(mid, fill):
        return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0 0.5L10 5L0 9.5z" fill="{fill}"/></marker>')
    return (f'<svg xmlns="{SVG_NS}" width="0" height="0" focusable="false" aria-hidden="true" class="sprite"><defs>'
            f'{marker("arr", ARROW)}{marker("arr-ac", color)}</defs></svg>')


def convert(doc, id_doc, problems):
    soup = BeautifulSoup(doc.body, "html.parser")
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    has_svg = False
    for svg in soup.find_all("svg"):
        has_svg = True
        svg["xmlns"] = SVG_NS
        for el in [svg] + svg.find_all(True):
            for key in list(el.attrs):
                if key in SVG_CAMEL:
                    el.attrs[SVG_CAMEL[key]] = el.attrs.pop(key)
            for key, val in list(el.attrs.items()):
                if val == "context-stroke":
                    el.attrs[key] = ARROW
        svg.attrs.setdefault("focusable", "false")
    for path in soup.select("svg path.d-line"):
        if "plain-end" not in path.get("class", []):
            path["marker-end"] = "url(#arr-ac)" if "accent" in path.get("class", []) else "url(#arr)"

    for r in soup.select("span.rating"):
        cls = r.get("class", [])
        n = next((int(c[1]) for c in cls if re.fullmatch(r"r[1-5]", c)), 0)
        on, off = ("■", "□") if "ink" in cls else ("●", "○")
        r.clear()
        r.string = on * n + off * (5 - n)

    for t in soup.find_all("table"):
        heads = [th.get_text(" ", strip=True) for th in t.select("thead th")]
        if heads:
            for tr in t.select("tbody tr"):
                for i, td in enumerate(tr.find_all("td", recursive=False)):
                    if i < len(heads) and heads[i]:
                        td["data-label"] = heads[i]
        wrap = soup.new_tag("div", attrs={"class": "tbl-wrap"})
        t.wrap(wrap)

    for dv in soup.select("div.gl-entry"):
        dv.name = "dl"

    for a in soup.select("a.code-label[href]"):
        target = id_doc.get("code:" + a["href"])
        if target:
            a["href"] = target
    for s in soup.select("span.code-lines"):
        s.string = s.get_text().replace("in this PDF and the companion repository", "listed in Appendix B and in the companion repository")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#"):
            target = id_doc.get(href[1:])
            if target is None:
                problems.append(f"{doc.file}: link to missing id {href}")
            elif target != doc.file:
                a["href"] = f"{target}#{href[1:]}"

    for tag in soup.find_all(True):
        if tag.get("style") and "position:absolute" in tag["style"].replace(" ", ""):
            tag.decompose()

    body = soup.decode(formatter="minimal")
    if has_svg:
        body = sprite(doc.part) + "\n" + body
    return body, has_svg


def page_xhtml(doc, body):
    et = f' epub:type="{doc.epub_type}"' if doc.epub_type else ""
    cls = "cover-body" if doc.kind == "cover" else "ed-ebook"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        f'<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">\n'
        f'<head>\n<meta charset="utf-8"/>\n<title>{esc(doc.title)}</title>\n'
        '<link rel="stylesheet" type="text/css" href="../css/epub.css"/>\n</head>\n'
        f'<body class="{cls}"{et}>\n{body}\n</body>\n</html>\n'
    )


# --------------------------------------------------------------------------
# Appendix B: code files
# --------------------------------------------------------------------------
def code_documents(listings, attachments, chapter_titles, b):
    """Listings for every file that left its chapter, one document per chapter, plus the index document."""
    moved = [e for e in listings if not e["inline"]]
    by_ch = {}
    for e in moved:
        by_ch.setdefault(e["chapter"], []).append(e)
    docs, anchors = [], {}
    for ch in sorted(by_ch):
        parts = []
        for e in sorted(by_ch[ch], key=lambda x: x["path"]):
            aid = "code-" + slug(e["path"])
            anchors["code:" + e["url"]] = f"appendix-b-ch{ch}.xhtml#{aid}"
            anchors["id:" + aid] = f"appendix-b-ch{ch}.xhtml"
            text = attachments[e["path"]].decode("utf-8")
            note = f" · {esc(e['note'])}" if e["note"] else ""
            parts.append(
                f'<section class="code-listing" id="{aid}"><h2><code>{esc(e["path"])}</code></h2>'
                f'<p class="code-meta">{e["label"]} · {e["lines"]} lines{note}</p>'
                f'<div class="codeblock"><pre>{esc(text)}</pre></div></section>')
        title = chapter_titles.get(ch, ch)
        body = (f'<article class="chapter attached" data-ch="B" data-part="ref"><header class="appendix-head">'
                f'<p class="appendix-eyebrow">Appendix B · Chapter {ch}</p>'
                f'<h1 class="appendix-title" id="h-appendix-b-ch{ch}">Code files, Chapter {ch}</h1></header>'
                f'<p class="att-intro">{esc(title)}. {len(by_ch[ch])} listing{"" if len(by_ch[ch]) == 1 else "s"}.</p>'
                + "".join(parts) + "</article>")
        d = Doc(f"appendix-b-ch{ch}", f"Appendix B: code files, Chapter {ch}", body, kind="body", part="ref", epub_type="appendix")
        d.chapter = ch
        docs.append(d)
    return docs, anchors, by_ch


def code_index(listings, chapter_doc, anchors, n_moved):
    rows = []
    for e in sorted(listings, key=lambda x: (x["label"], x["path"])):
        moved = not e["inline"]
        aid = "code-" + slug(e["path"])
        if moved:
            link = f'<a href="appendix-b-ch{e["chapter"]}.xhtml#{aid}">{e["label"]}</a>'
            where = "listing in this appendix"
        else:
            link = f'<a href="{chapter_doc[e["chapter"]]}">{e["label"]}</a>'
            where = "shown in full in the chapter"
        note = f" · {esc(e['note'])}" if e["note"] else ""
        rows.append(f'<div class="att"><b class="att-label">{link}</b><span class="att-path">{esc(e["path"])}</span>'
                    f'<span class="att-meta">{e["lines"]} line{"" if e["lines"] == 1 else "s"}{note} · {where}</span></div>')
    repo = f'{b_REPO_URL}'
    intro = (
        f'<p class="att-intro">This index lists all {len(listings)} code files from the chapter walkthroughs. {n_moved} of them are longer than '
        "eight lines, so a chapter shows a one-line pointer instead of the code. Each of those files is listed in full in this appendix, "
        "one document per chapter, and the pointer in the chapter links to it. The shorter files stay in the chapter. "
        "The same files are in the companion repository, one folder per chapter. The repository address and the command that copies all of it:</p>"
        f'<pre class="att-code"><a href="{esc(repo)}">{esc(repo)}</a>\n{esc(b_CLONE_CMD)}</pre>'
        '<p class="att-intro">The chapters cite each code file by its label. Every source link in the book, by chapter and number, '
        "is also listed in the companion repository under sources/.</p>"
    )
    body = ('<article class="chapter attached" data-ch="B" data-part="ref" data-appendix="B"><header class="appendix-head">'
            '<p class="appendix-eyebrow">Appendix B</p><h1 class="appendix-title" id="h-appendix-b">Code files</h1></header>'
            f'<section>{intro}<div class="att-list">{"".join(rows)}</div></section></article>')
    return Doc("appendix-b", "Appendix B: code files", body, kind="body", part="ref", epub_type="appendix")


b_REPO_URL = ""
b_CLONE_CMD = ""


# --------------------------------------------------------------------------
# Package files
# --------------------------------------------------------------------------
def opf(identifier, modified, date, items, spine, nav_doc):
    man = []
    for item_id, href, media, props in items:
        p = f' properties="{props}"' if props else ""
        man.append(f'    <item id="{item_id}" href="{href}" media-type="{media}"{p}/>')
    sp = "\n".join(f'    <itemref idref="{i}"/>' for i in spine)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="en">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{identifier}</dc:identifier>
    <dc:title id="title-main">AI Memory</dc:title>
    <meta refines="#title-main" property="title-type">main</meta>
    <meta refines="#title-main" property="display-seq">1</meta>
    <dc:title id="title-sub">{esc(SUBTITLE)}</dc:title>
    <meta refines="#title-sub" property="title-type">subtitle</meta>
    <meta refines="#title-sub" property="display-seq">2</meta>
    <dc:creator id="creator">{esc(AUTHOR)}</dc:creator>
    <meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
    <meta refines="#creator" property="file-as">{esc(AUTHOR_SORT)}</meta>
    <dc:language>en</dc:language>
    <dc:date>{date}</dc:date>
    <meta property="dcterms:modified">{modified}</meta>
    <meta name="cover" content="cover-image"/>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessMode">visual</meta>
    <meta property="schema:accessModeSufficient">textual</meta>
    <meta property="schema:accessibilityFeature">structuralNavigation</meta>
    <meta property="schema:accessibilityFeature">tableOfContents</meta>
    <meta property="schema:accessibilityFeature">readingOrder</meta>
    <meta property="schema:accessibilityHazard">none</meta>
    <meta property="schema:accessibilitySummary">Reflowable text with a linked table of contents, chapter and section navigation, and linked citations. Diagrams are inline vector graphics with a text description in the label and the caption.</meta>
  </metadata>
  <manifest>
{chr(10).join(man)}
  </manifest>
  <spine toc="ncx">
{sp}
  </spine>
</package>
"""


def nav_xhtml(tree, landmarks, title):
    lm = "\n".join(f'      <li><a epub:type="{t}" href="{esc(h)}">{esc(n)}</a></li>' for t, h, n in landmarks)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        f'<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">\n'
        f'<head>\n<meta charset="utf-8"/>\n<title>{esc(title)}</title>\n'
        '<link rel="stylesheet" type="text/css" href="css/epub.css"/>\n</head>\n<body class="ed-ebook">\n'
        f'<nav epub:type="toc" id="toc" role="doc-toc">\n<h1>Contents</h1>\n{render_ol(tree, "text/")}\n</nav>\n'
        f'<nav epub:type="landmarks" id="landmarks" hidden="hidden">\n<h2>Landmarks</h2>\n    <ol>\n{lm}\n    </ol>\n</nav>\n'
        "</body>\n</html>\n"
    )


def ncx(identifier, tree):
    count = [0]

    def rec(nodes, ind):
        out = []
        for n in nodes:
            count[0] += 1
            pid = count[0]
            out.append(f'{ind}<navPoint id="np{pid}" playOrder="{pid}"><navLabel><text>{esc(n.title)}</text></navLabel>'
                       f'<content src="text/{esc(n.href())}"/>')
            out.extend(rec(n.children, ind + "  "))
            out.append(f"{ind}</navPoint>")
        return out

    points = "\n".join(rec(tree, "    "))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">
  <head>
    <meta name="dtb:uid" content="{identifier}"/>
    <meta name="dtb:depth" content="{depth(tree)}"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>AI Memory</text></docTitle>
  <navMap>
{points}
  </navMap>
</ncx>
"""


CONTAINER = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def write_zip(path, entries):
    """entries: [(name, bytes)]. mimetype first and stored; everything else deflated; fixed timestamps."""
    with zipfile.ZipFile(path, "w") as z:
        zi = zipfile.ZipInfo("mimetype", (1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, b"application/epub+zip")
        for name, data in entries:
            zi = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data, compresslevel=9)


# --------------------------------------------------------------------------
# Verification of the finished file against its own navigation
# --------------------------------------------------------------------------
def verify(path):
    problems = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if z.namelist()[0] != "mimetype" or z.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            problems.append("mimetype is not the first stored entry")
        pkg = BeautifulSoup(z.read("OEBPS/content.opf"), "html.parser")
        manifest = {i["id"]: i for i in pkg.find_all("item")}
        for i in manifest.values():
            if "OEBPS/" + i["href"] not in names:
                problems.append(f"manifest file missing: {i['href']}")
        spine = [manifest[r["idref"]]["href"] for r in pkg.find_all("itemref")]
        nav = BeautifulSoup(z.read("OEBPS/nav.xhtml"), "html.parser")
        toc = nav.find("nav", attrs={"epub:type": "toc"}) or nav.find("nav", id="toc")
        targets = [a["href"] for a in toc.find_all("a")]
        nav_docs = {t.split("#")[0] for t in targets}
        for t in targets:
            doc, _, frag = t.partition("#")
            if "OEBPS/" + doc not in names:
                problems.append(f"nav points at a missing file: {t}")
            elif frag and f'id="{frag}"' not in z.read("OEBPS/" + doc).decode("utf-8"):
                problems.append(f"nav fragment not found: {t}")
        for href in spine:
            if href not in nav_docs and not href.startswith("text/appendix-b-ch"):
                problems.append(f"spine document not in the navigation: {href}")
        chapters = sorted(re.findall(r"chapter-(\d\d)\.xhtml", " ".join(spine)))
        if chapters != [f"{i:02d}" for i in range(24)]:
            problems.append(f"chapter documents 00 to 23 expected, found {chapters}")
        props = [i for i in pkg.find_all("item") if i.get("properties") == "cover-image"]
        if len(props) != 1:
            problems.append("cover image is not declared exactly once")
    return problems, len(spine)


# --------------------------------------------------------------------------
# Kindle edition: diagrams as images
# --------------------------------------------------------------------------
# Kindle's converter rejects the book when a diagram relies on stylesheet rules or on
# markers defined in another <svg> ("SVG specified in the content is not renderable").
# For the Kindle file every diagram is drawn once by headless Chrome and stored as a PNG.
SVG_BLOCK = re.compile(r"<svg\b[^>]*>.*?</svg>", re.S)
RASTER_W = 1200


def rasterize_diagrams(entries, css_bytes):
    import shutil, subprocess, tempfile
    chrome = os.environ.get("CHROME", "/usr/bin/google-chrome")
    work = Path(tempfile.mkdtemp(prefix="epub-kindle-"))
    (work / "css").mkdir()
    (work / "text").mkdir()
    (work / "css" / "epub.css").write_bytes(css_bytes)
    images, out, n = [], [], 0
    try:
        for name, data in entries:
            text = data.decode("utf-8")
            sprites = [m.group(0) for m in SVG_BLOCK.finditer(text) if 'class="sprite"' in m.group(0)[:300]]

            def swap(m):
                nonlocal n
                svg = m.group(0)
                head = svg[: svg.index(">") + 1]
                if 'class="sprite"' in head:
                    return ""
                vb = re.search(r'viewBox="([\d.\s-]+)"', head)
                if not vb:
                    sys.exit(f"{name}: a diagram has no viewBox, cannot size its image")
                _, _, vw, vh = (float(x) for x in vb.group(1).split())
                height = int(round(RASTER_W * vh / vw))
                pad = int(round(height * 0.04))  # some diagrams draw a legend line just below the viewBox
                n += 1
                img = f"diagram-{n:03d}.png"
                page = work / "text" / f"d{n}.xhtml"
                page.write_text(
                    '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
                    f'<html xmlns="{XHTML_NS}"><head><meta charset="utf-8"/><title>d</title>'
                    '<link rel="stylesheet" type="text/css" href="../css/epub.css"/>'
                    f'<style>html,body{{margin:0;padding:0;background:#fff}}figure{{margin:0 !important;padding:0 !important;border:0 !important;width:{RASTER_W}px !important;max-width:none !important;background:#fff !important}}'
                    f'figure svg{{width:{RASTER_W}px !important;min-width:0 !important;max-width:none !important;height:{height}px !important;margin:0 !important;overflow:visible !important}}</style>'
                    f'</head><body class="ed-ebook">{"".join(sprites)}<figure class="diagram">{svg}</figure></body></html>',
                    encoding="utf-8")
                png = work / img
                prof = tempfile.mkdtemp(prefix="epub-chrome-")
                try:
                    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                                    f"--user-data-dir={prof}", f"--window-size={RASTER_W},{height + pad}",
                                    "--force-device-scale-factor=1", "--default-background-color=ffffffff",
                                    f"--screenshot={png}", page.as_uri()],
                                   check=True, capture_output=True, timeout=120,
                                   env={k: v for k, v in os.environ.items() if k != "DISPLAY"})
                finally:
                    shutil.rmtree(prof, ignore_errors=True)
                if not png.exists() or png.stat().st_size < 2000:
                    sys.exit(f"{name}: diagram {n} did not render")
                # Flat-colour line art: a 256-colour palette keeps it sharp at a fraction of the size,
                # which keeps the Kindle file in the lowest delivery-size tier.
                from PIL import Image
                Image.open(png).convert("RGB").quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(png, optimize=True)
                images.append((f"OEBPS/images/{img}", png.read_bytes()))
                label = re.search(r'aria-label="([^"]*)"', head)
                alt = label.group(1) if label else "Diagram"
                return f'<img class="diagram-img" src="../images/{img}" alt="{alt}" style="max-width:100%;height:auto"/>'

            out.append((name, SVG_BLOCK.sub(swap, text).encode("utf-8")))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out, images


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    global b_REPO_URL, b_CLONE_CMD
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default=str(DEFAULT_OUT))
    ap.add_argument("--kindle", action="store_true", help="store diagrams as PNG images, for Kindle upload")
    args = ap.parse_args()

    b = load_build()
    import listings as listing_mod
    b_REPO_URL, b_CLONE_CMD = listing_mod.REPO_URL, listing_mod.CLONE_CMD
    files, attachments, listings = load_book(b)

    used = set()
    for _, t in files:
        used.update(re.findall(r'\bid="([^"]+)"', t))
    docs, entries, ch_titles, chapter_doc = [], [], {}, {}
    front_facts = None
    for name, text in files:
        new, ents, meta = b.process_fragment(name, text, used)
        entries.extend(ents)
        if name == "00-front.html":
            secs = split_front(new)
            front_facts = cover_facts(secs["cover"])
            docs.append(Doc("cover", "Cover", "", kind="cover", epub_type="cover"))
            docs.append(Doc("titlepage", "Title page", title_page(front_facts), epub_type="titlepage"))
            docs.append(Doc("howto", "How to read this book", section_html(secs["howto"]), epub_type="preface"))
            nav_el = secs["toc"].find("nav", id="toc")
            nav_el.replace_with(BeautifulSoup('<div class="toc-book" id="toc-book">@@TOC@@</div>', "html.parser"))
            docs.append(Doc("contents", "Contents", section_html(secs["toc"]), epub_type="toc"))
        elif name.startswith("part-"):
            letter = re.search(r'data-part="([a-z]+)"', new).group(1)
            docs.append(Doc(f"part-{letter}", f"Part {letter.upper()}", new, part=letter, epub_type="part"))
        elif meta and meta["ch"] == "A":
            docs.append(Doc("appendix-a", "Appendix A: Glossary", new, part="ref", epub_type="glossary"))
        elif meta:
            ch = meta["ch"]
            t = re.search(r"<h1[^>]*>(.*?)</h1>", new, re.S)
            ttl = b.normalized_text(t.group(1)) if t else ch
            ch_titles[ch] = ttl
            chapter_doc[ch] = f"chapter-{ch}.xhtml#ch-{ch}"
            docs.append(Doc(f"chapter-{ch}", f"Chapter {ch}: {ttl}", new, part=meta["part"], epub_type="chapter"))
        else:
            sys.exit(f"{name}: unclassified fragment")
    if b.errors:
        sys.exit("\n".join(b.errors))
    # the in-book contents is generated below; Appendix B follows the glossary
    code_docs, anchors, by_ch = code_documents(listings, attachments, ch_titles, b)
    n_moved = sum(len(v) for v in by_ch.values())
    index_doc = code_index(listings, chapter_doc, anchors, n_moved)
    docs.append(index_doc)
    docs.extend(code_docs)

    # id -> file
    id_doc = {}
    for d in docs:
        for i in re.findall(r'\bid="([^"]+)"', d.body):
            id_doc.setdefault(i, d.file)
    id_doc.update(anchors)
    cover_img_doc = next(d for d in docs if d.kind == "cover")

    # navigation tree
    by_file = {d.file: d for d in docs}
    tree = []
    tree.append(Node("Cover", "cover.xhtml"))
    tree.append(Node("Title page", "titlepage.xhtml"))
    current_part, last_chapter = None, None
    for e in entries:
        target = id_doc.get(e["id"])
        if not target:
            continue
        kind = e["kind"]
        if kind == "front":
            tree.append(Node(e["title"], target, e["id"]))
            tree.append(Node("Contents", "contents.xhtml"))
        elif kind == "part":
            label = f"Appendix {e['appendix']}: {e['title']}" if e.get("appendix") else f"Part {e['part'].upper()}: {e['title']}"
            node = Node(label, target, e["id"], cls="toc-part")
            tree.append(node)
            current_part = None if e.get("appendix") else node
            last_chapter = None
        elif kind == "chapter":
            node = Node(f"Chapter {e['ch']}: {e['title']}", target, e["id"])
            (current_part.children if current_part else tree).append(node)
            last_chapter = node
        elif kind == "sec" and last_chapter:
            last_chapter.children.append(Node(e["title"], target, e["id"]))
    appx = next(n for n in tree if n.title.startswith("Appendix A"))
    b_node = Node("Appendix B: Code files", "appendix-b.xhtml", "h-appendix-b", cls="toc-part")
    for d in code_docs:
        b_node.children.append(Node(f"Chapter {d.chapter}: {ch_titles.get(d.chapter, '')}", d.file, f"h-appendix-b-ch{d.chapter}"))
    tree.append(b_node)

    problems = []
    contents_html = render_ol([n for n in tree if n.doc not in ("cover.xhtml", "titlepage.xhtml", "contents.xhtml")], "")
    contents = by_file["contents.xhtml"]
    contents.body = contents.body.replace("@@TOC@@", "\n" + contents_html + "\n")
    for d in docs:
        d.ids = set(re.findall(r'\bid="([^"]+)"', d.body))

    # convert and collect
    entries_out, manifest, spine = [], [], []
    has_svg = {}
    for d in docs:
        if d.kind == "cover":
            body = ('<section class="cover-page" epub:type="cover"><img src="../images/cover.jpg" '
                    f'alt="AI Memory, {esc(SUBTITLE)}, by {esc(AUTHOR)}"/></section>')
            svg = False
        else:
            body, svg = convert(d, id_doc, problems)
        has_svg[d.file] = svg
        entries_out.append((f"OEBPS/text/{d.file}", page_xhtml(d, body).encode("utf-8")))
    if problems:
        sys.exit("\n".join(problems))

    css = CSS_SRC.read_bytes()
    diagram_images = []
    if args.kindle:
        entries_out, diagram_images = rasterize_diagrams(entries_out, css)
        has_svg = {k: False for k in has_svg}
    cover_bytes = COVER_SRC.read_bytes()
    stamp_src = [CSS_SRC, COVER_SRC, HERE / "make-epub.py"] + list(b.CHAPTERS.glob("*.html")) + [HERE / n for n in ("build.py", "listings.py", "make-dividers.py")]
    mtime = max(int(p.stat().st_mtime) for p in stamp_src)
    modified = __import__("datetime").datetime.fromtimestamp(mtime, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    identifier = "urn:uuid:" + str(uuid.uuid5(ID_NAMESPACE, "ai-memory-building-an-llm-brain"))

    items = [("ncx", "toc.ncx", "application/x-dtbncx+xml", ""),
             ("nav", "nav.xhtml", "application/xhtml+xml", "nav"),
             ("css", "css/epub.css", "text/css", ""),
             ("cover-image", "images/cover.jpg", "image/jpeg", "cover-image")]
    for path, _ in diagram_images:
        stem = Path(path).stem
        items.append((stem, f"images/{Path(path).name}", "image/png", ""))
    spine_ids = []
    for d in docs:
        items.append((f"d-{d.stem}", f"text/{d.file}", "application/xhtml+xml", "svg" if has_svg[d.file] else ""))
        spine_ids.append(f"d-{d.stem}")

    first_chapter = next(d for d in docs if d.stem == "chapter-00")
    landmarks = [("cover", "text/cover.xhtml", "Cover"), ("toc", "text/contents.xhtml", "Contents"),
                 ("bodymatter", f"text/{first_chapter.file}", "Start of the book")]
    out = [
        ("META-INF/container.xml", CONTAINER.encode()),
        ("OEBPS/content.opf", opf(identifier, modified, pub_date(front_facts["date"]), items, spine_ids, None).encode()),
        ("OEBPS/nav.xhtml", nav_xhtml(tree, landmarks, "Contents").encode()),
        ("OEBPS/toc.ncx", ncx(identifier, tree).encode()),
        ("OEBPS/css/epub.css", css),
        ("OEBPS/images/cover.jpg", cover_bytes),
    ] + entries_out + diagram_images
    out.sort(key=lambda kv: kv[0])
    target = Path(args.output)
    write_zip(target, out)

    issues, n_docs = verify(target)
    size = target.stat().st_size
    print(f"wrote {target} ({size / 1e6:.2f} MB), {n_docs} documents in the reading order, {n_moved} code listings")
    for p in issues:
        print(f"error: {p}", file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
