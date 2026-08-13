# HANDOFF: primary_entity 疑似选错（E-USER vs E-CAR）

> **交接对象**：新 session 讨论「PT017 的 primary_entity = E-USER 是否选错」。
> **交接日期**：2026-08-13。分支 `V3`，未提交改动在工作区。
> **阅读前置**：本文件自包含；相关记忆 `[[topology-base-data-primary-gate]]`、`[[phase-basis-stage0-fix]]`、`[[causal-degree-primary-fix]]`、`[[s0-entry-phase-ref-not-text]]`。

> ⚠️ **状态：已于 2026-08-13 解决**。最终解法是 **causal 信号改度中心**（§8），
> 非本文件 §5 猜测的 struct 权重调整/降权。PT017 primary=E-CAR、review 保持 E-PLAN，
> 全套校验器 pass 0/0，PT017_output.json 已重生成（E-CAR）为新黄金基线。

---

## 1. 问题（用户原始疑问）

做完 **B+D（base-data-primary 门控）** 改造后，PT017 的 `primary_entity` **仍然选择 E-USER**，用户质疑：
- 载体 E-CAR 才是主业务流程（移交/留存/回收/外送）的状态机载体；
- E-USER 只是基础数据（用户），为什么成了主实体？
- B+D 改造是不是没生效 / 选错了？

reference 项目（review）的 `primary_entity = E-PLAN`（计划），与 PT017 的 E-USER 选择逻辑是否自洽也是待讨论点。

---

## 2. 已确认的事实

### 2.1 B+D 门控**不触及**主实体选择

`_compute_topology_levels`（`nodes/s0_topology.py`）里的 base-data-primary 门控，只在 **primary 已选定之后** 钉拓扑层（managed 主实体模式收敛 actor_action 启发式、E-CAR 钉到 level 2 等）。它**不是** E-USER 当选的原因。主实体选择完全由 `_identify_primary_entity` 决定。

### 2.2 主实体选择机制：5 信号融合（`nodes/s0_topology.py:330`）

v29 #19 多信号融合，权重：

| 信号 | 权重 | 含义 |
|---|---|---|
| `structural_driver_freq` | 0.20 | structural_relations **from-side** 频次 |
| `causal_driver_freq` | 0.25 | transition_relations **from-side**（因果链源头，权重最高） |
| `dependee_score` | 0.20 | structural_relations **to-side**（被依赖=主） |
| `lifecycle_completeness` | 0.20 | (has_initial + has_terminal + state_score + trans_score)/4 |
| `container_degree` | 0.15 | composition **from-side** 计数 |

另有 v28 保留的**容器优先 override**（父为容器且 multi-state 时上提）与 tie-break（multi_state、chain_length、crud 数、dim 数）。

### 2.3 为什么 E-USER 当选（上轮实测，lifecycle 修复**前**）

- **struct 信号**：E-USER 出现在 structural_relations from-side **10/18 条**引用边，得分最高——多数实体（角色/部门/用户/载体）都以 E-USER 为前置引用源。
- 融合分：**E-USER 0.700 vs E-CAR 0.600**。
- E-CAR 虽是 dependee（被 E-USER composition 拥有）且生命周期完整，但 struct 差距拉不开。
- 结论：**E-USER 靠 struct（from-side 引用密度）胜出**，不是 B+D 造成的。

### 2.4 lifecycle 信号曾是死代码（**本轮已修**）

- 原实现只读 `state_info[ent][dim]`（Layout A 形态）。本项目 state_info 是 **Layout B**（`{entity_name, dimensions:[...]}`），直读 `.items()` 迭代到的是 `entity_name`/`dimensions` 键 → `state_count` 恒 0、无 initial/terminal → **全实体 lifecycle 信号恒 0.25 平坦**，完全不参与判别。
- 已改为 `_normalize_dim_list()` 统一归一（`nodes/s0_topology.py:437-447`）。
- 修复后主实体**仍为 E-USER**（引擎状态与基线零 diff 证明——见 §4）。

### 2.5 修复后各实体融合分（实测，本轮捕获）

`_identify_primary_entity` 返回前临时打点（stderr `[FUSION]`，已捕获后删除）。PT017：

| 实体 | struct | causal | dependee | lifecycle | container | **fusion** |
|---|---|---|---|---|---|---|
| **E-USER** | **1.000** | 1.000 | 1.000 | 0.667 | 0.000 | **0.783** |
| E-CAR | 0.500 | 1.000 | 1.000 | 1.000 | 0.000 | **0.750** |
| E-TRF / E-RET / E-RCY / E-OUT / E-ARC | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.650 |
| E-REG | 0.100 | 1.000 | 0.500 | 1.000 | 0.000 | 0.570 |
| E-IMP / E-EXP / E-SCN | 0.000 | 0.000 | 0.500 | 1.000 | 0.000 | 0.300 |
| E-ROLE / E-DEPT | 0.100 | 0.000 | 0.000 | 0.000 | 0.000 | 0.020 |

