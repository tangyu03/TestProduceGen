#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constraint-referenced semantic field registry (Step 3) — **全量派生层**。

P2 的 constraint 前提引用若干领域字段（评级/评审组人数/组长专家数/暂停前计划
状态/评审计划超时类型/各项打分/选入次数/连续密码错误次数）。本模块是这些字段的
唯一注册表，且**不手抄任何领域数据**——字段集合、值域、kind、value_type、
strip_suffix、aliases、count_aliases、value_normalization、anchors、
ref_state_dimension 全部从**本次运行的 P1 输入**（`model_view(p1)` 适配的
domain_model/state_and_flow/_meta）**派生**。本模块不再硬编码任何 SRS 域，
跑哪个项目注册表就由哪个项目的 P1 生成。

旧架构是 `srs_data/constraint_field_overlay.py` 手写 8 条语义增量 + 本模块派生
值域。用户裁定：overlay 是第二份手抄源，删掉，全部改从真源推导（决策 A/B 见
context/DECISIONS.md）。

派生规则（每一条都是单一定式，不是脆弱 NLP）：

**1. 字段集合**（`_discover_fields`）
  a) 分支维度（`branch_dimensions`）里**非本实体态维度**者 → 字段：
     `项目评级`/`评审组人数`/`暂停前计划状态`/`评审计划超时类型`；
     `项目阶段` 是 E-PROJ 自己的态维度 → 排除。
  b) transition constraint 前提**表层语法**发现的无分支字段：
     `只有N次…机会` → 选入次数；`只能有一个…` → 组长专家数；
     `…全部为零` → 各项打分；`连续…N次` → 连续密码错误次数。

**2. canonical 名字**（`_canonical_name`）
  剥实体名前缀；**若剥后短名仍被约束语料引用则用短名**（项目评级→评级，因为
  约束表层写"评级"），否则保留全名（评审计划超时类型，"超时类型"单独从未在
  语料出现）。

**3. kind / value_type**（`_derive_kind_value_type`）
  分支维度全为（数字）字符串且可转 int → config/int；表层 occurrence/consecutive
  → counter/int；numeric_zero → attribute/int；singleton → config/int；闭集 ⊆
  某实体态维度态名 → state_snapshot/str（ref_state_dimension = 该态维度）；
  其余 attribute/str。

**4. strip_suffix**（`_build_record`）
  分支值集的最长公共后缀（下发超时/启动超时/… → "超时"）。

**5. aliases**（`_derive_aliases`）
  config 表层"…由<名词>…组成"主语（评审组）；singleton 表层名词（组长专家）；
  同实体属性 desc 值域与字段值集相等 → 其名的最长公共后缀（开题/验收评价结果
  → "评价结果"→评级）。

**6. count_aliases**（`_derive_count_aliases`）
  聚合表层 `(累计|连续)N次<对象>` / `连续<对象>N次` 的计数对象，若命中某字段
  名/别名则记为该字段 count_alias（o03"累计3次评级"→评级、o04"累计10次项目
  阶段评价结果"→评级、u03"连续密码错误3次"→连续密码错误次数）。

**7. value_normalization**（`_derive_normalization`）
  值域元素互不冲突的前缀 → 前缀归一（优→优秀/良→良好；超时型前缀+strip_suffix
  往返恒等，不改变值）；singleton 表层的中文数字 → 阿拉伯（"有且只能有一个…"
  → {"一":"1"}）。

**8. anchors**（`_derive_anchors`）
  写点 transition 的 from/to 态：
  - config → 配置表层的 to 态（p01→已建立）；
  - counter/numeric → 表层 transition 的 from 态（选入次数→待选入、连续密码
    错误次数→未锁定、各项打分→已保存）；
  - 超时型 attribute（带 strip_suffix）→ 所有 `剥后缀值+时限超时` 触发 transition
    的 from 态（**6 态** {已建立,待启动,待评审,评审中,暂停,已完成}，决策 A；
    p15/p16/p17 的 评审中/暂停 写点必须在内）；
  - 其他 attribute（评级）→ 引用其 canonical 名（不含别名/值 → 不误收读点）的
    transition 的 from 态（t07a-d → 待归档；t02 只写别名"评价结果"不写"评级"→
    不引入 待选入）；
  - state_snapshot → 闭集（ref_state_dimension 态集）。

加载时对照模型 fail-fast（源分支维度/实体/维度必须存在、anchor 状态可解析、
闭集 ⊆ 维度态名、config 值为 int、value_type 仅 str|int、别名键无冲突）。模型
一改，这里当场报错，不再静默漂移。锚点由写点扫描**全量派生**，故"引用写点 ⊆
锚点"按构造成立，无需单独校验（决策 A 原 fail-fast 因此移除——见 DECISIONS.md）。

消费方（不变）：
  - P2 constraint 谓词解析器（context/generate_obligation_model.py）三处迭代
    build_registry 产物：_resolve_field_from_text（name+aliases 最长子串）、
    _parse_occurrence_when（值在名前的反序表层）、_resolve_counter_from_text
    （count_aliases）；_normalize_constraint_value 读 value_normalization/
    value_type/strip_suffix。
  - S1（nodes/s1_generation.py）predicate_phase_lower_bound() 算谓词相位下界。
  - phase 下界从不硬编码进字段记录，由 field_phase_lower_bound() 运行时对照
    **当前** dep_state_phase_map 推导。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

