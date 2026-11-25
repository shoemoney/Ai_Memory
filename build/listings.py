"""Build-only listing relocation and chapter-local citation checks.

Beautiful Soup's html.parser preserves source line numbers for lint diagnostics.
Chapter source files are never rewritten.
"""
import html
import re
from collections import Counter

from bs4 import BeautifulSoup

import json
import os

# A named code block longer than this many lines leaves the page: the chapter keeps a one-line pointer.
# One constant for the whole build. GUIDE_LISTING_LINES overrides it for page-count experiments only.
LISTING_LINE_THRESHOLD = int(os.environ.get('GUIDE_LISTING_LINES', '8'))
UNNAMED_WARN_LINES = 40  # an unnamed block this long cannot move off the page: warn so the author names it
REPO_URL = 'https://github.com/shoemoney/Ai_Memory'
REPO_BLOB = REPO_URL + '/blob/main/'
CLONE_CMD = 'git clone https://github.com/shoemoney/Ai_Memory.git'
MAP_FILES = {'21': 'map-painter', '22': 'map-medical-office', '23': 'map-homebuilder'}  # chapter -> maps/<name>.png
BLOCK_RE = re.compile(r'<div\b[^>]*\bclass=["\'][^"\']*\bcodeblock\b[^"\']*["\'][^>]*>.*?</pre>\s*</div>', re.S | re.I)


def normalized_text(markup):
    # A line-break element separates words just as whitespace in source does.
    markup = re.sub(r'<br\b[^>]*>', ' ', markup, flags=re.I)
    return ' '.join(BeautifulSoup(markup, 'html.parser').get_text().split())


def code_blocks(text):
    soup = BeautifulSoup(text, 'html.parser')
    for match, node in zip(BLOCK_RE.finditer(text), soup.select('div.codeblock')):
        pre = node.find('pre')
        if pre is None:
            continue
        filename = node.select_one('.code-file')
        language = node.select_one('.code-lang')
        head = node.select_one('.code-head')
        tag = node.select_one('.code-tag')
        code = pre.get_text()  # Preserve whitespace, final newline and decoded entities exactly.
        step = None
        li = node.find_parent('li')
        if li and li.parent.name == 'ol' and 'steps' in li.parent.get('class', []):
            siblings = li.parent.find_all('li', recursive=False)
            number = int(li.parent.get('start', 1)) - 1
            for item in siblings:
                number = int(item.get('value', number + 1))
                if item is li:
                    step = number
                    break
        yield dict(match=match, code=code, lines=len(code.splitlines()),
                   filename=filename.get_text().strip() if filename else '',
                   language=language.get_text().strip().lower() if language else '',
                   head=str(head) if head else '', step=step,
                   tag=tag.get_text().strip() if tag else '', tag_class=' '.join(tag.get('class', [])) if tag else '',
                   note=node.get('data-listing-note', ''),
                   output='output' in node.get('class', []) or node.has_attr('data-output')
                          or (language is not None and language.get_text().strip().lower() == 'output'))


def lint_citations(files, err, warn):
    for name, text in files:
        soup = BeautifulSoup(text, 'html.parser')
        sources = {li.get('id'): li for li in soup.select('.sources-list li[id]')}
        source_numbers = {}
        for ol in soup.select('ol.sources-list'):
            number = int(ol.get('start', 1)) - 1
            for li in ol.find_all('li', recursive=False):
                number = int(li.get('value', number + 1))
                source_numbers[li.get('id')] = number
                if not li.get('id'):
                    warn(f'{name}:{li.sourceline}: Sources entry {number} has no id and is never cited')
        cited = set()
        first_numbers = []
        for cite in soup.select('.cite'):
            links = cite.find_all('a')
            if not links:
                err(f'{name}:{cite.sourceline}: citation has no source link')
            for link in links:
                sid = link.get('href', '').removeprefix('#')
                number = normalized_text(str(link))
                expected = source_numbers.get(sid)
                if sid not in sources or expected is None or number != str(expected):
                    err(f'{name}:{link.sourceline}: citation {number!r} / {sid!r} has no matching numbered entry in this chapter Sources list')
                if sid not in cited and expected:
                    n = expected
                    if n != len(first_numbers) + 1:
                        warn(f'{name}:{link.sourceline}: citation {n} is out of order of first appearance (expected {len(first_numbers) + 1})')
                    first_numbers.append(n)
                cited.add(sid)
        # Catch source-shaped links even if the author omitted .cite.
        for link in soup.select('a[href]'):
            sid = link['href'].removeprefix('#')
            if re.fullmatch(r's\d+-[\w.-]+', sid):
                if sid not in sources:
                    err(f'{name}:{link.sourceline}: citation points to missing chapter source {sid!r}')
                cited.add(sid)
        for sid, li in sources.items():
            if sid not in cited:
                warn(f'{name}:{li.sourceline}: source {sid} is listed but never cited')
        for block in code_blocks(text):
            if block['lines'] > UNNAMED_WARN_LINES and not block['filename'] and not block['output']:
                line = text.count('\n', 0, block['match'].start()) + 1
                warn(f'{name}:{line}: code block has {block["lines"]} lines but no file name (threshold {UNNAMED_WARN_LINES})')


