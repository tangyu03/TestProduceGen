# branch_values 生命周期归属改造 — 交付说明与验证报告

> 交付日期：2026-09-03 ｜ 交付包：`branch_lifecycle_refactor.zip`
> 原则：全部为根因治理（schema / 相位 / 依赖边三层），无任何数据补丁。

---

## 一、改造范围（三层 + prompt + 数据）

### 第 1 层：schema 根治 —— 转换获得"生命周期身份"

- `srs_pipeline/model.py` `add_trans()`：新增结构化 `branch_values` 字段
  （`[str(v) for v in branch_values or []]`），随 P1.5 `assemble()` 序列化进 JSON。
- 语义：`branch_values` = 转换仅在哪些分支值（生命周期）下存在；空 = 共享模板
  （每个分支值下都实例化）。P2 拆分层消费（有归属不展开），S0/S1/S3 相位与
  依赖按归属分支链取值。

### 第 2 层：P2 拆分层根治 —— "有归属 → 不展开，无归属 → 才全量展开"

- `context/generate_obligation_model.py`（拆分核心约 1353–1392 行）：
  - TO 携带非空 `branch_values` → 保留单实例，**不再做 all-values 笛卡尔展开**
    （消灭 T-044[a]/T-016[b]/T-065[a] 类伪变体的生产线）；
  - 无归属（真共享/非分支）→ 维持原有展开/复用行为；
  - 保留多组合展开变体（id 带 `[a-z]` 后缀）形态供运行时选择型分支使用，
    `branch_path` 取值为互斥归属。
- per-branch 相位链（约 2897–2947 行）：对生命周期型分支维度（`branches[].target_transition`
  全部指向 frm=None 创建转换），在每个分支入口创建转换落点为 initial 的约束下，
  为归属分支各推导一条独立相位链，写入
  `state_info[entity].dimensions[*].phase_mapping_by_branch`。

### 第 3 层：S0/S1/S3 相位与依赖边根治

- `nodes/s0_topology.py`：
  - `_get_branch_phase_mappings()` 读取 P2 的 `phase_mapping_by_branch`；
  - S0.3b 生成 per-branch `phase_table`；S0.4b 生成 per-branch
    `dep_state_phase_map_by_branch`（引擎态），S3 全部消费。
- `nodes/s3_dependency.py`（本次改造收口，依赖边分支感知）：
  - 归属解析：`_to_branch_values()`（TO 显式声明 > 展开变体 branch_path 取值 >
    空=共享）；`_proc_branch_values()`（proc 归属 = source_ids 解析到的 TO 归属
    并集）；`_branch_compatible()`（共享与任何归属兼容；两个非空归属须相交才可连边）。
  - **13 处 `cross_branch` 调用点**，覆盖全部连边机制：
    | 机制 | 剔除口径（branch_skip_stats） |
    |---|---|
    | Guard 1 状态机前驱（含去重对） | guard1_state_pred |
    | 同维链序（跨分支同名状态汇合点不构成链） | chain_ordering |
    | Guard 5 创建先于使用 | guard5_create_use |
    | Guard 6 前置态产出者（结构化/回退全路径） | guard6_precond |
    | CO 使能者 / VE.co_ids | co_enabler / ve_co_ids |
    | side_effect 弱依赖 | weak_side_effect |
    | B2 容器创建边（v3 归属消歧） | composition_container |
  - 回退边判定用归属分支相位图：`state_pos_for(proc)` 优先返回归属分支视图，
    平行链上互逆的推进（报名中→待开始）在归属链内是顺向，不再被误判回退；
  - B2 容器创建边 v3：多创建候选时子 proc 归属与父创建 proc 归属取交集，
    唯一兼容者入选；仍歧义（多个/零个）才显式留白+警告（替代 v1 赌 min sort_key）；
  - 兼容旧 P2 输出（无 branch_path/branch_values 时归属全空，行为与改造前一致）。
  - 汇总审计：`S3.B 分支感知: 跨分支候选剔除 <origin>×<n>` 警告行。

### 建模 prompt：`srs_pipeline/glm5pr.md`

- §3.1 新增**归属铁律**：`branch_values` 是转换的生命周期身份；分立型转换
  **必须**声明 `branch_values=[<本条仅在的分支值>]`；共用型不声明。
- **平行流程型分支**（同一实体维度在文档多章节各有完整生命周期、且与首条转换
  落点次序互逆）：除两条创建转换互为分立外，**每条分支各自的全部后续推进转换
  都必须声明归属**；仅两分支共有的收尾动作保持共享不声明。
