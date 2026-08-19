
框架侧配套清单相应更新为：`validate_llm` 入口对 `xc_source="镜像"` 直接报错（LLM 通道关闭的唯一守门）；source_ref 章节号与原文目录 ∪ 处置表“不适用”章的双向差集；其余校验（op 全局唯一、词表定位、BR 承载含字面量、direction 词族一致、穿透逐值覆盖、signal_type 方向性）与此前约定相同。这套 prompt 交付后，如果跑一轮新文档仍有框架侧拦截不到的遗漏类型，那就是下一轮让渡的候选——按“让渡后必清除”的节奏继续收敛即可。

## **两点必须配套落实的说明**

这份 prompt 变薄成立的前提是框架接住让渡出去的职责，否则部分规则会悬空。`srs_pipeline` 侧需同步实现的最小集：**派生器**（遍历全部 precond 的跨实体 state_ref 生成镜像 XC，source_transition 由框架反查）；**对账校验**（op 名称全局唯一、章节处置表覆盖率与产物对应、prohibit_keywords 短语可被 source_ref 定位、每条 branch_dimension 有 BR 承载且 desc 含分支值字面量、direction 自报词与取值同族、分支转换 expected_results 覆盖全部 values、signal_type 与 desc 关键词方向性一致）；**歧义收集**（汇总 note.ambiguity 输出供人工仲裁）。这些都是纯机械检查，几十行量级。

另外按此前结论执行了两处纪律：没有为 category/signal_type 串位加专门提醒（schema 已对该类错误 100% 拦截，示例中的正确配对足以示范）；没有把"证据从严"写成新清单，而是并入既有判定（IT 仅文档明确禁止、因果排除流程表并排依据、状态枚举以状态分析表为权威、禁止重排 states），保持规则总量净减。



### **框架侧配套校验清单（prompt 之外，srs_pipeline 实现）**

此版本 prompt 的生效依赖以下框架校验与派生器同步实现。按优先级排列：

| 编号 | 类型 | 项 | 说明 |
|---|---|---|---|
| C-1 | 校验 | 角色覆盖 | `add_role` 中 `readonly=False` 的角色在 `transitions.role` 出现 0 次 → 报警不中断，由 LLM 裁决补转换或标 readonly |
| C-2 | 校验 | 注释标签引用 | 扫描全部 note/comment 中匹配 `[txbi]\d+[a-z]?` 的局部标签，被引用者必须有对应产物；承诺未兑现即报错 |
| C-3 | 校验 | 分支值覆盖 | 每个分支维度的每个 value，出现在 ≥1 条转换的 **precondition 文本或 expected_results 若句式**中（旧版"逐值若句式"校验废止） |
| C-4 | 校验 | 分支穿透型判 | 路径分歧型转换的 `role` 取值互不相同、precondition 含分支值 constraint；结果差异型所有 value 共用同一转换、role 单值 |
| C-5 | 派生 | 镜像 XC | 框架遍历 preconditions 中的跨实体 state_ref，自动派生镜像 XC，`validate_llm` 入口对 `xc_source="镜像"` 直接报错（LLM 通道关闭） |
| C-6 | 校验 | source_ref 差集 | 产物 source_ref 章节号与原文目录 ∪ 处置表"不适用"章的双向差集，缺口报警 |
| C-7 | 校验 | direction 词族一致性 | direction note 中的语义描述词（回退/主线外/恢复）与 direction 取值同族，冲突即报错 |
| C-8 | 校验 | BR 承载含字面量 | 每条 `note.branch_dimension` 对应的 BR，desc 含分支值字面量 |
| C-9 | 校验 | signal_type 方向性 | `signal_type=restrictive` 时 desc 含"必须/不得/仅当/禁止"关键词；`signal_type=display` 时 desc 含"显示/展示/页面提示"——关键词方向性不匹配时报警告 |
| C-10 | 校验 | op 名称全局唯一 | 全部产物的 op name 跨实体唯一，重复即报错 |

C-1/C-2/C-3/C-4 是此次 badcase 修复的直接产物（角色覆盖、注释标签、分支值覆盖、型判合规），其余为之前已商定的延续项。C-1/C-2 是 badcase 场景的最后防线——即使正路径失手，这两条必捕捉到二级审批员悬空与 t02b 注释承诺未兑现，触发回看修复。



### **框架侧配套校验清单（prompt 之外，srs_pipeline 实现）**

| 编号 | 类型 | 项 | 说明 |
|---|---|---|---|
| C-1 | 校验 | 角色覆盖 | `add_role` 中 `readonly=False` 的角色在 `transitions.role` 出现 0 次 → 报警不中断，由 LLM 裁决补转换或标 readonly |
| C-2 | 校验 | 注释标签引用 | 扫描全部 note/comment 中匹配 `[txbi]\d+[a-z]?` 的局部标签，被引用者必须有对应产物；承诺未兑现即报错 |
| C-3 | 校验 | 分支值覆盖（双通道） | 该维度**存在** branch 转换时：每个 value 须被 ≥1 条转换的 precondition 字面量或 expected_results 若句式覆盖；该维度**无** branch 转换时：须有 ≥1 条 BR 的 desc 含分支值字面量，且 impact_scope 注明纯计算型。两通道字面量均可机械检查 |
| C-4 | 校验 | 分支穿透型判一致性 | 同维度 branch 转换组内 frm/to/role 与分支值对应一致（每个分支值对应的结构字段组合唯一）；共用转换的 expected_results 若句式覆盖该转换涉及的全部 values |
| C-5 | 派生 | 镜像 XC | 框架遍历 preconditions 中的跨实体 state_ref 自动派生镜像 XC，`validate_llm` 入口对 `xc_source="镜像"` 直接报错（LLM 通道关闭） |
| C-6 | 校验 | source_ref 差集 | 产物 source_ref 章节号与原文目录 ∪ 处置表"不适用"章的双向差集，缺口报警 |
| C-7 | 校验 | direction 词族一致性 | direction note 中的语义描述词与取值同族，冲突即报错 |
| C-8 | 校验 | BR 承载含字面量 | 每条 `note.branch_dimension` 对应的 BR，desc 含分支值字面量 |
| C-9 | 校验 | signal_type 方向性 | restrictive ↔ desc 含"必须/不得/仅当/禁止"类词、display ↔ desc 含"显示/展示/页面提示"——不匹配报警告 |
| C-10 | 校验 | op 名称全局唯一 | 全部产物的 op name 跨实体唯一，重复即报错 |

本版相对上一版的三处实质变更：其一，穿透判型从“路径分歧/结果差异”业务二分改为**分立型/共用型结构字段比较**（frm/to/role 任一不同即分立，全同仅结果差异才共用），删除了不可操作的动作集判据，新增纯计算型分支的合法出口；其二，4.2 判定表插入“分支维度取值条件”行，修补了穿透落盘与 precondition 归类的接口裂缝，降级理由条款同步豁免该行；其三，C-3 重设计为双通道（有 branch 转换走转换层字面量覆盖、无 branch 转换走 BR 层字面量＋impact_scope 注明），消除了原设计对纯计算分支的强制凑数诱导；C-4 相应改为结构字段组合唯一性检查。示例与 §9 检查清单已同步换用“分立型/共用型”措辞。



S1 生成器主文件（最高优先级，可能为 main.py / s1_generation.py）

struct_srs.py 完整内容


constraint_fields.py

co_derivation.py（P2 依赖）

builders.py / constants.py / escape.py（构建器与常量）

测试产物：review_structured.json、coverage_obligations.json、output.json、case_spec.json