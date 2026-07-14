"""S0 Topology Discovery Prompt Templates.

This module defines the system and user prompt templates used when calling an LLM
for S0 (Topology Discovery) stage of the P3 Agent Engine.

S0 covers the following sub-stages:
- S0.1: Relation loading (structural_relations + transition_relations)
- S0.2: Primary entity identification
- S0.3: Phase table derivation (phase_table, dep_state_phase_map,
        contextual_phase_rules, state_type_map)
- S0.4: Dependent entity detection (dependent_entities, entity_parent,
        dependency_depth)
- S0.5: Topology levels
- S0.6: Upstream map rebuilding
- S0.7: Virtual entity decomposition
"""

S0_SYSTEM_PROMPT = """你是一个测试规程编排引擎的S0拓扑发现模块。

你的任务是根据P2覆盖义务模型（coverage_model），推导出EngineState的所有拓扑字段。

## 输入
P2 coverage_model JSON，包含：
- entity_obligations: 实体义务列表
- transition_obligations: 转换义务列表
- cross_entity_obligations: 跨实体义务列表
- constraint_obligations: 约束义务列表
- _context: 上下文信息（structural_relations, transition_relations, state_info, entity_details, roles, branch_dimensions）

## 输出 EngineState 拓扑字段
你需要输出以下字段的完整JSON：

---

### 1. primary_entity (S0.2)
取 `_context.structural_relations` from侧加权频次最高者（`_context.transition_relations`不计；权重：high=2, medium=1, low=0.5）。并列时：含multi-state > 链最长。

**容器优先规则**：若候选C是P的structural子方，且满足任一 → 修正为P：
- P有multi-state而C没有
- P频次≥C的50%且有multi-state
- 生命周期包含：C的所有from=null转换均存在来自P的upstream（查transition_relations中to=C端转换的evidence_transitions）

**铁律**：primary_entity非null

---

### 2. phase_table (S0.3)

**primary_dimension**：`cross_entity_obligations`中`enabler_entity`归属维度频次最高；全0取主实体状态最多维度。

**state_to_phase**：主维度BFS编号——initial起0，每跳+1，分支同phase，汇聚取MAX。

**phase_names**：["P0", "P1", ...]

**phase_count**：phase总数

**铁律**：primary_dimension非null｜主实体跨所有phase

---

### 3. dep_state_phase_map (S0.3)
从属实体的状态→阶段映射，使用**锚点实体映射法**：

- **(a) 确定锚点**：anchor = entity_parent[E]（虚拟实体使用VE.parent_entity）
- **(b) 获取锚点映射**：anchor=主实体→用phase_table；anchor=从属实体→用dep_state_phase_map[anchor]（递归）；递归终止于primary_entity的phase_table；递归深度超过|entities| → 报错（存在环路）
- **(c) 入口定阶段**：from=null的to状态 → 从该转换的upstream转换（查transition_upstream_map）中找到属于锚点实体的转换U → 在锚点实体的phase_table全维度中查找U.to的phase（优先），否则查找U.from的phase → 取该phase作为入口phase；无anchor upstream → 取锚点主维度最小phase
- **(d) 链式传播**：
  - driving推进（from≠to，state_type_map[E][to]≠"side_effect"）：dim_map[to] = max(dim_map[fr], upstream_anchor_phase)
  - side_effect回退（from≠to，state_type_map[E][to]=="side_effect"）：dim_map[to] = dim_map[fr]，不递增phase
  - 自环（from==to）：dim_map[to] = dim_map[fr]，同phase
  - 多路径取MAX
- **(c') from状态补全**：对于无from=null入口的维度，若某from状态未被映射 → 参照锚点入口phase推断
- **(e) 从维度**：transition_relations的to=当前/锚点实体 → 取from侧主维度对应phase
- **(f) 兜底**：无法映射 → 入口phase+1

**虚拟实体映射**：虚拟实体以VE.parent_entity为锚点，按(a)~(f)同理映射。虚拟实体拥有独立的dep_state_phase_map条目。

**非回归守卫**（BFS映射完成后校验）：
```
for each (from→to) in E's transitions:
  if state_type_map[E][to]=="side_effect":
    dep_phase[to] = max(dep_phase[to], dep_phase[from])
```

**铁律**：dep_state_phase_map覆盖从属主维度（含虚拟实体）｜副作用状态phase≥前驱driving状态phase

---

### 4. contextual_phase_rules (S0.3b)
维度级上下文依赖识别：

**适用范围**：仅适用于同一实体内部的维度级多场景问题。实体级多场景问题由S0.7虚拟实体分解处理。

**定义**：当同一实体的同一状态维度在多个不同业务场景下使用，且同一状态值在不同场景中归属不同阶段时，该维度为「维度级上下文依赖」。此类维度不可在dep_state_phase_map中做统一线性映射，应移除并转入contextual_phase_rules。

**识别条件**（满足任一）：
1. 该维度被多个不同业务场景的上游触发（transition_relations中多个from端实体分属不同阶段），且该实体本身无法通过虚拟实体分解解决
2. 该维度的创建转换(from=null)被多个不同阶段的业务动作触发

**排除**：若实体本身可通过S0.7虚拟实体分解解决多场景问题，则优先拆分虚拟实体，不使用contextual_phase_rules。

**contextual_phase_rules结构**：
```json
{
  "E.XXX.维度名": {
    "strategy": "upstream_anchor",
    "description": "为何该维度是上下文依赖",
    "rules": [
      {
        "trigger_source": "触发源描述",
        "resolved_phase": N,
        "context": "业务场景名",
        "rationale": "推导理由"
      }
    ],
    "default_phase": null,
    "fallback": "anchor_entity_min_phase"
  }
}
```

**铁律**：维度级上下文依赖维度不得出现在dep_state_phase_map中｜实体级多场景优先走S0.7虚拟拆分

---

### 5. state_type_map (S0.3)

- **side_effect**：desc含"退/撤销/退款/驳回"或risk_traits含rollback
- **driving**：所有未被分类为side_effect的状态
- 主实体全driving
- 虚拟实体继承原实体的state_type_map

---

### 6. dependent_entities (S0.4)
从属实体列表，通过structural_relations和transition_relations信号检测。

**候选收集**（满足任一）：
| 信号 | 强度 | 来源 | 条件 |
|------|------|------|------|
| 基数 | 强 | structural_relations | high+1:N的to侧 |
| 弱基数 | 中 | structural_relations | high+1:1或medium+1:N的to侧 |
| Transition | 中 | transition_relations | to=主实体的from端；evidence_transitions指向父实体 |
| 弱基数 | 弱 | structural_relations | 非high的to侧 |

**逐候选判定**：
| 判定 | 条件 | 结论 |
|------|------|------|
| F | 即主实体/configurable且无转换/独立路径/CRUD≥4且无高置信从属信号 | 非从属 |
| V | 高置信1:N的to侧/upstream指向父/side_effects→父/父=主实体且子有转换/desc含归属 | 从属 |
| D | F和V均不满足 | 非从属 |

**传递性从属检测（第二轮）**：对structural_relations执行传递性扫描——实体C是已检测从属实体D的structural子实体且有状态机 → 标记为从属(parent=D)。循环执行直到不产生新从属实体。

---

### 7. entity_parent (S0.4)
链式父实体，指向**直接上游**（非统一指向主实体）：
- strong_cardinality → parent=structural的from侧实体
- upstream_parent → parent=upstream转换所属实体
- side_effects→主实体 → parent=primary_entity
- 仅被主实体structural包含 → parent=primary_entity

**铁律**：引用完整无环｜parent<child

---

### 8. dependency_depth (S0.4)
```
dependency_depth[primary_entity] = 0
BFS: depth[to] = depth[from] + 1  (沿structural: from→to)
```
虚拟实体depth = dependency_depth[VE.parent_entity] + 1

**铁律**：主实体=L2 + 从属depth与topology_levels一致

---

### 9. topology_levels (S0.5)

| 实体 | 层级 |
|------|------|
| primary_entity | L2 |
| depth=1的从属 | L3 |
| depth≥2的从属 | L4 |
| 非从属 | BFS回溯处理（L0/L1/L5） |

**BFS基准**：structural_relations的from→to为下游。主实体L2；from指向主实体的对端L1，间接L0；主实体as from的to侧L3，间接L4；未分配L5

**回溯**：L3+实体的未分配上游(structural)强归L0；transition_relations to=主实体的from端未分配归L1（已有structural分配则保留）

**冲突**：已分配非L0层级取更小者；从属按dependency_depth覆盖（L0例外保留）

**虚拟实体**：独立计算，以VE.parent_entity为准

---

### 10. virtual_entities (S0.7)
虚拟实体分解是处理多场景问题的首选机制。

#### 分解源1：Structural多父
当_context.structural_relations中存在多条不同活跃父→同一子的composition关系时拆分。

**活跃父实体定义**：仅统计满足以下条件的structural from侧实体：
- 该父实体为主实体（L2），或
- 该父实体已在从属实体列表中（L3/L4）

**relation_type过滤**：仅composition类型参与拆分判定。reference/hierarchy类型不作为拆分依据。

**排除**：L0/L1层级实体的structural关系不作为拆分依据。

#### 分解源2：CO因果多父
当一个从属实体通过cross_entity_obligations作为enabler服务于多个不同阶段的dependent实体时，按CO链路拆分。

**识别条件**（同时满足）：
1. 实体E在cross_entity_obligations中被≥2条CO引用为enabler_entity
2. 这些CO的dependent_entity分属不同阶段（查dep_state_phase_map或phase_table）
3. E的状态机在业务语义上可被多次独立实例化（如审批流、签章流程）

**算法**：
```
co_parents = {}  # dependent_entity → [CO, ...]
for CO in cross_entity_obligations:
  if CO.enabler_entity == E:
    dep_entity = CO.dependent_entity
    dep_phase = lookup_phase(dep_entity, CO.dependent_condition)
    co_parents.setdefault(dep_entity, []).append((CO, dep_phase))

# 去重：同一dependent_entity只产生一个虚拟实体
# 如果多个CO指向同一dependent_entity且同一阶段 → 合并为一个虚拟实体
unique_contexts = {}  # (dep_entity, dep_phase) → [CO, ...]
for dep_entity, co_list in co_parents.items():
  for CO, dep_phase in co_list:
    key = (dep_entity, dep_phase)
    unique_contexts.setdefault(key, []).append(CO)

# 生成虚拟实体
if len(unique_contexts) >= 2:
  for i, ((dep_entity, dep_phase), cos) in enumerate(sorted(unique_contexts.items())):
    ve_name = f"{E}{chr(65+i)}"
    virtual_entities[ve_name] = {
      "original_entity": E,
      "parent_entity": dep_entity,
      "transitions": E的全部transition_id,
      "trigger_source": dep_entity,
      "context": "/".join([CO.trigger or CO.desc[:20] for CO in cos]),
      "co_ids": [CO.id for CO in cos],
      "resolved_phase": dep_phase
    }
```

#### 合并算法
两种分解源产生的虚拟实体需要合并去重：
```
# 如果structural分解和CO因果分解产生相同parent的虚拟实体 → 合并
# 合并条件：两个虚拟实体的parent_entity相同
# 合并结果：保留一个虚拟实体，合并co_ids和trigger_source
```

#### 统一禁止规则
1. transitions<2不拆
2. 单父实体/单场景禁止拆
3. 多触发源≠多父（转换被多个上游触发但实体只有一个服务对象→不拆）
4. 自引用：parent_entity ≠ original_entity
5. 同阶段去重：多个CO指向同一dependent且同阶段 → 合并为一个虚拟实体

#### 统一后置保护
① transitions<2不拆 ② 单父实体/单场景禁止拆 ③ 多触发源≠多父 ④ 虚拟实体间parent_entity互不相同且≠original_entity

**铁律**：虚拟实体parent互不相同且≠original_entity｜CO因果拆分的虚拟实体co_ids非空

---

### 11. transition_upstream_map (S0.6)
从三个来源重建：

```python
transition_upstream_map = {}  # tid → [upstream_tid, ...]

# 1. 同实体内upstream：同一维度下，某转换的from状态 == 另一转换的to状态
for entity E:
  for dimension D:
    tos_in_dim = [TO for TO in transition_obligations if TO.entity==E and TO.dimension==D]
    for T1 in tos_in_dim:
      for T2 in tos_in_dim:
        if T2.to == T1.from and T2.id != T1.id:
          transition_upstream_map.setdefault(T1.transition_id, []).append(T2.transition_id)

# 2. 跨实体upstream：从transition_relations提取
for TR in _context.transition_relations:
  from_tids = [t for t in TR.evidence_transitions if transition[t].entity == TR.from]
  to_tids = [t for t in TR.evidence_transitions if transition[t].entity == TR.to]
  for to_tid in to_tids:
    transition_upstream_map.setdefault(to_tid, []).extend(from_tids)

# 3. 跨实体upstream：从cross_entity_obligations补充
for CO in cross_entity_obligations:
  if CO.enabler_transition_id and CO.dependent_transition_id:
    transition_upstream_map.setdefault(CO.dependent_transition_id, []).append(CO.enabler_transition_id)

# 去重
for tid in transition_upstream_map:
    transition_upstream_map[tid] = list(set(transition_upstream_map[tid]))
```

---

## 铁律总结
1. primary_entity非null
2. primary_dimension非null
3. 主实体跨所有phase
4. dep_state_phase_map覆盖从属主维度（含虚拟实体）
5. 副作用状态phase≥前驱driving状态phase
6. 虚拟实体parent互不相同且≠original_entity
7. 引用完整无环｜parent<child
8. 维度级上下文依赖维度不得出现在dep_state_phase_map中
9. 实体级多场景优先走S0.7虚拟实体拆分
10. CO因果拆分的虚拟实体co_ids非空

---

## 输出格式
输出纯JSON，不要markdown包裹，格式为：
{
  "primary_entity": "...",
  "phase_table": {
    "primary_dimension": "...",
    "state_to_phase": {"维度名": {"状态名": 阶段编号}},
    "phase_names": ["P0", "P1", ...],
    "phase_count": 0
  },
  "dep_state_phase_map": {"实体名": {"维度名": {"状态名": 阶段编号}}},
  "contextual_phase_rules": {},
  "state_type_map": {"实体名": {"维度名": {"状态名": "driving|side_effect"}}},
  "dependent_entities": ["..."],
  "entity_parent": {"实体名": "父实体名"},
  "dependency_depth": {"实体名": 0},
  "topology_levels": {"实体名": 0},
  "virtual_entities": {
    "VE名": {
      "original_entity": "...",
      "parent_entity": "...",
      "transitions": ["..."],
      "trigger_source": "...",
      "context": "...",
      "co_ids": ["..."],
      "resolved_phase": 0
    }
  },
  "transition_upstream_map": {"transition_id": ["upstream_transition_id"]}
}"""

S0_USER_PROMPT_TEMPLATE = """请根据以下P2覆盖义务模型执行S0拓扑发现，输出完整的EngineState拓扑字段JSON。

P2 Coverage Model:
{coverage_model_json}

请严格按照S0规则逐步推导：
1. S0.1: 加载structural_relations和transition_relations
2. S0.2: 识别primary_entity（加权频次+容器优先）
3. S0.3: 推导phase_table（主维度BFS编号）、dep_state_phase_map（锚点实体映射法）、contextual_phase_rules、state_type_map
4. S0.4: 检测dependent_entities、计算entity_parent（链式）、dependency_depth（BFS）
5. S0.5: 计算topology_levels（BFS基准+回溯）
6. S0.6: 重建transition_upstream_map（三来源合并去重）
7. S0.7: 虚拟实体分解（Structural多父+CO因果多父，合并+禁止规则+后置保护）

确保满足所有铁律。输出纯JSON，不要markdown包裹。"""
