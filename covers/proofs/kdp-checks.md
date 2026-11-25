# KDP checks, measured 22 November 2026

## Update, 23 November 2026

The interiors were rebuilt after further revision and both print wraps were recut. Re-measured on 23 November from the files in `build/` and `covers/`; the tables below still describe the 22 November files, and every hardcover figure of 308 pages in them is now 304.

| Check | Measured | Result |
|---|---|---|
| Paperback interior | 300 pages, every page 8.5 x 11 in, all fonts embedded, smallest inside margin 0.88 in, page 300 blank | PASS |
| Hardcover interior | 304 pages (even), every page 8.25 x 11 in, all fonts embedded, smallest inside margin 0.896 in against the 0.625 in minimum for 301 to 500 pages | PASS |
| Paperback wrap | cut for 300 pages, 17.9542 x 11.25 in, `covers/build/preflight.py` passes | PASS |
| Hardcover wrap | cut for 304 pages, spine 0.902 in, 18.9769 x 12.4169 in against the calculator's 18.977 x 12.417 | PASS |
| Ebook cover | 1600 x 2560 px RGB JPEG, unchanged | PASS |
| EPUB | epubcheck 5.4.0: 0 fatals, 0 errors, 0 warnings, 0 infos | PASS |

Not re-measured on 23 November: image resolution, text-outside-page and Type3 scans, and the part-divider background fill on the hardcover. KDP Previewer and a printed proof are still to do.

Every value below was measured on 22 November 2026 from the files as they stand in `build/` and `covers/`. Nothing was rebuilt or edited. PDFs were read with PyMuPDF; page images were rendered at 60 dpi (all pages) and 300 dpi (dividers, covers, barcode zones). The EPUB was checked with epubcheck 5.4.0 (EPUB 3.4 rules) and by unzipping it. Cover reference values are the KDP Cover Calculator results cached in `covers/build/kdp-calculator-cache.json` (white paper, premium colour ink) and the published paperback formula. The checks follow the build-ebook-kdp and kdp-print-cover-rejections skills.

Cover page counts versus interiors: `covers/build/geometry.json` `pages_used` is paperback 300 and hardcover 308. The measured interiors are 300 and 308. They match.

Result: paperback interior 13 of 13 pass. Hardcover interior 13 of 14 pass, **1 fail** (white sliver on the part dividers). Free PDF recorded only. Paperback cover 18 of 18 pass. Hardcover cover 18 of 18 pass. EPUB 10 of 10 pass. Ebook JPEG 5 of 5 pass.

## Paperback interior: `build/ai-memory-guide-print.pdf`

| Check | Measured | Result |
|---|---|---|
| Page count, limits 24 to 828 | 300 | PASS |
| Even page count | 300 | PASS |
| Trim size, every page | 8.5 x 11 in on all 300 pages | PASS |
| Bleed boxes (No Bleed: media = crop = trim = bleed) | equal on all 300 pages | PASS |
| Inside gutter, minimum 0.5 in for 151 to 300 pages (ink bounds, mirrored by page side, all 300 pages including 7 part dividers, tables, code pages, Sources pages) | smallest 0.88 in (page 3) | PASS |
| Outside margin, minimum 0.25 in | smallest 0.68 in (page 2) | PASS |
| Top margin, minimum 0.25 in | smallest 0.43 in (page 8) | PASS |
| Bottom margin, minimum 0.25 in | smallest 0.47 in (page 3) | PASS |
| Text outside the page | 0 spans on 300 pages | PASS |
| Fonts embedded, no Type3 | 18 fonts, all embedded TrueType subsets (Type0), 0 Type3 | PASS |
| Raster images, minimum 300 ppi | 0 raster images in the file (title page is typeset) | PASS |
| Metadata | Title "AI Memory", Author "Jeremy Schoemaker"; Subject, Keywords, Creator and Producer empty. A creation and modification date is present | PASS |
| File size, limit 650 MB | 11,554,889 bytes (11.55 MB) | PASS |

Part dividers (pages 16, 42, 79, 104, 154, 184, 230): navy fill reaches all four page edges with no white sliver; text sits at least 1.05 in from the left and 2.14 in from the right, 4.45 in from the top and 0.60 in from the bottom.

## Hardcover interior: `build/ai-memory-guide-hardcover.pdf`