# repo root 显式入 sys.path：兼容 `python context/generate_obligation_model.py`
# （script-dir 模式，sys.path[0]=context/）与 `python -m ...` 两种调用。
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ── 表层语法（跨类型数据表；字段发现 / 锚点 / 别名 / 计数 / 归一共用） ────────
# 每一型一行，机制层只遍历；新增形态在此加行，不写散落 if。
_OCCURRENCE_RE = re.compile(r"只有\s*\d+\s*次\s*([^，。]+?)机会")          # t02: 只有 1 次选入机会
_SINGLETON_RE = re.compile(r"(?:有且只能|只能)有一个\s*([^，。]+)")         # p01: 有且只能有一个组长专家
_SINGLETON_NUM_RE = re.compile(r"有且只能有\s*([一壹二两三四五六七八九十\d]+)\s*个")  # 中文数字 → 阿拉伯
_NUMERIC_ZERO_RE = re.compile(r"([^，。]+?)全部为零")                       # s03: 项目各项打分全部为零
_CONSECUTIVE_RE = re.compile(r"连续\s*([^，。\s\d]+?)\s*(\d+)\s*次")        # u03: 连续密码错误 3 次
_CONFIG_CHOICE_RE = re.compile(r"([^，。]+?)由\s*([^，。]+?)\s*(?:组成|构成)")  # p01: 评审组由 5、7 或 9 个专家组成
_AGGREGATE_RE = re.compile(r"(?:累计|连续)\s*\d+\s*次\s*([^为\s，。；]+)")   # o03/o04: 累计 N 次<对象>

# 中文数字 → 阿拉伯（通用跨字段映射，非领域数据）。
_CN_NUM = {"一": "1", "壹": "1", "二": "2", "两": "2", "贰": "2", "三": "3",
           "叁": "3", "四": "4", "肆": "4", "五": "5", "伍": "5", "六": "6",
           "陆": "6", "七": "7", "柒": "7", "八": "8", "捌": "8", "九": "9", "玖": "9"}


def _is_int_str(v):
    return isinstance(v, str) and v.strip().isdigit()


# ── 本次 P1 输入：唯一机器可读事实源 ─────────────────────────────────
def model_view(p1: dict) -> SimpleNamespace:
    """把 P1 JSON 的三条路径适配为派生函数需要的 `.entities/.transitions/
    .branch_dimensions` 视图。元素仍是 dict，派生函数用 `.get()/[]` 访问，
    与 DomainModel 的 transition/entity 形状完全同构（P1 JSON 即 build() 序列化）。

    三者与 DomainModel 同源：`domain_model.entities`、
    `state_and_flow.transitions`、`_meta.branch_dimensions`（model.py 序列化
    时 meta["branch_dimensions"] = self.branch_dimensions 是同一对象）。
    """
    return SimpleNamespace(
        entities=p1["domain_model"]["entities"],
        transitions=p1["state_and_flow"]["transitions"],
        branch_dimensions=p1["_meta"].get("branch_dimensions", []),
    )


def _entity(model, eid):
    return next((e for e in model.entities if e["id"] == eid), None)


def _entity_name(model, eid):
    e = _entity(model, eid)
    return (e or {}).get("name") or eid


def _dim_states(model, eid, dim):
    """实体维度 → 态名列表；实体/维度任一缺失 → None。"""
    e = _entity(model, eid)
    if e is None:
        return None
    for d in e.get("state_dimensions", []):
        if d["dimension_name"] == dim:
            return list(d["states"])
    return None


def _state_dims(model, eid):
    """实体自身的态维度名集合（字段发现时据此排除状态维度）。"""
    e = _entity(model, eid)
    return {d["dimension_name"] for d in (e or {}).get("state_dimensions", [])}


def _state_dim_containing(model, eid, vals):
    """值集 ⊆ 的态维度（state_snapshot 判定）：值全是某态维度态名 → 该维度名。"""
    for d in (_entity(model, eid) or {}).get("state_dimensions", []):
        if all(v in d["states"] for v in vals):
            return d["dimension_name"]
    return None


def _branch_values(model, ent, dim):
    """分支维度取值 → 列表；缺失/为空 → raise（fail-fast）。"""
    for d in model.branch_dimensions:
        if d.get("entity") == ent and d.get("dimension") == dim:
            vals = list(d.get("values") or [])
            if not vals:
                raise ValueError(
                    f"分支维度 {ent}.{dim} 存在但 values 为空（数据源）")
            return vals
    raise ValueError(
        f"分支维度 {ent}.{dim} 不在 P1 输入（检查名称或删除/改源对应字段）")


def _precondition_texts(transition):
    """transition 的 constraint 前提文本列表（跨类型数据表，供表层扫描）。"""
    out = []
    for p in transition.get("preconditions") or []:
        txt = (p.get("text") or "").strip()
        if txt and p.get("type") in ("constraint", "when"):
            out.append(txt)
    return out


