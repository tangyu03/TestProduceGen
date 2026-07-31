"""V07 角色一致性（重构版）：actor 非空、在角色矩阵中、与 spec 迁移定义一致、
且迁移的 alternate_actors（备选执行者，从 note 解析）亦被接受。

三层检查：
1. 存在性：obligation_type=1（迁移型）用例的 actor 必须非空（blocker 级）。
2. 合法性：actor ∈ role_permissions.matrix 键 ∪ SYSTEM_ACTORS。
3. 一致性：source_ids 引用的 spec 迁移，其 actor 字段或用例 actor 不一致时 fail；
   若迁移的 note 含"X亦可"类备选角色描述，X 加入合法集合（T-PLAN-012 归档
   的"评审助理亦可归档"场景）。
4. 权限覆盖：actor 对 when.action 在 matrix 中有权限（负向用例生成依据）。
   匹配策略：子串匹配（matrix action 是 proc action 的子串，或反过来）。
   例如 proc action="添加研制机构"，matrix 有"机构管理"→不匹配；
   proc action="新增项目"，matrix 有"项目新增"→不匹配。子串匹配捕获
   "项目新增" vs "新增项目"这类语序变体。

整体 warning 级：actor 语义缺陷在骨架阶段不阻断，供 S0/S1 修复参考。
"""
from .base import CheckResult, get_procedures, normalize_text

CHECK_ID = "V07"
SYSTEM_ACTORS = {"系统"}
ALT_ACTOR_MARKERS = ("亦可", "也可以", "也可")


def _has_permission(action: str, allowed: set) -> bool:
    """检查 actor 是否有 action 权限。子串双向匹配。"""
    if not action:
        return True
    for a in allowed:
        if not a:
            continue
        # 子串双向匹配：proc action 含 catalog action，或反过来
        if a in action or action in a:
            return True
    return False


def _tid2actors(spec: dict) -> dict:
    """从 spec.state_machines 提取 tid → {主 actor, 备选 actors}。"""
    result = {}
    for m in (spec.get("state_machines") or {}).values():
        for t in m.get("transitions", []) or []:
            if not t.get("id"):
                continue
            actors = set()
            if t.get("actor"):
                actors.add(t["actor"])
            note = t.get("note") or ""
            for marker in ALT_ACTOR_MARKERS:
                if marker in note:
                    # "评审助理亦可归档" → 提取 "评审助理"
                    idx = note.index(marker)
                    prefix = note[:idx].rstrip("；;，, ")
                    # 取最后一个完整词作为备选角色（简化处理）
                    for role_len in (5, 4, 3, 2):
                        if len(prefix) >= role_len:
                            candidate = prefix[-role_len:]
                            if any(kw in candidate for kw in ("管理员", "助理", "专家")):
                                actors.add(candidate)
                                break
            result[t["id"]] = actors
    return result


def check(output: dict, spec: dict) -> CheckResult:
    res = CheckResult(check_id=CHECK_ID, severity="warning", suspected_stage="S0",
                      suspected_files=["prompts/s0_prompt.py", "nodes/s0_topology.py"])
    rp = (spec or {}).get("role_permissions") or {}
    matrix = rp.get("matrix") or {}
    machines = (spec or {}).get("state_machines") or {}
    if not matrix or not machines:
        res.skip("case_spec.role_permissions or state_machines missing")
        return res

    tid2actors = _tid2actors(spec)
    all_roles = set(matrix.keys()) | SYSTEM_ACTORS
    empty_actor = unknown_actor = actor_mismatch = 0

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

        # 2. actor 在合法集合中
        if actor and actor not in all_roles:
            unknown_actor += 1
            res.fail({"temp_id": p.get("temp_id"), "actor": actor,
                      "reason": f"actor not in role matrix or system set "
                                f"(known: {sorted(all_roles)})"})

        # 3. 与 spec 迁移的 actor 一致性（含备选）
        for sid in p.get("source_ids", []) or []:
            allowed_actors = tid2actors.get(sid, set())
            if allowed_actors and actor and actor not in allowed_actors:
                actor_mismatch += 1
                res.fail({"temp_id": p.get("temp_id"), "transition": sid,
                          "actor": actor,
                          "allowed_actors": sorted(allowed_actors),
                          "reason": "actor conflicts with spec transition definition"})

        # 4. 权限覆盖（负向用例依据）：actor 对 action 在 matrix 中应有权限
        if actor in matrix:
            action = (when.get("action") or "").strip()
            if action and not _has_permission(action, matrix[actor]):
                res.fail({"temp_id": p.get("temp_id"), "actor": actor,
                          "action": action,
                          "reason": f"actor '{actor}' lacks permission for action "
                                    f"(matrix has: {sorted(matrix[actor])[:5]}...)"})

    res.note = (f"empty_actor={empty_actor}, unknown_actor={unknown_actor}, "
                f"actor_mismatch={actor_mismatch}")
    return res