| Check | Measured | Result |
|---|---|---|
| Page count, limits 75 to 550 | 308 | PASS |
| Even page count | 308 (page 308 is a deliberate blank) | PASS |
| Trim size, every page | 8.25 x 11 in (a KDP hardcover trim) on all 308 pages | PASS |
| Bleed boxes (No Bleed) | equal on all 308 pages | PASS |
| Inside gutter, minimum 0.625 in for 301 to 500 pages (all 308 pages) | smallest 0.88 in (page 3) | PASS |
| Outside margin, minimum 0.25 in | smallest 0.68 in (page 2) | PASS |
| Top margin, minimum 0.25 in | smallest 0.43 in (page 8) | PASS |
| Bottom margin, minimum 0.25 in | smallest 0.47 in (page 3) | PASS |
| Text outside the page | 0 spans on 308 pages | PASS |
| Fonts embedded, no Type3 | 18 fonts, all embedded TrueType subsets (Type0), 0 Type3 | PASS |
| Raster images, minimum 300 ppi | 0 raster images in the file | PASS |
| Metadata | Title "AI Memory", Author "Jeremy Schoemaker"; Subject, Keywords, Creator and Producer empty. A creation and modification date is present | PASS |
| File size, limit 650 MB | 11,942,558 bytes (11.94 MB) | PASS |
| Part dividers (pages 16, 42, 79, 104, 155, 185, 234) fill the page | The navy fill is 591.18 x 788.24 pt on a 594 x 792 pt page, leaving a white strip 2.82 pt (0.039 in) wide on the right edge and 3.76 pt (0.052 in) tall along the bottom edge on all 7 pages. Visible in the render. The paperback dividers do not have this | **FAIL** |

## Free PDF edition: `build/ai-memory-guide.pdf` (recorded only, not a KDP upload)

| Item | Measured |
|---|---|
| Pages | 296 |
| Page size | 8.5 x 11 in |
| File size | 14,902,529 bytes (14.90 MB) |
| Fonts | 57 Type3 fonts (7,309 uses, on all 296 pages) carry the body text; 5 embedded TrueType subsets (JetBrains Mono four weights, DejaVu Sans Mono) |
| Images | 9 placed images on page 1, 8 of them below 300 ppi (a 150 ppi page image and 72 ppi overlays) |
| Text outside the page | 7 spans (pages 16, 41, 76, 100, 149 and two more), the large part-divider letters reach 16 pt above the page |
| Metadata | Title "AI Memory", Author "Jeremy Schoemaker"; Subject, Keywords, Creator and Producer empty; creation date present |

## Paperback cover: `covers/paperback/AI-Memory-paperback-cover.pdf`

| Check | Measured | Result |
|---|---|---|
| Interior page count the cover is cut for | 300 (`pages_used`), interior measures 300 | PASS |
| Full size against the formula (2 x 8.5 + 300 x 0.002347 + 2 x 0.125 by 11.25) | 17.9542 x 11.25 in against 17.9541 x 11.25 (the calculator rounds to 17.954) | PASS |
| Spine width | 0.7041 in (300 x 0.002347; calculator 0.704) | PASS |
| Pixel size at 300 ppi | 5387 x 3375 | PASS |
| Bleed and boards | 0.125 in bleed, boards 8.5 x 11 in, no hinge | PASS |
| Text from the outer edges, minimum 0.375 in | back 0.760, front 0.760, top 0.622, bottom 0.578 in | PASS |
| Back and front text from the spine edge, minimum 0.4 in | back 0.772, front 0.718 in | PASS |
| Text crossing a fold | none | PASS |
| Spine text allowed (79 pages or more) | 300 pages | PASS |
| Spine text clearance to each fold, minimum 0.0625 in | 0.238 in left, 0.234 in right | PASS |
| Spine text vertically centred | 3.847 in above, 3.851 in below | PASS |
| Barcode zone 2.0 x 1.2 in, empty and white | 2.00 x 1.20 in, mean 254.4 of 255, no text, no art (the few dark pixels are the antialiased zone border) | PASS |
| Barcode position | 0.30 in from the spine side, 0.30 in above the trim bottom | PASS |
| Fonts embedded, no Type3 | 4 embedded subset Type0 fonts | PASS |
| Image resolution, minimum 300 ppi | one CMYK image, 320 ppi | PASS |
| Colour space | CMYK | PASS |
| Fold seams (rendered 0.125 in bands at both folds) | horizontal channel range 0 of 255 at both | PASS |
| File size and metadata | 1,169,441 bytes; Title "AI Memory", Author "Jeremy Schoemaker", Subject "paperback cover"; Creator and Producer empty | PASS |

## Hardcover cover: `covers/hardcover/AI-Memory-hardcover-cover.pdf`