def present_maps(files):
    """MAP_FILES restricted to the case-study chapters present in this build (single-chapter previews omit them)."""
    chapters = set()
    for _, text in files:
        for m in re.finditer(r'<article\b[^>]*\bdata-ch=["\'](\d+)["\']', text):
            chapters.add(m.group(1))
    return {ch: name for ch, name in MAP_FILES.items() if ch in chapters}


def block_note(b):
    """One short line for the index: the author's listing note, else the language and evidence tag."""
    if b['note']:
        return b['note']
    return ', '.join(x for x in (b['language'], b['tag']) if x)


def relocate(files, pages=None, enabled=True, edition='ebook'):
    """Return transformed files, PDF attachments and per-file metadata (labels, URLs, moved or inline).

    Chapter source files are never rewritten. Every named block gets a label chNN-codeKK (document order
    per chapter; a repeated file name keeps its first label). Blocks longer than LISTING_LINE_THRESHOLD
    are replaced by a pointer; shorter ones stay inline with the label in their header.
    """
    attachments, entries, out = [], [], []
    for name, text in files:
        root = BeautifulSoup(text, 'html.parser').select_one('article.chapter')
        if root is None or 'glossary' in name.lower():
            out.append((name, text))
            continue
        ch = root.get('data-ch')
        blocks = list(code_blocks(text))
        counts = Counter(b['filename'] for b in blocks if b['filename'])
        used, labels = set(), {}
        replacements = []
        for b in blocks:
            filename = b['filename']
            if not filename:
                continue
            attachment = f'ch{ch}/{filename}'
            if counts[filename] > 1:
                attachment = f'ch{ch}/step-{b["step"] or "unassigned"}/{filename}'
            base, suffix = attachment, 2
            while attachment in used:
                attachment = f'{base}.{suffix}'
                suffix += 1
            used.add(attachment)
            attachments.append((attachment, b['code'].encode('utf-8')))
            if filename not in labels:
                labels[filename] = f'ch{ch}-code{len(labels) + 1:02d}'
            label = labels[filename]
            moved = enabled and not b['output'] and b['lines'] > LISTING_LINE_THRESHOLD
            url = REPO_BLOB + attachment
            entry = dict(label=label, chapter=ch, path=attachment, lines=b['lines'], note=block_note(b),
                         inline=not moved, url=url)
            entries.append(entry)
            if not moved:
                head = re.sub(r'(<span class="code-file")', f'<span class="code-label">{label}</span>\\1',
                              b['match'].group(0), count=1)
                replacements.append((b['match'].start(), b['match'].end(), head))
                continue
            lang = b['language']
            tag = (f'<span class="{html.escape(b["tag_class"])}">{html.escape(b["tag"])}</span>' if b['tag'] else '')
            link = f'<a class="code-label" href="{url}">{label} \u00b7 {html.escape(filename)}</a>'
            if edition == 'print':
                head = (f'<div class="code-head"><span class="code-lang">{html.escape(lang)}</span>'
                        f'<span class="code-label">{label}</span><span class="code-lines">{b["lines"]} lines</span>{tag}</div>')
                line = f'<p class="listing-url"><a class="url" href="{url}">{url}</a></p>'
            else:
                head = (f'<div class="code-head"><span class="code-lang">{html.escape(lang)}</span>{link}'
                        f'<span class="code-lines">{b["lines"]} lines \u00b7 in this PDF and the companion repository</span>{tag}</div>')
                line = ''
            note = f'<p class="listing-note">{html.escape(b["note"])}</p>' if b['note'] else ''
            pointer = f'<div class="listing-pointer">{head}{line}{note}</div>'
            replacements.append((b['match'].start(), b['match'].end(), pointer))
        for start, end, new in reversed(replacements):
            text = text[:start] + new + text[end:]
        out.append((name, text))
    entries.sort(key=lambda e: (e['label'], e['path']))
    out.append(('attached-files.html', index_html(entries, len(attachments), edition, present_maps(files))))
    return out, attachments, entries


