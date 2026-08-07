# TestProduceGen — 测试规程编排引擎

从 SRS 需求文档自动生成测试规程的流水线系统。通过 P1（结构化抽取）→ P2（覆盖义务建模）→ P3（测试规程编排）三阶段，将自然语言需求转化为可执行的 BDD 测试规程，并由 Gate-S 骨架门禁校验质量。

---

## 整体架构

```
SRS 文档
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  P1 结构化建模 (srs_pipeline)                         │
│  SRS → domain_model + state_and_flow + constraints  │
│  入口:   srs_pipeline/（Step6 内联校验 C01-C17）     │
│  产出:   review_structured.json（P1 真源）           │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  P2 覆盖义务建模 (确定性脚本)                        │
│  P1 产出 → coverage_obligations.json                 │
│  脚本:   context/generate_obligation_model.py       │
│  Prompt: context/P2_Prompt.md                        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  P3 测试规程编排 (LangGraph 流水线)                   │
│  S0 → S1 → S2 → S3 → S4                             │
│  入口:   main.py                                     │
│  图定义: graph.py                                    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Gate-S 骨架门禁 (verify/)                          │
│  10 项检查 (V01~V10) + 失败路由 + 自优化循环         │
└─────────────────────────────────────────────────────┘
```

---

## 模块职责

### `main.py` — P3 流水线入口

- 加载 coverage_model，编译 LangGraph 并 streaming 执行
- 各阶段进度输出、结果统计、Phase 分布
- 生成 `output.json`（机器可读）+ `output.md`（人类可读测试规程）
- 调用 LLM 生成 procedure 标题（可选，需配置 API key）

### `graph.py` — LangGraph 图定义

- 定义状态机：`S0 → S1 → S2 → S3 → S4 → END`
- 条件边：S0 失败 → END，S1 无 procedure → END
- 编译为可执行 graph

### `models/` — 数据模型

| 文件 | 职责 |
|------|------|
| `state.py` | `AgentState` TypedDict——全流水线共享的状态池，含 S0~S4 各阶段输出字段 |
| `schema.py` | Pydantic 模型——procedure 结构校验，`validate_engine_state` / `validate_procedures` |

### `nodes/` — P3 五阶段节点

| 文件 | 阶段 | 职责 |
|------|------|------|
| `s0_topology.py` | S0 拓扑发现 | 从 coverage_model 推导 EngineState：primary_entity、phase_table、dep_state_phase_map、transition_upstream_map、virtual_entities 等。V08 修复：优先读 P2 产出的 phase_mapping，BFS 推导降级为 fallback |
| `s1_generation.py` | S1 规程生成 | 确定性生成 Type1~Type7 测试规程（BDD Given/When/Then）。含 BR 嵌入、guard polarity 校验、from→to 字面形式追加 |
| `s2_sorting.py` | S2 排序元数据 | 计算 sort_key（8 维：phase/topology_level/entity_entry/entity/dim/obligation_type/dim_priority/gen_seq），不排序（排序在 S3） |
| `s3_dependency.py` | S3 依赖绑定 | 绑定 procedure 间依赖（transition_upstream / guard1_state_pred / chain_ordering / guard6_precond / weak_side_effect）。V01 修复：phase guard 命中时降级为 weak_dependency。环检测 + 置信度排序破环 + Kahn 拓扑排序 + 顺序 ID 分配 |
| `s4_multi_instance.py` | S4 多实例扩展 | 按 dimension_constraints 展开 procedure 实例（如 5/7/9 人组 × 开题/验收 = 6 实例） |

### `prompts/` — LLM Prompt 模板

| 文件 | 用途 |
|------|------|
| `s0_prompt.py` | S0 拓扑发现的 system/user prompt（确定性算法失败时的 LLM fallback） |
| `s1_prompt.py` | S1 规程生成的 system/user prompt（Type1~Type7 生成规则、BR 嵌入规则、铁律） |
| `title_prompt.py` | procedure 标题生成的 prompt |

