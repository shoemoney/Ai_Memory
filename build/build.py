#!/usr/bin/env python3
"""Build the guide: lint chapter fragments, assemble guide.html, render the PDF.

Pipeline
  1. read and lint build/chapters/*.html, then order chapters and appendices
  2. give every h1/h2 an id, build the table of contents, generate the per-chapter
     running headers (CSS named pages)
  3. render with headless Chrome, read the real page of every heading from the
     PDF link destinations, write those page numbers into the contents, render again
  4. check the PDF: contents numbers match, no blank pages, nothing outside the margins

Environment: EDITION=ebook (default), print (8.5 x 11 in paperback) or hardcover (8.25 x 11 in) selects the edition; overrides used for testing:
GUIDE_CHAPTERS, GUIDE_HTML, GUIDE_PDF, GUIDE_RELOCATE, GUIDE_LISTING_LINES, CHROME.
Exit code is non-zero on any lint error, render failure or layout check failure.
"""
import base64
import html
import json
import runpy
from listings import relocate, normalized_text, MAP_FILES, present_maps, write_manifest, lint_citations as lint_chapter_citations
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import pymupdf
except ImportError:  # older PyMuPDF
    import fitz as pymupdf

HERE = Path(__file__).resolve().parent
CHAPTERS = Path(os.environ.get("GUIDE_CHAPTERS", HERE / "chapters"))
EDITION = os.environ.get("EDITION", "ebook")
if EDITION not in ("ebook", "print", "hardcover"):
    sys.exit(f"EDITION must be ebook, print or hardcover, got {EDITION!r}")
_SUFFIX = "" if EDITION == "ebook" else f"-{EDITION}"
BODY_CLASS = {"ebook": "ed-ebook", "print": "ed-print", "hardcover": "ed-print ed-hardcover"}[EDITION]
HARDCOVER_CSS_FILE = HERE / "guide-hardcover.css"
OUT_HTML = Path(os.environ.get("GUIDE_HTML", HERE / f"guide{_SUFFIX}.html"))
OUT_PDF = Path(os.environ.get("GUIDE_PDF", HERE / f"ai-memory-guide{_SUFFIX}.pdf"))
MANIFEST = HERE / "listings-manifest.json"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
CSS_FILE = HERE / "guide.css"
TITLE = "AI Memory"
PAGE_TOP_IN, PAGE_BOTTOM_IN = 0.75, 0.8  # keep in step with @page in guide.css
COVER_IMG = re.compile(r"^cover-art/[\w.-]+\.jpg$")

errors: list[str] = []
warnings: list[str] = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def lineno(text, pos):
    return text.count("\n", 0, pos) + 1


# --------------------------------------------------------------------------
# Lint
# --------------------------------------------------------------------------
ATTRIBUTION = re.compile(
    r"\b(generated|written|authored|prepared|created|compiled|produced|drafted)\s+(by|with|using)\b",
    re.I,
)


def count_cols(row_html):
    n = 0
    for m in re.finditer(r"<(t[hd])\b([^>]*)>", row_html, re.I):
        c = re.search(r'colspan=["\']?(\d+)', m.group(2))
        n += int(c.group(1)) if c else 1
    return n


COVER_BYLINE = "Written By Jeremy Schoemaker"


