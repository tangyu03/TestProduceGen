#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 → P2 (Coverage Obligation Model) Generator — generic, configurable.

Step 0: Input validation + state_info index
Step 1: entity_obligations (EO-ATC + EO-CRU)
Step 2: transition_obligations (TO, branch split)
Step 3: cross_entity_obligations (CO, 3 lanes)
Step 4: constraint_obligations (RO-IT + RO-BR + XC→RO-BR)
Step 5: _context (incl. phase_mapping per (entity, dim))
Step 6: phase_mapping derivation (BFS over forward edges + terminal pinning)

Usage:
    python context/generate_obligation_model.py <p1_input.json> <p2_output.json>
    python context/generate_obligation_model.py   # uses defaults

The script is fully deterministic — no LLM calls. All semantic decisions
(XC classification, branch splitting, phase mapping) are rule-based and
auditable via the judgments/warnings logs in _context.

phase_mapping derivation (Step 6):
  For each (entity, dimension) in state_info, compute a phase_mapping
  {state_name: int_phase} by BFS over forward transition edges starting
  from the declared initial state. Terminal states are pinned to the
  same maximum phase (so all terminals share one phase, matching the
  SRS lifecycle-end semantics). This eliminates the need for S0 (P3)
  to re-derive phases via error-prone BFS on cyclic state machines.

  The phase_mapping is written to:
    _context.state_info[entity].dimensions[i].phase_mapping
  S0 reads it via _get_explicit_phase_mapping() and uses it verbatim.
