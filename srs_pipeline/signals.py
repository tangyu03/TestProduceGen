"""文档信号扫描器：高精确率、低召回率的确定性预扫描。
双通道的下界通道：①扫描结果可作为结构化线索注入 LLM prompt 压缩其自由度；
②与 LLM 产物对账（reconcile），差异即评审队列；③audit_source_refs 反幻觉。"""
from __future__ import annotations
import html
import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^#+[ \t]*(\d+(?:\.\d+){0,3})[、.．]?\s*(\S.*?)\s*$")
ENUM = re.compile(r"取值范围[:：]\s*(.+?)(?=[，。；;）)]|$)")
CHANGE = re.compile(r"由(.{1,12}?)变为(.{1,12}?)(?=[（(，。；;]|$)")

RESTRICTIVE = ("必须", "不得", "仅当", "禁止", "不能", "不可", "不超过", "只能", "只允许")
BR_CATEGORY_HINT = [                                    # Step5 信号① 的 category 映射表
    (("超时", "时限", "有效期", "分钟", "天"), "timing"),
    (("权限", "访问控制", "可查看", "可编辑", "可删除"), "authorization"),
    (("计算", "累计", "权重", "平均分", "四舍五入"), "computation"),
]
OP_CATEGORY_TABLE = {                                   # Step1 操作六枚举归类查找表
    "session": ("登录", "注销", "修改密码"),
    "ui": ("排序", "分页", "重置", "收起", "展开", "取消", "关闭"),
    "file": ("上传", "下载"),
    "query": ("查看", "查询", "搜索"),
    "config": ("设置", "超时", "限值"),
}
RUNTIME_BRANCH = ("根据", "分为")                        # Step3 运行时选择型信号
# 文档元信息词（GB/T8567 类 SRS 前言通用）：描述"文档本身"而非系统行为。
# 域门不依赖章节编号（换项目引言编号会变），只按词法/结构排除。
_DOC_META = ("本文档", "本文件", "文档标识", "知识产权", "编写单位",
             "出版日期", "术语和缩略语", "引用文档", "文档概述", "系统概述")

@dataclass
class DocSignals:
    source_refs: list = field(default_factory=list)      # [(章节号, 标题, 行号)]
    state_enums: list = field(default_factory=list)      # 状态枚举候选
    changes: list = field(default_factory=list)          # "由X变为Y"候选
    br_candidates: list = field(default_factory=list)    # 限制性语句候选
    runtime_branches: list = field(default_factory=list) # 运行时分支候选

def scan(text: str) -> DocSignals:
    text = _normalize_doc(text)               # 归一化后再扫描，标题/章节号才能命中
    lines = text.splitlines()
    sig = DocSignals()
    sig.source_refs = [(m.group(1), m.group(2), i)
                       for i, ln in enumerate(lines) if (m := HEADING.match(ln))]

    def section_of(line_no: int) -> str:
        cur = "未命名章节"
        for no, title, ln in sig.source_refs:
            if ln <= line_no:
                cur = f"{no} {title}"
        return cur

    for i, ln in enumerate(lines):
        ref = section_of(i)
        for m in ENUM.finditer(ln):
            values = [v.strip() for v in re.split(r"[、,，/]", m.group(1)) if v.strip()]
            if 2 <= len(values) <= 12:
                sig.state_enums.append({"values": values, "context": ln.strip()[:60],
                                        "source_ref": ref})
        for m in CHANGE.finditer(ln):
            sig.changes.append({"from": m.group(1), "to": m.group(2),
                                "context": ln.strip()[:60], "source_ref": ref})
        kw = next((k for k in RESTRICTIVE if k in ln), None)
        # 域门（Gate A）：表格行是字段规格、元信息词是文档自指，都不是系统行为规则
        # 表格含 markdown（| 开头）与 HTML（<table>/<tr>/<td>/<th>）两种形态，都排除
        if kw and not ln.lstrip().startswith("|") \
                and not re.search(r"<\s*(table|tr|td|th)\b", ln) \
                and not any(w in ln for w in _DOC_META):
            cat = next((c for words, c in BR_CATEGORY_HINT
                        if any(w in ln for w in words)), "validation")
            sig.br_candidates.append({"text": ln.strip(), "keyword": kw,
                                      "category_hint": cat, "source_ref": ref})
        if any(w in ln for w in RUNTIME_BRANCH) and ("选择" in ln or "情况" in ln):
            sig.runtime_branches.append({"context": ln.strip()[:60], "source_ref": ref})
    return sig