def _common_suffix(strings):
    """最长公共后缀；空或等于某整个元素 → 不返回（避免把单元素当后缀）。"""
    if not strings:
        return ""
    s = strings[0]
    for x in strings[1:]:
        while s and not x.endswith(s):
            s = s[1:]
        if not s:
            break
    if not s or any(x == s for x in strings if x != s):
        return ""
    return s


def _stem_referenced_independently(txt, v, suffix):
    """值 v（剥公共后缀 suffix 得词干）在文本中被**独立引用**（词干后跟的不是
    后缀本身）。纯数据驱动、无领域词：struct_srs "下发时限超时" 里词干"下发"后
    跟"时限超时"（非"超时"开头）→ 独立引用；PT017 "任务级别为A级" 里词干"A"
    后正是后缀"级"（值本体）→ 非独立引用。词干后无内容（文本末尾）也非独立。"""
    stem = v[:-len(suffix)]
    i = txt.find(stem)
    while i >= 0:
        tail = txt[i + len(stem):]
        if tail and not tail.startswith(suffix):
            return True
        i = txt.find(stem, i + 1)
    return False


# ── 字段发现 ────────────────────────────────────────────────────────────
def _corpus_refers(model, name):
    """短名是否被约束语料引用（canonical 名剥离判定）。只扫 transition
    constraint 前提（字段引用出现处），不扫 BR/prohibit（避免子串误判）。"""
    for t in model.transitions:
        for txt in _precondition_texts(t):
            if name in txt:
                return True
    return False


def _canonical_name(model, entity, dim):
    """剥实体名前缀；剥后短名仍被语料引用 → 用短名，否则保留全名。"""
    ent_name = _entity_name(model, entity)
    name = dim
    if dim.startswith(ent_name) and len(dim) > len(ent_name):
        short = dim[len(ent_name):]
        if _corpus_refers(model, short):
            name = short
    return name


def _strip_entity_prefix(model, text):
    """剥任意实体名前缀（"项目各项打分"→剥 E-PROJ 名"项目"→"各项打分"）。
    只剥一次；剥后不得为空。"""
    for e in model.entities:
        n = e["name"]
        if text.startswith(n) and len(text) > len(n):
            return text[len(n):]
    return text


def _noun_to_field_name(model, surface, noun):
    """表层名词 → 字段名定式（跨类型数据表驱动的单一定式）。"""
    noun = _strip_entity_prefix(model, noun)
    if surface == "occurrence":
        return noun[:-len("机会")] + "次数" if noun.endswith("机会") else noun + "次数"
    if surface == "singleton":
        return noun + "数"
    if surface == "consecutive":
        return "连续" + noun + "次数"
    return noun  # numeric_zero：各项打分


def _scan_surfaces(t):
    """在一条 transition 的 constraint 前提上扫全部表层，返回发现列表。
    每条 = {surface, entity, noun}。"""
    out = []
    ent = t.get("entity")
    for txt in _precondition_texts(t):
        m = _OCCURRENCE_RE.search(txt)
        if m:
            out.append({"surface": "occurrence", "entity": ent, "noun": m.group(1)})
        m = _SINGLETON_RE.search(txt)
        if m:
            out.append({"surface": "singleton", "entity": ent, "noun": m.group(1)})
        m = _NUMERIC_ZERO_RE.search(txt)
        if m:
            out.append({"surface": "numeric_zero", "entity": ent, "noun": m.group(1)})
        m = _CONSECUTIVE_RE.search(txt)
        if m:
            out.append({"surface": "consecutive", "entity": ent, "noun": m.group(1)})
    return out


def _discover_fields(model):
    """字段集合 = 非本实体态维度的分支维度 + 表层发现的无分支字段。
    返回 {canonical_key: {entity, name, dimension, surface}}。"""
    fields: dict[str, dict] = {}
    # a) 分支维度（排除实体自身态维度）
    for d in model.branch_dimensions:
        ent, dim = d["entity"], d["dimension"]
        if dim in _state_dims(model, ent):
            continue
        name = _canonical_name(model, ent, dim)
        fields.setdefault(f"{ent}.{name}", {"entity": ent, "dimension": dim,
                                            "surface": None})
    # b) 表层发现（去重：已存在键 → 仅补 surface 标注）
    for t in model.transitions:
        for hit in _scan_surfaces(t):
            ent = hit["entity"]
            name = _noun_to_field_name(model, hit["surface"], hit["noun"])
            key = f"{ent}.{name}"
            if key not in fields:
                fields[key] = {"entity": ent, "dimension": None, "surface": None,
                               "noun": None}
            fields[key]["surface"] = hit["surface"]
            fields[key]["noun"] = hit["noun"]
    return fields


# ── 记录派生 ────────────────────────────────────────────────────────────
def _attr_values(attr):
    """属性 desc 的"取值范围：X/Y/Z" → 值列表；无 → None。按 ；分段。"""
    for seg in (attr.get("desc") or "").split("；"):
        if "取值范围" in seg and "：" in seg:
            vals = [x.strip() for x in seg.split("：", 1)[1].split("/") if x.strip()]
            if vals:
                return vals
    return None


