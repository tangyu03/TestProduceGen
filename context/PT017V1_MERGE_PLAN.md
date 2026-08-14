# MERGE PLAN: V1 二级审批用例 移植进 CASC-STEC-PT017.py

> **目标**：把 `srs_data/CASC-STEC-PT017V1.py`（补充文件）中缺失的 **二级审批** 内容移植进
> `srs_data/CASC-STEC-PT017.py`（基础文件），用 PT017.py 的字段风格，补回黄金基线结构性缺失的
> **二级审批员 actor**。同时修复 PT017.py 当前无法 assemble 的输入契约违约。
> **交接日期**：2026-08-14。分支 `V3`。
> **前置阅读**：`[[output-entity-is-chinese-name]]`、`[[constraint-parser-no-name-hardcode]]`、
> `[[v10-coverage-obligation-granularity]]`、`[[validator-no-project-fallback]]`、
> `[[render-labels-registry]]`。

---

## 0. 结论摘要

| 项 | 结论 |
|---|---|
| 黄金缺什么 | `PT017_coverage_obligations.json` 91 条 TO 的 role 集合 **无 二级审批员**（普通用户30/一级审批员36/载体管理员16/system6/系统管理员3）；C级靠 branch-split 拆出但两路 role 都是一级审批员 |
| 谁补 | **只有 V1** 有 `role="二级审批员"` 的转换（18 次）+ `待二级审批` 状态（108 次引用） |
| op note.role | **必须带**（C18 强制）。PT017.py 84 条 op 全缺 role → **84 条 C18 error**，`assemble()` 抛 CriticalAmbiguity |
| 附带发现 | PT017.py t02 的 note 引用 `t02b`（不存在）→ **1 条 C21 error**。补上 t02b/t02c/t03b 后 C21 自动消失 |
| 现状 | 两个 .py（PT017.py 85 errors / V1 add_role 1-arg 无法 build）**当前都无法 assemble**；黄金 P2/P3 是旧产物 |

---

## 1. 现状（实测证据，2026-08-14）

### 1.1 输入契约违约

`python -c "…build() + Validator.run_all()"`：

| 文件 | errors | 构成 |
|---|---|---|
| `srs_data/CASC-STEC-PT017.py` | **85** | C18×84（op 缺 note.role）+ C21×1（t02 note 引用局部标签 `t02b` 不存在） |
| `srs_data/CASC-STEC-PT017V1.py` | 无法 build | `add_role("系统管理员")` 1-arg，model.py:146 需 2 参 `(id, name)` |

- `model.assemble()`（model.py:316）在 `report.errors` 非空时 `raise CriticalAmbiguity` → 两个 .py 当前都过不了 assemble。
- 黄金 `PT017_structured.json`（P1）仍含 op note.role（行 2670 等）→ 它比 .py 新，是 **C18 加入前的旧产物**。

### 1.2 C18 判据（`srs_pipeline/validate.py:489`）

```python
declared = {r["name"] for r in self.m.roles} | set(RESERVED_ROLES)
# note.role：单角色 str 或多角色 list；逐一命中 declared 才通过
```
- PT017.py 用 2 参 `add_role("r01","系统管理员")`…（行 45-52），**r04 = 二级审批员 已声明**（行 48）+ 权限 `["查询待审批任务"]`（行 72）→ 无需新增角色。
- C18 按 **name** 校验，V1 的 `note={"role":"普通用户"}` 与 PT017 的 add_role name 完全兼容。

### 1.3 黄金的结构性缺失（坐实"丢失二级用例"）

- 91 条 TO：`二级审批员` 0 次。
- 18 个 transition_splits（T-002[a]/[b]…T-050/051）：C级拆出但 **两路 role 都是一级审批员**。
- 输出层 `PT017_output.json`：二级审批员 6 次出现全是描述性文本（E-ROLE BR-031 角色管理 + branch_dimension desc "C级需经过二级审批员审批通过后进入待执行"），**没有一条以二级审批员为 actor 的用例**。

---

## 2. 移植内容（四步）

> V1 与 PT017.py 的 op 名集合**逐字一致**（各 84 条，差集为空）→ 所有回填/移植可按名 1:1 映射。
> PT017.py 各任务实体基址 tid 与 V1 完全对齐：E-IMP t01-06、E-REG t07-12、E-ARC t13-18、
> E-TRF t19-24、E-RET t25-30、E-RCY t31-36、E-OUT t37-42、E-EXP t43-48、E-SCN t49-54。

### Step A —— op note.role 回填（修 C18×84）

- **对象**：PT017.py 全部 84 条 `op(...)`，现 `note={"comment": …}` 无 role。
- **做法**：按 op 名从 V1 取 role 值，合并进现 note dict（保留现有 comment）：
  `note={"role": <V1 值>, "comment": <保留现注释>}`。
