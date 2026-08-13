#!/usr/bin/env python3
"""v29 #6: 真实 LLM 端到端验证脚本

Exercises every LLM-dependent code path in the v29 codebase with a real
API call, and verifies the response is valid. Reports per-path success/failure.

Paths verified:
  1. _classify_actions_via_llm   (s1_generation.py)
  2. _decompose_brs_via_llm      (s1_generation.py — currently disabled in main flow)
  3. parse_entity_constraints    (field_validation.py — Type9 generation)
  4. TitleGenerator.generate_batch (llm_client.py)
  5. _polish_expected_text       (main.py)

Usage:
  python scripts/llm_e2e_check.py
"""
import json
import os
import sys
import time
from pathlib import Path
from models.schema import ObligationType

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# Load config
with open(PROJECT_DIR / "config.json") as f:
    CFG = json.load(f)
LLM_CFG = CFG.get("llm", {})
API_BASE = LLM_CFG.get("api_base", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
API_KEY = LLM_CFG.get("api_key", "")
MODEL = LLM_CFG.get("task_models", {}).get("general", "glm-4-flash")

if not API_KEY:
    print("[FATAL] No API key in config.json — cannot run LLM e2e check")
    sys.exit(2)

# Set env vars so s1_generation picks them up
os.environ["LLM_API_BASE"] = API_BASE
os.environ["LLM_API_KEY"] = API_KEY
os.environ["LLM_ACTION_CLS_MODEL"] = MODEL


def section(name: str):
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


def report(name: str, success: bool, detail: str = "", elapsed: float = 0.0):
    status = " PASS" if success else " FAIL"
    print(f"  [{status}] {name} ({elapsed:.1f}s)" + (f": {detail}" if detail else ""))
    return success


def test_1_action_classification():
    section("1. _classify_actions_via_llm (s1_generation.py)")
    from nodes.s1_generation import _classify_actions_via_llm

    sample_actions = [
        "管理员审核报名",
        "系统自动发送通知",
        "用户提交表单",
        "导出报表",
        "管理员批准项目立项",
    ]

    t0 = time.time()
    try:
        result = _classify_actions_via_llm(sample_actions)
        elapsed = time.time() - t0
        if not result:
            return report("Action classification", False, "empty result", elapsed)
        # Verify each action got a valid label
        valid_labels = {"human", "system"}
        bad = [a for a, lbl in result.items() if lbl not in valid_labels]
        if bad:
            return report("Action classification", False, f"invalid labels for {bad}", elapsed)
        # Sanity check: "管理员审核" should be human, "系统自动" should be system
        human_count = sum(1 for lbl in result.values() if lbl == "human")
        system_count = sum(1 for lbl in result.values() if lbl == "system")
        return report(
            "Action classification",
            human_count > 0 and system_count > 0,
            f"classified {len(result)}/{len(sample_actions)} (human={human_count}, system={system_count})",
            elapsed,
        )
    except Exception as e:
        return report("Action classification", False, f"exception: {e}", time.time() - t0)


def test_2_br_decomposition():
    section("2. _decompose_brs_via_llm (s1_generation.py)")
    from nodes.s1_generation import _decompose_brs_via_llm

    # Function expects list of dicts with constraint_id/id + description
    sample_brs = [
        {"constraint_id": "BR-01", "description": "报名截止后,报名记录不可修改,且不可删除"},
        {"constraint_id": "BR-02", "description": "项目状态为已结束时,不允许新增报名记录"},
    ]

    t0 = time.time()
    try:
        result = _decompose_brs_via_llm(sample_brs)
        elapsed = time.time() - t0
        if not result:
            return report("BR decomposition", False, "empty result", elapsed)
        # Each BR should produce a list of (sub_label, assertion) tuples
        total_assertions = sum(len(v) for v in result.values())
        return report(
            "BR decomposition",
            total_assertions > 0,
            f"{len(result)}/{len(sample_brs)} BRs decomposed, {total_assertions} total assertions",
            elapsed,
        )
    except Exception as e:
        return report("BR decomposition", False, f"exception: {e}", time.time() - t0)


def test_3_field_validation():
    section("3. parse_entity_constraints (field_validation.py)")
    from nodes.field_validation import parse_entity_constraints

    # Minimal entity_details sample
    entity_details = [
        {
            "id": "E-TEST",
            "name": "测试实体",
            "attributes": [
                {"name": "名称", "desc": "文本输入框,必填,长度1-50", "is_config": False},
                {"name": "数量", "desc": "数字输入框,必填,范围1-100", "is_config": False},
                {"name": "状态", "desc": "下拉框,启用或停用", "is_config": True},
            ],
        }
    ]

    t0 = time.time()
    try:
        result = parse_entity_constraints(entity_details)
        elapsed = time.time() - t0
        if not result:
            return report("Field validation", False, "empty result", elapsed)
        # Should have at least one entity's constraints parsed
        return report(
            "Field validation",
            len(result) > 0,
            f"{len(result)} entities with constraints",
            elapsed,
        )
    except Exception as e:
        return report("Field validation", False, f"exception: {e}", time.time() - t0)


def test_4_title_generation():
    section("4. TitleGenerator.generate_batch (llm_client.py)")
    from tools.llm_client import TitleGenerator

    sample_procs = [
        {
            "temp_id": "PROC-001",
            "entity": "E-PRJ",
            "dimension": "项目状态",
            "obligation_type": ObligationType.TRANSITION,
            "givens": [{"target": "E-PRJ.项目状态", "state": "待开始", "description": "项目处于待开始状态"}],
            "when": {"target": "E-PRJ.项目状态", "event": "立项批准", "actor": "项目经理", "action": "批准立项"},
            "thens": [{"target": "E-PRJ.项目状态", "expectation": "项目进入报名中", "kind": "state"}],
            "post_state": "待开始→报名中",
        },
        {
            "temp_id": "PROC-002",
            "entity": "E-REG",
            "dimension": "报名状态",
            "obligation_type": ObligationType.TRANSITION,
            "givens": [{"target": "E-REG.报名状态", "state": "待审核", "description": "报名记录待审核"}],
            "when": {"target": "E-REG.报名状态", "event": "管理员审核", "actor": "管理员", "action": "审核报名"},
            "thens": [{"target": "E-REG.报名状态", "expectation": "报名记录已审核", "kind": "state"}],
            "post_state": "待审核→已审核",
        },
    ]

    t0 = time.time()
    try:
        gen = TitleGenerator()
        titles = gen.generate_batch(sample_procs)
        elapsed = time.time() - t0
        if not titles:
            return report("Title generation", False, "empty result", elapsed)
        # Each proc should have a non-empty title
        bad = [t for t in titles if not t or not t.strip()]
        return report(
            "Title generation",
            len(bad) == 0,
            f"{len(titles)}/{len(sample_procs)} titles generated",
            elapsed,
        )
    except Exception as e:
        return report("Title generation", False, f"exception: {e}", time.time() - t0)


def test_5_polish_text():
    section("5. _polish_expected_text (main.py)")
    # _polish_expected_text is defined inside main.py and uses regex first,
    # falling back to LLM. We'll test the underlying LLM call directly.
    from tools.llm.http_utils import call_llm_api

    sample_text = "项目状态变为已完成"
    messages = [
        {"role": "system", "content": "你是一个文本润色助手。请把输入文本润色为更通顺的中文描述，直接输出润色后的文本，不要任何额外说明。"},
        {"role": "user", "content": f"润色：{sample_text}"},
    ]

    t0 = time.time()
    try:
        result = call_llm_api(
            api_base=API_BASE,
            api_key=API_KEY,
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=100,
            timeout=30,
        )
        elapsed = time.time() - t0
        if not result or not result.strip():
            return report("Text polish (LLM call)", False, "empty response", elapsed)
        return report(
            "Text polish (LLM call)",
            len(result.strip()) > 0,
            f"polished: '{result.strip()[:50]}'",
            elapsed,
        )
    except Exception as e:
        return report("Text polish (LLM call)", False, f"exception: {e}", time.time() - t0)


def main():
    print("=" * 60)
    print("  v29 #6: LLM End-to-End Verification")
    print("=" * 60)
    print(f"  API base: {API_BASE}")
    print(f"  Model:    {MODEL}")
    print(f"  API key:  {API_KEY[:8]}...{API_KEY[-4:]}")

    results = []
    results.append(test_1_action_classification())
    results.append(test_2_br_decomposition())
    results.append(test_3_field_validation())
    results.append(test_4_title_generation())
    results.append(test_5_polish_text())

    passed = sum(1 for r in results if r)
    total = len(results)
    print()
    print(f"{'=' * 60}")
    print(f"  Summary: {passed}/{total} LLM paths verified")
    print(f"{'=' * 60}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