| Check | Measured | Result |
|---|---|---|
| Interior page count the cover is cut for | 308 (`pages_used`), interior measures 308 | PASS |
| Full size against the calculator (308 pages, white, premium colour) | 18.9869 x 12.4169 in against 18.987 x 12.417 | PASS |
| Spine width | 0.912 in (calculator) | PASS |
| Pixel size at 300 ppi | 5697 x 3726 | PASS |
| Wrap, boards and hinges | wrap 0.591 in, boards 8.447 x 11.236 in, hinges 0.394 in | PASS |
| Text from the outer edges, minimum 0.716 in | back 0.800, front 0.820, top 0.840, bottom 0.758 in | PASS |
| Back text from the spine edge, minimum 0.4 in | back 1.272, front 0.778 in | PASS |
| Text crossing a fold or hinge | none | PASS |
| Spine text allowed (79 pages or more) | 308 pages | PASS |
| Spine text clearance to each fold, minimum 0.0625 in | 0.342 in left, 0.338 in right | PASS |
| Spine text vertically centred | 4.430 in above, 4.434 in below | PASS |
| Barcode zone 2.0 x 1.2 in, empty and white | 2.00 x 1.20 in, mean 255.0 of 255, minimum pixel 238, no text, no art | PASS |
| Barcode position | 0.30 in from the hinge, 0.40 in above the board bottom (calculator margins 0.25 and 0.375 in) | PASS |
| Fonts embedded, no Type3 | 4 embedded subset Type0 fonts | PASS |
| Image resolution, minimum 300 ppi | one CMYK image, 320 ppi | PASS |
| Colour space | CMYK | PASS |
| Fold seams (rendered 0.125 in bands at both folds) | horizontal channel range 0 of 255 at both | PASS |
| File size and metadata | 1,289,305 bytes; Title "AI Memory", Author "Jeremy Schoemaker", Subject "hardcover cover"; Creator and Producer empty | PASS |

The Subject field on both cover PDFs holds the binding name. It is not a tool or credit line, but it is a third field beyond title and author.

## Kindle and free EPUB: `build/ai-memory.epub`

| Check | Measured | Result |
|---|---|---|
| epubcheck 5.4.0, EPUB 3.4 rules | 0 fatals, 0 errors, 0 warnings, 0 infos | PASS |
| Cover declared | `cover-image` item `images/cover.jpg` (properties cover-image, plus the `cover` meta) and a cover document first in the spine; byte-identical to the ebook cover JPEG | PASS |
| Title | "AI Memory", subtitle "Building an LLM brain" | PASS |
| Author | Jeremy Schoemaker (role aut) | PASS |
| Language | en | PASS |
| No generator or tool name | no generator meta, no tool names in the package metadata | PASS |
| Every spine document in the navigation | 56 spine documents, 0 missing from `nav.xhtml` | PASS |
| Navigation structure | nav has toc and landmarks, 270 entries; an NCX is included | PASS |
| File size, limit 650 MB | 1,324,534 bytes (1.32 MB), 63 files | PASS |
| Identifier | stable `urn:uuid` | PASS |

## Ebook cover JPEG: `covers/ebook/AI-Memory-Kindle-and-EPUB-cover.jpg`

| Check | Measured | Result |
|---|---|---|
| Pixel size | 1600 x 2560 | PASS |
| Ratio | 1.600 (height to width) | PASS |
| Colour mode | RGB | PASS |
| Format and tag | JPEG, 300 dpi tag | PASS |
| File size, limit 50 MB | 841,329 bytes | PASS |

## What the renders showed

Viewed: page 1, last page, a part divider, a table page, a code page and a Sources page of each print interior, both cover wraps in full, and both spines at 300 percent.

- Page 1 is a clean typeset title page in both interiors. Page 300 of the paperback is a code-file index page (not blank); page 308 of the hardcover is a deliberate blank.
- Part dividers are full-page navy with a large outlined letter, readable text and no clipping. The hardcover dividers show a thin white strip along the right and bottom edges (the failure above).
- The matrix tables (pages 215 paperback, 218 hardcover) and the code pages (page 25) fit inside the margins, with no clipped cells or lines.
- Sources pages (page 29) are three columns with long URLs wrapped; nothing is clipped.
- Orphaned headings: an automatic scan of both interiors found no page ending on a heading, and none was seen in the viewed pages.
- Nearly empty pages that are not deliberate blanks: paperback page 66 and hardcover pages 41 and 276 hold only the last eight to eleven Sources entries at the top; paperback page 280 holds a single code line and one short section; paperback page 298 is the end of the glossary. These are chapter and appendix tails, not errors.
- Both wraps: the barcode zone is an empty white rectangle at the bottom of the back cover, the spine text is a single centred line inside both folds, back copy is readable, and no seam shows at the folds. No ghost text or clipping was seen.

## Not checked

- KDP's online previewer and its acceptance of any file.
- A printed proof copy (colour, trim, spine alignment, portrait sharpness at print size).
- A physical Kindle or other e-reader.
