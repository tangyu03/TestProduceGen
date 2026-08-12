# -*- coding: utf-8 -*-
"""把 PT017_output.md 同步到 测试用例-AI版.xlsx。

只覆盖来自原文的列: 用例标识 / 模块 / 用例名称 / 对应需求条目 / 前置条件(Given) / 测试步骤(When) / 预期结果(Then)。
保留第1行表头和第2行示例行; 其余列(测试类型/对应需求内容/测试数据/实测结果/是否通过/备注/测试人员/测试日期)不动。
"""
import re
import openpyxl

MD = r'C:\Users\15831\Downloads\final_pkgV\PT017_output.md'
XLSX = r'C:\Users\15831\Desktop\航天软件功能性\测试用例-AI版.xlsx'

text = open(MD, encoding='utf-8').read()
blocks = re.split(r'\n(?=### )', text)

entries = []
for b in blocks:
    b = b.strip()
    if not b.startswith('### '):
        continue
    m = re.match(r'### (PROC-\d+)[：:]?\s*(.*)', b)
    if not m:
        continue
    pid = m.group(1)
    title = m.group(2).strip()
    cov = re.search(r'\*\*覆盖需求\*\*：(.+)', b)
    coverage = cov.group(1).strip() if cov else ''
    biz = re.search(r'\*\*业务定位\*\*：(.+)', b)
    biz_val = biz.group(1).strip() if biz else ''
    if '｜' in biz_val:
        module = biz_val.split('｜')[-1].strip()
    elif '|' in biz_val:
        module = biz_val.split('|')[-1].strip()
    else:
        module = biz_val
    gsec = re.search(r'\*\*Given\*\*(.*?)(?=\*\*|\Z)', b, re.S)
    given = gsec.group(1).strip() if gsec else ''
    wsec = re.search(r'\*\*When\*\*(.*?)(?=\*\*|\Z)', b, re.S)
    when = wsec.group(1).strip() if wsec else ''
    tsec = re.search(r'\*\*Then\*\*(.*?)(?=\*\*依赖\*\*|\*\*弱依赖\*\*|\Z)', b, re.S)
    then = tsec.group(1).strip() if tsec else ''
    entries.append((pid, title, module, coverage, given, when, then))

print(f'parsed {len(entries)} entries')

wb = openpyxl.load_workbook(XLSX)
ws = wb.active
print('sheet:', ws.title, 'max_row:', ws.max_row)

hdr = {str(c.value).strip(): c.column for c in ws[1] if c.value is not None}
print('headers:', hdr)
col_id = hdr['用例标识']
col_mod = hdr['模块']
col_name = hdr['用例名称']
col_req = hdr['对应需求条目']
col_pre = hdr['前置条件']
col_step = hdr['测试步骤']
col_exp = hdr['预期结果']

START = 3  # 数据从第3行开始(第1行表头, 第2行示例)
n_existing = ws.max_row - START + 1
n_new = len(entries)

# 覆盖已有数据行
for i, (pid, title, module, coverage, given, when, then) in enumerate(entries):
    r = START + i
    ws.cell(row=r, column=col_id, value=pid)
    ws.cell(row=r, column=col_mod, value=module)
    ws.cell(row=r, column=col_name, value=title)
    ws.cell(row=r, column=col_req, value=coverage)
    ws.cell(row=r, column=col_pre, value=given)
    ws.cell(row=r, column=col_step, value=when)
    ws.cell(row=r, column=col_exp, value=then)

# 若原文条目比文件现有行少, 清空多余行的来源列
for r in range(START + n_new, START + n_existing):
    for c in [col_id, col_mod, col_name, col_req, col_pre, col_step, col_exp]:
        ws.cell(row=r, column=c).value = None

wb.save(XLSX)
print(f'synced {n_new} rows (rows {START}..{START+n_new-1}); file total rows now {ws.max_row}')
