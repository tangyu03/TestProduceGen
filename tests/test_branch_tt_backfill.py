#!/usr/bin/env python
"""分支 target_transition 语义回填匹配器单元测试。

锁定 `_backfill_semantic_branch_tt`（model.py）的 11 族信号权重（标定案例锁）、
实体门（跨实体污染防护）、跨实体兜底回填、唯一/多/无候选判据、正式号透传与
C31 偏差报告。直接调用 `_backfill_semantic_branch_tt()`（不 assemble）——
避开校验器中断与编号移交，断言用局部标签（t01/t16 等）。

无 pytest 依赖：`python tests/test_branch_tt_backfill.py`；函数名 test_* 兼容
pytest（安装后 `python -m pytest tests/` 亦可）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from srs_pipeline.builders import precond
from srs_pipeline.model import DomainModel
from srs_pipeline.validate import Validator

# ---------------------------------------------------------------- 夹具

def model(transitions, dim):
    """transitions: (tid, entity, dimension, frm, to, action, preconds, note_bd)
    dim: (dimension, entity, values, branches)
    返回已执行回填的 DomainModel（meta.branch_tt_backfilled/deviations 已填充）。"""
    m = DomainModel({"source": "test", "version": "t"})
    for e in sorted({t[1] for t in transitions}):
        m.add_entity(e, e, "测试实体", state_dimensions=[{"dimension_name": "D",
                          "states": ["a", "b"], "initial": "a", "terminal": []}])
    m.add_role("r01", "执行人", readonly=False)
    for tid, ent, dim_, frm, to, action, preconds, nb in transitions:
        m.add_trans(tid=tid, entity=ent, dimension=dim_, frm=frm, to=to,
                    action=action, role="r01", preconditions=preconds,
                    expected_results=[], traits=[], direction="forward",
                    priority="P1", source_ref="s",
                    note={"branch_dimension": nb} if nb else None)
    m.add_branch_dimension(dimension=dim[0], entity=dim[1], values=dim[2],
                           impact_scope="影响", evidence="ev", branches=dim[3])
    m._backfill_semantic_branch_tt()
    return m


def backfilled(m):
    return {b["value"]: b["target_transition"]
            for b in m.meta.get("branch_tt_backfilled", [])}


def deviation_values(m):
    return [d["value"] for d in m.meta.get("branch_tt_deviations", [])]


C = lambda text: precond(text, "constraint")   # 约束前置快捷构造

# ---------------------------------------------------------------- 信号权重

def test_action_equality_40():
    m = model(
        [("t1", "E1", "D", "a", "b", "报名审核通过", [], None),
         ("t2", "E1", "D", "a", "b", "报名审核通过，另行处理", [], None)],
        ("审核", "E1", ["通过"], [{"value": "通过", "target_transition": "报名审核通过"}]))
    assert backfilled(m) == {"通过": "t1"}, "动作等值 40 应压过动作子串 20"


def test_action_substring_20():
    m = model(
        [("t1", "E1", "D", "a", "b", "审核通过", [], None),
         ("t2", "E1", "D", "a", "b", "无关动作", [], None)],
        ("审核", "E1", ["通过"], [{"value": "通过", "target_transition": "实验室审核通过"}]))
    assert backfilled(m) == {"通过": "t1"}, "动作包含（a in s）20"


def test_path_over_action_substring_30():
    # t02 vs t01 标定：路径 30（含子串 20 叠加）应胜创建转换的纯动作子串 20
    m = model(
        [("t01", "E1", "D", None, "报名中", "设计方案编制", [], None),
         ("t02", "E1", "D", "待开始", "报名中", "设计方案编制", [], None)],
        ("设计方案", "E1", ["报名中"],
         [{"value": "报名中", "target_transition": "设计方案编制（待开始变为报名中路径）"}]))
    assert backfilled(m) == {"报名中": "t02"}, "路径信号应胜创建转换子串"


def test_to_equality_50():
    m = model(
        [("t1", "E1", "D", "a", "待开始", "立项", [], None),
         ("t2", "E1", "D", "a", "b", "待开始", [], None)],
        ("项目状态", "E1", ["待开始"], [{"value": "待开始", "target_transition": "待开始"}]))
    assert backfilled(m) == {"待开始": "t1"}, "to 等值 50 应压过动作等值 40"


def test_constraint_exact_60():
    m = model(
        [("t1", "E1", "D", "a", "b", "退回", [C("报名审核结果=退回修改")], None),
         ("t2", "E1", "D", "a", "b", "退回修改", [], None)],
        ("报名审核结果", "E1", ["退回修改"],
         [{"value": "退回修改", "target_transition": "退回修改"}]))
    assert backfilled(m) == {"退回修改": "t1"}, "约束前置精确 {D}={S} 60 应压过动作等值 40"


def test_constraint_value_56():
    # t30 标定：「…转换（需还样分支）」→ 命中 还样要求=需还样 前置 56
    m = model(
        [("t1", "E1", "D", "a", "b", "提交", [C("还样要求=需还样")], None),
         ("t2", "E1", "D", "a", "b", "提交", [], None)],
        ("还样要求", "E1", ["需还样", "无需还样"],
         [{"value": "需还样", "target_transition": "参加者测试与结果提交转换（需还样分支）"}]))
    assert backfilled(m) == {"需还样": "t1"}, "{D}={分支值} 前置 56"


def test_constraint_value_longest_match():
    # 最长值匹配：desc 含「无需还样」不得被「需还样」子串抢先（需还样⊂无需还样）
    m = model(
        [("t1", "E1", "D", "a", "b", "提交", [C("还样要求=无需还样")], None),
         ("t2", "E1", "D", "a", "b", "提交", [C("还样要求=需还样")], None)],
        ("还样要求", "E1", ["需还样", "无需还样"],
         [{"value": "无需还样", "target_transition": "参加者测试与结果提交转换（无需还样分支）"}]))
    assert backfilled(m) == {"无需还样": "t1"}, "v_star 取最长匹配防子串碰撞"


def test_constraint_substring_55():
    m = model(
        [("t1", "E1", "D", "a", "b", "审批", [C("结果为退回时批量审批退回")], None),
         ("t2", "E1", "D", "a", "b", "批量审批退回", [], None)],
        ("结果", "E1", ["退回"], [{"value": "退回", "target_transition": "批量审批退回"}]))
    assert backfilled(m) == {"退回": "t1"}, "约束前置子串 55 应压过动作子串 20"


def test_init_anchor_45():
    # t01 标定：创建转换（frm=None）路径信号失效，须「初始变为X」落点锚
    m = model(
        [("t01", "E1", "D", None, "待开始", "设计方案编制", [], None),
         ("t02", "E1", "D", "设计", "设计完成", "设计方案编制", [], None)],
        ("设计方案", "E1", ["待开始"],
         [{"value": "待开始", "target_transition": "设计方案编制创建转换（初始变为待开始）"}]))
    assert backfilled(m) == {"待开始": "t01"}, "创建转换目标锚 45"


def test_self_loop_40():
    m = model(
        [("t1", "E1", "D", "在检", "在检", "复检", [], None),
         ("t2", "E1", "D", "在检", "完成", "复检", [], None)],
        ("样品", "E1", ["在检"], [{"value": "在检", "target_transition": "样品自环（在检）"}]))
    assert backfilled(m) == {"在检": "t1"}, "描述标自环 → frm==to 候选 40"


def test_same_dim_annotation_6():
    # t22 vs t24 标定：同路径时，标注本维度的候选 +6 胜出
    m = model(
        [("t22", "E1", "D", "已核查", "待核查", "还样", [], "还样情况"),
         ("t24", "E1", "D", "已核查", "待核查", "还样", [], "项目类型")],
        ("还样情况", "E1", ["待核查"],
         [{"value": "待核查", "target_transition": "已核查变为待核查"}]))
    assert backfilled(m) == {"待核查": "t22"}, "同维度标注 +6 让位跨维度同名候选"


def test_branch_value_to_2():
    # t19 标定：分支值落该转换 to → 消歧 +2
    m = model(
        [("t1", "E1", "D", "a", "已还样", "参加者测试与结果提交", [], None),
         ("t2", "E1", "D", "a", "其他", "参加者测试与结果提交", [], None)],
        ("还样要求", "E1", ["已还样"],
         [{"value": "已还样", "target_transition": "参加者测试与结果提交（已还样分支）"}]))
    assert backfilled(m) == {"已还样": "t1"}, "to∈分支值 消歧 +2"


def test_additive_path_substring():
    # 叠加而非取最高：路径 30 + 动作子串 20 = 50，胜纯子串 20
    m = model(
        [("t1", "E1", "D", "待审批", "审批退回", "批量审核退回", [], None),
         ("t2", "E1", "D", "a", "b", "批量审核退回", [], None)],
        ("结果", "E1", ["退回"],
         [{"value": "退回", "target_transition": "批量审核退回转换（待审批变为审批退回）"}]))
    assert backfilled(m) == {"退回": "t1"}, "多族信号叠加（30+20>20）"

# ---------------------------------------------------------------- 实体门

def test_entity_gate_bars_pollution():
    # 评价反例：E-LAB 误标「审核结果」且动作撞车 s==a(40)+标注(6)=46；
    # 本实体 E-TASK 有正分子串 20 → 外实体候选被门禁，回填本实体
    m = model(
        [("t_own", "E-TASK", "D", "待审核", "审核通过", "任务审核通过", [], "审核结果"),
         ("t_ext", "E-LAB", "D", "待审核", "已审核", "审核通过", [], "审核结果")],
        ("审核结果", "E-TASK", ["通过"],
         [{"value": "通过", "target_transition": "审核通过"}]))
    assert backfilled(m) == {"通过": "t_own"}, "实体门应拦截外实体污染候选"


def test_cross_entity_fallback_when_own_zero():
    # v9 业务类型(E-XM)→t16(E-BMJL) 复制：本实体零正分 → 外实体候选兜底允许
    m = model(
        [("t16", "E-BMJL", "D", "a", "报告完成", "编制结果报告", [], "业务类型"),
         ("t_x", "E-XM", "D", "a", "b", "立项", [], None),
         ("t_y", "E-XM", "D", "a", "b", "结项", [], None)],
        ("业务类型", "E-XM", ["能力验证"],
         [{"value": "能力验证", "target_transition": "编制结果报告转换"}]))
    assert backfilled(m) == {"能力验证": "t16"}, "本实体零正分时跨实体回填兜底"

# ---------------------------------------------------------------- 判据

def test_no_candidate_deviation():
    m = model(
        [("t1", "E1", "D", "a", "b", "无关动作", [], None)],
        ("审核", "E1", ["通过"],
         [{"value": "通过", "target_transition": "不存在的转换描述"}]))
    assert backfilled(m) == {}, "无候选不得回填"
    assert deviation_values(m) == ["通过"], "无候选记偏差 no_candidate"
    assert m.meta["branch_tt_deviations"][0]["reason"] == "no_candidate"


def test_ambiguous_deviation():
    m = model(
        [("t1", "E1", "D", "a", "b", "审核通过", [], None),
         ("t2", "E1", "D", "a", "b", "审核通过", [], None)],
        ("审核", "E1", ["通过"], [{"value": "通过", "target_transition": "审核通过"}]))
    assert backfilled(m) == {}, "多候选不得回填"
    assert deviation_values(m) == ["通过"]
    assert m.meta["branch_tt_deviations"][0]["reason"].startswith("ambiguous:")


def test_formal_id_passthrough():
    m = model(
        [("t1", "E1", "D", "a", "b", "审核通过", [], None)],
        ("审核", "E1", ["通过"], [{"value": "通过", "target_transition": "T-001"}]))
    br = m.branch_dimensions[0]["branches"][0]
    assert br["target_transition"] == "T-001", "正式号原样透传，不再回填"
    assert backfilled(m) == {}, "正式号不进回填记录"
    assert deviation_values(m) == []


def test_empty_noop():
    m = model(
        [("t1", "E1", "D", "a", "b", "审核通过", [], None)],
        ("审核", "E1", ["通过"], [{"value": "通过", "target_transition": ""}]))
    br = m.branch_dimensions[0]["branches"][0]
    assert br["target_transition"] == "", "空 target_transition 为纯配置，不动"
    assert backfilled(m) == {}
    assert deviation_values(m) == []

# ---------------------------------------------------------------- C31 报告

def test_c31_reports_deviations():
    m = model(
        [("t1", "E1", "D", "a", "b", "无关动作", [], None)],
        ("审核", "E1", ["通过"],
         [{"value": "通过", "target_transition": "不存在的转换描述"}]))
    v = Validator(m, {})
    v.c31_inv_branch_tt_deviation()
    warns = [i for i in v.report.issues if i.severity == "warning"]
    assert len(warns) == 1, f"偏差应报 1 条 C31 warning，实际 {len(warns)}"
    assert warns[0].check == "C31"
    assert "no_candidate" in warns[0].message


def test_c31_silent_without_deviations():
    m = model(
        [("t1", "E1", "D", "a", "b", "审核通过", [], None)],
        ("审核", "E1", ["通过"], [{"value": "通过", "target_transition": "审核通过"}]))
    v = Validator(m, {})
    v.c31_inv_branch_tt_deviation()
    assert v.report.issues == [], "无偏差时 C31 零报告"


# ---------------------------------------------------------------- 运行器

_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    failed = 0
    for fn in _TESTS:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(_TESTS) - failed}/{len(_TESTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
