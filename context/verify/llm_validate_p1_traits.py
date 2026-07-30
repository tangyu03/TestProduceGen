#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm_validate_p1_traits.py — 用 LLM 校验 P1 的 traits 和 direction 分类是否准确。

P1 输出后，脚本校验（validate_p1_direction.py）只能检查"必填 + 枚举合法 +
索引一致性"，无法判断"语义是否准确"。例如：
- T-006（待归档→已选入）的 direction 应该是 backward 还是 forward？
- T-107（待评审→暂停）的 direction 应该是 lateral 还是 forward？

这些需要语义理解，用 LLM 判别。LLM 只输出枚举值，不生成自由文本。

用法：
    python scripts/llm_validate_p1_traits.py <p1_output.json>
    python scripts/llm_validate_p1_traits.py   # 默认 context/P1_out.json

配置（优先级：环境变量 > config.json）：
    LLM_API_BASE / LLM_API_KEY / LLM_P1_VALIDATE_MODEL

退出码：0=全部一致或 LLM 不可用，1=有 LLM 判定不一致（需人工复核）
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_llm_config() -> dict | None:
    """加载 LLM 配置。"""
    api_base = os.environ.get("LLM_API_BASE")
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_P1_VALIDATE_MODEL")
    if api_base and api_key:
        return {"api_base": api_base.rstrip("/"), "api_key": api_key,
                "model": model or "glm-4-flash"}
    # Try config.json
    try:
        script_dir = Path(__file__).resolve().parent
        cfg_path = script_dir.parent / "config.json"
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f).get("llm", {})
            if cfg.get("api_key"):
                return {
                    "api_base": cfg.get("api_base", "https://open.bigmodel.cn/api/paas/v4"),
                    "api_key": cfg["api_key"],
                    "model": cfg.get("task_models", {}).get("p1_validate",
                               cfg.get("task_models", {}).get("general", "glm-4-flash")),
                }
    except Exception:
        pass
    return None


