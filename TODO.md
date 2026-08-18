
框架侧配套清单相应更新为：`validate_llm` 入口对 `xc_source="镜像"` 直接报错（LLM 通道关闭的唯一守门）；source_ref 章节号与原文目录 ∪ 处置表“不适用”章的双向差集；其余校验（op 全局唯一、词表定位、BR 承载含字面量、direction 词族一致、穿透逐值覆盖、signal_type 方向性）与此前约定相同。这套 prompt 交付后，如果跑一轮新文档仍有框架侧拦截不到的遗漏类型，那就是下一轮让渡的候选——按“让渡后必清除”的节奏继续收敛即可。

## **两点必须配套落实的说明**

这份 prompt 变薄成立的前提是框架接住让渡出去的职责，否则部分规则会悬空。`srs_pipeline` 侧需同步实现的最小集：**派生器**（遍历全部 precond 的跨实体 state_ref 生成镜像 XC，source_transition 由框架反查）；**对账校验**（op 名称全局唯一、章节处置表覆盖率与产物对应、prohibit_keywords 短语可被 source_ref 定位、每条 branch_dimension 有 BR 承载且 desc 含分支值字面量、direction 自报词与取值同族、分支转换 expected_results 覆盖全部 values、signal_type 与 desc 关键词方向性一致）；**歧义收集**（汇总 note.ambiguity 输出供人工仲裁）。这些都是纯机械检查，几十行量级。

另外按此前结论执行了两处纪律：没有为 category/signal_type 串位加专门提醒（schema 已对该类错误 100% 拦截，示例中的正确配对足以示范）；没有把"证据从严"写成新清单，而是并入既有判定（IT 仅文档明确禁止、因果排除流程表并排依据、状态枚举以状态分析表为权威、禁止重排 states），保持规则总量净减。