def lint_fragment(name, text, all_ids):
    scan = text
    if name == "00-front.html":
        # The owner's byline is allowed, once, inside the cover element only.
        cm = re.search(r'<section class="cover"[^>]*>.*?</section>', text, re.S)
        if cm and cm.group(0).count(COVER_BYLINE) == 1:
            scan = text[:cm.start()] + cm.group(0).replace(COVER_BYLINE, "x" * len(COVER_BYLINE)) + text[cm.end():]
    if re.search(r'<article class="chapter[^"]*\bcompact\d?\b', text):
        err(f"{name}: compact classes are set by the build (choose_compaction), remove them from the article")
    if "\u2014" in text:
        err(f"{name}:{lineno(text, text.index(chr(0x2014)))}: em dash found, rewrite the sentence")
    m = ATTRIBUTION.search(scan)
    if m:
        err(f"{name}:{lineno(text, m.start())}: authorship phrase '{m.group(0)}' is not allowed")
    if re.search(r"<\s*(html|head|body)\b", text, re.I):
        err(f"{name}: fragment must not contain html, head or body tags")
    if re.search(r"<\s*script\b", text, re.I):
        err(f"{name}: scripts are not allowed")
    if re.search(r"<\s*link\b|@import|url\(\s*['\"]?https?:|<\s*img\b[^>]*src=['\"]?https?:", text, re.I):
        err(f"{name}: external resource reference (no network at render time)")
    imgs = re.findall(r"<\s*img\b[^>]*>", text, re.I)
    for tag in imgs:
        src = re.search(r'src="([^"]*)"', tag)
        if name != "00-front.html" or not src or not COVER_IMG.match(src.group(1)):
            err(f"{name}: <img> is only allowed for the cover image (src cover-art/NAME.jpg in 00-front.html)")
        elif not (HERE / src.group(1)).exists():
            err(f"{name}: cover image {src.group(1)} does not exist (run make-cover.py)")
    if len(imgs) > 1:
        err(f"{name}: only one <img> (the cover) is allowed")
    if re.search(r"\bstyle=", text):
        warn(f"{name}: inline style attribute used; prefer a component class")

    for m in re.finditer(r"<table\b([^>]*)>(.*?)</table>", text, re.S | re.I):
        first_row = re.search(r"<tr\b[^>]*>(.*?)</tr>", m.group(2), re.S | re.I)
        if first_row:
            cols = count_cols(first_row.group(1))
            limit = 7 if "matrix" in m.group(1) else 5
            if cols > limit:
                err(f"{name}:{lineno(text, m.start())}: table has {cols} columns (max {limit})")
        if "legend" not in m.group(1) and not re.search(r"<thead\b", m.group(2), re.I):
            err(f"{name}:{lineno(text, m.start())}: table needs a <thead> so the header repeats across pages")

    for m in re.finditer(r"<pre\b[^>]*>(.*?)</pre>", text, re.S | re.I):
        body = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        for i, line in enumerate(body.split("\n")):
            if len(line) > 100:
                err(f"{name}:{lineno(text, m.start()) + i}: code line is {len(line)} chars (max 100, aim for 88)")
            elif len(line) > 88:
                warn(f"{name}:{lineno(text, m.start()) + i}: code line is {len(line)} chars (aim for 88)")

    for m in re.finditer(r'\bid="([^"]+)"', text):
        if m.group(1) in all_ids:
            err(f"{name}: duplicate id '{m.group(1)}' (also in {all_ids[m.group(1)]})")
        all_ids[m.group(1)] = name


def lint_citations(files):
    lint_chapter_citations(files, err, warn)


