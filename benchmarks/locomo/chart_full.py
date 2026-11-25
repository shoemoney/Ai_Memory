"""Create a theme-aware local per-category comparison for inline review."""
import html
from full_common import OUT,read
from finalize_full import SYSTEMS,CATEGORIES

def main():
    data=read(OUT/'matched-summary.json');scores=data['systems'];left=145;scale=4.65
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 500" role="img" aria-label="Local category accuracies with 95 percent Wilson intervals">']
    for tick in range(0,101,20):
        x=left+tick*scale
        parts.append(f'<line class="grid" x1="{x}" y1="20" x2="{x}" y2="475"/><text class="tick" x="{x}" y="493" text-anchor="middle">{tick}%</text>')
    for category,name in enumerate(CATEGORIES,1):
        top=26+(category-1)*115;n=scores['full-context']['by_category'][str(category)]['n']
        parts.append(f'<text class="category" x="0" y="{top}">{html.escape(name)} · N={n}</text>')
        for index,(title,key,*_) in enumerate(SYSTEMS):
            row=scores[key]['by_category'][str(category)];y=top+17+index*17
            parts.append(f'<text class="label" x="0" y="{y+4}">{html.escape(title)}</text>')
            if not row['n']:continue
            low,high=[left+100*v*scale for v in row['wilson_95']];x=left+100*row['accuracy']*scale
            tip=f"{title}: {row['correct']}/{row['n']}, {100*row['accuracy']:.1f}%; 95% Wilson {100*row['wilson_95'][0]:.1f}% to {100*row['wilson_95'][1]:.1f}%"
            parts.append(f'<g class="series s{index+1}"><title>{html.escape(tip)}</title><line x1="{low}" y1="{y}" x2="{high}" y2="{y}"/><line x1="{low}" y1="{y-3}" x2="{low}" y2="{y+3}"/><line x1="{high}" y1="{y-3}" x2="{high}" y2="{y+3}"/><circle cx="{x}" cy="{y}" r="4"/></g><text class="label" x="630" y="{y+4}">{row["correct"]}/{row["n"]}</text>')
    parts.append('</svg>')
    page='''<!doctype html><meta charset="utf-8"><style>
body{margin:0;font-family:var(--font-sans,system-ui);color:var(--foreground,CanvasText)}
p{font-size:13px;line-height:1.5;margin:0 0 10px;color:var(--muted-foreground,CanvasText)}
.mobile-hint{display:none}@media(max-width:600px){.mobile-hint{display:inline}}
.chart{width:100%;overflow-x:auto}svg{display:block;width:700px;height:500px}
text{fill:var(--foreground,CanvasText);font-family:var(--font-sans,system-ui)}.label,.tick{font-size:11px}.category{font-size:13px;font-weight:600}
.grid{stroke:var(--border,GrayText);stroke-width:1}.series line{stroke-width:2}.series circle{stroke:var(--background,Canvas);stroke-width:1}
.s1{stroke:var(--chart-1,currentColor);fill:var(--chart-1,currentColor)}.s2{stroke:var(--chart-2,currentColor);fill:var(--chart-2,currentColor)}.s3{stroke:var(--chart-3,currentColor);fill:var(--chart-3,currentColor)}.s4{stroke:var(--chart-4,currentColor);fill:var(--chart-4,currentColor)}.s5{stroke:var(--chart-5,currentColor);fill:var(--chart-5,currentColor)}
</style>'''+f'<p>Exploratory local per-category accuracy, matched N={data["n"]}. Dots show accuracy; bars show descriptive 95% Wilson intervals. Hover a point for its values. The histories and local judge introduce uncertainty beyond these intervals. <span class="mobile-hint">Swipe the chart horizontally for the full scale.</span></p><div class="chart">'+''.join(parts)+'</div>'
    path=OUT/'per-category-chart.html';path.write_text(page);print(path)
if __name__=='__main__':main()
