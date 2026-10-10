"""Assemble docs/REPORT_FINAL.md from REPORT.md, docs/sections/*.md and results/tables/*.md."""
import os, re

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
TAB = os.path.join(ROOT, 'results', 'tables')
SEC = os.path.join(D, 'sections')

slots = {
    '⟨REPRO_TABLE⟩': 'repro_results.md', '⟨REPRO_DIFF⟩': None,
    '⟨GAP_SECTION⟩': 'gap.md', '⟨METHOD_SECTION⟩': 'method.md',
    '⟨EVAL_SECTION⟩': 'eval.md', '⟨DISCUSSION⟩': 'discussion.md',
}
fills = {}
if os.path.exists(os.path.join(SEC, 'fills.md')):
    for block in open(os.path.join(SEC, 'fills.md'), encoding='utf-8').read().split('\n@@')[1:]:
        key, _, body = block.partition('\n')
        fills['⟨' + key.strip() + '⟩'] = body.strip()

txt = open(os.path.join(D, 'REPORT.md'), encoding='utf-8').read()
for _ in range(3):  # sections may contain further placeholders
    for k, f in slots.items():
        txt = txt.replace(k, open(os.path.join(SEC, f), encoding='utf-8').read().strip() if f else '')
    for k, v in fills.items():
        txt = txt.replace(k, v)
    txt = re.sub(r'⟨TABLE:([\w.]+)⟩',
                 lambda m: open(os.path.join(TAB, m.group(1)), encoding='utf-8').read().strip(), txt)
# Figure paths are relative to docs/sections in the sections; fix for docs/
txt = txt.replace('](../results/', '](../results/')
left = re.findall(r'⟨[^⟩]+⟩', txt)
open(os.path.join(D, 'REPORT_FINAL.md'), 'w', encoding='utf-8').write(txt)
print('written; unresolved placeholders:', left)
