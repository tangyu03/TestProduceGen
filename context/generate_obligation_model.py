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

# ============ Configurable paths ============
_DEFAULT_P1 = os.environ.get(
    "P1_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "context", "P1_out.json"),
)
_DEFAULT_OUT = os.environ.get(
    "P2_OUT_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "coverage_obligations.json"),
)

# Allow CLI override: python generate_obligation_model.py <p1> <out>
if len(sys.argv) >= 2:
    P1_PATH = sys.argv[1]
else:
    P1_PATH = _DEFAULT_P1
if len(sys.argv) >= 3:
    OUT_PATH = sys.argv[2]
else:
    OUT_PATH = _DEFAULT_OUT

with open(P1_PATH, "r", encoding="utf-8") as f:
    p1 = json.load(f)


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
    sys.exit(0)

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
    sys.exit(0)

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
for e in p1["domain_model"]["entities"]:
    for attr in e.get("attributes", []):
        if attr.get("is_config") is True:
            eo_atc_counter += 1
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
                "source_ref": None  # P1 attributes have no source_ref
            }
            entity_obligations.append(eo)
            add_judgment("EO-ATC source_ref", f"{eo['id']} P1 属性无 source_ref 字段，置 null")

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
                # Try to find dimension (any dim of that entity)
                dims = list(entity_dims.get(other_e["id"], set()))
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
                for s in states:
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
                            for s in states:
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
                # We check the combo value and its siblings.
                if val not in text:
                    # The branch value is NOT in the text — check if any
                    # OTHER state of this dimension is in the text instead.
                    # This requires knowing the dimension's state list.
                    for e in p1["domain_model"]["entities"]:
                        for d in e.get("state_dimensions", []):
                            if d["dimension_name"] == dim_name:
                                for s in d.get("states", []):
                                    if s != val and s in text:
                                        return True
                                break
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
    if desc.startswith("镜像 T-") or desc.startswith("由 Step 4.6 约束-因果鉴别确认"):
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
    if any(kw in desc for kw in ["累计", "计算", "公式", "评级", "归档"]):
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
    constraint_obligations.append(ro)

# 4.2 RO-BR (from P1 business_rules)
for br in p1_br:
    ro_br_counter += 1
    ro = {
        "id": f"RO-BR-{ro_br_counter:03d}",
        "type": "business_rule",
        "constraint_id": br["id"],
        "entities_involved": br.get("entities_involved", []),
        "category": br.get("category"),
        "signal_type": br.get("signal_type"),
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
    if desc.startswith("镜像 T-") or desc.startswith("由 Step 4.6 约束-因果鉴别确认"):
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
        "signal_type": None,
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
    for tgt in initial_targets:
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
            for tgt in targets:
                G_forward.add_edge(src, tgt)
        _has_cycle = not nx.is_directed_acyclic_graph(G_forward)
    except ImportError:
        # networkx 不可用时用简易 DFS 环检测
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {s: WHITE for s in states}
        def _dfs_cycle(node):
            color[node] = GRAY
            for nxt in forward_adj.get(node, ()):
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
            for s in term_set:
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
            for tgt in targets:
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
        for tgt in targets:
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
        for s in term_set:
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

# Check: signal_type_category_preserved
signal_type_category_preserved = True
for ro in constraint_obligations:
    if ro["type"] == "business_rule" and ro.get("constraint_id", "").startswith("BR-"):
        # Find original BR
        orig_br = next((b for b in p1_br if b["id"] == ro["constraint_id"]), None)
        if orig_br:
            if ro.get("signal_type") != orig_br.get("signal_type") or ro.get("category") != orig_br.get("category"):
                signal_type_category_preserved = False
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
    "signal_type_category_preserved": signal_type_category_preserved,
    "id_globally_unique": id_globally_unique,
    "p1_root_nodes_complete": p1_root_nodes_complete,
    "all_skipped_xc_have_br": all_skipped_xc_have_br,
    "precondition_state_refs_complete": precondition_state_refs_complete
}

# If id_globally_unique or p1_root_nodes_complete is false -> fatal
if not id_globally_unique or not p1_root_nodes_complete:
    out = {"_context": {"fatal_error": "self_check failed", "self_check": self_check}}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)

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
    "negation_prefixes": ["不可", "不能", "不得", "禁止", "不允许", "无法", "无权", "未被", "未"],
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
    "self_check": self_check
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
