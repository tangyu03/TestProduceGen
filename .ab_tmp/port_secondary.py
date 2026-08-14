#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""移植 V1 二级审批内容进 CASC-STEC-PT017.py（一次性数据移植）。

步骤：
  A. op note.role 回填（84 处，按 op 名从 V1 取 role）
  B. 待二级审批 状态（9 任务实体 states + inferred）
  C. 27 条二级转换（从 V1 提取）+ 基础通过转换 t02 precond 收窄 + note comment 更新

输出：.ab_tmp/CASC-STEC-PT017.merged.py（不就地覆盖，审查后落位）。
"""
import ast
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
V1_PATH = os.path.join(_HERE, "..", "srs_data", "CASC-STEC-PT017V1.py")
PT_PATH = os.path.join(_HERE, "..", "srs_data", "CASC-STEC-PT017.py")
OUT_PATH = os.path.join(_HERE, "CASC-STEC-PT017.merged.py")

# entity -> (base_pass_tid, second tids)
ENTITY_TIDS = {
    "E-IMP": ("t02", ("t02b", "t02c", "t03b")),
    "E-REG": ("t08", ("t08b", "t08c", "t09b")),
    "E-ARC": ("t14", ("t14b", "t14c", "t15b")),
    "E-TRF": ("t20", ("t20b", "t20c", "t21b")),
    "E-RET": ("t26", ("t26b", "t26c", "t27b")),
    "E-RCY": ("t32", ("t32b", "t32c", "t33b")),
    "E-OUT": ("t38", ("t38b", "t38c", "t39b")),
    "E-EXP": ("t44", ("t44b", "t44c", "t45b")),
    "E-SCN": ("t50", ("t50b", "t50c", "t51b")),
}
ALL_SEC_TIDS = {tid for _, sec in ENTITY_TIDS.values() for tid in sec}


def node_segment(src, node):
    return ast.get_source_segment(src, node)


# ---------- 1. role map from V1 op notes ----------
v1_src = open(V1_PATH, encoding="utf-8").read()
v1_tree = ast.parse(v1_src)
role_map = {}
for n in ast.walk(v1_tree):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "op":
        name = next((k.value.value for k in n.keywords
                     if k.arg == "name" and isinstance(k.value, ast.Constant)), None)
        for k in n.keywords:
            if k.arg == "note" and isinstance(k.value, ast.Dict):
                for key, val in zip(k.value.keys, k.value.values):
                    if isinstance(key, ast.Constant) and key.value == "role":
                        role_map[name] = ast.unparse(val)
print(f"[1] V1 op role map: {len(role_map)} entries")

# ---------- 2. extract 27 transition blocks from V1 ----------
sec_blocks = {}
for n in ast.walk(v1_tree):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_trans":
        tid = next((k.value.value for k in n.keywords
                    if k.arg == "tid" and isinstance(k.value, ast.Constant)), None)
        if tid in ALL_SEC_TIDS:
            seg = node_segment(v1_src, n)
            # get_source_segment 从 token 起返回，首行丢失行首缩进 → 补 PT017 的 4 空格
            seg = "    " + seg
            ent = next((k.value.value for k in n.keywords
                        if k.arg == "entity" and isinstance(k.value, ast.Constant)), None)
            ref = next((k.value.value for k in n.keywords
                        if k.arg == "source_ref" and isinstance(k.value, ast.Constant)), None)
            sec_blocks[tid] = (ent, seg, ref)
print(f"[2] V1 secondary blocks: {len(sec_blocks)}")
for tid, (ent, seg, ref) in sorted(sec_blocks.items()):
    print(f"    {tid}  entity={ent}  source_ref={ref}  lines={seg.count(chr(10))+1}")
assert len(sec_blocks) == 27, f"expected 27, got {len(sec_blocks)}"
for ent, (_, secs) in ENTITY_TIDS.items():
    for s in secs:
        assert sec_blocks[s][0] == ent, f"{s} entity mismatch"

# ---------- 3. edit PT017.py ----------
pt_src = open(PT_PATH, encoding="utf-8").read()
pt_tree = ast.parse(pt_src)
_lines = pt_src.splitlines(keepends=True)
_line_off = {}
_off = 0
for i, ln in enumerate(_lines, 1):
    _line_off[i] = _off
    _off += len(ln)

def _b2c(line_no, byte_col):
    """ast col_offset 是 UTF-8 字节偏移，换算为行内字符索引。"""
    line = _lines[line_no - 1].rstrip("\r\n")
    if byte_col <= 0:
        return 0
    acc = 0
    for i, ch in enumerate(line):
        if acc == byte_col:
            return i
        acc += len(ch.encode("utf-8"))
        if acc > byte_col:
            return i
    return len(line)

def pos(line, byte_col):
    return _line_off[line] + _b2c(line, byte_col)

def line_end(line):
    return _line_off[line] + len(_lines[line - 1])

edits = []

def rep(start, end, new):
    edits.append((start, end, new))

# ---- Step A: op note.role ----
missing = []
op_count = 0
for n in ast.walk(pt_tree):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "op":
        op_count += 1
        name = next((k.value.value for k in n.keywords
                     if k.arg == "name" and isinstance(k.value, ast.Constant)), None)
        role_src = role_map.get(name)
        if role_src is None:
            missing.append(name)
            continue
        note_kw = next((k for k in n.keywords if k.arg == "note"), None)
        if note_kw is not None and isinstance(note_kw.value, ast.Call):
            end = pos(note_kw.value.end_lineno, note_kw.value.end_col_offset) - 1  # N() 尾部 )
            rep(end, end, f", role={role_src}")
        elif note_kw is not None:
            # 其他形态 note（应无）：整体替换
            nv = note_kw.value
            seg = node_segment(pt_src, nv)
            rep(pos(nv.lineno, nv.col_offset), pos(nv.end_lineno, nv.end_col_offset),
                f'{{"role": {role_src}, **({seg})}}')
        else:
            # 无 note → op 调用尾部补 note=N(role=...)
            close_pos = pos(n.end_lineno, n.end_col_offset) - 1  # op 尾部 )
            if n.lineno == n.end_lineno:
                rep(close_pos, close_pos, f", note=N(role={role_src})")
            else:
                last_line = _lines[n.end_lineno - 1]
                indent = last_line[:len(last_line) - len(last_line.lstrip())]
                rep(close_pos, close_pos, f",\n{indent}note=N(role={role_src})")
print(f"[3A] op 处理 {op_count}，role 缺失 {len(missing)}: {missing}")

# ---- Step B: 待二级审批 state ----
pat_s = '"待审批", "审批通过", "审批拒绝", "待执行", "已完成",'
new_s = '"待审批", "待二级审批", "审批通过", "审批拒绝", "待执行", "已完成",'
n_s = 0
idx = 0
while True:
    i = pt_src.find(pat_s, idx)
    if i < 0:
        break
    rep(i, i + len(pat_s), new_s)
    idx = i + len(pat_s)
    n_s += 1
pat_i = '"inferred": ["草稿", "待审批", "待执行", "已完成"],'
new_i = '"inferred": ["草稿", "待审批", "待二级审批", "待执行", "已完成"],'
n_i = 0
idx = 0
while True:
    i = pt_src.find(pat_i, idx)
    if i < 0:
        break
    rep(i, i + len(pat_i), new_i)
    idx = i + len(pat_i)
    n_i += 1
print(f"[3B] states 替换 {n_s}，inferred 替换 {n_i}")
assert n_s == 9 and n_i == 9, "states/inferred 替换数异常"

# ---- Step C: 27 条转换插入 + t02 收窄 ----
for ent, (base, secs) in ENTITY_TIDS.items():
    base_node = None
    for n in ast.walk(pt_tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_trans":
            tid = next((k.value.value for k in n.keywords
                        if k.arg == "tid" and isinstance(k.value, ast.Constant)), None)
            ent_n = next((k.value.value for k in n.keywords
                          if k.arg == "entity" and isinstance(k.value, ast.Constant)), None)
            if tid == base and ent_n == ent:
                base_node = n
                break
    assert base_node is not None, f"{ent} {base} not found"
    b_start = pos(base_node.lineno, base_node.col_offset)
    b_end = line_end(base_node.end_lineno)
    # precond 收窄
    j = pt_src.find("任务级别为B级或C级", b_start, b_end)
    assert j >= 0, f"{ent} {base}: B级或C级 precond 未找到"
    rep(j, j + len("任务级别为B级或C级"), "任务级别为B级")
    # note comment 更新
    old_c = "C级需二级审批员（t02b）"
    c = pt_src.find(old_c, b_start, b_end)
    if c >= 0:
        rep(c, c + len(old_c), "C级需二级审批员（t02b/t02c）")
    # 插入三条二级转换（在基础块尾部 ) 之后）
    close_pos = pos(base_node.end_lineno, base_node.end_col_offset) - 1
    ins = "\n    # C级二级审批路径：一级通过→待二级审批→二级通过/拒绝\n" + \
          "\n".join(sec_blocks[s][1] for s in secs) + "\n"
    rep(close_pos, close_pos + 1, ")" + ins)
print("[3C] 27 条转换插入 + 9 处 t02 收窄完成")

# ---------- 应用 edits ----------
edits.sort(key=lambda e: (e[0], e[1]), reverse=True)
out = pt_src
for start, end, new in edits:
    out = out[:start] + new + out[end:]
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(out)
print(f"[4] 已写出 {OUT_PATH}（{len(out.splitlines())} 行）")
