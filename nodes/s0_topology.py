"""S0 Topology Discovery Node.

Reads existing S0 engine_state from the V2 output file, or discovers it via LLM.
"""
from __future__ import annotations
import json
import os
from typing import Any
from models.state import AgentState

# Constants matching V2 engine
ENTITY_NAME_MAP = {
    '验证项目': 'E-PRJ', '报名记录': 'E-REG', '实验室': 'E-LAB',
    '物品核验单': 'E-VRF', '付款记录': 'E-PAY', '评价': 'E-EVAL',
    '审批流程': 'E-APPR', '归档': 'E-ARCHIVE', '标准库': 'E-STD',
    '测试项': 'E-TEST', '子领域': 'E-CATE', '产品类型': 'E-PTYPE',
    '测试物品': 'E-ITEM', '通知公告': 'E-ANNOUNCE', '常见问题': 'E-FAQ',
    '信息发送记录': 'E-MSG'
}

ROLE_MAP = {
    'R-01': '技术主管', 'R-02': '实验室负责人', 'R-03': '授权签字人',
    'R-04': '策划人员', 'R-05': '项目管理员', 'R-06': '样品制备人员',
    'R-07': '样品管理员', 'R-08': '评价人员', 'R-09': '统计人员',
    'R-10': '质量专员', 'R-11': '财务管理人员', 'R-12': '系统管理人员',
    'R-13': '能力验证参加者', 'R-14': '印章管理员', 'R-15': '监督员',
    'system': '系统'
}

TYPE_PRIORITY_MAP = {
    'happy': 1, 'branch': 2, 'constraint': 3, 'audit': 4,
    'crud': 5, 'rule': 6, 'lifecycle': 7, 'cross': 8, 'invalid': 9,
    'data_constraint': 3, 'time_sensitive': 3, 'rollback': 4,
    'negative': 9, 'audit_rejection': 4
}

TYPE5_SPECIAL_OPS = {'删除', '审核', '状态变更', '撤销', '退回', '退款', '发布'}
L0_L1_L5_ENTITIES = {'E-LAB', 'E-STD', 'E-TEST', 'E-CATE', 'E-PTYPE', 'E-ITEM', 'E-ANNOUNCE', 'E-FAQ', 'E-MSG'}


def _load_existing_s0(s0_path: str) -> dict | None:
    """Try to load existing S0 engine_state from V2 output."""
    if not os.path.exists(s0_path):
        return None
    try:
        with open(s0_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # V2 output wraps engine_state
        if 'engine_state' in data:
            return data['engine_state']
        # Might be standalone engine_state
        if 'primary_entity' in data:
            return data
    except Exception:
        pass
    return None


def s0_topology_node(state: AgentState) -> dict:
    """S0 Topology Discovery node.
    
    Strategy:
    1. First try to load existing S0 from V2 output file (deterministic, reliable)
    2. If not found, try LLM-based discovery
    3. Validate the result with schema
    """
    warnings = list(state.get("warnings", []))
    errors = list(state.get("errors", []))
    
    # Load coverage model
    cm_path = state.get("coverage_model_path", "/home/z/my-project/download/coverage_model.json")
    with open(cm_path, 'r', encoding='utf-8') as f:
        cm_data = json.load(f)
    coverage_model = cm_data.get('coverage_model', cm_data)
    
    # Try loading existing S0 from V2 output
    s0_path = "/home/z/my-project/download/p3_s2_s3_s4_result.json"
    engine_state = _load_existing_s0(s0_path)
    
    if engine_state is None:
        # Try LLM-based discovery
        warnings.append("No existing S0 state found, attempting LLM discovery")
        try:
            from tools.llm_client import LLMClient
            from prompts.s0_prompt import S0_SYSTEM_PROMPT, S0_USER_PROMPT_TEMPLATE
            import asyncio
            
            client = LLMClient()
            user_msg = S0_USER_PROMPT_TEMPLATE.format(
                coverage_model_json=json.dumps(coverage_model, ensure_ascii=False, indent=2)
            )
            engine_state = asyncio.run(client.chat_json(S0_SYSTEM_PROMPT, user_msg))
        except Exception as e:
            errors.append(f"S0 LLM discovery failed: {e}")
            return {"errors": errors, "current_stage": "s0_failed"}
    
    # Validate
    try:
        from models.schema import validate_engine_state
        validated = validate_engine_state(engine_state)
        warnings.append(f"S0 validated: primary_entity={validated.primary_entity}, phases={validated.phase_table.phase_count}")
    except Exception as e:
        warnings.append(f"S0 validation warning: {e}")
    
    return {
        "primary_entity": engine_state.get("primary_entity"),
        "phase_table": engine_state.get("phase_table"),
        "dep_state_phase_map": engine_state.get("dep_state_phase_map", {}),
        "contextual_phase_rules": engine_state.get("contextual_phase_rules", {}),
        "state_type_map": engine_state.get("state_type_map", {}),
        "dependent_entities": engine_state.get("dependent_entities", []),
        "entity_parent": engine_state.get("entity_parent", {}),
        "dependency_depth": engine_state.get("dependency_depth", {}),
        "topology_levels": engine_state.get("topology_levels", {}),
        "virtual_entities": engine_state.get("virtual_entities", {}),
        "transition_upstream_map": engine_state.get("transition_upstream_map", {}),
        "coverage_model": coverage_model,
        "warnings": warnings,
        "errors": errors,
        "current_stage": "s0",
    }