def _attrs_sharing_values(model, eid, vals):
    """同实体属性中 desc 值域 == 字段值集的属性名（共享值域 → 别名来源）。"""
    e = _entity(model, eid)
    if e is None:
        return []
    target = set(vals)
    names = []
    for a in e.get("attributes", []):
        av = _attr_values(a)
        if av and set(av) == target:
            names.append(a["name"])
    return names


def _config_choice_ints(txt):
    """config 表层 '…由<vals>个专家组成/构成' 的取值 int 集；无 → None。"""
    m = _CONFIG_CHOICE_RE.search(txt)
    if not m:
        return None
    ints = re.findall(r"\d+", m.group(2))
    return {int(x) for x in ints} if ints else None


def _config_subject(txt):
    """config 表层主语（"评审计划的评审组由…" → "评审组"，剥"…的"前缀）。"""
    m = _CONFIG_CHOICE_RE.search(txt)
    if not m:
        return None
    subj = m.group(1)
    if "的" in subj:
        subj = subj[subj.rfind("的") + 1:]
    return subj or None


def _derive_aliases(model, spec):
    """别名来源（每条都有结构化出处）：
    - config 表层主语（评审组由…组成 → 评审组）；
    - singleton 表层名词（组长专家）；
    - 分支字段共享值域属性名的公共后缀（开题/验收评价结果 → 评价结果 → 评级）。"""
    ent = spec["entity"]
    aliases = []
    if spec.get("surface") == "singleton":
        aliases.append(spec.get("noun"))
    if spec.get("surface") is None and spec.get("dimension"):
        try:
            vals = _branch_values(model, ent, spec["dimension"])
        except ValueError:
            vals = []
        if vals and all(isinstance(v, int) or _is_int_str(v) for v in vals):
            # config：取值集合匹配 config 表层 → 主语即别名
            target = {int(v) for v in vals}
            for t in model.transitions:
                if t.get("entity") != ent:
                    continue
                for txt in _precondition_texts(t):
                    if _config_choice_ints(txt) == target:
                        subj = _config_subject(txt)
                        if subj:
                            aliases.append(subj)
        elif vals and all(isinstance(v, str) for v in vals):
            # attribute/state_snapshot：共享值域属性 → 公共后缀
            shares = _attrs_sharing_values(model, ent, vals)
            suffix = _common_suffix(shares)
            if suffix:
                aliases.append(suffix)
    # 去重，且别名不得与 canonical 名同
    out = []
    for a in aliases:
        if a not in out and a != spec["name"]:
            out.append(a)
    return out


def _derive_count_aliases(model, spec, aliases):
    """聚合表层计数对象 → count_alias（对象含字段名/别名则归属该字段）。
    `累计N次<对象>`（o03/o04）与 `连续<对象>N次`（u03）两种词序都扫。"""
    names = [spec["name"]] + list(aliases)
    if spec.get("dimension"):
        names.append(spec["dimension"])
    found = []
    for t in model.transitions:
        for txt in _precondition_texts(t):
            objs = [m.group(1) for m in _AGGREGATE_RE.finditer(txt)]
            objs += [m.group(1) for m in _CONSECUTIVE_RE.finditer(txt)]
            for obj in objs:
                for nm in names:
                    if nm in obj or obj in nm:
                        if obj not in found:
                            found.append(obj)
                        break
    return found


def _derive_normalization(model, spec):
    """值域元素互不冲突的前缀 → 前缀归一（优→优秀/良→良好；超时型前缀经
    strip_suffix 往返恒等）；singleton 中文数字 → 阿拉伯（{"一":"1"}）。"""
    norm = {}
    if spec.get("surface") == "singleton":
        for tr in model.transitions:
            for txt in _precondition_texts(tr):
                m = _SINGLETON_NUM_RE.search(txt)
                if m and m.group(1) in _CN_NUM:
                    norm[m.group(1)] = _CN_NUM[m.group(1)]  # {"一":"1"}
        return norm
    vals = []
    if spec.get("dimension"):
        try:
            vals = _branch_values(model, spec["entity"], spec["dimension"])
        except ValueError:
            vals = []
    for v in vals:
        if not isinstance(v, str) or not v:
            continue
        for pre_len in range(1, len(v)):
            pre = v[:pre_len]
            if not any(x != v and isinstance(x, str) and x.startswith(pre)
                       for x in vals):
                norm[pre] = v
    return norm