# --------------------------------------------------------------------------
# Assemble
# --------------------------------------------------------------------------
def slug(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", html.unescape(s).lower()).strip("-")
    return s[:40] or "x"


HEAD_RE = re.compile(r"<(h[123])\b([^>]*)>(.*?)</\1>", re.S | re.I)
ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')


def attrs(s):
    return dict(ATTR_RE.findall(s))


COMPACT: dict[str, int] = {}  # chapter file name -> compaction level (0 to MAX_COMPACT), chosen by choose_compaction()
MAX_COMPACT = 4
SPLIT_LINES = 5  # a code block of more than this many lines may split across pages (3 lines stay on each side)
TALL_CARD_CHARS = 700  # a use-case card with more text than this (about a third of a page) may split between its rows


def auto_split(text):
    """Let tall code blocks (and the step that holds them) split across pages.

    Short blocks stay whole. A block over SPLIT_LINES lines gets `splittable`, and the
    ordered-list step around it gets `step-long`, so a long block never leaves half a page empty.
    """
    def fix_block(m):
        block = m.group(0)
        pre = re.search(r"<pre\b[^>]*>(.*?)</pre>", block, re.S | re.I)
        lines = pre.group(1).count("\n") + 1 if pre else 0
        if lines > SPLIT_LINES and "splittable" not in block:
            block = block.replace('class="codeblock', 'class="codeblock splittable', 1)
        return block

    text = re.sub(r'<div class="codeblock[^"]*">.*?</pre>\s*</div>', fix_block, text, flags=re.S)

    def fix_card(m):
        card = m.group(0)
        plain = html.unescape(re.sub(r"<[^>]+>", "", card))
        if len(plain) > TALL_CARD_CHARS:
            card = card.replace('class="ucase"', 'class="ucase ucase-tall"', 1)
        return card

    text = re.sub(r'<article class="ucase">.*?</article>', fix_card, text, flags=re.S)

    def fix_step(m):
        step = m.group(0)
        if "splittable" in step and "step-long" not in step:
            step = step.replace("<li", '<li class="step-long"', 1) if "<li>" == step[:4] else step.replace("<li ", '<li class="step-long" ', 1) if 'class=' not in step[:30] else step.replace('class="', 'class="step-long ', 1)
        return step

    return re.sub(r"<li\b[^>]*>\s*<p class=\"step-title\">.*?</li>", fix_step, text, flags=re.S)


def process_fragment(name, text, used_ids):
    """Return (new_text, toc_entries, chapter_meta or None)."""
    text = auto_split(text)
    root = re.search(r"<(article|section)\b([^>]*)>", text)
    if not root:
        err(f"{name}: fragment must start with an <article> or <section> root element")
        return text, [], None
    rattrs = attrs(root.group(2))
    classes = rattrs.get("class", "").split()
    meta = None
    in_chapter = "chapter" in classes
    ch = rattrs.get("data-ch")
    part = rattrs.get("data-part", "")
    appendix = rattrs.get("data-appendix", "")
    if in_chapter:
        for req in ("data-ch", "data-part", "data-running"):
            if not rattrs.get(req):
                err(f"{name}: chapter root needs {req}")
        if ch and not re.fullmatch(r"\d{2}|A|B", ch):
            err(f"{name}: data-ch must be two digits")
        meta = {"ch": ch, "part": part, "running": rattrs.get("data-running", ""), "file": name}
        if ch and "id" not in rattrs:  # anchor for cross-references such as href="#ch-05"
            tagged = root.group(0)[:-1] + f' id="ch-{ch}">'
            text = text.replace(root.group(0), tagged, 1)
            root = re.search(r"<(article|section)\b([^>]*)>", text)
    entries = []
    prefix = re.sub(r"\.html$", "", name)
    if in_chapter and COMPACT.get(name):
        cls_attr = re.search(r'class="([^"]*)"', root.group(2))
        old = root.group(0)
        level = COMPACT[name]
        added = " ".join(["compact"] + [f"compact{i}" for i in range(2, level + 1)])
        new_root = old.replace(cls_attr.group(0), f'class="{cls_attr.group(1)} {added}"', 1)
        text = text.replace(old, new_root, 1)

    def repl(m):
        tag, a, inner = m.group(1).lower(), m.group(2), m.group(3)
        at = attrs(a)
        cls = at.get("class", "").split()
        title = normalized_text(inner)
        hid = at.get("id")
        wanted = False
        kind = None
        if "no-toc" in cls:
            pass
        elif tag == "h1" and "part-title" in cls:
            kind = "part"
        elif tag == "h1" and "appendix-title" in cls:
            kind = "part"
        elif tag == "h1" and in_chapter:
            kind = "chapter"
        elif tag == "h1" and "front-title" in cls:
            kind = "front"
        elif tag == "h2" and in_chapter:
            kind = "sec"
        if kind:
            wanted = True
        if wanted and not hid:
            base = f"h-{prefix}-{slug(title)}"
            hid = base
            n = 2
            while hid in used_ids:
                hid = f"{base}-{n}"
                n += 1
            a = f'{a} id="{hid}"'
        if hid:
            used_ids.add(hid)
        if wanted:
            entries.append({"kind": kind, "id": hid, "title": title, "ch": ch, "part": part, "appendix": appendix, "file": name})
        return f"<{m.group(1)}{a}>{inner}</{m.group(1)}>"

    new = HEAD_RE.sub(repl, text)
    return new, entries, meta


def toc_html(entries, pages):
    def pg(e):
        return str(pages[e["id"]]) if pages else "00"

    out = ['<div class="toc">']
    i = 0
    while i < len(entries):
        e = entries[i]
        if e["kind"] == "part":
            out.append(
                f'<a class="toc-part" data-part="{e["part"]}" href="#{e["id"]}"><span>{"Appendix " + e["appendix"] if e.get("appendix") else "Part " + e["part"].upper()}</span>'
                f'<span>{html.escape(e["title"])}</span><span class="pg">{pg(e)}</span></a>'
            )
        elif e["kind"] == "front":
            out.append(
                f'<div class="toc-chapter toc-front"><a class="toc-row ch" href="#{e["id"]}"><span class="num"></span>'
                f'<span class="t">{html.escape(e["title"])}</span><span class="fill"></span><span class="pg">{pg(e)}</span></a></div>'
            )
        elif e["kind"] == "chapter":
            secs = []
            j = i + 1
            while j < len(entries) and entries[j]["kind"] == "sec":
                secs.append(entries[j])
                j += 1
            out.append(f'<div class="toc-chapter" data-part="{e["part"]}">')
            out.append(
                f'<a class="toc-row ch" href="#{e["id"]}"><span class="num">{e["ch"]}</span>'
                f'<span class="t">{html.escape(e["title"])}</span><span class="fill"></span><span class="pg">{pg(e)}</span></a>'
            )
            if secs:
                out.append('<div class="toc-secs">')
                for s in secs:
                    out.append(
                        f'<a class="toc-row" href="#{s["id"]}"><span class="t">{html.escape(s["title"])}</span>'
                        f'<span class="fill"></span><span class="pg">{pg(s)}</span></a>'
                    )
                out.append("</div>")
            out.append("</div>")
            i = j - 1
        i += 1
    out.append("</div>")
    return "\n".join(out)


def css_str(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def running_css(metas):
    css = CSS_FILE.read_text()
    colors = dict(re.findall(r"--part-([a-z]+):\s*(#[0-9a-fA-F]{6})", css))
    rules = []
    for m in metas:
        color = colors.get(m["part"])
        if not color:
            err(f"{m['file']}: unknown part '{m['part']}' (use a to g)")
            continue
        label = css_str(f"{'Appendix ' + m['ch'] if m['ch'].isalpha() else m['ch']}  \\00B7  {m['running']}").replace("\\\\00B7", "\\00B7")
        box = (
            f'content: "{label}"; font: 600 7.5pt "Inter", sans-serif; letter-spacing: .1em; '
            f"text-transform: uppercase; color: {color}; vertical-align: bottom; padding-bottom: 16pt;"
        )
        n = m["ch"]
        rules.append(f"@page ch-{n}:left {{ @top-left {{ {box} }} }}")
        rules.append(f"@page ch-{n}:right {{ @top-right {{ {box} }} }}")
        rules.append(f'.chapter[data-ch="{n}"] {{ page: ch-{n}; }}')
    return "\n".join(rules)


SPRITE = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
    '<marker id="arr" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0 0.5L10 5L0 9.5z" style="fill:context-stroke"/></marker>'
    "</defs></svg>"
)


def embed_image(rel):
    """Inline the cover JPEG as a data URI so the render needs no file or network access."""
    data = (HERE / rel).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


SRC_LI = re.compile(r'(<li\b[^>]*>)(.*?)</li>', re.S)
SRC_URL = re.compile(r'\s*<a class="url" href="([^"]+)">[^<]*</a>')
SRC_TITLE = re.compile(r'<span class="src-title">.*?</span>', re.S)
PRINT_URL_TEXT = re.compile(r'(<a class="url" href="[^"]+">)https://')
ED_BLOCK = re.compile(r"<!--ed:(ebook|print)-->(.*?)<!--/ed-->", re.S)


def pick_edition(text):
    """Keep the text written for this edition and drop the other's (<!--ed:print-->...<!--/ed-->)."""
    text = ED_BLOCK.sub(lambda m: m.group(2) if m.group(1) == ("ebook" if EDITION == "ebook" else "print") else "", text)
    if EDITION != "ebook":
        # Print editions show source addresses without the scheme: shorter lines, same address.
        text = PRINT_URL_TEXT.sub(r"\1", text)
    return text


def link_sources(text):
    """Ebook: the source title is the link and the URL is not printed. The chapter file keeps both.

    A source with several URLs links its title to the first and adds a small "link 2" link for each other.
    """
    if EDITION != "ebook" or os.environ.get("GUIDE_SOURCE_URLS"):  # the env var is a measurement hook only
        return text

    def one_list(m):
        def one_item(li):
            urls = SRC_URL.findall(li.group(2))
            title = SRC_TITLE.search(li.group(2))
            if not urls:
                return li.group(0)
            body = SRC_URL.sub("", li.group(2))
            if title:
                body = body.replace(title.group(0), f'<a class="src-link" href="{urls[0]}">{title.group(0)}</a>', 1)
            else:  # a source written as plain text: link all of it
                body = f'<a class="src-link" href="{urls[0]}"><span class="src-title">{body.strip()}</span></a>'
            more = "".join(f' <a class="src-more" href="{u}">link {i}</a>' for i, u in enumerate(urls[1:], 2))
            return f"{li.group(1)}{body}{more}</li>"
        return SRC_LI.sub(one_item, m.group(0))

    return re.sub(r'<ol class="sources-list".*?</ol>', one_list, text, flags=re.S)


FONT_DIRS = [Path("/usr/share/fonts/opentype/urw-base35"), Path("/usr/share/fonts/opentype/inter")]
TTF_DIR = HERE / "fonts-ttf"
WEIGHTS = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400, "Roman": 400, "Medium": 500,
           "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900}
FAMILIES = {"P052": "P052", "Inter": "Inter", "InterDisplay": "Inter Display"}


def font_faces():
    """(family, weight, italic, source otf) for the fonts guide.css names, read from the system font folders."""
    out = []
    for d in FONT_DIRS:
        for f in sorted(d.glob("*.otf")):
            fam, _, style = f.stem.partition("-")
            if fam not in FAMILIES:
                continue
            italic = style.endswith("Italic")
            name = style[:-len("Italic")] if italic else style
            name = name or "Regular"
            if name in WEIGHTS:
                out.append((FAMILIES[fam], WEIGHTS[name], italic, f))
    return out


def otf_to_ttf(src, dst):
    """CFF OpenType to TrueType outlines. Chrome writes CFF fonts into a PDF as Type3 glyph procedures; TrueType
    fonts it embeds as real font subsets, which is what the print service's preflight wants."""
    from fontTools.ttLib import TTFont, newTable
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    font = TTFont(str(src))
    order = font.getGlyphOrder()
    gs = font.getGlyphSet()
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
        glyphs[name] = pen.glyph()
    font["loca"] = newTable("loca")
    font["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = order
    glyf.glyphs = glyphs
    del font["CFF "]
    if "VORG" in font:
        del font["VORG"]
    glyf.compile(font)
    hmtx = font["hmtx"]
    for name in order:
        adv, _ = hmtx[name]
        g = glyf[name]
        hmtx[name] = (adv, g.xMin if g.numberOfContours else 0)
    font["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.maxZones, maxp.maxTwilightPoints, maxp.maxStorage = 1, 0, 0
    maxp.maxFunctionDefs = maxp.maxInstructionDefs = maxp.maxStackElements = maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = max((len(getattr(g, "components", [])) for g in glyphs.values()), default=0)
    maxp.numGlyphs = len(order)
    font["head"].glyphDataFormat = 0
    post = font["post"]
    post.formatType = 2.0
    post.extraNames, post.mapping, post.glyphOrder = [], {}, order
    font.sfntVersion = "\000\001\000\000"
    font.save(str(dst))


def print_fonts_css():
    """Print editions only: @font-face rules for TrueType copies of the book's fonts (made once into fonts-ttf/)."""
    if EDITION == "ebook":
        return ""
    TTF_DIR.mkdir(exist_ok=True)
    rules = []
    for fam, weight, italic, src in font_faces():
        dst = TTF_DIR / (src.stem + ".ttf")
        if not dst.exists():
            try:
                otf_to_ttf(src, dst)
            except ImportError:
                err("fontTools is needed once to make build/fonts-ttf (pip install fonttools), or copy that folder in")
                return ""
        rules.append(f'@font-face {{ font-family: "{fam}"; font-weight: {weight}; '
                     f'font-style: {"italic" if italic else "normal"}; src: url("fonts-ttf/{dst.name}") format("truetype"); }}')
    return "\n<style id=\"print-fonts\">\n" + "\n".join(rules) + "\n</style>"


OUTLINE_JSON = HERE / "glyph-outlines.json"
OUTLINE_FONTS = {800: "InterDisplay-ExtraBold", 900: "InterDisplay-Black"}


def glyph_outlines(chars):
    """SVG path data, advance and vertical metrics per font weight for the characters the outlined display text uses.

    Chrome writes stroked text (-webkit-text-stroke) into the PDF as a Type3 font, so the print editions draw the big
    outlined chapter numerals and part letters as vector outlines instead. Cached in glyph-outlines.json.
    """
    cache = json.loads(OUTLINE_JSON.read_text()) if OUTLINE_JSON.exists() else {}
    missing = [(w, c) for w in OUTLINE_FONTS for c in chars if c not in cache.get(str(w), {}).get("glyphs", {})]
    if missing:
        try:
            from fontTools.ttLib import TTFont
            from fontTools.pens.svgPathPen import SVGPathPen
        except ImportError:
            err("fontTools is needed once to make build/glyph-outlines.json (pip install fonttools), or copy that file in")
            return cache
        for w, name in OUTLINE_FONTS.items():
            f = TTFont(str(TTF_DIR / (name + ".ttf")))
            gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
            ent = cache.setdefault(str(w), {"glyphs": {}})
            ent.update(upm=f["head"].unitsPerEm, asc=f["hhea"].ascent, desc=-f["hhea"].descent)
            for c in set(chars) | set(ent["glyphs"]):
                pen = SVGPathPen(gs)
                gs[cmap[ord(c)]].draw(pen)
                ent["glyphs"][c] = {"d": pen.getCommands(), "adv": hmtx[cmap[ord(c)]][0]}
        OUTLINE_JSON.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return cache


def outline_svg(text, weight, size_pt, spacing_em, line_height, stroke_pt):
    """Inline SVG of text as outlines, laid out like the CSS box (letter-spacing after every character)."""
    ent = glyph_outlines(set(text)).get(str(weight))
    if not ent or any(c not in ent["glyphs"] for c in text):
        return None
    k = size_pt / ent["upm"]
    x, paths = 0.0, []
    for c in text:
        g = ent["glyphs"][c]
        paths.append(f'<path transform="translate({x:.2f} {{b:.2f}}) scale({k:.6f} {-k:.6f})" stroke-width="{stroke_pt / k:.1f}" d="{g["d"]}"/>')
        x += g["adv"] * k + spacing_em * size_pt
    box_h = size_pt * line_height
    base = (box_h - (ent["asc"] + ent["desc"]) * k) / 2 + ent["asc"] * k
    body = "".join(paths).replace("{b:.2f}", f"{base:.2f}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x:.2f}pt" height="{box_h:.2f}pt" '
            f'viewBox="0 0 {x:.2f} {box_h:.2f}" style="display:block;overflow:visible">{body}</svg>')


OPENER_NUM = re.compile(r'<div (?:class="opener-num" aria-hidden="true"|aria-hidden="true" class="opener-num")>(\d\d)</div>')
PART_LETTER = re.compile(r'<div (?:class="part-letter" aria-hidden="true"|aria-hidden="true" class="part-letter")>([A-Z])</div>')


def print_outlines(text):
    """Print editions: replace the stroked display text (chapter numerals, part letters) with vector outlines."""
    if EDITION == "ebook":
        return text

    def num(m):
        svg = outline_svg(m.group(1), 800, 96, -0.04, 0.82, 1.1)
        return f'<div class="opener-num" aria-hidden="true">{svg}</div>' if svg else m.group(0)

    def letter(m):
        svg = outline_svg(m.group(1), 900, 300, 0, 1, 2.5)
        return f'<div class="part-letter" aria-hidden="true">{svg}</div>' if svg else m.group(0)

    return PART_LETTER.sub(letter, OPENER_NUM.sub(num, text))


COVER_SECTION = re.compile(r'<section class="cover" id="cover">.*?</section>', re.S)
TITLE_PAGE = (
    '<section class="titlepage" id="cover">'
    '<p class="tp-title"><span class="ai">AI</span> Memory</p>'
    '<p class="tp-sub">Building an LLM brain</p>'
    '<p class="tp-by">Written By Jeremy Schoemaker</p>'
    '<p class="tp-author">Author of AiBook</p>'
    '<p class="tp-date">Sources checked to 22 November 2026 · Labs rerun to 23 November 2026</p>'
    '</section>'
)


def print_titlepage(text):
    """Print editions: a typeset title page replaces the cover image, which is the printed cover's job."""
    return COVER_SECTION.sub(lambda _m: TITLE_PAGE, text, count=1) if EDITION != "ebook" else text



def hardcover_style():
    """Hardcover only: the 8.25 in trim and the full-bleed pages sized to it. Other editions get nothing."""
    if EDITION != "hardcover":
        return ""
    return f'\n<style id="hardcover">\n{HARDCOVER_CSS_FILE.read_text()}</style>'


def assemble(files, pages):
    files, _, _ = relocate(files, pages, enabled=os.environ.get("GUIDE_RELOCATE", "1") != "0", edition="ebook" if EDITION == "ebook" else "print")
    files = [(n, print_outlines(print_titlepage(link_sources(t)))) for n, t in files]
    used_ids: set[str] = set()
    for _, t in files:
        used_ids.update(re.findall(r'\bid="([^"]+)"', t))
    bodies, entries, metas = [], [], []
    for name, text in files:
        new, ents, meta = process_fragment(name, text, used_ids)
        bodies.append(new)
        entries.extend(ents)
        if meta:
            metas.append(meta)
    seen = set()
    for m in metas:
        if m["ch"] in seen:
            err(f"duplicate chapter number {m['ch']}")
        seen.add(m["ch"])
    body = "\n".join(bodies)
    for m in re.finditer(r'href="#ch-(\d+)"', body):
        if m.group(1) not in seen:
            err(f"cross-reference to chapter {m.group(1)} has no chapter")
    body = re.sub(r'src="(cover-art/[\w.-]+\.jpg)"', lambda m: f'src="{embed_image(m.group(1))}"', body)
    if '<nav id="toc"' not in body and "<nav id='toc'" not in body:
        err("00-front.html must contain <nav id=\"toc\"></nav>")
    body = re.sub(r'<nav id="toc"[^>]*>\s*</nav>', lambda _m: toc_html(entries, pages), body, count=1)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{TITLE}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="guide.css">
<style id="running-headers">
{running_css(metas)}
</style>{print_fonts_css()}{hardcover_style()}
</head>
<body class="{BODY_CLASS}">
{SPRITE}
{body}
</body>
</html>
"""
    return doc, entries


# --------------------------------------------------------------------------
# Render and verify
# --------------------------------------------------------------------------
def render(html_path, pdf_path):
    if not Path(CHROME).exists():
        err(f"Chrome not found at {CHROME}")
        return False
    prof = tempfile.mkdtemp(prefix="guide-chrome-")
    try:
        if pdf_path.exists():
            pdf_path.unlink()
        cmd = [
            CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
            f"--user-data-dir={prof}", "--no-pdf-header-footer", "--generate-pdf-document-outline",
            "--run-all-compositor-stages-before-draw", "--disable-extensions", "--no-first-run",
            f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri(),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if r.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size < 2000:
            err(f"Chrome failed (exit {r.returncode}): {r.stderr.strip()[-400:]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        err("Chrome timed out")
        return False
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def link_pages(pdf_path):
    doc = pymupdf.open(str(pdf_path))
    dest = {}
    for p in doc:
        for l in p.get_links():
            nd = l.get("nameddest")
            if nd and "page" in l:
                dest.setdefault(nd, l["page"] + 1)
    n = len(doc)
    doc.close()
    return dest, n


def check_pdf(pdf_path):
    doc = pymupdf.open(str(pdf_path))
    notes = []
    for idx, page in enumerate(doc):
        num = idx + 1
        rect = page.rect
        full_bleed = any(i["bbox"][2] - i["bbox"][0] > 0.9 * rect.width and i["bbox"][3] - i["bbox"][1] > 0.9 * rect.height
                         for i in page.get_image_info())
        for d in page.get_drawings():
            r = d.get("rect")
            if r and r.width * r.height > 0.9 * rect.width * rect.height and d.get("fill"):
                full_bleed = True
                break
        if full_bleed:
            continue
        right_page = num % 2 == 1
        left_edge = (0.9 if right_page else 0.7) * 72 - 3
        right_edge = rect.width - (0.7 if right_page else 0.9) * 72 + 3
        top, bottom = PAGE_TOP_IN * 72 - 4, rect.height - PAGE_BOTTOM_IN * 72 + 4
        body_text = 0
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for sp in line["spans"]:
                    x0, y0, x1, y1 = sp["bbox"]
                    if not sp["text"].strip():
                        continue
                    if y0 >= top and y1 <= bottom:
                        body_text += len(sp["text"].strip())
                        if x1 > right_edge or x0 < left_edge:
                            notes.append(f"page {num}: text outside margins at x={x0:.0f}..{x1:.0f}: '{sp['text'][:40]}'")
        if body_text < 15 and len(page.get_drawings()) < 3:
            notes.append(f"page {num}: looks blank")
    doc.close()
    return notes


def chapter_pages(pdf_path, entries):
    """Pages used by each compactable chapter: {file name: pages}, from the heading destinations in the PDF."""
    dest, total = link_pages(pdf_path)
    starts = [(dest[e["id"]], e) for e in entries if e["kind"] in ("chapter", "part", "front") and e["id"] in dest]
    out = {}
    for i, (pg, e) in enumerate(starts):
        if e["kind"] == "chapter" and not e.get("appendix"):
            end = starts[i + 1][0] if i + 1 < len(starts) else total + 1
            out[e["file"]] = end - pg
    return out


def compactable(files):
    """File names of numbered chapters: the only ones the build may tighten."""
    out = []
    for name, text in files:
        root = re.search(r"<(article|section)\b([^>]*)>", text)
        if root and "chapter" in attrs(root.group(2)).get("class", "").split() and not attrs(root.group(2)).get("data-appendix"):
            out.append(name)
    return out


def choose_compaction(files):
    """Single owner of the compact classes: pick each chapter's lowest spacing level that gives its fewest pages.

    Chapters start on new pages, so they do not affect each other. The whole book is rendered once at each level
    (0 to MAX_COMPACT), and every chapter takes the lowest level that reaches its smallest page count. A chapter
    that no level shortens keeps level 0. GUIDE_COMPACT=N forces level N for every chapter (a measurement hook).
    """
    names = compactable(files)
    forced = os.environ.get("GUIDE_COMPACT", "auto")
    if forced != "auto":
        COMPACT.clear()
        COMPACT.update({n: int(forced) for n in names} if int(forced) else {})
        print(f"compact spacing forced to level {forced}")
        return True
    counts = {}
    for level in range(MAX_COMPACT + 1):
        COMPACT.clear()
        COMPACT.update({n: level for n in names} if level else {})
        doc, entries = assemble(files, None)
        if errors:
            return False
        OUT_HTML.write_text(doc, encoding="utf-8")
        if not render(OUT_HTML, OUT_PDF):
            return False
        counts[level] = chapter_pages(OUT_PDF, entries)
    COMPACT.clear()
    for n in names:
        best = min(counts[l][n] for l in counts)
        level = next(l for l in sorted(counts) if counts[l][n] == best)
        if level:
            COMPACT[n] = level
    saved = sum(counts[0][n] - min(counts[l][n] for l in counts) for n in names)
    print("compact spacing: " + (", ".join(f"{n[:2]}:{l}" for n, l in sorted(COMPACT.items())) or "none") + f" ({saved} pages saved)")
    return True


def export_maps(pdf_path, maps=None):
    """Render the three full-page maps from the final PDF at 300 dpi, trimmed to their content.

    Writes build/maps/<name>.png and returns [(attachment name, bytes)] so the PNGs always match the printed pages.
    """
    from PIL import Image, ImageChops
    import io
    doc = pymupdf.open(str(pdf_path))
    out = []
    (HERE / "maps").mkdir(exist_ok=True)
    maps = MAP_FILES if maps is None else maps
    for ch, name in maps.items():
        hit = [p for p in doc if "what does what" in p.get_text().lower() and f"chapter {ch}" in p.get_text()[:400].lower()]
        if len(hit) != 1:
            err(f"map page for chapter {ch}: expected 1 page, found {len(hit)}")
            continue
        page = hit[0]
        clip = pymupdf.Rect(0, 0.7 * 72, page.rect.width, page.rect.height - PAGE_BOTTOM_IN * 72)  # drop running header and footer
        pix = page.get_pixmap(dpi=300, clip=clip)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        bbox = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255))).getbbox()
        pad = 36
        box = (max(bbox[0] - pad, 0), max(bbox[1] - pad, 0), min(bbox[2] + pad, img.width), min(bbox[3] + pad, img.height))
        buf = io.BytesIO()
        img.crop(box).save(buf, "PNG", optimize=True)
        (HERE / "maps" / f"{name}.png").write_bytes(buf.getvalue())
        out.append((f"maps/{name}.png", buf.getvalue()))
    doc.close()
    return out


def clean_metadata(pdf_path, entries, pages, attachments):
    """Keep only the title in the PDF info dictionary (no creator or producer strings)."""
    doc = pymupdf.open(str(pdf_path))
    outline = []
    for e in entries:
        kind = e['kind']
        if kind not in ('part', 'chapter', 'front', 'sec'):
            continue
        # Build outline titles from normalized HTML text, never Chrome's wrapped glyph runs.
        title = e['title']
        if kind == 'part' and e.get('appendix'):
            title = f"Appendix {e['appendix']}: {title}"
        level = 1 if kind in ('part', 'front') else 2 if kind == 'chapter' else 3
        if not outline:
            level = 1
        level = min(level, outline[-1][0] + 1) if outline else level
        outline.append([level, title, pages[e['id']]])
    doc.set_toc(outline)
    for name, content in (attachments if EDITION == "ebook" else []):
        desc = 'High-resolution architecture map (PNG)' if name.startswith('maps/') else 'Chapter source code'
        doc.embfile_add(name, content, filename=name, ufilename=name, desc=desc)
    if EDITION != "ebook" and len(doc) % 2:
        last = doc[len(doc) - 1].rect  # print services need an even count: one blank final page, no running foot
        doc.new_page(-1, width=last.width, height=last.height)
    doc.set_metadata({"title": TITLE, "author": "Jeremy Schoemaker", "subject": "",
                      "keywords": "", "creator": "", "producer": ""})
    tmp = pdf_path.with_suffix(".clean.pdf")
    doc.save(str(tmp), garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf_path)


def main():
    files = []
    for p in sorted(CHAPTERS.glob("*.html"), key=lambda x: x.name):
        files.append((p.name, pick_edition(p.read_text(encoding="utf-8"))))
    if not files:
        print(f"no chapters in {CHAPTERS}", file=sys.stderr)
        return 2
    all_ids: dict[str, str] = {}
    for name, text in files:
        lint_fragment(name, text, all_ids)
    lint_citations(files)

    files = runpy.run_path(str(HERE / 'make-dividers.py'))['ordered_files'](files)
    _, attachments, listings = relocate(files, enabled=os.environ.get('GUIDE_RELOCATE', '1') != '0', edition='ebook' if EDITION == 'ebook' else 'print')
    write_manifest(listings, MANIFEST)
    moved = [e for e in listings if not e['inline']]
    print(f"edition: {EDITION}; code files: {len(attachments)}; moved off the page: {len(moved)}")
    pages = None
    entries = []
    if not choose_compaction(files):
        report()
        return 1
    if True:
        doc, entries = assemble(files, None)
        if errors:
            report()
            return 1
        OUT_HTML.write_text(doc, encoding="utf-8")
        if not render(OUT_HTML, OUT_PDF):
            report()
            return 1
        pages = None
        for _ in range(3):
            dest, n = link_pages(OUT_PDF)
            missing = [e["id"] for e in entries if e["id"] not in dest]
            if missing:
                err(f"headings not found in PDF destinations: {missing[:5]}")
                break
            new_pages = {e["id"]: dest[e["id"]] for e in entries}
            if new_pages == pages:
                break
            pages = new_pages
            doc, _ = assemble(files, pages)
            OUT_HTML.write_text(doc, encoding="utf-8")
            if not render(OUT_HTML, OUT_PDF):
                break
        else:
            err("table of contents page numbers did not settle after 3 passes")

    if not errors:
        dest, n = link_pages(OUT_PDF)
        for e in entries:
            if dest.get(e["id"]) != pages[e["id"]]:
                err(f"contents says {pages[e['id']]} for '{e['title']}' but PDF has {dest.get(e['id'])}")
        for note in check_pdf(OUT_PDF):
            err(note)
        maps = present_maps(files)
        for ch in sorted(set(MAP_FILES) - set(maps)):
            warn(f"chapter {ch} is absent from this build: its map was not exported or attached")
        map_files = export_maps(OUT_PDF, maps) if EDITION == "ebook" else []
        attachments = list(attachments) + map_files
        if errors:
            report()
            return 1
        clean_metadata(OUT_PDF, entries, pages, attachments)
        print(f"pages: {n}")
    report()
    if errors:
        return 1
    print(f"ok: {OUT_PDF}")
    return 0


def report():
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