### `tools/` — 工具库

| 文件 | 职责 |
|------|------|
| `graph_algo.py` | 图算法：`build_transition_graph`、`calc_all_chain_depths`（按 entity+dimension 隔离）、`break_cycles`（置信度排序破环）、`topological_sort_procedures`（Kahn + sort_key 优先级） |
| `llm_client.py` | LLM 客户端封装 |
| `fallback_log.py` | Fallback 观测日志——记录确定性算法降级到 keyword/regex fallback 的位置 |
| `data_access.py` | 数据访问辅助 |
| `llm/` | LLM 子模块：`client.py`、`config.py`、`cache.py`、`http_utils.py`、`task_types.py` |

### `context/` — P1/P2 阶段

| 文件 | 职责 |
|------|------|
| ~~P1_Prompt.md~~ | P1 抽取已迁移至 `srs_pipeline/`（仓库根模块，见下），此文件仅存为历史 prompt 留档 |
| `P2_Prompt.md` | P2 覆盖义务建模的 prompt——P1 产出 → entity_obligations + transition_obligations + cross_entity_obligations + constraint_obligations |
| `generate_obligation_model.py` | P2 确定性脚本实现。V08 修复：`_derive_phase_mapping` 从 transitions 推导相位映射写入 state_info；state_info 扁平化布局；分支拆分逻辑 |

### `verify/` — Gate-S 骨架门禁

| 文件 | 职责 |
|------|------|
| `validators.py` | 校验调度器——加载 case_spec + output，运行 V01~V10 检查，聚合 verdict |
| `case_spec.json` | 产品规约（verify 私有数据）——state_machines(含 phase_mapping)、guard_policies、coverage_matrix、role_permissions、field_validation_rules 等 |
| `loop_manager.py` | 自优化循环管理者——编排 git worktree 快照 → 代码 Agent 修改 → 冒烟 → 流水线 → Gate-S → 失败签名路由 / 回归门控 / 硬停止 / 升级 |
| `oracles.py` | 预言机——评分计算、评级判定的可执行 Python 函数 |
| `code_agent_cli.py` | 代码 Agent CLI 接入——stdin 收 task JSON，stdout 出声明 |
| `loop_config.json` | 循环配置——pipeline_cmd、agent_cmd、预算、历史路径 |
| `llm_config.json` | LLM 配置 |
| `quality_history.jsonl` | 质量历史——每次 attempt 的 signature/verdict/metrics |
| `checks/` | 10 项检查器（见下表） |

#### `verify/checks/` — 10 项检查器

| 检查 | 文件 | 严重度 | 职责 |
|------|------|--------|------|
| V01 | `v01_dependency_closure.py` | blocker | 依赖图健康：悬空引用、依赖环、依赖相位单调性 |
| V02 | `v02_guard_polarity.py` | blocker | 守卫极性：given 命中禁止规则时，then 必须为拒绝断言，不得断言成功迁移 |
| V03 | `v03_action_ownership.py` | blocker | 动作归属：跨实体级联只能用 indirect_via，不得直接操作从动实体 |
| V04 | `v04_builtin_entity_protect.py` | blocker | 内置对象保护：readonly/no_form_page 实体禁止 type3/9 义务 |
| V05 | `v05_dimension_combo.py` | blocker | 维度组合：实例化前用 dimension_constraints 做可达性剪枝 |
| V06 | `v06_time_control.py` | warning | 时间控制：超时事件必须声明 mechanism |
| V07 | `v07_role_permission.py` | warning | 角色权限：when.actor 必须在 role_permissions.matrix 内 |
| V08 | `v08_phase_consistency.py` | blocker | 相位一致性：终态=最大相位、沿迁移相位不倒退、≥3 状态不坍缩到同一相位 |
| V09 | `v09_dedup_instances.py` | blocker | 去重：相同 (givens,when,thens) 合并，单例实体不复制 |
| V10 | `v10_coverage_matrix.py` | blocker | 覆盖矩阵：coverage_matrix 每条目的关键词必须在 procedure 文本中命中 |

