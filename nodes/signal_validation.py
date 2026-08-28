from __future__ import annotations
"""校验意图驱动（signal-intent）的验证点生成 via LLM。

BR 的校验意图由新字段派生（旧 signal_type 税已于 2026-08-25 迁移删除）：
``restrictive`` (bool) 与 ``category`` (str) 共同决定一条规则属于哪种
"校验意图"。本模块把每条 BR 映射到专用 LLM prompt，生成比确定性模板
更丰富、更贴合的 V 步骤。

校验意图路由（见 _verification_intent）：:

    restrictive=True              "This operation MUST be blocked"  → negative-test gen
    category=validation           "Input MUST match format"         → boundary / equivalence class
    category=usability            "User MUST see correct feedback"  → UI-copy verification
    category=display              "Page MUST show correct data"     → data-presentation verification
    category=computation          "Calculation MUST be correct"     → input→output table
    其它 category / 无意图映射      Unclassified                      → lightweight classify-then-route

Integration points (called from ``s1_generation.py``):

* ``generate_signal_v_steps()`` — main entry point; returns br_id → V-step
  dicts that replace or enrich the template-based V-steps in Type7 standalone
  and BR-embedding flows.
"""

import hashlib
import json
import os
import re
import time
from collections import defaultdict

# ---------------------------------------------------------------------------
# 校验意图路由键派生（数据驱动）
# ---------------------------------------------------------------------------
# category 承袭旧税值（validation = 旧 field_constraint 等）并新增
# notification/authorization/timing；restrictive 是 S1 闸门布尔，优先于
# category 决定负向测试意图。
_INTENT_BY_CATEGORY = {
    "validation": "field_constraint",
    "field_constraint": "field_constraint",  # 旧值兼容（防历史数据残留）
    "usability": "usability",
    "display": "display",
    "computation": "computation",
    "restrictive": "restrictive",
}


def _verification_intent(br: dict) -> str | None:
    """从新字段 (restrictive bool + category str) 派生校验意图路由键。

    返回 None = 无专用意图 prompt（notification/authorization/timing 等），
    走轻量 classify-then-route（_classify_null_brs）或跳过，与旧
    "Unknown signal_type ... skipping" 行为一致。
    """
    if br.get("restrictive"):
        return "restrictive"
    return _INTENT_BY_CATEGORY.get(br.get("category") or "")


# ---------------------------------------------------------------------------
# Per-intent system prompts
# ---------------------------------------------------------------------------

# Each prompt tells the LLM:
#   1. What this intent MEANS (verification intent)
#   2. HOW to generate V-steps for this type
#   3. WHAT the output format should be