def op_category_of(name: str) -> str | None:
    """Step1 操作归类的确定性部分；None 表示需语义判断（默认 crud 由调用方决定）。"""
    for cat, words in OP_CATEGORY_TABLE.items():
        if any(w in name for w in words):
            return cat
    return None

def _normalize_doc(text: str) -> str:
    """把 markdown 原文规整为可审计的纯文本：
    保留标题行前导 #（作结构标记——标题识别靠它而非长度启发式，长标题章节
    如 `#### 20.5.1.6 默认为…（FR-TEST-PLAN-06）**` 才不会漏注册），并解除
    反斜杠转义（原样 `## 4\\.6 项目管理` → `## 4.6 项目管理`），
    使章节号/子项与数据里的 source_ref 逐字可比。"""
    return re.sub(r"\\(.)", r"\1", text)

# 标题行：`#### 4.6 项目管理`、`## 4.8.1评审计划`（必须带 markdown # 前缀，
# 长标题不限长；数字后可不带空格/标点）
_HEAD = re.compile(r"^#+[ \t]*(\d+(?:\.\d+){0,3})[、.．]?\s*(\S.*?)\s*$")
# 目录条目尾缀：`4.4 通用功能要求....7`（标题 + 省略点 + 页码）。目录页行也匹配
# _HEAD，若注册会把章节锚到 TOC 上、正文变空（C15 假阳性）。真实标题无此尾缀。
_TOC_ENTRY = re.compile(r"\.{2,}\d*\s*$")
# 子项标号：全角（1）与半角 (1) 都收（4.13 用转义的 \(1\)）
_ITEM = re.compile(r"[（(](\d+)[）)]")

def _section_bodies(norm: str):
    """标题行号与各节正文区间。返回 (headings, {章节号: 正文全文})，
    正文不含标题行，到下一个标题行截断。目录页条目（省略点+页码尾缀）跳过。"""
    lines = norm.splitlines()
    at = {}
    for i, ln in enumerate(lines):
        m = _HEAD.match(ln)
        if m and not _TOC_ENTRY.search(ln):
            at.setdefault(m.group(1), i)      # 重复章节号取首个
    order = sorted((i, num) for num, i in at.items())
    bodies = {}
    for k, (i, num) in enumerate(order):
        end = order[k + 1][0] if k + 1 < len(order) else len(lines)
        bodies[num] = "".join(lines[i + 1:end])
    return set(at), bodies

def audit_source_refs(model, doc_text: str) -> list:
    """铁律2 的确定性兜底：每条 source_ref 必须能在原文命中（反幻觉）。
    原文先规整（去 #、解转义）；复合引用（如 `4.8.1（5）；4.8.4（2）`）按
    "；"切分后逐段核验：段首章节号必须存在、段内子项标号必须落在该节正文。"""
    issues = []
    norm = _normalize_doc(doc_text)
    headings, bodies = _section_bodies(norm)
    compact = re.sub(r"\s+", "", norm)

    def check(ref, owner):
        if not ref:
            issues.append(f"{owner}: source_ref 为空（输入契约）")
            return
        head = ref.split()[0]
        if re.fullmatch(r"\d+(\.\d+)*", head):           # 纯章节号（可带标题）
            if head not in headings:
                issues.append(f"{owner}: 章节号[{head}]在原文中不存在")
            return
        rp = re.sub(r"\s+", "", ref)                     # 复合引用：章节号+子项…
        for part in re.split(r"[；;]", rp):               # 逐段，段首即归属章节
            if not part:
                continue
            pm = re.match(r"^(\d+(?:\.\d+)*)", part)
            if not pm:                                   # 无章节号 → 退回逐字搜索
                if part not in compact:
                    issues.append(f"{owner}: 原文片段[{ref[:20]}…]未命中原文")
                continue
            sec = pm.group(1)
            if sec not in headings:
                issues.append(f"{owner}: 章节号[{sec}]在原文中不存在")
                return
            body = bodies.get(sec, "")
            for it in _ITEM.finditer(part):
                n = it.group(1)
                if f"（{n}）" not in body and f"({n})" not in body:
                    issues.append(f"{owner}: 子项[{n}]未在章节[{sec}]正文中命中")
                    return

    for t in model.transitions:
        check(t["source_ref"], t["id"])
    for coll in (model.business_rules, model.cross_entity, model.invalid_transitions):
        for x in coll:
            check(x["source_ref"], x["id"])
    for e in model.entities:
        for o in e["operations"]:
            check(o["source_ref"], f"{e['id']}.{o['name']}")
    return issues