### `scripts/` — 辅助脚本

| 文件 | 用途 |
|------|------|
| `run_pipeline.py` | 无 LLM 模式跑流水线（禁用 API key，跳过标题生成） |
| `regression_baseline.py` | 回归基线 |
| `cross_domain_test.py` | 跨领域测试 |
| `llm_e2e_check.py` | LLM 端到端检查 |
| `test_*.py` | 单元测试（guard6、pause_restart、primary_entity 等） |
| `patch_*.py` | 覆盖模型补丁脚本 |
| `verify_fixes.py` | 修复验证 |

### 配置文件

| 文件 | 用途 |
|------|------|
| `config.json` | LLM 配置（api_key、base_url、model、concurrency 等） |
| `coverage_obligations.json` | P2 产出（P3 流水线输入） |
| `review_structured.json` | P1 产出（P2 输入，真源） |

---

## 数据流

```
review_structured.json
  │  context/generate_obligation_model.py (P2)
  ▼
coverage_obligations.json
  │  main.py (P3: S0→S1→S2→S3→S4)
  ▼
output.json
  │  verify/validators.py --spec verify/case_spec.json --output output.json
  ▼
verdict.json (skeleton_pass: true/false)
```

## 角色与职责边界

| 角色 | 职责 | 可见范围 |
|------|------|---------|
| **P1** (srs_pipeline) | SRS → 结构化 domain_model + transitions + constraints | SRS 原文 + srs_pipeline/ |
| **P2** (确定性脚本) | P1 产出 → 覆盖义务模型 (EO/TO/CO/RO + state_info) | review_structured.json + P2_Prompt |
| **P3 builder** (代码工程) | 修复 nodes/、prompts/、tools/、context/ 代码 | 失败证据 + routing_hints + context/ 参考目录 |
| **verify** (校验) | 跑验证器、产出 verdict、定义路由表 | 全部（含 case_spec.json） |
| **loop_manager** (管理者) | 编排快照→构建→冒烟→流水线→Gate-S→路由/升级 | 全部 |

**关键约束**：`verify/case_spec.json` 是 verify 私有数据，P3 builder 不能读。phase_mapping 应由 P2 产出到 coverage_model._context.state_info。

---

## 快速开始

### 1. 运行 P2（从 P1 产出生成覆盖义务模型）

> P1 输入必传（argv[1] 或 `P1_PATH` 环境变量），当前真源为仓库根 `review_structured.json`。

```bash
python context/generate_obligation_model.py review_structured.json coverage_obligations.json
```
### 2. 校验P2生成质量

```bash
python.exe context/verify/validate_p2.py coverage_obligations.json review_structured.json
```
### 3. 运行 P3 流水线

```bash
python main.py coverage_obligations.json output.json
```

### 4. 运行 Gate-S 校验

```bash
python -m verify.validators -s verify/case_spec.json -o output.json --json verdict.json
python verify/validators.py -s verify/case_spec.json -o p3_agent_output.json --model coverage_obligations.json -j verdict.json
```

### 5. 运行自优化循环（可选）

```bash
python -m verify.loop_manager --config verify/loop_config.json --once
# 或循环模式
python -m verify.loop_manager --config verify/loop_config.json --loop
python -m verify.loop_manager --config verify/loop_config.json --loop --full
python -m verify.loop_manager --config verify/loop_config.json --dry-run --once
python -m verify.loop_manager --config verify/loop_config.json --init-baseline
  --loop        快速模式: 只跑 generate_obligation_model.py (秒级)，适合 P2 迭代
  --loop --full 完整模式: 跑 main.py 全 LLM 流水线 (分钟级)，适合最终验证
```