def _anchor_state_for(model, spec, t):
    """transition 是否引用字段写点 → 是则返回锚点态（config 用 to，其余 from）。"""
    if t.get("entity") != spec["entity"]:
        return None
    surface = spec.get("surface")
    for txt in _precondition_texts(t):
        if surface == "numeric_zero" and _NUMERIC_ZERO_RE.search(txt):
            return t.get("from")
        if surface == "occurrence" and _OCCURRENCE_RE.search(txt):
            return t.get("from")
        if surface == "consecutive" and _CONSECUTIVE_RE.search(txt):
            return t.get("from")
        if surface == "singleton" and _SINGLETON_RE.search(txt):
            return t.get("to")
        if surface is None and spec.get("dimension"):
            try:
                vals = _branch_values(model, spec["entity"], spec["dimension"])
            except ValueError:
                continue
            if vals and all(isinstance(v, int) or _is_int_str(v) for v in vals):
                # config：取值集合匹配 config 表层 → 配置完成态 to
                if _config_choice_ints(txt) == {int(v) for v in vals}:
                    return t.get("to")
            elif vals and all(isinstance(v, str) for v in vals):
                suffix = _common_suffix([v for v in vals if isinstance(v, str)])
                if suffix:
                    # 超时型：词干在文本中被独立引用（"下发"+"时限超时"）→ 写点
                    # from。公共后缀是值本体（A级/B级/C级 的"级"）时非独立引用。
                    for v in vals:
                        if v.endswith(suffix) and _stem_referenced_independently(txt, v, suffix):
                            return t.get("from")
                # 普通属性（评级/任务级别）：引用 canonical 名（不含别名/值 →
                # 不误收读点）。公共后缀（如"级"）非超时语义时不得挡住普通属性
                # 判定——超时分支未命中仍回落到这里（A级/B级/C级 → "任务级别"）。
                if spec["name"] in txt:
                    return t.get("from")
    return None


def _derive_anchors(model, spec):
    """锚点 = 字段写点的 from/to 态；state_snapshot → 闭集（ref_state_dimension）。"""
    ent = spec["entity"]
    # state_snapshot：锚点 = 闭集（含源态维度）
    dim = spec.get("dimension")
    vals = []
    if dim:
        try:
            vals = _branch_values(model, ent, dim)
        except ValueError:
            vals = []
        if vals and all(isinstance(v, str) for v in vals):
            ssdim = _state_dim_containing(model, ent, vals)
            if ssdim is not None:
                return [{"entity": ent, "dimension": ssdim, "state": v}
                        for v in vals]
    # 其余 kind：锚点 = 引用写点 transition 的 from（config 为 to）
    refs = [(t, s) for t in model.transitions
            if (s := _anchor_state_for(model, spec, t)) is not None]
    if dim:
        # 分支字段写点常只声明在 note.branch_dimension 上（字段名引用落在
        # state_ref 前提 / expected_results / note，不在 constraint/when 文本，
        # _precondition_texts 扫不到）→ 数据驱动兜底，与文本扫描取并集
        # （防部分打标漏锚；golden 任务级别文本扫描已全覆盖，并集不变）。
        # 限定本实体：跨实体转换（如 E-YT 预通知审批按 E-XM.项目类型 分支）只
        # 声明"该转换按此维度分支"，不是字段写点；混入会把对方维度（预通知状态）
        # 错锚进本实体（anchors 恒 {ent, 转换自身 dimension}，跨实体不可能合法）。
        gated = [t for t in model.transitions
                 if t.get("entity") == ent
                 and (t.get("note") or {}).get("branch_dimension") == dim]
        if gated:
            is_config = bool(vals) and all(
                isinstance(v, int) or _is_int_str(v) for v in vals)
            for t in gated:
                s = t.get("to") if is_config else t.get("from")
                if s:
                    refs.append((t, s))
    if not refs:
        if dim:
            # 分支字段：写点引用完全缺失 = 配置型分支（分支维度声明注明
            # "转换层无 branch 转换属合法"，如 评分方式 分值/权重 仅影响计算与
            # 展示）。无状态机写点 → 空锚点，下游 field_phase_lower_bound 返回
            # None → 保守 P0，安全降级而非漂移。
            return []
        raise ValueError(
            f"[{ent}.{spec['name']}] 找不到锚点引用 transition（数据源已漂移）")
    dims = sorted({t.get("dimension") for t, _ in refs} - {None})
    if not dims:
        raise ValueError(f"[{ent}.{spec['name']}] 锚点维度缺失（引用 transition 无 dimension）")
    if len(dims) == 1:
        # 单维度：保持旧形状（dims[0] + 态名排序），字节级兼容既有基线。
        states = sorted({s for _, s in refs} - {None})
        return [{"entity": ent, "dimension": dims[0], "state": s}
                for s in states]
    # 分支字段跨态维度（如 项目归档分支=项目状态×项目阶段）：dims[0] 坍缩
    # 会错锚（开题 挂到 项目状态 → 相位解析落空），按 transition 保留各自维度。
    anchors, seen = [], set()
    for t, s in refs:
        d = t.get("dimension")
        if d and s and (d, s) not in seen:
            seen.add((d, s))
            anchors.append({"entity": ent, "dimension": d, "state": s})
    return anchors


def _derive_kind_value_type(model, spec):
    """kind + value_type + ref_state_dimension 定式。"""
    dim = spec.get("dimension")
    vals = []
    if dim:
        try:
            vals = _branch_values(model, spec["entity"], dim)
        except ValueError:
            vals = []
    if dim and vals and all(isinstance(v, int) or _is_int_str(v) for v in vals):
        return "config", "int", None                    # 评审组人数 5/7/9
    if spec.get("surface") in ("occurrence", "consecutive"):
        return "counter", "int", None                    # 选入次数 / 连续密码错误次数
    if spec.get("surface") == "numeric_zero":
        return "attribute", "int", None                  # 各项打分
    if spec.get("surface") == "singleton":
        return "config", "int", None                     # 组长专家数 = 1
    if dim and vals and all(isinstance(v, str) for v in vals):
        ssdim = _state_dim_containing(model, spec["entity"], vals)
        if ssdim is not None:
            return "state_snapshot", "str", f"{spec['entity']}.{ssdim}"  # 暂停前计划状态
    return "attribute", "str", None                      # 评级 / 评审计划超时类型


