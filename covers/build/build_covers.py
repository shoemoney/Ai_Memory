#!/usr/bin/env python3
"""Build cover uploads and guided proofs. Run from any directory; page count required."""
import argparse, io, json, os, subprocess, hashlib, shutil
from pathlib import Path
import pymupdf as pdf
from PIL import Image, ImageFilter
from kdp_calculator import measurements
ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parent; AS=ROOT/'build/assets'
os.environ['KDP_COVER_CACHE']=str(ROOT/'build/kdp-calculator-cache.json')
# The calculator module reads CACHE at import time.
import kdp_calculator
kdp_calculator.CACHE=os.environ['KDP_COVER_CACHE']
NAVY=(8,13,28); COLORS=['#1f4bd8','#0a7c78','#6a3fd1','#d23b1c','#9a6200','#2c7a3a']
COPY=[
'AI Memory explains how to give an AI agent a memory it can write, search and revise. It is for engineers building assistants, coding agents and services that need to carry useful information from one session to the next.',
'Fourteen architecture chapters work through plain files, maintained wikis, embeddings, retrieval, local models, databases, caches, memory frameworks and temporal graphs. Each chapter describes the mechanism, setup, costs, limits and failure modes. The essays cover the history of the field, current research, security, operations and choosing a stack.',
'Four case studies use only models you run yourself: a personal assistant built in six stages, a painter, a doctor’s office and an international homebuilder. A glossary defines the terms. Every lab and benchmark is runnable from the companion repository, so you can inspect the code, repeat the measurements and test the tradeoffs on your own hardware.'
]
BIO='Jeremy Schoemaker is an engineer who builds AI agent infrastructure and runs models on his own hardware. He is the author of AiBook and a contributor to open-source AI projects.'
URL='https://github.com/shoemoney/Ai_Memory'
FONTS={n:pdf.Font(fontfile=str(AS/(n+'.otf'))) for n in ['display','sans','body','italic']}
def rgb(h):return tuple(int(h[i:i+2],16)/255 for i in (1,3,5))
def text(p,x,y,t,size=12,font='body',color='#ffffff',right=None):
 if right is not None:x=right-FONTS[font].text_length(t,fontsize=size)
 p.insert_font(fontname=font,fontfile=str(AS/(font+'.otf')))
 p.insert_text((x,y),t,fontname=font,fontsize=size,color=rgb(color))
def paragraph(p,x,y,txt,width,size=13,leading=19,font='body',color='#d9e0ef'):
 words=txt.split(); line=''
 for word in words:
  test=(line+' '+word).strip()
  if FONTS[font].text_length(test,fontsize=size)>width:
   text(p,x,y,line,size,font,color);y+=leading;line=word
  else:line=test
 if line:text(p,x,y,line,size,font,color);y+=leading
 return y

def background(w,h,ebook=False):
 # All photographic effects are flattened at >=320ppi. Typography stays vector.
 dpi=320; W,H=round(w*dpi),round(h*dpi)
 art=Image.open(AS/'portrait-4x.jpg').convert('RGB')
 shift=round((1.72 if ebook else 1.267)*dpi)
 aw=W; ah=round(aw*art.height/art.width)
 art=art.resize((aw,ah),Image.Resampling.LANCZOS)
 strip=art.crop((0,0,aw,30)).filter(ImageFilter.GaussianBlur(14)).resize((aw,1))
 bg=strip.resize((W,H));bg.paste(art,(0,shift))
 if shift+ah<H:bg.paste(art.crop((0,ah-1,W,ah)).resize((W,H-shift-ah)),(0,shift+ah))
 import numpy as np
 a=np.asarray(bg).astype('float32'); yy=np.arange(H)/dpi
 top=(np.maximum(0,1-yy/3.4)*.78)[:,None,None]
 bottom=(np.clip((yy-(h-2.1))/(1.7 if ebook else 2.1),0,1)*(1.0 if ebook else .94))[:,None,None]
 alpha=np.maximum(top,bottom)
 a=a*(1-alpha)+__import__('numpy').array(NAVY)[None,None,:]*alpha
 im=Image.fromarray(a.clip(0,255).astype('uint8'));b=io.BytesIO();im.save(b,format='JPEG',quality=96,subsampling=0);return b.getvalue()

