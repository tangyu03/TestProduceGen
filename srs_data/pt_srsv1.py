"""网数中心能力验证服务平台升级维护项目-需求分析与设计1116 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    # ── 标签分配表 ──
    # 实体: E-SYS(实验室信息) | E-BZK(标准库) | E-CSX(测试项) | E-ZLY(子领域) | E-XX(信息发送记录)
    #        | E-XM(项目) | E-BMJL(报名记录) | E-PJ(项目评价) | E-SP(流程审批)
    #        | E-JFD(缴费信息) | E-LSPJ(历史项目)
    # 转换: t01-t06(E-XM.项目状态) | t07-t08(E-XM.样品状态)
    #        | t10-t16(E-BMJL.通知状态) | t20-t30(E-BMJL.报名记录状态)
    #        | t40-t43(E-BMJL.报名记录样品状态) | t50-t51(E-BMJL.费用状态) | t60-t61(E-BMJL.发票状态)
    #        | t70-t75(E-SYS.实验室状态) | t80-t82(E-BZK.标准库状态) | t90-t94(E-PJ.评价状态)
    #        | t100-t102(E-SP.审批状态)
    # XC: x01-x06 | BR: b01-b30 | IT: 无（原文无"不允许从X状态到Y状态"的明确禁止措辞）
    # 角色: r01(实验室负责人) | r02(技术主管) | r03(授权签字人) | r04(策划人员) | r05(项目管理员)
    #        | r06(样品制备人员) | r07(样品管理员) | r08(评价人员) | r09(统计人员) | r10(质量专员)
    #        | r11(财务管理人员) | r12(系统管理人员) | r13(能力验证参加者) | r14(监督员)
    # 分支维度: 项目类型@E-XM | 评分方式@E-PJ
    # ── 章节处置表 ──
    # 1-3 项目要求/设计要求/功能要求 → 不适用：纯非功能性/总体说明，无状态语义
    # 4 系统功能架构分析 → 不适用：纯总体描述
    # 5-18 用户角色分析 → r01-r14（Step 0.5 承载，无独立实体）
    # 19.1 能力验证提供者流程 → E-XM(项目状态/样品状态)、E-BMJL(报名记录状态族)；t01-t06, t10-t30
    # 19.2 测量审核提供者流程 → E-XM(项目类型=测量审核分支)、E-BMJL；t01b，与 19.1 共用 t02b-t06
    # 19.3 项目状态分析 → E-XM、E-BMJL 的 state_dimensions（权威枚举来源）
    # 19.4-19.5 参加者工作流程分析 → 不适用：纯叙述，状态归属已在提供者流程承载
    # 20.2 首页 → b01(new标识15天)、b02(待办统计)；其余不适用：纯展示无状态语义
    # 20.3 基本信息 → E-SYS
    # 20.4 系统管理 → E-SYS、E-BZK、E-CSX、E-ZLY、E-XX；b03-b10
    # 20.5 能力验证 → E-XM(项目类型=能力验证分支)、E-BMJL、E-PJ；t01,t02-t06,t10-t30,t90-t94；b11-b18
    # 20.6 测量审核 → E-XM(项目类型=测量审核分支)、E-BMJL；t01b；与 20.5 共用 t02-t06,t10-t30；b11-b18 共用
    # 20.7 项目评价 → E-PJ；t90-t94；b19-b22
    # 20.8 统计分析 → E-LSPJ；b23(时间快速录入)；其余不适用：纯查询/展示
    # 20.9 业务审核 → E-SP；t100-t102；b24-b26
    # 20.10 财务管理 → E-JFD、E-BMJL(费用状态/发票状态)；b27-b30
    # 20.11 其他 → E-LSPJ；b31(留痕)、b32(UI风格)
    # 21 非功能性需求 → 不适用：纯非功能性要求

    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116",
        document_scope="19.1-19.5 系统流程分析；20.2-20.11 系统功能需求分析；非功能性（21）不在范围"
    )

    # ===== Step 0：动词种子词表 =====
    m.set_prohibition_config(config={
        "action_verbs": [
            "新增", "修改", "删除", "查询", "重置", "审核", "通过", "退回", "停用", "启用",
            "提交", "保存", "审批", "批准", "签发", "归档", "整理", "发放", "发送", "上传",
            "下载", "导入", "导出", "登录", "退出", "查看", "编辑", "选择", "选入", "纳入",
            "启动", "暂停", "结束", "重启", "确认", "撤销", "评价", "统计", "缴费", "退款",
            "开票", "报名", "选为", "执行", "签章", "测试", "签发", "归还", "借出", "复制",
        ],
        "prohibit_keywords": [
            "不能同时为空",
            "不能大于当前缴费金额",
            "不可以删除",
            "不允许删除",
            "不可被选择",
            "不能查看和修改其他评价人员",
        ],
    })

    # ===== Step 0.5：角色与权限 =====
    m.add_role(id="r01", name="实验室负责人")
    m.add_role(id="r02", name="技术主管")
    m.add_role(id="r03", name="授权签字人")
    m.add_role(id="r04", name="策划人员")
    m.add_role(id="r05", name="项目管理员")
    m.add_role(id="r06", name="样品制备人员")
    m.add_role(id="r07", name="样品管理员")
    m.add_role(id="r08", name="评价人员")
    m.add_role(id="r09", name="统计人员")
    m.add_role(id="r10", name="质量专员")
    m.add_role(id="r11", name="财务管理人员")
    m.add_role(id="r12", name="系统管理人员", readonly=True)
    m.add_role(id="r13", name="能力验证参加者")
    m.add_role(id="r14", name="监督员")

    m.add_permission(role="系统管理人员",
                     operations=["查询实验室", "审核实验室", "修改实验室", "停用实验室", "启用实验室",
                                 "新增标准库", "修改标准库", "删除标准库", "停用标准库", "启用标准库",
                                 "管理测试项", "新增测试项", "修改测试项", "删除测试项",
                                 "查询信息发送记录", "查看消息详情", "查询子领域", "管理子领域测试项",
                                 "新增子领域测试项", "删除子领域测试项"])
    m.add_permission(role="项目管理员",
                     operations=["新增项目", "修改项目", "查询项目", "删除项目", "上传附件", "下载附件",
                                 "文件整理", "查看归档", "上传归档文件", "打包下载归档", "代码导入",
                                 "批量处理", "上传结果通知单", "上传证书", "提交审核", "消息发送",
                                 "上传付款单", "上传预通知文件", "导出项目", "查询已报名项目"])
    m.add_permission(role="评价人员",
                     operations=["评价", "导出评价结果", "完善评价项目", "另存常用测试项"])
    m.add_permission(role="策划人员",
                     operations=["编制结果报告", "编制结果通知单", "编制证书", "编制缴费通知书",
                                 "编制任务通知书", "编制设计方案", "编制作业指导书", "编制评价细则",
                                 "编制样品制备方案"])
    m.add_permission(role="技术主管",
                     operations=["审核报告", "审核通知单", "审核证书", "审核物品配置方案", "审核评价细则"])
    m.add_permission(role="实验室负责人",
                     operations=["批准证书", "批准邀请函", "批准结果通知单", "批准结果报告"])
    m.add_permission(role="授权签字人",
                     operations=["批准结果报告", "批准结果通知单", "批准使用认可标识"])
    m.add_permission(role="样品管理员",
                     operations=["样品入库", "样品出库", "样品核查", "样品发放", "样品领用登记"])
    m.add_permission(role="样品制备人员",
                     operations=["样品制备", "样品配置", "一致性测试"])
    m.add_permission(role="财务管理人员",
                     operations=["查询缴费信息", "导出缴费信息", "修改财务备注", "上传发票", "缴费退款"])
    m.add_permission(role="能力验证参加者",
                     operations=["报名项目", "上传付款单", "上传缴费证明", "上传测试结果",
                                 "下载报告", "下载证书", "下载预通知", "查询已报名项目", "意见反馈"])
    m.add_permission(role="统计人员", operations=["统计分析", "查询统计"])
    m.add_permission(role="质量专员", operations=["查询统计", "业务上报统计"])

    # ===== Step 1：实体 =====

    # ── E-SYS 实验室信息 ──
    m.add_entity(
        id="E-SYS", name="实验室信息",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名；列表字段含实验室名称、统一社会信用代码、状态、法人名称、企业类型、企业规模、CNAS、CMA、邮箱、座机号码、地址、联系人、联系电话、默认实验室、证明文件",
        type="managed", tags=["multi-state"],
        attributes=[
            attr(name="实验室名称", desc="文本输入框；模糊查询"),
            attr(name="统一社会信用代码", desc="文本输入框；模糊查询"),
            attr(name="法人名称", desc="文本"),
            attr(name="企业类型", desc="文本"),
            attr(name="企业规模", desc="文本"),
            attr(name="CNAS", desc="已获 CNAS 认可；CNAS 证书号"),
            attr(name="CMA", desc="已获 CMA 认可；CMA 证书编号"),
            attr(name="邮箱", desc="文本"),
            attr(name="座机号码", desc="文本"),
            attr(name="地址", desc="行政区域+详细地址"),
            attr(name="联系人", desc="文本"),
            attr(name="联系电话", desc="文本"),
            attr(name="默认实验室", desc="标识字段"),
            attr(name="证明文件", desc="请上传营业执照或其他证书材料；链接可下载"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "启用", "停用", "退回修改"],
                "initial": "待审核",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "状态枚举来源：20.3.1（状态包括：待审核、启用、停用、退回修改）；20.4.1.2 审核退回后状态字段值称谓为'已退回'，与 20.3.1 '退回修改'不一致——按歧义显性化并列：本维度取 20.3.1 列举值，20.4.1.2 退回审核后写入实际值为'已退回'，由框架收集；ambiguity: 实验室退回态在 20.3.1 与 20.4.1.2 命名不一致（退回修改 vs 已退回）"},
            },
        ],
        operations=[
            op(name="查询实验室", category="query",
               expected_results=["分页展示符合条件的数据记录"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员")),
            op(name="审核实验室", category="ui",
               expected_results=["弹出审核窗口；通过则状态变为启用并生成快照记录；退回修改则状态变为已退回"],
               source_ref="20.4.1.2",
               note=N(role="系统管理人员")),
            op(name="修改实验室", category="crud",
               expected_results=["弹出修改窗口，提交后修改内容保存"],
               source_ref="20.4.1.3",
               note=N(role="系统管理人员")),
            op(name="停用实验室", category="config",
               expected_results=["状态立即变为停用，列表刷新"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员")),
            op(name="启用实验室", category="config",
               expected_results=["状态立即变为启用，列表刷新"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-BZK 标准库 ──
    m.add_entity(
        id="E-BZK", name="标准库",
        desc="代表一个完整的、可被引用的标准集合，如GB/T 12345-2020 电子产品安全标准；通过分层级维护方式管理其下属测试项和参数；停用的标准库在项目创建等环节不可被选择",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="文本输入框；必填；模糊查询"),
            attr(name="标准库名称", desc="文本输入框；必填；模糊查询"),
            attr(name="描述", desc="文本输入框；选填"),
            attr(name="状态", desc="单选框；必填；包含启用、停用两个状态", is_config=True),
            attr(name="创建时间", desc="系统记录"),
        ],
        state_dimensions=[
            {
                "dimension_name": "标准库状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "状态枚举来源：20.4.2.1 列表展示字段（状态：启用/停用）；20.4.2.2 新增表单状态单选框包含启用、停用"},
            },
        ],
        operations=[
            op(name="查询标准库", category="query",
               expected_results=["分页展示符合条件的数据记录"],
               source_ref="20.4.2.1",
               note=N(role="系统管理人员")),
            op(name="新增标准库", category="crud",
               expected_results=["弹出表单对话框，提交后新增记录"],
               source_ref="20.4.2.2",
               note=N(role="系统管理人员")),
            op(name="修改标准库", category="crud",
               expected_results=["弹出编辑表单，提交后保存修改"],
               source_ref="20.4.2.3",
               note=N(role="系统管理人员")),
            op(name="删除标准库", category="crud",
               expected_results=["弹出二次确认框，确认后删除"],
               source_ref="20.4.2.4",
               note=N(role="系统管理人员")),
            op(name="停用标准库", category="config",
               expected_results=["弹出二次确认框，确认后状态立即变为停用，列表刷新"],
               source_ref="20.4.2.5",
               note=N(role="系统管理人员")),
            op(name="启用标准库", category="config",
               expected_results=["弹出二次确认框，确认后状态立即变为启用，列表刷新"],
               source_ref="20.4.2.5",
               note=N(role="系统管理人员")),
            op(name="管理测试项", category="ui",
               expected_results=["跳转或新标签页进入该标准库的测试项管理界面"],
               source_ref="20.4.2.6",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-CSX 测试项 ──
    m.add_entity(
        id="E-CSX", name="测试项",
        desc="由编号和名称组成的一组数据；测试项下可以有子测试项；存在于标准库或子领域下；含有子项的记录不允许删除",
        type="managed", tags=[],
        attributes=[
            attr(name="标号", desc="文本输入框；必填"),
            attr(name="名称", desc="文本输入框；必填"),
            attr(name="父测试项", desc="可挂载于标准库或子领域下，支持多级嵌套"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud",
               expected_results=["弹出表单对话框，提交后新增记录；此处只能新增一级测试项"],
               source_ref="20.4.2.8",
               note=N(role="系统管理人员")),
            op(name="修改测试项", category="crud",
               expected_results=["打开编辑表单弹窗，系统校验后保存，刷新列表数据"],
               source_ref="20.4.2.9",
               note=N(role="系统管理人员")),
            op(name="删除测试项", category="crud",
               expected_results=["弹出二次确认框，确认后删除；含有子项的记录不允许删除"],
               source_ref="20.4.2.10",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-ZLY 子领域 ──
    m.add_entity(
        id="E-ZLY", name="子领域",
        desc="本次升级对子领域下的测试项管理方式调整为选择方式，数据来源于标准库",
        type="managed", tags=[],
        attributes=[
            attr(name="子领域名称", desc="文本"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询子领域", category="query",
               expected_results=["下拉列表展示所有子领域信息"],
               source_ref="20.4.3.2",
               note=N(role="系统管理人员")),
            op(name="管理子领域测试项", category="ui",
               expected_results=["跳转或新标签页进入该子领域的测试项管理界面"],
               source_ref="20.4.3.1",
               note=N(role="系统管理人员")),
            op(name="新增子领域测试项", category="crud",
               expected_results=["弹出表单对话框，选择标准库及测试项后保存，新标准库出现在列表中"],
               source_ref="20.4.3.3",
               note=N(role="系统管理人员")),
            op(name="删除子领域测试项", category="crud",
               expected_results=["弹出二次确认框，确认后删除；存在子项的数据不可以删除"],
               source_ref="20.4.3.4",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-XX 信息发送记录 ──
    m.add_entity(
        id="E-XX", name="信息发送记录",
        desc="系统发送记录模块用于记录系统中的信息发送历史，记录内容包含发送方式、接收人、发送时间、发送人、发送结果；只有系统管理员和项目管理员可以查看",
        type="managed", tags=[],
        attributes=[
            attr(name="接收号码", desc="文本；模糊匹配查询"),
            attr(name="发送方式", desc="下拉列表精确匹配；选项有：短信、邮件、站内信"),
            attr(name="发送时间", desc="时间范围选择框；精确匹配"),
            attr(name="发送人", desc="系统记录"),
            attr(name="消息标题", desc="文本"),
            attr(name="消息内容", desc="文本"),
            attr(name="发送结果", desc="系统记录"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query",
               expected_results=["分页展示符合条件的数据记录"],
               source_ref="20.4.4.1",
               note=N(role=["系统管理人员", "项目管理员"])),
            op(name="查看消息详情", category="ui",
               expected_results=["查看消息详细内容"],
               source_ref="20.4.4.1",
               note=N(role=["系统管理人员", "项目管理员"])),
        ],
    )

    # ── E-XM 项目 ──
    m.add_entity(
        id="E-XM", name="项目",
        desc="能力验证/测量审核项目；项目类型在创建时确定并影响后续流转；包含项目准备、方案设计、实施、评价统计、报告编制、归档等阶段；项目状态与样品状态独立推进",
        type="core", tags=["multi-state", "collaborative", "approvable", "expirable", "configurable"],
        attributes=[
            attr(name="项目编号", desc="系统生成"),
            attr(name="项目名称", desc="文本"),
            attr(name="项目类型", desc="能力验证 / 测量审核；创建时定、影响后续流转", is_config=True),
            attr(name="产品类型", desc="下拉框；精确匹配；系统内所有产品信息"),
            attr(name="子领域", desc="关联 E-ZLY"),
            attr(name="所属年度", desc="年度"),
            attr(name="依据标准", desc="关联标准库"),
            attr(name="项目费用", desc="金额；财务可改"),
            attr(name="财务备注", desc="财务管理可修改"),
            attr(name="技术主管", desc="项目人员；候选人单一时默认填充"),
            attr(name="实验室负责人", desc="项目人员；候选人单一时默认填充"),
            attr(name="授权签字人", desc="项目人员；候选人单一时默认填充"),
            attr(name="监督员", desc="项目人员；下拉框可为空；导出项目通知书时填充到对应位置"),
            attr(name="评价人员", desc="多选；第一个被选择的评价人员默认作为评价组长"),
            attr(name="项目管理员", desc="项目人员"),
            attr(name="评分方式", desc="分值 / 权重", is_config=True),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（验证项目状态.项目状态）；19.1/19.2 流程表作为辅助参考，未列出新状态"},
            },
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查"],
                "initial": "待核查",
                "terminal": ["已核查"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（验证项目状态.样品状态）；流程表 19.1/19.2 中出现的 '已发样/待发样/已还样' 等措辞系流程表散文描述，不覆盖枚举表"},
            },
        ],
        operations=[
            op(name="新增项目", category="crud",
               expected_results=["进入项目新增表单页面；项目人员字段在候选人单一时默认填充；监督员字段可选填"],
               source_ref="20.5.1.5；20.5.1.6；20.6.1.3；20.6.1.4",
               note=N(role="项目管理员")),
            op(name="修改项目", category="crud",
               expected_results=["弹出修改表单，提交后修改内容保存"],
               source_ref="20.5.1",
               note=N(role="项目管理员")),
            op(name="查询项目", category="query",
               expected_results=["分页展示符合条件的数据记录"],
               source_ref="20.5.1",
               note=N(role="项目管理员")),
            op(name="删除项目", category="crud",
               expected_results=["删除项目记录"],
               source_ref="20.2.3；20.5.1",
               note=N(role="项目管理员")),
            op(name="文件整理", category="ui",
               expected_results=["系统开启整理任务并提示'归档任务已开启，请稍后查看'；整理完成后显示【查看归档】按钮"],
               source_ref="20.5.1.1；20.6.1.1",
               note=N(role="项目管理员")),
            op(name="查看归档", category="ui",
               expected_results=["进入归档数据查看页面；用户可查看并补充归档信息"],
               source_ref="20.5.1.1；20.6.1.1",
               note=N(role="项目管理员")),
            op(name="上传归档文件", category="file",
               expected_results=["弹出上传文件表单弹窗；补充文件的项目阶段为其它"],
               source_ref="20.5.1.1；20.6.1.1",
               note=N(role="项目管理员")),
            op(name="打包下载归档", category="file",
               expected_results=["下载为zip格式，内含清单文件和按项目阶段命名的目录"],
               source_ref="20.5.1.1；20.6.1.1",
               note=N(role="项目管理员")),
            op(name="代码导入", category="file",
               expected_results=["弹出代码导入表单窗口，提交后导入报名机构三方代码"],
               source_ref="20.5.1.2",
               note=N(role="项目管理员")),
            op(name="批量处理", category="ui",
               expected_results=["跳转到报名信息批量处理页面；可集中上传通知单与证书并批量提交审核"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="上传结果通知单", category="file",
               expected_results=["弹出上传表单弹窗，提交后保存文件"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="上传证书", category="file",
               expected_results=["弹出上传表单弹窗，提交后保存文件"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="提交审核", category="ui",
               expected_results=["对选择的记录进行任务提交操作；如未选择记录将提示用户选择记录信息"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员")),
            op(name="消息发送", category="ui",
               expected_results=["进入消息发送页面；如系统验证通过则将消息按选择的方式进行发送"],
               source_ref="20.5.1.4；20.6.1.2",
               note=N(role="项目管理员")),
            op(name="导出项目", category="file",
               expected_results=["下载评价结果文件"],
               source_ref="20.7.1.4",
               note=N(role="评价人员")),
            op(name="完善评价项目", category="ui",
               expected_results=["进入完善页面；评价组长可编辑完善评价项目及评价细则内容"],
               source_ref="20.7.1.1",
               note=N(role="评价人员")),
            op(name="另存常用测试项", category="ui",
               expected_results=["弹出常用项新增表单，保存后常用项出现在下拉列表中"],
               source_ref="20.5.1.7；20.6.1.5；20.7.1.1",
               note=N(role=["项目管理员", "评价人员"])),
            op(name="上传付款单", category="file",
               expected_results=["弹出付款录入表单，提交后保存付款记录；支持多次付款不对付款金额进行校验限制"],
               source_ref="20.5.2.1；20.6.2.1",
               note=N(role="能力验证参加者")),
            op(name="上传预通知文件", category="file",
               expected_results=["文件下载Tab下可下载预通知文件"],
               source_ref="20.5.2.2；20.5.3.1；20.6.2.2；20.6.3.1",
               note=N(role="能力验证参加者")),
            op(name="修改财务备注", category="crud",
               expected_results=["弹出备注修改表单弹窗，提交后保存备注内容"],
               source_ref="20.10.2.1",
               note=N(role="财务管理人员")),
            op(name="上传发票", category="file",
               expected_results=["弹出发票上传表单弹窗；支持多次分批上传发票；表单提交后生效"],
               source_ref="20.10.2.2",
               note=N(role="财务管理人员")),
        ],
    )

    # ── E-BMJL 报名记录 ──
    m.add_entity(
        id="E-BMJL", name="报名记录",
        desc="参加者就项目提交的报名记录；同一记录生命周期中包含通知状态、报名记录状态、报名记录样品状态、费用状态、发票状态共五个状态维度，强耦合、共享操作主体；费用状态/发票状态由财务管理与参加者共同维护",
        type="core", tags=["multi-state", "collaborative", "expirable"],
        attributes=[
            attr(name="报名编号", desc="系统生成；用于查询与显示"),
            attr(name="项目编号", desc="关联 E-XM"),
            attr(name="实验室名称", desc="关联 E-SYS"),
            attr(name="统一社会信用代码", desc="关联 E-SYS"),
            attr(name="行政区划", desc="实验室所在地域"),
            attr(name="报名时间", desc="时间戳"),
            attr(name="实施状态", desc="展示字段；与报名记录状态对应"),
            attr(name="付款状态", desc="展示字段；与费用状态对应"),
            attr(name="评价得分", desc="评价完成后回填"),
            attr(name="评价结果", desc="评价完成后回填"),
            attr(name="退款金额", desc="多次退款金额做累加处理；红色字体且大于0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额=实际付款"),
            attr(name="管理备注", desc="用于记录退款原因等内容"),
            attr(name="证书编号", desc="证书签发后回填"),
            attr(name="证书到期时间", desc="用于到期前30天提醒"),
            attr(name="机构代码", desc="导入的报名机构三方代码"),
        ],
        state_dimensions=[
            {
                "dimension_name": "通知状态",
                "states": ["未发送", "待确认", "待审核", "退回", "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已批准"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（报名记录状态.通知状态）；19.1/19.2 流程表'预通知状态'列与本维度同义"},
            },
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交",
                          "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（报名记录状态.报名记录状态）"},
            },
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（报名记录状态.报名记录样品状态）"},
            },
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（报名记录状态.费用状态）"},
            },
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "inferred": [],
                "note": {"comment": "状态枚举来源：19.3 项目状态分析表（报名记录状态.发票状态）"},
            },
        ],
        operations=[
            op(name="报名项目", category="crud",
               expected_results=["参加者提交报名信息；记录状态初始化为报名待审核"],
               source_ref="19.1实施阶段；19.2项目准备阶段",
               note=N(role="能力验证参加者")),
            op(name="审核报名", category="ui",
               expected_results=["通过则报名记录状态变为报名成功；退回修改则报名记录状态变为报名退回；并发送短信通知用户"],
               source_ref="20.5.3.2；20.6.3.2；19.1实施阶段",
               note=N(role="项目管理员")),
            op(name="缴费", category="crud",
               expected_results=["参加者上传付款单；费用状态变为已缴费；支持多次付款不对付款金额进行校验限制"],
               source_ref="20.5.2.1；20.6.2.1；19.1实施阶段",
               note=N(role="能力验证参加者")),
            op(name="上传测试结果", category="file",
               expected_results=["参加者提交测试结果；报名记录状态变为结果已提交"],
               source_ref="19.1实施阶段；19.4",
               note=N(role="能力验证参加者")),
            op(name="发样", category="ui",
               expected_results=["样品管理员发放样品；报名记录样品状态推进；并发送短信'您xxxx项目的样品已发出，请知悉'"],
               source_ref="19.1实施阶段；20.5.3.2；20.6.3.2",
               note=N(role="样品管理员")),
            op(name="样品核查", category="ui",
               expected_results=["样品状态变为已核查"],
               source_ref="19.1实施阶段；19.2实施阶段",
               note=N(role="样品管理员")),
            op(name="样品领用登记", category="crud",
               expected_results=["登记样品领用信息；通知状态变为待审核"],
               source_ref="19.2实施阶段",
               note=N(role="样品管理员")),
            op(name="结果退回修改", category="ui",
               expected_results=["报名记录状态变为结果退回修改；并发送短信'您xxxx项目测试报告审核未通过，请知悉'"],
               source_ref="19.1报告编制；20.5.3.2；20.6.3.2",
               note=N(role=["技术主管", "授权签字人"])),
            op(name="编制结果报告", category="crud",
               expected_results=["策划人员编制结果报告；报名记录状态推进至报告/证书审核中"],
               source_ref="19.1报告编制；19.2报告编制",
               note=N(role="策划人员")),
            op(name="审核报告", category="ui",
               expected_results=["技术主管审核；通过则推进；退回则状态回退；并发送短信通知"],
               source_ref="19.1报告编制；20.5.3.2；20.6.3.2",
               note=N(role="技术主管")),
            op(name="批准结果报告", category="ui",
               expected_results=["授权签字人批准；推进状态"],
               source_ref="19.1报告编制；19.2报告编制",
               note=N(role="授权签字人")),
            op(name="批准结果通知单", category="ui",
               expected_results=["授权签字人批准结果通知单"],
               source_ref="19.2报告编制",
               note=N(role="授权签字人")),
            op(name="批准证书", category="ui",
               expected_results=["实验室负责人批准证书"],
               source_ref="19.1报告编制",
               note=N(role="实验室负责人")),
            op(name="发放结果报告和证书", category="ui",
               expected_results=["报名记录状态变为报告/证书已发布；并发送短信'您xxx项目的结果通知单已发布，请知悉'"],
               source_ref="19.1报告编制；19.2报告编制；20.5.3.2；20.6.3.2",
               note=N(role="项目管理员")),
            op(name="缴费退款", category="crud",
               expected_results=["弹出付款单退款表单弹窗；退款金额累加；实际付款=付款金额-退款金额；项目费用更新为实际付款金额"],
               source_ref="20.10.2.3",
               note=N(role="财务管理人员")),
            op(name="上传缴费证明", category="file",
               expected_results=["参加者上传缴费证明文件"],
               source_ref="19.4",
               note=N(role="能力验证参加者")),
            op(name="下载报告", category="file",
               expected_results=["参加者下载《能力验证计划结果报告》"],
               source_ref="19.4",
               note=N(role="能力验证参加者")),
            op(name="下载证书", category="file",
               expected_results=["参加者下载《能力验证合格证书》"],
               source_ref="19.4",
               note=N(role="能力验证参加者")),
            op(name="下载预通知", category="file",
               expected_results=["文件下载Tab下下载预通知文件"],
               source_ref="20.5.2.2；20.5.3.1；20.6.2.2；20.6.3.1",
               note=N(role="能力验证参加者")),
            op(name="查询已报名项目", category="query",
               expected_results=["参加者查看已报名项目列表"],
               source_ref="20.5.2；20.6.2",
               note=N(role="能力验证参加者")),
            op(name="意见反馈", category="crud",
               expected_results=["提交意见反馈内容"],
               source_ref="5-18 用户角色分析",
               note=N(role="能力验证参加者")),
        ],
    )

    # ── E-PJ 项目评价 ──
    m.add_entity(
        id="E-PJ", name="项目评价",
        desc="评价人员对报名项目进行评价；支持分值和权重两种评价方式；支持协同评价；新建项目时第一个被选择的评价人员默认作为评价组长；评价组长可在评价结果确认页面查看各评价人员的评价结果并对最终结果进行确认",
        type="core", tags=["approvable", "collaborative", "configurable", "multi-state"],
        attributes=[
            attr(name="评价项目", desc="测试项目列表，支持多级嵌套"),
            attr(name="评价细则", desc="被标记为调整状态的评价细则将显示不同的背景颜色"),
            attr(name="分值/权重", desc="文本框；必填；受评分方式分支影响"),
            attr(name="说明/评分细则", desc="文本框；选填"),
            attr(name="显示顺序", desc="文本框；必填；用来控制数据的展示顺序"),
            attr(name="及格分", desc="评价确认页面录入；录入后跟随其他结果一起记录到系统中"),
            attr(name="评价组长", desc="第一个被选择的评价人员默认作为评价组长"),
            attr(name="评分方式", desc="分值 / 权重；影响计算与展示，不影响转换；is_config", is_config=True),
            attr(name="历史结果", desc="可保存为历史结果；可下载"),
            attr(name="统计规则", desc="由低值、高值组成；判断规则为大于等于低值，小于高值"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["待评价", "评价中", "退回修改", "已确认"],
                "initial": "待评价",
                "terminal": ["已确认"],
                "inferred": ["待评价", "评价中"],
                "note": {"comment": "推断依据：19.1/19.2 流程表中'评价人员进行评价'/'评价组长结果确认'/'退回修改开启下一轮评价'等措辞指向评价流程存在评价前态与进行态；待评价/评价中未在原文逐字命名（原文仅见'退回修改'/'已确认'），按隐式初态/进行态推断列入 inferred"},
            },
        ],
        operations=[
            op(name="评价", category="ui",
               expected_results=["跳转到评价页面；此页面只显示评价人员自己的评价结果；评价人员找到评价项对应单元格可以输入或调整评价分数"],
               source_ref="20.7.1.2",
               note=N(role="评价人员")),
            op(name="导出评价结果", category="file",
               expected_results=["下载评价结果"],
               source_ref="20.7.1.4",
               note=N(role="评价人员")),
            op(name="结果确认", category="ui",
               expected_results=["评价组长点击结果确认；将当前结果正式提交为项目的最终评价结果，项目评价状态关闭"],
               source_ref="20.7.1.3",
               note=N(role="评价人员")),
            op(name="保存历史", category="crud",
               expected_results=["将当前评价结果保存为历史结果"],
               source_ref="20.7.1.3",
               note=N(role="评价人员")),
            op(name="调整细则", category="ui",
               expected_results=["打开评价细节完善页面，配置完成后回到本页面将会刷新本页面数据"],
               source_ref="20.7.1.3",
               note=N(role="评价人员")),
            op(name="退回修改评价", category="ui",
               expected_results=["将当前评价结果保存为历史结果；并开启下一轮评价"],
               source_ref="20.7.1.3",
               note=N(role="评价人员")),
            op(name="调整统计规则", category="config",
               expected_results=["弹出统计规则配置弹窗；评价组长可配置统计规则"],
               source_ref="20.7.1.3",
               note=N(role="评价人员")),
        ],
    )

    # ── E-SP 流程审批 ──
    m.add_entity(
        id="E-SP", name="流程审批",
        desc="流程审批模块；本次升级将测量审核结果通知单审批流程多个流程合并为一个流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序；系统预设若干自定义流程（4个以内）用于用户选择并提交文档审核；预置电子签章位置信息",
        type="core", tags=["approvable", "collaborative"],
        attributes=[
            attr(name="任务类型", desc="审批任务类型；如结果通知单审核、报告审核、证书审核"),
            attr(name="创建时间", desc="时间选择框查询参数"),
            attr(name="审批顺序", desc="提交申请时签字人的选择顺序"),
            attr(name="签章位置", desc="预置电子签章位置信息；签章时自动代入"),
            attr(name="自定义流程", desc="系统预设若干自定义流程（4个以内）"),
            attr(name="审核结果", desc="同意 / 退回"),
            attr(name="审核意见", desc="文本输入框；选填"),
        ],
        state_dimensions=[
            {
                "dimension_name": "审批状态",
                "states": ["待审批", "已通过", "已退回"],
                "initial": "待审批",
                "terminal": ["已通过", "已退回"],
                "inferred": ["待审批", "已通过"],
                "note": {"comment": "状态枚举来源：20.9.1 流程审批；20.9.1.4 批量审核结果选项有：同意、退回；20.9.1.1 重构审批流程，按签字人顺序处理；待审批/已通过未在原文逐字命名（原文仅见'退回'），按流程首态/审核同意终态推断列入 inferred；已退回对应原文'退回'逐字命中"},
            },
        ],
        operations=[
            op(name="批量审核", category="ui",
               expected_results=["弹出批量审核表单弹窗；用户勾选任务后批量审核；系统根据任务节点类型及内容判断当前节点是否可以被批量处理"],
               source_ref="20.9.1.4",
               note=N(role=["技术主管", "授权签字人", "实验室负责人"], inferred=True,
                     comment="推断角色：审批流程签字人，依 19.1/19.2 流程分为 技术主管审核→授权签字人/实验室负责人批准")),
            op(name="查询审批流程", category="query",
               expected_results=["分页展示符合条件的数据记录；支持任务类型、创建时间查询"],
               source_ref="20.9.1.5",
               note=N(role=["技术主管", "授权签字人", "实验室负责人"], inferred=True,
                     comment="推断角色：审批流程处理人")),
            op(name="导出审批流程", category="file",
               expected_results=["导出满足当前查询条件的数据"],
               source_ref="20.9.1.5",
               note=N(role=["技术主管", "授权签字人", "实验室负责人"], inferred=True,
                     comment="推断角色：审批流程处理人")),
            op(name="自定义流程", category="config",
               expected_results=["选择预设的自定义流程并提交文档审核；支持相应的签章"],
               source_ref="20.9.1.6",
               note=N(role="项目管理员")),
        ],
    )

    # ── E-JFD 缴费信息 ──
    m.add_entity(
        id="E-JFD", name="缴费信息",
        desc="财务管理下缴费信息管理模块；用于分析整理项目费用信息；可按时间维度（月、季度、年度、自选择时间范围）、业务维度（能力验证、测量审核）、发票类型维度（电子专票、电子普票）进行筛选；支持导出；包含退款功能",
        type="managed", tags=[],
        attributes=[
            attr(name="统一社会信用代码", desc="文本"),
            attr(name="实验室名称", desc="文本"),
            attr(name="项目编号", desc="关联 E-XM"),
            attr(name="项目类型", desc="能力验证 / 测量审核；查询条件"),
            attr(name="业务类型", desc="能力验证 / 测量审核；查询条件"),
            attr(name="付款金额", desc="金额"),
            attr(name="开票类型", desc="电子专票 / 电子普票；查询条件"),
            attr(name="缴费时间", desc="时间；月度/季度/年度/自选择"),
            attr(name="到款日期", desc="日期"),
            attr(name="报名编号", desc="关联 E-BMJL；查询条件"),
            attr(name="退款金额", desc="多次退款金额做累加处理；红色字体且大于0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额=实际付款"),
            attr(name="管理备注", desc="用于记录退款原因等内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询缴费信息", category="query",
               expected_results=["分页展示符合条件的数据记录"],
               source_ref="20.10.1.1",
               note=N(role="财务管理人员")),
            op(name="导出缴费信息", category="file",
               expected_results=["导出符合筛选条件的所有数据"],
               source_ref="20.10.1.1",
               note=N(role="财务管理人员")),
        ],
    )

    # ── E-LSPJ 历史项目 ──
    m.add_entity(
        id="E-LSPJ", name="历史项目",
        desc="往年项目数据进行分析整理并导入到系统中为数据分析提供关键数据；包含往年历史用户及项目数据；列表支持通过项目名称、项目类型、子领域等查询条件进行数据筛选",
        type="managed", tags=[],
        attributes=[
            attr(name="项目编号", desc="文本"),
            attr(name="项目名称", desc="文本；模糊匹配"),
            attr(name="子领域", desc="文本；模糊匹配"),
            attr(name="项目类型", desc="能力验证 / 测量审核；精确匹配"),
            attr(name="项目管理员", desc="文本"),
            attr(name="所属年度", desc="文本；精确匹配"),
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
            op(name="查询历史项目", category="query",
               expected_results=["分页展示符合条件的数据记录"],
               source_ref="20.11.1.1",
               note=N(role=["系统管理人员", "项目管理员"], inferred=True,
                     comment="推断角色：管理人员可访问统计模块，20.4.4 同类仅系统管理员和项目管理员可查")),
        ],
    )

    # ===== Step 2：结构关系 =====
    # 四元分类判定（按序首条命中 a→b→c→d）
    # E-BZK → E-CSX：标准库提供测试项分类，测试项随标准库创建（无独立业务流程）→ (b) composition+business_ownership
    m.add_structural(
        frm="E-BZK", to="E-CSX",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="标准库下挂载测试项；测试项无独立创建流程，标准库创建时测试项随其管理",
        confidence="high",
        note={"comment": "四元分类判(b)：B无独立创建流程，A创建时B自动入initial，每条A必有B；20.4.2.7 测试项列表展示该标准库下的所有测试项"},
    )
    # E-ZLY → E-CSX：子领域引用标准库的测试项（B独立创建流程，无(c)容器证据）→ (d) reference+configuration_source
    m.add_structural(
        frm="E-ZLY", to="E-CSX",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="子领域通过选择方式从标准库引用测试项；20.4.3 调整后由表单方式变为选择方式",
        confidence="high",
        note={"comment": "四元分类判(d)：B(E-CSX)有独立创建流程且A(E-ZLY)非其业务归属容器；测试项数据来源标准库而非子领域创建"},
    )
    # E-BZK → E-ZLY：标准库作为子领域测试项的配置来源 → (a) reference+configuration_source
    m.add_structural(
        frm="E-BZK", to="E-ZLY",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="标准库为子领域测试项管理提供数据源；子领域独立创建",
        confidence="high",
        note={"comment": "四元分类判(a)：A为B提供配置/模板/分类，B独立创建"},
    )
    # E-XM → E-BMJL：项目作为业务归属容器，报名记录生命周期挂靠项目侧（报名记录归属于项目）→ (c) composition+business_ownership
    m.add_structural(
        frm="E-XM", to="E-BMJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目下挂载多条报名记录；删除项目须校验报名记录存在性；报名记录归属字段继承自项目",
        confidence="high",
        note={"comment": "四元分类判(c)：B(E-BMJL)有独立创建流程、是core流程实体，A(E-XM)为其业务归属容器（容器证据：B归属字段继承自A、删除A须校验B存在性、B生命周期挂靠A侧管理）"},
    )
    # E-SYS → E-BMJL：实验室信息作为报名记录的参加者身份来源；实验室删除/停用须校验报名记录存在性 → (c) composition+business_ownership
    m.add_structural(
        frm="E-SYS", to="E-BMJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="实验室信息作为报名记录的参加者身份载体；机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        confidence="high",
        note={"comment": "四元分类判(c)：B(E-BMJL)有独立创建流程、是core流程实体，A(E-SYS)为其业务归属容器（容器证据：B归属字段包含实验室、A审核通过后方可用于项目报名=B生命周期挂靠A侧管理）"},
    )
    # E-XM → E-PJ：项目下挂载评价；评价生命周期挂靠项目 → (c) composition+business_ownership
    m.add_structural(
        frm="E-XM", to="E-PJ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="项目下挂载评价；评价确认后项目评价状态关闭",
        confidence="high",
        note={"comment": "四元分类判(c)：B(E-PJ)有独立创建流程、是core流程实体，A(E-XM)为其业务归属容器（容器证据：B归属字段继承自A、B生命周期挂靠A侧管理）"},
    )
    # E-XM → E-SP：项目下挂载审批任务 → (c) composition+business_ownership
    m.add_structural(
        frm="E-XM", to="E-SP",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目下挂载审批任务；审批任务由项目流程触发",
        confidence="high",
        note={"comment": "四元分类判(c)：B(E-SP)有独立创建流程、是core流程实体，A(E-XM)为其业务归属容器（容器证据：B归属字段继承自A、B生命周期挂靠A侧管理）"},
    )
    # E-BMJL → E-JFD：报名记录下挂载缴费信息 → (c) composition+business_ownership
    m.add_structural(
        frm="E-BMJL", to="E-JFD",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="报名记录下挂载缴费信息；缴费信息记录与报名记录关联；退款后更新项目费用为实际付款金额",
        confidence="high",
        note={"comment": "四元分类判(c)：B(E-JFD)有独立创建流程、是managed流程实体，A(E-BMJL)为其业务归属容器（容器证据：B归属字段继承自A、删除A须校验B存在性、B生命周期挂靠A侧管理）"},
    )

    # ===== Step 3：分支维度 =====
    # 项目类型（能力验证 / 测量审核）：①配置型
    m.add_branch_dimension(
        dimension="项目类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="E-XM.项目状态 创建转换；19.1（能力验证提供者流程）vs 19.2（测量审核提供者流程）的项目状态推进路径不同——能力验证项目从待开始状态进入，测量审核项目从报名中状态进入；下游报名记录/评价/审批共用相同状态机，仅在初始态与路径长度上分立",
        evidence="三型判定：①配置型（对应 is_config 属性 项目类型）；原文 19.1/19.2 分别描述能力验证/测量审核提供者流程，项目类型在创建时定，互斥并影响后续；分立型分支——能力验证路径 frm=None→待开始（t01），测量审核路径 frm=None→报名中（t01b），frm 不同须分立",
        branches=[
            {"value": "能力验证", "target_transition": "t01",
             "desc": "能力验证项目创建：frm=None→待开始；后续经 t02 待开始→报名中"},
            {"value": "测量审核", "target_transition": "t01b",
             "desc": "测量审核项目创建：frm=None→报名中；直接进入报名阶段，跳过待开始态"},
        ],
    )
    # 评分方式（分值 / 权重）：①配置型，仅影响计算/展示
    m.add_branch_dimension(
        dimension="评分方式", entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="E-PJ 评价结果计算与展示；不影响任何转换的结构字段，转换层无 branch 转换属合法，BR 层承载即可",
        evidence="三型判定：①配置型（对应 is_config 属性 评分方式）；原文 20.7 调整评价功能支持分值和权重两种评价方式；20.7.1.1 表单字段'分值/权重'，20.7.1.3 评价结果列'权重/分值'；frm/to/role 全同仅计算展示不同→共用型不影响转换结构",
        branches=[
            {"value": "分值", "target_transition": "t90",
             "desc": "按分值方式评价；评价结果以分值形式展示"},
            {"value": "权重", "target_transition": "t90",
             "desc": "按权重方式评价；评价结果以权重形式展示"},
        ],
    )

    # ===== Step 4：转换与因果 =====

    # ── E-XM.项目状态 转换 ──
    # t01：创建项目（能力验证）frm=None→待开始
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="新增项目", role="项目管理员",
        preconditions=[],
        expected_results=["项目创建并初始化为待开始状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1项目准备阶段；19.3项目状态分析",
        note={"branch_dimension": "项目类型",
              "comment": "direction ⓪frm=None→forward；分支穿透分立型：项目类型=能力验证路径首条转换；Step 3 branches[能力验证].target_transition=t01；项目人员字段在候选人单一时默认填充，监督员字段可选填"},
    )
    # t01b：创建项目（测量审核）frm=None→报名中
    m.add_trans(
        tid="t01b", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="新增项目", role="项目管理员",
        preconditions=[],
        expected_results=["项目创建并直接进入报名中状态"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2项目准备阶段；19.3项目状态分析",
        note={"branch_dimension": "项目类型",
              "comment": "direction ⓪frm=None→forward；分支穿透分立型：项目类型=测量审核路径首条转换；Step 3 branches[测量审核].target_transition=t01b；测量审核项目受理用户报名触发，跳过待开始态"},
    )
    # t02：项目计划发布（能力验证路径）待开始→报名中
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[precond(text="项目处于待开始状态", ptype="state_ref",
                                ref=state_ref("E-XM", "项目状态", "待开始")),
                       precond(text="项目类型=能力验证", ptype="constraint",
                                note={"comment": "分支值条件"})],
        expected_results=["项目状态变为报名中；预通知状态联动初始化为未发送；报名记录可被创建"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "项目类型",
              "comment": "direction ③frm待开始先于to报名中→forward；分支穿透分立型：仅能力验证路径，因测量审核项目不经待开始态"},
    )
    # t03：进入实施 报名中→进行中
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="进入实施", role="项目管理员",
        preconditions=[precond(text="项目处于报名中状态", ptype="state_ref",
                                ref=state_ref("E-XM", "项目状态", "报名中"))],
        expected_results=["项目状态变为进行中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "direction ③frm报名中先于to进行中→forward；能力验证与测量审核共用"},
    )
    # t04：进入报告审核 进行中→报告审核中
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="进入报告审核", role="system",
        preconditions=[precond(text="项目处于进行中状态", ptype="state_ref",
                                ref=state_ref("E-XM", "项目状态", "进行中")),
                       precond(text="项目所有报名记录评价完成且结果报告编制完成", ptype="event_ref",
                                ref=None)],
        expected_results=["项目状态变为报告审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制；19.2报告编制",
        note={"comment": "direction ③frm进行中先于to报告审核中→forward；role=system：项目状态由系统依据整体流程自动推进，无显式角色动作"},
    )
    # t05：项目结束 报告审核中→已结束
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="结束项目", role="system",
        preconditions=[precond(text="项目处于报告审核中状态", ptype="state_ref",
                                ref=state_ref("E-XM", "项目状态", "报告审核中")),
                       precond(text="结果报告和证书已发放", ptype="event_ref", ref=None)],
        expected_results=["项目状态变为已结束；可执行文件整理"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制；19.2报告编制",
        note={"comment": "direction ③frm报告审核中先于to已结束→forward；终态；role=system：项目状态由系统依据整体流程自动推进"},
    )
    # t06：文件整理 已结束→已结束（自环）
    m.add_trans(
        tid="t06", entity="E-XM", dimension="项目状态",
        frm="已结束", to="已结束", action="文件整理", role="项目管理员",
        preconditions=[precond(text="项目处于已结束状态", ptype="state_ref",
                                ref=state_ref("E-XM", "项目状态", "已结束"))],
        expected_results=["系统开启整理任务并提示'归档任务已开启，请稍后查看'；整理完成后显示【查看归档】按钮；用户可查看并补充归档信息"],
        traits=["time_sensitive"], direction="forward", priority="P2",
        source_ref="20.5.1.1；20.6.1.1",
        note={"comment": "direction ⑤frm==to自环→forward+inferred，注明无状态迁移；文件整理不改项目状态，仅在已结束态执行归档任务；priority P2：辅助性/低频"},
    )

    # ── E-XM.样品状态 转换 ──
    m.add_trans(
        tid="t07", entity="E-XM", dimension="样品状态",
        frm=None, to="待核查", action="样品领用登记", role="样品管理员",
        preconditions=[],
        expected_results=["项目样品状态初始化为待核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"comment": "direction ⓪frm=None→forward；19.1流程中样品核查发生在实施阶段；19.2 显式有'样品领用登记'动作"},
    )
    m.add_trans(
        tid="t08", entity="E-XM", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查通过", role="样品管理员",
        preconditions=[precond(text="样品处于待核查状态", ptype="state_ref",
                                ref=state_ref("E-XM", "样品状态", "待核查"))],
        expected_results=["样品状态变为已核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "direction ③frm待核查先于to已核查→forward"},
    )

    # ── E-BMJL.通知状态 转换 ──
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="通知状态",
        frm=None, to="未发送", action="创建通知记录", role="system",
        preconditions=[],
        expected_results=["新报名记录的通知状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "direction ⓪frm=None→forward；通知状态为报名记录创建时的隐式初态"},
    )
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="通知状态",
        frm="未发送", to="待确认", action="发送预通知", role="项目管理员",
        preconditions=[precond(text="通知处于未发送状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "通知状态", "未发送"))],
        expected_results=["通知状态变为待确认"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "direction ③frm未发送先于to待确认→forward"},
    )
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="通知状态",
        frm="待确认", to="待审核", action="提交审核", role="样品管理员",
        preconditions=[precond(text="通知处于待确认状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "通知状态", "待确认"))],
        expected_results=["通知状态变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.2实施阶段",
        note={"comment": "direction ③frm待确认先于to待审核→forward；19.2 流程表'作业指导书编制'后通知状态为待审核，角色依流程归样品管理员"},
    )
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="通知状态",
        frm="待审核", to="已审核", action="审核通过", role="技术主管",
        preconditions=[precond(text="通知处于待审核状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "通知状态", "待审核"))],
        expected_results=["通知状态变为已审核"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="19.2实施阶段",
        note={"comment": "direction ③frm待审核先于to已审核→forward；19.2 流程表'作业指导书编制'行有 退回/已审核 取值；此处取推进态"},
    )
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="通知状态",
        frm="待审核", to="退回", action="审核退回", role="技术主管",
        preconditions=[precond(text="通知处于待审核状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "通知状态", "待审核"))],
        expected_results=["通知状态变为退回"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.2实施阶段",
        note={"comment": "direction ④frm待审核后于to退回（按 states 顺序 退回 index=3 > 待审核 index=2）→backward；19.2 流程表'退回'取值"},
    )
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="通知状态",
        frm="退回", to="待审核", action="重新提交", role="样品管理员",
        preconditions=[precond(text="通知处于退回状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "通知状态", "退回"))],
        expected_results=["通知状态重新变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.2实施阶段",
        note={"comment": "direction 序判④frm退回后于to待审核（按 states 顺序 退回 index=3 > 待审核 index=2），语义forward（重新提交，恢复到审核前推进态）；序判与语义冲突→语义优先，comment 注明"},
    )
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="通知状态",
        frm="已审核", to="已批准", action="批准通知", role="授权签字人",
        preconditions=[precond(text="通知处于已审核状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "通知状态", "已审核"))],
        expected_results=["通知状态变为已批准"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制；19.2报告编制",
        note={"comment": "direction ③frm已审核先于to已批准→forward；授权签字人批准结果通知单"},
    )

    # ── E-BMJL.报名记录状态 转换 ──
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["参加者提交报名信息；报名记录状态初始化为报名待审核；费用状态联动初始化为待缴费；发票状态联动初始化为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "direction ⓪frm=None→forward；参加者提交报名触发的创建转换"},
    )
    m.add_trans(
        tid="t21", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="审核通过", role="项目管理员",
        preconditions=[precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "报名待审核"))],
        expected_results=["报名记录状态变为报名成功；并发送短信'您xxx项目的报名信息审核通过，请知悉'"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.5.3.2；20.6.3.2",
        note={"comment": "direction ③frm报名待审核先于to报名成功→forward；并发送短信通知参加者"},
    )
    m.add_trans(
        tid="t22", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="审核退回", role="项目管理员",
        preconditions=[precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "报名待审核"))],
        expected_results=["报名记录状态变为报名退回；并发送短信'您xxx项目的报名信息审核未通过，请知悉'"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.1实施阶段；20.5.3.2；20.6.3.2",
        note={"comment": "direction ④frm报名待审核后于to报名退回（按 states 顺序 报名退回 index=1 < 报名待审核 index=0 不成立——退回在后）→backward；19.1/19.2 流程表'报名退回'取值"},
    )
    m.add_trans(
        tid="t23", entity="E-BMJL", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="重新提交报名", role="能力验证参加者",
        preconditions=[precond(text="报名记录处于报名退回状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "报名退回"))],
        expected_results=["报名记录状态重新变为报名待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "direction 序判④frm报名退回后于to报名待审核（按 states 顺序 报名退回 index=1 > 报名待审核 index=0），语义forward（重新提交）；序判与语义冲突→语义优先，comment 注明"},
    )
    m.add_trans(
        tid="t24", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="进入结果阶段", role="system",
        preconditions=[precond(text="报名记录处于报名成功状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
                       precond(text="样品已发放且作业指导书已发送", ptype="event_ref", ref=None)],
        expected_results=["报名记录状态变为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "direction ③frm报名成功先于to结果待提交→forward；role=system：报名记录状态由系统依据样品发放等业务事件自动推进"},
    )
    m.add_trans(
        tid="t25", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="提交结果", role="能力验证参加者",
        preconditions=[precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "结果待提交"))],
        expected_results=["报名记录状态变为结果已提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.4",
        note={"comment": "direction ③frm结果待提交先于to结果已提交→forward；参加者提交测试结果触发的转换"},
    )
    m.add_trans(
        tid="t26", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果退回", role="技术主管",
        preconditions=[precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "结果已提交"))],
        expected_results=["报名记录状态变为结果退回修改；并发送短信'您xxxx项目测试报告审核未通过，请知悉'"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.1报告编制；20.5.3.2；20.6.3.2",
        note={"comment": "direction ④frm结果已提交后于to结果退回修改（按 states 顺序 结果退回修改 index=5 > 结果已提交 index=4）→backward"},
    )
    m.add_trans(
        tid="t27", entity="E-BMJL", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交", action="重新提交结果", role="能力验证参加者",
        preconditions=[precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "结果退回修改"))],
        expected_results=["报名记录状态重新变为结果已提交"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1报告编制；19.2报告编制",
        note={"comment": "direction 序判④frm结果退回修改后于to结果已提交（按 states 顺序 结果退回修改 index=5 > 结果已提交 index=4），语义forward（重新提交）；序判与语义冲突→语义优先，comment 注明"},
    )
    m.add_trans(
        tid="t28", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
                       precond(text="评价已完成并统计", ptype="event_ref", ref=None)],
        expected_results=["报名记录状态变为报告/证书审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制；19.2报告编制",
        note={"comment": "direction ③frm结果已提交先于to报告/证书审核中→forward；策划人员编制结果报告触发的转换"},
    )
    m.add_trans(
        tid="t29", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
                       precond(text="技术主管审核通过、授权签字人/实验室负责人批准", ptype="event_ref", ref=None)],
        expected_results=["报名记录状态变为报告/证书已发布；并发送短信'您xxx项目的结果通知单已发布，请知悉'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制；19.2报告编制；20.5.3.2；20.6.3.2",
        note={"comment": "direction ③frm报告/证书审核中先于to报告/证书已发布→forward；终态；项目管理员发放触发的转换"},
    )
    m.add_trans(
        tid="t30", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="已撤销", action="撤销报名", role="能力验证参加者",
        preconditions=[precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录状态", "报名待审核"))],
        expected_results=["报名记录状态变为已撤销"],
        traits=["rollback"], direction="lateral", priority="P1",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "direction ①语义类：原文 19.1/19.2 流程表'报名待审核/已撤销'取值，'已撤销'为侧挂终态，参加者主动撤销；lateral 挂起至主线外终态；frm 可为多状态，此处取报名待审核作为最常见前置态"},
    )

    # ── E-BMJL.报名记录样品状态 转换 ──
    m.add_trans(
        tid="t40", entity="E-BMJL", dimension="报名记录样品状态",
        frm=None, to="待发样", action="初始化样品状态", role="system",
        preconditions=[],
        expected_results=["报名记录样品状态初始化为待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "direction ⓪frm=None→forward；报名记录创建时样品状态隐式初始化"},
    )
    m.add_trans(
        tid="t41", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待发样", to="待收样", action="发样", role="样品管理员",
        preconditions=[precond(text="样品处于待发样状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录样品状态", "待发样"))],
        expected_results=["样品状态变为待收样；并发送短信'您xxxx项目的样品已发出，请知悉'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.5.3.2；20.6.3.2",
        note={"comment": "direction ③frm待发样先于to待收样→forward；并发送短信通知参加者"},
    )
    m.add_trans(
        tid="t42", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待收样", to="已收样", action="收样", role="能力验证参加者",
        preconditions=[precond(text="样品处于待收样状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录样品状态", "待收样"))],
        expected_results=["样品状态变为已收样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"comment": "direction ③frm待收样先于to已收样→forward"},
    )
    m.add_trans(
        tid="t43", entity="E-BMJL", dimension="报名记录样品状态",
        frm="已收样", to="已确认", action="确认样品", role="能力验证参加者",
        preconditions=[precond(text="样品处于已收样状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "报名记录样品状态", "已收样"))],
        expected_results=["样品状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析；19.1实施阶段",
        note={"comment": "direction ③frm已收样先于to已确认→forward；终态；19.1 流程表'已确认'取值"},
    )

    # ── E-BMJL.费用状态 转换 ──
    m.add_trans(
        tid="t50", entity="E-BMJL", dimension="费用状态",
        frm=None, to="待缴费", action="初始化费用状态", role="system",
        preconditions=[],
        expected_results=["费用状态初始化为待缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "direction ⓪frm=None→forward；报名记录创建时费用状态隐式初始化"},
    )
    m.add_trans(
        tid="t51", entity="E-BMJL", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[precond(text="费用处于待缴费状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "费用状态", "待缴费"))],
        expected_results=["费用状态变为已缴费；支持多次付款不对付款金额进行校验限制"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.5.2.1；20.6.2.1",
        note={"comment": "direction ③frm待缴费先于to已缴费→forward；20.5.2.1/20.6.2.1 多次付款功能不校验金额"},
    )

    # ── E-BMJL.发票状态 转换 ──
    m.add_trans(
        tid="t60", entity="E-BMJL", dimension="发票状态",
        frm=None, to="待开票", action="初始化发票状态", role="system",
        preconditions=[],
        expected_results=["发票状态初始化为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "direction ⓪frm=None→forward；报名记录创建时发票状态隐式初始化"},
    )
    m.add_trans(
        tid="t61", entity="E-BMJL", dimension="发票状态",
        frm="待开票", to="已开票", action="开票", role="财务管理人员",
        preconditions=[precond(text="发票处于待开票状态", ptype="state_ref",
                                ref=state_ref("E-BMJL", "发票状态", "待开票"))],
        expected_results=["发票状态变为已开票；支持多次分批上传发票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.10.2.2",
        note={"comment": "direction ③frm待开票先于to已开票→forward；20.10.2.2 修改发票上传功能支持多次分批上传"},
    )

    # ── E-SYS.实验室状态 转换 ──
    m.add_trans(
        tid="t70", entity="E-SYS", dimension="实验室状态",
        frm=None, to="待审核", action="新增实验室", role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室信息创建并初始化为待审核状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1；20.4.1.1",
        note={"comment": "direction ⓪frm=None→forward；机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名；20.4.1.1 列表'修改/删除'操作"},
    )
    m.add_trans(
        tid="t71", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="启用", action="审核通过", role="系统管理人员",
        preconditions=[precond(text="实验室处于待审核状态", ptype="state_ref",
                                ref=state_ref("E-SYS", "实验室状态", "待审核"))],
        expected_results=["实验室状态变为启用；为当前数据生成该数据的快照记录"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2",
        note={"comment": "direction ③frm待审核先于to启用→forward；20.4.1.2 审核结果=通过时实验室状态变更为启用；为当前数据生成快照记录"},
    )
    m.add_trans(
        tid="t72", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="退回修改", action="审核退回", role="系统管理人员",
        preconditions=[precond(text="实验室处于待审核状态", ptype="state_ref",
                                ref=state_ref("E-SYS", "实验室状态", "待审核")),
                       precond(text="必须填写审核意见", ptype="constraint", ref=None)],
        expected_results=["实验室状态变为退回修改（20.4.1.2 称'已退回'）；必须填写审核意见"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.4.1.2",
        note={"comment": "direction ④frm待审核后于to退回修改（按 states 顺序 退回修改 index=3 > 待审核 index=0）→backward；ambiguity: 20.3.1 列举状态名为'退回修改'，20.4.1.2 审核退回后写入状态名为'已退回'，本维度统一取'退回修改'"},
    )
    m.add_trans(
        tid="t73", entity="E-SYS", dimension="实验室状态",
        frm="退回修改", to="待审核", action="重新提交", role="能力验证参加者",
        preconditions=[precond(text="实验室处于退回修改状态", ptype="state_ref",
                                ref=state_ref("E-SYS", "实验室状态", "退回修改"))],
        expected_results=["实验室状态重新变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.3.1；20.4.1",
        note={"comment": "direction 序判④frm退回修改后于to待审核（按 states 顺序 退回修改 index=3 > 待审核 index=0），语义forward（重新提交）；序判与语义冲突→语义优先，comment 注明"},
    )
    m.add_trans(
        tid="t74", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="停用", action="停用", role="系统管理人员",
        preconditions=[precond(text="实验室处于启用状态", ptype="state_ref",
                                ref=state_ref("E-SYS", "实验室状态", "启用"))],
        expected_results=["实验室状态立即变为停用，列表刷新"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction ④frm启用后于to停用（按 states 顺序 停用 index=2 > 启用 index=1）→backward；20.4.1.1 操作列'停用'按钮"},
    )
    m.add_trans(
        tid="t75", entity="E-SYS", dimension="实验室状态",
        frm="停用", to="启用", action="启用", role="系统管理人员",
        preconditions=[precond(text="实验室处于停用状态", ptype="state_ref",
                                ref=state_ref("E-SYS", "实验室状态", "停用"))],
        expected_results=["实验室状态立即变为启用，列表刷新"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction ③frm停用先于to启用（按 states 顺序 停用 index=2 > 启用 index=1 不成立——启用在前）→forward；20.4.1.1 操作列'启用'按钮"},
    )

    # ── E-BZK.标准库状态 转换 ──
    m.add_trans(
        tid="t80", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理人员",
        preconditions=[],
        expected_results=["标准库创建并初始化为启用状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2",
        note={"comment": "direction ⓪frm=None→forward；20.4.2.2 新增表单状态单选框包含启用、停用；默认取启用为初态"},
    )
    m.add_trans(
        tid="t81", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="停用", role="系统管理人员",
        preconditions=[precond(text="标准库处于启用状态", ptype="state_ref",
                                ref=state_ref("E-BZK", "标准库状态", "启用"))],
        expected_results=["标准库状态立即变为停用；停用的标准库在项目创建等环节不可被选择"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction ④frm启用后于to停用（按 states 顺序 启用 index=0 < 停用 index=1）→backward；停用后标准库在项目创建等环节不可被选择"},
    )
    m.add_trans(
        tid="t82", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="启用", role="系统管理人员",
        preconditions=[precond(text="标准库处于停用状态", ptype="state_ref",
                                ref=state_ref("E-BZK", "标准库状态", "停用"))],
        expected_results=["标准库状态立即变为启用，列表刷新"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction ③frm停用先于to启用（按 states 顺序 停用 index=1 > 启用 index=0 不成立——启用在前）→forward；20.4.2.5 启用按钮"},
    )

    # ── E-PJ.评价状态 转换 ──
    m.add_trans(
        tid="t90", entity="E-PJ", dimension="评价状态",
        frm=None, to="待评价", action="初始化评价", role="system",
        preconditions=[],
        expected_results=["评价状态初始化为待评价；第一个被选择的评价人员默认作为评价组长"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2；20.7.1.3",
        note={"comment": "direction ⓪frm=None→forward；待评价为隐式初态（推断），第一个被选择的评价人员默认作为评价组长"},
    )
    m.add_trans(
        tid="t91", entity="E-PJ", dimension="评价状态",
        frm="待评价", to="评价中", action="启动评价", role="评价人员",
        preconditions=[precond(text="评价处于待评价状态", ptype="state_ref",
                                ref=state_ref("E-PJ", "评价状态", "待评价")),
                       precond(text="评价组长已完善测试项目及评价细则", ptype="event_ref", ref=None)],
        expected_results=["评价状态变为评价中；评价人员可对自己的评价结果进行修改"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.1；20.7.1.2",
        note={"comment": "direction ③frm待评价先于to评价中→forward；20.7.1.1 评价组长完善测试项目及评价细则；20.7.1.2 评价人员对报名项目进行评价"},
    )
    m.add_trans(
        tid="t92", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="退回修改", action="退回修改评价", role="评价人员",
        preconditions=[precond(text="评价处于评价中状态", ptype="state_ref",
                                ref=state_ref("E-PJ", "评价状态", "评价中"))],
        expected_results=["将当前评价结果保存为历史结果；并开启下一轮评价"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="20.7.1.3",
        note={"comment": "direction ④frm评价中后于to退回修改（按 states 顺序 退回修改 index=2 > 评价中 index=1）→backward；20.7.1.3 退回修改按钮；保存历史并开启下一轮评价"},
    )
    m.add_trans(
        tid="t93", entity="E-PJ", dimension="评价状态",
        frm="退回修改", to="评价中", action="重新评价", role="评价人员",
        preconditions=[precond(text="评价处于退回修改状态", ptype="state_ref",
                                ref=state_ref("E-PJ", "评价状态", "退回修改"))],
        expected_results=["评价状态重新变为评价中，开启下一轮评价"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.7.1.3",
        note={"comment": "direction 序判④frm退回修改后于to评价中（按 states 顺序 退回修改 index=2 > 评价中 index=1），语义forward（开启下一轮评价）；序判与语义冲突→语义优先，comment 注明"},
    )
    m.add_trans(
        tid="t94", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="已确认", action="结果确认", role="评价人员",
        preconditions=[precond(text="评价处于评价中状态", ptype="state_ref",
                                ref=state_ref("E-PJ", "评价状态", "评价中")),
                       precond(text="评价组长填写及格分及得分", ptype="constraint", ref=None,
                                note={"comment": "评价组长需填写各客户得分"})],
        expected_results=["将当前结果正式提交为项目的最终评价结果；项目评价状态关闭"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3",
        note={"comment": "direction ③frm评价中先于to已确认→forward；终态；20.7.1.3 确认按钮：将当前结果正式提交为项目的最终评价结果，项目评价状态关闭"},
    )

    # ── E-SP.审批状态 转换 ──
    m.add_trans(
        tid="t100", entity="E-SP", dimension="审批状态",
        frm=None, to="待审批", action="提交审批", role="项目管理员",
        preconditions=[],
        expected_results=["生成一个新的审核任务；任务状态初始化为待审批；并发送短信通知相关负责人'您有一个新的xxx审核任务，请及时处理'"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.9.1.1；20.9.1.3",
        note={"comment": "direction ⓪frm=None→forward；20.9.1.1 重构测量审核结果通知单审批流程；20.9.1.3 用户通过表单或审核一个已存在的任务，生成一个新的审核任务；系统发送短信通知相关负责人"},
    )
    m.add_trans(
        tid="t101", entity="E-SP", dimension="审批状态",
        frm="待审批", to="已通过", action="审批通过", role="技术主管",
        preconditions=[precond(text="审批处于待审批状态", ptype="state_ref",
                                ref=state_ref("E-SP", "审批状态", "待审批"))],
        expected_results=["审批状态变为已通过"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.9.1.4",
        note={"comment": "direction ③frm待审批先于to已通过→forward；20.9.1.4 审核结果选项：同意、退回；签字人顺序按提交申请时选择顺序"},
    )
    m.add_trans(
        tid="t102", entity="E-SP", dimension="审批状态",
        frm="待审批", to="已退回", action="审批退回", role="技术主管",
        preconditions=[precond(text="审批处于待审批状态", ptype="state_ref",
                                ref=state_ref("E-SP", "审批状态", "待审批"))],
        expected_results=["审批状态变为已退回"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.9.1.4",
        note={"comment": "direction ④frm待审批后于to已退回（按 states 顺序 已退回 index=2 > 待审批 index=0）→backward；20.9.1.4 审核结果选项：同意、退回"},
    )

    # ===== Step 4.4：因果 =====
    # C01: 报名审核通过/退回 → 短信通知发送
    m.add_causal(
        frm="E-BMJL", to="E-XX",
        desc="管理人员对用户报名项目操作后使用短信方式对用户进行通知；报名审核通过/退回、发样通知、测试结果审核通过/退回、结果通知单发布均触发短信通知",
        trigger="管理人员对用户报名项目操作后使用短信方式对用户进行通知",
        trigger_source="desc",
        evidence_transitions=["t21", "t22", "t41", "t26", "t27", "t29"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "trigger_source=desc：显式句式'管理人员对用户报名项目操作后使用短信方式对用户进行通知'；evidence_transitions 含 t21/t22（报名审核通过/退回）/t41（发样）/t26/t27（测试结果审核通过/退回）/t29（结果通知单发布）；4.5 鉴别：Q1 X(报名操作)直接致Y(短信通知记录创建)，Y不需额外操作；Q2 Y侧无 precondition/XC 表达；Q3 非上下级门禁→因果"},
    )
    # C02: 任务创建 → 短信通知
    m.add_causal(
        frm="E-SP", to="E-XX",
        desc="用户通过表单或审核一个已存在的任务，生成一个新的审核任务后，系统发送短信通知相关负责人",
        trigger="用户通过表单或审核一个已存在的任务，生成一个新的审核任务",
        trigger_source="desc",
        evidence_transitions=["t100"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "trigger_source=desc：20.9.1.3 显式句式'生成一个新的审核任务...系统发送短信通知相关负责人'；4.5 鉴别：Q1 X(任务创建)直接致Y(短信通知)，Y不需额外操作；Q2/Q3 非门禁/非上下级→因果"},
    )
    # C03: 缴费退款 → 项目费用更新
    m.add_causal(
        frm="E-JFD", to="E-BMJL",
        desc="退款后更新'项目费用'为实际付款金额；实际付款=付款金额-退款金额",
        trigger="退款后更新'项目费用'为实际付款金额",
        trigger_source="desc",
        evidence_transitions=None,
        rollback_propagation=False,
        confidence="high",
        note={"comment": "trigger_source=desc：20.10.2.3 显式句式'退款后更新项目费用为实际付款金额'；evidence_transitions 可空（desc 来源允许）；4.5 鉴别：Q1 X(退款操作)直接致Y(项目费用/实际付款字段更新)，Y不需额外操作；Q2/Q3 非门禁→因果"},
    )
    # C04: 证书距到期30天 → 邮件通知
    m.add_causal(
        frm="E-BMJL", to="E-XX",
        desc="系统在每天上午9点对系统中的证书信息进行查询；如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送给项目管理员",
        trigger="如证书距到期时间等于30天则通过邮件方式对用户进行提醒",
        trigger_source="desc",
        evidence_transitions=None,
        rollback_propagation=False,
        confidence="high",
        note={"comment": "trigger_source=desc：20.5.2.3/20.6.2.3 显式句式；时间触发型因果；frm=E-BMJL（证书信息字段载体）；4.5 鉴别：Q1 X(证书到期条件满足)直接致Y(邮件通知记录创建)；Q2/Q3 非门禁→因果"},
    )

    # ===== Step 4.3 自检 =====
    # ① Step 3 的 target_transition 局部 tid 均有对应 add_trans：t01/t01b（项目类型）、t90（评分方式）✓
    # ② 回写遗漏动词/权限：Step 0 已包含文档主要动词；新发现的'签章'动词已在 action_verbs 中

    # Step 4 中发现新动词'签章'与操作归属：在当前位置追加（回写协议）
    m.add_action_verbs(verbs=["签章"])
    m.add_permission(role="技术主管", operations=["签章"])
    m.add_permission(role="授权签字人", operations=["签章"])
    m.add_permission(role="实验室负责人", operations=["签章"])

    # ===== Step 5：约束补充 =====

    # ── invalid_transitions：原文无'不允许从X到Y'的明确禁止措辞，不生成 IT ──

    # ── XC：跨实体约束 ──
    # x01: 项目进入报名中 联动 报名记录创建（能力验证路径）
    m.add_xc(
        xid="x01",
        source_entity="E-XM", source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名待审核",
        target_transition="t20",
        xc_source="联动",
        desc="能力验证项目计划发布进入报名中后，开启报名通道，新报名记录初始化为报名待审核",
        source_ref="19.1实施阶段；19.3项目状态分析",
    )
    # x02: 测量审核项目创建 联动 报名记录创建
    m.add_xc(
        xid="x02",
        source_entity="E-XM", source_transition="t01b", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名待审核",
        target_transition="t20",
        xc_source="联动",
        desc="测量审核项目创建后即进入报名中，受理用户测量审核报名，新报名记录初始化为报名待审核",
        source_ref="19.2项目准备阶段",
    )
    # x03: 报名审核通过 联动 缴费通知单状态变化
    m.add_xc(
        xid="x03",
        source_entity="E-BMJL", source_transition="t21", source_state="报名成功",
        target_entity="E-BMJL", target_dimension="通知状态",
        target_condition="待审核",
        target_transition="t12",
        xc_source="联动",
        desc="报名审核通过后联动缴费通知单状态变化，缴费通知单由未发送推进至待审核",
        source_ref="19.1实施阶段；19.2项目准备阶段",
    )
    # x04: 项目类型分支差异（能力验证/测量审核）的项目状态推进路径分立
    m.add_xc(
        xid="x04",
        source_entity="E-XM", source_transition="t01", source_state="待开始",
        target_entity="E-XM", target_dimension="项目状态",
        target_condition="待开始",
        target_transition=None,
        xc_source="分支差异",
        desc="项目类型=能力验证路径须经待开始→报名中两步（t01→t02）；项目类型=测量审核路径直接经报名中创建（t01b）跳过待开始态；两条路径在报名中后合并至 t03-t05 共用推进",
        source_ref="19.1能力验证提供者流程；19.2测量审核提供者流程",
    )
    # x05: 报名记录创建 联动 费用状态/发票状态初始化
    m.add_xc(
        xid="x05",
        source_entity="E-BMJL", source_transition="t20", source_state="报名待审核",
        target_entity="E-BMJL", target_dimension="费用状态",
        target_condition="待缴费",
        target_transition="t50",
        xc_source="联动",
        desc="报名记录创建后联动初始化费用状态为待缴费、发票状态为待开票",
        source_ref="19.1实施阶段；19.3项目状态分析",
    )
    # x06: 报名记录创建 联动 通知状态初始化
    m.add_xc(
        xid="x06",
        source_entity="E-BMJL", source_transition="t20", source_state="报名待审核",
        target_entity="E-BMJL", target_dimension="通知状态",
        target_condition="未发送",
        target_transition="t10",
        xc_source="联动",
        desc="报名记录创建后联动初始化通知状态为未发送",
        source_ref="19.1实施阶段；19.3项目状态分析",
    )

    # ── BR：业务规则 ──
    # b01: 首页通知new标识15天
    m.add_br(
        bid="b01", category="display",
        desc="对新旧通知内容进行区分显示；15天内发布的通知在内容前标注'new'标识；超过15天后此标识自动隐藏",
        entities_involved=["E-XX"],
        source_ref="20.2.1",
        signal_type="display",
        note={"comment": "signal_type 命中'标注'new'标识/自动隐藏'属显示展示→display（15天仅触发条件，非 signal 取值）；category 判信息展示规则→display；signal_type 命中词与 category 不互斥，两步独立判定"},
    )
    # b02: 首页待办统计
    m.add_br(
        bid="b02", category="display",
        desc="完善用户侧首页能力验证和测试审核统计部分内容；能力验证增加'待提交结果'统计内容；测量审核增加'待审核'统计内容",
        entities_involved=["E-XM", "E-BMJL"],
        source_ref="20.2.3",
        signal_type="display",
        constrained_entity="E-BMJL",
        note={"comment": "signal_type 命中'统计部分内容'属信息展示→display；category 判信息展示规则→display；constrained_entity 判④对称规则：统计内容源于报名记录（E-BMJL）的提交/审核状态，取 E-BMJL 为代表实体（E-XM 为统计对象之一，非门禁主体）"},
    )
    # b03: 实验室信息审核通过后方可用于项目报名
    m.add_br(
        bid="b03", category="authorization",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-SYS", "E-BMJL"],
        source_ref="20.3.1",
        signal_type="restrictive",
        constrained_entity="E-SYS",
        note={"comment": "signal_type 命中'需经...方可'属限制→restrictive；category 判访问控制与操作权限→authorization；constrained_entity 判①：操作的对象实体为 E-SYS（实验室信息的增改门禁）"},
    )
    # b04: 实验室审核通过生成快照记录
    m.add_br(
        bid="b04", category="usability",
        desc="审核结果为通过时，为当前数据生成该数据的快照记录",
        entities_involved=["E-SYS"],
        source_ref="20.4.1.2",
        signal_type="usability",
        note={"comment": "signal_type 命中'生成...快照'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b05: 实验室审核退回必须填写审核意见
    m.add_br(
        bid="b05", category="validation",
        desc="审核结果为退回修改时，必须填写'审核意见'",
        entities_involved=["E-SYS"],
        source_ref="20.4.1.2",
        signal_type="restrictive",
        constrained_entity="E-SYS",
        note={"comment": "signal_type 命中'必须'属限制→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-SYS"},
    )
    # b06: 停用的标准库不可被选择
    m.add_br(
        bid="b06", category="authorization",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"],
        source_ref="20.4.2.5",
        signal_type="restrictive",
        constrained_entity="E-BZK",
        note={"comment": "signal_type 命中'不可'属限制→restrictive；category 判访问控制与操作权限→authorization；constrained_entity 判①：门禁对象为 E-BZK（标准库停用后不可被选择）"},
    )
    # b07: 含有子项的记录不允许删除（测试项）
    m.add_br(
        bid="b07", category="validation",
        desc="含有子项的测试项记录不允许删除",
        entities_involved=["E-CSX"],
        source_ref="20.4.2.10",
        signal_type="restrictive",
        constrained_entity="E-CSX",
        note={"comment": "signal_type 命中'不允许'属限制→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：删除门禁对象为 E-CSX"},
    )
    # b08: 含有子项的子领域测试项不可以删除
    m.add_br(
        bid="b08", category="validation",
        desc="数据删除前会做前置判断，存在子项的子领域测试项数据不可以删除",
        entities_involved=["E-ZLY", "E-CSX"],
        source_ref="20.4.3.4",
        signal_type="restrictive",
        constrained_entity="E-CSX",
        note={"comment": "signal_type 命中'不可以'属限制→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：删除门禁对象为 E-CSX（子领域引用的测试项）"},
    )
    # b09: 信息发送记录仅系统管理员和项目管理员可查
    m.add_br(
        bid="b09", category="authorization",
        desc="信息发送记录只有系统管理员和项目管理员可以查看",
        entities_involved=["E-XX"],
        source_ref="20.4.4.1",
        signal_type="restrictive",
        constrained_entity="E-XX",
        note={"comment": "signal_type 命中'只有...可以'属限制→restrictive；category 判访问控制→authorization；constrained_entity 判①：门禁对象为 E-XX"},
    )
    # b10: 项目人员字段候选人单一时默认填充
    m.add_br(
        bid="b10", category="usability",
        desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"],
        source_ref="20.5.1.6；20.6.1.4",
        signal_type="usability",
        note={"comment": "signal_type 命中'默认填充'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b11: 监督员字段可选填
    m.add_br(
        bid="b11", category="usability",
        desc="项目新增表单在项目人员信息区域最后一行增加监督员字段（下拉框可以为空）；导出项目通知书时填充到对应位置",
        entities_involved=["E-XM"],
        source_ref="20.5.1.5；20.6.1.3",
        signal_type="usability",
        note={"comment": "signal_type 命中'可以为空'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b12: 批量处理选择列规则
    m.add_br(
        bid="b12", category="validation",
        desc="选择列用于选定当前数据，只有已上传对应文件且未提交审核的记录才可以被选定",
        entities_involved=["E-BMJL"],
        source_ref="20.5.1.3",
        signal_type="restrictive",
        constrained_entity="E-BMJL",
        note={"comment": "signal_type 命中'只有...才可以'属限制→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-BMJL"},
    )
    # b13: 消息发送接收人1和接收人2不能同时为空
    m.add_br(
        bid="b13", category="validation",
        desc="消息发送左侧消息发送区，接收人1和接收人2不能同时为空",
        entities_involved=["E-XX"],
        source_ref="20.5.1.4；20.6.1.2",
        signal_type="restrictive",
        constrained_entity="E-XX",
        note={"comment": "signal_type 命中 prohibit_keywords '不能同时为空'→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-XX"},
    )
    # b14: 未结束的项目可以进行消息发送
    m.add_br(
        bid="b14", category="authorization",
        desc="在详情页提供'消息发送'按钮，未结束的项目可以进行消息发送",
        entities_involved=["E-XM", "E-XX"],
        source_ref="20.5.1.4；20.6.1.2",
        signal_type="restrictive",
        constrained_entity="E-XM",
        note={"comment": "signal_type 命中'未结束...可以'属限制→restrictive；category 判访问控制→authorization；constrained_entity 判①：门禁对象为 E-XM（项目状态门禁）"},
    )
    # b15: 多次付款不对付款金额进行校验限制
    m.add_br(
        bid="b15", category="validation",
        desc="修改已报名项目的付款验证，可以多次进行付款操作；不对付款金额进行校验限制",
        entities_involved=["E-BMJL"],
        source_ref="20.5.2.1；20.6.2.1",
        signal_type="restrictive",
        constrained_entity="E-BMJL",
        note={"comment": "signal_type 命中'不对...校验限制'属限制→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-BMJL"},
    )
    # b16: 证书距到期时间等于30天邮件提醒
    m.add_br(
        bid="b16", category="notification",
        desc="系统在每天上午9点对系统中的证书信息进行查询；如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送给项目管理员",
        entities_involved=["E-BMJL", "E-XX"],
        source_ref="20.5.2.3；20.6.2.3",
        signal_type="usability",
        constrained_entity="E-BMJL",
        note={"comment": "signal_type 无 restrictive/display/field_constraint 强信号→usability 兜底（时间/次数约束归 category，非 signal_type）；category 判通知与消息触发→notification；constrained_entity 判①：操作对象实体为 E-BMJL（证书信息载体）"},
    )
    # b17: 评价人员只能修改自己的评价结果
    m.add_br(
        bid="b17", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"],
        source_ref="20.7.1.2",
        signal_type="restrictive",
        constrained_entity="E-PJ",
        note={"comment": "signal_type 命中 prohibit_keywords '不能查看和修改其他评价人员'→restrictive；category 判访问控制→authorization；constrained_entity 判①：门禁对象为 E-PJ"},
    )
    # b18: 第一个被选择的评价人员默认作为评价组长
    m.add_br(
        bid="b18", category="usability",
        desc="新建项目时第一个被选择的评价人员默认做为评价组长，评价组长可以在评价结果确认页面查看各评价人员的评价结果，并对最终结果进行确认",
        entities_involved=["E-PJ"],
        source_ref="20.7",
        signal_type="usability",
        note={"comment": "signal_type 命中'默认做为'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b19: 评价结果确认后项目评价状态关闭
    m.add_br(
        bid="b19", category="validation",
        desc="评价组长点击'确认'按钮后，将当前结果正式提交为项目的最终评价结果，项目评价状态关闭",
        entities_involved=["E-PJ"],
        source_ref="20.7.1.3",
        signal_type="restrictive",
        constrained_entity="E-PJ",
        note={"comment": "signal_type 命中'正式提交...关闭'属限制→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-PJ"},
    )
    # b20: 评价退回修改保存历史并开启下一轮
    m.add_br(
        bid="b20", category="usability",
        desc="评价组长点击'退回修改'按钮后，将当前评价结果保存为历史结果；并开启下一轮评价",
        entities_involved=["E-PJ"],
        source_ref="20.7.1.3",
        signal_type="usability",
        note={"comment": "signal_type 命中'保存为历史结果...开启下一轮'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b21: 统计规则配置
    m.add_br(
        bid="b21", category="computation",
        desc="每个统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值",
        entities_involved=["E-PJ"],
        source_ref="20.7.1.3",
        signal_type="field_constraint",
        note={"comment": "signal_type 命中'取值范围'属字段约束→field_constraint；category 判数值计算与衍生值规则→computation"},
    )
    # b22: 评分方式支持分值和权重两种评价方式
    m.add_br(
        bid="b22", category="computation",
        desc="调整评价功能，支持分值和权重两种评价方式",
        entities_involved=["E-PJ"],
        source_ref="20.7",
        signal_type="field_constraint",
        note={"branch_dimension": "评分方式",
              "comment": "desc 含分支值字面量'分值/权重'；signal_type 命中'取值范围'属字段约束→field_constraint；category 判数值计算与衍生值规则→computation（评分方式影响计算）"},
    )
    # b23: 客户统计时间快速录入
    m.add_br(
        bid="b23", category="usability",
        desc="优化客户统计列表录入时间的快速录入，增加年度、季度、月度时间的快速录入",
        entities_involved=["E-LSPJ"],
        source_ref="20.8.6.1",
        signal_type="usability",
        note={"comment": "signal_type 命中'增加...快速录入'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b24: 测量审核结果通知单审批流程合并
    m.add_br(
        bid="b24", category="usability",
        desc="重构测量审核结果通知单审批流程，将原来多个流程合并为一个流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-SP"],
        source_ref="20.9.1.1",
        signal_type="usability",
        note={"comment": "signal_type 命中'重构...合并'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b25: 预置签章位置信息
    m.add_br(
        bid="b25", category="usability",
        desc="系统内增加电子签章位置信息，当进行签章操作时自动代入此位置信息减少手动调整操作",
        entities_involved=["E-SP"],
        source_ref="20.9.1.2",
        signal_type="usability",
        note={"comment": "signal_type 命中'自动代入'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b26: 审批流程列表增加创建时间查询与导出
    m.add_br(
        bid="b26", category="usability",
        desc="审批流程列表增加创建时间查询，并增加结果导出能力；在审核流程列表查询区域'任务类型'查询参数后增加'创建时间'查询参数；增加'导出'按钮导出满足当前查询条件的数据",
        entities_involved=["E-SP"],
        source_ref="20.9.1.5",
        signal_type="usability",
        note={"comment": "signal_type 命中'增加...查询/导出能力'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b27: 自定义流程预设4个以内
    m.add_br(
        bid="b27", category="validation",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
        entities_involved=["E-SP"],
        source_ref="20.9.1.6",
        signal_type="field_constraint",
        constrained_entity="E-SP",
        note={"comment": "signal_type 命中'4个以内'属取值范围→field_constraint；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-SP"},
    )
    # b28: 缴费信息多维度筛选与导出
    m.add_br(
        bid="b28", category="usability",
        desc="缴费信息可以按照时间维度（月、季度、年度、自选择时间范围）、业务维度（能力验证、测量审核）、发票类型维度（电子专票、电子普票）进行筛选，并支持导出功能",
        entities_involved=["E-JFD"],
        source_ref="20.10.1",
        signal_type="usability",
        note={"comment": "signal_type 命中'可以按照...进行筛选/支持导出'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b29: 发票上传支持多次分批上传
    m.add_br(
        bid="b29", category="usability",
        desc="调整项目列表中的发票上传功能，修改后支持多次分批上传发票；发票上传后会显示在发票列表中，点击文件地址后的'x'可以移除文件（表单提交后生效）",
        entities_involved=["E-BMJL"],
        source_ref="20.10.2.2",
        signal_type="usability",
        note={"comment": "signal_type 命中'支持...分批上传'属功能支持→usability；category 判交互易用性功能→usability"},
    )
    # b30: 退款金额不能大于当前缴费金额
    m.add_br(
        bid="b30", category="validation",
        desc="退款金额必填，不能大于当前缴费金额；退款金额使用红色字体且大于0时显示；实际付款=付款金额-退款金额",
        entities_involved=["E-JFD", "E-BMJL"],
        source_ref="20.10.2.3",
        signal_type="restrictive",
        constrained_entity="E-JFD",
        note={"comment": "signal_type 命中 prohibit_keywords '不能大于当前缴费金额'→restrictive；category 判数据/业务有效性校验→validation；constrained_entity 判①：门禁对象为 E-JFD（缴费记录退款）"},
    )
    # b31: 项目类型分支约束（能力验证/测量审核）
    m.add_br(
        bid="b31", category="validation",
        desc="项目类型分为能力验证与测量审核两种；能力验证项目创建后进入待开始状态，测量审核项目创建后直接进入报名中状态",
        entities_involved=["E-XM"],
        source_ref="19.1；19.2",
        signal_type="field_constraint",
        note={"branch_dimension": "项目类型",
              "comment": "配置型分支（对应 E-XM.is_config 属性 项目类型，值域=能力验证/测量审核）；desc 含分支值字面量'能力验证/测量审核'；signal_type 命中'取值范围'属字段约束→field_constraint；category 判数据/业务有效性校验→validation；两路径差异同 Step 3 分支表（t01 vs t01b）"},
    )

    return m