# ============ C32 维度出生行序（状态面挂错实体检测） ============
# 需求流程表（19.1/19.3 等）状态列在「动作行」逐行取值；某状态列首现所在行的
# 动作必须就是该维度创建转换的动作。若列首现行早于创建转换动作所在行，说明该
# 状态面出生点被后移（如预通知状态列首现于「能力验证计划发布」行，却由「报名」
# 初始化）——状态面挂到了后建的记录实体上。纯数据驱动，无硬编码列名/动作别名。

def _cell_text(body: str) -> str:
    """HTML <td> 正文 → 纯文本（去标签、解实体、去空白）。"""
    t = re.sub(r"<[^>]+>", "", body)
    t = html.unescape(t)
    return re.sub(r"[\s　]+", "", t)


def _table_grid(html_text: str) -> list:
    """HTML <tr>/<td>（含 rowspan）→ 逐行单元格列表。rowspan 单元在后续行补齐。"""
    grid = []
    pending = []                       # (col, value, remaining)
    for rh in re.findall(r"<tr>(.*?)</tr>", html_text, re.S):
        row = []
        cidx = 0
        while pending and pending[0][0] == cidx:      # 补挂起 rowspan
            col, val, rem = pending.pop(0)
            row.append(val)
            if rem > 1:
                pending.append((cidx, val, rem - 1))
            cidx += 1
        for attrs, body in re.findall(r"<td([^>]*)>(.*?)</td>", rh, re.S):
            while pending and pending[0][0] == cidx:
                col, val, rem = pending.pop(0)
                row.append(val)
                if rem > 1:
                    pending.append((cidx, val, rem - 1))
                cidx += 1
            rs = re.search(r'rowspan="?(\d+)"?', attrs)
            span = int(rs.group(1)) if rs else 1
            row.append(_cell_text(body))
            if span > 1:
                pending.append((cidx, row[-1], span - 1))
            cidx += 1
        grid.append(row)
    return grid


def _parse_flow_tables(text: str) -> list:
    """doc 中所有含「动作」列的 HTML 流程表。
    返回 [{head, rows, act_idx, start_ln}]；head 为列头行，rows 为数据行，
    act_idx 为动作列下标，start_ln 为表起始行号（章节定位用）。"""
    out = []
    for m in re.finditer(r"<table>(.*?)</table>", text, re.S):
        grid = _table_grid(m.group(1))
        hdr = next((i for i, r in enumerate(grid)
                    if any("动作" in c for c in r)), None)
        if hdr is None:                # 枚举/状态分析表无动作列 → 跳过
            continue
        act_idx = next(i for i, c in enumerate(grid[hdr]) if "动作" in c)
        start_ln = text.count("\n", 0, m.start())
        out.append({"head": grid[hdr], "rows": grid[hdr + 1:],
                    "act_idx": act_idx, "start_ln": start_ln})
    return out


def _dimension_by_column(model, col_values: set):
    """列值集 → 承载维度：与各实体维度 states 交集最大者。
    数据驱动（列名别名如「预通知状态→通知状态」靠值域重叠自动消解）；
    交集为零或并列 → None（精度优先，防误报）。返回 (entity_id, dimension_name)。"""
    best = None
    best_hit = 0
    for e in model.entities:
        for d in e["state_dimensions"]:
            states = set(d["states"])
            hit = len(col_values & states)
            if hit > best_hit:
                best, best_hit = (e["id"], d["dimension_name"]), hit
            elif hit and hit == best_hit:
                best = None
    return best if best_hit else None