def wrap_background(W,H,frontx,y,bw,bh,backx):
 """One continuous photographic field; fade tile art before the front fold."""
 import numpy as np
 from PIL import ImageDraw
 dpi=320; nw,nh=round(W*dpi),round(H*dpi)
 photo=Image.open(io.BytesIO(background(bw,bh))).convert('RGB')
 # The outermost right edge is unoccupied photographic background. Its vertical
 # light falloff becomes the common ground across back, spine and front.
 strip=photo.crop((photo.width-round(.20*dpi),0,photo.width,photo.height))
 strip=strip.resize((1,photo.height),Image.Resampling.BOX).resize((64,photo.height))
 strip=strip.filter(ImageFilter.GaussianBlur(round(.30*dpi))).resize((1,photo.height))
 strip=np.pad(np.asarray(strip),((round(y*dpi),nh-photo.height-round(y*dpi)),(0,0),(0,0)),mode='edge')
 base=Image.fromarray(strip).resize((nw,nh))
 # The two folds and +/-0.125in drift bands contain only the common ground.
 # A smooth 0.45-1.30in fade on the front prevents both tile truncation and seams.
 alpha=np.clip((np.arange(photo.width)/dpi-.45)/.85,0,1)
 alpha=alpha*alpha*(3-2*alpha)
 mask=Image.fromarray(np.tile((alpha*255).astype('uint8'),(photo.height,1)))
 base.paste(photo,(round(frontx*dpi),round(y*dpi)),mask)
 # Continue the final photographic pixel through the outer wrap and bleed.
 right=round((frontx+bw)*dpi)
 if right<nw:base.paste(base.crop((right-1,0,right,nh)).resize((nw-right,nh)),(right,0))
 top=round(y*dpi);bottom=round((y+bh)*dpi)
 if top:base.paste(base.crop((0,top,nw,top+1)).resize((nw,top)),(0,0))
 if bottom<nh:base.paste(base.crop((0,bottom-1,nw,bottom)).resize((nw,nh-bottom)),(0,bottom))
 # Faint memory tiles occupy only the empty band between copy and author block.
 tile=Image.new('RGBA',base.size,(0,0,0,0));draw=ImageDraw.Draw(tile)
 for row in range(2):
  for col in range(8):
   xx=(backx+4.25+col*.39)*dpi;yy=(y+6.23+row*.39)*dpi
   cc=tuple(round(v*255) for v in rgb(COLORS[(row+col)%6]))
   opacity=round(47*(1-col/10))
   draw.rounded_rectangle((xx,yy,xx+.24*dpi,yy+.24*dpi),radius=.04*dpi,fill=(*cc,opacity//3),outline=(*cc,opacity),width=3)
   draw.ellipse((xx+.09*dpi,yy+.05*dpi,xx+.15*dpi,yy+.11*dpi),fill=(*cc,opacity))
   draw.rounded_rectangle((xx+.07*dpi,yy+.13*dpi,xx+.17*dpi,yy+.19*dpi),radius=.02*dpi,fill=(*cc,opacity))
 base=Image.alpha_composite(base.convert('RGBA'),tile).convert('RGB')
 out=io.BytesIO();base.save(out,format='JPEG',quality=96,subsampling=0);return out.getvalue()

def front(p,x,y,w,h,ebook=False,outer=0,draw_art=True):
 if draw_art:
  data=background(w,h,ebook)
  if outer:
   im=Image.open(io.BytesIO(data));import numpy as np
   extra=round(outer*320);a=np.pad(np.asarray(im),((extra,extra),(0,extra),(0,0)),mode='edge');buf=io.BytesIO();Image.fromarray(a).save(buf,format='JPEG',quality=96,subsampling=0);data=buf.getvalue()
  p.insert_image(pdf.Rect(x,y-outer*72,x+(w+outer)*72,y+(h+outer)*72),stream=data)
 # All positions are within the visible panel, with extra binding clearance.
 hard=outer>.2
 inset=.82 if hard else .76
 left=x+inset*72; right=x+(w-inset)*72
 top=.95 if hard else .72
 foot1=1.05 if hard else .87
 foot2=.80 if hard else .62
 text(p,left,y+top*72,'T E C H N I C A L   B O O K',7.8,'sans','#c3cce0')
 if not ebook:text(p,0,y+top*72,'N O V E M B E R   2 0 2 6',7.5,'sans','#c3cce0',right=right)
 size=88 if w>8 else 69
 ty=y+(2.18 if not ebook else 2.14)*72
 text(p,left-3,ty,'AI',size,'display','#8fb0ff')
 aiw=FONTS['display'].text_length('AI',fontsize=size)
 text(p,left+aiw+8,ty,'Memory',size,'display')
 text(p,left,y+2.88*72,'Building an LLM brain',21 if not ebook else 19,'italic','#e1e7f4')
 for i,c in enumerate(COLORS):
  xx=left+i*32;p.draw_rect(pdf.Rect(xx,y+(h-(1.55 if hard else 1.36))*72,xx+26,y+(h-(1.55 if hard else 1.36))*72+5),fill=rgb(c),color=None)
 text(p,0,y+(h-foot1)*72,'Jeremy Schoemaker',14,'sans',right=right)
 text(p,0,y+(h-foot2)*72,'Author of AiBook',11,'italic','#e1e7f4',right=right)
 if not ebook:
  text(p,left,y+(h-foot1)*72,'RESEARCH CURRENT AS OF',7.4,'sans')
  text(p,left,y+(h-(.82 if hard else .65))*72,'22 November 2026',8,'body','#b4bfd6')

# Paperback spine per page on white paper: KDP's published figures by ink type.
PAPERBACK_CALIPER={'premium-color':.002347,'color':.002252,'bw':.002252}
INTERIOR='premium-color'

def wrap(binding,pages):
 hard=binding=='hardcover'
 if hard:
  m=measurements('hardcover','8.25x11',pages,'white',INTERIOR)
  W,H=m['full-cover-width'],m['full-cover-height'];edge=m['wrap-width'];bw,bh=m['front-cover-width'],m['front-cover-height'];sp=m['spine-width']; hinge=m['hinge-width']
 else:
  sp=pages*PAPERBACK_CALIPER[INTERIOR];bw,bh=8.5,11;edge=.125;W,H=2*bw+sp+2*edge,bh+2*edge;hinge=0;m={}
 # Calculator rounds dimensions to .001in, so center the geometry on that page.
 y=(H-bh)/2; spine0=(W-sp)/2;backx=spine0-bw;frontx=spine0+sp
 d=pdf.open();p=d.new_page(width=W*72,height=H*72)
 p.draw_rect(p.rect,color=None,fill=tuple(v/255 for v in NAVY))
 # Use one background image across both folds, with no panel image edge.
 p.insert_image(p.rect,stream=wrap_background(W,H,frontx,y,bw,bh,backx))
 front(p,frontx*72,y*72,bw,bh,outer=y,draw_art=False)
 # Back copy is reset, never reduced from a raster.
 margin=.80 if hard else .76; x=(backx+margin)*72; width=(bw-2*margin-(hinge if hard else 0))*72
 text(p,x,(y+1.18)*72,'Memory, from files',27,'display')
 text(p,x,(y+1.66)*72,'to working systems.',27,'display')
 yy=(y+2.34)*72
 for para in COPY:yy=paragraph(p,x,yy,para,width,12.4,18.2)+14
 # Fixed independent author block deliberately well above barcode reserve.
 for i,c in enumerate(COLORS):
  xx=x+i*32;p.draw_rect(pdf.Rect(xx,(y+6.80)*72,xx+26,(y+6.80)*72+5),fill=rgb(c),color=None)
 text(p,x,(y+7.55)*72,'ABOUT THE AUTHOR',9,'sans','#8fb0ff')
 paragraph(p,x,(y+7.92)*72,BIO,width,11.5,16.5)
 text(p,x,(y+9.13)*72,'COMPANION REPOSITORY',8.5,'sans','#8fb0ff')
 text(p,x,(y+9.43)*72,URL,10,'body')
 # KDP barcode: 2 x 1.2 in, right of back panel, clear of hardcover hinge.
 bx2=(spine0-hinge-.30)*72;by2=(y+bh-(.40 if hard else .30))*72
 barcode=pdf.Rect(bx2-144,by2-86.4,bx2,by2)
 p.draw_rect(barcode,color=None,fill=(1,1,1))
 # Spine typography has generous clearance inside both folds.
 label='AI Memory   ·   Jeremy Schoemaker';fs=15
 p.insert_font(fontname='sans',fontfile=str(AS/'sans.otf'))
 length=FONTS['sans'].text_length(label,fontsize=fs)
 # 270 degrees reads from top to bottom.
 sx=(spine0+sp/2)*72-fs*.34
 p.insert_text((sx,(H*72-length)/2),label,fontname='sans',fontsize=fs,rotate=270,color=(1,1,1))
 d.set_metadata({'title':'AI Memory','author':'Jeremy Schoemaker','subject':binding+' cover','creator':'','producer':''})
 scratch=Path('/var/tmp/membench-covers');scratch.mkdir(exist_ok=True)
 raw=scratch/('raw-'+binding+'.pdf');d.save(raw);d.close()
 out=ROOT/binding/('AI-Memory-'+binding+'-cover.pdf')
 subprocess.run(['gs','-dNOSAFER','-q','-dBATCH','-dNOPAUSE','-sDEVICE=pdfwrite','-dCompatibilityLevel=1.4','-sColorConversionStrategy=CMYK','-dProcessColorModel=/DeviceCMYK','-dEmbedAllFonts=true','-dSubsetFonts=true','-dDownsampleColorImages=false','-sOutputFile='+str(scratch/(binding+'.pdf')),str(raw)],check=True)
 shutil.move(scratch/(binding+'.pdf'),out)
 # Strip software metadata after conversion.
 q=pdf.open(out);q.set_metadata({'title':'AI Memory','author':'Jeremy Schoemaker','subject':binding+' cover','creator':'','producer':''});q.del_xml_metadata();clean=out.with_suffix('.clean.pdf');q.save(clean,garbage=4,deflate=True);q.close();clean.replace(out);raw.unlink()
 proof=pdf.open(out);p=proof[0]
 def rect(r,c):p.draw_rect(r,color=c,width=.7)
 panels=[pdf.Rect(backx*72,y*72,spine0*72,(y+bh)*72),pdf.Rect(frontx*72,y*72,(frontx+bw)*72,(y+bh)*72)]
 for r in panels:
  rect(r,(0,1,1));rect(r+(.76*72,.76*72,-.76*72,-.76*72),(0,1,0))
 for xx in [spine0,spine0+sp]:p.draw_line((xx*72,0),(xx*72,H*72),color=(1,0,1),width=.7)
 if hard:
  for xx in [spine0-hinge,spine0+sp+hinge]:p.draw_line((xx*72,y*72),(xx*72,(y+bh)*72),color=(1,.7,0),width=1)
 rect(barcode,(1,0,0));p.insert_text((8,12),'PROOF ONLY: cyan boards/trim | green safe | magenta spine | orange hinges | red barcode',fontsize=7,color=(1,1,1))
 proof.save(ROOT/'proofs'/(binding+'-guides.pdf'));p.get_pixmap(matrix=pdf.Matrix(1.25,1.25)).save(ROOT/'proofs'/(binding+'-guides.png'));proof.close()
 q=pdf.open(out);q[0].get_pixmap(matrix=pdf.Matrix(1,1)).save(ROOT/'proofs'/(binding+'-upload-render.png'))
 for side,xx in [('back',backx),('front',frontx)]:
  q[0].get_pixmap(matrix=pdf.Matrix(2,2),clip=pdf.Rect(xx*72,y*72,(xx+bw)*72,(y+bh)*72)).save(ROOT/'proofs'/(binding+'-'+side+'-200pct.png'))
 for side,xx in [('back-fold',spine0),('front-fold',frontx)]:
  q[0].get_pixmap(matrix=pdf.Matrix(2,2),clip=pdf.Rect((xx-.45)*72,y*72,(xx+.45)*72,(y+bh)*72)).save(ROOT/'proofs'/(binding+'-'+side+'-200pct.png'))
 q.close()
 return {'file':str(out.relative_to(ROOT)),'width_in':W,'height_in':H,'spine_in':sp,'board_width_in':bw,'board_height_in':bh,'outer_in':edge,'hinge_in':hinge,'barcode_pt':list(barcode),'panel_top_in':y,'front_x_in':frontx,'back_x_in':backx}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--pages',type=int,help='page count for both bindings when they match')
 ap.add_argument('--pages-paperback',type=int);ap.add_argument('--pages-hardcover',type=int)
 ap.add_argument('--interior',choices=sorted(PAPERBACK_CALIPER),default='premium-color',help='ink type the wraps are cut for')
 args=ap.parse_args()
 global INTERIOR;INTERIOR=args.interior
 pp=args.pages_paperback or args.pages;hp=args.pages_hardcover or args.pages
 if not pp or not hp:raise SystemExit('Give --pages-paperback and --pages-hardcover (or --pages for both).')
 provenance=json.loads((ROOT/'build/art-provenance.json').read_text())
 if hashlib.sha256((AS/'portrait-4x.jpg').read_bytes()).hexdigest()!=provenance['upscaled_sha256']:raise SystemExit('Portrait asset hash changed; inspect art and update provenance deliberately.')
 actual={p.name:len(pdf.open(p)) for p in (REPO/'build').glob('ai-memory-guide*.pdf')}
 if not 79<=pp<=828 or not 79<=hp<=550:raise SystemExit('Page count does not support spine text on these covers.')
 for b in ['ebook','paperback','hardcover','proofs']:(ROOT/b).mkdir(exist_ok=True)
 d=pdf.open();p=d.new_page(width=6.875*72,height=11*72);front(p,0,0,6.875,11,True)
 pix=p.get_pixmap(matrix=pdf.Matrix(1600/(6.875*72),2560/(11*72)),alpha=False)
 im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);assert im.size==(1600,2560)
 im.save(ROOT/'ebook/AI-Memory-Kindle-and-EPUB-cover.jpg',quality=96,subsampling=0,dpi=(300,300));im.resize((600,960)).save(ROOT/'proofs/ebook-preview.png');d.close()
 result={'pages_used':{'paperback':pp,'hardcover':hp},'actual_pdf_counts':actual,'paperback':wrap('paperback',pp),'hardcover':wrap('hardcover',hp)}
 (ROOT/'build/geometry.json').write_text(json.dumps(result,indent=2)+'\n')
 (ROOT/'back-cover-copy.txt').write_text('\n\n'.join(COPY)+'\n\n'+BIO+'\n\n'+URL+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
