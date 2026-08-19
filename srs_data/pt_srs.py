"""网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    # ── 标签分配表 ──
    # 实体: E-XM(项目) | E-BMJL(报名记录) | E-SYS(实验室信息) | E-BZK(标准库)
    #       | E-CSX(测试项) | E-ZLY(子领域) | E-XX(信息发送记录) | E-JFD(缴费记录)
    #       | E-FP(发票) | E-PJL(评价记录) | E-SP(审批任务) | E-LSPJ(历史项目)
    #       | E-CYDX(常用项)
    # 转换: t01-t05(E-XM.项目状态) | t06-t07(E-XM.样品状态)
    #       | t08-t18(E-BMJL.报名记录状态) | t19-t22(E-BMJL.费用状态)
    #       | t23-t25(E-BMJL.发票状态) | t26-t29(E-BMJL.报名记录样品状态)
    #       | t30-t35(E-BMJL.通知状态) | t36-t41(E-SYS.实验室状态)
    #       | t42-t44(E-BZK.标准库状态) | t45-t48(E-PJL.评价状态)
    #       | t49-t52(E-SP.任务状态)
    # XC: x01-x02 | BR: b01-b25 | IT: (无)
    # 角色: r01(实验室负责人) | r02(技术主管) | r03(授权签字人) | r04(策划人员)
    #       | r05(项目管理员) | r06(样品制备人员) | r07(样品管理员) | r08(评价人员)
    #       | r09(统计人员) | r10(质量专员) | r11(财务管理人员) | r12(系统管理人员)
    #       | r13(能力验证参加者) | r14(监督员)
    # 分支维度: 项目类型@E-XM | 评分方式@E-PJL | 发票类型@E-FP
    # ── 章节处置表 ──
    # 1-2 项目背景/目标 → 不适用：非功能性陈述，无实体/状态语义
    # 3 项目要求 → r01-r14（角色清单来自§3.2与§5-#6~#18；§3.2 超级管理员/审核人员口径与§5-#17系统管理人员/审核角色口径不一致，按§5-#6~#18登记，ambiguity 见维度级 note）
    # 4 系统功能架构分析 → 不适用：架构综述，无新实体/状态
    # 5 用户角色分析 → r01-r14（同§3，固定/非固定角色清单）
    # 19 系统流程分析 → E-XM(项目状态/样品状态), E-BMJL(五状态维度), t01-t35；状态枚举权威来源§19.3
    # 20.1 系统功能需求说明 → 不适用：综述段，无新实体
    # 20.2 首页 → 不适用：通知公告/常见问题/待办事项均为展示，无状态语义
    # 20.3 基本信息 → E-SYS(实验室状态)，t36-t41，b01-b05
    # 20.4 系统管理 → E-SYS、E-BZK、E-CSX、E-ZLY、E-XX，s1-s2，b06-b09，b32
    # 20.5 能力验证 → E-XM、E-BMJL、E-JFD、E-FP、E-CYDX，s3-s5，b10-b14，b16-b18
    # 20.6 测量审核 → 并入 E-XM(项目类型分支)、E-BMJL，bd1(项目类型)覆盖，t01-t35 同构适用
    # 20.7 项目评价 → E-PJL(评价状态)，t45-t48，s6，b15,b19-b22
    # 20.8 统计分析 → E-LSPJ(历史项目)，s7(E-XM→E-SP)，b33-b35；其余不适用：纯查询展示
    # 20.9 业务审核 → E-SP(任务状态)，t49-t52，s7(E-XM→E-SP)，b23-b25
    # 20.10 财务管理 → E-JFD、E-FP，bd3(发票类型)，b26-b29
    # 20.11 其他 → E-LSPJ(历史项目)，b30,b31
    # 21 非功能性 → 不适用：非功能要求，无实体/状态
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704.md",
        document_scope="网数中心能力验证服务平台升级维护项目需求分析，覆盖首页/基本信息/系统管理/能力验证/测量审核/项目评价/统计分析/业务审核/财务管理/其他模块的功能升级需求",
    )

    # ── Step 0：动词种子词表 ──
    m.set_prohibition_config(config={
        "action_verbs": [
            "新建", "编辑", "查询", "删除", "保存", "提交", "审批", "批准", "通过",
            "归档", "重启", "暂停", "结束", "发放", "退出", "登录", "分配", "入选",
            "进入", "选为", "选择", "执行", "退回", "撤销", "启用", "停用", "评价",
            "统计", "审核", "确认", "发布", "缴费", "退款", "开票", "收样", "发样",
            "还样", "核查", "整理", "导出", "导入", "下载", "上传", "批量处理",
            "选入", "纳入", "启动", "另存", "完成", "拒绝", "报名",
        ],
        "prohibit_keywords": [
            "含有子项的记录不允许删除",
            "退款金额不能大于当前缴费金额",
            "接收人1和接收人2不能同时为空",
            "评价人员不能查看和修改其他评价人员的评价结果",
        ],
    })

    # ── Step 0.5：角色与权限 ──
    # 角色：固定角色 r01-r08,r10-r13；非固定角色 r03(授权签字人)、r06(样品制备人员)、r08(评价人员)、r09(统计人员)、r14(监督员)
    # §3.2 "超级管理员" 与§5-#17 "系统管理人员" 口径不一致，按§5-#17 登记为 r12 系统管理人员
    # §3.2 "审核人员" 为类别（覆盖 r01/r02/r03），不单列
    m.add_role(id="r01", name="实验室负责人")
    m.add_role(id="r02", name="技术主管")
    m.add_role(id="r03", name="授权签字人")
    m.add_role(id="r04", name="策划人员")
    m.add_role(id="r05", name="项目管理员")
    m.add_role(id="r06", name="样品制备人员")
    m.add_role(id="r07", name="样品管理员")
    m.add_role(id="r08", name="评价人员")
    m.add_role(id="r09", name="统计人员")
    m.add_role(id="r10", name="质量专员", readonly=True)
    m.add_role(id="r11", name="财务管理人员")
    m.add_role(id="r12", name="系统管理人员", readonly=True)
    m.add_role(id="r13", name="能力验证参加者")
    m.add_role(id="r14", name="监督员", readonly=True)

    m.add_permission(role="项目管理员", operations=[
        "新建项目", "编辑项目", "查询项目", "删除项目", "文件整理", "代码导入",
        "批量处理", "消息发送", "上传附件", "下载附件", "上传结果通知单", "上传证书",
        "查看信息发送记录", "导出项目通知书",
    ])
    m.add_permission(role="能力验证参加者", operations=[
        "报名", "查询报名", "修改报名", "删除报名", "缴费", "上传付款单",
        "提交结果", "上传证明文件", "查询历史项目", "查看详情", "预通知文件下载",
    ])
    m.add_permission(role="财务管理人员", operations=[
        "上传发票", "退款", "修改财务备注", "查询缴费", "导出缴费", "查询收入统计",
        "查询发票",
    ])
    m.add_permission(role="系统管理人员", operations=[
        "新增实验室", "修改实验室", "删除实验室", "审核实验室", "启用实验室",
        "停用实验室", "查询实验室", "新增标准库", "修改标准库", "删除标准库",
        "启用标准库", "停用标准库", "管理测试项", "新增测试项", "修改测试项",
        "删除测试项", "查看信息发送记录", "创建自定义流程",
    ])
    m.add_permission(role="技术主管", operations=["审核报告", "审核证书", "审核结果通知单"])
    m.add_permission(role="实验室负责人", operations=["批准证书", "批准报告"])
    m.add_permission(role="授权签字人", operations=["批准结果报告", "批准结果通知单"])
    m.add_permission(role="评价人员", operations=[
        "完善评价项目", "协同评价", "评价结果导出", "保存历史", "调整细则",
        "退回修改评价",
    ])
    m.add_permission(role="策划人员", operations=[
        "编制设计方案", "编制结果报告", "编制结果通知单", "编制作业指导书", "项目归档",
    ])
    m.add_permission(role="样品管理员", operations=["样品核查", "样品发放", "样品入库", "样品出库"])
    m.add_permission(role="统计人员", operations=["统计分析", "查询统计"])

    # ── Step 1：实体 ──
    # E-XM 项目：core，多状态维度（项目状态+样品状态），多角色协作（项目管理员/策划人员/技术主管等），可审批，可配置（项目类型 is_config）
    m.add_entity(
        id="E-XM",
        name="项目",
        desc="能力验证/测量审核项目，承载立项、方案设计、实施、评价统计、报告编制、验收总结全生命周期；项目新增表单含技术主管、实验室负责人、授权签字人、监督员字段；项目状态枚举五值，样品状态枚举两值",
        type="core",
        tags=["approvable", "multi-state", "collaborative", "configurable"],
        attributes=[
            attr(name="项目编号", desc="唯一标识；自动生成"),
            attr(name="项目名称", desc="必填；唯一"),
            attr(name="项目类型", desc="必填；能力验证或测量审核；互斥", is_config=True),
            attr(name="产品类型", desc="必填；系统内所有产品类型"),
            attr(name="所属年度", desc="必填；时间范围"),
            attr(name="项目费用", desc="必填；金额；退款后更新为实际付款金额"),
            attr(name="子领域", desc="必填；引用E-ZLY"),
            attr(name="依据标准", desc="选填"),
            attr(name="技术主管", desc="必填；引用r02；备选人唯一时默认填充"),
            attr(name="实验室负责人", desc="必填；引用r01；备选人唯一时默认填充"),
            attr(name="授权签字人", desc="必填；引用r03；备选人唯一时默认填充"),
            attr(name="监督员", desc="选填；引用r14；下拉框可以为空"),
            attr(name="项目管理员", desc="必填；引用r05"),
            attr(name="评价人员", desc="选填；引用r08；第一个被选择的评价人员默认作为评价组长"),
            attr(name="财务备注", desc="选填；财务管理人员可修改"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": [],
                "note": {
                    "comment": "枚举来源§19.3；终态已结束-具名且全文无返回回路，§19.1 流程表项目状态列仅显式展示待开始/报名中，进行中/报告审核中/已结束由阶段推进推断",
                    "ambiguity": "§19.1 流程表未显式展示进行中/报告审核中/已结束的状态值，§19.3 枚举为权威来源，状态枚举与流程表展示口径不一致",
                },
            },
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查"],
                "initial": "待核查",
                "terminal": ["已核查"],
                "inferred": ["待核查"],
                "note": {
                    "comment": "枚举来源§19.3；待核查为隐式初态，依据§19.1实施阶段缴费行设置样品状态=待核查；§19.1流程表另出现已发样/已还样/无需还样等字符串，§19.3未收录，按查无处理不入states",
                },
            },
        ],
        operations=[
            op(name="新建项目", category="crud", expected_results=["项目创建成功"], source_ref="20.5.1",
               note=N(role="项目管理员")),
            op(name="编辑项目", category="crud", expected_results=["项目信息修改成功"], source_ref="20.5.1.7",
               note=N(role="项目管理员")),
            op(name="查询项目", category="query", expected_results=["返回项目列表"], source_ref="20.5.1",
               note=N(inferred=True, comment="查询操作隐式存在，框架补全", role="项目管理员")),
            op(name="删除项目", category="crud", expected_results=["项目删除成功"], source_ref="20.2.3待办事项",
               note=N(role="项目管理员")),
            op(name="文件整理", category="config", expected_results=["归档任务已开启，请稍后查看"], source_ref="20.5.1.1",
               note=N(role="项目管理员")),
            op(name="代码导入", category="file", expected_results=["机构代码导入成功"], source_ref="20.5.1.2",
               note=N(role="项目管理员")),
            op(name="批量处理", category="crud", expected_results=["批量处理完成"], source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="消息发送", category="config", expected_results=["消息发送成功"], source_ref="20.5.1.4",
               note=N(role="项目管理员")),
            op(name="上传附件", category="file", expected_results=["附件上传成功"], source_ref="20.5.1.1",
               note=N(inferred=True, comment="跨实体通用操作，宿主为E-XM", role="项目管理员")),
            op(name="下载附件", category="file", expected_results=["附件下载"], source_ref="20.5.1.1",
               note=N(inferred=True, comment="跨实体通用操作，宿主为E-XM", role="项目管理员")),
            op(name="导出项目通知书", category="file", expected_results=["项目通知书导出"], source_ref="20.5.1.5",
               note=N(role="项目管理员")),
            # 注："另存常用"操作宿主为E-CYDX（常用项），在E-CYDX登记一次，跨实体不重复
        ],
    )

    # E-BMJL 报名记录：core，五状态维度（通知状态/报名记录状态/报名记录样品状态/费用状态/发票状态），可审批，可过期（证书到期提醒），多角色协作
    m.add_entity(
        id="E-BMJL",
        name="报名记录",
        desc="参加者报名项目后生成的记录，承载报名审核、缴费、发样、结果提交、报告/证书审核发布全流程；含五状态维度；同一报名记录可多次付款、多次分批上传发票",
        type="core",
        tags=["approvable", "multi-state", "expirable", "collaborative"],
        attributes=[
            attr(name="报名编号", desc="唯一标识；自动生成"),
            attr(name="项目编号", desc="必填；引用E-XM"),
            attr(name="实验室", desc="必填；引用E-SYS；项目状态为待开始/报名中时右侧实验室列表为所有实验室，其他状态为报名实验室"),
            attr(name="报名时间", desc="自动记录"),
            attr(name="报名表", desc="上传文件"),
            attr(name="实施状态", desc="跟随报名记录状态派生"),
            attr(name="评价得分", desc="评价组长填写"),
            attr(name="评价结果", desc="评价确认后生成"),
            attr(name="到款时间", desc="财务确认"),
            attr(name="退款金额", desc="多次退款累加；红色字体且大于0时显示"),
            attr(name="实际付款", desc="=付款金额-退款金额"),
            attr(name="管理备注", desc="记录退款原因等内容"),
        ],
        state_dimensions=[
            {
                "dimension_name": "通知状态",
                "states": ["未发送", "待确认", "待审核", "退回", "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已批准"],
                "inferred": ["未发送"],
                "note": {
                    "comment": "枚举来源§19.3；未发送为隐式初态，依据§19.1实施阶段报名行初始化；§19.1流程表预通知状态列出现已发送/已确认等字符串，§19.3未收录按查无处理",
                    "ambiguity": "§19.1流程表预通知状态列与§19.3 通知状态枚举存在口径不一致：流程表使用已发送/已确认，§19.3使用待确认/已审核/已批准",
                },
            },
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "inferred": ["报名待审核"],
                "note": {
                    "comment": "枚举来源§19.3；报名待审核为隐式初态，依据§19.1报名行；终态报告/证书已发布-具名+全文无返回回路；已撤销-具名+全文无返回回路",
                },
            },
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "inferred": ["待发样"],
                "note": {"comment": "枚举来源§19.3；待发样为隐式初态，依据§19.1报名行初始化"},
            },
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": [],
                "inferred": ["待缴费"],
                "note": {"comment": "枚举来源§19.3；待缴费为隐式初态，依据§19.1报名行初始化；多次付款为已缴费自环"},
            },
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": [],
                "inferred": ["待开票"],
                "note": {"comment": "枚举来源§19.3；待开票为隐式初态，依据§19.1报名行初始化；分批上传发票为已开票自环"},
            },
        ],
        operations=[
            op(name="报名", category="crud", expected_results=["报名提交成功，等待审核"], source_ref="19.1实施阶段",
               note=N(role="能力验证参加者")),
            op(name="查询报名", category="query", expected_results=["返回报名列表"], source_ref="20.5.3",
               note=N(inferred=True, comment="查询操作隐式存在", role="项目管理员")),
            op(name="修改报名", category="crud", expected_results=["报名信息修改成功"], source_ref="20.5.3",
               note=N(role="能力验证参加者")),
            op(name="删除报名", category="crud", expected_results=["报名删除成功"], source_ref="20.2.3待办事项",
               note=N(inferred=True, comment="删除执行者未明示，推断为能力验证参加者", role="能力验证参加者")),
            op(name="缴费", category="crud", expected_results=["付款单上传成功"], source_ref="20.5.2.1",
               note=N(role="能力验证参加者")),
            op(name="退款", category="crud", expected_results=["退款成功"], source_ref="20.10.2.3",
               note=N(role="财务管理人员")),
            op(name="上传付款单", category="file", expected_results=["付款单上传成功"], source_ref="20.5.2.1",
               note=N(role="能力验证参加者")),
            op(name="上传结果通知单", category="file", expected_results=["结果通知单上传成功"], source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="上传证书", category="file", expected_results=["证书上传成功"], source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="提交结果", category="crud", expected_results=["结果提交成功"], source_ref="19.1实施阶段",
               note=N(role="能力验证参加者")),
            op(name="查看详情", category="query", expected_results=["返回报名详情"], source_ref="20.5.2.1",
               note=N(inferred=True, comment="详情查看操作隐式存在", role="能力验证参加者")),
            op(name="预通知文件下载", category="file", expected_results=["预通知文件下载"], source_ref="20.5.2.2",
               note=N(role="能力验证参加者")),
        ],
    )

    # E-SYS 实验室信息：managed，单状态维度（实验室状态），可审批（实验室审核）
    # §20.3.1 状态枚举为 待审核、启用、停用、退回修改；§20.4.1.1 状态枚举为 待审核、启用、停用、已退回
    # §20.4.1.2 审核退回修改 → 状态变更为"已退回"；按§20.4 功能模块枚举为权威来源
    m.add_entity(
        id="E-SYS",
        name="实验室信息",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名；管理页面字段含实验室名称、统一社会信用代码、状态、法人名称、企业类型、企业规模、CNAS、CMA、邮箱、座机号码、地址、联系人、联系电话、默认实验室、证明文件",
        type="managed",
        tags=["approvable"],
        attributes=[
            attr(name="实验室名称", desc="必填"),
            attr(name="统一社会信用代码", desc="必填；唯一"),
            attr(name="法人名称", desc="必填"),
            attr(name="企业类型", desc="必填"),
            attr(name="企业规模", desc="必填"),
            attr(name="CNAS", desc="已获CNAS认可；CNAS证书号"),
            attr(name="CMA", desc="已获CMA认可；CMA证书编号"),
            attr(name="邮箱", desc="选填"),
            attr(name="座机号码", desc="选填"),
            attr(name="行政区域", desc="必填"),
            attr(name="详细地址", desc="必填"),
            attr(name="联系人", desc="必填"),
            attr(name="联系电话", desc="必填"),
            attr(name="默认实验室", desc="标识是否为默认实验室"),
            attr(name="证明文件", desc="上传营业执照或其他证书材料；提示文字：请上传营业执照或其他证书材料"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "启用", "停用", "已退回"],
                "initial": "待审核",
                "terminal": [],
                "inferred": [],
                "note": {
                    "comment": "枚举来源§20.4.1.1；初始待审核由§20.3.1机构新增后置为待审核；§20.4.1.2退回修改操作使状态变更为已退回",
                    "ambiguity": "§20.3.1 列退回修改为状态值；§20.4.1.1 列已退回为状态值；§20.4.1.2 退回修改为操作名而结果状态为已退回；口径不一致，按§20.4 功能模块枚举取已退回",
                },
            },
        ],
        operations=[
            op(name="新增实验室", category="crud", expected_results=["实验室新增成功，等待审核"], source_ref="20.4.1.1",
               note=N(inferred=True, comment="新增操作由§20.3机构侧触发，推断为能力验证参加者", role="能力验证参加者")),
            op(name="修改实验室", category="crud", expected_results=["实验室修改成功，等待审核"], source_ref="20.4.1.3",
               note=N(inferred=True, comment="修改操作由§20.3机构侧触发，推断为能力验证参加者", role="能力验证参加者")),
            op(name="删除实验室", category="crud", expected_results=["实验室删除成功"], source_ref="20.3.1",
               note=N(inferred=True, comment="§20.3.1列出修改/删除操作，删除执行者推断为能力验证参加者", role="能力验证参加者")),
            op(name="审核实验室", category="crud", expected_results=["审核完成"], source_ref="20.4.1.2",
               note=N(role="系统管理人员")),
            op(name="启用实验室", category="crud", expected_results=["实验室启用成功"], source_ref="20.4.1.1",
               note=N(role="系统管理人员")),
            op(name="停用实验室", category="crud", expected_results=["实验室停用成功"], source_ref="20.4.1.1",
               note=N(role="系统管理人员")),
            op(name="查询实验室", category="query", expected_results=["返回实验室列表"], source_ref="20.4.1.1",
               note=N(role="系统管理人员")),
            op(name="上传证明文件", category="file", expected_results=["证明文件上传成功"], source_ref="20.3.1",
               note=N(inferred=True, comment="跨实体通用操作，宿主为E-SYS", role="能力验证参加者")),
        ],
    )

    # E-BZK 标准库：managed，单状态维度（标准库状态 启用/停用）
    m.add_entity(
        id="E-BZK",
        name="标准库",
        desc="代表一个完整的、可被引用的标准集合，如GB/T 12345-2020；下属测试项和参数；停用的标准库在项目创建等环节不可被选择",
        type="managed",
        tags=[],
        attributes=[
            attr(name="标准库编号", desc="必填；文本输入框"),
            attr(name="标准库名称", desc="必填；文本输入框"),
            attr(name="描述", desc="选填；文本输入框"),
            attr(name="创建时间", desc="自动记录"),
        ],
        state_dimensions=[
            {
                "dimension_name": "标准库状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "inferred": ["启用"],
                "note": {"comment": "枚举来源§20.4.2.1；启用为隐式初态，依据§20.4.2.2新增标准库时状态必填默认启用"},
            },
        ],
        operations=[
            op(name="新增标准库", category="crud", expected_results=["标准库新增成功"], source_ref="20.4.2.2",
               note=N(role="系统管理人员")),
            op(name="修改标准库", category="crud", expected_results=["标准库修改成功"], source_ref="20.4.2.3",
               note=N(role="系统管理人员")),
            op(name="删除标准库", category="crud", expected_results=["标准库删除成功"], source_ref="20.4.2.4",
               note=N(role="系统管理人员")),
            op(name="启用标准库", category="crud", expected_results=["标准库启用成功"], source_ref="20.4.2.5",
               note=N(role="系统管理人员")),
            op(name="停用标准库", category="crud", expected_results=["标准库停用成功"], source_ref="20.4.2.5",
               note=N(role="系统管理人员")),
            op(name="管理测试项", category="ui", expected_results=["进入测试项管理页面"], source_ref="20.4.2.6",
               note=N(role="系统管理人员")),
            op(name="查询标准库", category="query", expected_results=["返回标准库列表"], source_ref="20.4.2.1",
               note=N(role="系统管理人员")),
        ],
    )

    # E-CSX 测试项：managed，无状态，分层级（子测试项），CRUD 在标准库管理页内
    m.add_entity(
        id="E-CSX",
        name="测试项",
        desc="由编号和名称组成的一组数据，测试项下可以有子测试项；在标准库或子领域下进行分层级维护；含有子项的记录不允许删除",
        type="managed",
        tags=[],
        attributes=[
            attr(name="标号", desc="必填；文本输入框"),
            attr(name="名称", desc="必填；文本输入框"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud", expected_results=["测试项新增成功"], source_ref="20.4.2.8",
               note=N(role="系统管理人员")),
            op(name="修改测试项", category="crud", expected_results=["测试项修改成功"], source_ref="20.4.2.9",
               note=N(role="系统管理人员")),
            op(name="删除测试项", category="crud", expected_results=["测试项删除成功"], source_ref="20.4.2.10",
               note=N(role="系统管理人员")),
        ],
    )

    # E-ZLY 子领域：managed，无状态，测试项由选择方式从标准库引用
    m.add_entity(
        id="E-ZLY",
        name="子领域",
        desc="子领域下的测试项管理方式由表单方式变更为选择方式，选择数据来源于标准库；为降低项目录入难度，子领域下保存常用测试项组合",
        type="managed",
        tags=[],
        attributes=[
            attr(name="子领域名称", desc="必填"),
            attr(name="子领域编号", desc="必填；唯一"),
        ],
        state_dimensions=[],
        operations=[
            op(name="管理子领域测试项", category="ui", expected_results=["进入子领域测试项管理页面"], source_ref="20.4.3.1",
               note=N(role="系统管理人员")),
            op(name="新增子领域测试项", category="crud", expected_results=["子领域测试项新增成功"], source_ref="20.4.3.3",
               note=N(role="系统管理人员")),
            op(name="删除子领域测试项", category="crud", expected_results=["子领域测试项删除成功"], source_ref="20.4.3.4",
               note=N(role="系统管理人员")),
            op(name="查询子领域", category="query", expected_results=["返回子领域列表"], source_ref="20.4.3.2",
               note=N(inferred=True, comment="查询操作隐式存在", role="系统管理人员")),
        ],
    )

    # E-XX 信息发送记录：managed，无状态，仅系统管理员和项目管理员可查看
    m.add_entity(
        id="E-XX",
        name="信息发送记录",
        desc="记录系统中的信息发送历史，记录内容包含发送方式、接收人、发送时间、发送人、发送结果；只有系统管理员和项目管理员可以查看",
        type="managed",
        tags=[],
        attributes=[
            attr(name="接收号码", desc="文本输入框，模糊匹配"),
            attr(name="发送方式", desc="短信；邮件；站内信"),
            attr(name="发送时间", desc="时间范围选择框，精确匹配"),
            attr(name="消息标题", desc="文本"),
            attr(name="消息内容", desc="文本"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query", expected_results=["返回信息发送记录列表"], source_ref="20.4.4.1",
               note=N(role=["系统管理人员", "项目管理员"])),
            op(name="查看消息详情", category="query", expected_results=["返回消息详细内容"], source_ref="20.4.4.1",
               note=N(role=["系统管理人员", "项目管理员"])),
        ],
    )

    # E-JFD 缴费记录：managed，无状态，支持多次付款累加、退款
    m.add_entity(
        id="E-JFD",
        name="缴费记录",
        desc="每次缴费生成一条记录，包含支付方式、付款金额、退款金额、实际付款；多次退款金额累加；实际付款=付款金额-退款金额",
        type="managed",
        tags=[],
        attributes=[
            attr(name="支付方式", desc="必填；下拉选择框"),
            attr(name="支付账户名称", desc="必填；文本输入框"),
            attr(name="汇款金额", desc="必填；默认为项目费用金额"),
            attr(name="付款底单", desc="必填；文件选择框"),
            attr(name="付款项目", desc="只读；内容为当前报名编号"),
            attr(name="备注", desc="选填"),
            attr(name="退款金额", desc="必填；不能大于当前缴费金额；多次退款累加；红色字体且大于0时显示"),
            attr(name="实际付款", desc="=付款金额-退款金额"),
            attr(name="管理备注", desc="记录退款原因等内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询缴费", category="query", expected_results=["返回缴费列表"], source_ref="20.10.1.1",
               note=N(role="财务管理人员")),
            op(name="导出缴费", category="file", expected_results=["缴费数据导出"], source_ref="20.10.1.1",
               note=N(role="财务管理人员")),
            op(name="修改财务备注", category="crud", expected_results=["财务备注修改成功"], source_ref="20.10.2.1",
               note=N(role="财务管理人员")),
        ],
    )

    # E-FP 发票：managed，无状态，支持多次分批上传
    m.add_entity(
        id="E-FP",
        name="发票",
        desc="发票记录，关联到报名记录；支持多次分批上传；缴费信息管理按发票类型筛选；证书距到期时间等于30天邮件提醒",
        type="managed",
        tags=["expirable"],
        attributes=[
            attr(name="开票时间", desc="时间选择框；最后一次开票时间"),
            attr(name="电子发票", desc="文件选择组件；可多张"),
            attr(name="关联项目", desc="只读；项目报名编号"),
            attr(name="项目金额", desc="只读；项目费用"),
            attr(name="发票类型", desc="电子专票；电子普票", is_config=True),
            attr(name="证书编号", desc="唯一"),
            attr(name="证书到期时间", desc="每天上午9点检查；距到期30天邮件提醒"),
        ],
        state_dimensions=[],
        operations=[
            op(name="上传发票", category="file", expected_results=["发票上传成功"], source_ref="20.10.2.2",
               note=N(role="财务管理人员")),
            op(name="查询发票", category="query", expected_results=["返回发票列表"], source_ref="20.10.1.1",
               note=N(inferred=True, comment="查询操作隐式存在", role="财务管理人员")),
        ],
    )

    # E-PJL 评价记录：core，单状态维度（评价状态 推断），多角色协作（评价人员/评价组长）
    # 评价组长为评价人员中的子角色，第一个被选择的评价人员默认作为评价组长
    m.add_entity(
        id="E-PJL",
        name="评价记录",
        desc="评价人员对报名项目进行协同评价；新建项目时第一个被选择的评价人员默认作为评价组长；评价组长可在评价结果确认页面查看各评价人员评价结果并对最终结果确认；评价人员只能对自己的评价结果修改；评价支持分值和权重两种方式",
        type="core",
        tags=["approvable", "collaborative"],
        attributes=[
            attr(name="评价项目", desc="评价组长完善；含分值/权重/说明评分细则/显示顺序"),
            attr(name="评价细则", desc="评价组长完善"),
            attr(name="评分方式", desc="分值；权重", is_config=True),
            attr(name="及格分", desc="评价组长录入"),
            attr(name="评价结果", desc="评价人员录入分值/权重；评价组长确认得分"),
            attr(name="历史结果", desc="保存历史；可下载"),
            attr(name="统计规则", desc="每个统计规则由低值+高值组成；判断规则为大于等于低值，小于高值"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["待评价", "评价中", "已确认"],
                "initial": "待评价",
                "terminal": ["已确认"],
                "inferred": ["待评价", "评价中", "已确认"],
                "note": {
                    "comment": "§19.3 未单列评价状态枚举；依据§20.7.1.2协同评价、§20.7.1.3评价确认（确认后项目评价状态关闭）与退回修改（开启下一轮评价）推断三状态",
                    "inferred_basis": "§20.7.1.3 确认操作使项目评价状态关闭；§20.7.1.3 退回修改开启下一轮评价",
                },
            },
        ],
        operations=[
            op(name="完善评价项目", category="crud", expected_results=["评价项目完善"], source_ref="20.7.1.1",
               note=N(inferred=True, comment="评价组长为评价人员子角色，本操作由评价组长执行，对齐已登记角色评价人员", role="评价人员")),
            op(name="协同评价", category="crud", expected_results=["评价结果提交"], source_ref="20.7.1.2",
               note=N(role="评价人员")),
            op(name="评价结果导出", category="file", expected_results=["评价结果下载"], source_ref="20.7.1.4",
               note=N(role="评价人员")),
            op(name="保存历史", category="crud", expected_results=["评价结果保存为历史"], source_ref="20.7.1.3",
               note=N(inferred=True, comment="评价组长为评价人员子角色，对齐已登记角色评价人员", role="评价人员")),
            op(name="调整细则", category="crud", expected_results=["打开评价细节完善页面"], source_ref="20.7.1.3",
               note=N(inferred=True, comment="评价组长为评价人员子角色，对齐已登记角色评价人员", role="评价人员")),
            op(name="退回修改评价", category="crud", expected_results=["开启下一轮评价"], source_ref="20.7.1.3",
               note=N(inferred=True, comment="评价组长为评价人员子角色，对齐已登记角色评价人员", role="评价人员")),
        ],
    )

    # E-SP 审批任务：core，单状态维度（任务状态 推断），多角色审批链（技术主管/授权签字人/实验室负责人），合并流程
    m.add_entity(
        id="E-SP",
        name="审批任务",
        desc="流程审批任务；测量审核结果通知单审批流程合并为一个流程；处理者审批顺序为提交申请时签字人的选择顺序；系统预设4个以内自定义流程；任务创建时短信通知相关负责人",
        type="core",
        tags=["approvable", "collaborative"],
        attributes=[
            attr(name="任务类型", desc="结果通知单审核；报告审核；证书审核；通知审核等"),
            attr(name="处理人顺序", desc="提交申请时签字人的选择顺序"),
            attr(name="审批意见", desc="文本输入框，选填"),
            attr(name="审核结果", desc="同意；退回"),
            attr(name="创建时间", desc="时间选择框"),
            attr(name="签章位置", desc="电子签章位置信息，自动代入"),
        ],
        state_dimensions=[
            {
                "dimension_name": "任务状态",
                "states": ["待审核", "已审核", "已退回", "已批准"],
                "initial": "待审核",
                "terminal": ["已批准", "已退回"],
                "inferred": ["待审核", "已审核", "已退回", "已批准"],
                "note": {
                    "comment": "§19.3 未单列审批任务状态枚举；依据§20.9.1.4批量审核选项同意/退回、§20.9.1.7节点状态颜色标记推断三状态；依据§19.1'授权签字人/证书实验室负责人批准'推断增加已批准终态",
                    "inferred_basis": "§20.9.1.4 审核结果选项为同意/退回；§20.9.1.7 不同颜色对各个状态的节点进行标记；§19.1 报告编制和结果通知批准环节",
                },
            },
        ],
        operations=[
            op(name="提交审核", category="crud", expected_results=["审核任务提交"], source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="对应转换 t49")),
            op(name="批量审核", category="crud", expected_results=["批量审核完成"], source_ref="20.9.1.4",
               note=N(inferred=True, comment="批量审核由审核角色执行，推断为系统管理人员；对应转换 t50；t51（通过/退回）", role="系统管理人员")),
            op(name="任务列表查询", category="query", expected_results=["返回审批流程列表"], source_ref="20.9.1.5",
               note=N(inferred=True, comment="查询操作隐式存在", role="系统管理人员")),
            op(name="任务列表导出", category="file", expected_results=["审批流程列表导出"], source_ref="20.9.1.5",
               note=N(inferred=True, comment="导出操作由系统管理人员执行", role="系统管理人员")),
            op(name="创建自定义流程", category="config", expected_results=["自定义流程创建"], source_ref="20.9.1.6",
               note=N(role="系统管理人员")),
            op(name="增加任务提醒", category="config", expected_results=["任务创建短信通知相关负责人"], source_ref="20.9.1.3",
               note=N(role="system")),
        ],
    )


    # E-LSPJ 历史项目：managed，无状态，列表+查询+导出
    m.add_entity(
        id="E-LSPJ",
        name="历史项目",
        desc="对往年项目数据进行分析整理并导入到系统中为数据分析提供关键数据；历史项目列表支持按项目名称、项目类型、子领域、所属年度筛选；包含报名/评价/费用/证书等历史信息",
        type="managed",
        tags=[],
        attributes=[
            attr(name="项目编号", desc="文本"),
            attr(name="项目名称", desc="文本输入框，模糊匹配"),
            attr(name="子领域", desc="文本输入框，模糊匹配"),
            attr(name="项目类型", desc="能力验证；测量审核"),
            attr(name="项目管理员", desc="文本"),
            attr(name="所属年度", desc="文本输入框，精确匹配"),
            attr(name="统一社会信息代码", desc="文本"),
            attr(name="实验室名称", desc="文本"),
            attr(name="企业类型", desc="文本"),
            attr(name="企业规模", desc="文本"),
            attr(name="法人名称", desc="文本"),
            attr(name="联系人", desc="文本"),
            attr(name="联系电话", desc="文本"),
            attr(name="报告时间", desc="时间"),
            attr(name="证书时间", desc="时间"),
            attr(name="证书编号", desc="文本"),
            attr(name="评价结果", desc="文本"),
            attr(name="项目费用", desc="金额"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询历史项目", category="query", expected_results=["返回历史项目列表"], source_ref="20.11.1.1",
               note=N(inferred=True, comment="查询操作隐式存在，对齐r05/r09/r10等可访问统计角色", role="项目管理员")),
        ],
    )

    # E-CYDX 常用项：managed，无状态，子领域下保存常用测试项/评价细则组合
    m.add_entity(
        id="E-CYDX",
        name="常用项",
        desc="为降低项目录入难度，减少出错概率，在项目新建页面增加子领域常用测试项管理能力；另存常用后可在常用下拉列表中选择填充或删除",
        type="managed",
        tags=[],
        attributes=[
            attr(name="名称", desc="必填；文本输入框"),
            attr(name="子领域", desc="引用E-ZLY"),
            attr(name="测试项组合", desc="保存的测试项/评价细则组合数据"),
        ],
        state_dimensions=[],
        operations=[
            op(name="另存常用", category="crud", expected_results=["常用项保存"], source_ref="20.5.1.7",
               note=N(role="项目管理员")),
            op(name="选择常用", category="crud", expected_results=["常用项填充到表单"], source_ref="20.5.1.7",
               note=N(inferred=True, comment="选择常用操作隐式存在", role="项目管理员")),
            op(name="删除常用", category="crud", expected_results=["常用项删除"], source_ref="20.5.1.7",
               note=N(inferred=True, comment="删除操作隐式存在", role="项目管理员")),
        ],
    )

    # ── Step 2：结构关系 ──
    # s1: E-BZK → E-CSX (reference, configuration_source, 1:N)
    # 判定 (d)：测试项有独立创建流程（CRUD在标准库管理页内），E-CSX 为 managed 不满足 (c) core 要求
    m.add_structural(
        frm="E-BZK", to="E-CSX",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="标准库为测试项提供配置/分类容器，测试项在标准库管理页内独立创建/修改/删除",
        confidence="high",
        note={"comment": "四元判(d)B有独立创建流程且不满足(c)core要求；management_dimension复核：标准库作为测试项的配置容器，结论configuration_source"},
    )

    # s2: E-BZK → E-ZLY (reference, configuration_source, M:N)
    # 判定 (a)：标准库为子领域提供测试项配置/模板，子领域独立创建测试项引用
    m.add_structural(
        frm="E-BZK", to="E-ZLY",
        relation_type="reference", cardinality="M:N",
        ownership_dimension="configuration_source",
        desc="子领域下的测试项由选择方式从标准库引用，标准库为子领域提供测试项配置/模板",
        confidence="high",
        note={"comment": "四元判(a)A为B提供配置/模板，B独立创建；§20.4.3 子领域管理由表单方式变更为选择方式，数据来源于标准库"},
    )

    # s3: E-XM → E-BMJL (composition, business_ownership, 1:N)
    # 判定 (c)：报名记录有独立创建流程（用户报名），B 是 core，A 为业务归属容器（报名记录归属字段继承自项目，删除项目须校验报名记录存在性）
    m.add_structural(
        frm="E-XM", to="E-BMJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目为报名记录的业务归属容器，每个项目可含多条报名记录；删除项目须校验报名记录存在性",
        confidence="high",
        note={"comment": "四元判(c)B有独立创建流程+core+容器证据（归属字段继承自项目，生命周期挂靠项目）；(c)先于(d)"},
    )

    # s4: E-BMJL → E-JFD (reference, configuration_source, 1:N)
    # 判定 (d)：缴费记录有独立创建流程（每次付款创建），E-JFD 为 managed 不满足 (c) core 要求
    m.add_structural(
        frm="E-BMJL", to="E-JFD",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联多条缴费记录；同一报名记录可多次付款（不对付款金额进行校验限制）",
        confidence="high",
        note={"comment": "四元判(d)B有独立创建流程且不满足(c)core要求；管理维度复核：报名记录为缴费记录的业务承载，但缴费记录仅 managed，降判configuration_source"},
    )

    # s5: E-BMJL → E-FP (reference, configuration_source, 1:N)
    # 判定 (d)：发票有独立创建流程（每次上传），E-FP 为 managed
    m.add_structural(
        frm="E-BMJL", to="E-FP",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联多张发票；支持多次分批上传发票",
        confidence="high",
        note={"comment": "四元判(d)B有独立创建流程且不满足(c)core要求；E-BMJL.发票状态 维度跟踪整体开票状态"},
    )

    # s6: E-XM → E-PJL (composition, business_ownership, 1:N)
    # 判定 (c)：评价记录有独立创建流程（评价组长完善），E-PJL 为 core，A 为业务归属容器
    m.add_structural(
        frm="E-XM", to="E-PJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目为评价记录的业务归属容器；评价可多轮（退回修改开启下一轮）",
        confidence="high",
        note={"comment": "四元判(c)B有独立创建流程+core+容器证据（评价记录归属项目，生命周期挂靠项目）"},
    )

    # s7: E-XM → E-SP (composition, business_ownership, 1:N)
    # 判定 (c)：审批任务有独立创建流程（提交审核创建），E-SP 为 core，A 为业务归属容器
    m.add_structural(
        frm="E-XM", to="E-SP",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目为审批任务的业务归属容器；审批任务关联项目文档（结果通知单/报告/证书）",
        confidence="medium",
        note={"comment": "四元判(c)B有独立创建流程+core；容器证据较弱：审批任务实际挂靠项目文档，间接归属项目；confidence=medium"},
    )

    # s8: E-ZLY → E-CYDX (reference, configuration_source, 1:N)
    # 判定 (d)：常用项有独立创建（另存常用），E-CYDX 为 managed
    m.add_structural(
        frm="E-ZLY", to="E-CYDX",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="子领域下保存常用测试项组合；常用项独立创建",
        confidence="high",
        note={"comment": "四元判(d)B有独立创建流程且不满足(c)core要求"},
    )

    # s9: E-SYS → E-BMJL (reference, configuration_source, 1:N)
    # 判定 (d) 排除项：实验室为报名记录的申请人/持有人，B 生命周期独立、删除 A 不级联 B
    m.add_structural(
        frm="E-SYS", to="E-BMJL",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="实验室为报名记录的申请人/持有人；实验室必须启用方可用于项目报名",
        confidence="high",
        note={"comment": "四元判(d)排除项：A为B发起人/持有人（B生命周期独立、删除A不级联B）→降判(d)；§20.3.1 实验室审核通过后方可用于项目报名"},
    )

    # ── Step 3：分支维度 ──
    # bd1: 项目类型 @ E-XM
    # 三型判 ① 配置型：对应 is_config 属性（项目类型），创建时定、互斥、影响后续（能力验证走§19.1流程，测量审核走§19.2流程）
    m.add_branch_dimension(
        dimension="项目类型",
        entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="项目流程、统计分析、财务管理、缴费信息查询的业务维度",
        evidence="三型判：①配置型（对应 is_config 属性项目类型，创建时定、互斥、影响后续流程）；§19.1能力验证提供者流程与§19.2测量审核提供者流程为两套独立流程；§20.5能力验证与§20.6测量审核分章描述",
        branches=[
            {"value": "能力验证", "target_transition": "t02",
             "desc": "项目类型=能力验证时走§19.1能力验证流程：包含能力验证计划发布、报名、报名审核、缴费、发票开具、能力验证预通知、样品核查、样品发放、参加者测试与结果提交、报告编制与结果通知等子步骤"},
            {"value": "测量审核", "target_transition": "t02",
             "desc": "项目类型=测量审核时走§19.2测量审核流程：包含受理用户测量审核报名、报名审核、编制缴纳测量审核费用通知、缴费、发票开具、任务通知书编制、设计方案编制、样品领用登记、作业指导书编制、能力验证预通知、样品核查、样品发放、参加者测试与结果提交返样、报告编制和结果通知等子步骤"},
        ],
    )

    # bd2: 评分方式 @ E-PJL
    # 三型判 ① 配置型：对应 is_config 属性（评分方式），互斥、影响评价录入字段
    m.add_branch_dimension(
        dimension="评分方式",
        entity="E-PJL",
        values=["分值", "权重"],
        impact_scope="评价项目完善、协同评价、评价结果确认的字段录入与显示",
        evidence="三型判：①配置型（对应 is_config 属性评分方式，互斥、影响后续）；§20.7.1.1评价项目表单分值/权重字段必填；§20.7.1.2协同评价列表显示分值/权重列",
        branches=[
            {"value": "分值", "target_transition": "t46",
             "desc": "评分方式=分值时评价列表显示分值列，评价人员录入分值"},
            {"value": "权重", "target_transition": "t46",
             "desc": "评分方式=权重时评价列表显示权重列，评价人员录入权重"},
        ],
    )

    # bd3: 发票类型 @ E-FP
    # 三型判 ① 配置型：对应 is_config 属性（发票类型），影响财务管理查询
    m.add_branch_dimension(
        dimension="发票类型",
        entity="E-FP",
        values=["电子专票", "电子普票"],
        impact_scope="财务管理缴费信息查询的业务维度筛选",
        evidence="三型判：①配置型（对应 is_config 属性发票类型，互斥、影响财务管理查询）；§20.10.1.1缴费信息查询支持按发票类型筛选",
        branches=[
            {"value": "电子专票", "target_transition": None,
             "desc": "发票类型=电子专票时缴费信息查询返回电子专票记录"},
            {"value": "电子普票", "target_transition": None,
             "desc": "发票类型=电子普票时缴费信息查询返回电子普票记录"},
        ],
    )

    # ── Step 4.1：转换 ──
    # === E-XM.项目状态 ===
    # t01: 创建转换（必补）— 新建项目
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="新建项目", role="项目管理员",
        preconditions=[], expected_results=["项目创建成功"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.5.1",
        note={"comment": "direction判⓪frm=None→forward；§20.5.1项目新增表单"},
    )
    # t02: 待开始 → 报名中 — 能力验证计划发布（§19.1实施阶段能力验证计划发布行项目状态=报名中）
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="发布能力验证计划", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
        ],
        expected_results=["项目状态变更为报名中，开启用户报名"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={
            "comment": "direction判③frm待开始先于to报名中→forward；分支穿透：项目类型影响后续流程",
            "branch_dimension": "项目类型",
        },
    )
    # t03: 报名中 → 进行中 — 启动实施（inferred，§19.3枚举有进行中状态但§19.1流程表未显式展示）
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="启动实施", role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目状态变更为进行中，进入样品核查/发放/结果提交阶段"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1实施阶段后续子步骤（样品核查/样品发放/参加者测试）应使项目进入进行中状态；direction判③frm报名中先于to进行中→forward",
        },
    )
    # t04: 进行中 → 报告审核中 — 结果报告回收（inferred）
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="结果报告回收", role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
        ],
        expected_results=["项目状态变更为报告审核中，进入报告编制与结果通知阶段"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报告编制和结果通知阶段对应项目状态报告审核中；direction判③frm进行中先于to报告审核中→forward",
        },
    )
    # t05: 报告审核中 → 已结束 — 项目归档/验收总结（inferred）
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="项目归档", role="策划人员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
        ],
        expected_results=["项目状态变更为已结束，进入文件整理阶段"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1项目验收总结；20.5.1.1",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1项目验收总结阶段+§20.5.1.1文件整理按钮仅对已结束项目记录提供；direction判③frm报告审核中先于to已结束→forward",
        },
    )

    # === E-XM.样品状态 ===
    # t06: 创建转换 — 样品状态初始化为待核查（inferred initial）
    m.add_trans(
        tid="t06", entity="E-XM", dimension="样品状态",
        frm=None, to="待核查", action="初始化样品状态", role="system",
        preconditions=[], expected_results=["样品状态初始化为待核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段缴费行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1缴费行设置样品状态=待核查；direction判⓪frm=None→forward；隐式初态",
        },
    )
    # t07: 待核查 → 已核查 — 样品核查
    m.add_trans(
        tid="t07", entity="E-XM", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变更为已核查、待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段样品核查行",
        note={"comment": "direction判③frm待核查先于to已核查→forward"},
    )

    # === E-BMJL.报名记录状态 ===
    # t08: 创建转换 — 报名（§19.1实施阶段报名行报名记录状态=报名待审核/已撤销）
    m.add_trans(
        tid="t08", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="实验室状态为启用", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["报名记录创建，状态为报名待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段报名行",
        note={"comment": "direction判⓪frm=None→forward；§20.3.1实验室审核通过后方可用于项目报名"},
    )
    # t09: 报名待审核 → 报名成功 — 报名审核通过
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为报名成功；用户收到'您xxx项目的报名信息审核通过，请知悉'短信"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段报名审核行；20.5.3.2",
        note={"comment": "direction判③frm报名待审核先于to报名成功→forward；§20.5.3.2报名审核通过触发短信通知"},
    )
    # t10: 报名待审核 → 报名退回 — 报名审核退回
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核退回", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为报名退回；用户收到'您xxx项目的报名信息审核未通过，请知悉'短信"],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="19.1实施阶段报名审核行；20.5.3.2",
        note={"comment": "direction判③frm报名待审核先于to报名退回→forward，语义backward（业务回退，序判与语义冲突，语义优先）；§20.5.3.2报名审核退回触发短信通知"},
    )
    # t11: 报名退回 → 报名待审核 — 重新提交
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="重新提交报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名退回")),
        ],
        expected_results=["报名记录状态变更为报名待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段报名审核行",
        note={"comment": "direction判④frm报名退回后于to报名待审核→backward，语义forward（重新提交为业务推进，序判与语义冲突，语义优先）；禁止为序判成立重排states顺序"},
    )
    # t12: 报名成功 → 结果待提交 — 启动结果提交阶段（inferred）
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="启动结果提交", role="system",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["报名记录状态变更为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段能力验证预通知行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1能力验证预通知行报名记录状态=结果待提交，报名成功后自动推进；direction判③frm报名成功先于to结果待提交→forward",
        },
    )
    # t13: 结果待提交 → 结果已提交 — 提交结果
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="提交结果", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变更为结果已提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段参加者测试与结果提交行",
        note={"comment": "direction判③frm结果待提交先于to结果已提交→forward"},
    )
    # t14: 结果已提交 → 结果退回修改 — 结果审核退回
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果审核退回", role="技术主管",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变更为结果退回修改；用户收到'您xxxx项目测试报告审核未通过，请知悉'短信"],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知结果报告回收行；20.5.3.2",
        note={"comment": "direction判③frm结果已提交先于to结果退回修改→forward，语义backward（业务回退，序判与语义冲突，语义优先）；§20.5.3.2测试结果审核退回触发短信通知"},
    )
    # t15: 结果退回修改 → 结果已提交 — 重新提交
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交", action="重新提交结果", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果退回修改")),
        ],
        expected_results=["报名记录状态变更为结果已提交"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1报告编制和结果通知结果报告回收行",
        note={"comment": "direction判④frm结果退回修改后于to结果已提交→backward，语义forward（重新提交为业务推进，序判与语义冲突，语义优先）；禁止为序判成立重排states顺序"},
    )
    # t16: 结果已提交 → 报告/证书审核中 — 启动报告审核（inferred）
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="启动报告审核", role="system",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变更为报告/证书审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知编制结果报告行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报告编制和结果通知行报名记录状态=报告/证书审核中；direction判③frm结果已提交先于to报告/证书审核中→forward",
        },
    )
    # t17: 报告/证书审核中 → 报告/证书已发布 — 发布结果报告和证书
    m.add_trans(
        tid="t17", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发布结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["报名记录状态变更为报告/证书已发布；用户收到'您xxx项目的结果通知单已发布，请知悉'短信"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知发放结果报告和证书行；20.5.3.2",
        note={"comment": "direction判③frm报告/证书审核中先于to报告/证书已发布→forward；§20.5.3.2结果通知单发布触发短信通知"},
    )
    # t18: 报名待审核 → 已撤销 — 撤销报名（lateral，①explicit "撤销"）
    m.add_trans(
        tid="t18", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="已撤销", action="撤销报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为已撤销"],
        traits=[], direction="lateral", priority="P2",
        source_ref="19.1实施阶段报名行",
        note={"comment": "direction判①explicit措辞'撤销'→lateral；§19.1报名行报名记录状态=报名待审核/已撤销，撤销为侧挂主线外"},
    )

    # === E-BMJL.费用状态 ===
    # t19: 创建转换 — 费用状态初始化为待缴费（inferred initial）
    m.add_trans(
        tid="t19", entity="E-BMJL", dimension="费用状态",
        frm=None, to="待缴费", action="初始化费用状态", role="system",
        preconditions=[], expected_results=["费用状态初始化为待缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段报名行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报名行费用状态=待缴费；direction判⓪frm=None→forward；隐式初态",
        },
    )
    # t20: 待缴费 → 已缴费 — 缴费
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="费用状态为待缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "待缴费")),
        ],
        expected_results=["费用状态变更为已缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段缴费行；20.5.2.1",
        note={"comment": "direction判③frm待缴费先于to已缴费→forward；§20.5.2.1已报名项目增加多次付款功能"},
    )
    # t21: 已缴费 → 已缴费 — 多次付款（self-loop，⑤forward+inferred）
    m.add_trans(
        tid="t21", entity="E-BMJL", dimension="费用状态",
        frm="已缴费", to="已缴费", action="多次付款", role="能力验证参加者",
        preconditions=[
            precond(text="费用状态为已缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "已缴费")),
        ],
        expected_results=["新增一条缴费记录；费用状态保持已缴费；不对付款金额进行校验限制"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.5.2.1",
        note={
            "inferred": True,
            "comment": "direction判⑤frm==to→forward+inferred，无状态迁移；§20.5.2.1多次付款不对付款金额进行校验限制",
        },
    )
    # t22: 已缴费 → 已缴费 — 退款（self-loop，⑤forward+inferred）
    m.add_trans(
        tid="t22", entity="E-BMJL", dimension="费用状态",
        frm="已缴费", to="已缴费", action="退款", role="财务管理人员",
        preconditions=[
            precond(text="费用状态为已缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "已缴费")),
            precond(text="退款金额不能大于当前缴费金额", ptype="constraint", ref=None,
                    note={"comment": "§20.10.2.3退款金额必填且不能大于当前缴费金额"}),
        ],
        expected_results=["新增一条退款记录；退款金额累加；实际付款=付款金额-退款金额；项目费用更新为实际付款金额"],
        traits=["data_constraint"], direction="forward", priority="P1",
        source_ref="20.10.2.3",
        note={
            "inferred": True,
            "comment": "direction判⑤frm==to→forward+inferred，无状态迁移；§20.10.2.3退款后更新项目费用为实际付款金额",
        },
    )

    # === E-BMJL.发票状态 ===
    # t23: 创建转换 — 发票状态初始化为待开票（inferred initial）
    m.add_trans(
        tid="t23", entity="E-BMJL", dimension="发票状态",
        frm=None, to="待开票", action="初始化发票状态", role="system",
        preconditions=[], expected_results=["发票状态初始化为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段报名行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报名行发票状态=待开票；direction判⓪frm=None→forward；隐式初态",
        },
    )
    # t24: 待开票 → 已开票 — 发票开具
    m.add_trans(
        tid="t24", entity="E-BMJL", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务管理人员",
        preconditions=[
            precond(text="发票状态为待开票", ptype="state_ref",
                    ref=state_ref("E-BMJL", "发票状态", "待开票")),
        ],
        expected_results=["发票状态变更为已开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段发票开具行",
        note={"comment": "direction判③frm待开票先于to已开票→forward"},
    )
    # t25: 已开票 → 已开票 — 分批上传发票（self-loop，⑤forward+inferred）
    m.add_trans(
        tid="t25", entity="E-BMJL", dimension="发票状态",
        frm="已开票", to="已开票", action="分批上传发票", role="财务管理人员",
        preconditions=[
            precond(text="发票状态为已开票", ptype="state_ref",
                    ref=state_ref("E-BMJL", "发票状态", "已开票")),
        ],
        expected_results=["新增一条发票记录；发票状态保持已开票"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.10.2.2",
        note={
            "inferred": True,
            "comment": "direction判⑤frm==to→forward+inferred，无状态迁移；§20.10.2.2发票上传支持多次分批上传",
        },
    )

    # === E-BMJL.报名记录样品状态 ===
    # t26: 创建转换 — 报名记录样品状态初始化为待发样（inferred initial）
    m.add_trans(
        tid="t26", entity="E-BMJL", dimension="报名记录样品状态",
        frm=None, to="待发样", action="初始化报名记录样品状态", role="system",
        preconditions=[], expected_results=["报名记录样品状态初始化为待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段报名行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报名行报名记录样品状态=待发样（隐式初态）；direction判⓪frm=None→forward",
        },
    )
    # t27: 待发样 → 待收样 — 样品发放
    m.add_trans(
        tid="t27", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待发样", to="待收样", action="样品发放", role="样品管理员",
        preconditions=[
            precond(text="样品状态为已核查", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已核查")),
            precond(text="报名记录样品状态为待发样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待发样")),
        ],
        expected_results=["报名记录样品状态变更为待收样；用户收到'您xxxx项目的样品已发出，请知悉'短信"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段样品发放行；20.5.3.2",
        note={"comment": "direction判③frm待发样先于to待收样→forward；§20.5.3.2发样通知触发短信"},
    )
    # t28: 待收样 → 已收样 — 参加者收样（inferred）
    m.add_trans(
        tid="t28", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待收样", to="已收样", action="参加者收样", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为待收样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待收样")),
        ],
        expected_results=["报名记录样品状态变更为已收样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3报名记录样品状态枚举",
        note={
            "inferred": True,
            "comment": "推断依据：§19.3报名记录样品状态枚举含待收样/已收样，§19.1流程表未显式展示参加者收样动作；direction判③frm待收样先于to已收样→forward",
        },
    )
    # t29: 已收样 → 已确认 — 参加者确认（inferred）
    m.add_trans(
        tid="t29", entity="E-BMJL", dimension="报名记录样品状态",
        frm="已收样", to="已确认", action="参加者确认收样", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为已收样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "已收样")),
        ],
        expected_results=["报名记录样品状态变更为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3报名记录样品状态枚举；19.1实施阶段样品发放行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1样品发放行报名记录样品状态=已确认（确认收样）；direction判③frm已收样先于to已确认→forward",
        },
    )

    # === E-BMJL.通知状态 ===
    # t30: 创建转换 — 通知状态初始化为未发送（inferred initial）
    m.add_trans(
        tid="t30", entity="E-BMJL", dimension="通知状态",
        frm=None, to="未发送", action="初始化通知状态", role="system",
        preconditions=[], expected_results=["通知状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段报名行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报名行预通知状态=未发送（隐式初态）；direction判⓪frm=None→forward",
        },
    )
    # t31: 未发送 → 待确认 — 能力验证预通知
    m.add_trans(
        tid="t31", entity="E-BMJL", dimension="通知状态",
        frm="未发送", to="待确认", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "未发送")),
        ],
        expected_results=["通知状态变更为待确认"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段能力验证预通知行",
        note={"comment": "direction判③frm未发送先于to待确认→forward；§19.1能力验证预通知行预通知状态=已发送/待确认，按§19.3枚举取待确认"},
    )
    # t32: 待确认 → 待审核 — 样品核查（inferred）
    m.add_trans(
        tid="t32", entity="E-BMJL", dimension="通知状态",
        frm="待确认", to="待审核", action="等待审核", role="样品管理员",
        preconditions=[
            precond(text="通知状态为待确认", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "待确认")),
        ],
        expected_results=["通知状态变更为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段样品核查行",
        note={
            "inferred": True,
            "comment": "推断依据：§19.3通知状态枚举含待审核，§19.1流程表样品核查行预通知状态保持已发送/待确认，状态推进至待审核为推断；direction判③frm待确认先于to待审核→forward",
        },
    )
    # t33: 待审核 → 退回 — 审核退回
    m.add_trans(
        tid="t33", entity="E-BMJL", dimension="通知状态",
        frm="待审核", to="退回", action="通知审核退回", role="技术主管",
        preconditions=[
            precond(text="通知状态为待审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "待审核")),
        ],
        expected_results=["通知状态变更为退回"],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="19.3通知状态枚举",
        note={"comment": "direction判③frm待审核先于to退回→forward，语义backward（业务回退，序判与语义冲突，语义优先）；禁止为序判成立重排states顺序"},
    )
    # t34: 待审核 → 已审核 — 技术主管审核通过
    m.add_trans(
        tid="t34", entity="E-BMJL", dimension="通知状态",
        frm="待审核", to="已审核", action="技术主管审核通过", role="技术主管",
        preconditions=[
            precond(text="通知状态为待审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "待审核")),
        ],
        expected_results=["通知状态变更为已审核"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知技术主管审核报告行",
        note={"comment": "direction判③frm待审核先于to已审核→forward"},
    )
    # t35: 已审核 → 已批准 — 授权签字人批准
    m.add_trans(
        tid="t35", entity="E-BMJL", dimension="通知状态",
        frm="已审核", to="已批准", action="授权签字人批准", role="授权签字人",
        preconditions=[
            precond(text="通知状态为已审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "已审核")),
        ],
        expected_results=["通知状态变更为已批准"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知授权签字人/证书实验室负责人批准行",
        note={"comment": "direction判③frm已审核先于to已批准→forward"},
    )

    # === E-SYS.实验室状态 ===
    # t36: 创建转换 — 新增实验室
    m.add_trans(
        tid="t36", entity="E-SYS", dimension="实验室状态",
        frm=None, to="待审核", action="新增实验室", role="能力验证参加者",
        preconditions=[], expected_results=["实验室记录创建，状态为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.1.1；20.3.1",
        note={"comment": "direction判⓪frm=None→forward；§20.3.1机构新增/修改实验室信息后需经管理用户审核通过"},
    )
        # t36: 退回 → 待审核 — 重新提交通知审核（inferred，解决 C02 退回无出边）
    m.add_trans(
        tid="t36", entity="E-BMJL", dimension="通知状态",
        frm="退回", to="待审核", action="重新提交通知审核", role="策划人员",
        preconditions=[
            precond(text="通知状态为退回", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "退回")),
        ],
        expected_results=["通知状态变更为待审核，重新进入审核流程"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1审核流程存在退回回路，退回后重新提交进入待审核；direction判④frm退回后于to待审核→backward，语义forward（重新提交为业务推进，语义优先）",
        },
    )

    # t37: 待审核 → 启用 — 审核通过
    m.add_trans(
        tid="t37", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核通过", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
        ],
        expected_results=["实验室状态变更为启用；为当前数据生成快照记录"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2",
        note={"comment": "direction判③frm待审核先于to启用→forward；§20.4.1.2审核通过时为当前数据生成快照记录"},
    )
    # t38: 待审核 → 已退回 — 审核退回
    m.add_trans(
        tid="t38", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="已退回", action="实验室审核退回", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果为退回修改时必须填写审核意见", ptype="constraint", ref=None,
                    note={"comment": "§20.4.1.2退回修改必须填写审核意见"}),
        ],
        expected_results=["实验室状态变更为已退回"],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="20.4.1.2",
        note={"comment": "direction判③frm待审核先于to已退回→forward，语义backward（业务回退，序判与语义冲突，语义优先）；禁止为序判成立重排states顺序"},
    )
    # t39: 已退回 → 待审核 — 重新提交
    m.add_trans(
        tid="t39", entity="E-SYS", dimension="实验室状态",
        frm="已退回", to="待审核", action="重新提交实验室", role="能力验证参加者",
        preconditions=[
            precond(text="实验室状态为已退回", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "已退回")),
        ],
        expected_results=["实验室状态变更为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3",
        note={"comment": "direction判④frm已退回后于to待审核→backward，语义forward（重新提交为业务推进，序判与语义冲突，语义优先）；禁止为序判成立重排states顺序"},
    )
    # t40: 启用 → 停用 — 停用（lateral，①explicit "停用"）
    m.add_trans(
        tid="t40", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="停用", action="停用实验室", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为启用", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变更为停用"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction判①explicit措辞'停用'→lateral；停用为挂起至主线外"},
    )
    # t41: 停用 → 启用 — 启用（resume，①explicit "启用"）
    m.add_trans(
        tid="t41", entity="E-SYS", dimension="实验室状态",
        frm="停用", to="启用", action="启用实验室", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为停用", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变更为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction判①explicit措辞'启用'→resume；自挂起恢复"},
    )

    # === E-BZK.标准库状态 ===
    # t42: 创建转换 — 新增标准库（inferred initial 启用）
    m.add_trans(
        tid="t42", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理人员",
        preconditions=[], expected_results=["标准库记录创建，状态为启用"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2",
        note={
            "inferred": True,
            "comment": "direction判⓪frm=None→forward；§20.4.2.2新增标准库状态必填，默认启用为推断隐式初态",
        },
    )
    # t43: 启用 → 停用 — 停用标准库（lateral，①explicit "停用"）
    m.add_trans(
        tid="t43", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="停用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库状态为启用", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态变更为停用；停用的标准库在项目创建等环节不可被选择"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction判①explicit措辞'停用'→lateral；停用为挂起至主线外"},
    )
    # t44: 停用 → 启用 — 启用标准库（resume，①explicit "启用"）
    m.add_trans(
        tid="t44", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="启用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库状态为停用", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态变更为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction判①explicit措辞'启用'→resume；自挂起恢复"},
    )

    # === E-PJL.评价状态 ===
    # t45: 创建转换 — 创建评价（inferred initial 待评价）
    m.add_trans(
        tid="t45", entity="E-PJL", dimension="评价状态",
        frm=None, to="待评价", action="创建评价", role="项目管理员",
        preconditions=[], expected_results=["评价记录创建，状态为待评价"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1",
        note={
            "inferred": True,
            "comment": "推断依据：§20.7.1新建项目时第一个被选择的评价人员默认作为评价组长；direction判⓪frm=None→forward；隐式初态",
        },
    )
    # t46: 待评价 → 评价中 — 评价人员开始评价（inferred；分支穿透评分方式）
    m.add_trans(
        tid="t46", entity="E-PJL", dimension="评价状态",
        frm="待评价", to="评价中", action="评价人员开始评价", role="评价人员",
        preconditions=[
            precond(text="评价状态为待评价", ptype="state_ref",
                    ref=state_ref("E-PJL", "评价状态", "待评价")),
        ],
        expected_results=[
            "若评分方式=分值，则评价人员录入分值，评价状态变更为评价中",
            "若评分方式=权重，则评价人员录入权重，评价状态变更为评价中",
        ],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="20.7.1.2",
        note={
            "inferred": True,
            "comment": "推断依据：§20.7.1.2协同评价；direction判③frm待评价先于to评价中→forward；分支穿透：评分方式影响录入字段",
            "branch_dimension": "评分方式",
        },
    )
    # t47: 评价中 → 已确认 — 评价确认（inferred）
    m.add_trans(
        tid="t47", entity="E-PJL", dimension="评价状态",
        frm="评价中", to="已确认", action="评价确认", role="评价人员",
        preconditions=[
            precond(text="评价状态为评价中", ptype="state_ref",
                    ref=state_ref("E-PJL", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变更为已确认；项目评价状态关闭；当前结果正式提交为项目的最终评价结果"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3",
        note={
            "inferred": True,
            "comment": "推断依据：§20.7.1.3确认操作使项目评价状态关闭；direction判③frm评价中先于to已确认→forward；评价组长为评价人员子角色，对齐已登记角色评价人员",
        },
    )
    # t48: 评价中 → 评价中 — 退回修改开启新一轮（self-loop，⑤forward+inferred）
    m.add_trans(
        tid="t48", entity="E-PJL", dimension="评价状态",
        frm="评价中", to="评价中", action="退回修改开启新一轮", role="评价人员",
        preconditions=[
            precond(text="评价状态为评价中", ptype="state_ref",
                    ref=state_ref("E-PJL", "评价状态", "评价中")),
        ],
        expected_results=["当前评价结果保存为历史结果；开启下一轮评价；评价状态保持评价中"],
        traits=["rollback"], direction="forward", priority="P1",
        source_ref="20.7.1.3",
        note={
            "inferred": True,
            "comment": "direction判⑤frm==to→forward+inferred，无状态迁移（开启新一轮评价但状态保持评价中）；§20.7.1.3退回修改保存历史结果并开启下一轮评价",
        },
    )

    # === E-SP.任务状态 ===
    # t49: 创建转换 — 创建审核任务（inferred initial 待审核）
    m.add_trans(
        tid="t49", entity="E-SP", dimension="任务状态",
        frm=None, to="待审核", action="创建审核任务", role="system",
        preconditions=[], expected_results=["审核任务创建，状态为待审核；短信通知相关负责人'您有一个新的xxx审核任务，请及时处理'"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.9.1.3",
        note={
            "inferred": True,
            "comment": "推断依据：§20.9.1.3用户通过表单或审核一个已存在的任务，生成一个新的审核任务；direction判⓪frm=None→forward；隐式初态",
        },
    )
    # t50: 待审核 → 已审核 — 审核通过（inferred）
    m.add_trans(
        tid="t50", entity="E-SP", dimension="任务状态",
        frm="待审核", to="已审核", action="审核通过", role="技术主管",
        preconditions=[
            precond(text="任务状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SP", "任务状态", "待审核")),
        ],
        expected_results=["任务状态变更为已审核"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.9.1.4",
        note={
            "inferred": True,
            "comment": "推断依据：§20.9.1.4批量审核选项同意/退回；direction判③frm待审核先于to已审核→forward；审核角色可能为技术主管/授权签字人/实验室负责人，按多角色审批链顺序",
        },
    )
    # t51: 待审核 → 已退回 — 审核退回（inferred；语义backward）
    m.add_trans(
        tid="t51", entity="E-SP", dimension="任务状态",
        frm="待审核", to="已退回", action="审核退回", role="技术主管",
        preconditions=[
            precond(text="任务状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SP", "任务状态", "待审核")),
        ],
        expected_results=["任务状态变更为已退回"],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="20.9.1.4",
        note={
            "inferred": True,
            "comment": "direction判③frm待审核先于to已退回→forward，语义backward（业务回退，序判与语义冲突，语义优先）；§20.9.1.4批量审核选项同意/退回；禁止为序判成立重排states顺序",
        },
    )
    # t52: 已退回 → 待审核 — 重新提交（inferred；语义forward）
    m.add_trans(
        tid="t52", entity="E-SP", dimension="任务状态",
        frm="已退回", to="待审核", action="重新提交审核", role="项目管理员",
        preconditions=[
            precond(text="任务状态为已退回", ptype="state_ref",
                    ref=state_ref("E-SP", "任务状态", "已退回")),
        ],
        expected_results=["任务状态变更为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.9.1.4",
        note={
            "inferred": True,
            "comment": "direction判④frm已退回后于to待审核→backward，语义forward（重新提交为业务推进，序判与语义冲突，语义优先）；禁止为序判成立重排states顺序",
        },
    )

        # t53: 已审核 → 已批准 — 证书批准（实验室负责人，消除 C22 角色缺口）
    m.add_trans(
        tid="t53", entity="E-SP", dimension="任务状态",
        frm="已审核", to="已批准", action="证书批准", role="实验室负责人",
        preconditions=[
            precond(text="任务状态为已审核", ptype="state_ref",
                    ref=state_ref("E-SP", "任务状态", "已审核")),
        ],
        expected_results=["任务状态变更为已批准；证书批准生效"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={
            "inferred": True,
            "comment": "推断依据：§19.1报告编制和结果通知'项目管理员编制证书项目，技术主管审核，实验室负责人批准'；direction判③frm已审核先于to已批准→forward",
        },
    )


    # ── Step 4.3 自检 ──
    # ① 核对 Step 3 的 target_transition 局部 tid 均有对应 add_trans：
    #   bd1 项目类型 → t02 ✓；bd2 评分方式 → t46 ✓；bd3 发票类型 → None（可缺省）✓
    # ② 核对 crud 操作 comment 是否回填对应转换标签：
    #   新建项目(t01)/报名(t08)/缴费(t20)/退款(t22)/新增实验室(t36)/新增标准库(t42)/创建评价(t45)/创建审核任务(t49)
    #   等均已在对应 add_trans 中建模；crud 操作与转换已一一对应

    # ── Step 4.4：因果 ──
    # 鉴别 4.5：Q1 项目状态报名中是否直接致报名记录创建？需用户报名操作 → 约束（precondition on t08 已表达）
    #   按 Q2 → 门禁不写入 causal，约束已在 t08.preconditions 表达
    # Q3 下级全完成上级自动推进 → 因果：未发现明确的"下级全完成上级自动推进"句式
    # 文档显式因果句式（X后Y变/B触发A/A依赖B完成）经全文扫描未发现状态间跨实体因果；§19.1流程表多列并排不构成因果依据
    # 故本流程不写入 add_causal 调用；如有遗漏由框架校验阶段补充提示

    # ── Step 5：约束补充 ──
    # 5.1 回访①：全文检索[待写入]无命中（4.5 判约束均已在 transition.preconditions 中表达，未产生 XC 形态约束）
    # 5.2 回访②：章节处置表引用的实体/标签均有对应产物 ✓
    # 5.3 回访③：prohibit_keywords 每条短语须有产物 source_ref 可定位
    #   "含有子项的记录不允许删除" → b08 (§20.4.2.10)
    #   "退款金额不能大于当前缴费金额" → t22.preconditions (§20.10.2.3)
    #   "接收人1和接收人2不能同时为空" → b10 (§20.5.1.4)
    #   "评价人员不能查看和修改其他评价人员的评价结果" → b14 (§20.7.1.2)

    # ── 5.1 invalid_transitions ──
    # 文档未出现"不允许/不可以从X到Y"明确禁止状态转换的句式
    # §20.4.2.10 含有子项的记录不允许删除 → 操作约束，非状态转换
    # §20.7.1.2 评价人员不能查看和修改其他评价人员的评价结果 → 权限约束，非状态转换
    # 故不生成 add_invalid 调用

    # ── 5.2 XC ──
    # x01: 4.5判 — 项目状态报名中（t02）→ 报名记录创建（t08）门禁
    # 鉴别 Q1：项目状态变报名中是否直接致报名记录变？需用户报名操作 → 约束
    # Q2：t08.preconditions 已表达门禁（项目处于报名中状态+实验室状态为启用）→ 门禁不写入 causal，但 XC 形态仍可表达
    m.add_xc(
        xid="x01",
        source_entity="E-XM", source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名待审核",
        target_transition="t08",
        xc_source="4.5判",
        desc="项目进入报名中状态后用户方可报名创建报名记录；4.5判鉴别为约束，承载门禁BR=b02；门禁已在t08.preconditions表达",
        source_ref="19.1实施阶段；20.3.1",
    )

    # x02: 分支差异 — 项目类型分支导致的约束差异
    m.add_xc(
        xid="x02",
        source_entity="E-XM", source_transition="t02", source_state="报名中",
        target_entity="E-XM", target_dimension="项目状态",
        target_condition="进行中",
        target_transition=None,
        xc_source="分支差异",
        desc="项目类型为能力验证时走§19.1流程，为测量审核时走§19.2流程；分支差异导致后续转换集与状态推进路径不同；承载BR=b15",
        source_ref="19.1；19.2",
    )

    # ── 5.3 BR ──
    # === 实验室信息 ===
    m.add_br(
        bid="b01", category="validation",
        desc="实验室状态枚举为待审核、启用、停用、已退回；机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-SYS"], source_ref="20.4.1.1；20.3.1",
        signal_type="field_constraint",
        note={"comment": "signal_type命中field_constraint（状态枚举）；category判validation（数据/业务有效性校验）"},
    )
    m.add_br(
        bid="b02", category="authorization",
        desc="实验室审核结果为退回修改时必须填写审核意见；审核结果为通过时审核意见可以为空",
        entities_involved=["E-SYS"], source_ref="20.4.1.2",
        signal_type="restrictive",
        constrained_entity="E-SYS",
        note={"comment": "signal_type命中'必须'；category判authorization（审核操作权限与必填约束）；constrained_entity判①操作对象实体E-SYS"},
    )
    m.add_br(
        bid="b03", category="validation",
        desc="实验室审核通过时为当前数据生成快照记录",
        entities_involved=["E-SYS"], source_ref="20.4.1.2",
        signal_type="restrictive",
        constrained_entity="E-SYS",
        note={"comment": "signal_type命中'为...时'（隐含必须）；category判validation（业务有效性校验）"},
    )
    m.add_br(
        bid="b04", category="display",
        desc="证明文件表单下提示文字：请上传营业执照或其他证书材料",
        entities_involved=["E-SYS"], source_ref="20.3.1",
        signal_type="display",
        note={"comment": "signal_type命中display（页面提示）；category判display（信息展示规则）"},
    )

    # === 标准库管理 ===
    m.add_br(
        bid="b05", category="validation",
        desc="标准库状态枚举为启用、停用；新增标准库时状态必填",
        entities_involved=["E-BZK"], source_ref="20.4.2.1；20.4.2.2",
        signal_type="field_constraint",
        note={"comment": "signal_type命中field_constraint（状态枚举+必填）；category判validation"},
    )
    m.add_br(
        bid="b06", category="authorization",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"], source_ref="20.4.2.5",
        signal_type="restrictive",
        constrained_entity="E-BZK",
        note={"comment": "signal_type命中'不可'；category判authorization（操作权限约束）；constrained_entity判①操作对象实体E-BZK"},
    )
    m.add_br(
        bid="b07", category="validation",
        desc="含有子项的记录不允许删除",
        entities_involved=["E-CSX", "E-BZK"], source_ref="20.4.2.10；20.4.3.4",
        signal_type="restrictive",
        constrained_entity="E-CSX",
        note={"comment": "signal_type命中'不允许'；category判validation（删除前业务校验）；constrained_entity判①操作对象实体E-CSX"},
    )

    # === 项目管理 ===
    m.add_br(
        bid="b08", category="authorization",
        desc="文件整理按钮仅对已结束的项目记录提供；整理完成后操作列显示查看归档按钮",
        entities_involved=["E-XM"], source_ref="20.5.1.1",
        signal_type="restrictive",
        constrained_entity="E-XM",
        note={"comment": "signal_type命中'仅对'（条件限制）；category判authorization（操作权限）；constrained_entity判①操作对象实体E-XM"},
    )
    m.add_br(
        bid="b09", category="validation",
        desc="消息发送表单中接收人1和接收人2不能同时为空；内容文本输入框必填；发送方式选择框必填",
        entities_involved=["E-XM"], source_ref="20.5.1.4",
        signal_type="restrictive",
        constrained_entity="E-XM",
        note={"comment": "signal_type命中'不能'+'必填'；category判validation（表单校验）；constrained_entity判①操作对象实体E-XM"},
    )
    m.add_br(
        bid="b10", category="validation",
        desc="项目新增表单新增监督员字段；导出项目通知书时填充到对应位置",
        entities_involved=["E-XM"], source_ref="20.5.1.5",
        signal_type="display",
        note={"comment": "signal_type命中display（表单字段新增）；category判validation（表单结构）"},
    )
    m.add_br(
        bid="b11", category="usability",
        desc="技术主管、实验室负责人、授权签字人备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"], source_ref="20.5.1.6",
        signal_type="display",
        note={"comment": "signal_type命中display（默认填充）；category判usability（交互易用性）"},
    )
    m.add_br(
        bid="b12", category="usability",
        desc="项目人员信息区域最后一行增加监督员字段；下拉框可以为空",
        entities_involved=["E-XM"], source_ref="20.5.1.5",
        signal_type="field_constraint",
        note={"comment": "signal_type命中field_constraint（字段约束可以为空）；category判usability"},
    )

    # === 已报名项目 ===
    m.add_br(
        bid="b13", category="validation",
        desc="已报名项目增加多次付款功能，不对付款金额进行校验限制",
        entities_involved=["E-BMJL", "E-JFD"], source_ref="20.5.2.1",
        signal_type="restrictive",
        constrained_entity="E-JFD",
        note={"comment": "signal_type命中'不对...进行校验'（限制性表述）；category判validation；constrained_entity判①操作对象实体E-JFD"},
    )
    m.add_br(
        bid="b14", category="timing",
        desc="证书距到期时间等于30天时通过邮件方式对用户进行提醒，并抄送项目管理员；系统在每天上午9点对系统中的证书信息进行查询",
        entities_involved=["E-FP"], source_ref="20.5.2.3；20.6.2.3",
        signal_type="restrictive",
        constrained_entity="E-FP",
        note={"comment": "signal_type命中'等于30天时'（时间条件）；category判timing（时间触发）；constrained_entity判①操作对象实体E-FP"},
    )

    # === 用户报名列表 ===
    m.add_br(
        bid="b15", category="notification",
        desc="管理人员对用户报名项目操作后使用短信方式对用户进行通知：报名审核通过/退回修改、发样通知、测试结果审核通过/退回、结果通知单发布",
        entities_involved=["E-BMJL", "E-XX"], source_ref="20.5.3.2；20.6.3.2",
        signal_type="restrictive",
        constrained_entity="E-XX",
        note={"comment": "signal_type命中'操作后...对用户进行通知'（条件性通知）；category判notification（通知触发）；constrained_entity判①操作对象实体E-XX（信息发送记录）"},
    )

    # === 项目评价 ===
    m.add_br(
        bid="b16", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJL"], source_ref="20.7.1.2",
        signal_type="restrictive",
        constrained_entity="E-PJL",
        note={"comment": "signal_type命中'只能'+'不能'；category判authorization（访问控制）；constrained_entity判①操作对象实体E-PJL"},
    )
    m.add_br(
        bid="b17", category="validation",
        desc="新建项目时第一个被选择的评价人员默认作为评价组长",
        entities_involved=["E-PJL", "E-XM"], source_ref="20.7.1",
        signal_type="restrictive",
        constrained_entity="E-PJL",
        note={"comment": "signal_type命中'第一个...默认'（隐含必须）；category判validation；constrained_entity判①操作对象实体E-PJL"},
    )
    m.add_br(
        bid="b18", category="validation",
        desc="评价项目完善表单中标号、名称、分值/权重、显示顺序为必填；说明/评分细则为选填",
        entities_involved=["E-PJL"], source_ref="20.7.1.1",
        signal_type="field_constraint",
        constrained_entity="E-PJL",
        note={"comment": "signal_type命中field_constraint（必填/选填）；category判validation；constrained_entity判①操作对象实体E-PJL；分支维度评分方式覆盖"},
    )
    m.add_br(
        bid="b19", category="computation",
        desc="统计规则由低值和高值组成；判断规则为大于等于低值，小于高值；成绩区间统计区用于动态统计报名实验室得分的区间分布",
        entities_involved=["E-PJL"], source_ref="20.7.1.3",
        signal_type="field_constraint",
        constrained_entity="E-PJL",
        note={"comment": "signal_type命中field_constraint（取值范围）；category判computation（数值计算与衍生值规则）；constrained_entity判①操作对象实体E-PJL"},
    )

    # === 业务审核 ===
    m.add_br(
        bid="b20", category="validation",
        desc="测量审核结果通知单审批流程合并为一个流程；流程处理者审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-SP"], source_ref="20.9.1.1",
        signal_type="restrictive",
        constrained_entity="E-SP",
        note={"comment": "signal_type命中'合并为'+'为...选择顺序'（限制性表述）；category判validation（流程结构校验）；constrained_entity判①操作对象实体E-SP"},
    )
    m.add_br(
    bid="b36", category="validation",
    desc="消息发送时接收人1：项目类型=能力验证时为选填；项目类型=测量审核时为必填且只包含当前报名实验室",
    entities_involved=["E-XM"],
    source_ref="20.5.1.4；20.6.1.2",
    signal_type="field_constraint",
    note={"branch_dimension": "项目类型",
          "comment": "signal_type命中'必填'；分支承载：两流程接收人约束为原文真实差异"},
    )
    m.add_br(
        bid="b37", category="validation",
        desc="评价项目完善与协同评价中：评分方式=分值时录入并显示分值；评分方式=权重时录入并显示权重",
        entities_involved=["E-PJL"],
        source_ref="20.7.1.1；20.7.1.2",
        signal_type="field_constraint",
        note={"branch_dimension": "评分方式",
          "comment": "signal_type命中'必填'；分支承载：录入字段随评分方式切换"},
    )

    m.add_br(
        bid="b21", category="validation",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
        entities_involved=["E-SP"], source_ref="20.9.1.6",
        signal_type="field_constraint",
        constrained_entity="E-SP",
        note={"comment": "signal_type命中field_constraint（数量限制4个以内）；category判validation；constrained_entity判①操作对象实体E-SP"},
    )
    m.add_br(
        bid="b22", category="display",
        desc="审核流程详情页完整展示审核流程，用不同颜色对各个状态的节点进行标记",
        entities_involved=["E-SP"], source_ref="20.9.1.7",
        signal_type="display",
        note={"comment": "signal_type命中display（颜色标记展示）；category判display（信息展示规则）；对称规则无操作主体，constrained_entity自动派生"},
    )

    # === 财务管理 ===
    m.add_br(
        bid="b23", category="validation",
        desc="缴费信息查询支持按业务类型（能力验证、测量审核）和发票类型（电子专票、电子普票）筛选；按时间维度（月、季度、年度、自选择时间范围）筛选",
        entities_involved=["E-JFD", "E-FP"], source_ref="20.10.1.1",
        signal_type="display",
        constrained_entity="E-JFD",
        note={
            "comment": "signal_type命中display（查询参数）；category判validation（查询校验）；constrained_entity判①操作对象实体E-JFD；分支维度发票类型覆盖",
            "branch_dimension": "发票类型",
        },
    )
    m.add_br(
        bid="b24", category="usability",
        desc="发票上传支持多次分批上传；上传后发票列表显示已上传发票，可移除文件（表单提交后生效）",
        entities_involved=["E-FP"], source_ref="20.10.2.2",
        signal_type="usability",
        constrained_entity="E-FP",
        note={"comment": "signal_type命中usability（'支持'）；category判usability（交互易用性）；constrained_entity判①操作对象实体E-FP"},
    )
    m.add_br(
        bid="b25", category="computation",
        desc="退款后更新项目费用为实际付款金额；实际付款=付款金额-退款金额；退款金额多次累加；退款金额使用红色字体且大于0时显示；退款金额不能大于当前缴费金额",
        entities_involved=["E-JFD", "E-BMJL", "E-XM"], source_ref="20.10.2.3",
        signal_type="restrictive",
        constrained_entity="E-JFD",
        note={"comment": "signal_type命中'不能大于'（限制性表述）；category判computation（数值计算与衍生值规则）；constrained_entity判①操作对象实体E-JFD"},
    )

    # === 信息发送记录 ===
    m.add_br(
        bid="b26", category="authorization",
        desc="只有系统管理员和项目管理员可以查看信息发送记录",
        entities_involved=["E-XX"], source_ref="20.4.4.1",
        signal_type="restrictive",
        constrained_entity="E-XX",
        note={"comment": "signal_type命中'只有'（操作权限限制）；category判authorization（访问控制）；constrained_entity判①操作对象实体E-XX；§20.4.4.1使用'系统管理员'口径，§5-#17登记r12系统管理人员，存在名称口径不一致按r12对齐"},
    )

    # === 其他 ===
    m.add_br(
        bid="b27", category="validation",
        desc="对关键操作进行留痕处理，系统自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-XM", "E-BMJL", "E-SYS", "E-BZK", "E-PJL", "E-SP"],
        source_ref="20.11.1.2",
        signal_type="restrictive",
        constrained_entity="E-XM",
        note={"comment": "signal_type命中'对...进行'（隐含必须）；category判validation（审计日志）；对称规则无单一操作主体，constrained_entity任一involved实体代表，note注明'代表实体'"},
    )
    m.add_br(
        bid="b28", category="validation",
        desc="历史项目列表支持按项目名称、项目类型、子领域、所属年度独立或组合查询",
        entities_involved=["E-LSPJ"], source_ref="20.11.1.1",
        signal_type="display",
        constrained_entity="E-LSPJ",
        note={"comment": "signal_type命中display（查询参数）；category判validation（查询校验）；constrained_entity判①操作对象实体E-LSPJ"},
    )

    return m
