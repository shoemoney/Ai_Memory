#!/usr/bin/env python3
"""Compose the print cover image: art scaled to full page width, extended upward with the
matching dark navy so the title has room, then saved as a JPEG for embedding.
Input:  cover-art/cover-b-20261120-095134.png (portrait, no text)
Output: cover-art/cover-ai-memory.jpg (8.5 x 11 in at 150 dpi)
"""
from pathlib import Path
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
SRC = HERE / "cover-art" / "cover-b-20261120-095134.png"
OUT = HERE / "cover-art" / "cover-ai-memory.jpg"
W, H, SHIFT = 1275, 1650, 190

art = Image.open(SRC).convert("RGB")
scale = W / art.width
art = art.resize((W, round(art.height * scale)), Image.LANCZOS)

# Extension: take a blurred strip from the top rows and repeat it upward.
strip = art.crop((0, 0, W, 24)).filter(ImageFilter.GaussianBlur(14)).resize((W, 1), Image.BILINEAR)
canvas = Image.new("RGB", (W, H))
canvas.paste(strip.resize((W, SHIFT + 40), Image.NEAREST), (0, 0))
canvas.paste(art, (0, SHIFT))
# Soften the seam.
seam = canvas.crop((0, SHIFT - 30, W, SHIFT + 60)).filter(ImageFilter.GaussianBlur(5))
canvas.paste(seam, (0, SHIFT - 30))
canvas.save(OUT, "JPEG", quality=86, optimize=True, progressive=True, subsampling=0)
print(OUT, OUT.stat().st_size)