**关键发现（直接支撑"选错"讨论）**：
- **lifecycle 死代码修复把 E-CAR 从 0.600 拉高到 0.750，差距从 0.100 缩到 0.033**——只剩一个信号在撑：
  - E-USER 唯一优势 = `struct=1.000 vs 0.500`（from-side 引用密度），折算 0.20×0.5 = **+0.10**；
  - E-USER 的 lifecycle 反而更弱（0.667 vs 1.000，缺 terminal 完整度），折算 0.20×0.333 = **−0.067**；
  - 净优势 = **+0.033**。
- 若 struct 信号权重/判据有任何调整，或引入"主流程密度"轴，**E-CAR 即刻反超**。
- `container` 全部 0.000 → v28 容器优先 override 在本项目无作用（composition 未从 from-side 计到）。
- 其余业务载体（TRF/RET/RCY/OUT/ARC）同分 0.650，全生命周期完整，只缺 struct。
- 上轮"0.700 vs 0.600"是 **lifecycle 修复前**的旧数；本表为修复后现状。

---

## 3. 本轮已完成的代码修复（`nodes/s0_topology.py`）

目标：消灭 **Layout-A-only 读 state_info**（对 Layout B 数据静默退化）。全部改为 `dimensions` 字段 + `_normalize_dim_list` 归一。

| 位置 | 内容 |
|---|---|
| `_identify_primary_entity` lifecycle 循环 (:437) | 死代码修复（见 §2.4） |
| `_derive_phase_table` `declared_initial_state` (:913) | Layout B 读不到 initial → 归一 |
| `_derive_phase_table` `_primary_terminals` (:990) | 同上 |
| `_derive_phase_table` state_order Spot 1 (:1015) | 回归边剔除(G0.3/I14)用的 state_order |
| `_derive_phase_table` state_order Spot 2 (:1107) | **cycle 背边检测**（环形主状态机空序退化） |
| `_derive_dep_state_phase_map` `_dim_terminals` (:1871) | toggle/副作用边判据 |
| `_derive_dep_state_phase_map` `terminal_states` (:1923) | 跨阶段 +1 判据 |
| `_derive_dep_state_phase_map` `si_dim_sub` (:2083) | 子状态机 initial 并入 |
| `_derive_dep_state_phase_map` `si initial` (:2277) + `si_term_states` (:2295) | 回填 P0 / 终态锚点 |

> 说明：本轮这 7 处 + 上轮 3 处（lifecycle、2×state_order）对**当前两个黄金项目是行为中性的**（engine_state 零 diff）——是潜伏 bug 修正，不改变现输出。它们只有在其它 Layout B 项目里这些读值真正影响结果时才显现价值。`_detect_leaf_entities` / `_build_state_pos` 是 **Layout-B 向**读（当前数据形态下正确），不在本类修复内。

---

## 4. 回归验证（全部通过）

- **PT017**：`python scripts/engine_state_ab.py <fresh> PT017_output.json` → **12/12 字段 0 diff**。
- **review**：同上 vs `output.json` → **12/12 字段 0 diff**。
- **确定性**：`PYTHONHASHSEED` 默认 vs 999 双跑，engine_state canonical SHA-256 **MATCH**（`4ce863aa…`）。
- `py_compile nodes/s0_topology.py` OK。
- 新增 A/B 脚本：`scripts/engine_state_ab.py`（12 字段，`leaf_entity_ids` 排序化比较）。

---

## 5. 开放问题（新 session 讨论核心）

1. **业务判据**：E-USER 作为 primary 是否成立？"选错"的判定标准是什么——业务语义（主流程状态机=E-CAR）还是结构信号（引用密度=E-USER）？需要用户给出期望主实体的判据。
2. **权重质疑**：`structural_driver_freq`(0.20) 从 from-side 计频，天然偏向**基础数据提供方/被引用前置**（E-USER/部门/角色），是否应降权或改判据？
3. **缺"流程密度"信号**：主实体是否应是承载最多 transition / 最完整流转链的实体（E-CAR 载体状态机）？当前 5 信号没有显式"主流程"轴。
4. **跨项目自洽**：review 项目 primary=E-PLAN（也是业务主数据），与 PT017=E-USER 是否逻辑自洽？两者选择轨迹需对比。
5. **若改选 E-CAR 的影响面**（需 A/B 量化）：S1 阶段锚定、跨实体前置（C04 镜像）、dep_state_phase_map、S2 排序、C05 分支维度穿透都会变。改主实体会牵连多少输出。
6. **B+D 语义回顾**：门控把 E-CAR 钉到 level 2（依赖主实体）、E-USER 在 level 0——这是"主实体=基础数据"的刻意设计还是掩盖了选错？