_SIGNAL_SYSTEM_PROMPTS: dict[str, str] = {
    # ── restrictive: 限制性规则 → 负向测试 ──────────────────────────────
    "restrictive": """你是一个限制性业务规则的校验点生成器。

## 规则含义
"restrictive" 类型的规则用于 **阻止不合规的操作**。每条规则定义了：
- 什么条件下操作被允许/禁止
- 违反规则时应有什么反馈

## 你的任务
对每条规则，生成 1-3 个 V（验证）步骤，每个 V 步骤描述一个具体的违规场景。

## V 步骤格式
```json
{"constraint_id": "BR-XXXX", "v_steps": [
  {"input": "具体的违规输入或操作", "expected": "验证操作被阻止，提示'具体拒绝原因'"}
]}
```

## 生成规则
1. 对每个禁止条件，生成 1 个违规场景。如果规则有多个禁止分支，每个分支各生成 1 条
2. expected 必须用自然语言描述，包含：(a)操作被拒绝/阻止 (b)具体的拒绝原因或提示文案 (c)状态不变。不要用"状态验证:"/"验证:"等前缀
3. input 必须具体可执行，不能模糊写"尝试违规操作"
4. 如有角色/权限限制，明确指出由哪个角色尝试

## 示例
规则：项目评级为"差"时不可选入验收阶段
→ input: "将评级为'差'的项目执行选入验收"  expected: "系统拒绝选入操作，弹出提示'本阶段评级为差的项目不可选入'，项目仍保持当前状态"

规则：登录时密码连续错误5次锁定账户30分钟
→ 生成2条: (1)input: "连续输入5次错误密码" expected: "第5次错误后账户被自动锁定，页面显示'账户已锁定，请30分钟后重试'" (2)input: "账户锁定后立即尝试登录" expected: "登录被拒绝，页面提示'账户已锁定，剩余锁定时间28分钟'"

## 输出格式
每行一个 JSON 对象（JSONL）。只输出 JSONL，不要数组、不要额外文字、不要代码块。""",

    # ── field_constraint: 字段约束 → 边界值+等价类 ──────────────────────
    "field_constraint": """你是一个字段约束规则的校验点生成器。

## 规则含义
"field_constraint" 类型的规则定义了字段的格式/范围/类型约束。

## 你的任务
对每条规则，生成 2-5 个 V 步骤，覆盖以下维度：
1. **合法边界值**（1条）：刚好满足约束的值 → 验证通过
2. **非法越界值**（1-2条）：超出约束的值 → 验证拒绝
3. **空值/特殊值**（1条）：留空、纯空格、特殊字符等 → 验证拒绝

## V 步骤格式
```json
{"constraint_id": "BR-XXXX", "v_steps": [
  {"input": "具体的输入值", "expected": "校验通过，提示'成功'" 或 "校验失败，提示'具体限制'"}
]}
```

## 生成规则
1. 有明确数值范围(N-M) → 生成：M+1(超限) + M-1(合法边界) + N(合法边界) + N-1(低于下限)
2. 有长度限制 → 生成：超长+合法最长+空值
3. 有格式要求(如含字母+数字+特殊字符) → 生成：缺字母+缺数字+缺特殊字符+全满足
4. 有枚举限制 → 生成：不在枚举中的值
5. expected 必须用自然语言描述校验结果，引用规则原文的限制值，不能模糊写"格式错误"。不要用"校验失败"/"校验通过"等生硬前缀

## 示例
规则：密码长度8-18位，包含字母、数字和特殊字符
→ 生成5条:
  input:"abc123_" → expected:"输入框下方显示红色提示'密码长度不足8位'，提交按钮保持禁用"
  input:"abcdefgh1_" → expected:"密码通过校验，输入框显示绿色对勾，提交按钮可用"
  input:"abcdefghijklmnopqrs1_" → expected:"输入框下方显示红色提示'密码长度不能超过18位'"
  input:"abcdefgh_" → expected:"输入框下方显示红色提示'密码必须包含数字'"
  input:"" → expected:"输入框失焦后显示红色提示'密码为必填项'"

## 输出格式
每行一个 JSON 对象（JSONL）。只输出 JSONL，不要数组、不要额外文字、不要代码块。""",

    # ── usability: 可用性规则 → UI反馈验证 ──────────────────────────────
    "usability": """你是一个可用性规则的校验点生成器。

## 规则含义
"usability" 类型的规则关注 **用户操作后的反馈和引导**，如提示信息、操作引导、错误说明等。

## 你的任务
对每条规则，生成 1-3 个 V 步骤，验证用户界面的反馈是否到位。

## V 步骤格式
```json
{"constraint_id": "BR-XXXX", "v_steps": [
  {"input": "操作描述", "expected": "验证UI显示'具体的提示文案'"}
]}
```

## 生成规则
1. 规则提到"提示/显示/引导" → expected用自然语言描述应出现的界面反馈
2. 规则提到"提供选项" → expected描述可用的操作选项和交互行为
3. 规则提到"错误提示" → expected描述具体的错误信息内容和展示位置
4. 区分正向反馈(操作成功)和负向反馈(操作失败)
5. expected 使用流畅的业务语言，不要用"验证"/"确认"等前缀开头

## 示例
规则：登录时用户名或密码错误应明确提示
→ input: "输入错误的用户名"  expected: "页面顶部出现红色Toast提示'用户名或密码错误'，3秒后自动消失，输入框保留已输入的用户名"
→ input: "输入正确的用户名但错误的密码"  expected: "页面顶部同样显示'用户名或密码错误'的红色Toast，不区分具体是用户名还是密码错误"

规则：删除操作应提供二次确认
→ input: "点击删除按钮"  expected: "弹出确认对话框，标题为'确认删除'，正文显示'删除后数据不可恢复，确定要继续吗？'，提供'取消'(灰色)和'确定删除'(红色)两个按钮"

## 输出格式
每行一个 JSON 对象（JSONL）。只输出 JSONL，不要数组、不要额外文字、不要代码块。""",
    # ── display: 展示规则 → 数据呈现验证 ────────────────────────────────
    "display": """你是一个展示规则的校验点生成器。

## 规则含义
"display" 类型的规则关注 **信息在界面上的正确展示**，如统计结果、状态标签、列表数据等。

## 你的任务
对每条规则，生成 1-3 个 V 步骤，验证页面展示的数据是否正确。

## V 步骤格式
```json
{"constraint_id": "BR-XXXX", "v_steps": [
  {"input": "触发展示的操作", "expected": "验证页面展示'具体数据/状态/统计结果'正确"}
]}
```

## 生成规则
1. 规则提到"展示/显示/查看"某信息 → expected用自然语言描述页面上应出现的具体内容和样式
2. 规则提到统计/汇总 → 生成具体数值和呈现形式（如"页面顶部统计卡片显示：共3个项目，2个合格(绿色)，1个不合格(红色)"）
3. 规则提到状态 → expected描述状态标签的颜色、文字和位置
4. 区分不同条件/角色下的展示差异
5. 如有条件展示 → 同时生成"条件满足时"和"条件不满足时"两个验证点

## 示例
规则：提供展示项目阶段评价结果的功能
→ input: "打开项目详情页，查看开题阶段评价"  expected: "页面'阶段评价'区域展示开题阶段的评价结果，评级标签显示为蓝色'合格'，下方列出各评审专家的打分明细"
→ input: "切换到验收阶段评价Tab"  expected: "Tab切换后展示验收阶段的评价结果，包含每位评审专家的评分(如85分)、评级(如良好)和评语摘要"

## 输出格式
每行一个 JSON 对象（JSONL）。只输出 JSONL，不要数组、不要额外文字、不要代码块。""",
    # ── computation: 计算规则 → 公式验证 ─────────────────────────────────
    "computation": """你是一个计算规则的校验点生成器。

## 规则含义
"computation" 类型的规则定义了 **业务计算逻辑**，如评分计算、比例计算、汇总统计等。

## 你的任务
对每条规则，生成 2-4 个 V 步骤，覆盖多组输入→预期输出的验证。

## V 步骤格式
```json
{"constraint_id": "BR-XXXX", "v_steps": [
  {"input": "设置具体输入条件", "expected": "验证计算结果为'具体数值或结果'"}
]}
```

## 生成规则
1. 正常输入 → 正常输出（1-2组不同输入）
2. 边界输入 → 边界输出（如0、最大值、空集）
3. 异常输入 → 异常处理（如除零、空值）
4. expected 必须用自然语言描述计算结果，包含具体数值和计算逻辑的简要说明
5. 如果规则含公式，在input中明确每个自变量的值

## 示例
规则：计分结果 = 已提交专家打分结果占总专家打分结果的比例
→ 生成3条:
  input: "5位专家中3位已提交打分结果"  expected: "项目详情页'评审进度'区域显示计分结果为60%（3/5），进度条填充至60%位置，颜色为蓝色"
  input: "5位专家全部已提交打分结果"  expected: "项目详情页显示计分结果为100%（5/5），进度条满格变为绿色，'提交评审'按钮变为灰色不可点击"
  input: "5位专家中0位已提交打分结果"  expected: "项目详情页显示计分结果为0%（0/5），进度条为空，显示灰色提示'暂无专家提交打分'"

## 输出格式
每行一个 JSON 对象（JSONL）。只输出 JSONL，不要数组、不要额外文字、不要代码块。""",
}