def audit_dimension_birth(model, doc_text: str) -> list:
    """C32 维度出生行序：流程表状态列首现行 vs 维度创建转换动作行。
    列首现早于创建转换动作所在行 → 状态面出生点被后移，疑似挂错实体。
    返回 issue 字符串列表（调用方 report.error("C32", msg)）。"""
    issues = []
    # 维度创建转换索引：(entity, dimension) → [(action, id), ...]；创建转换 frm 为空
    # 平行流程分支（能力验证/测量审核）各有创建转换（如 E-XM.项目状态：设计方案编制
    # vs 受理用户测量审核报名），须按动作集合整体比对，不得 setdefault 只取首个。
    creation = {}
    for t in model.transitions:
        if not t.get("from"):
            creation.setdefault((t["entity"], t["dimension"]), []).append(
                (t["action"], t.get("id") or t.get("tid")))
    # action → 承载实体集（恰一实体时供消息锚定提示）
    action_entities = {}
    for t in model.transitions:
        action_entities.setdefault(t["action"], set()).add(t["entity"])

    # 流程表所在章节（消息上下文用）：标题行号 → 章节号
    lines = doc_text.splitlines()
    heading_lines = [(i, m.group(1)) for i, ln in enumerate(lines)
                     if (m := HEADING.match(ln))]

    for tb in _parse_flow_tables(doc_text):
        head, rows, act_idx = tb["head"], tb["rows"], tb["act_idx"]
        # 表所在章节：从表起始行往前找最近的标题
        sec = next((num for i, num in reversed(heading_lines)
                    if i <= tb["start_ln"]), "")
        col_values = {}
        first_seen = {}                # 列 → (行号, 动作, 首现值)
        for ri, row in enumerate(rows, 1):
            if len(row) <= act_idx:
                continue
            action = row[act_idx]
            if not action:
                continue
            for ci, ch in enumerate(head):
                if ci == act_idx or ci >= len(row):
                    continue
                if not (("状态" in ch) or ch == "缴费通知单"):
                    continue
                v = row[ci]
                if not v:
                    continue
                col_values.setdefault(ch, set()).update(
                    x for x in re.split(r"[/、，。;；]", v) if x)
                if ch not in first_seen:
                    first_seen[ch] = (ri, action, v)
        for ch, (ri, action, v) in first_seen.items():
            dim = _dimension_by_column(model, col_values[ch])
            if dim is None:
                continue
            eid, dname = dim
            inits = creation.get((eid, dname)) or []
            if not inits:
                continue
            init_actions = {a for a, _ in inits}
            if action in init_actions:      # 首现动作本身就是某创建动作 → 一致
                continue
            # 找任一创建动作在表中最早所在行；创建动作不在表中（操作节出生，
            # 如样品状态/样品制备）→ 跳过
            r_init = next((ri2 for ri2, row in enumerate(rows, 1)
                           if len(row) > act_idx and row[act_idx] in init_actions),
                          None)
            if r_init is None:
                continue
            if ri < r_init:
                a_init = sorted(init_actions)[0]
                tid = next((tid for a, tid in inits if a == a_init), "")
                ents = action_entities.get(action)
                hint = (f"，应锚定于首现动作所属实体 {next(iter(ents))}（项目级）"
                        if ents and len(ents) == 1 else "")
                issues.append(
                    f"维度[{dname}]（实体[{eid}]）在流程表[{sec}]列[{ch}]首现于动作"
                    f"[{action}]（行{ri}，值[{v}]），但创建转换(action=[{a_init}]，"
                    f"{tid})所在行更晚（行{r_init}）。列值早于创建转换出现 → "
                    f"状态面出生点被后移，疑似挂错实体{hint}；修法：创建转换动作须为"
                    f"[{action}]，不得由后建记录实体承载初始化。")
    return issues
