"""依赖来源置信度——全仓库唯一事实源 (C-12)。

背景: break_cycles 与 S3 曾各自内联 DEP_CONFIDENCE, 双表漂移是已知维护陷阱
(DECISIONS, 2026-08-14 实测 co_enabler 缺表 conf 归 0 被优先剪错边)。本次
合并为单一表:
  - guard2_constraint_gate 旧版只在 graph_algo 注册 (S3 未注册)
  - domain_precond        旧版只在 s3_dependency 注册 (graph_algo 未注册
    → break_cycles 把它当未知 origin, conf 0, 优先剪除 Guard 7 对象存在性
    前置——真实错误)

新 origin tag 只需在此注册一处, 不再双表同步。S3 负责记录 origin,
graph_algo.break_cycles 负责消费, 双方都从这里取值。
"""
import warnings

# origin → 置信度。数值语义见 graph_algo.break_cycles 的 category 说明:
# 5 = 因果链/状态机结构 (权威); 4 = CO 结构绑定; 3 = 同维排序/创建-使用/
# 对象存在性启发式; 2 = 前置文本匹配 (脆弱); 1 = 弱依赖 (永远最低)。
DEP_CONFIDENCE: dict[str, int] = {
    "transition_upstream": 5,
    "guard1_state_pred": 5,
    "co_enabler": 4,
    "co_enabler_both_lateral": 4,
    "co_enabler_phase_inversion": 4,
    "ve_co_ids": 4,
    "chain_ordering": 3,
    "guard5_create_use": 3,
    "domain_precond": 3,
    "guard2_constraint_gate": 3,  # S3 注释声明为 no-op, 保留以兼容历史 origin
    "guard6_precond": 2,
    "weak_side_effect": 1,
}

_seen_unknown: set[str] = set()


def confidence_of(origin: str) -> int:
    """返回 dep origin 的置信度; 未知 → 0 (按最弱处理) 并告警一次。

    未知 origin 意味着 S3 记了 graph_algo 不知道的标签——正是双表漂移要
    防的错位。每类未知标签只告警一次, 避免逐边刷屏。
    """
    if origin not in DEP_CONFIDENCE:
        if origin not in _seen_unknown:
            _seen_unknown.add(origin)
            warnings.warn(
                f"unknown dep origin {origin!r} — conf=0 (按最弱剪边); "
                f"请注册到 context/dep_confidence.py.DEP_CONFIDENCE",
                RuntimeWarning,
                stacklevel=2,
            )
        return 0
    return DEP_CONFIDENCE[origin]