# Prompt for unclassified BRs (无 restrictive 且 category 无意图映射) —
# lightweight classification into a verification intent before routing.
_NULL_CLASSIFY_PROMPT = """你是一个业务规则分类器。请根据规则描述，判断它属于哪种校验类型。

类型定义：
- restrictive: 限制性规则 — 阻止不合规操作（含"不可/不能/不允许/必须/才可/只有"等）
- field_constraint: 字段约束 — 输入格式/长度/类型限制（含"长度/格式/位数/必填/唯一"等）
- usability: 可用性规则 — 用户提示/引导/反馈（含"提示/显示/提供选项/确认"等）
- display: 展示规则 — 信息正确展示（含"展示/查看/统计/列表"等）
- computation: 计算规则 — 业务计算逻辑（含"计算/比例/汇总/公式/占比"等）

对每条规则输出 JSONL。**constraint_id 必须使用输入中给出的精确值，不要修改或自创**：
{"constraint_id": "输入中的精确ID", "classified_signal_type": "restrictive", "confidence": "high或medium"}

只输出 JSONL，不要额外文字。"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Normalise BR ID: some entries use "constraint_id", others use "id"
def _get_br_id(br: dict) -> str:
    """Return the canonical constraint ID from a BR dict."""
    return br.get("constraint_id") or br.get("id", "")


def _find_br_by_id(br_list: list[dict], br_id: str) -> dict | None:
    """Find a BR in a list by its constraint_id or id field."""
    for b in br_list:
        if _get_br_id(b) == br_id:
            return b
    return None


def generate_signal_v_steps(
    constraint_obligations: list[dict],
    entity_name_map: dict[str, str] | None = None,
) -> dict[str, list[dict]]:
    """Generate signal-type-aware V-steps for all business_rule constraint obligations.

    Groups BRs by verification intent, calls the LLM with the corresponding specialized
    prompt, and returns a ``{constraint_id: [V-step-dict, ...]}`` map.

    Args:
        constraint_obligations: The ``constraint_obligations`` list from the
            P2 coverage model.  Only entries with ``type == "business_rule"``
            are processed.
        entity_name_map: Optional entity-ID → Chinese-name mapping for
            richer V-step generation.

    Returns:
        Dict mapping ``constraint_id`` (str) → list of V-step dicts, each with
        keys ``aaa``, ``input``, ``expected``.  An empty dict is returned when
        the LLM is unavailable or there are no BRs to process.
    """
    if entity_name_map is None:
        entity_name_map = {}

    # Filter: only business_rule type
    brs = [ro for ro in constraint_obligations if ro.get("type") == "business_rule"]
    if not brs:
        return {}

    # Check API availability
    api_base, api_key, model = _load_api_config()
    if not api_key:
        print("      [SIGNAL] LLM_API_KEY not set — skipping signal validation")
        return {}

    # 按校验意图分组（由 restrictive bool + category 派生，旧 signal_type
    # 税已删）；无意图映射的 BR 进 unclassified 走轻量 classify-then-route。
    by_signal: dict[str, list[dict]] = defaultdict(list)
    unclassified: list[dict] = []
    for br in brs:
        intent = _verification_intent(br)
        if intent:
            by_signal[intent].append(br)
        else:
            unclassified.append(br)

    # Attempt cache load first
    cached = _load_cache(brs)
    if cached is not None:
        print(f"      [SIGNAL] Loaded from cache ({len(cached)} BRs)")
        return cached

    all_results: dict[str, list[dict]] = {}

    # Phase 1: classify unclassified BRs if any
    if unclassified:
        classified, class_order = _classify_null_brs(unclassified, api_base, api_key, model)
        for br_id, st in classified.items():
            br = _find_br_by_id(unclassified, br_id)
            if br is None:
                # LLM may have returned a different ID — try position-based fallback
                if class_order and br_id in class_order:
                    pos = class_order.index(br_id)
                    if pos < len(unclassified):
                        br = unclassified[pos]
                        print(f"      [SIGNAL]   Position-fallback: {br_id} → {_get_br_id(br)} ({st})")
            if br is not None:
                by_signal[st].append(br)
            else:
                print(f"      [SIGNAL]   WARN: Cannot find BR for classified {br_id}")
                # BUGFIX #12: previously only called setdefault() without
                # appending anything, so the BR was silently dropped.
                # Now append a placeholder so downstream can see the gap;
                # use restrictive bucket as a safe default.
                by_signal.setdefault("restrictive", []).append({"id": br_id, "_orphan": True})

    # Phase 2: generate V-steps per intent
    total_brs = sum(len(v) for v in by_signal.values())
    print(f"      [SIGNAL] Calling {model}, {total_brs} BRs in {len(by_signal)} intent(s)...")

    for intent, br_group in sorted(by_signal.items()):
        prompt = _SIGNAL_SYSTEM_PROMPTS.get(intent)
        if not prompt:
            print(f"      [SIGNAL] Unknown intent '{intent}' — skipping {len(br_group)} BRs")
            continue

        n_batches = (len(br_group) + _BATCH_SIZE - 1) // _BATCH_SIZE
        print(f"      [SIGNAL]   {intent}: {len(br_group)} BRs in {n_batches} batch(es)")

        for batch_idx in range(0, len(br_group), _BATCH_SIZE):
            batch = br_group[batch_idx:batch_idx + _BATCH_SIZE]
            batch_num = batch_idx // _BATCH_SIZE + 1

            entries = _call_llm_batch(
                api_base, api_key, model, prompt, batch,
                batch_num, n_batches, intent, entity_name_map,
            )

            for entry in entries:
                cid = entry.get("constraint_id", "")
                v_steps = entry.get("v_steps", [])
                # Fallback: LLM may have returned flat V-step objects without
                # the {constraint_id, v_steps} envelope. Treat each entry as
                # its own V-step if it has "input" and "expected".
                if not cid and entry.get("input") and entry.get("expected"):
                    # Use position: assign to the first BR in the batch that
                    # hasn't received V-steps yet
                    for b in batch:
                        b_cid = _get_br_id(b)
                        if b_cid and b_cid not in [e.get("constraint_id", "") for e in entries if e.get("constraint_id")]:
                            cid = b_cid
                            v_steps = [entry]
                            break
                if cid and v_steps:
                    # BDD: normalise V-steps to ThenClause dict format
                    # (was: {"aaa":"THEN", "location":..., "input":..., "expected":...})
                    normalized: list[dict] = []
                    for vs in v_steps:
                        then = {
                            "target": vs.get("location", ""),
                            "expectation": vs.get("expected", "") or vs.get("input", ""),
                            "kind": "behavior",
                            "br_refs": [],
                            "cross_refs": [],
                        }
                        normalized.append(then)
                    all_results[cid] = normalized

            if n_batches > 1 and batch_num < n_batches:
                time.sleep(1)

    # Cache results
    _save_cache(brs, all_results)

    n_total_v = sum(len(v) for v in all_results.values())
    print(f"      [SIGNAL] Done: {n_total_v} V-steps for {len(all_results)} BRs "
          f"({len(brs) - len(all_results)} skipped/empty)")

    return all_results


# ---------------------------------------------------------------------------
# Unclassified-routing (lightweight LLM call to assign a verification intent)
# ---------------------------------------------------------------------------

def _classify_null_brs(
    brs: list[dict],
    api_base: str,
    api_key: str,
    model: str,
) -> tuple[dict[str, str], list[str]]:
    """Use a lightweight LLM call to classify unclassified BRs into an intent.

    Returns ``({constraint_id: intent}, order_list)``.
    ``order_list`` preserves the LLM output order for position-based
    fallback when the LLM returns IDs that don't match the original data.
    """
    if not brs:
        return {}, []

    print(f"      [SIGNAL] Classifying {len(brs)} unclassified BRs...")
    entries = _call_llm_batch(
        api_base, api_key, model, _NULL_CLASSIFY_PROMPT, brs,
        1, 1, "null_classify", {},
    )

    result: dict[str, str] = {}
    order: list[str] = []
    for entry in entries:
        cid = entry.get("constraint_id", "")
        st = entry.get("classified_signal_type", "")
        order.append(cid)
        if cid and st in _SIGNAL_SYSTEM_PROMPTS:
            result[cid] = st
            conf = entry.get("confidence", "medium")
            print(f"      [SIGNAL]   {cid} → {st} (confidence: {conf})")
        elif cid:
            # Default to restrictive for safety (most common type)
            result[cid] = "restrictive"
            print(f"      [SIGNAL]   {cid} → restrictive (fallback)")

    return result, order


# ---------------------------------------------------------------------------
# LLM call (same HTTP pattern as field_validation.py)
# ---------------------------------------------------------------------------

_BATCH_SIZE = 8  # Smaller batches — signal prompts generate more tokens per BR


def _build_user_prompt(
    batch: list[dict],
    intent: str,
    entity_name_map: dict[str, str],
) -> str:
    """Build the user prompt listing BRs with their context."""
    lines = [
        f"请为以下 {len(batch)} 条 {intent} 校验意图的业务规则生成校验 V 步骤：",
        "",
    ]
    for i, br in enumerate(batch):
        cid = _get_br_id(br) or "?"
        desc = br.get("description", "")
        entities_raw = br.get("entities_involved", br.get("entities", ""))
        # Resolve entity names (handles both list and string formats)
        if entity_name_map and entities_raw:
            resolved = []
            items = entities_raw if isinstance(entities_raw, list) else re.split(r'[,，、\s]+', entities_raw)
            for e in items:
                e = e.strip() if isinstance(e, str) else str(e)
                if e:
                    resolved.append(entity_name_map.get(e, e))
            entities_str = "、".join(resolved) if resolved else str(entities_raw)
        else:
            entities_str = str(entities_raw) if entities_raw else "(未指定)"

        category = br.get("category", "")
        enforcement = br.get("enforcement", "mandatory")
        suggested = br.get("suggested_action", "")

        lines.append(f"### {i + 1}. {cid}")
        lines.append(f"涉及实体: {entities_str}")
        lines.append(f"规则分类: {category}")
        lines.append(f"强制级别: {enforcement}")
        lines.append(f"规则描述: {desc}")
        if suggested:
            lines.append(f"建议操作: {suggested}")
        lines.append("")

    return "\n".join(lines)


def _call_llm_batch(
    api_base: str,
    api_key: str,
    model: str,
    system_prompt: str,
    batch: list[dict],
    batch_num: int,
    total_batches: int,
    intent: str,
    entity_name_map: dict[str, str],
) -> list[dict]:
    """Send one batch of BRs to LLM with the intent-specific prompt.

    Returns parsed entries list (each entry is ``{constraint_id, v_steps: [...]}``).
    """
    import urllib.error
    import urllib.request

    url = f"{api_base}/chat/completions"
    user_prompt = _build_user_prompt(batch, intent, entity_name_map)

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.15,
        "max_tokens": len(batch) * 300 + 400,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    last_error = ""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            break
        except urllib.error.HTTPError as e:
            last_error = str(e)
            if e.code == 429 and attempt < 2:
                wait = (attempt + 1) * 10
                print(f"      [SIGNAL] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"      [SIGNAL] Batch {batch_num}/{total_batches} failed: HTTP {e.code}")
            return []
        except Exception as e:
            last_error = str(e)
            if attempt < 2:
                time.sleep(3)
                continue
            print(f"      [SIGNAL] Batch {batch_num}/{total_batches} failed: {last_error}")
            return []
    else:
        print(f"      [SIGNAL] Batch {batch_num}/{total_batches} failed after 3 retries: {last_error}")
        return []

    text = _repair_json(raw)

    # Try JSONL first
    entries = _parse_jsonl(text)
    if entries:
        print(f"      [SIGNAL] Batch {batch_num}/{total_batches}: "
              f"{len(entries)} JSONL entries from {len(batch)} BRs")
        return entries

    # Fallback: JSON array
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            print(f"      [SIGNAL] Batch {batch_num}/{total_batches}: "
                  f"{len(parsed)} array entries from {len(batch)} BRs")
            return parsed
    except json.JSONDecodeError:
        pass

    # Last resort: extract {...} objects
    parsed = _extract_json_objects(text)
    if parsed:
        print(f"      [SIGNAL] Batch {batch_num}/{total_batches}: "
              f"salvaged {len(parsed)} objects")

    return parsed


# ---------------------------------------------------------------------------
# JSON repair helpers (same pattern as field_validation.py / http_utils.py)
# ---------------------------------------------------------------------------

def _repair_json(text: str) -> str:
    """Fix common JSON formatting errors in LLM output."""
    if text.startswith("```"):
        nl = text.find("\n")
        text = text[nl + 1:] if nl >= 0 else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start:end + 1]

    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    for ch_quote, escaped in [("“", "\\u201c"), ("”", "\\u201d")]:
        text = text.replace(ch_quote, escaped)

    return text


def _parse_jsonl(text: str) -> list[dict]:
    """Parse JSONL (one JSON object per line)."""
    entries = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        line = line.rstrip(",").rstrip()
        for cq, esc in [("“", "\\u201c"), ("”", "\\u201d")]:
            line = line.replace(cq, esc)
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "constraint_id" in obj:
                entries.append(obj)
        except json.JSONDecodeError:
            continue
    return entries


def _extract_json_objects(text: str) -> list[dict]:
    """Fallback: extract individual {...} objects from malformed JSON."""
    objects = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start:i + 1]
                candidate = re.sub(r",\s*}", "}", candidate)
                candidate = re.sub(r",\s*]", "]", candidate)
                for cq, esc in [("“", "\\u201c"), ("”", "\\u201d")]:
                    candidate = candidate.replace(cq, esc)
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    return objects


# ---------------------------------------------------------------------------
# API config
# ---------------------------------------------------------------------------

def _load_api_config() -> tuple[str, str, str]:
    """Load API credentials, returning (api_base, api_key, model)."""
    api_base = os.environ.get("LLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_SIGNAL_MODEL", "glm-4-flash")

    if not api_key:
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            llm_cfg = cfg.get("llm", {})
            api_base = llm_cfg.get("api_base", api_base).rstrip("/")
            api_key = llm_cfg.get("api_key", api_key)
            # Support task-specific model config
            task_models = llm_cfg.get("task_models", {})
            model = task_models.get("signal_validation", llm_cfg.get("signal_model", model))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return api_base, api_key, model


# ---------------------------------------------------------------------------
# Cache (same pattern as field_validation.py)
# ---------------------------------------------------------------------------

def _cache_path(items: list[dict]) -> str:
    """Derive a stable cache path from the BR items content."""
    stable = json.dumps(
        sorted(items, key=lambda x: _get_br_id(x)),
        ensure_ascii=True, sort_keys=True,
    )
    h = hashlib.sha256(stable.encode()).hexdigest()[:16]
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
    return os.path.join(cache_dir, f"sv_{h}.json")


def _load_cache(items: list[dict]) -> dict[str, list[dict]] | None:
    """Try to load cached result; return None if cache miss."""
    cpath = _cache_path(items)
    if not os.path.exists(cpath):
        return None
    try:
        with open(cpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result: dict[str, list[dict]] = {}
        for cid, steps in data.items():
            if isinstance(steps, list):
                result[cid] = steps
        return result if result else None
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _save_cache(items: list[dict], result: dict[str, list[dict]]) -> None:
    """Save result to cache file."""
    cpath = _cache_path(items)
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    try:
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # Cache write failure is non-fatal
