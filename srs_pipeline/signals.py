"""文档信号扫描器：高精确率、低召回率的确定性预扫描。
双通道的下界通道：①扫描结果可作为结构化线索注入 LLM prompt 压缩其自由度；
②与 LLM 产物对账（reconcile），差异即评审队列；③audit_source_refs 反幻觉。"""
from __future__ import annotations
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