def _is_timeout_field(model, ent, vals):
    """超时型字段判据：某值的词干（剥公共后缀）在 transition 前提中被独立引用
    （词干后跟的不是后缀本身，见 _stem_referenced_independently）。纯数据驱动、
    无领域词。只有超时型设置 strip_suffix——普通 attribute（评级、任务级别）
    值域的公共后缀（A级/B级/C级 的"级"）是值本体的一部分，不得剥。"""
    suffix = _common_suffix([v for v in vals if isinstance(v, str)])
    if not suffix:
        return False
    for t in model.transitions:
        if t.get("entity") != ent:
            continue
        for txt in _precondition_texts(t):
            for v in vals:
                if v.endswith(suffix) and _stem_referenced_independently(txt, v, suffix):
                    return True
    return False


def _build_record(model, key, spec) -> dict:
    """从发现 spec 派生完整记录。派生失败 → raise（fail-fast，数据源已漂移）。"""
    ent, name = key.split(".", 1)
    kind, value_type, ref_state_dimension = _derive_kind_value_type(model, spec)
    spec = {**spec, "name": name}
    aliases = _derive_aliases(model, spec)
    rec = {
        "entity": ent, "name": name, "kind": kind,
        "value_type": value_type, "ref_state_dimension": ref_state_dimension,
        "aliases": aliases,
        "count_aliases": _derive_count_aliases(model, spec, aliases),
        "value_normalization": _derive_normalization(model, spec),
        "strip_suffix": None,
        "values": None, "value_closed_set": None,
    }
    dim = spec.get("dimension")
    if dim:
        vals = _branch_values(model, ent, dim)
        if kind == "state_snapshot":
            rec["value_closed_set"] = vals
        elif kind == "config":
            rec["values"] = [int(v) for v in vals]
        else:
            rec["values"] = vals
            if _is_timeout_field(model, ent, vals):
                # 仅超时型 attribute 可剥公共后缀（下发超时→下发）；
                # 普通 attribute（评级/任务级别）值域是完整值本体，不剥。
                rec["strip_suffix"] = _common_suffix(
                    [v for v in vals if isinstance(v, str)])
    if kind == "config" and not rec["values"]:
        rec["values"] = [1]  # singleton（组长专家数）无分支维度，恒 1
    rec["populated_anchors"] = _derive_anchors(model, spec)
    return rec


def _alias_keys(registry: dict) -> dict:
    """从各 canonical 记录的 aliases 合成别名注册键（不再手写第二条记录）。"""
    add = {}
    for key, rec in registry.items():
        if rec.get("kind") == "alias":
            continue
        for al in rec.get("aliases") or []:
            add[f"{rec['entity']}.{al}"] = {
                "entity": rec["entity"], "name": al, "kind": "alias",
                "canonical": key, "values": None, "value_normalization": {},
                "strip_suffix": None,
                "populated_anchors": [], "ref_state_dimension": None,
                "value_closed_set": None,
            }
    return add


def _validate_registry(model, registry: dict) -> None:
    """对照模型 fail-fast：锚点状态可解析、闭集 ⊆ 维度态名、config 值为 int、
    value_type 仅 str|int、别名键无冲突。任一不符 → raise，禁止静默 P0 降级。"""
    errors: list[str] = []
    for key, rec in registry.items():
        if rec.get("kind") == "alias":
            if rec.get("canonical") not in registry:
                errors.append(f"别名键 {key} 的 canonical 缺失: {rec.get('canonical')}")
            continue
        if _entity(model, rec["entity"]) is None:
            errors.append(f"[{key}] 实体 {rec['entity']} 不存在于 P1 输入")
        for a in rec.get("populated_anchors") or []:
            sts = _dim_states(model, a["entity"], a["dimension"])
            if sts is None:
                errors.append(
                    f"[{key}] anchor 维度 {a['entity']}.{a['dimension']} 不存在")
            elif a["state"] not in sts:
                errors.append(
                    f"[{key}] anchor 状态 {a['state']} 不在 "
                    f"{a['entity']}.{a['dimension']} 态集 {sts}")
        cs = rec.get("value_closed_set")
        if cs and rec.get("ref_state_dimension"):
            ent, dim = rec["ref_state_dimension"].split(".", 1)
            sts = _dim_states(model, ent, dim)
            for v in cs:
                if sts is None or v not in sts:
                    errors.append(f"[{key}] 闭集值 {v} 不在 {ent}.{dim} 态集")
        if rec.get("kind") == "config" and (rec.get("values") or []):
            for v in rec["values"]:
                if not isinstance(v, int):
                    errors.append(f"[{key}] config 值非 int: {v!r}")
        vt = rec.get("value_type")
        if vt not in ("str", "int"):
            errors.append(f"[{key}] value_type 非法: {vt!r}（仅 str|int）")
        if vt == "int" and (rec.get("values") or []):
            for v in rec["values"]:
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    errors.append(f"[{key}] value_type=int 但值非数值: {v!r}")
    if errors:
        raise ValueError(
            "constraint_fields 注册表与 P1 输入不一致（数据源已漂移）:\n  "
            + "\n  ".join(errors))


