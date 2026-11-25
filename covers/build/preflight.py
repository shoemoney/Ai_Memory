#!/usr/bin/env python3
"""Check page geometry, fonts, raster resolution, barcode clearance and safe text."""
from pathlib import Path
import json, subprocess
import pymupdf as pdf
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
g=json.loads((ROOT/'build/geometry.json').read_text());report=[]
im=Image.open(ROOT/'ebook/AI-Memory-Kindle-and-EPUB-cover.jpg');assert im.mode=='RGB' and im.size==(1600,2560)
assert (ROOT/'ebook/AI-Memory-Kindle-and-EPUB-cover.jpg').stat().st_size<50_000_000
report.append('Ebook: RGB JPEG, 1600 x 2560 pixels, ratio 1.6, under 50MB: PASS')
for binding in ['paperback','hardcover']:
 m=g[binding];path=ROOT/m['file'];d=pdf.open(path);assert len(d)==1 and not d.is_encrypted
 p=d[0];assert abs(p.rect.width/72-m['width_in'])<.01 and abs(p.rect.height/72-m['height_in'])<.01
 fonts=p.get_fonts(full=True)
 assert fonts and all(len(d.extract_font(f[0])[3])>0 and f[2]!='Type3' for f in fonts)
 image_info=p.get_image_info();assert image_info
 for item in image_info:
  box=pdf.Rect(item['bbox']);xp=item['width']/(box.width/72);yp=item['height']/(box.height/72)
  assert min(xp,yp)>=300,(binding,xp,yp)
  assert item['colorspace']==4,(binding,item['colorspace'])
 pix=p.get_pixmap(matrix=pdf.Matrix(150/72,150/72),colorspace=pdf.csRGB,alpha=False)
 im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
 zone=pdf.Rect(m['barcode_pt']); zone=zone+(1,1,-1,-1)
 a=np.asarray(im.crop(tuple(round(v*150/72) for v in zone)))
 assert a.mean()>250 and (a<230).mean()<.001
 # Check a drift band on each side of both folds. The photographic ground
 # is shared here; typography and barcode are outside these narrow bands.
 arr=np.asarray(im).astype('int16')
 fold_metrics=[]
 for xx in [(m['width_in']-m['spine_in'])/2,m['front_x_in']]:
  center=round(xx*150); band=arr[:,center-19:center+20,:]
  spread=(band.max(axis=1)-band.min(axis=1)).max()
  assert spread<=5,(binding,'fold tonal discontinuity',int(spread))
  fold_metrics.append(int(spread))
 report.append(f'{binding}: +/-0.125in rendered fold bands, maximum horizontal channel range {fold_metrics}/255: PASS')
 safe=[]
 for b in p.get_text('dict')['blocks']:
  if b['type']!=0:continue
  for l in b['lines']:
   for s in l['spans']:
    r=pdf.Rect(s['bbox']); txt=s['text']
    if 'AI Memory' in txt and 'Jeremy' in txt:
     center=m['width_in']*36;half=m['spine_in']*36
     assert r.x0>center-half+.0625*72 and r.x1<center+half-.0625*72,(binding,txt,list(r))
    else:
     panelx=m['front_x_in'] if r.x0>m['width_in']*36 else m['back_x_in']
     minimum=.716 if binding=='hardcover' else .375
     assert r.x0>= (panelx+minimum)*72 and r.x1<= (panelx+m['board_width_in']-minimum)*72,(binding,txt,list(r))
     assert r.y0>=(m['panel_top_in']+minimum)*72 and r.y1<=(m['panel_top_in']+m['board_height_in']-minimum)*72,(binding,txt,list(r))
    assert not r.intersects(pdf.Rect(m['barcode_pt'])),txt
    safe.append(txt)
 report.append(f'{binding}: one page, {p.rect.width/72:.6f} x {p.rect.height/72:.6f} in; embedded fonts {len(fonts)}; all images CMYK at >=300ppi; safe text; clear 2 x 1.2in white barcode zone: PASS')
 report.append('Fonts: '+str([(f[3],f[2],len(d.extract_font(f[0])[3])) for f in fonts]))
 report.append('Images: '+str([(v['width'],v['height'],v['colorspace'],list(v['bbox'])) for v in image_info]))
report.append('Local preflight cannot certify KDP acceptance, physical color, or the hardcover interior. Use KDP Previewer and order a printed proof.')
(ROOT/'proofs/preflight.txt').write_text('\n'.join(report)+'\n');print('\n'.join(report))
