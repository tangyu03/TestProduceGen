p3_agent_engine/
├── __init__.py                     ← S0→S1→S2→S3→S4 五阶段
├── graph.py                        ← S4 阶段已加入流水线
├── main.py                         ← streaming输出 + 多实例汇总 + MD折叠
├── minV4.json                      ← 测试数据
│
├── models/
│   ├── __init__.py                 ← 相对导入 (.state, .schema)
│   ├── state.py                    ← AgentState TypedDict
│   └── schema.py                   ← Pydantic 模型
│
├── nodes/
│   ├── __init__.py                 ← 导出5个节点（含s4）
│   ├── s0_topology.py              ← 🔴 重写：全量确定性算法 + 动态映射
│   ├── s1_generation.py            ← 🔴 重写：动态映射 + I21/I22增强
│   ├── s2_sorting.py               ← 🟢 仅改import路径
│   ├── s3_dependency.py            ← 🔴 重写：I23时间守卫 + 环检测
│   └── s4_multi_instance.py        ← 🆕 新增：多实例扩展
│
├── prompts/
│   ├── __init__.py                 ← 相对导入
│   ├── s0_prompt.py                ← 无变化
│   └── s1_prompt.py                ← 无变化
│
└── tools/
    ├── __init__.py                 ← 已移除s0_compute引用
    ├── graph_algo.py               ← 小改：find_cycle替代simple_cycles
    └── llm_client.py               ← 仅加 from __future__




#结构化分析与覆盖义务建模脚本包

## 脚本清单

| 脚本 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `extract_docx.py` | 从源 docx 提取全文内容 | `upload/网数中心能力验证服务平台升级维护项目-歧义修正.docx` | `scripts/doc_content.txt` |
| `build_analysis.py` | P1 结构化分析引擎（Step 1-6） | `scripts/doc_content.txt`（人工对照） | `download/structured_analysis.json` |
| `build_obligations.py` | P2 覆盖义务建模引擎（Step 0-5） | `download/structured_analysis.json` | `download/obligation_coverage_model.json` |
| `doc_content.txt` | 源文档提取结果（供 build_analysis.py 参考） | - | - |

## 执行顺序

```bash
# 1. 提取源文档内容（如需重新提取）
python scripts/extract_docx.py

# 2. P1 结构化分析（生成 structured_analysis.json）
python scripts/build_analysis.py

# 3. P2 覆盖义务建模（生成 obligation_coverage_model.json）
python scripts/build_obligations.py
```

## 依赖

```bash
pip install python-docx
```

## 目录结构约定

```
my-project/
├── upload/                          # 源文档输入
│   └── 网数中心能力验证服务平台升级维护项目-歧义修正.docx
├── scripts/                         # 脚本目录
│   ├── extract_docx.py
│   ├── build_analysis.py
│   ├── build_obligations.py
│   └── doc_content.txt
└── download/                        # 产物输出
    ├── structured_analysis.json     # P1 产物
    └── obligation_coverage_model.json  # P2 产物
```

## 关键设计点

### P1 build_analysis.py
- Step 2.3 三元分类：配置来源 / 生命周期同步归属 / 事件触发归属
- Step 4.4 逆向路径捕获：终态语义约束（from 必须非终态）
- Step 6 校验12：composition 创建同步性校验（语义校验，非关键词扫描）
- Step 6 校验13：终态语义校验（from 不得为终态）

### P2 build_obligations.py
- Step 0 输入校验：9 个必须根节点
- Step 2.2 coverage_priority：终态语义感知（inferred+终态降级为 medium）
- Step 2.7 异常检测：终态→终态降级为 low
- Step 3.0a 统一门禁：G5 仅检查字段缺失，enabler_state 合法性由 (E,D,S) 统一处理
- Step 3.3 lifecycle 前置过滤：安全网①state_dimensions 空 + 安全网②preconditions 引用 enabler 后期状态
- Step 3.5 校验4：lifecycle 创建同步性复核
- 输出前 self_check：6 项结构化自检

## 字段命名规范

- P1 `business_rules.entities_involved`: 数组形式 `["E-XXX"]` 或 `["E-XXX", "E-YYY"]`
- P2 `RO-BR.entities_involved`: 数组形式（与 P1 字段名对齐）

## ID 命名规范

| 类型 | 前缀 | 序号格式 | 拆分后缀 |
|------|------|----------|----------|
| entity_obligations | `EO-ATC-` | NNN (3位零填充) | 无拆分 |
| transition_obligations | `T-` | NNN (沿用 P1) | `[a/b/c]` 无连字符 |
| cross_entity_obligations | `CO-` | NNN | `-a/-b` 有连字符 |
| constraint_obligations (IT) | `RO-IT-` | NNN | 无拆分 |
| constraint_obligations (BR) | `RO-BR-` | NNN | 无拆分 |
