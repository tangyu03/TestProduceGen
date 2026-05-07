p3_agent_engine/
├── main.py                 # 1. 运行入口 (极简)
├── graph.py                # 2. 流水线编排 (LangGraph 状态机定义)
├── models/                 # 3. 数据与状态契约
│   ├── __init__.py
│   ├── state.py            # AgentState 全局状态池定义
│   └── schema.py           # Pydantic 强校验模型 (守卫不变量)
├── nodes/                  # 4. LangGraph 节点实现 (大脑决策层)
│   ├── __init__.py
│   ├── s0_topology.py      # S0: 拓扑发现节点
│   ├── s1_generation.py    # S1: 规程生成与校验节点
│   ├── s2_sorting.py       # S2: 排序节点
│   └── s3_dependency.py    # S3: 依赖绑定节点
├── tools/                  # 5. 确定性工具集 (外脑计算层)
│   ├── __init__.py
│   ├── graph_algo.py       # NetworkX 图算法封装 (环检测/拓扑排序)
│   └── llm_client.py       # 智谱 GLM 调用封装
└── prompts/                # 6. Prompt 模板 (知识库)
    ├── __init__.py
    ├── s0_prompt.py
    └── s1_prompt.py