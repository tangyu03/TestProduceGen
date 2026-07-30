"""数值预言机：SRS 4.9.2 / 4.9.6 / 4.9.7 / 4.5(5) / 4.8 超时流转的可执行翻译。

Gate-E 的 V15 数值重算与 R1 语义复核依赖本模块。
所有计算使用 Decimal + ROUND_HALF_UP，与 SRS"四舍五入保留两位小数"一致。
"""
import re
from decimal import ROUND_HALF_UP, Decimal

# ── 打分权重（SRS 表 4.9-4）──
WEIGHT_TABLE = {5: ("0.40", "0.60"), 7: ("0.25", "0.75"), 9: ("0.18", "0.82")}

# ── 级别判定（SRS 表 4.9-5，"只降一级"）──
GRADE_TABLE = [   # (级别, 得分下限, 创新性下限, 应用前景下限)
    ("优秀", "90.00", "13.00", "17.00"),
    ("良好", "70.00", "11.00", "14.00"),
    ("合格", "60.00", "9.00", "12.00"),
    ("不合格", "30.00", None, None),
    ("差", "0.00", None, None),
]
GRADE_PASS = {"优秀", "良好", "合格"}          # "合格及以上"

# ── 打分项上限（SRS 表 4.9-1）──
SCORE_ITEM_LIMITS = {
    "开题": {"创新性": "15.00", "研究目标及技术指标": "10.00", "研究基础和保障条件": "15.00",
             "应用前景": "20.00", "成果及考核方式": "20.00", "研究方案及技术途径": "20.00"},
    "验收": {"创新性": "15.00", "技术指标达标情况": "10.00", "成果及其完成情况": "20.00",
             "应用前景": "20.00", "研制过程": "15.00", "关键技术": "20.00"},
}
TOTAL_LIMIT = "100.00"