def build_registry(model) -> dict:
    """从 P1 适配视图派生完整注册表（canonical 记录 + 别名键 + fail-fast 校验）。

    事实源是本次运行的 P1 输入；每次运行由 P2 调用一次并序列化进 coverage_model。
    """
    fields = _discover_fields(model)
    registry: dict[str, dict] = {}
    for key, spec in fields.items():
        registry[key] = _build_record(model, key, spec)
    aliases = _alias_keys(registry)
    collisions = set(aliases) & set(registry)
    if collisions:
        raise ValueError(f"别名键与 canonical 键冲突: {sorted(collisions)}")
    registry.update(aliases)
    _validate_registry(model, registry)
    return registry


def resolve_field(field_ref: dict, registry: dict | None) -> dict | None:
    """按 {entity, name} 解析字段记录；别名（评价结果→评级、评审组→评审组人数）
    归一化到 canonical 记录。返回 None 表示未注册（含 registry 未传入 = 保守
    「不可解析」，与字段确实未注册语义一致）。"""
    entity = (field_ref or {}).get("entity")
    name = (field_ref or {}).get("name")
    if not registry or not entity or not name:
        return None
    rec = registry.get(f"{entity}.{name}")
    if rec is None:
        return None
    if rec.get("kind") == "alias":
        rec = registry.get(rec.get("canonical"))
    return rec


def get_state_phase(entity: str, dimension: str, state: str,
                    dep_state_phase_map: dict | None = None,
                    phase_table: dict | None = None) -> int | None:
    """统一相位查询：自动路由两表。

    主实体的态相位在 phase_table.state_to_phase（按维度键控），依赖实体在
    dep_state_phase_map（按实体键控）。E-PLAN 是主实体（计划状态），只查
    dep_state_phase_map 会全部落空——这里封装成单一接口。

    Step 5 做 (state, path) 消歧时，路径消歧后的相位查询只需改这一个函数，
    不用散落在每个消费者里。
    """
    dmap = dep_state_phase_map or {}
    ent_dims = dmap.get(entity, {})
    if ent_dims:
        ph = ent_dims.get(dimension, {}).get(state)
        if ph is not None:
            return int(ph)
    pt = phase_table or {}
    if entity == pt.get("primary_entity"):
        ph = (pt.get("state_to_phase") or {}).get(dimension, {}).get(state)
        if ph is not None:
            return int(ph)
    return None


def field_phase_lower_bound(field_ref: dict, dep_state_phase_map: dict | None,
                            phase_table: dict | None = None,
                            value: str | None = None,
                            registry: dict | None = None) -> int | None:
    """字段 phase 下界 = min(各 populated_anchor 的 phase)，对照**当前**
    （Step 1 shift 之后）的相位表解析。

    语义规则（schema 第 4 节映射表）：谓词下界从字段生命周期推导，不存进字段。
    任一锚点不可解析 → 返回 None（消费方回退保守 P0，见 PREDICATE_RULES）。

    registry 为本次运行的字段注册表（P2 派生、经 coverage_model 序列化到 S1）；
    未传 → resolve_field 返回 None（保守「不可解析」）。

    value 参数为 value-level override 预留：超时类型这种"同字段多值、各值写入
    时点不同"的情况，未来可接一张 {(field_key, value): phase} 覆盖表，避免
    field-level min 丢失精度。当前未实现，默认走 field-level；接口先留好，
    解析器现在不必传 value。
    """
    rec = resolve_field(field_ref, registry)
    if rec is None:
        return None
    anchors = rec.get("populated_anchors") or []
    if not anchors:
        return None
    phases: list[int] = []
    for a in anchors:
        ph = get_state_phase(a["entity"], a["dimension"], a["state"],
                             dep_state_phase_map, phase_table)
        if ph is None:
            return None
        phases.append(ph)
    return min(phases)