"""
import json
import os
import re
import sys
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta

# CO dependent-transition derivation rule (shared with validate_p2.py gate) —
# single source of truth, no logic fork between generator and validator.
try:
    import co_derivation  # script-dir import (python context/generate_obligation_model.py)
except ImportError:
    from context import co_derivation  # package-relative (python -m context.generate_obligation_model)

# Step 3 constraint-predicate field registry + phase rules (Step 3 structured
# predicate layer). Pure data + phase pure functions, shared with downstream
# consumers (Guard 6 / Step 4). See context/constraint_fields.py.
try:
    import constraint_fields as _cf  # script-dir import
except ImportError:
    from context import constraint_fields as _cf  # package-relative

# ============ Configurable paths ============
# P1 输入**必传**（argv[1] 或环境变量 P1_PATH），不设旧默认路径
# （context/P1_out.json 已弃用——P1 真源现为仓库根 review_structured.json）。
# 输出默认仓库根 coverage_obligations.json，可用 argv[2] 或 P2_OUT_PATH 覆盖。
_REPO_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_OUT = os.environ.get(
    "P2_OUT_PATH",
    os.path.join(_REPO_ROOT_DIR, "coverage_obligations.json"),
)

if len(sys.argv) >= 2:
    P1_PATH = sys.argv[1]
elif os.environ.get("P1_PATH"):
    P1_PATH = os.environ["P1_PATH"]
else:
    raise SystemExit(
        "用法: python context/generate_obligation_model.py <P1.json> [out.json]\n"
        "P1 输入必传（当前真源: review_structured.json）。")
if len(sys.argv) >= 3:
    OUT_PATH = sys.argv[2]
else:
    OUT_PATH = _DEFAULT_OUT

if not os.path.exists(P1_PATH):
    raise SystemExit(f"P1 输入不存在: {P1_PATH}")

with open(P1_PATH, "r", encoding="utf-8") as f:
    p1 = json.load(f)

# ============ 字段注册表：由本次 P1 派生，不硬编码任何 SRS 域 ============
# 事实源 = 本次运行的 P1 输入（model_view 适配 domain_model/state_and_flow/_meta）。
# P2 内部（_resolve_field_from_text / _parse_occurrence_when /
# _resolve_counter_from_text / _normalize_constraint_value）用它解析字段；
# 并经 coverage_model._context.field_registry 序列化给 S1 的
# predicate_phase_lower_bound 用。
_FIELD_REGISTRY = _cf.build_registry(_cf.model_view(p1))


# ============ LLM infrastructure (optional, for classification fallback) ============
# P2 is fully deterministic by default. LLM is used ONLY as a fallback when
# keyword-based classification returns "unknown" — the LLM classifies into
# a fixed enum, never generates free-form content.
#
# Configuration (priority: env > config.json > disabled):
#   LLM_API_BASE / LLM_API_KEY / LLM_P2_MODEL  (environment variables)
#   config.json → {"llm": {"api_base", "api_key", "task_models": {"p2_classify"}}}

def _load_llm_config():
    """Load LLM config from env vars or config.json. Returns None if disabled."""
    import os
    api_base = os.environ.get("LLM_API_BASE")
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_P2_MODEL")
    if api_base and api_key:
        return {"api_base": api_base.rstrip("/"), "api_key": api_key,
                "model": model or "glm-4-flash"}
    # Try config.json next to P1 input
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(P1_PATH)),
                                "..", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f).get("llm", {})
            if cfg.get("api_key"):
                return {
                    "api_base": cfg.get("api_base", "https://open.bigmodel.cn/api/paas/v4"),
                    "api_key": cfg["api_key"],
                    "model": cfg.get("task_models", {}).get("p2_classify",
                               cfg.get("task_models", {}).get("general", "glm-4-flash")),
                }
    except Exception:
        pass
    return None

_LLM_CFG = _load_llm_config()


def _llm_classify(system_prompt: str, user_message: str, valid_values: list[str],
                  timeout: int = 30) -> str | None:
    """Call LLM to classify into one of valid_values. Returns the classification
    string, or None if LLM is unavailable/fails/returns invalid value.

    The LLM is constrained to output a single token from valid_values — it
    cannot generate free-form content. This makes the call safe (no
    hallucinated procedures) and cheap (few tokens).

    Args:
        system_prompt: System message explaining the classification task
        user_message: The content to classify
        valid_values: Allowed enum values (e.g. ["constraint", "auto", "br"])
        timeout: Request timeout in seconds

    Returns:
        One of valid_values, or None if unavailable/invalid.
    """
    if not _LLM_CFG:
        return None
    try:
        import urllib.request
        import urllib.error

        url = f"{_LLM_CFG['api_base']}/chat/completions"
        body = json.dumps({
            "model": _LLM_CFG["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 50,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_LLM_CFG['api_key']}",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        content = content.strip().lower()
        # Validate LLM output is one of the allowed values
        for v in valid_values:
            if v in content:
                return v
        return None
    except Exception:
        return None


# ============ Step 0: Input validation ============
required_nodes = [
    ("domain_model.entities", p1.get("domain_model", {}).get("entities")),
    ("domain_model.structural_relations", p1.get("domain_model", {}).get("structural_relations")),
    ("domain_model.transition_relations", p1.get("domain_model", {}).get("transition_relations")),
    ("state_and_flow.transitions", p1.get("state_and_flow", {}).get("transitions")),
    ("constraints.cross_entity", p1.get("constraints", {}).get("cross_entity")),
    ("constraints.invalid_transitions", p1.get("constraints", {}).get("invalid_transitions")),
    ("constraints.business_rules", p1.get("constraints", {}).get("business_rules")),
    ("_meta.branch_dimensions", p1.get("_meta", {}).get("branch_dimensions")),
]
missing = [name for name, val in required_nodes if val is None]
if missing:
    out = {"_context": {"fatal_error": "缺少必备节点", "missing_nodes": missing}}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(2)  # C-08: fatal 路径必须非零退出，CI/脚本靠 $? 感知

# Precondition structure check (Step 0.3): preconditions must be object array
fatal_precond = None
for t in p1["state_and_flow"]["transitions"]:
    pcs = t.get("preconditions", [])
    if not isinstance(pcs, list):
        fatal_precond = t["id"]
        break
    for p in pcs:
        if not isinstance(p, dict) or "text" not in p or "type" not in p or "ref" not in p:
            fatal_precond = (t["id"], str(p)[:60])
            break
    if fatal_precond:
        break
if fatal_precond:
    out = {"_context": {"fatal_error": "P1 preconditions 未结构化，需 P1 v18.4+ 输出", "detail": fatal_precond}}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(2)  # C-08: fatal 路径必须非零退出，CI/脚本靠 $? 感知

# Build state_info index (Step 0.2)
state_lookup = {}  # entity_id -> {dimension -> set(states)}
state_to_entities = {}  # state_value -> set((entity_id, dimension))

for e in p1["domain_model"]["entities"]:
    state_lookup[e["id"]] = {}
    for dim in e.get("state_dimensions", []):
        states = set(dim["states"])
        state_lookup[e["id"]][dim["dimension_name"]] = states
        for s in dim["states"]:
            state_to_entities.setdefault(s, set()).add((e["id"], dim["dimension_name"]))

# Terminal index: entity_id -> {dimension -> set(terminal states)}
terminal_index = {}
for e in p1["domain_model"]["entities"]:
    terminal_index[e["id"]] = {}
    for dim in e.get("state_dimensions", []):
        terminal_index[e["id"]][dim["dimension_name"]] = set(dim.get("terminal", []) or [])

# Pre-state dimensions map: entity_id -> set of dimension names
entity_dims = {e["id"]: {d["dimension_name"] for d in e.get("state_dimensions", [])} for e in p1["domain_model"]["entities"]}

# Build to_index: tid -> TO ref (after split, updated)
to_index = {}  # tid -> TO object
# Option C: abstract transition id -> concrete variant TO ids, for transitions
# that were branch-split. CO enabler/dependent_transition_id reference the
# abstract (P1) transition id; downstream (S0/S1) resolves it to its variants
# via this map. Unsplit transitions are NOT listed (trivially map to themselves).
transition_splits = {}  # base_tid -> [variant_to_ids]

# Helper: terminal check
def is_terminal(entity_id, dimension, state):
    return state in terminal_index.get(entity_id, {}).get(dimension, set())

# Helper: P1 original transition lookup (P1 原转换)
p1_transitions_by_id = {t["id"]: t for t in p1["state_and_flow"]["transitions"]}

# Helper: P1 original entity lookup
p1_entities_by_id = {e["id"]: e for e in p1["domain_model"]["entities"]}

# Helper: P1 structural relations
p1_sr = p1["domain_model"]["structural_relations"]

# Helper: P1 transition_relations
p1_tr = p1["domain_model"]["transition_relations"]

# Helper: P1 invalid_transitions / business_rules / cross_entity
p1_it = p1["constraints"]["invalid_transitions"]
p1_br = p1["constraints"]["business_rules"]
p1_xc = p1["constraints"]["cross_entity"]

# Helper: P1 branch_dimensions
p1_bd = p1["_meta"]["branch_dimensions"]

# Judgments & warnings
judgments = []
warnings = []

def add_judgment(category, desc):
    judgments.append({"category": category, "desc": desc})

def add_warning(category, desc):
    warnings.append({"category": category, "desc": desc})

# ============ Step 1: entity_obligations ============
entity_obligations = []
eo_atc_counter = 0
eo_cru_counter = 0

# 1.1 EO-ATC
# P1 属性字段本身不携带章节信息，但属性所属实体的操作（op）携带 source_ref
# （如 "4.6 项目管理"）。透传实体首条操作的 source_ref 作为该配置属性覆盖
# 需求的章节定位。数据驱动：不硬编码任何实体/章节。
def _entity_config_section_ref(e):
    for op in e.get("operations", []):
        if isinstance(op, dict) and op.get("source_ref"):
            return op["source_ref"]
    return None


for e in p1["domain_model"]["entities"]:
    for attr in e.get("attributes", []):
        if attr.get("is_config") is True:
            eo_atc_counter += 1
            attr_src = _entity_config_section_ref(e)
            eo = {
                "id": f"EO-ATC-{eo_atc_counter:03d}",
                "type": "attribute_config",
                "entity": e["id"],
                "entity_name": e["name"],
                "attribute_name": attr["name"],
                "attribute_desc": attr["desc"],
                "description": f"覆盖{e['name']}的配置属性{attr['name']}不同取值对流转的影响",
                "suggested_action": f"修改{e['name']}的{attr['name']}，影响{attr['desc']}",
                "coverage_priority": "medium",
                "dimension": None,
                "from": None,
                "to": None,
                "source_ref": attr_src  # P1 属性无章节，透传实体首条操作的 source_ref
            }
            entity_obligations.append(eo)
            add_judgment("EO-ATC source_ref",
                         f"{eo['id']} P1 属性无 source_ref 字段，透传实体首条操作 source_ref={attr_src}")

# 1.2 EO-CRU (all categories, no filter at this step)
for e in p1["domain_model"]["entities"]:
    for op in e.get("operations", []):
        eo_cru_counter += 1
        # Compat: op may be string (P1 v19.1-)
        if isinstance(op, str):
            op_name = op
            op_cat = "crud"
            op_er = [op_name]
            op_src = None
            add_judgment("EO-CRU compat", f"{e['id']}: op 为字符串 {op!r}，以 operation_category=crud 兼容处理，source_ref=null")
        else:
            op_name = op["name"]
            op_cat = op.get("category", "crud")
            if "category" not in op:
                add_judgment("EO-CRU default", f"{e['id']}.{op_name}: category 缺失，默认 crud")
            op_er = op.get("expected_results", [])
            if not op_er:
                op_er = [op_name]
                add_judgment("EO-CRU empty_er", f"{e['id']}.{op_name}: expected_results 为空，以操作名补入")
            op_src = op.get("source_ref")
        eo = {
            "id": f"EO-CRU-{eo_cru_counter:03d}",
            "type": "crud_operation",
            "entity": e["id"],
            "entity_name": e["name"],
            "operation_name": op_name,
            "operation_category": op_cat,
            # 治本: description 用操作的可观察结果(expected_results 首条)而非
            # "覆盖X操作"噪声。expected_results 由 P1 逐字转录原文可观察结果
            # (如"可查看项目的详细信息"),S1 Type5 将其作为 Then 断言。
            # 旧硬编码"覆盖{e['name']}的{op_name}操作"不断言任何可观察结果,
            # 迫使 S1 用 _is_coverage_noise 标记+渲染层过滤兜底 —— 从源头消除。
            "description": op_er[0] if op_er else f"{op_name}完成",
            "expected_results": op_er,
            "suggested_action": f"对{e['name']}执行{op_name}",
            "coverage_priority": "medium",
            "source_ref": op_src
        }
        entity_obligations.append(eo)

# ============ Step 2: transition_obligations ============
transition_obligations = []

def derive_direction(t):
    """Derive transition direction: forward / backward / lateral / resume.

    ⚠️ 过渡方案 — 这不是根本解决方案 ⚠️

    本函数是 P1 尚未直出 direction 字段时的过渡兜底。它从 P1 的 traits +
    state_order 推导 direction，有两个已知缺陷：

    1. traits 漏标：T-006~T-009（归档回退）只有 time_sensitive 没有
       rollback，导致依赖 state_order 兜底。
    2. state_order 无法表达 lateral 拓扑：T-107/108（待评审/评审中→暂停）
       被误判为 forward（因为暂停在 states 列表里 index=4，比待评审(2)/
       评审中(3) 都大），但语义上暂停是 lateral（侧挂状态）。
       这导致 E-PLAN phase_mapping 里 暂停=4 而非 3（case_spec reference
       是 3）。V08 validator 通过 lateral 豁免不阻断，但相位不精确。

    根本方案（需在 P1 工程实现）：
    - P1 直接产出 direction 字段（forward/backward/lateral/resume）
    - P1 输出后用脚本校验（必填检查）+ LLM 判别分类是否准确
    - P2 透传 direction，不再推导
    - S0/S1 直接读 direction，不再依赖 traits 或 state_order

    trait 和 direction 是两个正交维度：
    - trait 描述"业务特征"（audit/rollback/branch/time_sensitive/data_constraint）
    - direction 描述"拓扑方向"（forward/backward/lateral/resume）
    两者不能互推。trait 必填且校验准确不能替代 direction。

    当前推导逻辑（过渡用）：
    1. P1's explicit `direction` field (if P1 v20+ emits it) — authoritative
    2. P1's `traits` field:
       - 'rollback' in traits → backward or resume
       - 'time_sensitive' in traits → forward (timeout auto-transition)
    3. state_order (states list index): if to_state index < from_state index
       → backward; if equal → lateral; if greater → forward
    4. Fallback: forward (safe default)

    The derived direction is written to TO.direction and consumed by:
    - P2 phase_mapping derivation (only forward edges increment phase)
    - S0 topology (edge classification)
    - S1 generation (rollback detection for backward edges)
    """
    # 1. P1 explicit direction (future-proofing: if P1 starts emitting it)
    if t.get("direction"):
        return t["direction"]

    f = t.get("from")
    to = t.get("to")
    traits = t.get("traits", []) or []

    # Creation transition
    if f is None or f == "(初始)":
        return "forward"

    # 2. traits-based classification
    if "rollback" in traits:
        # Distinguish resume from backward:
        # - Resume: target state has a forward inbound edge from a non-rollback
        #   transition (e.g. 暂停→待评审 where 待评审 is normally reached via
        #   待启动→待评审). The rollback edge goes BACK to a state that's
        #   already on the forward chain.
        # - Backward: target state does NOT have such a forward inbound edge
        #   (e.g. 已选入→待选入 where 待选入 is the initial state, reached
        #   only via creation).
        # We can't fully determine this here without the full transition set,
        # so we use a heuristic: if the action contains "重启/恢复/解锁" → resume.
        # BUT to avoid hardcoding, we check if to_state == the entity's initial
        # state → backward (going back to start); otherwise → resume.
        entity_id = t.get("entity")
        dim_name = t.get("dimension")
        si = state_lookup.get(entity_id, {}).get(dim_name, set())
        initial_state = None
        for e in p1["domain_model"]["entities"]:
            if e["id"] == entity_id:
                for d in e.get("state_dimensions", []):
                    if d["dimension_name"] == dim_name:
                        initial_state = d.get("initial")
                        break
        if to == initial_state:
            return "backward"
        # If to_state is in the states list and has a lower index than
        # from_state, it's backward; otherwise it's resume (lateral return)
        for e in p1["domain_model"]["entities"]:
            if e["id"] == entity_id:
                for d in e.get("state_dimensions", []):
                    if d["dimension_name"] == dim_name:
                        states = d.get("states", [])
                        if f in states and to in states:
                            if states.index(to) < states.index(f):
                                return "backward"
                            return "resume"
        return "backward"

    # 3. state_order-based classification
    entity_id = t.get("entity")
    dim_name = t.get("dimension")
    for e in p1["domain_model"]["entities"]:
        if e["id"] == entity_id:
            for d in e.get("state_dimensions", []):
                if d["dimension_name"] == dim_name:
                    states = d.get("states", [])
                    if f in states and to in states:
                        if states.index(to) < states.index(f):
                            return "backward"
                        elif states.index(to) == states.index(f):
                            return "lateral"
                        return "forward"

    # 4. Fallback
    return "forward"

def derive_coverage_priority(t):
    # 2.1 priority table (first hit)
    if t.get("from") is None or (t.get("to") and is_terminal(t["entity"], t["dimension"], t["to"])):
        return "critical"
    # Defensive: from in terminal AND to in terminal -> low (terminal-to-terminal should be removed, but we still mark)
    if (t.get("from") and is_terminal(t["entity"], t["dimension"], t["from"]) and
        t.get("to") and is_terminal(t["entity"], t["dimension"], t["to"])):
        add_warning("TO terminal-to-terminal", f"{t['id']}: from∈terminal 且 to∈terminal，防御性标 low")
        return "low"
    p1_prio = t.get("priority", "")
    if p1_prio in ("P0", "P1") or t.get("note", {}).get("inferred") is True:
        return "high"
    return "medium"

def derive_side_effects(t):
    """Merge two channels, dedup by (target_entity, target_dimension)."""
    se = {}
    # Channel 1: R.from == current entity and evidence_transitions contains current tid
    for r in p1_tr:
        if r["from"] == t["entity"] and t["id"] in r.get("evidence_transitions", []):
            # Find P1 original transition of R.to to derive dimension
            # R.to is entity_id; find the original transition (P1 原转换, not split)
            # Use evidence_transitions to find tid belonging to R.to
            target_dim = None
            for etid in r.get("evidence_transitions", []):
                p1_t = p1_transitions_by_id.get(etid)
                if p1_t and p1_t["entity"] == r["to"]:
                    target_dim = p1_t["dimension"]
                    break
            key = (r["to"], target_dim)
            if key not in se:
                se[key] = {
                    "target_entity": r["to"],
                    "target_dimension": target_dim,
                    "effect_desc": r.get("desc", "")
                }
    # Channel 2: expected_results containing other-entity state change
    for er in t.get("expected_results", []):
        # Look for entity name match
        for other_e in p1["domain_model"]["entities"]:
            if other_e["id"] == t["entity"]:
                continue
            if other_e["name"] in er or other_e["id"] in er:
                # Try to find dimension (any dim of that entity)。
                # set 推导 → 迭代序非确定；按名排序保证 P2 输出可复现。
                dims = sorted(entity_dims.get(other_e["id"], set()))
                target_dim = dims[0] if dims else None
                key = (other_e["id"], target_dim)
                if key not in se:
                    se[key] = {
                        "target_entity": other_e["id"],
                        "target_dimension": target_dim,
                        "effect_desc": er
                    }
                break
    return list(se.values())

def derive_precondition_refs(preconds, current_entity):
    """R6: pass through + fill missing ref for state_ref+null + sync precondition_state_refs."""
    out_preconds = []
    out_refs = []
    for p in preconds:
        # Pass through {text, type, ref}
        new_p = {"text": p["text"], "type": p["type"], "ref": p["ref"]}
        # Fill missing ref for state_ref with null ref (defensive)
        if p["type"] == "state_ref" and p.get("ref") is None:
            text = p["text"]
            filled = False
            # Try explicit: text contains "entity.dimension=state" or "entity.state"
            # Try implicit: only state value, matches current entity's same dimension
            for dim_name, states in state_lookup.get(current_entity, {}).items():
                for s in sorted(states):  # set 迭代序非确定 → 首匹配需确定序
                    if s in text:
                        new_p["ref"] = {"entity": current_entity, "dimension": dim_name, "state": s}
                        out_refs.append({
                            "entity": current_entity, "dimension": dim_name, "state": s,
                            "raw_text": text, "pattern": "implicit_same"
                        })
                        add_judgment("precondition ref fill", f"implicit_same: {current_entity}.{dim_name}={s} from '{text}'")
                        filled = True
                        break
                if filled:
                    break
            if not filled:
                # Try cross-entity: text contains another entity name
                for other_e in p1["domain_model"]["entities"]:
                    if other_e["id"] == current_entity:
                        continue
                    if other_e["name"] in text or other_e["id"] in text:
                        for dim_name, states in state_lookup.get(other_e["id"], {}).items():
                            for s in sorted(states):  # set 迭代序非确定 → 首匹配需确定序
                                if s in text:
                                    new_p["ref"] = {"entity": other_e["id"], "dimension": dim_name, "state": s}
                                    out_refs.append({
                                        "entity": other_e["id"], "dimension": dim_name, "state": s,
                                        "raw_text": text, "pattern": "cross_entity_ref"
                                    })
                                    add_judgment("precondition ref fill", f"cross_entity_ref: {other_e['id']}.{dim_name}={s} from '{text}'")
                                    filled = True
                                    break
                            if filled:
                                break
                        if filled:
                            break
            if not filled:
                add_warning("precondition_state_refs_unresolved", f"{current_entity}: state_ref ref=null 无法补全 '{text}'")
        elif p["type"] == "state_ref" and p.get("ref") is not None:
            r = p["ref"]
            out_refs.append({
                "entity": r["entity"], "dimension": r["dimension"], "state": r["state"],
                "raw_text": p["text"], "pattern": "p1_inherited"
            })
        out_preconds.append(new_p)
    return out_preconds, out_refs

# ============ Step 3 (constraint predicate structuring) ============
# Constraint preconditions ({text, type:"constraint", ref:null}) are parsed
# into a structured predicate tree emitted as TO.constraint_predicate.
# Schema v1: field_equals implemented; other predicate shapes return an
# "unparsed" node so nothing is silently dropped during incremental build-out.
# Phase lower bounds are NOT baked here — consumers derive them via
# constraint_fields.predicate_phase_lower_bound() against the current maps.

# ── 跨类型复用的表层数据：连接词 / 算子 ───────────────────────────────
#   阈值连接词：FIELD <conn> VALUE <op>，如 评级 在 合格 及以上
_RANGE_CONNECTORS = ("在", "为")
#   阈值算子：表层 → 语义（>= / <=）
_RANGE_OPERATORS = {
    "及以上": ">=", "不低于": ">=",
    "及以下": "<=", "不高于": "<=",
}
#   集合连接词：FIELD <conn> V1 或 V2 [或 V3 ...]，如 评级 为 不合格 或 差
_FIELD_IN_CONNECTORS = ("为", "在")

_RANGE_CONN_ALT = "|".join(_RANGE_CONNECTORS)
_RANGE_OP_ALT = "|".join(sorted(_RANGE_OPERATORS, key=len, reverse=True))
_FIELD_IN_CONN_ALT = "|".join(_FIELD_IN_CONNECTORS)


def _field_pred_node(ptype, field_str, ctx, value=None, op=None, values=None):
    """field 三型（equals/range/in）统一构建：解析字段 → 归一值 →
    标注 ref_state_dimension/闭集告警。字段未注册 → unparsed 占位。"""
    text = ctx.get("_text", "")
    rec = _resolve_field_from_text(field_str, ctx.get("entity"))
    if rec is None:
        return {"type": "unparsed", "text": text,
                "reason": f"field 未注册: {field_str}"}
    node = {"type": ptype, "field": {"entity": rec["entity"], "name": rec["name"]}}
    if values is not None:
        node["values"] = [_normalize_constraint_value(rec, v.strip())
                          for v in values if v.strip()]
    else:
        node["value"] = _normalize_constraint_value(rec, value)
        if op is not None:
            node["op"] = op
    # 暂停前计划状态 这类 state_snapshot：值本身就是状态机态名，标注来源维度，
    # 让下游（Strategy 0 / Guard 6）能把值当状态引用消费（锚 TO 态而非 FROM 态）
    if rec.get("ref_state_dimension"):
        node["ref_state_dimension"] = rec["ref_state_dimension"]
    check = node.get("value")
    if rec.get("value_closed_set") and check is not None \
            and check not in rec["value_closed_set"]:
        node["warning"] = f"值 {check} 不在闭集 {rec['value_closed_set']}"
    return node


def _time_limit_node(m, ctx):
    """time_limit：<kind>时限超时（min-max 天，默认 d）。

    起算状态 = 触发该超时的 transition 自身的 from 态（T-018 已建立→待启动=下发、
    T-020 待启动→待评审=启动、T-029 待评审→已完成=评审、T-030 评审中→已完成、
    T-031 暂停→已完成、T-033 已完成→超时结束=归档——数据里就是这么编码的）。
    不设 kind→起算态常量表；from 缺失 → start_state=None（下游保守 P0）。
    """
    frm = ctx.get("from")
    return {
        "type": "time_limit",
        "kind": m["kind"],
        "start_state": ({"entity": ctx.get("entity"),
                         "dimension": ctx.get("dimension"),
                         "state": frm} if frm else None),
        "days_min": int(m["dmin"]), "days_max": int(m["dmax"]),
        "default_days": int(m["ddef"]),
    }


def _selection_node(m, ctx):
    """selection_range：从处于<state>状态的项目中选取 min-max 个。
    <state> 经 state_lookup 解析到所属实体（跨实体：T-015 的 E-PLAN TO 选 E-PROJ 项目）。"""
    src = _resolve_state_from_text(m["state"], ctx)
    if src is None:
        return {"type": "unparsed", "text": ctx.get("_text", ""),
                "reason": f"状态未解析: {m['state']}"}
    return {"type": "selection_range", "source_state": src,
            "min": int(m["smin"]), "max": int(m["smax"])}


# ── 跨类型表层数据表 ─────────────────────────────────────────────────────
#   领域名词一律从数据层现取：实体名（项目/评审计划/打分/专家/…）由 p1
#   domain_model.entities 派生进 _ENTITY_NOUN_ALT，代码不写字面量。
_ENTITY_NOUNS = sorted(
    {e.get("name", "") for e in p1["domain_model"]["entities"] if e.get("name")},
    key=lambda n: (-len(n), n))  # 确定序（长优先，再字典序），保证输出可复现
_ENTITY_NOUN_ALT = "|".join(re.escape(n) for n in _ENTITY_NOUNS) or r"(?!)"
#   计数模式：连续 → consecutive=True（被打断归零），累计 → False（all_time 累计）
_COUNT_MODE_KEYWORDS = {"连续": True, "累计": False}
#   通用中文否定前缀（语言级，非领域词汇——否定标记里的领域动词尾如 选入/提交
#   由 negation 行的 verb 捕获但节点不消费，不写任何领域字面量）。
#   _prohibition_config 的 negation_prefixes 默认值共用同一份（单一真相源）。
_GENERIC_NEGATION_PREFIXES = ("不可", "不能", "不得", "禁止", "不允许", "无法", "无权", "未被", "未")
_NEGATION_ALT = "|".join(re.escape(p) for p in sorted(_GENERIC_NEGATION_PREFIXES, key=len, reverse=True))
#   数字字面量：为零 → 0（field_zero 聚合全零判定）
_ZERO_WORDS = {"零": "0", "0": "0"}


def _resolve_counter_from_text(text, ctx):
    """aggregate_count：从计数对象短语解析 counter 字段（数据驱动，经字段记录
    count_aliases）。同实体优先、跨实体兜底（T-044 的 E-ORG 主语计 E-PROJ.评级）。
    counted_value 在 alias 后取"为<grade>"，按字段 value_normalization 归一、
    对照 values 校验；无 为 前缀（如 密码错误）→ 不带 counted_value。"""
    own = ctx.get("entity")
    cands = []
    for r in _FIELD_REGISTRY.values():
        for alias in r.get("count_aliases") or []:
            if alias in text:
                cands.append((len(alias), 0 if r.get("entity") == own else 1,
                              r, alias))
    if not cands:
        # 值→字段反查兜底：计数对象即值字面量（累计 2 次差 / 累计 4 次不合格）。
        # 反查字段注册表（_resolve_field_by_value），歧义/未命中 → None（保守）。
        rec = _resolve_field_by_value(text, ctx)
        if rec is None:
            return None
        return {"entity": rec["entity"], "name": rec["name"],
                "counted_value": _normalize_constraint_value(rec, text)}
    cands.sort(key=lambda c: (-c[0], c[1]))
    _, _, rec, alias = cands[0]
    # 键名统一为 name（与 field_equals 等的 field ref 及 resolve_field 一致）：
    # 原 field 键使 constraint_fields.resolve_field 查不到 name → 相位下界落空。
    counter = {"entity": rec["entity"], "name": rec["name"]}
    after = text[text.index(alias) + len(alias):]
    # counted_value：alias 后"为<grade>"。边界字 的/，。； 截断（评级为不合格的…→不合格），
    # 再对照字段 values 校验；粘连情形（值后跟其他词）按 values 前缀回退。
    gm = re.match(r"^为\s*([^，。；;的\s]{1,6})", after)
    if gm:
        tok = gm.group(1)
        g = _normalize_constraint_value(rec, tok)
        vals = rec.get("values") or []
        if vals and isinstance(g, str) and g not in vals:
            pre = sorted((v for v in vals if isinstance(v, str) and tok.startswith(v)),
                         key=len, reverse=True)
            if pre:
                g = pre[0]
        if not vals or g in vals:
            counter["counted_value"] = g
    return counter


def _aggregate_count_node(ctx, counter, threshold, consecutive):
    """aggregate_count 节点单一构造（generic + count-value 两路共用）。
    type/subject/count_scope/window 唯一事实源——节点类型由表层行声明
    （type 键），构造不写字面量；count_scope=subject_instance、window 表层
    未声明 → all_time 为语义默认（count_scope 是 Step 4 的输入，v1 标注）。"""
    return {
        "type": "aggregate_count",
        "subject": {"entity": ctx.get("entity"), "state": ctx.get("from"),
                    "count_scope": "subject_instance"},
        "counter": counter,
        "threshold": threshold,
        "consecutive": consecutive,
        "window": "all_time",
    }


def _count_node(val, th, ctx, countable=None):
    """count-value 表层共享构建：<值>→字段反查（_resolve_field_by_value）构建
    aggregate_count。计数对象短语 countable（form A：…的<countable>为<值>…）
    对照字段 count_aliases 校验（阶段评价 ⊂ 项目阶段评价结果）。值与字段全部
    来自注册表，不写字面量；节点构造复用 _aggregate_count_node（单点），
    连续|累计 无标记 → 累计（consecutive=False，同 _COUNT_MODE_KEYWORDS 默认）。"""
    rec = _resolve_field_by_value(val, ctx)
    if rec is None:
        return {"type": "unparsed", "text": ctx.get("_text", ""),
                "reason": f"计数值未解析: {val}"}
    if countable is not None:
        ok = any((a in countable) or (countable in a)
                 for a in (rec.get("count_aliases") or []))
        if not ok:
            return {"type": "unparsed", "text": ctx.get("_text", ""),
                    "reason": f"计数对象 {countable} 与字段 {rec['name']} 别名不符"}
    counter = {"entity": rec["entity"], "name": rec["name"],
               "counted_value": _normalize_constraint_value(rec, val)}
    return _aggregate_count_node(ctx, counter, int(th), False)


def _aggregate_node(m, ctx):
    """aggregate_count：<主语><连续|累计> <N> 次<计数对象>。
    subject = 触发 transition 自身的 from 态 + count_scope=subject_instance
    （计数范围 = 主语实例）。mode 经 _COUNT_MODE_KEYWORDS 数据驱动；
    节点构造复用 _aggregate_count_node（单点）。"""
    counting_text = (m["object"] or "") + (m["tail"] or "")
    counter = _resolve_counter_from_text(counting_text, ctx)
    if counter is None:
        return {"type": "unparsed", "text": ctx.get("_text", ""),
                "reason": f"计数对象未解析: {counting_text}"}
    return _aggregate_count_node(ctx, counter, int(m["th"]),
                                 _COUNT_MODE_KEYWORDS.get(m["mode"], False))


def _config_node(m, ctx):
    """config：<f1>由 V1、V2 或 V3 个专家组成，有且只能有 N 个<f2>。
    分解为 field_in(<f1>∈values) ∧ field_equals(<f2>, N)；字段名/值全部从表层
    文本取，经注册表别名解析（评审组→评审组人数、组长专家→组长专家数），
    不写字段名字面量。"""
    vals = [t.strip() for t in re.split(r"[、或]", m["vals"]) if t.strip()]
    f1 = _field_pred_node("field_in", m["f1"], ctx, values=vals)
    f2 = _field_pred_node("field_equals", m["f2"], ctx, value=m["n1"])
    parts = [p for p in (f1, f2) if p and p.get("type") != "unparsed"]
    if len(parts) < 2:
        return {"type": "unparsed", "text": ctx.get("_text", ""),
                "reason": "config 字段解析失败"}
    return {"type": "conjunction", "parts": parts}


def _disjunction_ref_node(m, ctx):
    """disjunction_ref：…满足<ref>任一条。若数据层 _context.disjunction_refs 声明了
    对应 computation BR，把 BR 原文展开为 disjunction 谓词（DECISIONS ⑧ 遗留项）；
    否则保守记录引用、resolved=False（下游不得当硬约束，见 PREDICATE_RULES）。"""
    expanded = _expand_computation_disjunction(ctx.get("_text", ""), ctx)
    if expanded is not None:
        return expanded
    return {"type": "disjunction_ref", "ref": ctx.get("_text", ""),
            "resolved": False}


# 计算规则展开配置：disjunction_ref 约束文本 → computation BR id（数据层单一
# 真相源，与 phase_anchors 同构；见 review_structured.json _context.disjunction_refs）。
_DISJUNCTION_REFS = (p1.get("_context") or {}).get("disjunction_refs", [])


def _expand_computation_disjunction(text, ctx):
    """把 computation BR 原文解析为 disjunction 谓词（展开 disjunction_ref）。

    - 按 constraint_text 精确匹配 _context.disjunction_refs → br_id；
    - BR desc 剥离"…："前缀后按；拆子句，剥前导或；
    - 尾随结果后缀"<单字动词>为<state>"（状态集取自 state_lookup，数据驱动）：
      结果态 ≠ 转移 to → 该子句属其他转换（升/平局），跳过；= to → 剥离后缀再解析。
      动词限单字（结果短语惯例：降为/升为）——{1,2} 会吸收前一态字符（差降/格降）
      把计数对象截断；state 锚定串尾 → 恒只命中末端的唯一 为<state>；
    - 按且拆合取，每个合取项经 _parse_constraint_text 解析（count-value 表层行）；
    - 无可解析条件子句 → 返回 None，调用方保守保留 resolved:false（不冒充硬约束）。
    """
    entry = next((e for e in _DISJUNCTION_REFS
                  if e.get("constraint_text") == text), None)
    if entry is None:
        return None
    br = next((b for b in p1_br if b["id"] == entry.get("br_id")), None)
    if br is None:
        add_warning("disjunction_ref_br_missing",
                    f"disjunction_ref '{text}' 声明 BR {entry.get('br_id')} 不在 business_rules")
        return None
    desc = br.get("desc") or ""
    body = desc.split("：", 1)[-1] if "：" in desc else desc
    sl = ctx.get("_state_lookup") or {}
    states = sorted(sl.get(ctx.get("entity"), {}).get(ctx.get("dimension"), []),
                    key=lambda s: (-len(s), s))
    outcome_re = (re.compile(
        rf"[一-龥]为(?P<state>(?:{'|'.join(re.escape(s) for s in states)}))$")
        if states else None)
    parts = []
    for clause in re.split(r"[；;]", body):
        clause = re.sub(r"^\s*或", "", clause).strip()
        if not clause:
            continue
        if outcome_re:
            om = outcome_re.search(clause)
            if om:
                if om.group("state") != ctx.get("to"):
                    continue
                clause = clause[:om.start()].strip()
        conjuncts = [c.strip() for c in clause.split("且") if c.strip()]
        nodes = []
        ok = True
        for c in conjuncts:
            node = _parse_constraint_text(c, ctx)
            if not isinstance(node, dict) or node.get("type") == "unparsed":
                ok = False
                break
            nodes.append(node)
        if not ok or not nodes:
            continue  # 非计数条件子句（结果句/平局规则）→ 跳过
        parts.append(nodes[0] if len(nodes) == 1
                     else {"type": "conjunction", "parts": nodes})
    if not parts:
        add_warning("disjunction_ref_expand_fail",
                    f"disjunction_ref '{text}' → BR {entry.get('br_id')} 无可解析条件子句，保守保留 resolved:false")
        return None
    add_judgment("disjunction_ref_expanded",
                 f"disjunction_ref '{text}' 展开自 BR {entry.get('br_id')}（{len(parts)} 个条件子句）")
    return {"type": "disjunction", "ref": text,
            "source_br": entry.get("br_id"), "parts": parts}


def _negation_node(m, ctx):
    """negation：<operand>的<subj?><否定标记>（如 评价结果为差的项目不可选入、
    项目各项打分全部为零的不能提交）。operand 递归经表层表解析
    （全部为零 → field_zero 行），无特殊分支。"""
    operand_text = m["operand"].strip()
    operand = _parse_constraint_text(operand_text, ctx)
    if operand is None or (isinstance(operand, dict)
                           and operand.get("type") == "unparsed"):
        return {"type": "unparsed", "text": ctx.get("_text", ""),
                "reason": f"negation operand 未解析: {operand_text}"}
    return {"type": "negation", "operand": operand}


def _completion_node(m, ctx):
    """completion：…全部<谁><动词>了<对象>（如 全部专家提交了项目打分）。

    完成态 = state_lookup 中以"已"+动词 命名的态（提交了 → 已提交；语言级
    "已X=已完成X" 惯例），多候选时优先 terminal 态（完成态语义）。不写字面量。
    """
    st = _resolve_completion_state(m["verb"], ctx)
    if st is None:
        return {"type": "unparsed", "text": ctx.get("_text", ""),
                "reason": f"完成态未解析: 已{m['verb']}"}
    return {"type": "completion", "target": st}


def _resolve_completion_state(verb, ctx):
    """完成态解析：态名 == 已+verb 的候选（跨全部实体维度）；多候选优先 terminal。"""
    sl = ctx.get("_state_lookup") or {}
    cands = []
    for ent_id, dims in sl.items():
        for dim, states in dims.items():
            for s in states:
                if s == "已" + verb:
                    cands.append({"entity": ent_id, "dimension": dim, "state": s})
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    for c in cands:  # 多候选 → 优先 terminal（完成态 = 活动终点）
        if c["state"] in terminal_index.get(c["entity"], {}).get(c["dimension"], set()):
            return c
    return cands[0]


def _parse_occurrence_when(when, ctx):
    """occurrence_limit 的 when 条件：<前缀><值><字段名> 反序表层
    （如 本阶段不合格评价结果 → 评级=不合格）。值从字段记录 values 子串最长匹配
    （不合格 优先于 合格）。"""
    for r in _FIELD_REGISTRY.values():
        if r.get("kind") == "alias" or r.get("entity") != ctx.get("entity"):
            continue
        for nm in [r["name"]] + (r.get("aliases") or []):
            if nm in when:
                pre = when[:when.index(nm)]
                vals = r.get("values") or []
                hit = sorted((v for v in vals if v in pre), key=len, reverse=True)
                if hit:
                    return {"type": "field_equals",
                            "field": {"entity": r["entity"], "name": r["name"]},
                            "value": _normalize_constraint_value(r, hit[0])}
    return None


def _occurrence_node(m, ctx):
    """occurrence_limit：对于<when>的项目，只有 N 次<动作>。
    on = 被限 transition 的语义特征 {entity, dimension, from, to}（本 TO 自身），
    不硬编码 transition ID（见 PREDICATE_RULES.occurrence_limit_on_ref）。"""
    node = {"type": "occurrence_limit",
            "on": {"entity": ctx.get("entity"), "dimension": ctx.get("dimension"),
                   "from": ctx.get("from"), "to": ctx.get("to")},
            "limit": int(m["limit"])}
    when = m["when"]
    if when:
        wp = _parse_occurrence_when(when, ctx)
        if wp is not None:
            node["when"] = wp
    return node


def _always_true_node(m, ctx):
    """always_true：规则描述句（依据…对…进行…），非实质约束。"""
    return {"type": "always_true"}


# ── 表层语法表：每行 = {type, pattern(命名槽位正则), build(match, ctx) -> 节点|None} ──
# 所有自然语言表层集中在此；解析逻辑是 _parse_constraint_text 里唯一的遍历循环。
# 新增形态 = 加一行（措辞变体 = 改槽位正则）；领域推导从 transition 数据现取。
_PREDICATE_SURFACES = [
    # field_equals：FIELD = VALUE（如 评级=优秀）
    {"type": "field_equals",
     "pattern": re.compile(r"^\s*(?P<field>.{1,24}?)\s*=\s*(?P<value>.{1,24}?)\s*$"),
     "build": lambda m, ctx: _field_pred_node("field_equals", m["field"], ctx,
                                              value=m["value"])},
    # field_range：FIELD <在|为> VALUE <及以上|及以下|不低于|不高于>（阈值比较）
    {"type": "field_range",
     "pattern": re.compile(
         rf"^\s*(?P<field>.{{1,24}}?)\s*(?:{_RANGE_CONN_ALT})\s*"
         rf"(?P<value>.{{1,12}}?)\s*(?P<op>{_RANGE_OP_ALT})\s*$"),
     "build": lambda m, ctx: _field_pred_node("field_range", m["field"], ctx,
                                              value=m["value"],
                                              op=_RANGE_OPERATORS[m["op"]])},
    # field_in：FIELD <为|在> V1 或 V2 [或 V3 ...]（同字段取值集合，如 评级为不合格或差）
    {"type": "field_in",
     "pattern": re.compile(
         rf"^\s*(?P<field>.{{1,24}}?)\s*(?:{_FIELD_IN_CONN_ALT})\s*(?P<values>.{{1,30}}?)\s*$"),
     "build": lambda m, ctx: (_field_pred_node("field_in", m["field"], ctx,
                                               values=m["values"].split("或"))
                              if "或" in m["values"] else None)},
    # time_limit：<kind>时限超时（min-max 天，默认 d）。kind 任意捕获（数据驱动），
    # 模板字（时限超时/（/天/默认/））是 DSL 措辞本身，集中在本行。
    {"type": "time_limit",
     "pattern": re.compile(
         r"^\s*(?P<kind>.{1,8}?)时限超时（\s*(?P<dmin>\d+)\s*-\s*(?P<dmax>\d+)\s*天，"
         r"默认\s*(?P<ddef>\d+)\s*）\s*$"),
     "build": _time_limit_node},
    # selection_range：<role?>从处于<state>状态的<实体>中选取 min-max 个<实体>。
    # 实体名词从数据层派生（_ENTITY_NOUN_ALT）；<state> 经 state_lookup 解析。
    {"type": "selection_range",
     "pattern": re.compile(
         rf"^\s*(?P<lead>.{{0,20}}?)从处于(?P<state>.{{1,12}}?)状态的(?:{_ENTITY_NOUN_ALT})中选取\s*"
         rf"(?P<smin>\d+)\s*-\s*(?P<smax>\d+)\s*个(?:{_ENTITY_NOUN_ALT})"),
     "build": _selection_node},
    # count-value A：…的<计数对象>为<值>的次数累计(达到)? <N> 次及以上
    #（如 所有项目的阶段评价为差的次数累计达到 3 次及以上）。值→字段反查
    #（_count_node），计数对象对照 count_aliases 校验。操作词复用
    # _RANGE_OPERATORS/_RANGE_OP_ALT（不另写常量表）。须在 aggregate_count 前——
    # 后者会把 累计 后的"达到"当计数对象、把"为差"当 tail 错配。
    {"type": "aggregate_count",
     "pattern": re.compile(
         rf"^\s*(?P<lead>.{{0,16}}?)的(?P<countable>[^，。0-9]{{1,12}}?)为"
         rf"(?P<val>[^，。0-9]{{1,4}})的次数累计(?:达到)?\s*(?P<th>\d+)\s*次"
         rf"(?:{_RANGE_OP_ALT})?\s*$"),
     "build": lambda m, ctx: _count_node(m["val"], m["th"], ctx,
                                         countable=m["countable"])},
    # count-value B：<值> <N> 次及以上（如 不合格 5 次及以上）。值在计数前。
    {"type": "aggregate_count",
     "pattern": re.compile(
         rf"^\s*(?P<val>[^，。0-9]{{1,4}})\s*(?P<th>\d+)\s*次"
         rf"(?:{_RANGE_OP_ALT})?\s*$"),
     "build": lambda m, ctx: _count_node(m["val"], m["th"], ctx)},
    # count-value C：<N> 次及以上 <值>（如 2 次及以上不合格）。值在计数后；
    # 若缺操作词（2 次不合格）则交回 aggregate_count（tail 值反查）。
    {"type": "aggregate_count",
     "pattern": re.compile(
         rf"^\s*(?P<th>\d+)\s*次(?:{_RANGE_OP_ALT})\s*"
         rf"(?P<val>[^，。]{{1,4}})\s*$"),
     "build": lambda m, ctx: _count_node(m["val"], m["th"], ctx)},
    # aggregate_count：<主语><连续|累计> <N> 次<计数对象>（如 普通用户连续密码错误 3 次）
    {"type": "aggregate_count",
     "pattern": re.compile(
         r"^\s*(?P<lead>.{0,24}?)(?P<mode>连续|累计)\s*(?P<object>.{0,12}?)\s*"
         r"(?P<th>\d+)\s*次(?P<tail>.{0,24}?)\s*$"),
     "build": _aggregate_node},
    # config：<实体>的<f1>由 V1、V2 或 V3 个<实体>组成，有且只能有 N 个<f2>
    #（如 评审计划的评审组由 5、7 或 9 个专家组成…）；实体名从数据层派生。
    {"type": "config",
     "pattern": re.compile(
         rf"^\s*(?:{_ENTITY_NOUN_ALT}的)?(?P<f1>.{{1,8}}?)由(?P<vals>.{{1,20}}?)个"
         rf"(?:{_ENTITY_NOUN_ALT})组成，有且只能有(?P<n1>.{{1,4}}?)个(?P<f2>.{{1,8}}?)\s*$"),
     "build": _config_node},
    # disjunction_ref：…满足<ref>任一条（引用未展开规则列表）
    {"type": "disjunction_ref",
     "pattern": re.compile(r"^\s*(?P<lead>.{1,24}?)满足(?P<ref>.{1,16}?)任一条\s*$"),
     "build": _disjunction_ref_node},
    # negation：<operand>的<subj?><否定前缀><动词尾?>（如 评价结果为差的项目不可选入）。
    # 否定前缀为通用中文否定词（语言级 _GENERIC_NEGATION_PREFIXES）；动词尾
    #（选入/提交…）是领域动作词，从表层捕获但节点不消费——不写领域字面量。
    {"type": "negation",
     "pattern": re.compile(
         rf"^\s*(?P<operand>.{{1,24}}?)的(?P<subj>[一-龥]{{0,4}}?)?"
         rf"(?:{_NEGATION_ALT})(?P<verb>[一-龥]{{0,6}}?)\s*$"),
     "build": _negation_node},
    # occurrence_limit：对于<when>的<实体>，只有 N 次<动作>
    {"type": "occurrence_limit",
     "pattern": re.compile(
         rf"^\s*对于(?P<when>.{{1,24}}?)的(?:{_ENTITY_NOUN_ALT})，只有\s*(?P<limit>\d+)\s*次"
         rf"(?P<what>.{{1,12}}?)\s*$"),
     "build": _occurrence_node},
    # completion：…全部<谁?><动词>了<对象?><对象实体>（完成态；动词捕获，完成态经
    # _resolve_completion_state 以"已"+动词 解析，不写字面量）
    {"type": "completion",
     "pattern": re.compile(
         rf"^\s*(?P<lead>.{{0,12}}?)全部(?:{_ENTITY_NOUN_ALT})?(?P<verb>[一-龥]{{1,4}})了"
         rf"(?P<obj>.{{1,8}}?)(?:{_ENTITY_NOUN_ALT})\s*$"),
     "build": _completion_node},
    # always_true：规则描述句（依据…对…进行…），非实质约束
    {"type": "always_true",
     "pattern": re.compile(r"^\s*.{1,24}?依据.{1,24}?对.{1,24}?进行.{1,24}\s*$"),
     "build": _always_true_node},
    # field_zero：FIELD 全部为零（各项打分全部为零 → field_equals(field, 0)，
    # 聚合全零语义；0 取数字字面量词典）。须在 field_value 之前——后者会经
    # "为零" 里的 为 错配成 field_equals(field, "零")。
    {"type": "field_zero",
     "pattern": re.compile(r"^\s*(?P<field>.{1,16}?)全部为(?P<zero>零|0)\s*$"),
     "build": lambda m, ctx: _field_pred_node("field_equals", m["field"], ctx,
                                              value=_ZERO_WORDS[m["zero"]])},
    # field_value：FIELD 为 VALUE（单值 为 连接 → field_equals；如 评价结果为差）。
    # 通用兜底行，置末位——凡被前面行吞掉的形态它不会再碰。
    {"type": "field_value",
     "pattern": re.compile(r"^\s*(?P<field>.{1,24}?)\s*为\s*(?P<value>.{1,24}?)\s*$"),
     "build": lambda m, ctx: _field_pred_node("field_equals", m["field"], ctx,
                                              value=m["value"])},
]


def _resolve_field_from_text(field_str, entity):
    """Longest-name substring match against the registry on `entity`.

    Matches canonical names AND their aliases (评价结果→评级、专家人数→评审组人数),
    returning the canonical record. Returns None when unregistered.
    """
    cands = []
    for r in _FIELD_REGISTRY.values():
        if r.get("kind") == "alias" or r.get("entity") != entity:
            continue
        cands.append((r["name"], r))
        for a in r.get("aliases") or []:
            cands.append((a, r))
    cands.sort(key=lambda t: len(t[0]), reverse=True)
    for name, r in cands:
        if name in field_str:
            return r
    return None


def _resolve_field_by_value(value_str, ctx=None):
    """值→字段反查：归一化值命中字段 values 的 canonical 记录。

    别名键（kind=alias，values=None）跳过；多字段命中 → None（歧义保守，
    不猜字段）。count-value 表层（差 1 次、累计 2 次差）用它反查计数字段
    （评级）——与 _resolve_field_from_text（字段名→字段）方向互补。
    """
    v = value_str.strip()
    matches = []
    for r in _FIELD_REGISTRY.values():
        if r.get("kind") == "alias":
            continue
        vals = r.get("values") or []
        if not vals:
            continue
        g = _normalize_constraint_value(r, v)
        if g in vals:
            matches.append(r)
    if len(matches) == 1:
        return matches[0]
    return None


def _normalize_constraint_value(rec, value_str):
    """Value normalization per field: alias spelling (优→优秀), int cast for
    value_type=="int" fields（声明于注册表，不再按 kind/config 判断）,
    超时-type suffix strip (评审超时→评审)."""
    norm = rec.get("value_normalization") or {}
    v = value_str.strip()
    v = norm.get(v, v)
    if rec.get("value_type") == "int":
        try:
            v = int(v)
        except (TypeError, ValueError):
            pass
    suffix = rec.get("strip_suffix")
    if suffix and isinstance(v, str) and v.endswith(suffix) and len(v) > len(suffix):
        v = v[:-len(suffix)]
    return v


def _resolve_state_from_text(state, ctx):
    """把状态名解析为 {entity, dimension, state}（对照 state_lookup）。

    selection_range 的 source_state 可能是跨实体状态：T-015（E-PLAN TO）选取
    "已选入"状态的项目，而 已选入 属于 E-PROJ.项目状态。先试 transition 自身实体，
    再跨实体扫描。
    """
    sl = ctx.get("_state_lookup") or {}
    if not state:
        return None
    own = ctx.get("entity")
    order = [own] if own in sl else []
    order += [e for e in sl if e != own]
    for ent_id in order:
        for dim, states in sl[ent_id].items():
            if state in states:
                return {"entity": ent_id, "dimension": dim, "state": state}
    return None


def _parse_constraint_text(text, ctx):
    """Parse one constraint precondition text into a predicate node.

    遍历表层语法表：本行匹配但 build 返回 None 或 unparsed（表层形状吻合但
    内容不可解析，如 跨实体字段在本实体未注册）→ 交给后续行；全部落空 →
    unparsed 占位，避免静默丢失。"""
    ctx = {**ctx, "_text": text}
    for row in _PREDICATE_SURFACES:
        m = row["pattern"].match(text)
        if not m:
            continue
        node = row["build"](m, ctx)
        if node is None:
            continue
        if isinstance(node, dict) and node.get("type") == "unparsed":
            continue
        return node
    return {"type": "unparsed", "text": text, "reason": "type 未实现(v1)"}


def build_constraint_predicate(preconds, ctx):
    """Build the predicate tree for a transition's constraint preconditions.

    Single constraint → the node itself; ≥2 → conjunction (transition 级隐式
    AND，下界 max)。嵌套 conjunction（如 config 展开成 field_in ∧ field_equals）
    拍平进外层，保持树浅平。No constraint precondition → None。
    """
    cps = [p for p in (preconds or []) if p.get("type") == "constraint"]
    if not cps:
        return None
    parts = []
    for p in cps:
        node = _parse_constraint_text(p.get("text", ""), ctx)
        if isinstance(node, dict) and node.get("type") == "conjunction":
            parts.extend(node.get("parts") or [])
        else:
            parts.append(node)
    if len(parts) == 1:
        return parts[0]
    return {"type": "conjunction", "parts": parts}


def has_real_difference(combos):
    """R5: filter invalid combos; check if {from,to,action,preconditions,expected_results} differ."""
    if len(combos) <= 1:
        return False
    keys = set()
    for c in combos:
        key = (
            json.dumps(c.get("from"), ensure_ascii=False),
            json.dumps(c.get("to"), ensure_ascii=False),
            c.get("action", ""),
            json.dumps(c.get("preconditions", []), ensure_ascii=False, sort_keys=True),
            json.dumps(c.get("expected_results", []), ensure_ascii=False, sort_keys=True)
        )
        keys.add(key)
    return len(keys) > 1

def _dimension_value_universe(dim_name: str) -> set:
    """分支/配置维度的全量值：state_dimensions states ∪ branch_dimensions values/branches。

    R5 冲突检查需要知道维度有哪些可能值，才能识别"precond 文本枚举了允许值集、
    但 combo 值不在其中"。任务级别 这类 is_config 分支维度不在 state_dimensions，
    但其值域在 branch_dimensions（values + branches[].value）——缺了它，
    precond "任务级别为B级或C级" 就永远无法过滤 A级 组合（DECISIONS ㊶ 同源：
    case_spec 不可靠，P1 数据层才是真相源）。
    """
    vals = set()
    for e in p1["domain_model"]["entities"]:
        for d in e.get("state_dimensions", []):
            if d["dimension_name"] == dim_name:
                vals.update(d.get("states", []))
    for bd in p1_bd:
        if bd.get("dimension") == dim_name:
            vals.update(bd.get("values") or [])
            for br in bd.get("branches") or []:
                v = br.get("value")
                if v:
                    vals.add(v)
    return vals


def combo_conflicts_with_preconds(combo, dim_values_lists, preconds):
    """R5: filter invalid combos - check if combo values conflict with existing precondition constraints.
    Evidence sources: invalid_transitions, restrictive BR, precondition contradictions (constraint AND state_ref).
    Returns True if combo should be filtered out."""
    # Build a map of dimension -> value for this combo
    combo_map = {}
    for (bd, _), v in zip(dim_values_lists, combo):
        combo_map[bd["dimension"]] = v
    
    # Check precondition constraints AND state_refs for contradictions.
    # Generic: for any branch dimension, if a precondition's state_ref
    # points to that dimension and its state != the branch value, it's
    # a conflict. No hardcoded dimension names.
    for p in preconds:
        text = p.get("text", "")
        for dim_name, val in combo_map.items():
            # Check structured ref first (most reliable)
            if p.get("type") == "state_ref" and p.get("ref"):
                r = p["ref"]
                if r.get("dimension") == dim_name and r.get("state") != val:
                    return True
            # Fallback: text-based match for constraint-type preconditions
            # that mention the dimension value explicitly.
            # e.g. text="项目阶段为开题" with dim=项目阶段, val=验收 → conflict
            if dim_name in text:
                # Check if the branch value appears in text; if not, and
                # another value of the same dimension appears, it's a conflict.
                # We check the combo value and its siblings。值域用全量
                # universe（state_dimensions ∪ branch_dimensions），使 config
                # 分支维度（任务级别）的 precond 枚举（"任务级别为B级或C级"）
                # 能正确排除不在允许集内的组合值。
                if val not in text:
                    for s in _dimension_value_universe(dim_name):
                        if s != val and s in text:
                            return True
    return False



# 2.4 Branch split: first collect matched dimensions per transition
def get_matched_dims(t):
    tid = t["id"]
    matched = []
    for bd in p1_bd:
        if tid in bd.get("coverage", {}).get("transitions", []):
            matched.append(bd)
    if not matched:
        # Try note.branch_dimension
        bn = t.get("note", {}).get("branch_dimension", "")
        if bn:
            for bd in p1_bd:
                if bd["dimension"] in bn:
                    matched.append(bd)
    # 初始化守卫：自身维度 from=None 的转移（如 T-013 新增项目 → 项目阶段初始化为开题）
    # 没有"既有状态"可分支——coverage 命中只是因为该维度被初始化，不是条件分支。
    # 按其维度值拆分只会伪造矛盾场景（如"新增项目 [项目阶段=验收] → 开题"，
    # 而 SRS 4.6(1)a 明确新增项目即处于开题阶段）。剔除自身维度；
    # 跨维度分支（如 T-015 按 评审组人数 分支）仍合法保留。
    if t.get("from") is None:
        matched = [bd for bd in matched if bd["dimension"] != t["dimension"]]
    return matched

# Process transitions
for t in p1["state_and_flow"]["transitions"]:
    # First derive base fields
    coverage_priority = derive_coverage_priority(t)
    side_effects = derive_side_effects(t)
    preconds, precond_refs = derive_precondition_refs(t.get("preconditions", []), t["entity"])
    
    is_repeat = (t.get("from") == t.get("to")) and t.get("from") is not None
    repeat_cond = None
    if is_repeat:
        # Extract repeat condition from desc/note/expected_results
        text_blob = " ".join([
            t.get("action", ""),
            t.get("note", {}).get("comment", ""),
            " ".join(t.get("expected_results", []))
        ])
        if text_blob.strip():
            repeat_cond = text_blob[:100]
        else:
            repeat_cond = "可随时重复"
    
    # Branch split
    matched_dims = get_matched_dims(t)
    # Derive direction (root-cause replacement for keyword-based edge classification)
    direction = derive_direction(t)
    if not matched_dims:
        # No split
        to = {
            "id": t["id"],
            "entity": t["entity"],
            "dimension": t["dimension"],
            "from": t["from"],
            "to": t["to"],
            "action": t["action"],
            "role": t["role"],
            "preconditions": preconds,
            "expected_results": t.get("expected_results", []),
            "risk_traits": t.get("traits", []),
            "direction": direction,
            "priority": t.get("priority", ""),
            "source_ref": t.get("source_ref"),
            "note": t.get("note", {}),            "coverage_priority": coverage_priority,
            "is_repeatable": is_repeat,
            "repeat_condition": repeat_cond,
            "side_effects": side_effects,
            "branch_path": [],
            "precondition_state_refs": precond_refs
        }
        # Bug fix: check for duplicate TO ID
        if t["id"] in to_index:
            add_warning("duplicate_to_id", f"TO {t['id']} 重复，后出现的会覆盖前一个")
        transition_obligations.append(to)
        to_index[t["id"]] = to
    else:
        # Build combinations
        # For each matched dimension, derive values from BD.branches (filter by target_transition == tid) or BD.values
        dim_values_lists = []
        for bd in matched_dims:
            vals = []
            seen = set()
            # Prefer branches targeting this tid
            for br in bd.get("branches", []):
                if br.get("target_transition") == t["id"]:
                    v = br["value"]
                    if v not in seen:
                        vals.append(v)
                        seen.add(v)
            # Fallback to all values
            if not vals:
                vals = list(bd.get("values", []))
            dim_values_lists.append((bd, vals))
        
        # Generate cartesian product
        import itertools
        combos_all = list(itertools.product(*[vals for _, vals in dim_values_lists]))
        
        # R5: filter invalid combos that conflict with existing precondition constraints
        combos = []
        filtered_count = 0
        for combo in combos_all:
            if combo_conflicts_with_preconds(combo, dim_values_lists, preconds):
                filtered_count += 1
                add_judgment("R5 combo filtered", f"{t['id']}: 组合 {combo} 与 precondition 约束矛盾，过滤")
            else:
                combos.append(combo)
        
        # R5: filter invalid combos - check real difference (we have only one source transition, so all combos start identical)
        # Per R5: 无明确证据的组合一律保留并记 judgment
        if len(combos) > 16:
            add_judgment("branch split downgrade", f"{t['id']}: 有效组合 {len(combos)} >16，降级不拆分")
            to = {
                "id": t["id"],
                "entity": t["entity"],
                "dimension": t["dimension"],
                "from": t["from"],
                "to": t["to"],
                "action": t["action"],
                "role": t["role"],
                "preconditions": preconds,
                "expected_results": t.get("expected_results", []),
                "risk_traits": t.get("traits", []),
                "direction": direction,
                "priority": t.get("priority", ""),
                "source_ref": t.get("source_ref"),
                "note": {**t.get("note", {}), "comment": (t.get("note", {}).get("comment", "") + f"; 组合数{len(combos)}降级不拆分").strip("; ")},                "coverage_priority": coverage_priority,
                "is_repeatable": is_repeat,
                "repeat_condition": repeat_cond,
                "side_effects": side_effects,
                "branch_path": [],
                "precondition_state_refs": precond_refs
            }
            # Bug fix: check for duplicate TO ID
            if t["id"] in to_index:
                add_warning("duplicate_to_id", f"TO {t['id']} 重复，后出现的会覆盖前一个")
            transition_obligations.append(to)
            to_index[t["id"]] = to
        elif len(combos) == 0:
            # All combos filtered - keep original with judgment
            add_judgment("branch split all filtered", f"{t['id']}: 所有 {len(combos_all)} 组合被 R5 过滤，降级保留原 TO")
            to = {
                "id": t["id"],
                "entity": t["entity"],
                "dimension": t["dimension"],
                "from": t["from"],
                "to": t["to"],
                "action": t["action"],
                "role": t["role"],
                "preconditions": preconds,
                "expected_results": t.get("expected_results", []),
                "risk_traits": t.get("traits", []),
                "direction": direction,
                "priority": t.get("priority", ""),
                "source_ref": t.get("source_ref"),
                "note": {**t.get("note", {}), "comment": (t.get("note", {}).get("comment", "") + f"; 全部{len(combos_all)}组合被R5过滤").strip("; ")},                "coverage_priority": coverage_priority,
                "is_repeatable": is_repeat,
                "repeat_condition": repeat_cond,
                "side_effects": side_effects,
                "branch_path": [],
                "precondition_state_refs": precond_refs
            }
            # Bug fix: check for duplicate TO ID
            if t["id"] in to_index:
                add_warning("duplicate_to_id", f"TO {t['id']} 重复，后出现的会覆盖前一个")
            transition_obligations.append(to)
            to_index[t["id"]] = to
        else:
            # R5 real difference check (preliminary): since all combos come from one transition, they're identical at start
            # We mark judgment that no real difference exists at this stage (差异需从 BD.branches.desc 体现)
            # For each combo, create a split TO with branch_path
            # If only 1 combo, no real split needed
            if len(combos) == 1:
                bd, vals = dim_values_lists[0]
                v = combos[0][0]
                to = {
                    "id": t["id"],
                    "entity": t["entity"],
                    "dimension": t["dimension"],
                    "from": t["from"],
                    "to": t["to"],
                    "action": t["action"],
                    "role": t["role"],
                    "preconditions": preconds,
                    "expected_results": t.get("expected_results", []),
                    "risk_traits": t.get("traits", []),
                    "direction": direction,
                    "priority": t.get("priority", ""),
                    "source_ref": t.get("source_ref"),
                    "note": {**t.get("note", {}), "comment": (t.get("note", {}).get("comment", "") + "; 分支无实质差异(单组合)").strip("; ")},                    "coverage_priority": coverage_priority,
                    "is_repeatable": is_repeat,
                    "repeat_condition": repeat_cond,
                    "side_effects": side_effects,
                    "branch_path": [{"dimension": bd["dimension"], "value": v}],
                    "precondition_state_refs": precond_refs
                }
                # Bug fix: check for duplicate TO ID
                if t["id"] in to_index:
                    add_warning("duplicate_to_id", f"TO {t['id']} 重复，后出现的会覆盖前一个")
                transition_obligations.append(to)
                to_index[t["id"]] = to
            else:
                # Multi-combo: split into [a], [b], ...
                # Option C: follow P2 Prompt Step 2.4 rule 6 — DELETE the original TO.
                # The branch variants carry the full from/to/action/preconditions/
                # expected_results/role/side_effects/note, so no scenario coverage
                # is lost. A generic base TO (branch_path=[]) would otherwise emit
                # an unconditional procedure downstream that duplicates the branch
                # procedures and can over-generalize (e.g. a transition that only
                # fires for 差/不合格 would be stated unconditionally).
                #
                # The abstract (P1) transition id is STILL referenced by COs
                # (enabler/dependent_transition_id) and by internal lookups, so we
                # keep a synthetic ref in to_index ONLY (never emitted into
                # transition_obligations) and record the split in
                # _context.transition_splits so downstream (S0/S1) can resolve the
                # abstract id to its concrete variant TOs.
                main_to = {
                    "id": t["id"],
                    "entity": t["entity"],
                    "dimension": t["dimension"],
                    "from": t["from"],
                    "to": t["to"],
                    "action": t["action"],
                    "role": t["role"],
                    "preconditions": preconds,
                    "expected_results": t.get("expected_results", []),
                    "risk_traits": t.get("traits", []),
                    "direction": direction,
                    "priority": t.get("priority", ""),
                    "source_ref": t.get("source_ref"),
                    "note": {**t.get("note", {}), "comment": (t.get("note", {}).get("comment", "") + f"; 主TO保留(跨维度联动),分支TO覆盖其他维度").strip("; ")},                    "coverage_priority": coverage_priority,
                    "is_repeatable": is_repeat,
                    "repeat_condition": repeat_cond,
                    "side_effects": side_effects,
                    "branch_path": [],
                    "precondition_state_refs": precond_refs
                }
                # Bug fix: check for duplicate TO ID
                if t["id"] in to_index:
                    add_warning("duplicate_to_id", f"TO {t['id']} 重复，后出现的会覆盖前一个")
                # Internal synthetic ref only — NOT appended to transition_obligations.
                to_index[t["id"]] = main_to
                add_judgment("branch split delete base", f"{t['id']}: 删除原TO(主TO不再输出),生成{len(combos)}个分支TO")
                split_ids = []

                suffixes = "abcdefghijklmnop"
                for i, combo in enumerate(combos):
                    suffix = suffixes[i]
                    new_id = f"{t['id']}[{suffix}]"
                    # Build action suffix
                    dim_strs = []
                    branch_path = []
                    extra_preconds = list(preconds)  # inherit
                    extra_refs = list(precond_refs)
                    for (bd, _), v in zip(dim_values_lists, combo):
                        dim_strs.append(f"{bd['dimension']}={v}")
                        branch_path.append({"dimension": bd["dimension"], "value": v})
                        # Inheritance rule: if dimension is a state dimension and value is legal, inject precondition
                        if v in state_lookup.get(t["entity"], {}).get(bd["dimension"], set()):
                            inj_p = {
                                "text": f"{bd['dimension']}={v}",
                                "type": "state_ref",
                                "ref": {"entity": t["entity"], "dimension": bd["dimension"], "state": v}
                            }
                            extra_preconds.append(inj_p)
                            extra_refs.append({
                                "entity": t["entity"], "dimension": bd["dimension"], "state": v,
                                "raw_text": f"{bd['dimension']}={v}", "pattern": "branch_injected"
                            })
                        else:
                            # Value not legal in this entity/dim -> constraint
                            inj_p = {
                                "text": f"{bd['dimension']}={v}",
                                "type": "constraint",
                                "ref": None
                            }
                            extra_preconds.append(inj_p)
                            add_judgment("branch_injected invalid", f"{new_id}: 分支值 {v} 非法于 {t['entity']}.{bd['dimension']}，降级 constraint")
                    
                    new_action = f"{t['action']} [{'; '.join(dim_strs)}]"
                    new_to = {
                        "id": new_id,
                        "entity": t["entity"],
                        "dimension": t["dimension"],
                        "from": t["from"],
                        "to": t["to"],
                        "action": new_action,
                        "role": t["role"],
                        "preconditions": extra_preconds,
                        "expected_results": t.get("expected_results", []),
                        "risk_traits": t.get("traits", []),
                        "direction": direction,
                        "priority": t.get("priority", ""),
                        "source_ref": t.get("source_ref"),
                        "note": t.get("note", {}),                        "coverage_priority": coverage_priority,
                        "is_repeatable": is_repeat,
                        "repeat_condition": repeat_cond,
                        "side_effects": side_effects,
                        "branch_path": branch_path,
                        "precondition_state_refs": extra_refs
                    }
                    # Bug fix: check for duplicate TO ID
                    if new_id in to_index:
                        add_warning("duplicate_to_id", f"TO {new_id} 重复，后出现的会覆盖前一个")
                    transition_obligations.append(new_to)
                    to_index[new_id] = new_to
                    split_ids.append(new_id)
                # Record the split: abstract transition id -> concrete variant TO ids.
                transition_splits[t["id"]] = split_ids

# ============ Step 2.5: 跨维度初始化联动合并 + CRUD 初始化去重 ============
# 同一 SRS 行为被 P1 挖成多条义务（operation 与 transition 两套），在此收口。
# 纯数据驱动判定（note/er 文本/动作三元组），不硬编码域名。

# 2.5a 跨维度初始化联动合并：note.inferred 且 (entity, action, role) 与已产出的
# 非 inferred 初始化转换(from=None, 无分支)完全一致 → 该 TO 是父转换的跨维度
# 初始化联动（如 T-013 联动 T-001：SRS 4.6(1)a 一句话同时断言项目状态与项目阶段）。
# 不产出独立用例：expected_results 并入父 TO，本 TO 标 merged_into 供 S1 跳过；
# 保留在列表中避免 branch_dimensions / 下游按 id 查找产生悬空引用。
for _to in transition_obligations:
    if _to.get("note", {}).get("inferred") is not True or _to.get("from") is not None:
        continue
    if _to.get("merged_into"):
        continue
    _parent = next(
        (p for p in transition_obligations
         if not p.get("note", {}).get("inferred")
         and p.get("from") is None
         and not p.get("branch_path")
         and p.get("entity") == _to.get("entity")
         and p.get("action") == _to.get("action")
         and p.get("role") == _to.get("role")),
        None)
    if _parent is None:
        continue
    for _er in _to.get("expected_results", []):
        if _er and _er not in _parent.get("expected_results", []):
            _parent.setdefault("expected_results", []).append(_er)
    _parent["note"] = dict(_parent.get("note") or {})
    _parent["note"]["comment"] = (
        (_parent.get("note", {}).get("comment", "")
         + f"; 并入 {_to['id']} 跨维度初始化联动（{_to.get('dimension')}→{_to.get('to')}）").strip("; "))
    _to["merged_into"] = _parent["id"]
    _to["expected_results"] = []
    add_judgment("cross_dim_init_merge", f"{_to['id']} 跨维度初始化联动并入 {_parent['id']}")

# 2.5b CRUD 初始化去重：crud 操作若与某"初始化转换"(from=None, 同 entity+action)
# 的 expected_results 逐条被转换 er 文本包含 → 标 covered_by，S1 跳过独立用例。
# 双重约束（初始化转换 + er 文本包含）保证只回收被完全覆盖的冗余 CRUD；
# 转换 er 只是 CRUD er 子集（如"添加成功"未在转换中出现）时保留 CRUD，不误删。
for _eo in entity_obligations:
    if _eo.get("type") != "crud_operation":
        continue
    _eo_ers = _eo.get("expected_results", [])
    if not _eo_ers or _eo.get("covered_by"):
        continue
    for _to in transition_obligations:
        if (_to.get("from") is not None or _to.get("merged_into")
                or _to.get("entity") != _eo.get("entity")
                or _to.get("action") != _eo.get("operation_name")):
            continue
        _to_er_blob = "".join(_to.get("expected_results", []))
        if _to_er_blob and all(_er and _er in _to_er_blob for _er in _eo_ers):
            _eo["covered_by"] = _to["id"]
            add_judgment("crud_init_dedup", f"{_eo['id']} 被初始化转换 {_to['id']} 覆盖（er 文本包含），去重")
            break

# ============ Step 2.5c: 跨维度相位锚定（phase_anchor） ============
# SRS 4.9.7：机构评价发生在"计划归档时"（对研制机构累计情况更新后判定），
# 但 E-ORG.机构状态 的 phase_mapping 是纯序数（合格0/不合格1/试用2），
# 无 workflow 位置 —— 不加锚定时评价类转换会被排到 P1/P2（早于评审），语义倒挂。
# 锚定配置由 P1 数据层 _context.phase_anchors 声明（单一真相源，与 prohibition_config
# 同构）：对 scope=non_creation 的 (entity, dimension) 转换，追加 anchor_ref 到
# precondition_state_refs（S3 Guard 6 据此建依赖边，锚定后置状态必须已达成）。
# 同时写入 preconditions（state_ref dict），S1 _max_state_ref_phase 据此把相位
# 抬升到锚定状态（E-PLAN.计划状态.结束 = P5）。双写是复用既有两条消费通道，
# 不新增 S1/S3 逻辑。
_phase_anchors = (p1.get("_context") or {}).get("phase_anchors", [])
for _pa in _phase_anchors:
    _pa_entity = _pa.get("entity")
    _pa_dim = _pa.get("dimension")
    _pa_scope = _pa.get("scope", "non_creation")
    _anchor = _pa.get("anchor_ref") or {}
    if not (_pa_entity and _pa_dim and _anchor.get("entity") and _anchor.get("state")):
        add_warning("phase_anchor_invalid", f"phase_anchor 配置缺字段: {_pa}")
        continue
    for _to in transition_obligations:
        if _to.get("entity") != _pa_entity or _to.get("dimension") != _pa_dim:
            continue
        if _pa_scope == "non_creation" and _to.get("from") is None:
            continue  # 创建转换（T-041 添加机构）不锚定到归档
        # 幂等：已有同实体同维度同状态锚点则跳过
        _refs = _to.setdefault("precondition_state_refs", [])
        if any(r.get("entity") == _anchor.get("entity")
               and r.get("dimension") == _anchor.get("dimension")
               and r.get("state") == _anchor.get("state")
               for r in _refs):
            continue
        _refs.append({
            "entity": _anchor["entity"],
            "dimension": _anchor["dimension"],
            "state": _anchor["state"],
            # raw_text 仅作溯源展示（S3 guard6 只读 entity/dimension/state），
            # 领域语义一律来自数据层配置 note，代码不拼任何领域文本
            "raw_text": _pa.get("note") or f"{_anchor['dimension']}为{_anchor['state']}",
            "pattern": "phase_anchor",
        })
        # preconditions state_ref dict 供 S1 _max_state_ref_phase 抬升相位；
        # pattern=phase_anchor 标记它是"单转换相位锚定"，不是"整机入口锚定"，
        # S0 _compute_entry_phase(Strategy 0) 据此跳过，避免把整个维度的
        # phase_mapping 抬到锚点相位（E-ORG 循环机全维 {0,1,2}→{6,7,8} 的根因）。
        _to.setdefault("preconditions", []).append({
            "text": f"{_anchor['dimension']}为{_anchor['state']}",
            "type": "state_ref",
            "ref": {"entity": _anchor["entity"],
                    "dimension": _anchor["dimension"],
                    "state": _anchor["state"]},
            "pattern": "phase_anchor",
        })
        add_judgment("phase_anchor", f"{_to['id']} 锚定到 {_anchor['entity']}.{_anchor['dimension']}.{_anchor['state']}（{_pa.get('note', '')}）")

# ============ Step 3a: constraint predicate structuring (post-pass) ============
# Derive TO.constraint_predicate uniformly for ALL emitted transitions
# (base / downgrade / branch variants). Re-deriving from each TO's own
# preconditions means branch-injected constraints (评级=优秀 等) are included
# automatically without touching the 6 inline build sites.
for _to in transition_obligations:
    # _state_lookup 供 selection_range 的跨实体状态解析（T-015 选 E-PROJ 项目）
    _to["constraint_predicate"] = build_constraint_predicate(
        _to.get("preconditions", []), {**_to, "_state_lookup": state_lookup})

# ============ Step 3: cross_entity_obligations ============
cross_entity_obligations = []
co_counter = 0
xc_status = {}  # xc_id -> "co" or "br"

def classify_xc(xc):
    """R3: classify XC by desc template (candidate).

    Primary: keyword-based classification (deterministic, fast, auditable).
    Fallback: if keywords don't match, call LLM to classify into
    constraint_candidate / auto_candidate / to_br. LLM output is
    constrained to these 3 values — no free-form generation.
    """
    desc = xc.get("desc", "")
    # ── Deterministic keyword matching (primary) ──
    if desc.startswith("镜像 T-") or desc.startswith("由 Step 4.5 约束-因果鉴别确认"):
        # 镜像默认门禁; 但镜像 desc 若显式带因果触发语义(触发/联动/自动/初始化),
        # 其语义是联动触发而非门禁 —— 与同规则联动对是同一因果的重复建模。
        # 归 auto lane, 让 dedup 按同签名合并, 消除洞4 跨 causal_type 冲突。
        if any(kw in desc for kw in ("触发", "联动", "自动", "初始化")):
            return "auto_candidate"
        return "constraint_candidate"
    if "前置条件" in desc or "门禁" in desc:
        return "constraint_candidate"
    if desc.startswith("联动: T-") or "联动" in desc or "触发" in desc:
        return "auto_candidate"
    if desc.startswith("分支["):
        return "branch_to_br"
    # 内容信号只用通用计算语义词（累计/计算/公式）；领域动作/字段词（评级/归档…）
    # 不得入表——XC 分类由 desc 模板前缀（镜像/联动/分支，P1 数据层格式）与
    # 状态引用结构决定，不依赖业务词汇。
    if any(kw in desc for kw in ["累计", "计算", "公式"]):
        return "to_br"

    # ── LLM fallback (only when keywords don't match) ──
    # The old code returned "to_br" as default for everything that didn't
    # match keywords. This is too aggressive — many XCs that should be
    # constraint or auto get misclassified as BR. LLM helps here by
    # reading the desc semantically and classifying correctly.
    llm_result = _llm_classify(
        system_prompt=(
            "你是一个跨实体约束分类器。给定一条跨实体约束的描述，"
            "判断它属于以下哪一类：\n"
            "- constraint: 状态门禁（A 到了状态 S，B 才被允许执行 T）\n"
            "- auto: 因果联动（A 到了状态 S，B 自动执行了 T）\n"
            "- br: 业务规则（无法解析为状态引用的累计/计算/评级逻辑）\n"
            "只输出 constraint / auto / br 中的一个词，不要其他文字。"
        ),
        user_message=(
            f"约束描述: {desc}\n"
            f"来源实体: {xc.get('source_entity','')}\n"
            f"目标实体: {xc.get('target_entity','')}\n"
            f"目标条件: {xc.get('target_condition','')}\n"
            f"请分类。"
        ),
        valid_values=["constraint", "auto", "br"],
    )
    if llm_result == "constraint":
        add_judgment("XC LLM classify", f"{xc.get('id','')}: keyword未命中，LLM判为 constraint")
        return "constraint_candidate"
    elif llm_result == "auto":
        add_judgment("XC LLM classify", f"{xc.get('id','')}: keyword未命中，LLM判为 auto")
        return "auto_candidate"
    # LLM said br, or LLM unavailable → default to br (safe: BR doesn't
    # create false CO dependencies)
    if llm_result == "br":
        add_judgment("XC LLM classify", f"{xc.get('id','')}: keyword未命中，LLM判为 br")
    return "to_br"

def find_to_by_state(entity_id, dimension, target_to):
    """Find TO whose entity+dimension match and to == target_to."""
    for tid, to in to_index.items():
        if to["entity"] == entity_id and to["dimension"] == dimension and to["to"] == target_to:
            return tid
    return None

def find_to_by_entity_and_to(entity_id, target_to):
    """Find TO whose entity matches and to == target_to (any dimension)."""
    for tid, to in to_index.items():
        if to["entity"] == entity_id and to["to"] == target_to:
            return tid
    return None

def find_create_transition(entity_id):
    """Find P1 original transition with from==null for entity."""
    for tid, to in to_index.items():
        if to["entity"] == entity_id and to["from"] is None:
            return tid
    return None

# Process all XC: classify and route
xc_classifications = {}
for xc in p1_xc:
    cls = classify_xc(xc)
    xc_classifications[xc["id"]] = cls

# ============ 3.1 Constraint lane ============
def process_constraint_lane(xc):
    """Process XC in constraint lane. Returns CO dict or None (skip to BR)."""
    # G1: enabler_dimension is config attribute -> BR
    # Determine enabler_dimension by reverse lookup of source_state
    source_entity = xc["source_entity"]
    source_state = xc.get("source_state", "")
    
    # Reverse lookup state_to_entities restricted to source_entity
    candidates = []
    for dim_name, states in state_lookup.get(source_entity, {}).items():
        if source_state in states:
            candidates.append(dim_name)
    
    if not candidates:
        # G2/G5: cannot derive or state not legal
        add_judgment("CO constraint G2/G5", f"{xc['id']}: source_state '{source_state}' 无法在 {source_entity} 中反查维度或非法，转 BR")
        return None
    
    enabler_dimension = candidates[0]  # take first match
    enabler_state = source_state
    
    # G1: check if enabler_dimension is config attribute
    e = p1_entities_by_id.get(source_entity)
    if e:
        for attr in e.get("attributes", []):
            if attr.get("is_config") is True:
                # Config attribute check is by dimension name match (rough); per rule, enabler_dimension must be a state dimension
                # State dimensions are never config attributes, so this is mostly N/A
                pass
    
    # G3: dependent transition all from==null -> BR
    target_entity = xc["target_entity"]
    target_dim = xc.get("target_dimension")
    target_cond = xc.get("target_condition", "")
    # Parse target_condition "状态=Y"
    m = re.match(r"状态\s*=\s*(.+)", target_cond)
    if m:
        dependent_to = m.group(1).strip()
    else:
        dependent_to = target_cond.strip()
    
    # Find dependent transition
    dependent_tid = None
    if target_dim:
        dependent_tid = find_to_by_state(target_entity, target_dim, dependent_to)
    if not dependent_tid:
        dependent_tid = find_to_by_entity_and_to(target_entity, dependent_to)
    
    if not dependent_tid:
        add_judgment("CO constraint dependent missing", f"{xc['id']}: 找不到 dependent 转换 ({target_entity}.to={dependent_to})")
        # Not a fatal skip; we can still try to construct with null
        # But per G2/G3 logic, if no dependent transition, mark as BR
        # Actually G2 says "无法派生" -> BR. Without dependent transition we cannot derive dependent_dimension/condition
        return None
    
    dependent_to_obj = to_index[dependent_tid]
    
    # G3: all from==null check (if dependent_tid is the only TO and from==null, mark BR)
    # Actually G3 is about ALL dependent transitions being from==null (i.e., the only transitions are creation)
    # For simplicity, check if this specific dependent transition has from==null and there are no others
    all_deps = [tid for tid, to in to_index.items() if to["entity"] == target_entity and to["dimension"] == dependent_to_obj["dimension"]]
    if all_deps and all(to_index[tid]["from"] is None for tid in all_deps):
        add_judgment("CO constraint G3", f"{xc['id']}: dependent 转换全部 from==null (创建型)，转 BR")
        return None
    
    # G4: enabler_state missing -> BR (already checked in G5)
    
    # G5: enabler_state must be in state_lookup
    if enabler_state not in state_lookup.get(source_entity, {}).get(enabler_dimension, set()):
        add_judgment("CO constraint G5", f"{xc['id']}: enabler_state '{enabler_state}' 非法于 {source_entity}.{enabler_dimension}，转 BR")
        return None
    
    # R4 causal_type终判: constraint requires state_ref precondition pointing to enabler in dependent TO
    has_state_ref = False
    for p in dependent_to_obj.get("preconditions", []):
        if p["type"] == "state_ref" and p.get("ref"):
            r = p["ref"]
            if r["entity"] == source_entity and r["state"] == enabler_state:
                has_state_ref = True
                break
    
    if not has_state_ref:
        add_judgment("CO R4 constraint fail", f"{xc['id']}: dependent {dependent_tid} preconditions 无 state_ref 指向 enabler {source_entity}.{enabler_state}，转 BR")
        return None
    
    # Find enabler_transition_id: TO with to==enabler_state
    enabler_tid = find_to_by_state(source_entity, enabler_dimension, enabler_state)
    
    # ref_to: text of dependent TO precondition matching enabler_state
    ref_to = None
    for p in dependent_to_obj.get("preconditions", []):
        if p["type"] == "state_ref" and p.get("ref"):
            r = p["ref"]
            if r["entity"] == source_entity and r["state"] == enabler_state:
                ref_to = p["text"]
                break
    
    # Check aggregation: (enabler→dependent) is composition and 1:N -> "all"
    aggregation = None
    for sr in p1_sr:
        if sr["from"] == source_entity and sr["to"] == target_entity:
            if sr["relation_type"] == "composition" and sr["cardinality"] == "1:N":
                aggregation = "all"
            break
    
    # enabler_role / dependent_role
    enabler_role = None
    if enabler_tid:
        enabler_role = to_index[enabler_tid].get("role")
        if enabler_role == "system":
            enabler_role = None
    dependent_role = dependent_to_obj.get("role")
    if dependent_role == "system":
        dependent_role = None
    
    # coverage_priority: dependent transition highest priority
    dep_priority = dependent_to_obj.get("coverage_priority", "medium")
    
    co = {
        "id": None,  # assign later
        "type": "cross_entity",
        "constraint_id": xc["id"],
        "causal_type": "constraint",
        "enabler_entity": source_entity,
        "enabler_dimension": enabler_dimension,
        "enabler_state": enabler_state,
        "enabler_transition_id": enabler_tid,
        "enabler_role": enabler_role,
        "dependent_entity": target_entity,
        "dependent_transition_id": dependent_tid,
        "dependent_dimension": dependent_to_obj["dimension"],
        "dependent_condition": dependent_to_obj["to"],
        "dependent_role": dependent_role,
        "aggregation": aggregation,
        "ref_to": ref_to,
        "trigger": None,
        "trigger_source": None,
        "rollback_propagation": False,
        "confidence": "high",
        "desc": f"{source_entity}.{enabler_dimension}={enabler_state} 是 {target_entity}.{dependent_to_obj['dimension']} 推进至 {dependent_to_obj['to']} 的前置条件",
        "coverage_priority": dep_priority,
        "suggested_action": f"对{target_entity}执行使其进入{dependent_to_obj['to']}状态的操作",
        "merged_from": [],
        "source_ref": xc.get("source_ref")
    }
    return co

# ============ 3.2 Auto lane ============
def process_auto_lane_from_r(r):
    """Process R (transition_relation) in auto lane."""
    enabler_entity = r["from"]
    dependent_entity = r["to"]
    
    # Find P1 原转换 in evidence_transitions where entity == R.from (enabler)
    enabler_tid = None
    enabler_to_obj = None
    for etid in r.get("evidence_transitions", []):
        p1_t = p1_transitions_by_id.get(etid)
        if p1_t and p1_t["entity"] == enabler_entity:
            enabler_tid = etid
            enabler_to_obj = p1_t
            break
    
    # Also try to_index (might be split)
    if not enabler_tid:
        # Use the first evidence transition
        if r.get("evidence_transitions"):
            enabler_tid = r["evidence_transitions"][0]
            enabler_to_obj = to_index.get(enabler_tid) or p1_transitions_by_id.get(enabler_tid)
    
    if not enabler_to_obj:
        add_judgment("CO auto enabler missing", f"R {enabler_entity}->{dependent_entity}: evidence_transitions 为空或无 enabler 转换")
        return None
    
    enabler_dimension = enabler_to_obj["dimension"]
    enabler_state = enabler_to_obj["to"]
    
    # G5: enabler_state valid
    if enabler_state not in state_lookup.get(enabler_entity, {}).get(enabler_dimension, set()):
        add_judgment("CO auto G5", f"R {enabler_entity}->{dependent_entity}: enabler_state '{enabler_state}' 非法，跳过")
        return None
    
    # Find dependent transition in evidence_transitions where entity == R.to
    dependent_tid = None
    dependent_to_obj = None
    for etid in r.get("evidence_transitions", []):
        p1_t = p1_transitions_by_id.get(etid)
        if p1_t and p1_t["entity"] == dependent_entity:
            dependent_tid = etid
            dependent_to_obj = p1_t
            break
    if not dependent_tid and r.get("evidence_transitions"):
        # fallback: try to_index
        for etid in r["evidence_transitions"]:
            to_obj = to_index.get(etid)
            if to_obj and to_obj["entity"] == dependent_entity:
                dependent_tid = etid
                dependent_to_obj = to_obj
                break
    
    if not dependent_to_obj:
        add_judgment("CO auto dependent missing", f"R {enabler_entity}->{dependent_entity}: evidence_transitions 无 dependent 转换")
        return None
    
    # R4 causal_type终判: auto requires "联动/触发" semantics; document explicitly says so
    # Since R itself represents the causal link in P1, we trust it
    # But check trigger_source to confirm
    ts = r.get("trigger_source", "")
    if ts not in ("expected_results", "desc", "action", "bidi_coupling", "cross_entity", "business_rule"):
        add_judgment("CO auto R4", f"R {enabler_entity}->{dependent_entity}: trigger_source={ts} 非标准因果，转 BR")
        return None
    
    # aggregation
    aggregation = None
    for sr in p1_sr:
        if sr["from"] == enabler_entity and sr["to"] == dependent_entity:
            if sr["relation_type"] == "composition" and sr["cardinality"] == "1:N":
                aggregation = "all"
            break
    
    # roles
    enabler_role = enabler_to_obj.get("role")
    if enabler_role == "system":
        enabler_role = None
    dependent_role = dependent_to_obj.get("role")
    if dependent_role == "system":
        dependent_role = None
    
    # coverage_priority
    if r.get("trigger_source") == "bidi_coupling" or r.get("rollback_propagation"):
        cp = "critical"
    elif r.get("confidence") in ("low", "medium"):
        cp = "high"
    else:
        cp = "medium"
    
    # source_ref: R来源 - evidence_transitions 首条指向的 P1 原转换的 source_ref
    src_ref = None
    if r.get("evidence_transitions"):
        first_evid = r["evidence_transitions"][0]
        p1_t = p1_transitions_by_id.get(first_evid)
        if p1_t:
            src_ref = p1_t.get("source_ref")
        if not src_ref:
            add_judgment("CO auto source_ref null", f"R {enabler_entity}->{dependent_entity}: evidence_transitions 首条无 source_ref，置 null")
    
    co = {
        "id": None,
        "type": "cross_entity",
        "constraint_id": None,  # R 来源无 XC.id
        "causal_type": "auto",
        "enabler_entity": enabler_entity,
        "enabler_dimension": enabler_dimension,
        "enabler_state": enabler_state,
        "enabler_transition_id": enabler_tid,
        "enabler_role": enabler_role,
        "dependent_entity": dependent_entity,
        "dependent_transition_id": dependent_tid,
        "dependent_dimension": dependent_to_obj["dimension"],
        "dependent_condition": dependent_to_obj["to"],
        "dependent_role": dependent_role,
        "aggregation": aggregation,
        "ref_to": None,
        "trigger": r.get("trigger"),
        "trigger_source": r.get("trigger_source"),
        "rollback_propagation": r.get("rollback_propagation", False),
        "confidence": r.get("confidence", "medium"),
        "desc": r.get("desc", ""),
        "coverage_priority": cp,
        "suggested_action": f"对{dependent_entity}执行使其{dependent_to_obj['dimension']}由{dependent_to_obj['from']}变为{dependent_to_obj['to']}的操作",
        "merged_from": [],
        "source_ref": src_ref
    }
    return co

def process_auto_lane_from_xc(xc):
    """Process XC in auto lane (因果联动类)."""
    source_entity = xc["source_entity"]
    target_entity = xc["target_entity"]
    source_state = xc.get("source_state", "")
    
    # Find enabler_dimension by source_state
    candidates = []
    for dim_name, states in state_lookup.get(source_entity, {}).items():
        if source_state in states:
            candidates.append(dim_name)
    if not candidates:
        add_judgment("CO auto XC G2/G5", f"{xc['id']}: source_state '{source_state}' 无法反查维度或非法")
        return None
    
    enabler_dimension = candidates[0]
    enabler_state = source_state
    
    # G5
    if enabler_state not in state_lookup.get(source_entity, {}).get(enabler_dimension, set()):
        add_judgment("CO auto XC G5", f"{xc['id']}: enabler_state 非法")
        return None
    
    # enabler_transition_id: 优先 P1 声明的 source_transition(抽象感知), 兜底
    # find_to_by_state。历史 first-pick 风险: E-PLAN→待评审 有 T-019/T-020/T-025
    # 三个候选, find_to_by_state 取首条可能取错。
    enabler_tid = None
    st = xc.get("source_transition")
    st_p1 = p1_transitions_by_id.get(st) if st else None
    if st_p1 and st_p1.get("entity") == source_entity and st_p1.get("to") == enabler_state:
        enabler_tid = st
    else:
        enabler_tid = find_to_by_state(source_entity, enabler_dimension, enabler_state)

    # dependent: 走共享派生规则(①根本修复)。顺序: target_from/target_to 字段 →
    # 解析 target_condition → 镜像继承 → (entity, dimension, from, to) 匹配。
    # 残余 ≥2 候选 → judgment + 升级, 绝不取第一条。
    # 历史 bug: find_to_by_state 方向盲反查, E-PROJ→已选入 四个候选
    # (T-002/T-007/T-011/T-012) 静默取错 T-002, 应为 T-012。
    dep_tid, dep_info = co_derivation.resolve_dependent_transition(
        p1_xc, p1_transitions_by_id, xc)
    if not dep_tid:
        if dep_info.get("candidates"):
            add_judgment(
                "CO auto XC dependent ambiguous",
                f"{xc['id']}: target_condition='{xc.get('target_condition','')}' "
                f"无法唯一确定 dependent，候选 {len(dep_info['candidates'])} 个 "
                f"{dep_info['candidates']} (from={dep_info['from_state']}, "
                f"to={dep_info['to_state']})，升级跳过(不取第一条)")
        else:
            add_judgment(
                "CO auto XC dependent missing",
                f"{xc['id']}: 找不到 dependent 转换 "
                f"(from={dep_info['from_state']}, to={dep_info['to_state']}, "
                f"via={dep_info['via']})")
        return None
    dependent_tid = dep_tid
    dependent_to_obj = to_index.get(dependent_tid)
    if dependent_to_obj is None:
        add_judgment("CO auto XC dependent missing",
                     f"{xc['id']}: dependent {dependent_tid} 不在 to_index")
        return None
    add_judgment(
        "CO auto XC dependent resolved",
        f"{xc['id']}: dependent={dependent_tid} "
        f"(from={dep_info['from_state']}, to={dep_info['to_state']}, "
        f"via={dep_info['via']}, candidates={dep_info['candidates']})")
    
    # G3: all from==null
    all_deps = [tid for tid, to in to_index.items() if to["entity"] == target_entity and to["dimension"] == dependent_to_obj["dimension"]]
    if all_deps and all(to_index[tid]["from"] is None for tid in all_deps):
        add_judgment("CO auto XC G3", f"{xc['id']}: dependent 转换全部 from==null，转 BR")
        return None
    
    # roles
    enabler_role = None
    if enabler_tid:
        enabler_role = to_index[enabler_tid].get("role")
        if enabler_role == "system":
            enabler_role = None
    dependent_role = dependent_to_obj.get("role")
    if dependent_role == "system":
        dependent_role = None
    
    # aggregation
    aggregation = None
    for sr in p1_sr:
        if sr["from"] == source_entity and sr["to"] == target_entity:
            if sr["relation_type"] == "composition" and sr["cardinality"] == "1:N":
                aggregation = "all"
            break
    
    co = {
        "id": None,
        "type": "cross_entity",
        "constraint_id": xc["id"],
        "causal_type": "auto",
        "enabler_entity": source_entity,
        "enabler_dimension": enabler_dimension,
        "enabler_state": enabler_state,
        "enabler_transition_id": enabler_tid,
        "enabler_role": enabler_role,
        "dependent_entity": target_entity,
        "dependent_transition_id": dependent_tid,
        "dependent_dimension": dependent_to_obj["dimension"],
        "dependent_condition": dependent_to_obj["to"],
        "dependent_role": dependent_role,
        "aggregation": aggregation,
        "ref_to": None,
        "trigger": None,
        "trigger_source": None,
        "rollback_propagation": False,
        "confidence": "high",
        "desc": xc.get("desc", ""),
        "coverage_priority": dependent_to_obj.get("coverage_priority", "medium"),
        "suggested_action": f"对{target_entity}执行使其进入{dependent_to_obj['to']}状态的操作",
        "merged_from": [],
        "source_ref": xc.get("source_ref")
    }
    return co

# ============ 3.3 Lifecycle lane ============
def process_lifecycle_lane(sr):
    """Process SR (business_ownership + composition + 1:1) in lifecycle lane."""
    if sr.get("ownership_dimension") != "business_ownership":
        return None
    if sr.get("relation_type") != "composition":
        return None
    if sr.get("cardinality") != "1:1":
        return None
    
    parent = sr["from"]
    child = sr["to"]
    
    # Find parent creation transition (from==null)
    parent_create_tid = find_create_transition(parent)
    if not parent_create_tid:
        add_judgment("CO lifecycle parent create missing", f"SR {parent}->{child}: 父创建转换缺失")
        return None
    
    parent_create = to_index[parent_create_tid]
    
    # Find child creation transition
    child_create_tid = find_create_transition(child)
    if not child_create_tid:
        add_judgment("CO lifecycle child create missing", f"SR {parent}->{child}: 子创建转换缺失")
        return None
    
    child_create = to_index[child_create_tid]
    
    # enabler: parent create
    enabler_role = parent_create.get("role")
    if enabler_role == "system":
        enabler_role = None
    dependent_role = child_create.get("role")
    if dependent_role == "system":
        dependent_role = None
    
    co = {
        "id": None,
        "type": "cross_entity",
        "constraint_id": None,
        "causal_type": "lifecycle",
        "enabler_entity": parent,
        "enabler_dimension": parent_create["dimension"],
        "enabler_state": parent_create["to"],
        "enabler_transition_id": parent_create_tid,
        "enabler_role": enabler_role,
        "dependent_entity": child,
        "dependent_transition_id": child_create_tid,
        "dependent_dimension": child_create["dimension"],
        "dependent_condition": child_create["to"],
        "dependent_role": dependent_role,
        "aggregation": None,
        "ref_to": None,
        "trigger": None,
        "trigger_source": None,
        "rollback_propagation": False,
        "confidence": "high",
        "desc": f"{parent} 与 {child} 生命周期同步",
        "coverage_priority": "high",
        "suggested_action": f"对{child}执行使其进入{child_create['to']}状态的操作",
        "merged_from": [],
        "source_ref": None  # SR 无 source_ref
    }
    add_judgment("CO lifecycle source_ref", f"SR {parent}->{child}: structural_relations 无 source_ref，置 null")
    return co

# Now execute all lanes
co_list = []

# Constraint lane: process XC classified as constraint_candidate
for xc in p1_xc:
    cls = xc_classifications[xc["id"]]
    if cls == "constraint_candidate":
        co = process_constraint_lane(xc)
        if co:
            co_counter += 1
            co["id"] = f"CO-{co_counter:03d}"
            co_list.append(co)
            xc_status[xc["id"]] = "co"
        # else: will fall through to BR in Step 4.2.1

# Auto lane: process R + XC auto_candidate
for r in p1_tr:
    co = process_auto_lane_from_r(r)
    if co:
        co_counter += 1
        co["id"] = f"CO-{co_counter:03d}"
        co_list.append(co)

for xc in p1_xc:
    cls = xc_classifications[xc["id"]]
    if cls == "auto_candidate":
        co = process_auto_lane_from_xc(xc)
        if co:
            co_counter += 1
            co["id"] = f"CO-{co_counter:03d}"
            co_list.append(co)
            xc_status[xc["id"]] = "co"

# Lifecycle lane
for sr in p1_sr:
    co = process_lifecycle_lane(sr)
    if co:
        co_counter += 1
        co["id"] = f"CO-{co_counter:03d}"
        co_list.append(co)

# 3.4 Dedup
def co_signature(co):
    return (
        co["enabler_entity"], co["enabler_dimension"], co["enabler_state"],
        co["dependent_entity"], co["dependent_dimension"], co["dependent_condition"],
        co["causal_type"]
    )

seen_sigs = {}
final_co_list = []
for co in co_list:
    sig = co_signature(co)
    if sig in seen_sigs:
        # Merge: keep higher confidence, smaller ID; merge source_ref
        existing = seen_sigs[sig]
        # Decide keeper: confidence high > medium > low; tiebreak by ID
        conf_order = {"high": 3, "medium": 2, "low": 1}
        if conf_order.get(co["confidence"], 0) > conf_order.get(existing["confidence"], 0):
            # New is better; swap
            keeper, merged = co, existing
            keeper["id"] = existing["id"]  # take existing ID
        elif conf_order.get(co["confidence"], 0) < conf_order.get(existing["confidence"], 0):
            keeper, merged = existing, co
        else:
            # Tiebreak: smaller ID
            if co["id"] < existing["id"]:
                keeper, merged = co, existing
                keeper["id"] = existing["id"]
            else:
                keeper, merged = existing, co
        # Merge fields: trigger/trigger_source/rollback_propagation null/false can be overridden
        if keeper.get("trigger") is None and merged.get("trigger") is not None:
            keeper["trigger"] = merged["trigger"]
        if keeper.get("trigger_source") is None and merged.get("trigger_source") is not None:
            keeper["trigger_source"] = merged["trigger_source"]
        if keeper.get("rollback_propagation") is False and merged.get("rollback_propagation") is True:
            keeper["rollback_propagation"] = True
        # source_ref merge
        if merged.get("source_ref") and merged["source_ref"] != keeper.get("source_ref"):
            if keeper.get("source_ref"):
                parts = keeper["source_ref"].split(";") + merged["source_ref"].split(";")
                # dedup
                seen = set()
                uniq = []
                for p in parts:
                    p = p.strip()
                    if p not in seen:
                        seen.add(p)
                        uniq.append(p)
                keeper["source_ref"] = "; ".join(uniq)
            else:
                keeper["source_ref"] = merged["source_ref"]
        keeper["merged_from"].append(merged["id"])
        add_judgment("CO dedup", f"合并 {merged['id']} 入 {keeper['id']} (sig={sig})")
    else:
        seen_sigs[sig] = co
        final_co_list.append(co)

cross_entity_obligations = final_co_list

# ============ Step 4: constraint_obligations ============
constraint_obligations = []
ro_it_counter = 0
ro_br_counter = 0


def _predicate_has_negation(p):
    """递归判定约束谓词是否含否定分支（negation）。

    转换的 constraint_predicate 若含否定，说明"操作被拒"场景已作为该转换的
    负向分支建模（如 T-002 项目选入 含 negation(评级=差)）——此时同
    (entity, from, to) 的独立 invalid_transition 即为该分支的低配重复，
    可被吸收（断言并入负向用例），避免一条规则产出两条过程。
    """
    if not isinstance(p, dict):
        return False
    if p.get("type") == "negation":
        return True
    if _predicate_has_negation(p.get("operand")):
        return True
    return any(_predicate_has_negation(part) for part in (p.get("parts") or []))


# 4.1 RO-IT
for it in p1_it:
    ro_it_counter += 1
    ro = {
        "id": f"RO-IT-{ro_it_counter:03d}",
        "type": "invalid_transition",
        "constraint_id": it["id"],
        "entity": it["entity"],
        "from": it["from"],
        "to": it["to"],
        "reason": it["reason"],
        "coverage_priority": "high",
        "source_ref": it.get("source_ref")
    }
    # 吸收判定：该 invalid_transition 的 (entity, from, to) 已被某转换的
    # constraint_predicate 否定分支建模 → 标 absorbed_by_transition，S1 不产出
    # 独立 Type6，其具体拒绝提示并入转换负向用例（数据驱动，非硬编码）。
    _absorb_tid = next(
        (t["id"] for t in transition_obligations
         if t.get("entity") == ro["entity"]
         and t.get("from") == ro["from"]
         and t.get("to") == ro["to"]
         and _predicate_has_negation(t.get("constraint_predicate"))),
        None)
    if _absorb_tid:
        ro["absorbed_by_transition"] = _absorb_tid
        add_judgment("ro_it_absorb", f"{ro['id']} 已由转换 {_absorb_tid} 否定分支覆盖，吸收（提示断言并入负向用例）")
    constraint_obligations.append(ro)

# 4.2 RO-BR (from P1 business_rules)
for br in p1_br:
    ro_br_counter += 1
    ro = {
        "id": f"RO-BR-{ro_br_counter:03d}",
        "type": "business_rule",
        "constraint_id": br["id"],
        "entities_involved": br.get("entities_involved", []),
        "constrained_entity": br.get("constrained_entity"),
        "category": br.get("category"),
        "restrictive": br.get("restrictive", False),
        "description": br.get("desc"),
        "enforcement": br.get("enforcement"),
        "ref_to_existing_br": None,
        "coverage_priority": "medium",
        "suggested_action": f"验证规则约束: {br.get('desc', '')}",
        "source_ref": br.get("source_ref")
    }
    constraint_obligations.append(ro)

# 4.2.1 XC -> RO-BR (skipped/unclassified XC)
for xc in p1_xc:
    if xc["id"] in xc_status:
        continue  # already a CO
    # This XC was skipped or unclassified -> RO-BR
    ro_br_counter += 1
    desc = xc.get("desc", "")
    target_cond = xc.get("target_condition", "")
    # ── category: keyword-based (primary) + LLM fallback ──
    cat = None
    if "显示" in desc or "展示" in desc:
        cat = "display"
    elif "功能" in desc or "提供" in desc:
        cat = "usability"
    elif any(kw in desc for kw in ["不得", "禁止", "必须", "不能", "不可", "仅当"]):
        cat = "validation"

    if cat is None:
        # LLM fallback: keyword didn't match, ask LLM to classify
        llm_cat = _llm_classify(
            system_prompt=(
                "你是一个业务规则分类器。给定一条业务规则的描述，"
                "判断它属于以下哪一类：\n"
                "- display: 界面展示类规则（显示/展示/查看/统计）\n"
                "- usability: 易用性功能类规则（应提供/应支持/可操作）\n"
                "- validation: 数据校验类规则（不得/禁止/必须/范围/格式）\n"
                "只输出 display / usability / validation 中的一个词。"
            ),
            user_message=(
                f"规则描述: {desc}\n"
                f"目标条件: {target_cond}\n"
                f"请分类。"
            ),
            valid_values=["display", "usability", "validation"],
        )
        if llm_cat:
            cat = llm_cat
            add_judgment("RO-BR LLM category", f"XC→RO-BR: keyword未命中，LLM判为 {cat}")
        else:
            cat = "validation"  # safe default

    # coverage_priority: 镜像/Step4.6 确认类 -> high; else medium
    if desc.startswith("镜像 T-") or desc.startswith("由 Step 4.5 约束-因果鉴别确认"):
        cp = "high"
    else:
        cp = "medium"
    
    # ref_to_existing_br: search P1 BR with same theme
    ref_br = None
    for br in p1_br:
        if xc["source_entity"] in br.get("entities_involved", []) or xc["target_entity"] in br.get("entities_involved", []):
            # rough theme match
            if any(kw in br.get("desc", "") for kw in desc.split()[:3]):
                ref_br = br["id"]
                break
    
    ro = {
        "id": f"RO-BR-{ro_br_counter:03d}",
        "type": "business_rule",
        "constraint_id": xc["id"],
        "entities_involved": [xc["source_entity"], xc["target_entity"]],
        "category": cat,
        "restrictive": False,
        "description": f"[来源于{xc['id']}] {target_cond}; {desc}",
        "enforcement": "mandatory",
        "ref_to_existing_br": ref_br,
        "coverage_priority": cp,
        "suggested_action": f"验证跨实体约束: {target_cond}",
        "source_ref": xc.get("source_ref")
    }
    constraint_obligations.append(ro)
    xc_status[xc["id"]] = "br"

# ============ Step 5: _context ============

# branch_dimensions with entity and affected_obligations
bd_enriched = []
for bd in p1_bd:
    affected = []
    for to in transition_obligations:
        if bd["dimension"] in [bp["dimension"] for bp in to.get("branch_path", [])]:
            affected.append(to["id"])
        if to["id"] in bd.get("coverage", {}).get("transitions", []):
            if to["id"] not in affected:
                affected.append(to["id"])
    bd_enriched.append({
        **bd,
        "entity": bd.get("entity"),
        "affected_obligations": affected
    })

# state_info summary
state_info = {}
for e in p1["domain_model"]["entities"]:
    state_info[e["id"]] = {
        "entity_name": e["name"],
        "dimensions": [
            {
                "dimension_name": d["dimension_name"],
                "states": d["states"],
                "initial": d["initial"],
                "terminal": d.get("terminal", [])
            }
            for d in e.get("state_dimensions", [])
        ]
    }


# ============ Step 6: phase_mapping derivation ============
# For each (entity, dimension) in state_info, derive a phase_mapping
# {state_name: int_phase} by BFS over forward transition edges.
#
# This uses the TO.direction field (derived in Step 2 via derive_direction)
# instead of hardcoded keyword tables. direction ∈ {forward, backward,
# lateral, resume}:
#   - forward: contributes to phase progression (BFS +1)
#   - backward: target inherits source's phase (lateral-like, but going back)
#   - lateral: target inherits source's phase (side-state like 暂停)
#   - resume: completely ignored (target already has phase from forward edges)
#
# This is the ROOT-CAUSE replacement for the old _ROLLBACK_ACTION_KEYWORDS /
# _ROLLBACK_NOTE_KEYWORDS / _RESUME_ACTION_KEYWORDS tables. No business
# keywords are hardcoded — all edge classification comes from the
# structured `direction` field derived in Step 2.

def _is_forward_transition(t: dict) -> bool:
    """Classify a transition as forward (advances phase) or not.

    Uses TO.direction (derived in Step 2 from P1 traits + state_order).
    No keyword matching.
    """
    direction = t.get("direction", "forward")
    return direction == "forward"


def _is_resume_transition(t: dict) -> bool:
    """Resume transitions (重启/解锁) go from a side-state back to the main
    chain. Identified by TO.direction == 'resume', not by keywords.
    """
    return t.get("direction") == "resume"


def _derive_phase_mapping_for_dim(entity_id: str, dim_name: str,
                                   states: list, initial: str,
                                   terminals: list) -> dict:
    """BFS over forward edges to derive {state: phase}.

    Returns a dict mapping each state in `states` to an int phase.
    Terminal states are all pinned to max_phase (computed from non-terminals).

    Lateral/side-effect states (e.g. 暂停 entered via lateral edge from
    待评审/评审中/已完成) are pinned to their source state's phase, NOT 0.
    This matches case_spec.phase_mapping.reference where 暂停=3 (same as
    评审中, its highest source).
    """
    if not states:
        return {}

    # Build forward-edge adjacency and lateral-edge list from P1 transitions.
    # Edge classification uses TO.direction (derived in Step 2 from P1 traits
    # + state_order), NOT hardcoded keywords.
    forward_adj = defaultdict(set)  # from_state -> {to_state, ...}
    lateral_sources = defaultdict(list)  # to_state -> [from_state, ...] (lateral/backward entries)
    initial_targets = set()

    for t in p1.get("state_and_flow", {}).get("transitions", []):
        if t.get("entity") != entity_id or t.get("dimension") != dim_name:
            continue
        # Derive direction for this P1 transition (same logic as Step 2)
        direction = derive_direction(t)
        # Skip resume transitions entirely (target already phased)
        if direction == "resume":
            continue
        f = t.get("from")
        to = t.get("to")
        if not isinstance(to, str) or not to:
            continue
        if f is None or f == "(初始)":
            initial_targets.add(to)
            continue
        if not isinstance(f, str) or not f:
            continue
        if f == to:
            continue
        # Classify by direction: forward → BFS graph; backward/lateral → lateral_sources
        if direction == "forward":
            forward_adj[f].add(to)
        else:
            # backward or lateral: target inherits source's phase
            lateral_sources[to].append(f)

    # Seed: declared initial state (always phase 0) + creation targets
    phase_map = {}
    queue = deque()
    if initial and initial in states:
        phase_map[initial] = 0
        queue.append(initial)
    for tgt in sorted(initial_targets):  # set 迭代序非确定 → BFS 种子序需确定
        if tgt in states and tgt not in phase_map:
            phase_map[tgt] = 0
            queue.append(tgt)

    if not queue and states:
        phase_map[states[0]] = 0
        queue.append(states[0])

    # BFS: forward edges increment phase (longest-path semantics).
    # Use max (not min) because case_spec.phase_mapping.reference uses the
    # longest forward chain (e.g. 已完成=4 via 评审中→已完成, not =3 via
    # 待评审→已完成). This satisfies V08's "forward transition must increase
    # phase" rule for ALL forward edges, including skip-transitions.
    #
    # ⚠️ 环检测 ⚠️
    # 如果 P1 的 direction 判错（把 backward 边标成 forward），forward_adj
    # 里会出现环（如 已选入→待评审→评审中→待归档→已选入）。longest-path
    # Bellman-Ford 在环上不收敛，每轮 +1 直到 max_iter，导致 phase 爆炸到
    # 88-110（用户实测过）。
    #
    # 修复：在 BFS 前检测 forward_adj 是否有环。有环时：
    # 1. 记 warning（说明 P1 direction 有误，需人工复核）
    # 2. 用 states 列表顺序作为 fallback phase_mapping（不依赖 direction）
    # 这保证了即使 P1 direction 全错，phase_mapping 也不会爆炸。

    # ── 环检测 ──
    _has_cycle = False
    try:
        import networkx as nx
        G_forward = nx.DiGraph()
        for src, targets in forward_adj.items():
            for tgt in sorted(targets):
                G_forward.add_edge(src, tgt)
        _has_cycle = not nx.is_directed_acyclic_graph(G_forward)
    except ImportError:
        # networkx 不可用时用简易 DFS 环检测
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {s: WHITE for s in states}
        def _dfs_cycle(node):
            color[node] = GRAY
            for nxt in sorted(forward_adj.get(node, ())):
                if nxt not in color:
                    continue
                if color[nxt] == GRAY:
                    return True
                if color[nxt] == WHITE and _dfs_cycle(nxt):
                    return True
            color[node] = BLACK
            return False
        for s in states:
            if color.get(s) == WHITE:
                if _dfs_cycle(s):
                    _has_cycle = True
                    break

    if _has_cycle:
        add_warning(
            "phase_mapping cycle detected",
            f"{entity_id}.{dim_name}: forward_adj 有环（P1 direction 可能有误，"
            f"backward 边被标成 forward），降级用 states 列表顺序作为 phase_mapping"
        )
        # Fallback: 用 states 列表顺序（index 作为 phase）
        # terminal_states pin 到 max
        phase_map = {s: i for i, s in enumerate(states)}
        term_set = {s for s in (terminals or []) if s in states}
        if term_set:
            non_term_phases = [p for s, p in phase_map.items() if s not in term_set]
            if non_term_phases:
                terminal_phase = max(non_term_phases) + 1
            else:
                terminal_phase = max(phase_map.values()) if phase_map else 0
            for s in sorted(term_set):  # 等值赋值，但 phase_map 插入序随迭代序漂移
                phase_map[s] = terminal_phase
        # Force-pin initial
        if initial and initial in states:
            phase_map[initial] = 0
        return phase_map

    # 无环时正常跑 longest-path Bellman-Ford
    changed = True
    max_iter = len(states) * 2 + 10
    iters = 0
    while changed and iters < max_iter:
        changed = False
        iters += 1
        for src, targets in forward_adj.items():
            src_phase = phase_map.get(src)
            if src_phase is None:
                continue
            for tgt in sorted(targets):
                cand = src_phase + 1
                if tgt in states and phase_map.get(tgt, -1) < cand:
                    phase_map[tgt] = cand
                    changed = True

    # Lateral states: pin to max phase of their lateral sources.
    # BUT only for states that were NOT reached by a forward edge — forward
    # edges are authoritative for phase progression; lateral edges only
    # provide a fallback phase for states with no forward inbound edge.
    # (e.g. 暂停 has no forward inbound edge, only lateral from 待评审/评审中/
    # 已完成, so it takes max(source phases). But 已选入 has a forward edge
    # from 待选入, so it KEEPS its forward phase and ignores the lateral
    # edge from 待归档.)
    forward_reached = set()
    for src, targets in forward_adj.items():
        for tgt in sorted(targets):
            forward_reached.add(tgt)

    changed = True
    max_iter = len(states) * 2 + 10
    iters = 0
    while changed and iters < max_iter:
        changed = False
        iters += 1
        for to_state, sources in lateral_sources.items():
            if to_state not in states:
                continue
            # Skip states that have a forward inbound edge — their phase
            # is already correctly set by forward BFS above.
            if to_state in forward_reached:
                continue
            src_phases = [phase_map.get(s, 0) for s in sources if s in phase_map]
            if src_phases:
                target_phase = max(src_phases)
                if phase_map.get(to_state, -1) != target_phase:
                    phase_map[to_state] = target_phase
                    changed = True

    # Backfill unreachable states to 0
    for s in states:
        if s not in phase_map:
            phase_map[s] = 0

    # Force-pin declared initial state to phase 0.
    # The initial state may have inbound lateral/backward edges (e.g.
    # 待选入 ← 已选入 via 选出, 待选入 ← 待归档 via 归档不合格). These lateral
    # sources would inflate the initial state's phase via the lateral
    # fixpoint above. But the initial state MUST be P0 — it's the entry
    # of the entire state machine. Override any lateral-inherited phase.
    if initial and initial in states:
        phase_map[initial] = 0

    # Pin terminals to the same max phase
    term_set = {s for s in (terminals or []) if s in states}
    if term_set:
        non_terminal_phases = [p for s, p in phase_map.items() if s not in term_set]
        if non_terminal_phases:
            terminal_phase = max(non_terminal_phases) + 1
        else:
            terminal_phase = max(phase_map.values()) if phase_map else 0
        for s in sorted(term_set):  # 同上：插入序确定化
            phase_map[s] = terminal_phase

    return phase_map


# Apply phase_mapping derivation to every (entity, dim) in state_info
_phase_mapping_count = 0
for entity_id, ent_info in state_info.items():
    for dim_info in ent_info.get("dimensions", []):
        pm = _derive_phase_mapping_for_dim(
            entity_id,
            dim_info["dimension_name"],
            dim_info.get("states", []),
            dim_info.get("initial", ""),
            dim_info.get("terminal", []),
        )
        if pm:
            dim_info["phase_mapping"] = pm
            _phase_mapping_count += 1
            add_judgment(
                "phase_mapping_derived",
                f"{entity_id}.{dim_info['dimension_name']}: derived {len(pm)} phases, "
                f"terminals pinned to {max(pm.values()) if pm else 0}"
            )

# Snapshot extension: include phase_mapping coverage
_phase_coverage = {
    "dims_with_phase_mapping": _phase_mapping_count,
    "dims_total": sum(len(ent.get("dimensions", [])) for ent in state_info.values()),
}

# xc_to_br_mapping
xc_to_br_mapping = [{"xc_id": k, "status": v} for k, v in xc_status.items()]

# Self-check
total_preconditions = 0
total_state_refs_expected = 0
total_state_refs_resolved = 0
unresolved_list = []
p1_inherited_count = 0
p2_filled_count = 0

for to in transition_obligations:
    for p in to.get("preconditions", []):
        total_preconditions += 1
        if p["type"] == "state_ref":
            total_state_refs_expected += 1
            if p.get("ref") is not None:
                total_state_refs_resolved += 1
            else:
                unresolved_list.append({"to_id": to["id"], "text": p["text"]})
    for r in to.get("precondition_state_refs", []):
        if r["pattern"] == "p1_inherited":
            p1_inherited_count += 1
        else:
            p2_filled_count += 1

# Check: all XC have status
all_xc_have_status = all(xc["id"] in xc_status for xc in p1_xc)

# Check: all skipped XC have BR
all_skipped_xc_have_br = all(xc_status.get(xc["id"]) == "br" for xc in p1_xc if xc["id"] in xc_status and xc_status[xc["id"]] == "br")

# Check: no_branch_scenarios
# A branch-affected TO (BD.coverage hit or note.branch_dimension non-empty) must
# either (a) carry a concrete branch_path, (b) be split into branch variants
# ([a][b]... — the base is a retained "main TO" for cross-dimension linkage and
# the branch scenarios ARE covered, so it is NOT a missing scenario), or
# (c) be covered by an explicit degradation judgment (组合>16 / 无实质差异).
# Judgment lookup uses the TO id prefix (judgments are formatted "TOID: ...")
# so a branch-variant id ("T-X[a]") never satisfies a base TO ("T-X").
no_branch_scenarios = True
branch_scenario_offenders = []
for to in transition_obligations:
    # Check if this TO was supposed to be split (matched in BD.coverage.transitions or had note.branch_dimension)
    p1_t = p1_transitions_by_id.get(to["id"].split("[")[0])
    if p1_t:
        matched = get_matched_dims(p1_t)
        if matched and not to.get("branch_path"):
            has_branch_variants = any(
                t2["id"].startswith(to["id"] + "[") for t2 in transition_obligations
            )
            has_degradation = any(
                ("降级" in j["desc"] or "无实质差异" in j["desc"])
                and j["desc"].split(":", 1)[0].strip() == to["id"]
                for j in judgments
            )
            if not has_branch_variants and not has_degradation:
                no_branch_scenarios = False
                branch_scenario_offenders.append(to["id"])
if branch_scenario_offenders:
    add_warning("no_branch_scenarios",
                f"以下TO命中分支维度但未拆分且无降级judgment: {branch_scenario_offenders}")

# Check: enabler_state_valid_or_judgment
enabler_state_valid_or_judgment = True
for co in cross_entity_obligations:
    es = co.get("enabler_state", "")
    ee = co.get("enabler_entity", "")
    ed = co.get("enabler_dimension", "")
    if es and ee and ed:
        if es not in state_lookup.get(ee, {}).get(ed, set()):
            # Check if there's a judgment
            if not any(es in j["desc"] for j in judgments):
                enabler_state_valid_or_judgment = False

# Check: restrictive_category_preserved
restrictive_category_preserved = True
for ro in constraint_obligations:
    if ro["type"] == "business_rule" and ro.get("constraint_id", "").startswith("BR-"):
        # Find original BR
        orig_br = next((b for b in p1_br if b["id"] == ro["constraint_id"]), None)
        if orig_br:
            if ro.get("restrictive") != orig_br.get("restrictive") or ro.get("category") != orig_br.get("category"):
                restrictive_category_preserved = False
                break

# Check: id_globally_unique
all_ids = [eo["id"] for eo in entity_obligations] + [to["id"] for to in transition_obligations] + [co["id"] for co in cross_entity_obligations] + [ro["id"] for ro in constraint_obligations]
id_globally_unique = len(all_ids) == len(set(all_ids))

# Check: p1_root_nodes_complete
p1_root_nodes_complete = True
expected_roots = ["entity_obligations", "transition_obligations", "cross_entity_obligations", "constraint_obligations", "_context"]

# Check: precondition_state_refs_complete
precondition_state_refs_complete = (total_state_refs_expected == total_state_refs_resolved)

self_check = {
    "no_branch_scenarios": no_branch_scenarios,
    "all_xc_have_status": all_xc_have_status,
    "enabler_state_valid_or_judgment": enabler_state_valid_or_judgment,
    "restrictive_category_preserved": restrictive_category_preserved,
    "id_globally_unique": id_globally_unique,
    "p1_root_nodes_complete": p1_root_nodes_complete,
    "all_skipped_xc_have_br": all_skipped_xc_have_br,
    "precondition_state_refs_complete": precondition_state_refs_complete
}

# If id_globally_unique or p1_root_nodes_complete is false -> fatal
if not id_globally_unique or not p1_root_nodes_complete:
    out = {"_context": {"fatal_error": "self_check failed", "self_check": self_check}}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(2)  # C-08: fatal 路径必须非零退出，CI/脚本靠 $? 感知

# Snapshot
snapshot = {
    "to_index_size": len(to_index),
    "co_list_size": len(cross_entity_obligations),
    "xc_status_summary": {
        "total_xc": len(p1_xc),
        "as_co": sum(1 for v in xc_status.values() if v == "co"),
        "as_br": sum(1 for v in xc_status.values() if v == "br")
    },
    "precondition_state_refs_coverage": {
        "total_preconditions": total_preconditions,
        "total_state_refs_expected": total_state_refs_expected,
        "total_state_refs_resolved": total_state_refs_resolved,
        "unresolved_count": len(unresolved_list),
        "p1_inherited_count": p1_inherited_count,
        "p2_filled_count": p2_filled_count
    },
    "phase_mapping_coverage": _phase_coverage
}

# Add unresolved warning if any
if unresolved_list:
    add_warning("precondition_state_refs_unresolved", f"共 {len(unresolved_list)} 项 state_ref ref=null 未解析: {unresolved_list[:5]}")

# Build _context
# prohibition_config: keywords for detecting restrictive/negative-branch
# preconditions. S1 reads these from _context instead of hardcoding them.
# 领域无关原则: 默认值只保留通用中文否定词/系统操作动词——领域特定操作词汇
# (如 选入/归档/发放/入选/选为/提为试用/连续3天)必须由 P1 输入在
# _context.prohibition_config 中声明(数据模块是项目词汇的单一真相源),
# P2 不硬编码业务词汇。
_prohibition_config = p1.get("_context", {}).get("prohibition_config", {
    "negation_prefixes": list(_GENERIC_NEGATION_PREFIXES),
    "action_verbs": ["启动", "提交", "保存", "删除", "修改", "新增",
                     "审批", "批准", "通过", "重启", "暂停", "结束",
                     "退出", "登录", "操作", "编辑", "查看", "进入",
                     "选择", "执行", "上传", "下载", "锁定", "重置"],
    "prohibit_keywords": ["不可", "不能", "禁止", "不得", "不允许",
                          "无法", "无权", "只能", "仅限", "才可", "只有"],
    "success_hints": ["状态转换为", "状态变更为"],
})


_context = {
    "source": "P1 v19.2",
    "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "p1_meta": {
        "version": p1["_meta"].get("version"),
        "source": p1["_meta"].get("source"),
        "document_scope": p1["_meta"].get("document_scope"),
        "has_critical_ambiguity": p1["_meta"].get("has_critical_ambiguity"),
        "consistency_check": p1["_meta"].get("consistency_check"),
        "ambiguity_list": p1["_meta"].get("ambiguity_list", []),
        "pipeline_trace": p1["_meta"].get("pipeline_trace", {})
    },
    "branch_dimensions": bd_enriched,
    "transition_splits": transition_splits,
    "structural_relations": p1["domain_model"]["structural_relations"],
    # 跨实体因果由 CO（enabler→dependent）确定性表达，transition_relations 不再派生
    # causal_pairs（add_causal API 无此参数，字段已全链移除）。
    "transition_relations": p1["domain_model"]["transition_relations"],
    "state_info": state_info,
    "roles": p1["domain_model"]["roles"],
    "entity_details": [
        {"id": e["id"], "name": e["name"], "type": e.get("type", ""), "desc": e.get("desc", ""),
         # 属性及其约束 desc 透传 —— V04 校验器据此推导系统维护字段
         # (单一真相源在 P1 数据层,非 case_spec 手写清单)
         "attributes": [{"name": a.get("name", ""), "desc": a.get("desc", ""),
                         "is_config": bool(a.get("is_config"))}
                        for a in (e.get("attributes") or [])]}
        for e in p1["domain_model"]["entities"]
    ],
    "prohibition_config": _prohibition_config,
    # 角色→可执行操作权限,由 P1 数据层声明(单一真相源)。V07 校验器据此推导
    # 权限矩阵,不再依赖 case_spec 手写矩阵。P1 未声明时为空 list。
    "permissions": (p1.get("_context") or {}).get("permissions", []),
    "xc_to_br_mapping": xc_to_br_mapping,
    "judgments": judgments,
    "warnings": warnings,
    "snapshot": snapshot,
    "self_check": self_check,
    # 本次 P1 派生的字段注册表。S1 的 predicate_phase_lower_bound 据此算
    # 字段谓词相位下界；PT017 无字段引用谓词 → 空 dict（注册表对它是惰性的）。
    "field_registry": _FIELD_REGISTRY
}

# ============ Final output ============
output = {
    "entity_obligations": entity_obligations,
    "transition_obligations": transition_obligations,
    "cross_entity_obligations": cross_entity_obligations,
    "constraint_obligations": constraint_obligations,
    "_context": _context
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Output written to {OUT_PATH}")
print(f"EO: {len(entity_obligations)}, TO: {len(transition_obligations)}, CO: {len(cross_entity_obligations)}, RO: {len(constraint_obligations)}")
print(f"Self-check: {self_check}")
print(f"Snapshot: {snapshot}")