def llm_classify(system_prompt: str, user_message: str, valid_values: list[str],
                 cfg: dict, timeout: int = 30) -> str | None:
    """调用 LLM 分类，输出约束为 valid_values 之一。"""
    try:
        url = f"{cfg['api_base']}/chat/completions"
        body = json.dumps({
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 50,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        content = content.strip().lower()
        for v in valid_values:
            if v in content:
                return v
        return None
    except Exception as e:
        print(f"  [LLM error] {e}")
        return None


def build_context_for_transition(t: dict, p1: dict) -> str:
    """为单个 transition 构建 LLM 判断所需的上下文。"""
    entity = t.get("entity")
    dim = t.get("dimension")
    f = t.get("from")
    to = t.get("to")
    action = t.get("action", "")
    traits = t.get("traits", [])
    note = t.get("note", {})
    note_comment = note.get("comment", "") if isinstance(note, dict) else ""

    # 找状态列表
    states = []
    for e in p1.get("domain_model", {}).get("entities", []):
        if e["id"] == entity:
            for d in e.get("state_dimensions", []):
                if d["dimension_name"] == dim:
                    states = d.get("states", [])
                    break

    return (
        f"实体: {entity}\n"
        f"维度: {dim}\n"
        f"状态列表: {states}\n"
        f"迁移: {f!r} → {to!r}\n"
        f"动作: {action}\n"
        f"traits: {traits}\n"
        f"note: {note_comment}\n"
    )


def validate_direction_via_llm(t: dict, p1: dict, cfg: dict) -> str | None:
    """用 LLM 判断 transition 的 direction 是否正确。"""
    context = build_context_for_transition(t, p1)
    system = (
        "你是一个状态机拓扑分析专家。给定一个状态迁移的上下文，判断它的拓扑方向：\n"
        "- forward: 主链推进，相位递增（如 待选入→已选入）\n"
        "- backward: 合法回退，回到更早的状态（如 已选入→待选入 选出）\n"
        "- lateral: 侧挂状态入口（如 待评审→暂停）\n"
        "- resume: 从侧挂返回主链（如 暂停→待评审 重启）\n"
        "只输出 forward / backward / lateral / resume 中的一个词。"
    )
    user = f"{context}\n请判断这个迁移的拓扑方向。"
    return llm_classify(system, user, ["forward", "backward", "lateral", "resume"], cfg)


def validate_traits_via_llm(t: dict, p1: dict, cfg: dict) -> list[str] | None:
    """用 LLM 判断 transition 的 traits 是否准确（只校验 rollback trait）。"""
    context = build_context_for_transition(t, p1)
    system = (
        "你是一个状态机迁移特征分析专家。给定一个状态迁移的上下文，判断它是否应该标记 rollback trait：\n"
        "- rollback=true: 这个迁移本身是回退操作（如 选出项目、取消评审计划）\n"
        "- rollback=false: 这个迁移是正向推进或侧挂/恢复\n"
        "只输出 true 或 false。"
    )
    user = f"{context}\n这个迁移是否应该标记 rollback trait？"
    result = llm_classify(system, user, ["true", "false"], cfg)
    if result == "true":
        return ["rollback"]
    elif result == "false":
        return []
    return None


def main():
    if len(sys.argv) >= 2:
        p1_path = sys.argv[1]
    else:
        script_dir = Path(__file__).resolve().parent
        p1_path = str(script_dir.parent / "context" / "P1_out.json")

    if not os.path.exists(p1_path):
        print(f"ERROR: P1 output not found: {p1_path}")
        sys.exit(1)

    cfg = load_llm_config()
    if not cfg:
        print("LLM 不可用（未配置 LLM_API_KEY 或 config.json）。退出。")
        print("配置方式：设置环境变量 LLM_API_BASE / LLM_API_KEY，或在 config.json 的 llm.api_key 配置。")
        sys.exit(0)  # LLM 不可用不算错误

    print(f"LLM config: {cfg['api_base']}, model={cfg['model']}")
    print(f"Validating P1 traits/direction via LLM: {p1_path}")
    print("=" * 60)

    with open(p1_path, encoding="utf-8") as f:
        p1 = json.load(f)

    transitions = p1.get("state_and_flow", {}).get("transitions", [])
    mismatches = []

    for i, t in enumerate(transitions):
        tid = t.get("id", "?")
        current_direction = t.get("direction")
        current_traits = t.get("traits", [])
        has_rollback = "rollback" in current_traits

        # 只校验非创建转换（from != null）
        if t.get("from") is None:
            continue

        print(f"[{i+1}/{len(transitions)}] {tid}: ", end="", flush=True)

        # direction 校验
        llm_direction = validate_direction_via_llm(t, p1, cfg)
        direction_match = "跳过" if llm_direction is None else ("一致" if llm_direction == current_direction else "不一致")

        # rollback trait 校验
        llm_rollback = validate_traits_via_llm(t, p1, cfg)
        rollback_match = "跳过" if llm_rollback is None else ("一致" if ("rollback" in llm_rollback) == has_rollback else "不一致")

        print(f"direction={current_direction!r}(LLM={llm_direction!r}, {direction_match}) "
              f"rollback={has_rollback}(LLM={llm_rollback}, {rollback_match})")

        if direction_match == "不一致":
            mismatches.append({
                "id": tid,
                "field": "direction",
                "current": current_direction,
                "llm_judgment": llm_direction,
                "transition": f"{t.get('from')}→{t.get('to')}",
                "action": t.get("action", ""),
            })
        if rollback_match == "不一致":
            mismatches.append({
                "id": tid,
                "field": "rollback_trait",
                "current": has_rollback,
                "llm_judgment": "rollback" in llm_rollback if llm_rollback is not None else None,
                "transition": f"{t.get('from')}→{t.get('to')}",
                "action": t.get("action", ""),
            })

    print("\n" + "=" * 60)
    print(f"LLM 判定不一致项: {len(mismatches)}")
    if mismatches:
        print("\n=== 需人工复核 ===")
        for m in mismatches:
            print(f"  {m['id']} ({m['transition']}): {m['field']} "
                  f"当前={m['current']!r} LLM判定={m['llm_judgment']!r}  action={m['action'][:40]}")
        sys.exit(1)
    else:
        print("✓ 全部一致（或 LLM 跳过的项）")
        sys.exit(0)


if __name__ == "__main__":
    main()
