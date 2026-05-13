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