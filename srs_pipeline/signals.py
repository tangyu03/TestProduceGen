"""文档信号扫描器：高精确率、低召回率的确定性预扫描。
双通道的下界通道：①扫描结果可作为结构化线索注入 LLM prompt 压缩其自由度；
②与 LLM 产物对账（reconcile），差异即评审队列；③audit_source_refs 反幻觉。"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})[、.．]?\s*(\S.{0,40}?)\s*$")
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

@dataclass
class DocSignals:
    source_refs: list = field(default_factory=list)      # [(章节号, 标题, 行号)]
    state_enums: list = field(default_factory=list)      # 状态枚举候选
    changes: list = field(default_factory=list)          # "由X变为Y"候选
    br_candidates: list = field(default_factory=list)    # 限制性语句候选
    runtime_branches: list = field(default_factory=list) # 运行时分支候选

def scan(text: str) -> DocSignals:
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
        if kw:
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

def audit_source_refs(model, doc_text: str) -> list:
    """铁律2 的确定性兜底：每条 source_ref 必须能在原文命中（反幻觉）。"""
    issues = []
    compact = re.sub(r"\s+", "", doc_text)

    def check(ref, owner):
        if not ref:
            issues.append(f"{owner}: source_ref 为空（输入契约）")
            return
        head = ref.split()[0]
        if re.fullmatch(r"\d+(\.\d+)*", head):
            if not re.search(rf"^{re.escape(head)}[、.．\s]", doc_text, re.M):
                issues.append(f"{owner}: 章节号[{head}]在原文中不存在")
        elif re.sub(r"\s+", "", ref) not in compact:
            issues.append(f"{owner}: 原文片段[{ref[:20]}…]未命中原文")

    for t in model.transitions:
        check(t["source_ref"], t["id"])
    for coll in (model.business_rules, model.cross_entity, model.invalid_transitions):
        for x in coll:
            check(x["source_ref"], x["id"])
    for e in model.entities:
        for o in e["operations"]:
            check(o["source_ref"], f"{e['id']}.{o['name']}")
    return issues