- 漏声明后果明示：另一分支子图被污染成环、相位链退化为枚举序。
- `add_trans` 签名与 §9 自查清单同步（含平行流程示例 t40/t44/t39）。

### 数据文件：`srs_data/pt_srsv12.py`

- 26 处结构化 `branch_values` 声明（能力验证 10 / 测量审核 16）：
  - 能力验证链：T-001/T-002/T-016/T-037 等；
  - 测量审核链：T-040/T-044/T-065/T-067 及报名记录/样品侧专属转换；
  - 共享收尾 T-039（发放结果报告和证书）不声明（真共享）。

---

## 二、遗留回归修复

- `context/generate_obligation_model.py` 三处（199/217/3071 行）
  `sys.exit(0)` → `sys.exit(2)`：fatal 路径必须非零退出，防止静默产出半截覆盖模型。

---

## 三、端到端验证（本包内已复跑通过）

运行链路（包根目录执行，LLM 可禁用走确定性路径）：

```bash
# P1.5 结构化导出
python3 -m srs_pipeline.cli srs_data.pt_srsv12 -o p1_review_structured.json
# P2 覆盖模型
python3 context/generate_obligation_model.py p1_review_structured.json coverage_model.json
# P3 规程编排（LLM_API_KEY 置空即走确定性标题兜底）
LLM_API_KEY='' python3 main.py coverage_model.json p3_output.json
```

验证结果（P1：0 error / 8 warning / 26 autofix；P2：exit 0，自检 8 项全 True；
P3：438 规程跑通）：

1. **伪变体消除**：E-XM.项目状态 全部单实例化 ——
   能力验证 T-001/T-002/T-016/T-037（bv=能力验证）、测量审核
   T-040/T-044/T-065/T-067（bv=测量审核）、共享 T-039。无任何 `[a]/[b]`
   生命周期伪变体（保留的 T-032/T-062/T-063 变体为同生命周期内真路径分歧，
   展开合法）。
2. **per-branch 相位链生效**：
   - 能力验证：待开始=0 → 报名中=1 → 进行中=2 → 报告审核中=3 → 已结束=4
   - 测量审核：报名中=0 → 待开始=1 → 进行中=2 → 报告审核中=3 → 已结束=4
   - 规程相位 basis 落在归属分支链（如 T-044 规程 basis=
     `dep_state_phase_map_by_branch.测量审核...待开始` = P1，不再是全局链 P0）。
3. **三症状消除**（对照 v12 基线 PROC-010/029/030 症状）：
   - T-001 规程为根（无依赖）；T-044 规程依赖 T-040（**同链**报名中创建者），
     不再重复/错位于 T-001 之后，也无 1→0 相位倒退；
   - T-044 规程 deps 不含能力验证链规程（guard5 跨链缺陷现场剔除，
     guard5_create_use×82）；
   - 两条链在共享收尾 T-039（已结束）汇合，依赖含双链前驱，语义正确。
4. **S3 分支感知剔除统计**（审计警告行）：
   `chain_ordering×10, guard1_state_pred×246, guard5_create_use×82, guard6_precond×32`。
5. **输出文件**：`verify_evidence/p2_coverage_model_v12_refactor.json`、
   `verify_evidence/p3_output_v12_refactor.json|.md`（多实例 `.1/.2` 为 S4
   实例展开，非分支变体）。

---

## 四、包内容

```
branch_lifecycle_refactor.zip
├── TestProduceGen/                        # 完整管线代码（含全部改造，可直接运行）
│   ├── nodes/s0_topology.py s3_dependency.py s1_generation.py ...
│   ├── context/generate_obligation_model.py（P2）
│   ├── srs_pipeline/{model.py, cli.py, glm5pr.md, ...}
│   ├── srs_data/pt_srsv12.py（数据：26 处 branch_values）
│   ├── main.py graph.py config.json ...
│   └── scripts/ tests/ tools/ verify/ ...
├── CHANGES_branch_lifecycle_refactor.md   # 本说明
└── verify_evidence/                       # 端到端验证产物（P1/P2/P3）
```

## 五、已知边界（非本次引入）

- P3 fallback 报告 1 起既有降级（s1.type5_special_ops.generic_fallback），
  与本次改造无关，属 P1 prompt 结构化字段让渡的遗留提示。
- `main.py` 引擎态快照未序列化 `dep_state_phase_map_by_branch`
  （功能已被 S3 消费，仅最终 JSON 审计视图缺该项；如需审计可在 es_keys 增补）。
