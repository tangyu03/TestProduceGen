# -*- coding: utf-8 -*-
"""把 PT017_output.md 中 Given/Then 段的 "- " 无序列表改为 "1. 2. 3." 有序编号。
When 段保持原样(已经是编号)。其余行不动。"""
import re

MD = r'C:\Users\15831\Downloads\final_pkgV\PT017_output.md'

with open(MD, encoding='utf-8') as f:
    lines = f.readlines()

header_re = re.compile(r'^(\*\*[^*]+\*\*)\s*')
section = None  # None | Given | When | Then
counter = 0
out = []
changed = 0
for line in lines:
    hm = header_re.match(line)
    if hm:
        h = hm.group(1)
        if h in ('**Given**', '**When**', '**Then**'):
            section = h.strip('*')
            counter = 0
        else:
            section = None
        out.append(line)
        continue
    if section in ('Given', 'Then'):
        m = re.match(r'^-\s+', line)
        if m:
            counter += 1
            out.append(f'{counter}. ' + line[m.end():])
            changed += 1
            continue
    out.append(line)

with open(MD, 'w', encoding='utf-8') as f:
    f.writelines(out)

print(f'done, renumbered {changed} lines')