- V1 role 值分布（84/84 全覆盖）：`普通用户`×59、`[普通用户, 监督员]`×9、
  `[普通用户, 载体管理员]`×1、`系统管理员`×11、`[日志管理员, 角色管理员]`×2、`日志管理员`×2。
- 校验：C18 会逐条对照 `r01-r08` 的 name —— 以上值全部命中。

### Step B —— 待二级审批 状态（9 任务实体维度）

- **对象**：E-IMP/E-REG/E-ARC/E-TRF/E-RET/E-RCY/E-OUT/E-EXP/E-SCN 的 `任务状态` dimension（PT017.py 行 116/181/236/292/349/404/460/523/583 附近，9 处）。
- **改法**（每处）：
  - `states` 列表：`"待审批", "审批通过", …` → `"待审批", "待二级审批", "审批通过", …`（插在 待审批 与 审批通过 之间）。
  - `inferred` 列表：`["草稿", "待审批", "待执行", "已完成"]` → 加 `"待二级审批"`。
- **不动**：`initial="草稿"`、`terminal=["审批拒绝","已完成"]`。
- 依据：4.5.2/4.6.2/…/4.13.2 "C级需经过二级审批"（branch_dimension evidence 已含此句）。

### Step C —— 27 条二级转换 + t02 收窄（补用例 + 修 C21×1）

**C.1 每实体新增 3 条转换**（表：X=基础通过 tid，Y=基础拒绝 tid）：

| 实体 | 新 tid 组 | 待审批→待二级审批 | 待二级审批→审批通过 | 待二级审批→审批拒绝 | source_ref |
|---|---|---|---|---|---|
| E-IMP | t02b / t02c / t03b | t02b | t02c | t03b | 4.5.2 |
| E-REG | t08b / t08c / t09b | t08b | t08c | t09b | 4.6.2 |
| E-ARC | t14b / t14c / t15b | t14b | t14c | t15b | 4.7.2 |
| E-TRF | t20b / t20c / t21b | t20b | t20c | t21b | 4.8.2 |
| E-RET | t26b / t26c / t27b | t26b | t26c | t27b | 4.9.2 |
| E-RCY | t32b / t32c / t33b | t32b | t32c | t33b | 4.10.2 |
| E-OUT | t38b / t38c / t39b | t38b | t38c | t39b | 4.11.2 |
| E-EXP | t44b / t44c / t45b | t44b | t44c | t45b | 4.12.2 |
| E-SCN | t50b / t50c / t51b | t50b | t50c | t51b | 4.13.2 |

每条模板（对齐 V1，转成 PT017 风格）：

```python
m.add_trans(
    tid="<X>b",            # 待审批 → 待二级审批
    entity="<ENT>", dimension="任务状态",
    frm="待审批", to="待二级审批",
    action="一级审批通过（C级送二级）",
    role="一级审批员",
    preconditions=[
        precond(text="<实体中文名>任务处于待审批状态", ptype="state_ref",
                ref=state_ref("<ENT>", "任务状态", "待审批")),
        precond(text="任务级别为C级", ptype="constraint", ref=None),
    ],
    expected_results=["若任务级别=C级，则一级审批员通过后任务进入待二级审批状态，待二级审批员审批"],
    traits=["branch"],
    direction="forward", priority="P0",
    source_ref="<对应节>",
    note={"branch_dimension": "任务级别",
          "comment": "direction: 待审批在 states 先于待二级审批，判 forward；C级一级审批通过送二级路径"},
)
# <X>c：frm=待二级审批 → to=审批通过, action=二级审批通过, role=二级审批员,
#        precond state_ref(待二级审批)+任务级别为C级, forward/P0/branch,
#        expected_results="…二级审批员通过后…任务状态变为审批通过"
# <Y>b：frm=待二级审批 → to=审批拒绝, action=二级审批拒绝, role=二级审批员,
#        precond state_ref(待二级审批)+任务级别为C级, lateral/P1/branch,
#        expected_results="…C级且二级审批员拒绝，则…任务终止…"
```

**C.2 收窄基础通过转换 t02**（9 实体 × 同款）：

- PT017.py t02 precond `任务级别为B级或C级` → **`任务级别为B级`**（否则 C级出现 待审批→审批通过 直通 与 待审批→待二级审批 双路径冲突）。
- note comment 更新为 `"B级一级审批员通过；C级需二级审批员（t02b→t02c）"` —— 该 comment 已引用 t02b，**补上转换后 C21×1 自动消失**。
- **t03 不动**：现 precond `任务级别为B级或C级` 覆盖 B/C 级一级审批员的 待审批 阶段拒绝，与 V1 t03（无级别约束 + comment "B/C 级适用"）语义一致。

**C.3 branch_dimension 联动**（PT017.py 行 910）：