def predicate_phase_lower_bound(pred: dict | None, dep_state_phase_map: dict | None,
                                phase_table: dict | None = None,
                                registry: dict | None = None) -> int | None:
    """谓词 phase 下界：谓词类型 → 字段/状态锚点的映射规则（schema 第 4 节映射表）。

    与 field_phase_lower_bound 正交解耦：字段表回答"这个字段什么时候有值"，
    本函数回答"这个谓词类型怎么用字段信息算下界"。两者独立可改。

    规则：field_equals/field_range/field_in → 字段下界；aggregate_count → counter
    字段下界；time_limit → 起算状态 phase；selection_range → source_state phase；
    completion → 完成态 phase；occurrence_limit → 被限 transition 的 from/to phase；
    always_true → 0；negation → operand 下界；conjunction → max(parts)；
    disjunction → min(parts)；disjunction_ref → PREDICATE_RULES 保守 P0，resolved=False。
    下界缺失的 part 按 0 处理（保守不抬升）；整体 None = 完全不可解析。

    registry 为本次运行的字段注册表；透传给 field_phase_lower_bound。
    """
    if pred is None:
        return None
    t = pred.get("type")

    def _safe(p):
        lb = predicate_phase_lower_bound(p, dep_state_phase_map, phase_table,
                                         registry=registry)
        return lb if lb is not None else 0

    if t in ("field_equals", "field_range", "field_in"):
        return field_phase_lower_bound(pred.get("field"), dep_state_phase_map, phase_table,
                                       value=pred.get("value"), registry=registry)
    if t == "aggregate_count":
        return field_phase_lower_bound(pred.get("counter"), dep_state_phase_map, phase_table,
                                       value=pred.get("value"), registry=registry)
    if t == "time_limit":
        st = pred.get("start_state") or {}
        return get_state_phase(st.get("entity"), st.get("dimension"), st.get("state"),
                               dep_state_phase_map, phase_table)
    if t == "selection_range":
        ss = pred.get("source_state") or {}
        return get_state_phase(ss.get("entity"), ss.get("dimension"), ss.get("state"),
                               dep_state_phase_map, phase_table)
    if t == "completion":
        tg = pred.get("target") or {}
        return get_state_phase(tg.get("entity"), tg.get("dimension"), tg.get("state"),
                               dep_state_phase_map, phase_table)
    if t == "occurrence_limit":
        on = pred.get("on") or {}
        return get_state_phase(on.get("entity"), on.get("dimension"),
                               on.get("to") or on.get("from"),
                               dep_state_phase_map, phase_table)
    if t == "always_true":
        return 0
    if t == "negation":
        return _safe(pred.get("operand"))
    if t == "conjunction":
        parts = pred.get("parts") or []
        lbs = [_safe(p) for p in parts]
        return max(lbs) if lbs else None
    if t == "disjunction":
        parts = pred.get("parts") or []
        lbs = [_safe(p) for p in parts]
        return min(lbs) if lbs else None
    if t == "disjunction_ref":
        # 未展开引用的保守下界：不抬升（P0），resolved=False
        return PREDICATE_RULES["disjunction_ref"]["default_phase"]
    return None  # 未识别类型（含 unparsed）


def iter_predicate_state_refs(pred):
    """遍历 constraint_predicate 树，产出结构化状态引用 (entity, dimension, state)。

    与 predicate_phase_lower_bound 同源（同一份谓词语义，单一真相源）：
    - field_equals/field_range/field_in + `ref_state_dimension` → 字段值按状态维度
      解析回状态（暂停前计划状态=评审中 → (E-PLAN, 计划状态, 评审中)）；
    - time_limit.start_state / selection_range.source_state / completion.target →
      直接命名状态；occurrence_limit.on 用 from/to（被限转换）；
    - negation/conjunction/disjunction/when → 递归子树。
    产出顺序确定（dict 键序 + 列表序）。消费方（S0 Strategy 0 入口锚定）按
    max 语义把每个引用状态当作入口门禁；主实体主维度过滤在消费方做。
    """
    if not isinstance(pred, dict):
        return
    t = pred.get("type")
    if t in ("field_equals", "field_range", "field_in"):
        rsd = pred.get("ref_state_dimension")
        if isinstance(rsd, str) and "." in rsd:
            rent, rdim = rsd.split(".", 1)
            vals = [pred.get("value")] if t != "field_in" else (pred.get("values") or [])
            for v in vals:
                if isinstance(v, str):
                    yield (rent, rdim, v)
    for k in ("start_state", "source_state", "target"):
        st = pred.get(k)
        if (isinstance(st, dict) and isinstance(st.get("entity"), str)
                and isinstance(st.get("state"), str)):
            yield (st["entity"], st.get("dimension"), st["state"])
    on = pred.get("on")
    if (isinstance(on, dict) and isinstance(on.get("entity"), str)
            and isinstance(on.get("to") or on.get("from"), str)):
        yield (on["entity"], on.get("dimension"), on.get("to") or on.get("from"))
    for k in ("parts", "operand", "when"):
        sub = pred.get(k)
        if isinstance(sub, dict):
            yield from iter_predicate_state_refs(sub)
        elif isinstance(sub, list):
            for s in sub:
                yield from iter_predicate_state_refs(s)


# ── 谓词级规则（解析器侧约定，Schema 审查补充） ────────────────────────────
PREDICATE_RULES = {
    # disjunction_ref：引用未展开的规则列表（满足降级规则任一条）。
    # v1 确定性行为：phase 下界 = P0 保守值（不抬升），resolved=False，
    # 下游（Guard 6 / Step 4）不得把这条谓词当硬约束。
    "disjunction_ref": {
        "default_phase": 0,
        "resolved": False,
        "resolved_marker": "resolved",
    },
    # completion：下界 = 完成态 phase，按 dep_state_phase_map 当前值取
    #（E-SCORE.已提交 Step 1 后 = 4，非 P2 局部值 2）。
    "completion_phase_rule": "target_state_phase",
    # occurrence_limit：on 引用用语义特征，不硬编码 transition ID。
    "occurrence_limit_on_ref": {"entity": None, "dimension": None, "from": None, "to": None},
}
