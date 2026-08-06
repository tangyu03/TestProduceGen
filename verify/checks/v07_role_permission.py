"""V07 角色一致性(模型推导版)：actor 非空、在模型角色集合中、且对 when.action
有权限——权限矩阵从模型推导,而非 case_spec 手写矩阵。

第一性原理：权限矩阵的单一真相源在 P1 数据层——
  1. transition_obligations 的 (role, action)：每个转换的 role 就是模型对该
     角色可执行该动作的陈述；
  2. _context.permissions：P1 数据层声明的角色→可执行操作。
两者并集构成矩阵。角色 ID 经 _context.roles 映射为角色名(与用例 actor 一致),
消除"项目新增 vs 新增项目"这类手写矩阵的名称漂移。

Type9(field_validation)特判——实体级,而非豁免：
  Type9 的 action "提交含违规值的表单" 是脚手架动作,不是领域操作,action 子串
  匹配对它天然失真(历史上 17/17 全报 no_permission,含 10 个正确 actor 的误报)。
  Type9 真正的不变量是实体级的: actor 必须是该实体表单的授权操作者。校验用
  context/entity_operators.py 的 entity_operator_set()——与生成器共用同一份
  派生(single source of truth),因此校验器验证的正是生成器被要求产生的 actor。

豁免(结构化标记,非文本)：
  - actor = 系统/空 → 系统驱动 transition
  - risk_trait ∈ {audit_rejection, time_sensitive} → S1 派生的驳回/超时变体
    (驳回动作、X(边界) 不在模型中)

缺 --model 时跳过(无法推导矩阵,不退回 case_spec)。
"""
from .base import CheckResult, get_procedures, normalize_text
from context.entity_operators import entity_operator_set

CHECK_ID = "V07"
SYSTEM_ACTORS = {"系统", "system"}
_S1_DERIVED_TRAITS = {"audit_rejection", "time_sensitive"}


def _build_matrix(model: dict) -> tuple[dict, set]:
    """返回 (matrix[role_name] -> set(actions), all_roles)。"""
    roles = (model.get("_context") or {}).get("roles", []) or []
    id2name = {r.get("id"): r.get("name") for r in roles if r.get("id")}
    matrix: dict = {}
    all_roles = set()
    for r in roles:
        nm = r.get("name")
        if nm:
            all_roles.add(nm)
    # 1. TO 派生 (role, action)
    for to in model.get("transition_obligations", []) or []:
        rid = to.get("role")
        act = to.get("action")
        name = id2name.get(rid, rid)
        if name and act:
            matrix.setdefault(name, set()).add(act)
            all_roles.add(name)
    # 2. P1 permissions (role, operations)
    # role 引用键经 id2name 归一: P1.5 用角色名,旧 P1 格式用角色 ID(R-001)。
    # 与 transitions.role 同一引用键(见 prompt Step 0.5),统一映射为角色名。
    for perm in (model.get("_context") or {}).get("permissions", []) or []:
        role = id2name.get(perm.get("role"), perm.get("role"))
        for op in perm.get("operations", []) or []:
            if role and op:
                matrix.setdefault(role, set()).add(op)
                all_roles.add(role)
    return matrix, all_roles


def _has_permission(action: str, allowed: set) -> bool:
    """子串双向匹配。"""
    if not action:
        return True
    for a in allowed:
        if not a:
            continue
        if a in action or action in a:
            return True
    return False


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="warning", suspected_stage="S0",
                      suspected_files=["nodes/s0_topology.py", "nodes/s1_generation.py"])
    model = output.get("_model")
    if not model:
        res.skip("no coverage model passed (--model); skipping model-derived V07")
        return res

    matrix, all_roles = _build_matrix(model)
    if not matrix:
        res.skip("model has no roles/permissions/transitions")
        return res

    empty_actor = unknown_actor = actor_mismatch = no_perm = 0

    for p in get_procedures(output):
        when = p.get("when") or {}
        actor = (when.get("actor") or "").strip()
        otype = p.get("obligation_type")

        # 1. 迁移型用例 actor 必须非空
        if otype == 1 and not actor:
            empty_actor += 1
            res.fail({"temp_id": p.get("temp_id"),
                      "reason": "transition case (obligation_type=1) has empty actor",
                      "severity_hint": "blocker"})
            continue

        # 2. actor 在合法角色集合中
        if actor and actor not in all_roles and actor not in SYSTEM_ACTORS:
            unknown_actor += 1
            res.fail({"temp_id": p.get("temp_id"), "actor": actor,
                      "reason": f"actor not in model roles or system set "
                                f"(known: {sorted(all_roles)})"})

        # 豁免: S1 派生变体(驳回/超时)的动作/角色不在模型
        if p.get("risk_trait") in _S1_DERIVED_TRAITS:
            continue

        # 3. 权限覆盖
        if otype == 9:
            # Type9: action 是脚手架("提交含违规值的表单"),非领域操作 → action
            # 子串匹配失真。不变量为实体级: actor 必须在该实体表单的操作者集合中
            # (与生成器共用 context/entity_operators 同一份派生,无豁免)。
            entity = (p.get("entity") or "").strip()
            operators = entity_operator_set(model).get(entity, set())
            if actor and actor not in SYSTEM_ACTORS and actor not in operators:
                no_perm += 1
                res.fail({"temp_id": p.get("temp_id"), "actor": actor,
                          "entity": entity,
                          "reason": f"Type9 actor '{actor}' is not an operator of "
                                    f"entity '{entity}' "
                                    f"(operators: {sorted(operators)})"})
        elif actor in matrix:
            # 非 Type9: actor 对 when.action 在矩阵中应有权限(负向用例依据)
            action = (when.get("action") or "").strip()
            if action and not _has_permission(action, matrix[actor]):
                no_perm += 1
                res.fail({"temp_id": p.get("temp_id"), "actor": actor,
                          "action": action,
                          "reason": f"actor '{actor}' lacks permission for action "
                                    f"(matrix has: {sorted(matrix[actor])[:5]}...)"})

    res.note = (f"empty_actor={empty_actor}, unknown_actor={unknown_actor}, "
                f"no_permission={no_perm}")
    return res
