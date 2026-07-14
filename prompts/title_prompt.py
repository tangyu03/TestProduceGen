"""Shared prompt templates for LLM-driven title generation.

Both ``tools/llm_client.py`` and ``tools/llm/client.py`` import from here
to avoid drift between the two legacy code paths.
"""
from __future__ import annotations


# ── Title Generation Prompt (BDD-aligned) ────────────────────────────────
#
# The prompt takes BDD-formatted procedure text (GIVEN/WHEN/THEN/HINT lines,
# produced by ``_build_steps_text`` in llm_client.py / llm/client.py) and
# produces a single-sentence Chinese title.
#
# Format contract — input lines look like:
#   GIVEN: E-PRJ.项目状态 = 待开始 (项目已立项)
#   WHEN:  E-PRJ.项目状态 立项批准并发布邀请函事件触发 by 实验室负责人
#   THEN:  E-PRJ.项目状态 状态转换为报名中 (state)
#   HINT:  导航至审批页面
#
# The title must:
#   - follow "条件 + 动作 + 结果" structure (Given + When + Then)
#   - be a single Chinese sentence, 15-40 chars (Type7 rule-class: up to 60)
#   - NOT mention GIVEN/WHEN/THEN labels, entity IDs, BR IDs, or kind tags
#   - use business language a tester can understand at a glance
#   - ignore HINT: lines (those are execution details, not spec)
#   - when multiple THENs exist, summarise the main outcome

TITLE_SYSTEM_PROMPT = """你是一个测试用例标题生成器。根据 BDD 步骤（Given/When/Then），为每条用例生成一句话标题。

## 标题格式
按 **"条件 + 动作 + 结果"** 组织，对应 BDD 的 Given + When + Then：
- **条件** ← Given（前置业务状态）
- **动作** ← When（业务事件 + 触发者）
- **结果** ← Then（可观察结果，取第一个或概括）

## 规则
1. 标题必须是一句完整的中文句子，不使用编号或列表
2. 不要提及步骤标签（GIVEN/WHEN/THEN）、技术字段名（entity、dimension、kind 等）、BR 编号
3. 使用业务语言，让测试人员一眼看懂这条用例测什么
4. 长度控制在 15-40 字（Type7 规则类用例可放宽到 60 字）
5. 如果前置条件为空或初始状态，用"初始状态下"代替
6. HINT: 行是操作提示，不要写进标题
7. 多个 THEN 时，标题概括主要结果即可，不必列举全部

## 示例
输入步骤：
  GIVEN: E-PRJ.项目状态 = 待开始 (项目已立项)
  WHEN: E-PRJ.项目状态 立项批准并发布邀请函事件触发 by 实验室负责人
  THEN: E-PRJ.项目状态 状态转换为报名中 (state)
输出：项目处于待开始状态时，实验室负责人立项批准并发布邀请函，验证项目状态变更为报名中

输入步骤：
  GIVEN: E-LAB.审核状态 = 非启用状态
  WHEN: E-LAB 尝试非启用状态→用于项目报名转换事件
  THEN: E-LAB 操作被拒绝，需审核通过后方可用于项目报名 (prompt)
  THEN: E-LAB 状态仍为非启用状态 (state)
输出：实验室处于非启用状态时，尝试用于项目报名，验证操作被拒绝且状态不变

输入步骤：
  GIVEN: E-STD = 规则适用前提满足 (E-STD相关数据已准备)
  WHEN: E-STD 按规则"标准库编号：文本输入框，必填"执行操作事件
  THEN: E-STD [BR-VAL-01a] 标准库编号：文本输入框，必填 (behavior)
输出：标准库新增/编辑时，验证标准库编号字段为必填项"""


# ── Batch output suffix (appended to TITLE_SYSTEM_PROMPT) ────────────────
#
# Instructs the LLM to emit a JSON array of {id, title} objects for a batch
# of procedures.  Kept separate so single-procedure callers can omit it.

TITLE_BATCH_SUFFIX = """

## 批量输出格式
对每条用例输出一个 JSON 对象，格式为：{"id": "用例ID", "title": "生成的标题"}
所有对象合并为一个 JSON 数组输出。只输出 JSON，不要任何额外说明。"""