- `{"value": "C级", "target_transition": "二级审批通过转换", …}` —— 该描述性名称现在指向真实存在的 t02c（action=二级审批通过），**无需改动**，移植后自动解析。

### Step D —— 角色/权限确认

- `r04 二级审批员` 已声明（行 48）+ `add_permission("二级审批员", ["查询待审批任务"])`（行 72）→ **零新增**。
- V1 的 `m.add_permission("二级审批员", […])` 仅含"查询待审批任务"，与 PT017 一致，无需补。

---

## 3. 排除项（V1 旧建模，不移植）

| V1 内容 | 为何不移植 |
|---|---|
| `add_role("系统管理员")` 1-arg（行 48-55） | 违约 model.py:146 签名；PT017 2 参风格保留 |
| E-CAR states `[已登记,已归档,已移交,已留存,已回收,已外送]` terminal `[已归档,已回收]` + t56 已移交/t57 已留存 | 已落地决策：移交/留存是**属性级操作非状态**（见 `[[carrier-state-operations-vs-states]]`）；PT017 E-CAR 建模保持 |
| 11 个 prohibit_keywords | PT017 已收敛为 3 个（领域无关原则）；不引入项目词汇硬编码 |
| `composition` / `business_ownership` struct 边 | PT017 全部 18 条 struct 边为 `reference`+`configuration_source`；V1 边型会扰动 S0 结构信号（主实体选择已定 E-CAR） |
| add_xc 用 `category="precondition", type="state"` | 与 model.py:194-210 strict 契约不符；PT017 用 `target_condition="状态=已登记"` 风格 |
| 6 条 add_invalid（i01-i06） | PT017 已有 4 条（i03-i06）；i01/i02 关联 V1 旧建模 |
| 逐状态 dict 风格 `{"value":"草稿","inferred":True,"note":…}` | 转成 PT017 维度级 `inferred` list + `note` dict 风格 |

---

## 4. 移植后连锁（黄金重生成）

移植后 PT017.py 可 assemble → 整链重生成（P2/P3 基线将**有意变化**，正是补回二级用例）：

```bash
# 1) P1：重新 assemble（此前因 C18/C21 卡死）
python -m srs_pipeline.cli srs_data.CASC-STEC-PT017 -o PT017_structured.json --strict

# 2) P2：重生成 coverage obligations（TO 数将 +27 二级转换，split 结构变化）
python context/generate_obligation_model.py PT017_structured.json PT017_coverage_obligations.json

# 3) P3：重生成输出
python main.py PT017_coverage_obligations.json PT017_output.json

# 4) 确定性双跑 + 引擎状态 A/B
PYTHONHASHSEED=999 python main.py PT017_coverage_obligations.json PT017_output.det.json
python scripts/engine_state_ab.py <fresh.json> PT017_output.json

# 5) 输出级校验器 v01-v10
python -m verify.validators …
```

**预期变化**（需重新验证，不是零 diff）：
- transition_obligations：新增 27 条（t02b/t02c/t03b…），**role=二级审批员 首次进入 TO 层**；
- transition_splits：18 个拆分结构改变（t02 收窄为 B级 单值，C级 由 t02b→t02c 链承载，不再靠拆）；
- V10 覆盖矩阵、EO/BR/IT 计数需按新基线重校；
- E-ROLE BR-031 文本、branch_dimension desc 不变（描述性文本与 actor 用例解耦）。

---

## 5. 验证清单

1. `py_compile srs_data/CASC-STEC-PT017.py` OK。
2. assemble 通过：C1-C23 全绿（尤其 **C18×84 归零**、**C21×1 归零**）。
3. P2 生成：TO 数 = 73 基础 + 27 二级 = **100**；split 结构含 二级审批员 角色。
4. P3 输出：`engine_state_ab.py` 12/12 0 diff（对新基线）；确定性 SHA-256 MATCH。
5. 校验器 v01-v10 pass 0 blocker 0 warning；V10 覆盖 100% 无 state_misses。
6. review 项目（struct_srs.py）回归 **零变化**（本移植不动通用代码，仅改 srs_data 数据模块）。

---

## 6. 待确认

1. **黄金重生成是否本次就做**：移植后若不同步重生成 P2/P3 基线，仓库会出现"数据文件新、基线旧"的中间态。建议移植+重生成+重校验一步到位，但重生成会让 `PT017_coverage_obligations.json` 不再与旧基线逐字节一致 —— 需用户确认接受。
2. **op note.role 合并方式**：保留 PT017 现有 `note.comment`、仅补 `role`（推荐）；还是完全照 V1 的 note？现有 comment 含 crud 回填引用（C12 相关），建议保留。
3. **t02 收窄 B级** 语义确认：C级 一级审批员 只有 通过→待二级审批 / 拒绝→终止 两条路（无 C级一级直通 审批通过），与 4.5.2 "C级需经过二级审批" 一致。
