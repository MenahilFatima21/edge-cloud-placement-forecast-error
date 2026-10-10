"""Render REPORT_FINAL.md to a self-contained HTML (images inlined) -> print to PDF from a browser."""
import base64, os, re, markdown
D = os.path.dirname(os.path.abspath(__file__))
md = open(os.path.join(D, 'REPORT_FINAL.md'), encoding='utf-8').read()
html = markdown.markdown(md, extensions=['tables', 'fenced_code'])
def inline(m):
    p = os.path.normpath(os.path.join(D, m.group(1)))
    return 'src="data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode() + '"'
html = re.sub(r'src="([^"]+\.png)"', inline, html)
css = """body{font-family:Georgia,serif;max-width:980px;margin:32px auto;padding:0 16px;line-height:1.5;color:#111;background:#fff}
table{border-collapse:collapse;font-size:12.5px;margin:10px 0;width:100%}th,td{border:1px solid #bbb;padding:4px 6px;vertical-align:top}
th{background:#f0f0f0}img{max-width:100%}code,pre{background:#f6f6f6;font-size:12px}pre{padding:8px;overflow-x:auto}
blockquote{border-left:4px solid #999;margin:8px 0;padding:2px 12px;color:#333}h2{border-bottom:2px solid #333;margin-top:36px}
@media print{body{max-width:none;margin:0}h2{page-break-before:auto}table,img{page-break-inside:avoid}}"""
out = f'<!doctype html><html><head><meta charset="utf-8"><title>G23 COSCO Reproduction and R-GOBI</title><style>{css}</style></head><body>{html}</body></html>'
open(os.path.join(D, 'REPORT_FINAL.html'), 'w', encoding='utf-8').write(out)
print('ok')