---

## 6. 复现与调试

```bash
# 全量跑（S0 确定性，S1 LLM 出标题）
python main.py PT017_coverage_obligations.json <out.json>
python main.py coverage_obligations.json <out.json>

# A/B 引擎状态（12 字段，leaf_entity_ids 排序化）
python scripts/engine_state_ab.py <fresh.json> PT017_output.json

# 确定性双跑
PYTHONHASHSEED=999 python main.py PT017_coverage_obligations.json <out2.json>

# 看 5 信号明细：s0_topology.py _identify_primary_entity 返回前
# 有临时 [FUSION] 调试 print（stderr），捕获后删除。
```

输入/基线：
- `PT017_coverage_obligations.json` / `PT017_output.json`（黄金基线，工作区更新未提交）
- `coverage_obligations.json` / `output.json`

---

## 7. 工作区状态提醒

- 本轮全部修复（§3）+ 之前 session 的 B+D 门控、C18-C23 校验器等 **28+ 文件改动均在工作区未 commit**（`git status` 可见）。
- `scripts/engine_state_ab.py` 为新增。
- `.ab_tmp/` 为 A/B 临时产物，可清理。

---

## 8. 已解决（2026-08-13）：causal 度中心修复

§5 开放问题 1/2/3/4 已回答，问题判定为**选错**，最终方案 = **causal 信号改度中心**。

### 8.1 为什么 §5 猜测的 struct 调整不成立

实测候选方案 `struct-filter`（排除 `configuration_source` 边）**在真代码上失败**：
PT017 全部 18 条 struct 边都是 `configuration_source`，过滤后 struct 信号归零，
任意任务实体（E-RET）当选，比 E-USER 更糟。真判别力不在 struct，在 **causal 图**：
E-CAR 是 6 条 task→CAR 因果边的汇点，而 from-only 计频对汇点平坦（所有实体 1 边同分）。

### 8.2 落地的三处改动（`nodes/s0_topology.py`）

| # | 位置 | 内容 |
|---|---|---|
| 1 | `_identify_primary_entity` Signal 2 | `causal_driver_freq` 从 **from-only** 改 **度中心**（from + to 各计，自环一次）= 因果图中心 = 业务流载体。PT017→E-CAR(6进+1出)，review→E-PLAN(2出+1进) |
| 2 | `_detect_dependent_entities` Step 2 | transition 信号升级：`t==primary` 的因果边是强依赖证据，`_signal_rank('transition')>=_signal_rank(existing)` 覆盖弱 struct medium（原 `f not in signal_strength` 被 E-CAR→ARC 已填的 medium 挡住） |
| 3 | 同函数 Step 3 F/V/D | CRUD≥4 排除豁免 `transition` 信号：CRUD 多的流程驱动者（载体归档任务）仍判 V |

### 8.3 下游塌陷的根因与修复

primary 从基础数据（E-USER）翻成受管实体（E-CAR）后，`_detect_dependent_entities`
曾有 760→463 proc 塌陷：Step 2 守卫挡住 transition 信号 + CRUD≥4 排除过滤掉全部载体任务 →
无传递种子 → dependent=[]。上述改动 2/3 修复后 **681 procs**（只剔 79 个无信号冗余）。

### 8.4 验证（全部通过）

- **PT017**：primary=E-CAR，dependent=`[E-ARC,E-TRF,E-RET,E-RCY,E-OUT,E-REG]` 全 parent=E-CAR；681 procs，0 source_ids 丢失，0 error，53 BRs 保留。
- **review**：primary 保持 E-PLAN，全量 pipeline（procs + engine_state）与改前**逐字节相同** = 中性。
- **校验器**：`verify/validators.py` v01-v10 → **pass 0 blocker 0 warning**；V10 TO 91/91、EO 89/89、BR 53/53、IT 4/4、state_misses=0；dedup_ratio 1.0。
- **确定性**：`scripts/s1_fix_replay.py --recompute-s0` 双跑 SHA-256 MATCH。
- **回归**：`regression_baseline.py` 10/10。
- **黄金基线**：`PT017_output.json` / `.md` 已重生成（E-CAR）。

### 8.5 遗留（非本次修复引入）

- **review `output.json` V10 fail=3**（本地未跟踪产物，改前已逐字节相同）：缺
  T-013 / EO-CRU-001 / EO-CRU-026 / RO-IT-001 —— review 项目基线未随当前代码再生的历史欠账，单独立项处理。
- §5 开放问题 5（改选影响面）已由校验器 0/0 + V10 全覆盖实证回答：S1 锚定/C04 镜像/S2 排序/C05 分支维度均无违规。
- §5 开放问题 6（B+D 语义）：E-CAR 钉 level 2、E-USER 在 level 0 的"主实体=基础数据"设计本身是**选错的表现**，非刻意——本轮已修正为 E-CAR。