# ── 超时自动流转（SRS 4.8.1(5), 4.8.8(2), 4.8.9(2)）──
TIMEOUT_TRANSITIONS = {
    "下发超时": {"已建立": "待启动"},
    "启动超时": {"待启动": "待评审"},
    "评审超时": {"待评审": "已完成", "评审中": "已完成", "暂停": "已完成"},
    "归档超时": {"已完成": "超时结束"},
}

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def _d(x) -> Decimal:
    return Decimal(str(x))


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _round1(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


# ═══ 4.9.6 项目评价 ═══

def compute_item_average(item_scores: list) -> float:
    """单个打分项分数 = 所有专家相应项打分的平均分（SRS 4.9.6 首句），保留两位。"""
    if not item_scores:
        raise ValueError("empty item_scores")
    vals = [_d(v) for v in item_scores]
    return float(_round2(sum(vals) / _d(len(vals))))


def compute_weighted_score(group_size: int, leader_total, ordinary_totals: list) -> float:
    """项目得分：普通专家去一个最高分一个最低分 → 剩余均值 → 组长加权。

    R-001 防御：普通专家 ≤2 人时去极值后无剩余，SRS 未定义该场景，
    抛明确异常而非静默返回错误值（待需求方澄清后修改此分支）。
    """
    if group_size not in WEIGHT_TABLE:
        raise ValueError(f"invalid group size: {group_size}")
    if len(ordinary_totals) != group_size - 1:
        raise ValueError(f"ordinary expert count mismatch: "
                         f"expect {group_size - 1}, got {len(ordinary_totals)}")
    trimmed = sorted((_d(v) for v in ordinary_totals))[1:-1]
    if not trimmed:
        raise ValueError("R-001 unresolved: ordinary experts <= 2, "
                         "trimmed set empty; SRS 4.9.6 undefined here")
    lw, ow = (_d(v) for v in WEIGHT_TABLE[group_size])
    avg = sum(trimmed) / _d(len(trimmed))
    return float(_round2(_d(leader_total) * lw + avg * ow))


def compute_project_grade(score, innovation, prospect) -> str:
    """级别判定：先按得分定最高可能级别，再验剩余约束；不满足只降一级。"""
    s, inno, pro = _d(score), _d(innovation), _d(prospect)
    order = [g[0] for g in GRADE_TABLE]
    if s < _d("30.00"):
        return "差"
    for i, (name, s_min, inno_min, pro_min) in enumerate(GRADE_TABLE[:-1]):
        if s >= _d(s_min):
            if inno_min is None or (inno >= _d(inno_min) and pro >= _d(pro_min)):
                return name
            return order[i + 1]          # 只降一级，不再复验下一级约束
    return "差"


def validate_score_items(items: dict, stage: str) -> list:
    """校验一组打分项：未知项 / 越界 / 总分超限。返回违规描述列表（空=合法）。"""
    limits = SCORE_ITEM_LIMITS.get(stage)
    if limits is None:
        raise ValueError(f"unknown stage: {stage}")
    violations = []
    total = _d(0)
    for item, val in items.items():
        if item not in limits:
            violations.append(f"{stage}阶段无此打分项: {item}")
            continue
        v = _d(val)
        if v < _d(0) or v > _d(limits[item]):
            violations.append(f"{item}={v} 超出 [0, {limits[item]}]")
        total += v
    if total > _d(TOTAL_LIMIT):
        violations.append(f"总分 {total} 超过 {TOTAL_LIMIT}")
    return violations


# ═══ 4.5(5) 项目归档分支 ═══

def apply_project_archive(stage: str, grade: str, current_state: str = "待归档") -> tuple:
    """计划归档时项目的状态/阶段迁移（SRS 4.5(5)a-e）。

    返回 (新状态, 新阶段)。
    a) 开题+合格及以上 → (已选入, 验收)
    b) 开题+不合格/差  → (待选入, 开题)
    c) 验收+合格及以上 → (已归档, 验收)
    d) 验收+不合格/差  → (待选入, 验收)
    e) 评审中项目随计划完成 → (已选入, 阶段不变)
    """
    if current_state == "评审中":
        return ("已选入", stage)
    if current_state != "待归档":
        raise ValueError(f"archive not applicable from state: {current_state}")
    if stage not in ("开题", "验收"):
        raise ValueError(f"unknown stage: {stage}")
    passed = grade in GRADE_PASS
    if stage == "开题":
        return ("已选入", "验收") if passed else ("待选入", "开题")
    return ("已归档", "验收") if passed else ("待选入", "验收")


# ═══ 4.9.7 机构评价 ═══

def compute_org_state_transition(current_state: str, counts: dict) -> dict:
    """机构状态自动迁移判定（计划归档时按当前状态期间累计触发）。

    counts: {"优": n, "不合格": n, "差": n}（当前状态期间的项目阶段评价累计）
    返回 {"to_state": ..., "matched_rule": "4.9.7(1)a" 等 或 None}

    优先级（SRS 4.9.7(3)e）：试用机构升降条件同时满足时，降为不合格——
    因此试用状态先判降级再判升级。
    """
    good = _d(counts.get("优", 0))
    fail = _d(counts.get("不合格", 0))
    bad = _d(counts.get("差", 0))

    if current_state == "合格":
        if bad >= 3:
            return {"to_state": "不合格", "matched_rule": "4.9.7(1)a 差>=3"}
        if bad >= 1 and fail >= 3:
            return {"to_state": "不合格", "matched_rule": "4.9.7(1)b 差>=1且不合格>=3"}
        if fail >= 5:
            return {"to_state": "不合格", "matched_rule": "4.9.7(1)c 不合格>=5"}
        return {"to_state": "合格", "matched_rule": None}

    if current_state == "试用":
        # 先降级（优先级规则 e）
        if bad >= 2:
            return {"to_state": "不合格", "matched_rule": "4.9.7(3)b 差>=2"}
        if bad >= 1 and fail >= 2:
            return {"to_state": "不合格", "matched_rule": "4.9.7(3)c 差>=1且不合格>=2"}
        if fail >= 4:
            return {"to_state": "不合格", "matched_rule": "4.9.7(3)d 不合格>=4"}
        # 再升级
        if good >= 10:
            return {"to_state": "合格", "matched_rule": "4.9.7(3)a 优>=10"}
        return {"to_state": "试用", "matched_rule": None}

    if current_state == "不合格":
        # 不合格状态无自动迁移（仅系统管理员提为试用，属人工动作）
        return {"to_state": "不合格", "matched_rule": None}

    raise ValueError(f"unknown org state: {current_state}")


def can_promote_to_trial(disqualification_times: int) -> bool:
    """不合格机构可否提为试用（SRS 4.9.7(2)d：累计3次评级不合格则禁止）。"""
    return _d(disqualification_times) < 3


# ═══ 4.8 超时流转 ═══

def apply_timeout(current_state: str, timeout_kind: str) -> str:
    """超时自动流转的目标状态；该状态无对应超时迁移时返回 None。"""
    table = TIMEOUT_TRANSITIONS.get(timeout_kind)
    if table is None:
        raise ValueError(f"unknown timeout kind: {timeout_kind}")
    return table.get(current_state)


# ═══ 通用字段校验 ═══

def validate_phone(phone) -> bool:
    """手机号规则（SRS 多处）：1 开头 + 第二位 3-9 + 共 11 位数字。"""
    return bool(PHONE_RE.match(str(phone or "")))


def round_threshold(value) -> float:
    """分数限值精度（SRS 4.9.4：保留一位小数）。"""
    return float(_round1(_d(value)))