def index_html(entries, n_files, edition, maps):
    n_maps = len(maps)
    clone = html.escape(CLONE_CMD)
    repo_block = (f'<pre class="att-code"><a class="url" href="{REPO_URL}">{REPO_URL}</a>\n{clone}</pre>')
    if edition == 'print':
        title, running = 'Code files', 'Code files'
        intro = (f'<p class="att-intro">The {n_files} code files from the chapter walkthroughs are in the companion repository, '
                 'one folder per chapter named like the label prefix. The repository address and the command that copies all of it:</p>'
                 + repo_block +
                 '<p class="att-intro">The chapters cite each file by its label. The repository README maps each label to its file.</p>')
        rows = ''.join(f'<div class="att"><b class="att-label">{e["label"]}</b>'
                       f'<span class="att-path">{html.escape(e["path"])}</span></div>' for e in entries)
        extra = ''
    else:
        title, running = 'Attached files', 'Attached files'
        intro = (f'<p class="att-intro">The {n_files + n_maps} files below are attached to this PDF: {n_files} code files from the chapter '
                 f'walkthroughs and {n_maps} large map images under maps/. The same files are in the companion repository, one folder '
                 'per chapter named like the attachment prefix, with the maps under maps/. The repository address and the command that copies all of it:</p>'
                 + repo_block +
                 '<p class="att-intro">The chapters cite each code file by its label. Every source link in the book, by chapter and '
                 'number, is also listed in the companion repository under sources/.</p>'
                 '<p class="att-intro">To open the attachments, look for a paperclip icon or an Attachments entry in the side panel of '
                 'your PDF reader and save the files from there. If your reader lists none, extract them with pymupdf:</p>'
                 '<pre class="att-code">import pymupdf, pathlib\n'
                 'doc = pymupdf.open("ai-memory-guide.pdf")\n'
                 'for name in doc.embfile_names():\n'
                 '    target = pathlib.Path("attachments") / name\n'
                 '    target.parent.mkdir(parents=True, exist_ok=True)\n'
                 '    target.write_bytes(doc.embfile_get(name))</pre>')
        rows = ''.join(f'<div class="att"><b class="att-label">{e["label"]}</b><span class="att-path">{html.escape(e["path"])}</span>'
                       f'<span class="att-meta">{e["lines"]} line{"" if e["lines"] == 1 else "s"} \u00b7 {html.escape(e["note"])}</span></div>' for e in entries)
        rows += ''.join(f'<div class="att"><b class="att-label">map</b><span class="att-path">maps/{n}.png</span>'
                        f'<span class="att-meta">Full-page map for Chapter {c}, 300 dpi</span></div>' for c, n in maps.items())
        extra = ''
    return ('<article class="chapter attached" data-ch="B" data-part="ref" data-appendix="B" '
            f'data-running="{running}"><header class="appendix-head"><p class="appendix-eyebrow">Appendix B</p>'
            f'<h1 class="appendix-title">{title}</h1></header><section>{intro}<div class="att-list">{rows}</div>{extra}</section></article>')


def write_manifest(entries, path):
    keep = ('label', 'chapter', 'path', 'lines', 'note', 'inline', 'url')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump([{k: e[k] for k in keep} for e in entries], fh, indent=2, ensure_ascii=False)
        fh.write('\n')
