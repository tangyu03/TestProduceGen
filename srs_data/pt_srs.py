"""网数中心能力验证服务平台升级维护项目 需求数据。

结构概览（仅供自身定位）：
- 文档涵盖实验室信息/标准库/能力验证项目/测量审核项目/报名记录/样品/预通知/费用/发票/付款/退款/评价/证书/结果通知单/结果报告/文件整理/流程审批等模块
- 主流程：能力验证提供者流程与测量审核提供者流程（19.1/19.2）的项目状态机
- 状态维度主要来源：19.3 项目状态分析 + 20.4-20.10 详细功能描述
- 角色映射：20-章中固定/非固定角色列表
- 局部标签：
  * 角色 r01-r14
  * 实体 E-LAB, E-STD, E-TEST, E-CTEST, E-MSG, E-PTXM, E-MAXM, E-BM, E-YP,
          E-YT, E-JF, E-FY, E-FP, E-FK, E-TK, E-PJ, E-PJXM, E-ZS, E-JG, E-BG,
          E-WJZL, E-SP
  * 转换 t01-t75（E-LAB: t01-t07; E-STD: t08-t11; E-PTXM: t12-t17;
              E-MAXM: t18-t23; E-BM: t24-t35; E-YP: t36-t41; E-YT: t42-t48;
              E-FY: t49-t50; E-FP: t51-t52; E-JF: t53-t54; E-PJ: t55-t59;
              E-ZS: t60-t62; E-JG: t63-t67; E-BG: t68-t70; E-WJZL: t71-t72;
              E-SP: t73-t75）
  * 分支 bd01-bd04；XC x01-x12；BR b01-b20；IT it01-it06
"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704.md",
        document_scope="能力验证服务平台升级维护项目需求分析与设计：覆盖项目背景、目标、要求、用户角色、系统流程、能力验证/测量审核项目管理、报名记录、样品、评价、统计分析、业务审核、财务管理等核心模块；不含非功能性需求的具体技术实现细节",
    )

    # ============================================================
    # Step 0: 动词种子词表
    # ============================================================
    m.set_prohibition_config(config={
        "action_verbs": [
            "新增", "修改", "删除", "启用", "停用", "审核", "退回", "确认",
            "提交", "保存", "查询", "重置", "导出", "导入", "上传", "下载",
            "发放", "归还", "回收", "签发", "批准", "撤销", "归档", "整理",
            "报名", "缴费", "开票", "退款", "评价", "统计", "发布", "发送",
            "通知", "提醒", "跳转", "查看", "编辑", "选择", "填充", "添加",
            "登录", "登出", "审批", "通过", "拒绝", "重启", "暂停", "结束",
            "选入", "纳入", "执行", "收回", "抄送", "下钻",
        ],
        "prohibit_keywords": [
            "未结束的项目不可以进行消息发送",
            "含有子项的记录不允许删除",
            "退款金额不能大于当前缴费金额",
            "只有已上传对应文件且未提交审核的记录才可以被选定",
            "评价人员不能查看和修改其他评价人员的评价结果",
            "未结束的项目才可以进行消息发送",
        ],
    })

    # ============================================================
    # Step 0.5: 角色与权限
    # ============================================================
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

    m.add_permission(role="系统管理人员", operations=[
        "查看信息发送记录", "查询信息发送记录", "管理用户角色", "管理机构信息",
        "查询实验室", "审核实验室", "启用实验室", "停用实验室", "修改实验室",
        "查询标准库", "新增标准库", "修改标准库", "删除标准库", "启用标准库",
        "停用标准库", "管理测试项", "新增测试项", "修改测试项", "删除测试项",
        "查询子领域测试项", "新增子领域测试项", "删除子领域测试项",
        "查询通知管理", "查询意见反馈", "管理内容", "查询统计模板",
    ])
    m.add_permission(role="项目管理员", operations=[
        "查看信息发送记录", "查询项目", "新增项目", "编辑项目", "删除项目",
        "查询项目附件", "上传附件", "下载附件", "代码导入", "批量处理项目",
        "上传结果通知单", "上传证书", "提交审核", "发送消息", "测试消息发送",
        "文件整理", "查看归档", "上传归档文件", "打包下载归档", "编辑归档",
        "修改财务备注", "上传发票", "退款", "查询缴费记录", "导出缴费信息",
        "查询项目统计", "查询客户统计", "查询收入统计", "查询报名信息",
        "管理项目人员", "另存常用测试项", "管理常用测试项", "删除常用测试项",
    ])
    m.add_permission(role="实验室负责人", operations=[
        "审批项目立项", "批准邀请函", "签发证书", "批准证书",
        "查看项目", "查询项目",
    ])
    m.add_permission(role="技术主管", operations=[
        "审批物品配置方案", "审批评价细则", "审核邀请函", "审核报告",
        "审核结果通知单", "审核证书", "查看项目",
    ])
    m.add_permission(role="授权签字人", operations=[
        "批准结果报告", "批准结果通知单", "批准使用认可标识", "查看项目",
    ])
    m.add_permission(role="策划人员", operations=[
        "编制设计方案", "编制作业指导书", "编制结果报告", "编制结果通知单",
        "编制任务通知书", "项目总结", "记录归档",
    ])
    m.add_permission(role="样品制备人员", operations=[
        "编制样品制备方案", "执行样品制备", "配置样品", "核查样品", "一致性测试",
    ])
    m.add_permission(role="样品管理员", operations=[
        "样品出入库登记", "样品领用登记", "样品发放", "样品回收", "样品借出归还",
        "查询样品",
    ])
    m.add_permission(role="评价人员", operations=[
        "编制评价细则", "评价参加者结果", "导出评价结果", "查询项目",
        "修改自己评价结果",
    ])
    m.add_permission(role="统计人员", operations=[
        "结果统计分析", "查询统计分析", "导出统计报表",
    ])
    m.add_permission(role="质量专员", operations=[
        "报告统计", "查询报告统计",
    ])
    m.add_permission(role="财务管理人员", operations=[
        "确认付款信息", "查询缴费信息", "导出缴费信息", "上传发票", "退款",
        "修改财务备注", "收入统计", "查询收入统计", "查询发票",
    ])
    m.add_permission(role="能力验证参加者", operations=[
        "报名项目", "上传付款单", "上传缴费证明", "下载发票",
        "下载预通知", "提交结果报告", "归还样品", "下载结果报告",
        "下载结果通知单", "下载合格证书", "意见反馈", "查看项目",
    ])
    m.add_permission(role="监督员", operations=[
        "查看项目", "查询项目",
    ])

    # ============================================================
    # Step 1: 实体
    # ============================================================

    # ---------- E-LAB: 实验室信息 ----------
    m.add_entity(
        id="E-LAB",
        name="实验室信息",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名；状态字段包括待审核、启用、停用、已退回；列表字段含实验室名称、统一社会信用代码、状态、法人名称、企业类型、企业规模、CNAS、CMA、邮箱、座机号码、地址、联系人、联系电话、默认实验室、证明文件",
        type="core",
        tags=["approvable", "multi-state"],
        attributes=[
            attr(name="实验室编号", desc="文本输入框，模糊查询"),
            attr(name="实验室名称", desc="文本输入框，必填；模糊查询"),
            attr(name="统一社会信用代码", desc="文本输入框，必填；唯一"),
            attr(name="法人名称", desc="文本输入框"),
            attr(name="企业类型", desc="下拉列表"),
            attr(name="企业规模", desc="下拉列表"),
            attr(name="CNAS", desc="已获CNAS认可；CNAS证书号"),
            attr(name="CMA", desc="已获CMA认可；CMA证书编号"),
            attr(name="邮箱", desc="文本输入框"),
            attr(name="座机号码", desc="文本输入框"),
            attr(name="行政区域", desc="下拉列表"),
            attr(name="详细地址", desc="文本输入框"),
            attr(name="联系人", desc="文本输入框，必填"),
            attr(name="联系电话", desc="文本输入框，必填"),
            attr(name="默认实验室", desc="布尔；标识默认实验室"),
            attr(name="证明文件", desc="文件上传；提示请上传营业执照或其他证书材料"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "已退回", "启用", "停用"],
                "initial": "待审核",
                "terminal": [],
                "note": {"comment": "状态字段在20.3.1与20.4.1.1原文明确列出待审核、启用、停用、已退回；新建实验室默认进入待审核"},
            },
        ],
        operations=[
            op(name="实验室列表查询", category="query",
               expected_results=["分页展示符合条件的实验室记录"],
               source_ref="20.4.1.1",
               note=N(comment="支持实验室编号/名称/状态独立或组合查询")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并分页展示所有数据"],
               source_ref="20.4.1.1",
               note=N(comment="通用操作")),
            op(name="新增实验室", category="crud",
               expected_results=["实验室状态变为待审核，等待审核通过"],
               source_ref="20.3.1",
               note=N(comment="对应转换 t01；机构新增实验室后需管理用户审核")),
            op(name="修改实验室", category="crud",
               expected_results=["触发状态重新变为待审核"],
               source_ref="20.4.1.3",
               note=N(comment="对应转换 t02；修改后需重新审核")),
            op(name="审核实验室", category="crud",
               expected_results=["状态变更为启用或已退回"],
               source_ref="20.4.1.2",
               note=N(comment="对应转换 t03/t04；仅待审核状态显示审核按钮")),
            op(name="停用实验室", category="crud",
               expected_results=["状态变更为停用"],
               source_ref="20.4.1.1",
               note=N(comment="对应转换 t06；仅启用状态显示停用按钮")),
            op(name="启用实验室", category="crud",
               expected_results=["状态变更为启用"],
               source_ref="20.4.1.1",
               note=N(comment="对应转换 t07；仅停用状态显示启用按钮")),
            op(name="下载证明文件", category="file",
               expected_results=["下载实验室证明文件"],
               source_ref="20.4.1.1",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-STD: 标准库 ----------
    m.add_entity(
        id="E-STD",
        name="标准库",
        desc="代表一个完整的、可被引用的标准集合；状态包括启用/停用；停用的标准库在项目创建等环节不可被选择",
        type="managed",
        tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="文本输入框，必填；模糊查询"),
            attr(name="标准库名称", desc="文本输入框，必填；模糊查询"),
            attr(name="状态", desc="单选框；包含启用、停用；必填", is_config=True),
            attr(name="描述", desc="文本输入框，选填"),
            attr(name="创建时间", desc="系统自动记录"),
        ],
        state_dimensions=[
            {
                "dimension_name": "启用状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "note": {"comment": "20.4.2.1原文列表展示状态（启用/停用）"},
            },
        ],
        operations=[
            op(name="标准库列表查询", category="query",
               expected_results=["分页展示符合条件标准库"],
               source_ref="20.4.2.1",
               note=N(comment="支持编号/名称/状态组合查询")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.4.2.1",
               note=N(comment="通用操作")),
            op(name="新增标准库", category="crud",
               expected_results=["列表新增一条标准库记录"],
               source_ref="20.4.2.2",
               note=N(comment="对应转换 t08/t09")),
            op(name="修改标准库", category="crud",
               expected_results=["刷新列表中标准库数据"],
               source_ref="20.4.2.3",
               note=N(comment="无对应状态转换；仅属性变更")),
            op(name="删除标准库", category="crud",
               expected_results=["二次确认后删除该标准库"],
               source_ref="20.4.2.4",
               note=N(comment="无对应状态转换；直接删除")),
            op(name="停用标准库", category="crud",
               expected_results=["状态变更为停用；列表刷新"],
               source_ref="20.4.2.5",
               note=N(comment="对应转换 t10；停用后项目创建环节不可被选择")),
            op(name="启用标准库", category="crud",
               expected_results=["状态变更为启用；列表刷新"],
               source_ref="20.4.2.5",
               note=N(comment="对应转换 t11")),
            op(name="管理测试项", category="ui",
               expected_results=["跳转至该标准库测试项管理界面"],
               source_ref="20.4.2.6",
               note=N(comment="对应转换：进入 E-TEST 管理")),
        ],
    )

    # ---------- E-TEST: 标准库测试项 ----------
    m.add_entity(
        id="E-TEST",
        name="标准库测试项",
        desc="由编号和名称组成的一组数据；测试项下可以有子测试项；以展开的嵌套表格方式展示",
        type="managed",
        attributes=[
            attr(name="标号", desc="文本输入框，必填"),
            attr(name="名称", desc="文本输入框，必填"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud",
               expected_results=["测试项加入到列表中"],
               source_ref="20.4.2.8",
               note=N(comment="可新增子项")),
            op(name="修改测试项", category="crud",
               expected_results=["系统校验后保存，刷新列表数据"],
               source_ref="20.4.2.9",
               note=N(comment="无对应状态转换")),
            op(name="删除测试项", category="crud",
               expected_results=["删除该测试项；含子项记录不允许删除"],
               source_ref="20.4.2.10",
               note=N(comment="含子项不可删除，对应 BR b03")),
        ],
    )

    # ---------- E-CTEST: 子领域测试项 ----------
    m.add_entity(
        id="E-CTEST",
        name="子领域测试项",
        desc="子领域下挂接的测试项；来源为标准库中已维护的测试项；以展开的树形表格展示",
        type="managed",
        attributes=[
            attr(name="标号", desc="继承自标准库测试项"),
            attr(name="名称", desc="继承自标准库测试项"),
            attr(name="子领域", desc="下拉列表，精确匹配；选项包括所有子领域信息", is_config=True),
            attr(name="标准库", desc="下拉列表，必填；变更后数据树会做数据更新", is_config=True),
        ],
        state_dimensions=[],
        operations=[
            op(name="子领域测试项列表查询", category="query",
               expected_results=["分页展示该子领域下测试项"],
               source_ref="20.4.3.2",
               note=N(comment="支持按子领域查询")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.4.3.2",
               note=N(comment="通用操作")),
            op(name="新增子领域测试项", category="crud",
               expected_results=["新标准库测试项出现在列表中"],
               source_ref="20.4.3.3",
               note=N(comment="选择标准库中测试项进行挂接")),
            op(name="删除子领域测试项", category="crud",
               expected_results=["删除该子领域测试项；含子项不可删除"],
               source_ref="20.4.3.4",
               note=N(comment="对应 BR b03；含子项不可删除")),
        ],
    )

    # ---------- E-MSG: 信息发送记录 ----------
    m.add_entity(
        id="E-MSG",
        name="信息发送记录",
        desc="记录系统中的信息发送历史；内容包含发送方式、接收人、发送时间、发送人、发送结果；只有系统管理员和项目管理员可以查看",
        type="managed",
        attributes=[
            attr(name="接收号码", desc="文本输入框，模糊匹配"),
            attr(name="发送方式", desc="下拉列表，精确匹配；选项有短信、邮件、站内信", is_config=True),
            attr(name="发送时间", desc="时间范围选择框，精确匹配"),
            attr(name="消息标题", desc="文本"),
            attr(name="消息内容", desc="文本"),
            attr(name="发送人", desc="系统自动记录"),
            attr(name="发送结果", desc="系统自动记录"),
        ],
        state_dimensions=[],
        operations=[
            op(name="信息发送记录查询", category="query",
               expected_results=["分页展示符合条件的发送记录"],
               source_ref="20.4.4.1",
               note=N(comment="支持接收号码/发送时间/发送方式组合查询")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件"],
               source_ref="20.4.4.1",
               note=N(comment="通用操作")),
            op(name="查看消息详情", category="ui",
               expected_results=["显示消息详细内容"],
               source_ref="20.4.4.1",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-PTXM: 能力验证项目 ----------
    m.add_entity(
        id="E-PTXM",
        name="能力验证项目",
        desc="能力验证提供者主流程实体；项目状态包括待开始、报名中、进行中、报告审核中、已结束；并增加文件归档阶段；项目人员含技术主管、实验室负责人、授权签字人、监督员",
        type="core",
        tags=["multi-state", "collaborative", "expirable"],
        attributes=[
            attr(name="项目编号", desc="系统自动生成"),
            attr(name="项目名称", desc="文本输入框，必填"),
            attr(name="产品类型", desc="下拉框", is_config=True),
            attr(name="项目类型", desc="能力验证", is_config=True),
            attr(name="所属年度", desc="时间选择"),
            attr(name="依据标准", desc="关联标准库"),
            attr(name="项目费用", desc="数值；财务可修改"),
            attr(name="子领域", desc="下拉列表", is_config=True),
            attr(name="技术主管", desc="下拉框；备选人唯一时默认填充"),
            attr(name="实验室负责人", desc="下拉框；备选人唯一时默认填充"),
            attr(name="授权签字人", desc="下拉框；备选人唯一时默认填充"),
            attr(name="监督员", desc="下拉框；可以为空；导出项目通知书时填充"),
            attr(name="评价人员", desc="多选；第一个被选择的评价人员默认作为评价组长"),
            attr(name="评分方式", desc="单选；分值/权重", is_config=True),
            attr(name="财务备注", desc="文本；财务管理人员可修改"),
            attr(name="机构代码", desc="批量导入报名机构三方代码"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束", "已归档"],
                "initial": "待开始",
                "terminal": ["已归档"],
                "inferred": ["已归档"],
                "note": {"comment": "19.3明确列出待开始/报名中/进行中/报告审核中/已结束；20.5.1.1新增文件整理后已结束项目可整理归档，推断已归档为终态"},
            },
        ],
        operations=[
            op(name="项目列表查询", category="query",
               expected_results=["分页展示项目记录"],
               source_ref="20.5.1",
               note=N(comment="通用操作")),
            op(name="新增项目", category="crud",
               expected_results=["项目状态初始化为待开始"],
               source_ref="20.5.1",
               note=N(comment="对应转换 t12")),
            op(name="编辑项目", category="crud",
               expected_results=["保存项目信息"],
               source_ref="20.5.1",
               note=N(comment="无对应状态转换；仅属性变更")),
            op(name="删除项目", category="crud",
               expected_results=["项目从列表中删除"],
               source_ref="20.2.3",
               note=N(comment="待办事项中提及能力验证项目删除；无对应状态转换")),
            op(name="代码导入", category="file",
               expected_results=["导入报名机构三方代码"],
               source_ref="20.5.1.2",
               note=N(comment="数据文件必填")),
            op(name="批量处理", category="crud",
               expected_results=["跳转至报名信息批量处理页面"],
               source_ref="20.5.1.3",
               note=N(comment="含上传结果通知单/证书/批量提交审核")),
            op(name="上传结果通知单", category="file",
               expected_results=["记录对应结果通知单文件"],
               source_ref="20.5.1.3",
               note=N(comment="通用操作")),
            op(name="上传证书", category="file",
               expected_results=["记录对应证书文件"],
               source_ref="20.5.1.3",
               note=N(comment="通用操作")),
            op(name="提交审核", category="crud",
               expected_results=["对所选记录进行任务提交操作"],
               source_ref="20.5.1.3",
               note=N(comment="仅已上传文件且未提交审核记录可选")),
            op(name="发送消息", category="crud",
               expected_results=["按选定方式发送消息"],
               source_ref="20.5.1.4",
               note=N(comment="未结束项目可发送；接收人1/2不能同时为空")),
            op(name="测试消息发送", category="crud",
               expected_results=["发送测试信息"],
               source_ref="20.5.1.4",
               note=N(comment="通用操作")),
            op(name="另存常用测试项", category="crud",
               expected_results=["保存当前测试项组合为常用项"],
               source_ref="20.5.1.7",
               note=N(comment="通用操作")),
            op(name="管理常用测试项", category="crud",
               expected_results=["选择/删除常用项"],
               source_ref="20.5.1.7",
               note=N(comment="通用操作")),
            op(name="文件整理", category="crud",
               expected_results=["提示\"归档任务已开启，请稍后查看\"；操作列变为查看归档"],
               source_ref="20.5.1.1",
               note=N(comment="对应转换 t17；仅已结束项目显示按钮")),
            op(name="查看归档", category="ui",
               expected_results=["进入归档数据查看页面"],
               source_ref="20.5.1.1",
               note=N(comment="整理完成后显示")),
            op(name="上传归档文件", category="file",
               expected_results=["补充文件项目阶段为其它"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
            op(name="打包下载归档", category="file",
               expected_results=["下载zip格式归档文件"],
               source_ref="20.5.1.1",
               note=N(comment="zip内含清单文件及按项目阶段命名的目录")),
            op(name="下载归档文件", category="file",
               expected_results=["下载当前归档文件"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
            op(name="编辑归档", category="crud",
               expected_results=["打开编辑表单弹窗"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
            op(name="导出项目通知书", category="file",
               expected_results=["导出含监督员等信息的项目通知书"],
               source_ref="20.5.1.5",
               note=N(comment="监督员字段填充到对应位置")),
        ],
    )

    # ---------- E-MAXM: 测量审核项目 ----------
    m.add_entity(
        id="E-MAXM",
        name="测量审核项目",
        desc="测量审核提供者主流程实体；项目状态包括待开始、报名中、进行中、报告审核中、已结束；项目人员配置同能力验证项目",
        type="core",
        tags=["multi-state", "collaborative", "expirable"],
        attributes=[
            attr(name="项目编号", desc="系统自动生成"),
            attr(name="项目名称", desc="文本输入框，必填"),
            attr(name="产品类型", desc="下拉框", is_config=True),
            attr(name="项目类型", desc="测量审核", is_config=True),
            attr(name="所属年度", desc="时间选择"),
            attr(name="依据标准", desc="关联标准库"),
            attr(name="项目费用", desc="数值"),
            attr(name="子领域", desc="下拉列表", is_config=True),
            attr(name="技术主管", desc="下拉框；备选人唯一时默认填充"),
            attr(name="实验室负责人", desc="下拉框；备选人唯一时默认填充"),
            attr(name="授权签字人", desc="下拉框；备选人唯一时默认填充"),
            attr(name="监督员", desc="下拉框；可以为空"),
            attr(name="评分方式", desc="单选；分值/权重", is_config=True),
            attr(name="财务备注", desc="文本；财务管理人员可修改"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["报名中", "待开始", "进行中", "报告审核中", "已结束", "已归档"],
                "initial": "报名中",
                "terminal": ["已归档"],
                "inferred": ["已归档"],
                "note": {"comment": "19.2测量审核流程受理报名后进入报名中状态；推断已归档为终态；与能力验证项目状态集合一致但初态不同"},
            },
        ],
        operations=[
            op(name="项目列表查询", category="query",
               expected_results=["分页展示测量审核项目记录"],
               source_ref="20.6.1",
               note=N(comment="通用操作")),
            op(name="新增项目", category="crud",
               expected_results=["项目状态初始化为报名中"],
               source_ref="20.6.1",
               note=N(comment="对应转换 t18；测量审核受理报名即创建")),
            op(name="编辑项目", category="crud",
               expected_results=["保存项目信息"],
               source_ref="20.6.1",
               note=N(comment="无对应状态转换")),
            op(name="发送消息", category="crud",
               expected_results=["按选定方式发送消息"],
               source_ref="20.6.1.2",
               note=N(comment="未结束项目可发送；接收人1/2不能同时为空")),
            op(name="测试消息发送", category="crud",
               expected_results=["发送测试信息"],
               source_ref="20.6.1.2",
               note=N(comment="通用操作")),
            op(name="另存常用测试项", category="crud",
               expected_results=["保存当前测试项组合为常用项"],
               source_ref="20.6.1.5",
               note=N(comment="通用操作")),
            op(name="管理常用测试项", category="crud",
               expected_results=["选择/删除常用项"],
               source_ref="20.6.1.5",
               note=N(comment="通用操作")),
            op(name="文件整理", category="crud",
               expected_results=["提示\"归档任务已开启\"；操作列变为查看归档"],
               source_ref="20.6.1.1",
               note=N(comment="对应转换 t23；仅已结束项目显示按钮")),
            op(name="查看归档", category="ui",
               expected_results=["进入归档数据查看页面"],
               source_ref="20.6.1.1",
               note=N(comment="通用操作")),
            op(name="上传归档文件", category="file",
               expected_results=["补充文件项目阶段为其它"],
               source_ref="20.6.1.1",
               note=N(comment="通用操作")),
            op(name="打包下载归档", category="file",
               expected_results=["下载zip格式归档文件"],
               source_ref="20.6.1.1",
               note=N(comment="通用操作")),
            op(name="下载归档文件", category="file",
               expected_results=["下载当前归档文件"],
               source_ref="20.6.1.1",
               note=N(comment="通用操作")),
            op(name="编辑归档", category="crud",
               expected_results=["打开编辑表单弹窗"],
               source_ref="20.6.1.1",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-BM: 报名记录 ----------
    m.add_entity(
        id="E-BM",
        name="报名记录",
        desc="参加者报名能力验证/测量审核项目的记录；状态包括报名待审核、报名退回、报名成功、结果待提交、结果已提交、结果退回修改、报告/证书审核中、报告/证书已发布、已撤销；含通知状态/费用状态/发票状态等多个维度",
        type="core",
        tags=["multi-state", "expirable"],
        attributes=[
            attr(name="报名编号", desc="系统自动生成；模糊匹配"),
            attr(name="项目编号", desc="关联项目；只读"),
            attr(name="项目名称", desc="关联项目；只读"),
            attr(name="统一社会信用代码", desc="关联实验室"),
            attr(name="实验室名称", desc="关联实验室"),
            attr(name="报名时间", desc="系统自动记录"),
            attr(name="报名表", desc="文件附件"),
            attr(name="测试结果", desc="文件附件"),
            attr(name="报名表盖章版", desc="文件附件"),
            attr(name="结果通知单", desc="文件附件"),
            attr(name="证书", desc="文件附件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交",
                           "结果已提交", "结果退回修改", "报告/证书审核中",
                           "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "note": {"comment": "19.3项目状态分析明确列出报名记录状态值集合"},
            },
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "note": {"comment": "19.3明确列出费用状态值；报名成功后生成待缴费记录"},
            },
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "note": {"comment": "19.3明确列出发票状态值"},
            },
        ],
        operations=[
            op(name="报名项目", category="crud",
               expected_results=["生成报名记录，状态为报名待审核"],
               source_ref="19.4",
               note=N(comment="对应转换 t24；参加者报名能力验证")),
            op(name="审核报名", category="crud",
               expected_results=["状态变更为报名成功或报名退回"],
               source_ref="20.5.3.2",
               note=N(comment="对应转换 t25/t26；通过/退回均触发短信")),
            op(name="上传付款单", category="file",
               expected_results=["生成付款记录；可多次上传"],
               source_ref="20.5.2.1",
               note=N(comment="对应 E-FK；不校验付款金额限制")),
            op(name="下载预通知", category="file",
               expected_results=["下载预通知文件"],
               source_ref="20.5.2.2",
               note=N(comment="通用操作")),
            op(name="提交结果报告", category="crud",
               expected_results=["报名记录状态变更为结果已提交"],
               source_ref="19.4",
               note=N(comment="对应转换 t29")),
            op(name="归还样品", category="crud",
               expected_results=["样品状态变更为已还样"],
               source_ref="19.4",
               note=N(comment="对应 E-YP 转换 t40")),
            op(name="下载结果报告", category="file",
               expected_results=["下载能力验证计划结果报告"],
               source_ref="19.4",
               note=N(comment="通用操作")),
            op(name="下载结果通知单", category="file",
               expected_results=["下载个人结果通知单"],
               source_ref="19.4",
               note=N(comment="通用操作")),
            op(name="下载合格证书", category="file",
               expected_results=["下载能力验证合格证书"],
               source_ref="19.4",
               note=N(comment="通用操作")),
            op(name="撤销报名", category="crud",
               expected_results=["报名记录状态变更为已撤销"],
               source_ref="19.1",
               note=N(comment="对应转换 t35")),
        ],
    )

    # ---------- E-YP: 样品 ----------
    m.add_entity(
        id="E-YP",
        name="样品",
        desc="能力验证/测量审核物品；状态包括待核查、已核查、待发样、待收样、已收样、已发样、已还样、已确认、无需还样",
        type="core",
        tags=["multi-state"],
        attributes=[
            attr(name="样品编号", desc="系统自动生成"),
            attr(name="样品名称", desc="文本"),
            attr(name="所属项目", desc="关联项目"),
            attr(name="所属报名记录", desc="关联报名记录"),
            attr(name="快递单号", desc="文本；发放时记录"),
            attr(name="软件访问路径", desc="软件类样品的访问路径"),
            attr(name="核查记录表", desc="文件附件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查", "待发样", "待收样", "已收样",
                           "已发样", "已还样", "已确认", "无需还样"],
                "initial": "待核查",
                "terminal": ["已还样", "无需还样"],
                "inferred": ["待发样", "待收样", "已收样", "已还样", "无需还样", "已确认"],
                "note": {"comment": "19.3明确列出待核查/已核查；19.1流程表中出现待发样/已发样/已还样/无需还样/已确认；推断终态为已还样/无需还样"},
            },
        ],
        operations=[
            op(name="样品领用登记", category="crud",
               expected_results=["样品状态初始化为待核查"],
               source_ref="19.2",
               note=N(comment="对应转换 t36")),
            op(name="样品核查", category="crud",
               expected_results=["状态变更为已核查；生成核查记录表"],
               source_ref="19.1",
               note=N(comment="对应转换 t37")),
            op(name="样品发放", category="crud",
               expected_results=["状态变更为已发样；记录快递单号或软件访问路径"],
               source_ref="19.1",
               note=N(comment="对应转换 t39")),
            op(name="样品归还", category="crud",
               expected_results=["状态变更为已还样"],
               source_ref="19.4",
               note=N(comment="对应转换 t40")),
            op(name="样品确认", category="crud",
               expected_results=["状态变更为已确认"],
               source_ref="19.1",
               note=N(comment="对应转换；参加者接收样品确认")),
            op(name="样品出入库登记", category="crud",
               expected_results=["库存记录更新"],
               source_ref="18.12",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-YT: 预通知 ----------
    m.add_entity(
        id="E-YT",
        name="预通知",
        desc="能力验证/测量审核预通知；状态包括未发送、已发送、待确认、待审核、退回、已审核、已批准",
        type="managed",
        attributes=[
            attr(name="通知标题", desc="文本"),
            attr(name="通知内容", desc="文本"),
            attr(name="用户信息表", desc="文件附件"),
            attr(name="发送方式", desc="短信/邮件/站内信", is_config=True),
        ],
        state_dimensions=[
            {
                "dimension_name": "通知状态",
                "states": ["未发送", "已发送", "待确认", "待审核", "退回",
                           "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已批准"],
                "note": {"comment": "19.3明确列出通知状态值；测量审核流程含待审核/退回/已审核"},
            },
        ],
        operations=[
            op(name="发送预通知", category="crud",
               expected_results=["通知状态变更为已发送"],
               source_ref="19.1",
               note=N(comment="对应转换 t43")),
            op(name="审核预通知", category="crud",
               expected_results=["状态变更为已审核或退回"],
               source_ref="19.2",
               note=N(comment="对应转换 t45/t46")),
        ],
    )

    # ---------- E-JF: 缴费通知单 ----------
    m.add_entity(
        id="E-JF",
        name="缴费通知单",
        desc="项目管理员发送给参加者的缴费通知；状态包括未发送/已发送",
        type="managed",
        attributes=[
            attr(name="缴费通知书", desc="文件附件"),
            attr(name="关联报名记录", desc="关联 E-BM"),
        ],
        state_dimensions=[
            {
                "dimension_name": "缴费通知状态",
                "states": ["未发送", "已发送"],
                "initial": "未发送",
                "terminal": ["已发送"],
                "note": {"comment": "19.1流程表中缴费通知单列出现未发送/已发送"},
            },
        ],
        operations=[
            op(name="发送缴费通知", category="crud",
               expected_results=["状态变更为已发送"],
               source_ref="19.1",
               note=N(comment="对应转换 t54")),
        ],
    )

    # ---------- E-FY: 费用 ----------
    m.add_entity(
        id="E-FY",
        name="费用",
        desc="报名记录关联的费用记录；状态包括待缴费/已缴费；支持多次付款及退款",
        type="managed",
        attributes=[
            attr(name="应收金额", desc="数值；默认为项目费用"),
            attr(name="已收金额", desc="数值；累加多次付款金额"),
            attr(name="退款金额", desc="数值；多次退款累加；大于0时显示红色字体"),
            attr(name="实际付款", desc="数值；付款金额-退款金额"),
            attr(name="管理备注", desc="文本；退款原因等"),
            attr(name="到款时间", desc="系统记录"),
            attr(name="关联报名记录", desc="关联 E-BM"),
        ],
        state_dimensions=[
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "note": {"comment": "19.3明确列出费用状态值；报名成功后生成待缴费记录"},
            },
        ],
        operations=[
            op(name="确认付款", category="crud",
               expected_results=["费用状态变更为已缴费"],
               source_ref="18.16",
               note=N(comment="对应转换 t50；财务管理人员确认")),
        ],
    )

    # ---------- E-FP: 发票 ----------
    m.add_entity(
        id="E-FP",
        name="发票",
        desc="报名记录关联的发票；状态包括待开票/已开票；支持分批多次上传",
        type="managed",
        attributes=[
            attr(name="开票时间", desc="时间选择框；最后一次开票时间"),
            attr(name="电子发票", desc="文件选择组件；可多次分批上传"),
            attr(name="开票类型", desc="电子专票/电子普票", is_config=True),
            attr(name="关联报名记录", desc="关联 E-BM"),
            attr(name="项目金额", desc="数值；只读"),
        ],
        state_dimensions=[
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "note": {"comment": "19.3明确列出发票状态值"},
            },
        ],
        operations=[
            op(name="发票上传", category="file",
               expected_results=["发票状态变更为已开票；支持分批多次上传"],
               source_ref="20.10.2.2",
               note=N(comment="对应转换 t52")),
            op(name="移除发票", category="crud",
               expected_results=["表单提交后从发票列表移除该文件"],
               source_ref="20.10.2.2",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-FK: 付款 ----------
    m.add_entity(
        id="E-FK",
        name="付款",
        desc="参加者上传的付款底单记录；支持多次付款；不对付款金额进行校验限制",
        type="managed",
        attributes=[
            attr(name="支付方式", desc="下拉选择框，必填", is_config=True),
            attr(name="支付账户名称", desc="文本输入框，必填"),
            attr(name="汇款金额", desc="文本输入框，必填；默认为项目费用金额"),
            attr(name="付款底单", desc="文件选择框，必填"),
            attr(name="付款项目", desc="文本输入框，只读；内容为当前报名编号"),
            attr(name="备注", desc="文本输入框，选填"),
            attr(name="关联报名记录", desc="关联 E-BM"),
        ],
        state_dimensions=[],
        operations=[
            op(name="上传付款单", category="file",
               expected_results=["生成付款记录；可多次上传"],
               source_ref="20.5.2.1",
               note=N(comment="无独立状态维度；联动 E-FY 费用状态变化")),
        ],
    )

    # ---------- E-TK: 退款 ----------
    m.add_entity(
        id="E-TK",
        name="退款",
        desc="缴费记录的退款记录；多次退款金额做累加处理；退款后更新项目费用为实际付款金额",
        type="managed",
        attributes=[
            attr(name="退款金额", desc="文本输入框，必填；不能为大于当前缴费金额"),
            attr(name="备注", desc="文本输入框，选填；退款原因等"),
            attr(name="关联缴费记录", desc="关联 E-FY"),
        ],
        state_dimensions=[],
        operations=[
            op(name="申请退款", category="crud",
               expected_results=["退款金额累加；实际付款更新为付款金额-退款金额"],
               source_ref="20.10.2.3",
               note=N(comment="无独立状态维度；联动 E-FY 金额更新")),
        ],
    )

    # ---------- E-PJ: 评价 ----------
    m.add_entity(
        id="E-PJ",
        name="评价",
        desc="评价人员对参加者结果进行评价的过程；评价人员只能修改自己的评价结果；评价组长可在评价结果确认页面查看各评价人员结果并对最终结果进行确认",
        type="core",
        tags=["approvable", "collaborative"],
        attributes=[
            attr(name="评价项目", desc="关联 E-PJXM"),
            attr(name="评价人员", desc="多选；第一个被选中的评价人员默认作为评价组长"),
            attr(name="评价组长", desc="默认第一个评价人员"),
            attr(name="评分方式", desc="分值/权重", is_config=True),
            attr(name="及格分", desc="数值；评价组长录入后跟随其他结果一起记录"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["未评价", "评价中", "评价确认中", "评价完成"],
                "initial": "未评价",
                "terminal": ["评价完成"],
                "inferred": ["未评价", "评价中", "评价确认中", "评价完成"],
                "note": {"comment": "20.7未明确状态枚举；依据协同评价/评价确认/退回修改流程推断四态状态机"},
            },
        ],
        operations=[
            op(name="完善评价项目", category="crud",
               expected_results=["保存评价项目及评价细则内容"],
               source_ref="20.7.1.1",
               note=N(comment="无对应状态转换；评价组长在评价前完善")),
            op(name="评价", category="crud",
               expected_results=["评价人员提交自己评价结果"],
               source_ref="20.7.1.2",
               note=N(comment="对应转换 t56/t57；评价人员只能修改自己的结果")),
            op(name="结果确认", category="crud",
               expected_results=["项目评价状态关闭；结果正式提交为最终评价结果"],
               source_ref="20.7.1.3",
               note=N(comment="对应转换 t58；评价组长执行")),
            op(name="保存历史", category="crud",
               expected_results=["当前评价结果保存为历史结果"],
               source_ref="20.7.1.3",
               note=N(comment="通用操作")),
            op(name="调整细则", category="ui",
               expected_results=["打开评价细节完善页面；返回后刷新本页面数据"],
               source_ref="20.7.1.3",
               note=N(comment="通用操作")),
            op(name="退回修改", category="crud",
               expected_results=["当前评价结果保存为历史；开启下一轮评价"],
               source_ref="20.7.1.3",
               note=N(comment="对应转换 t59；组长执行")),
            op(name="调整统计规则", category="crud",
               expected_results=["配置统计规则；规则含低值/高值，判断大于等于低值小于高值"],
               source_ref="20.7.1.3",
               note=N(comment="通用操作")),
            op(name="导出评价结果", category="file",
               expected_results=["下载评价结果"],
               source_ref="20.7.1.4",
               note=N(comment="通用操作")),
            op(name="下载历史评价结果", category="file",
               expected_results=["下载评价历史结果文件"],
               source_ref="20.7.1.3",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-PJXM: 评价项目 ----------
    m.add_entity(
        id="E-PJXM",
        name="评价项目",
        desc="评价组长完善的测试项目及评价细则；包含分值/权重、说明/评分细则、显示顺序",
        type="managed",
        attributes=[
            attr(name="标号", desc="文本框，必填"),
            attr(name="名称", desc="文本框，必填"),
            attr(name="分值/权重", desc="文本框，必填"),
            attr(name="说明/评分细则", desc="文本框，选填"),
            attr(name="显示顺序", desc="文本框，必填；用来控制数据展示顺序"),
            attr(name="调整标识", desc="选择框；标识当前行评分是否需要修改"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项目", category="crud",
               expected_results=["表单数据临时加入到数据列表"],
               source_ref="20.7.1.1",
               note=N(comment="只能新增一级测试项目")),
            op(name="修改测试项目", category="crud",
               expected_results=["打开编辑表单弹窗"],
               source_ref="20.7.1.1",
               note=N(comment="通用操作")),
            op(name="删除测试项目", category="crud",
               expected_results=["删除当前测试项和子级测试项目/评价细则数据"],
               source_ref="20.7.1.1",
               note=N(comment="通用操作")),
            op(name="新增子级评价细则", category="crud",
               expected_results=["新增该测试项的子级测试项或评价细则"],
               source_ref="20.7.1.1",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-ZS: 证书 ----------
    m.add_entity(
        id="E-ZS",
        name="证书",
        desc="能力验证合格证书；实验室负责人批准签发；证书到期前30天通过邮件方式提醒用户",
        type="core",
        tags=["expirable"],
        attributes=[
            attr(name="证书编号", desc="系统自动生成"),
            attr(name="签发时间", desc="系统自动记录"),
            attr(name="到期时间", desc="系统计算；签发后到期前30天触发提醒"),
            attr(name="关联报名记录", desc="关联 E-BM"),
            attr(name="合格证书文件", desc="文件附件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "证书状态",
                "states": ["未签发", "已签发", "已到期"],
                "initial": "未签发",
                "terminal": ["已到期"],
                "inferred": ["未签发", "已签发", "已到期"],
                "note": {"comment": "20.5.2.3提及证书到期前30天提醒；推断证书生命周期含未签发/已签发/已到期三态"},
            },
        ],
        operations=[
            op(name="签发证书", category="crud",
               expected_results=["证书状态变更为已签发"],
               source_ref="18.6",
               note=N(comment="对应转换 t61；实验室负责人批准")),
            op(name="下载合格证书", category="file",
               expected_results=["下载合格证书文件"],
               source_ref="19.4",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-JG: 结果通知单 ----------
    m.add_entity(
        id="E-JG",
        name="结果通知单",
        desc="策划人员编制、技术主管审核、授权签字人批准、项目管理员发放的结果通知单",
        type="core",
        tags=["approvable"],
        attributes=[
            attr(name="通知单标题", desc="文本"),
            attr(name="通知单内容", desc="文本"),
            attr(name="结果通知单文件", desc="文件附件"),
            attr(name="关联项目", desc="关联 E-PTXM/E-MAXM"),
            attr(name="电子签章位置", desc="系统预置；自动代入减少手动调整"),
        ],
        state_dimensions=[
            {
                "dimension_name": "通知单状态",
                "states": ["待审核", "退回", "已批准", "已发布"],
                "initial": "待审核",
                "terminal": ["已发布"],
                "inferred": ["退回", "已批准", "已发布"],
                "note": {"comment": "20.9.1.1重构测量审核结果通知单审批流程合并为一个流程；推断通知单状态机含待审核/退回/已批准/已发布"},
            },
        ],
        operations=[
            op(name="编制结果通知单", category="crud",
               expected_results=["生成结果通知单记录，状态为待审核"],
               source_ref="19.1",
               note=N(comment="对应转换 t63；策划人员编制")),
            op(name="审核结果通知单", category="crud",
               expected_results=["状态变更为已批准或退回"],
               source_ref="19.1",
               note=N(comment="对应转换 t64/t65")),
            op(name="重新提交结果通知单", category="crud",
               expected_results=["退回状态重新变更为待审核"],
               source_ref="19.1",
               note=N(comment="对应转换 t66")),
            op(name="发放结果通知单", category="crud",
               expected_results=["状态变更为已发布；用户接收短信通知"],
               source_ref="19.1",
               note=N(comment="对应转换 t67；项目管理员发放")),
        ],
    )

    # ---------- E-BG: 结果报告 ----------
    m.add_entity(
        id="E-BG",
        name="结果报告",
        desc="策划人员编制、技术主管审核、授权签字人批准、项目管理员发放的结果报告",
        type="core",
        tags=["approvable"],
        attributes=[
            attr(name="报告标题", desc="文本"),
            attr(name="报告内容", desc="文本"),
            attr(name="结果报告文件", desc="文件附件"),
            attr(name="关联项目", desc="关联 E-PTXM/E-MAXM"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报告状态",
                "states": ["待审核", "已批准", "已发布"],
                "initial": "待审核",
                "terminal": ["已发布"],
                "inferred": ["已批准", "已发布"],
                "note": {"comment": "19.1流程含技术主管审核报告/授权签字人批准/发放结果报告；推断状态机含待审核/已批准/已发布"},
            },
        ],
        operations=[
            op(name="编制结果报告", category="crud",
               expected_results=["生成结果报告记录，状态为待审核"],
               source_ref="19.1",
               note=N(comment="对应转换 t68；策划人员编制")),
            op(name="审核结果报告", category="crud",
               expected_results=["状态变更为已批准"],
               source_ref="19.1",
               note=N(comment="对应转换 t69；技术主管审核、授权签字人批准")),
            op(name="发放结果报告", category="crud",
               expected_results=["状态变更为已发布"],
               source_ref="19.1",
               note=N(comment="对应转换 t70；项目管理员发放")),
            op(name="回收结果报告", category="crud",
               expected_results=["回收参加者提交的结果报告"],
               source_ref="19.1",
               note=N(comment="通用操作；无对应状态转换")),
        ],
    )

    # ---------- E-WJZL: 文件整理 ----------
    m.add_entity(
        id="E-WJZL",
        name="文件整理",
        desc="根据归档清单对项目文件进行分类整理，包括归档、结构化分析和数字化存储；整理任务异步执行",
        type="managed",
        attributes=[
            attr(name="归档清单", desc="文件附件"),
            attr(name="项目阶段", desc="文本；归档文件按项目阶段命名目录"),
            attr(name="文件名称", desc="文本"),
            attr(name="份数", desc="数值"),
            attr(name="页数", desc="数值"),
            attr(name="备注", desc="文本"),
            attr(name="关联项目", desc="关联 E-PTXM/E-MAXM"),
        ],
        state_dimensions=[
            {
                "dimension_name": "整理状态",
                "states": ["整理中", "已归档"],
                "initial": "整理中",
                "terminal": ["已归档"],
                "inferred": ["整理中", "已归档"],
                "note": {"comment": "20.5.1.1开启整理任务后归档任务进行中；整理完成后显示查看归档按钮；推断两态"},
            },
        ],
        operations=[
            op(name="开启整理任务", category="crud",
               expected_results=["提示\"归档任务已开启，请稍后查看\"；状态为整理中"],
               source_ref="20.5.1.1",
               note=N(comment="对应转换 t71")),
            op(name="查看归档", category="ui",
               expected_results=["进入归档数据查看页面；状态为已归档"],
               source_ref="20.5.1.1",
               note=N(comment="对应转换 t72；整理完成后显示")),
            op(name="上传归档文件", category="file",
               expected_results=["补充文件项目阶段为其它"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
            op(name="打包下载归档", category="file",
               expected_results=["下载zip格式归档文件"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
            op(name="编辑归档", category="crud",
               expected_results=["打开编辑表单弹窗"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
            op(name="下载归档文件", category="file",
               expected_results=["下载当前归档文件"],
               source_ref="20.5.1.1",
               note=N(comment="通用操作")),
        ],
    )

    # ---------- E-SP: 流程审批 ----------
    m.add_entity(
        id="E-SP",
        name="流程审批",
        desc="业务审核流程；重构测量审核结果通知单审批流程合并为一个流程；支持批量审核、自定义流程、预置签章位置；流程处理人审批顺序为提交申请时签字人的选择顺序",
        type="core",
        tags=["approvable"],
        attributes=[
            attr(name="任务类型", desc="结果通知单审核/报告审核/证书审核等", is_config=True),
            attr(name="处理人", desc="按签字人选择顺序排列"),
            attr(name="创建时间", desc="系统自动记录"),
            attr(name="审核意见", desc="文本"),
            attr(name="签章位置", desc="系统预置；自动代入"),
        ],
        state_dimensions=[
            {
                "dimension_name": "审批状态",
                "states": ["待审核", "已通过", "已退回"],
                "initial": "待审核",
                "terminal": ["已通过", "已退回"],
                "inferred": ["已通过", "已退回"],
                "note": {"comment": "20.9.1流程审批模块支持批量审核含同意/退回；推断审批状态含待审核/已通过/已退回"},
            },
        ],
        operations=[
            op(name="创建审核任务", category="crud",
               expected_results=["生成新审核任务；状态为待审核；短信通知相关负责人"],
               source_ref="20.9.1.3",
               note=N(comment="对应转换 t73")),
            op(name="批量审核", category="crud",
               expected_results=["对所选任务进行批量审核操作"],
               source_ref="20.9.1.4",
               note=N(comment="系统根据任务节点类型及内容判断是否可被批量处理")),
            op(name="审核通过", category="crud",
               expected_results=["状态变更为已通过"],
               source_ref="20.9.1",
               note=N(comment="对应转换 t74")),
            op(name="审核退回", category="crud",
               expected_results=["状态变更为已退回"],
               source_ref="20.9.1",
               note=N(comment="对应转换 t75")),
            op(name="导出审批流程", category="file",
               expected_results=["导出满足当前查询条件的数据"],
               source_ref="20.9.1.5",
               note=N(comment="通用操作")),
            op(name="查询审批流程", category="query",
               expected_results=["分页展示符合条件审批记录"],
               source_ref="20.9.1.5",
               note=N(comment="支持任务类型/创建时间查询")),
            op(name="自定义流程", category="config",
               expected_results=["选择并提交文档审核的自定义流程"],
               source_ref="20.9.1.6",
               note=N(comment="系统预设4个以内自定义流程")),
        ],
    )

    # ============================================================
    # Step 2: 结构关系
    # ============================================================
    # 判定顺序：(a)→(b)→(c)→(d)
    # (a) A为B提供配置/模板/分类，B独立创建 → reference/configuration_source
    # (b) B无独立创建，A创建时B自动入initial，每条A必有B → composition/business_ownership
    # (c) B有独立创建流程+core+容器证据 → composition/business_ownership
    # (d) B有独立创建流程/前置条件/可能永不创建，不满足(c) → reference/configuration_source

    # E-STD → E-TEST: (a) 标准库为测试项提供分类容器，测试项无独立创建入口（通过标准库管理）
    m.add_structural(
        frm="E-STD", to="E-TEST",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="标准库包含多个测试项；测试项通过标准库管理界面维护",
        confidence="high",
        note={"comment": "判(b)：测试项无独立创建流程，依附标准库创建；标准库删除须校验测试项存在性"},
    )

    # E-STD → E-CTEST: (a) 标准库为子领域测试项提供数据来源
    m.add_structural(
        frm="E-STD", to="E-CTEST",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="子领域测试项数据来源于标准库；标准库变更后数据树更新",
        confidence="high",
        note={"comment": "判(a)：标准库提供配置来源；子领域测试项通过子领域管理界面独立新增"},
    )

    # E-PTXM → E-BM: (c) 报名记录有独立创建流程（参加者报名），core，项目为其业务归属容器（报名记录归属字段继承自项目；删除项目须校验报名记录）
    m.add_structural(
        frm="E-PTXM", to="E-BM",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="能力验证项目包含多条报名记录；报名记录归属项目",
        confidence="high",
        note={"comment": "判(c)：报名记录有独立创建流程（参加者报名）+core+项目为业务归属容器"},
    )

    # E-MAXM → E-BM: (c) 同上
    m.add_structural(
        frm="E-MAXM", to="E-BM",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="测量审核项目包含多条报名记录；报名记录归属项目",
        confidence="high",
        note={"comment": "判(c)：报名记录有独立创建流程+core+项目为业务归属容器"},
    )

    # E-BM → E-FY: (b) 费用无独立创建流程，报名成功时自动生成待缴费记录
    m.add_structural(
        frm="E-BM", to="E-FY",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录对应一条费用记录；报名成功自动生成",
        confidence="high",
        note={"comment": "判(b)：费用无独立创建流程，报名成功时自动入initial待缴费；每条报名必有费用"},
    )

    # E-BM → E-FP: (b) 发票无独立创建，报名成功时自动生成待开票
    m.add_structural(
        frm="E-BM", to="E-FP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录对应一条发票记录；报名成功自动生成待开票",
        confidence="high",
        note={"comment": "判(b)：发票无独立创建流程，报名成功时自动入initial待开票；每条报名必有发票"},
    )

    # E-BM → E-FK: (d) 付款有独立创建（参加者上传付款单），可能多次/可能永不付款
    m.add_structural(
        frm="E-BM", to="E-FK",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联多次付款记录；付款由参加者独立上传",
        confidence="high",
        note={"comment": "判(d)：付款有独立上传流程，可能多次可能永不付款；不满足(c)容器证据"},
    )

    # E-FY → E-TK: (d) 退款有独立创建（财务申请退款），可能永不退款
    m.add_structural(
        frm="E-FY", to="E-TK",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="费用记录关联多次退款记录；退款由财务人员独立申请",
        confidence="high",
        note={"comment": "判(d)：退款有独立申请流程，可能多次可能永不退款"},
    )

    # E-BM → E-YP: (c) 样品有独立创建流程（样品领用登记），core，报名记录为其业务归属容器
    m.add_structural(
        frm="E-BM", to="E-YP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录关联一件样品；样品归属报名记录",
        confidence="medium",
        note={"comment": "判(c)：样品有独立创建流程+core；管理_dimension复核：样品归属也可挂靠项目侧，此处取报名记录侧"},
    )

    # E-PTXM → E-PJ: (c) 评价有独立创建流程，core，项目为其业务归属容器
    m.add_structural(
        frm="E-PTXM", to="E-PJ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="能力验证项目关联一条评价记录；评价归属项目",
        confidence="high",
        note={"comment": "判(c)：评价有独立创建流程+core+项目为业务归属容器"},
    )

    # E-MAXM → E-PJ: (c) 同上
    m.add_structural(
        frm="E-MAXM", to="E-PJ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="测量审核项目关联一条评价记录；评价归属项目",
        confidence="high",
        note={"comment": "判(c)：评价有独立创建流程+core+项目为业务归属容器"},
    )

    # E-PJ → E-PJXM: (b) 评价项目无独立创建，评价创建时自动入initial
    m.add_structural(
        frm="E-PJ", to="E-PJXM",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="评价包含多个评价项目；评价项目通过评价管理界面维护",
        confidence="high",
        note={"comment": "判(b)：评价项目无独立创建流程，依附评价创建"},
    )

    # E-BM → E-ZS: (d) 证书有独立签发流程，参加者可能未通过验证永不获取证书
    m.add_structural(
        frm="E-BM", to="E-ZS",
        relation_type="reference", cardinality="1:1",
        ownership_dimension="configuration_source",
        desc="报名记录关联证书；证书由实验室负责人独立签发",
        confidence="high",
        note={"comment": "判(d)：证书有独立签发流程，可能永不签发；不满足(c)容器证据"},
    )

    # E-PTXM → E-JG: (b) 结果通知单无独立创建，项目流程到报告编制阶段自动生成
    m.add_structural(
        frm="E-PTXM", to="E-JG",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="能力验证项目关联一条结果通知单；通知单归属项目",
        confidence="high",
        note={"comment": "判(b)：结果通知单在报告编制阶段自动生成；每条项目必有通知单"},
    )

    # E-PTXM → E-BG: (b) 结果报告同上
    m.add_structural(
        frm="E-PTXM", to="E-BG",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="能力验证项目关联一条结果报告；报告归属项目",
        confidence="high",
        note={"comment": "判(b)：结果报告在报告编制阶段自动生成；每条项目必有报告"},
    )

    # E-PTXM → E-WJZL: (d) 文件整理有独立触发流程（项目管理员手动开启），可能永不整理
    m.add_structural(
        frm="E-PTXM", to="E-WJZL",
        relation_type="reference", cardinality="1:1",
        ownership_dimension="configuration_source",
        desc="能力验证项目关联文件整理任务；任务由项目管理员手动开启",
        confidence="high",
        note={"comment": "判(d)：文件整理有独立触发流程，可能永不整理；不满足(c)容器证据"},
    )

    # E-MAXM → E-WJZL: (d) 同上
    m.add_structural(
        frm="E-MAXM", to="E-WJZL",
        relation_type="reference", cardinality="1:1",
        ownership_dimension="configuration_source",
        desc="测量审核项目关联文件整理任务；任务由项目管理员手动开启",
        confidence="high",
        note={"comment": "判(d)：文件整理有独立触发流程，可能永不整理"},
    )

    # E-JG/E-BG/E-ZS → E-SP: (d) 流程审批有独立创建（提交申请时创建），可能永不审批
    m.add_structural(
        frm="E-JG", to="E-SP",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="结果通知单关联多条审批任务；审批任务由提交申请时独立创建",
        confidence="high",
        note={"comment": "判(d)：审批任务有独立创建流程，可能永不审批；不满足(c)容器证据"},
    )

    # E-LAB → E-BM: (d) 实验室为报名记录提供主体信息，但报名记录归属项目而非实验室
    m.add_structural(
        frm="E-LAB", to="E-BM",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="实验室信息为报名记录提供主体信息；报名记录关联实验室",
        confidence="high",
        note={"comment": "判(d)：实验室仅为报名记录提供主体引用，非业务归属容器"},
    )

    # ============================================================
    # Step 3: 分支维度
    # ============================================================

    # bd01: 项目类型 — 影响整体流程
    m.add_branch_dimension(
        dimension="项目类型",
        entity="E-PTXM",
        values=["能力验证", "测量审核"],
        impact_scope="项目整体流程：能力验证走能力验证提供者流程，测量审核走测量审核提供者流程；初态不同（待开始/报名中）",
        evidence="19.1能力验证提供者流程；19.2测量审核提供者流程；20.5/20.6两章分别描述",
        branches=[
            {"value": "能力验证", "target_transition": "t12",
             "desc": "立项创建，初态为待开始"},
            {"value": "测量审核", "target_transition": "t18",
             "desc": "受理报名创建，初态为报名中"},
        ],
    )

    # bd02: 评分方式 — 影响评价流程
    m.add_branch_dimension(
        dimension="评分方式",
        entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="评价项目录入分值/权重字段；评价结果计算方式不同",
        evidence="20.7.1调整评价功能支持分值和权重两种评价方式",
        branches=[
            {"value": "分值", "target_transition": "t56",
             "desc": "评价人员按分值评分；客户得分需评价组长填写补充"},
            {"value": "权重", "target_transition": "t56",
             "desc": "评价人员按权重评分；客户得分需评价组长填写补充"},
        ],
    )

    # bd03: 是否需要还样 — 影响样品流转
    m.add_branch_dimension(
        dimension="是否需要还样",
        entity="E-YP",
        values=["需还样", "无需还样"],
        impact_scope="样品流转终态不同：需还样经过已发样→已还样，无需还样直接进入无需还样终态",
        evidence="19.1流程表参加者测试与结果提交行：已还样、待核查/无需还样",
        branches=[
            {"value": "需还样", "target_transition": "t40",
             "desc": "已发样→已还样"},
            {"value": "无需还样", "target_transition": "t41",
             "desc": "待核查→无需还样"},
        ],
    )

    # bd04: 审核结果 — 影响审批流终态
    m.add_branch_dimension(
        dimension="审核结果",
        entity="E-SP",
        values=["同意", "退回"],
        impact_scope="批量审核结果决定审批任务终态：已通过/已退回",
        evidence="20.9.1.4批量审核表单：审核结果下拉选择框含同意/退回",
        branches=[
            {"value": "同意", "target_transition": "t74",
             "desc": "状态变更为已通过"},
            {"value": "退回", "target_transition": "t75",
             "desc": "状态变更为已退回"},
        ],
    )

    # ============================================================
    # Step 4.1: 转换
    # ============================================================

    # ---------- E-LAB 转换 ----------
    m.add_trans(
        tid="t01", entity="E-LAB", dimension="实验室状态",
        frm=None, to="待审核",
        action="新增实验室",
        role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室状态初始化为待审核，等待管理用户审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1；20.4.1.1",
        note={"comment": "direction判⓪frm=None创建转换；机构新增实验室"},
    )
    m.add_trans(
        tid="t02", entity="E-LAB", dimension="实验室状态",
        frm=None, to="待审核",
        action="修改实验室",
        role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室状态重新变为待审核，等待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3",
        note={"comment": "direction判⓪frm=None创建转换；机构修改实验室后状态重置为待审核"},
    )
    m.add_trans(
        tid="t03", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="启用",
        action="审核通过",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
        ],
        expected_results=["实验室状态变更为启用；为当前数据生成快照记录"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2",
        note={"comment": "direction判③frm待审核先于to启用；审核通过后启用方可用于项目报名"},
    )
    m.add_trans(
        tid="t04", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="已退回",
        action="审核退回修改",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
            precond(text="审核结果为退回修改时必须填写审核意见", ptype="constraint"),
        ],
        expected_results=["实验室状态变更为已退回；需填写审核意见"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2",
        note={"comment": "direction判③frm待审核先于to已退回；退回修改必须填写审核意见"},
    )
    m.add_trans(
        tid="t05", entity="E-LAB", dimension="实验室状态",
        frm="已退回", to="待审核",
        action="重新提交审核",
        role="能力验证参加者",
        preconditions=[
            precond(text="实验室处于已退回状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "已退回")),
        ],
        expected_results=["实验室状态重新变为待审核"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.4.1.3",
        note={"comment": "direction判④frm已退回后于to待审核；机构修改已退回实验室后重新提交"},
    )
    m.add_trans(
        tid="t06", entity="E-LAB", dimension="实验室状态",
        frm="启用", to="停用",
        action="停用实验室",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变更为停用；列表刷新"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction判③frm启用先于to停用；二次确认后状态立即改变"},
    )
    m.add_trans(
        tid="t07", entity="E-LAB", dimension="实验室状态",
        frm="停用", to="启用",
        action="启用实验室",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变更为启用；列表刷新"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction判④frm停用后于to启用；二次确认后状态立即改变"},
    )

    # ---------- E-STD 转换 ----------
    m.add_trans(
        tid="t08", entity="E-STD", dimension="启用状态",
        frm=None, to="启用",
        action="新增标准库-启用",
        role="系统管理人员",
        preconditions=[],
        expected_results=["标准库状态初始化为启用"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2",
        note={"comment": "direction判⓪frm=None创建转换；状态单选含启用/停用"},
    )
    m.add_trans(
        tid="t09", entity="E-STD", dimension="启用状态",
        frm=None, to="停用",
        action="新增标准库-停用",
        role="系统管理人员",
        preconditions=[],
        expected_results=["标准库状态初始化为停用"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.2.2",
        note={"comment": "direction判⓪frm=None创建转换；状态单选含启用/停用"},
    )
    m.add_trans(
        tid="t10", entity="E-STD", dimension="启用状态",
        frm="启用", to="停用",
        action="停用标准库",
        role="系统管理人员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-STD", "启用状态", "启用")),
        ],
        expected_results=["标准库状态变更为停用；列表刷新；停用后项目创建等环节不可被选择"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction判③frm启用先于to停用"},
    )
    m.add_trans(
        tid="t11", entity="E-STD", dimension="启用状态",
        frm="停用", to="启用",
        action="启用标准库",
        role="系统管理人员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-STD", "启用状态", "停用")),
        ],
        expected_results=["标准库状态变更为启用；列表刷新"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction判④frm停用后于to启用"},
    )

    # ---------- E-PTXM 转换 ----------
    m.add_trans(
        tid="t12", entity="E-PTXM", dimension="项目状态",
        frm=None, to="待开始",
        action="立项创建项目",
        role="项目管理员",
        preconditions=[],
        expected_results=["项目状态初始化为待开始；任务通知书编制"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；20.5.1",
        note={"comment": "direction判⓪frm=None创建转换；能力验证项目立项"},
    )
    m.add_trans(
        tid="t13", entity="E-PTXM", dimension="项目状态",
        frm="待开始", to="报名中",
        action="能力验证计划发布",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-PTXM", "项目状态", "待开始")),
            precond(text="设计方案已编制完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为报名中；预通知状态为未发送；发送能力验证计划通知或邀请函"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm待开始先于to报名中；进入实施阶段报名中"},
    )
    m.add_trans(
        tid="t14", entity="E-PTXM", dimension="项目状态",
        frm="报名中", to="进行中",
        action="进入实施阶段",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-PTXM", "项目状态", "报名中")),
            precond(text="样品核查完成，状态变更为已核查、待发样", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为进行中；样品发放，作业指导书发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm报名中先于to进行中；进入实施阶段含样品发放/作业指导书发送/参加者测试/结果提交"},
    )
    m.add_trans(
        tid="t15", entity="E-PTXM", dimension="项目状态",
        frm="进行中", to="报告审核中",
        action="进入报告编制阶段",
        role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-PTXM", "项目状态", "进行中")),
            precond(text="参加者结果已提交且评价完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为报告审核中；编制结果报告和结果通知单；技术主管审核/授权签字人批准"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm进行中先于to报告审核中；评价完成后进入报告编制和结果通知阶段"},
    )
    m.add_trans(
        tid="t16", entity="E-PTXM", dimension="项目状态",
        frm="报告审核中", to="已结束",
        action="发放结果报告和证书",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-PTXM", "项目状态", "报告审核中")),
            precond(text="结果报告和结果通知单已批准", ptype="event_ref"),
            precond(text="证书已签发", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为已结束；发放结果报告和证书给参加者"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm报告审核中先于to已结束；项目管理员发放结果通知单和证书"},
    )
    m.add_trans(
        tid="t17", entity="E-PTXM", dimension="项目状态",
        frm="已结束", to="已归档",
        action="文件整理归档",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于已结束状态", ptype="state_ref",
                    ref=state_ref("E-PTXM", "项目状态", "已结束")),
        ],
        expected_results=["项目状态变更为已归档；归档任务异步执行；完成后显示查看归档按钮"],
        traits=[], direction="forward", priority="P2",
        source_ref="20.5.1.1",
        note={"comment": "direction判③frm已结束先于to已归档；已结束项目才提供文件整理按钮；推断已归档为终态"},
    )

    # ---------- E-MAXM 转换 ----------
    m.add_trans(
        tid="t18", entity="E-MAXM", dimension="项目状态",
        frm=None, to="报名中",
        action="受理报名创建项目",
        role="项目管理员",
        preconditions=[],
        expected_results=["项目状态初始化为报名中；受理用户测量审核报名"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判⓪frm=None创建转换；测量审核受理报名即创建项目"},
    )
    m.add_trans(
        tid="t19", entity="E-MAXM", dimension="项目状态",
        frm="报名中", to="待开始",
        action="进入方案设计阶段",
        role="策划人员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-MAXM", "项目状态", "报名中")),
            precond(text="报名审核通过，状态变更为报名成功", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为待开始；设计方案编制；作业指导书编制；评价细则编制"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判③frm报名中先于to待开始；测量审核方案设计阶段项目状态为待开始"},
    )
    m.add_trans(
        tid="t20", entity="E-MAXM", dimension="项目状态",
        frm="待开始", to="进行中",
        action="进入实施阶段",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-MAXM", "项目状态", "待开始")),
            precond(text="样品核查完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为进行中；样品发放；参加者测试与结果提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判③frm待开始先于to进行中"},
    )
    m.add_trans(
        tid="t21", entity="E-MAXM", dimension="项目状态",
        frm="进行中", to="报告审核中",
        action="进入报告编制阶段",
        role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-MAXM", "项目状态", "进行中")),
            precond(text="评价完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为报告审核中；编制结果通知单；技术主管审核；授权签字人批准"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判③frm进行中先于to报告审核中"},
    )
    m.add_trans(
        tid="t22", entity="E-MAXM", dimension="项目状态",
        frm="报告审核中", to="已结束",
        action="发放结果通知单和证书",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-MAXM", "项目状态", "报告审核中")),
            precond(text="结果通知单已批准", ptype="event_ref"),
            precond(text="证书已签发", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为已结束；发放结果通知单和证书"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判③frm报告审核中先于to已结束"},
    )
    m.add_trans(
        tid="t23", entity="E-MAXM", dimension="项目状态",
        frm="已结束", to="已归档",
        action="文件整理归档",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于已结束状态", ptype="state_ref",
                    ref=state_ref("E-MAXM", "项目状态", "已结束")),
        ],
        expected_results=["项目状态变更为已归档；归档任务异步执行"],
        traits=[], direction="forward", priority="P2",
        source_ref="20.6.1.1",
        note={"comment": "direction判③frm已结束先于to已归档；测量审核已结束项目文件整理"},
    )

    # ---------- E-BM 转换 ----------
    m.add_trans(
        tid="t24", entity="E-BM", dimension="报名记录状态",
        frm=None, to="报名待审核",
        action="提交报名",
        role="能力验证参加者",
        preconditions=[
            precond(text="实验室信息已审核通过且处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["报名记录状态初始化为报名待审核；预通知状态为未发送；费用状态为待缴费；发票状态为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；19.4",
        note={"comment": "direction判⓪frm=None创建转换；参加者报名；前置条件含跨实体state_ref指向E-LAB启用状态"},
    )
    m.add_trans(
        tid="t25", entity="E-BM", dimension="报名记录状态",
        frm="报名待审核", to="报名退回",
        action="审核退回",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为报名退回；短信通知\"您xxx项目的报名信息审核未通过，请知悉\""],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判③frm报名待审核先于to报名退回；审核退回触发短信"},
    )
    m.add_trans(
        tid="t26", entity="E-BM", dimension="报名记录状态",
        frm="报名待审核", to="报名成功",
        action="审核通过",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为报名成功；缴费通知单状态变更为已发送；费用状态为待缴费；发票状态为待开票；短信通知\"您xxx项目的报名信息审核通过，请知悉\""],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判③frm报名待审核先于to报名成功；审核通过触发缴费通知单生成+短信"},
    )
    m.add_trans(
        tid="t27", entity="E-BM", dimension="报名记录状态",
        frm="报名退回", to="报名待审核",
        action="重新提交报名",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名退回")),
        ],
        expected_results=["报名记录状态重新变为报名待审核"],
        traits=[], direction="backward", priority="P1",
        source_ref="19.1",
        note={"comment": "direction判④frm报名退回后于to报名待审核；参加者修改后重新提交"},
    )
    m.add_trans(
        tid="t28", entity="E-BM", dimension="报名记录状态",
        frm="报名成功", to="结果待提交",
        action="进入结果提交阶段",
        role="system",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名成功")),
            precond(text="预通知已发送且样品已发放", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变更为结果待提交；预通知状态为已发送/待确认；样品状态为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm报名成功先于to结果待提交；进入结果待提交阶段"},
    )
    m.add_trans(
        tid="t29", entity="E-BM", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交",
        action="提交结果报告",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变更为结果已提交；测试结果和报名表盖章版上传"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；19.4",
        note={"comment": "direction判③frm结果待提交先于to结果已提交；参加者提交结果报告"},
    )
    m.add_trans(
        tid="t30", entity="E-BM", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改",
        action="评价退回修改",
        role="评价人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变更为结果退回修改；短信通知\"您xxxx项目测试报告审核未通过，请知悉\""],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判④frm结果已提交后于to结果退回修改；评价退回触发短信"},
    )
    m.add_trans(
        tid="t31", entity="E-BM", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交",
        action="重新提交结果",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果退回修改")),
        ],
        expected_results=["报名记录状态重新变为结果已提交"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1",
        note={"comment": "direction判③frm结果退回修改先于to结果已提交；参加者修改后重新提交"},
    )
    m.add_trans(
        tid="t32", entity="E-BM", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中",
        action="进入报告审核阶段",
        role="评价人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果已提交")),
            precond(text="评价完成且评价组长已确认", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变更为报告/证书审核中；编制结果报告和结果通知单；技术主管审核；授权签字人批准"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm结果已提交先于to报告/证书审核中；评价完成后进入审核阶段"},
    )
    m.add_trans(
        tid="t33", entity="E-BM", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布",
        action="发布结果通知单和证书",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")),
            precond(text="结果报告和结果通知单已批准且证书已签发", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变更为报告/证书已发布；短信通知\"您xxx项目的结果通知单已发布，请知悉\""],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判③frm报告/证书审核中先于to报告/证书已发布；发布触发短信"},
    )
    m.add_trans(
        tid="t34", entity="E-BM", dimension="报名记录状态",
        frm="报告/证书审核中", to="结果退回修改",
        action="审核退回",
        role="技术主管",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["报名记录状态变更为结果退回修改；短信通知\"您xxxx项目测试报告审核未通过，请知悉\""],
        traits=["audit"], direction="backward", priority="P1",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判④frm报告/证书审核中后于to结果退回修改；审核退回触发短信"},
    )
    m.add_trans(
        tid="t35", entity="E-BM", dimension="报名记录状态",
        frm="报名待审核", to="已撤销",
        action="撤销报名",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为已撤销"],
        traits=[], direction="lateral", priority="P2",
        source_ref="19.1",
        note={"comment": "direction判②侧挂至主线外；19.1流程表中报名记录可处于已撤销状态；从报名待审核挂起到已撤销"},
    )

    # ---------- E-YP 转换 ----------
    m.add_trans(
        tid="t36", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查",
        action="样品领用登记",
        role="样品管理员",
        preconditions=[],
        expected_results=["样品状态初始化为待核查；预通知状态为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判⓪frm=None创建转换；样品管理员领用登记"},
    )
    m.add_trans(
        tid="t37", entity="E-YP", dimension="样品状态",
        frm="待核查", to="已核查",
        action="样品核查",
        role="样品制备人员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变更为已核查；生成核查记录表"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm待核查先于to已核查；样品核查含配置/核查/一致性测试"},
    )
    m.add_trans(
        tid="t38", entity="E-YP", dimension="样品状态",
        frm="已核查", to="待发样",
        action="准备发样",
        role="样品管理员",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
        ],
        expected_results=["样品状态变更为待发样"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1",
        note={"comment": "direction判③frm已核查先于to待发样；19.1流程表样品核查后状态为已核查、待发样"},
    )
    m.add_trans(
        tid="t39", entity="E-YP", dimension="样品状态",
        frm="待发样", to="已发样",
        action="样品发放",
        role="样品管理员",
        preconditions=[
            precond(text="样品处于待发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待发样")),
        ],
        expected_results=["样品状态变更为已发样；记录快递单号或软件访问路径；短信通知\"您xxxx项目的样品已发出，请知悉\""],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判③frm待发样先于to已发样；发放触发短信"},
    )
    m.add_trans(
        tid="t40", entity="E-YP", dimension="样品状态",
        frm="已发样", to="已还样",
        action="归还样品",
        role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已发样")),
        ],
        expected_results=["样品状态变更为已还样"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1；19.4",
        note={"branch_dimension": "是否需要还样",
              "comment": "direction判③frm已发样先于to已还样；需还样项目参加者归还样品"},
    )
    m.add_trans(
        tid="t41", entity="E-YP", dimension="样品状态",
        frm="待核查", to="无需还样",
        action="标记无需还样",
        role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
        ],
        expected_results=["若是否需要还样=无需还样，则样品状态变更为无需还样，不经过已发样→已还样"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1",
        note={"branch_dimension": "是否需要还样",
              "comment": "direction判③frm待核查先于to无需还样；分支：需还样项目参加者归还样品，无需还样直接进入终态"},
    )

    # ---------- E-YT 转换 ----------
    m.add_trans(
        tid="t42", entity="E-YT", dimension="通知状态",
        frm=None, to="未发送",
        action="创建预通知",
        role="项目管理员",
        preconditions=[],
        expected_results=["预通知状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换"},
    )
    m.add_trans(
        tid="t43", entity="E-YT", dimension="通知状态",
        frm="未发送", to="已发送",
        action="发送预通知",
        role="项目管理员",
        preconditions=[
            precond(text="预通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "未发送")),
        ],
        expected_results=["预通知状态变更为已发送；包含预通知、用户信息表"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm未发送先于to已发送"},
    )
    m.add_trans(
        tid="t44", entity="E-YT", dimension="通知状态",
        frm="已发送", to="待确认",
        action="等待确认",
        role="system",
        preconditions=[
            precond(text="预通知处于已发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "已发送")),
        ],
        expected_results=["预通知状态变更为待确认；等待参加者确认"],
        traits=["time_sensitive"], direction="forward", priority="P1",
        source_ref="19.1",
        note={"comment": "direction判③frm已发送先于to待确认；参加者接收能力验证计划并确认"},
    )
    m.add_trans(
        tid="t45", entity="E-YT", dimension="通知状态",
        frm="待确认", to="已审核",
        action="审核通过",
        role="技术主管",
        preconditions=[
            precond(text="预通知处于待确认状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "待确认")),
        ],
        expected_results=["预通知状态变更为已审核"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.2",
        note={"comment": "direction判③frm待确认先于to已审核；测量审核流程含待审核/退回/已审核"},
    )
    m.add_trans(
        tid="t46", entity="E-YT", dimension="通知状态",
        frm="待确认", to="退回",
        action="审核退回",
        role="技术主管",
        preconditions=[
            precond(text="预通知处于待确认状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "待确认")),
        ],
        expected_results=["预通知状态变更为退回"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="19.2",
        note={"comment": "direction判③frm待确认先于to退回；测量审核流程含退回"},
    )
    m.add_trans(
        tid="t47", entity="E-YT", dimension="通知状态",
        frm="退回", to="已审核",
        action="重新审核通过",
        role="技术主管",
        preconditions=[
            precond(text="预通知处于退回状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "退回")),
        ],
        expected_results=["预通知状态变更为已审核"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="19.2",
        note={"comment": "direction判③frm退回先于to已审核；重新审核通过"},
    )
    m.add_trans(
        tid="t48", entity="E-YT", dimension="通知状态",
        frm="已审核", to="已批准",
        action="批准预通知",
        role="授权签字人",
        preconditions=[
            precond(text="预通知处于已审核状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "已审核")),
        ],
        expected_results=["预通知状态变更为已批准"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm已审核先于to已批准；授权签字人批准"},
    )

    # ---------- E-FY 转换 ----------
    m.add_trans(
        tid="t49", entity="E-FY", dimension="费用状态",
        frm=None, to="待缴费",
        action="生成费用记录",
        role="system",
        preconditions=[],
        expected_results=["费用状态初始化为待缴费；应收金额默认为项目费用"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换；报名审核通过后自动生成费用记录"},
    )
    m.add_trans(
        tid="t50", entity="E-FY", dimension="费用状态",
        frm="待缴费", to="已缴费",
        action="确认付款",
        role="财务管理人员",
        preconditions=[
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "待缴费")),
            precond(text="参加者已上传付款底单", ptype="event_ref"),
        ],
        expected_results=["费用状态变更为已缴费；已收金额累加付款金额"],
        traits=[], direction="forward", priority="P0",
        source_ref="18.16；20.5.2.1",
        note={"comment": "direction判③frm待缴费先于to已缴费；财务管理人员确认付款信息"},
    )

    # ---------- E-FP 转换 ----------
    m.add_trans(
        tid="t51", entity="E-FP", dimension="发票状态",
        frm=None, to="待开票",
        action="生成发票记录",
        role="system",
        preconditions=[],
        expected_results=["发票状态初始化为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换；报名审核通过后自动生成发票记录"},
    )
    m.add_trans(
        tid="t52", entity="E-FP", dimension="发票状态",
        frm="待开票", to="已开票",
        action="发票开具",
        role="财务管理人员",
        preconditions=[
            precond(text="发票处于待开票状态", ptype="state_ref",
                    ref=state_ref("E-FP", "发票状态", "待开票")),
        ],
        expected_results=["发票状态变更为已开票；支持分批多次上传；记录最后一次开票时间"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；20.10.2.2",
        note={"comment": "direction判③frm待开票先于to已开票；财务管理人员上传电子发票"},
    )

    # ---------- E-JF 转换 ----------
    m.add_trans(
        tid="t53", entity="E-JF", dimension="缴费通知状态",
        frm=None, to="未发送",
        action="生成缴费通知单",
        role="system",
        preconditions=[],
        expected_results=["缴费通知单状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换；报名审核通过后自动生成缴费通知单"},
    )
    m.add_trans(
        tid="t54", entity="E-JF", dimension="缴费通知状态",
        frm="未发送", to="已发送",
        action="发送缴费通知",
        role="项目管理员",
        preconditions=[
            precond(text="缴费通知单处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-JF", "缴费通知状态", "未发送")),
        ],
        expected_results=["缴费通知单状态变更为已发送；参加者接收缴费通知书"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm未发送先于to已发送；项目管理员发送缴费通知"},
    )

    # ---------- E-PJ 转换 ----------
    m.add_trans(
        tid="t55", entity="E-PJ", dimension="评价状态",
        frm=None, to="未评价",
        action="初始化评价任务",
        role="system",
        preconditions=[],
        expected_results=["评价状态初始化为未评价；第一个被选择的评价人员默认作为评价组长"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7",
        note={"comment": "direction判⓪frm=None创建转换；新建项目时选择评价人员触发"},
    )
    m.add_trans(
        tid="t56", entity="E-PJ", dimension="评价状态",
        frm="未评价", to="评价中",
        action="开始评价",
        role="评价人员",
        preconditions=[
            precond(text="评价处于未评价状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "未评价")),
            precond(text="评价组长已完善评价项目及评价细则", ptype="event_ref"),
        ],
        expected_results=["评价状态变更为评价中；评价人员只能修改自己的评价结果"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="20.7.1.2",
        note={"branch_dimension": "评分方式",
              "comment": "direction判③frm未评价先于to评价中；分支：评分方式=分值/权重影响评价录入字段"},
    )
    m.add_trans(
        tid="t57", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价确认中",
        action="提交评价结果",
        role="评价人员",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变更为评价确认中；评价人员提交自己评价结果"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2",
        note={"comment": "direction判③frm评价中先于to评价确认中；评价人员点击确定提交结果"},
    )
    m.add_trans(
        tid="t58", entity="E-PJ", dimension="评价状态",
        frm="评价确认中", to="评价完成",
        action="组长确认评价",
        role="评价人员",
        preconditions=[
            precond(text="评价处于评价确认中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价确认中")),
            precond(text="评价组长已填写客户得分", ptype="event_ref"),
        ],
        expected_results=["评价状态变更为评价完成；项目评价状态关闭；结果正式提交为最终评价结果"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3",
        note={"comment": "direction判③frm评价确认中先于to评价完成；评价组长点击确认；inferred角色：组长属于评价人员"},
    )
    m.add_trans(
        tid="t59", entity="E-PJ", dimension="评价状态",
        frm="评价确认中", to="评价中",
        action="退回修改",
        role="评价人员",
        preconditions=[
            precond(text="评价处于评价确认中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价确认中")),
        ],
        expected_results=["评价状态变更为评价中；当前评价结果保存为历史结果；开启下一轮评价"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.7.1.3",
        note={"comment": "direction判④frm评价确认中后于to评价中；组长退回修改开启下一轮评价；inferred角色：组长属于评价人员"},
    )

    # ---------- E-ZS 转换 ----------
    m.add_trans(
        tid="t60", entity="E-ZS", dimension="证书状态",
        frm=None, to="未签发",
        action="创建证书记录",
        role="system",
        preconditions=[],
        expected_results=["证书状态初始化为未签发"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换；项目管理员编制证书项目时自动生成"},
    )
    m.add_trans(
        tid="t61", entity="E-ZS", dimension="证书状态",
        frm="未签发", to="已签发",
        action="签发证书",
        role="实验室负责人",
        preconditions=[
            precond(text="证书处于未签发状态", ptype="state_ref",
                    ref=state_ref("E-ZS", "证书状态", "未签发")),
            precond(text="技术主管已审核证书", ptype="event_ref"),
        ],
        expected_results=["证书状态变更为已签发；记录签发时间；计算到期时间"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="18.6；19.1",
        note={"comment": "direction判③frm未签发先于to已签发；实验室负责人批准签发合格证书"},
    )
    m.add_trans(
        tid="t62", entity="E-ZS", dimension="证书状态",
        frm="已签发", to="已到期",
        action="证书到期",
        role="system",
        preconditions=[
            precond(text="证书处于已签发状态", ptype="state_ref",
                    ref=state_ref("E-ZS", "证书状态", "已签发")),
            precond(text="距证书到期时间等于30天时邮件提醒", ptype="constraint"),
        ],
        expected_results=["若距到期等于30天，则邮件提醒用户并抄送项目管理员；到达到期日证书状态变更为已到期"],
        traits=["time_sensitive"], direction="forward", priority="P2",
        source_ref="20.5.2.3；20.6.2.3",
        note={"comment": "direction判③frm已签发先于to已到期；系统每天上午9点查询证书信息；inferred终态"},
    )

    # ---------- E-JG 转换 ----------
    m.add_trans(
        tid="t63", entity="E-JG", dimension="通知单状态",
        frm=None, to="待审核",
        action="编制结果通知单",
        role="策划人员",
        preconditions=[],
        expected_results=["通知单状态初始化为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换；策划人员编制结果通知单"},
    )
    m.add_trans(
        tid="t64", entity="E-JG", dimension="通知单状态",
        frm="待审核", to="已批准",
        action="批准结果通知单",
        role="授权签字人",
        preconditions=[
            precond(text="通知单处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-JG", "通知单状态", "待审核")),
            precond(text="技术主管已审核报告", ptype="event_ref"),
        ],
        expected_results=["通知单状态变更为已批准"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm待审核先于to已批准；技术主管审核后授权签字人批准"},
    )
    m.add_trans(
        tid="t65", entity="E-JG", dimension="通知单状态",
        frm="待审核", to="退回",
        action="审核退回",
        role="技术主管",
        preconditions=[
            precond(text="通知单处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-JG", "通知单状态", "待审核")),
        ],
        expected_results=["通知单状态变更为退回"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="19.1",
        note={"comment": "direction判③frm待审核先于to退回；技术主管审核退回"},
    )
    m.add_trans(
        tid="t66", entity="E-JG", dimension="通知单状态",
        frm="退回", to="待审核",
        action="重新提交",
        role="策划人员",
        preconditions=[
            precond(text="通知单处于退回状态", ptype="state_ref",
                    ref=state_ref("E-JG", "通知单状态", "退回")),
        ],
        expected_results=["通知单状态重新变为待审核"],
        traits=[], direction="backward", priority="P1",
        source_ref="19.1",
        note={"comment": "direction判④frm退回后于to待审核；策划人员修改后重新提交"},
    )
    m.add_trans(
        tid="t67", entity="E-JG", dimension="通知单状态",
        frm="已批准", to="已发布",
        action="发放结果通知单",
        role="项目管理员",
        preconditions=[
            precond(text="通知单处于已批准状态", ptype="state_ref",
                    ref=state_ref("E-JG", "通知单状态", "已批准")),
        ],
        expected_results=["通知单状态变更为已发布；短信通知\"您xxx项目的结果通知单已发布，请知悉\""],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1；20.5.3.2",
        note={"comment": "direction判③frm已批准先于to已发布；项目管理员发放；发布触发短信"},
    )

    # ---------- E-BG 转换 ----------
    m.add_trans(
        tid="t68", entity="E-BG", dimension="报告状态",
        frm=None, to="待审核",
        action="编制结果报告",
        role="策划人员",
        preconditions=[],
        expected_results=["报告状态初始化为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判⓪frm=None创建转换；策划人员编制结果报告"},
    )
    m.add_trans(
        tid="t69", entity="E-BG", dimension="报告状态",
        frm="待审核", to="已批准",
        action="审核批准报告",
        role="授权签字人",
        preconditions=[
            precond(text="报告处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-BG", "报告状态", "待审核")),
            precond(text="技术主管已审核报告", ptype="event_ref"),
        ],
        expected_results=["报告状态变更为已批准"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm待审核先于to已批准；技术主管审核后授权签字人批准"},
    )
    m.add_trans(
        tid="t70", entity="E-BG", dimension="报告状态",
        frm="已批准", to="已发布",
        action="发放结果报告",
        role="项目管理员",
        preconditions=[
            precond(text="报告处于已批准状态", ptype="state_ref",
                    ref=state_ref("E-BG", "报告状态", "已批准")),
        ],
        expected_results=["报告状态变更为已发布；参加者接收能力验证计划结果报告"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1",
        note={"comment": "direction判③frm已批准先于to已发布；项目管理员发放"},
    )

    # ---------- E-WJZL 转换 ----------
    m.add_trans(
        tid="t71", entity="E-WJZL", dimension="整理状态",
        frm=None, to="整理中",
        action="开启整理任务",
        role="项目管理员",
        preconditions=[
            precond(text="关联项目处于已结束状态", ptype="state_ref",
                    ref=state_ref("E-PTXM", "项目状态", "已结束")),
        ],
        expected_results=["整理状态初始化为整理中；提示\"归档任务已开启，请稍后查看\""],
        traits=[], direction="forward", priority="P2",
        source_ref="20.5.1.1",
        note={"comment": "direction判⓪frm=None创建转换；前置条件含跨实体state_ref指向E-PTXM已结束；仅已结束项目显示文件整理按钮"},
    )
    m.add_trans(
        tid="t72", entity="E-WJZL", dimension="整理状态",
        frm="整理中", to="已归档",
        action="整理完成",
        role="system",
        preconditions=[
            precond(text="整理任务处于整理中状态", ptype="state_ref",
                    ref=state_ref("E-WJZL", "整理状态", "整理中")),
        ],
        expected_results=["整理状态变更为已归档；操作列显示查看归档按钮；用户可查看并补充归档信息"],
        traits=[], direction="forward", priority="P2",
        source_ref="20.5.1.1",
        note={"comment": "direction判③frm整理中先于to已归档；系统异步完成整理"},
    )

    # ---------- E-SP 转换 ----------
    m.add_trans(
        tid="t73", entity="E-SP", dimension="审批状态",
        frm=None, to="待审核",
        action="创建审核任务",
        role="system",
        preconditions=[],
        expected_results=["审批状态初始化为待审核；短信通知相关负责人\"您有一个新的xxx审核任务，请及时处理\""],
        traits=[], direction="forward", priority="P0",
        source_ref="20.9.1.3",
        note={"comment": "direction判⓪frm=None创建转换；用户通过表单或审核已存在任务生成新审核任务"},
    )
    m.add_trans(
        tid="t74", entity="E-SP", dimension="审批状态",
        frm="待审核", to="已通过",
        action="审核通过",
        role="项目管理员",
        preconditions=[
            precond(text="审批任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SP", "审批状态", "待审核")),
        ],
        expected_results=["若审核结果=同意，则审批状态变更为已通过"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.9.1.4",
        note={"branch_dimension": "审核结果",
              "comment": "direction判③frm待审核先于to已通过；分支：审核结果=同意/退回决定终态"},
    )
    m.add_trans(
        tid="t75", entity="E-SP", dimension="审批状态",
        frm="待审核", to="已退回",
        action="审核退回",
        role="项目管理员",
        preconditions=[
            precond(text="审批任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SP", "审批状态", "待审核")),
        ],
        expected_results=["若审核结果=退回，则审批状态变更为已退回"],
        traits=["branch", "audit"], direction="forward", priority="P1",
        source_ref="20.9.1.4",
        note={"branch_dimension": "审核结果",
              "comment": "direction判③frm待审核先于to已退回；分支：审核结果=同意/退回决定终态"},
    )

    # ============================================================
    # Step 4.3: 自检
    # ============================================================
    # 扫描 Step 3 target_transition 局部 tid 均有对应 add_trans：
    #   bd01: t12, t18 ✓；bd02: t56 ✓；bd03: t40, t41 ✓；bd04: t74, t75 ✓
    # crud 操作 comment 已回填对应转换标签或注明无对应转换：
    #   E-LAB 新增→t01；修改→t02；审核→t03/t04；停用→t06；启用→t07 ✓
    #   E-STD 新增→t08/t09；停用→t10；启用→t11；修改/删除→无对应转换 ✓
    #   E-TEST 新增/修改/删除→无对应转换 ✓
    #   E-CTEST 同上 ✓
    #   E-MSG 全部查询/详情→无对应转换 ✓
    #   E-PTXM 新增→t12；文件整理→t17；其余→无对应转换 ✓
    #   E-MAXM 新增→t18；文件整理→t23 ✓
    #   E-BM 报名→t24；审核→t25/t26；提交结果→t29；撤销→t35；其余→无对应转换 ✓
    #   E-YP 领用→t36；核查→t37；发放→t39；归还→t40 ✓
    #   E-YT 发送→t43；审核→t45/t46 ✓
    #   E-FY 确认付款→t50 ✓
    #   E-FP 上传→t52 ✓
    #   E-JF 发送→t54 ✓
    #   E-PJ 开始评价→t56；提交→t57；确认→t58；退回→t59 ✓
    #   E-ZS 签发→t61 ✓
    #   E-JG 编制→t63；批准→t64；退回→t65；重新提交→t66；发放→t67 ✓
    #   E-BG 编制→t68；批准→t69；发放→t70 ✓
    #   E-WJZL 开启→t71；查看归档→t72 ✓
    #   E-SP 创建→t73；通过→t74；退回→t75 ✓

    # ============================================================
    # Step 4.4 & 4.5: 因果与鉴别
    # ============================================================

    # 因果1: 项目待开始→报名中 直接联动预通知创建（项目发布触发预通知生成）
    # 鉴别 Q1: 项目发布是预通知生成的直接原因 ✓
    # 鉴别 Q2: 预通知创建无独立precondition表达 ✓
    # 鉴别 Q3: 上级(项目)作下级(预通知)门禁? 不是，是项目状态变化直接触发预通知创建 → 因果
    m.add_causal(
        frm="E-PTXM", to="E-YT",
        desc="项目状态由待开始变为报名中时触发预通知创建，预通知状态初始化为未发送",
        trigger="能力验证计划发布后自动创建预通知",
        trigger_source="expected_results",
        evidence_transitions=["t13", "t42"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1项目发布直接致预通知创建；Q2预通知创建无独立precondition；Q3上级直接触发下级"},
    )

    # 因果2: 报名审核通过→缴费通知单生成
    m.add_causal(
        frm="E-BM", to="E-JF",
        desc="报名记录审核通过状态变更为报名成功时自动生成缴费通知单，状态为未发送",
        trigger="报名审核通过后自动生成缴费通知单",
        trigger_source="expected_results",
        evidence_transitions=["t26", "t53"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1报名成功直接致缴费通知单生成；Q2缴费通知单生成无独立precondition；Q3上级直接触发下级"},
    )

    # 因果3: 报名审核通过→费用记录生成
    m.add_causal(
        frm="E-BM", to="E-FY",
        desc="报名记录审核通过状态变更为报名成功时自动生成费用记录，状态为待缴费",
        trigger="报名审核通过后自动生成费用记录",
        trigger_source="expected_results",
        evidence_transitions=["t26", "t49"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1报名成功直接致费用记录生成；Q2费用记录生成无独立precondition；Q3上级直接触发下级"},
    )

    # 因果4: 报名审核通过→发票记录生成
    m.add_causal(
        frm="E-BM", to="E-FP",
        desc="报名记录审核通过状态变更为报名成功时自动生成发票记录，状态为待开票",
        trigger="报名审核通过后自动生成发票记录",
        trigger_source="expected_results",
        evidence_transitions=["t26", "t51"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1报名成功直接致发票记录生成；Q2发票记录生成无独立precondition；Q3上级直接触发下级"},
    )

    # 因果5: 评价完成→报名记录进入报告/证书审核中
    m.add_causal(
        frm="E-PJ", to="E-BM",
        desc="评价状态变更为评价完成时报名记录状态由结果已提交变更为报告/证书审核中",
        trigger="评价组长确认评价完成后报名记录进入报告审核阶段",
        trigger_source="expected_results",
        evidence_transitions=["t58", "t32"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1评价完成直接致报名记录状态变化；Q2已在t32 precondition表达为event_ref；Q3下级完成触发上级推进"},
    )

    # 因果6: 结果通知单发布→报名记录报告/证书已发布
    m.add_causal(
        frm="E-JG", to="E-BM",
        desc="结果通知单状态变更为已发布时报名记录状态由报告/证书审核中变更为报告/证书已发布",
        trigger="结果通知单发布后报名记录状态变更为报告/证书已发布",
        trigger_source="expected_results",
        evidence_transitions=["t67", "t33"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通知单发布直接致报名记录状态变化；Q2已在t33 precondition表达为event_ref"},
    )

    # 因果7: 证书签发→项目已结束
    # 鉴别 Q2: t16 precondition已表达证书已签发event_ref → 门禁不写入因果
    # 但证书签发直接推动项目状态推进 → 仍是因果
    m.add_causal(
        frm="E-ZS", to="E-PTXM",
        desc="证书状态变更为已签发时项目状态由报告审核中变更为已结束",
        trigger="证书签发后项目状态变更为已结束",
        trigger_source="expected_results",
        evidence_transitions=["t61", "t16"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1证书签发直接致项目状态变化；Q2已在t16 precondition表达为event_ref；Q3下级完成触发上级推进"},
    )

    # 因果8: 文件整理→项目已归档
    m.add_causal(
        frm="E-WJZL", to="E-PTXM",
        desc="文件整理任务状态变更为已归档时项目状态由已结束变更为已归档",
        trigger="文件整理完成后项目状态变更为已归档",
        trigger_source="expected_results",
        evidence_transitions=["t72", "t17"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "Q1文件整理完成直接致项目状态变化；推导因果关系，medium confidence；Q2 t17未含event_ref指向E-WJZL"},
    )

    # 因果9: 测量审核文件整理→测量审核项目已归档
    m.add_causal(
        frm="E-WJZL", to="E-MAXM",
        desc="文件整理任务状态变更为已归档时测量审核项目状态由已结束变更为已归档",
        trigger="文件整理完成后测量审核项目状态变更为已归档",
        trigger_source="expected_results",
        evidence_transitions=["t72", "t23"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "Q1文件整理完成直接致项目状态变化；推导因果关系，medium confidence"},
    )

    # 因果10: 评价退回→报名记录结果退回修改
    m.add_causal(
        frm="E-PJ", to="E-BM",
        desc="评价组长退回修改评价结果时报名记录状态由结果已提交变更为结果退回修改",
        trigger="评价退回修改时报名记录状态变更为结果退回修改",
        trigger_source="expected_results",
        evidence_transitions=["t59", "t30"],
        rollback_propagation=True, confidence="high",
        note={"comment": "Q1评价退回直接致报名记录状态变化；Q2已在t30 precondition表达；rollback_propagation=True因含退回语义"},
    )

    # ============================================================
    # Step 5: 约束补充
    # ============================================================

    # ---------- Invalid transitions ----------
    m.add_invalid(
        iid="it01", entity="E-BM",
        frm="报告/证书已发布", to="报告/证书审核中",
        reason="已发布状态不允许退回至审核中",
        source_ref="19.1；20.5.3.2",
    )
    m.add_invalid(
        iid="it02", entity="E-PTXM",
        frm="已归档", to="已结束",
        reason="已归档为终态，不允许回退",
        source_ref="20.5.1.1",
    )
    m.add_invalid(
        iid="it03", entity="E-PTXM",
        frm="已归档", to="报名中",
        reason="已归档为终态，不允许重新进入流程",
        source_ref="20.5.1.1",
    )
    m.add_invalid(
        iid="it04", entity="E-BM",
        frm="已撤销", to="报名待审核",
        reason="已撤销为终态，不允许重新进入审核",
        source_ref="19.1",
    )
    m.add_invalid(
        iid="it05", entity="E-BM",
        frm="已撤销", to="报名成功",
        reason="已撤销为终态，不允许进入后续流程",
        source_ref="19.1",
    )
    m.add_invalid(
        iid="it06", entity="E-LAB",
        frm="停用", to="待审核",
        reason="停用状态只能直接启用，不能跳转至待审核",
        source_ref="20.4.1.1",
    )

    # ---------- Cross-entity (XC) ----------
    # x01: 镜像 - t24持有指向E-LAB启用状态的跨实体前置条件
    m.add_xc(
        xid="x01",
        source_entity="E-LAB", source_transition="t03", source_state="启用",
        target_entity="E-BM", target_dimension="报名记录状态",
        target_transition="t24",
        target_condition="报名待审核",
        xc_source="镜像",
        desc="precondition'实验室信息已审核通过且处于启用状态'",
        source_ref="19.1；20.3.1",
    )

    # x02: 联动 - 报名审核通过(t26)联动缴费通知单生成(t53)
    m.add_xc(
        xid="x02",
        source_entity="E-BM", source_transition="t26", source_state="报名成功",
        target_entity="E-JF", target_dimension="缴费通知状态",
        target_transition="t53",
        target_condition="未发送",
        xc_source="联动",
        desc="报名审核通过后自动生成缴费通知单",
        source_ref="19.1",
    )

    # x03: 联动 - 报名审核通过(t26)联动费用记录生成(t49)
    m.add_xc(
        xid="x03",
        source_entity="E-BM", source_transition="t26", source_state="报名成功",
        target_entity="E-FY", target_dimension="费用状态",
        target_transition="t49",
        target_condition="待缴费",
        xc_source="联动",
        desc="报名审核通过后自动生成费用记录",
        source_ref="19.1",
    )

    # x04: 联动 - 报名审核通过(t26)联动发票记录生成(t51)
    m.add_xc(
        xid="x04",
        source_entity="E-BM", source_transition="t26", source_state="报名成功",
        target_entity="E-FP", target_dimension="发票状态",
        target_transition="t51",
        target_condition="待开票",
        xc_source="联动",
        desc="报名审核通过后自动生成发票记录",
        source_ref="19.1",
    )

    # x05: 联动 - 评价完成(t58)联动报名记录状态(t32)
    m.add_xc(
        xid="x05",
        source_entity="E-PJ", source_transition="t58", source_state="评价完成",
        target_entity="E-BM", target_dimension="报名记录状态",
        target_transition="t32",
        target_condition="报告/证书审核中",
        xc_source="联动",
        desc="评价完成后报名记录进入报告/证书审核中",
        source_ref="19.1",
    )

    # x06: 联动 - 结果通知单发布(t67)联动报名记录状态(t33)
    m.add_xc(
        xid="x06",
        source_entity="E-JG", source_transition="t67", source_state="已发布",
        target_entity="E-BM", target_dimension="报名记录状态",
        target_transition="t33",
        target_condition="报告/证书已发布",
        xc_source="联动",
        desc="结果通知单发布后报名记录状态变更为报告/证书已发布",
        source_ref="19.1；20.5.3.2",
    )

    # x07: 联动 - 证书签发(t61)联动项目状态(t16)
    m.add_xc(
        xid="x07",
        source_entity="E-ZS", source_transition="t61", source_state="已签发",
        target_entity="E-PTXM", target_dimension="项目状态",
        target_transition="t16",
        target_condition="已结束",
        xc_source="联动",
        desc="证书签发后能力验证项目状态变更为已结束",
        source_ref="19.1",
    )

    # x08: 联动 - 文件整理完成(t72)联动项目状态(t17)
    m.add_xc(
        xid="x08",
        source_entity="E-WJZL", source_transition="t72", source_state="已归档",
        target_entity="E-PTXM", target_dimension="项目状态",
        target_transition="t17",
        target_condition="已归档",
        xc_source="联动",
        desc="文件整理完成后能力验证项目状态变更为已归档",
        source_ref="20.5.1.1",
    )

    # x09: 联动 - 文件整理完成(t72)联动测量审核项目状态(t23)
    m.add_xc(
        xid="x09",
        source_entity="E-WJZL", source_transition="t72", source_state="已归档",
        target_entity="E-MAXM", target_dimension="项目状态",
        target_transition="t23",
        target_condition="已归档",
        xc_source="联动",
        desc="文件整理完成后测量审核项目状态变更为已归档",
        source_ref="20.6.1.1",
    )

    # x10: 联动 - 评价退回(t59)联动报名记录状态(t30)
    m.add_xc(
        xid="x10",
        source_entity="E-PJ", source_transition="t59", source_state="评价中",
        target_entity="E-BM", target_dimension="报名记录状态",
        target_transition="t30",
        target_condition="结果退回修改",
        xc_source="联动",
        desc="评价退回修改时报名记录状态变更为结果退回修改",
        source_ref="19.1；20.7.1.3",
    )

    # x11: 镜像 - t71持有指向E-PTXM已结束状态的跨实体前置条件
    m.add_xc(
        xid="x11",
        source_entity="E-PTXM", source_transition="t16", source_state="已结束",
        target_entity="E-WJZL", target_dimension="整理状态",
        target_transition="t71",
        target_condition="整理中",
        xc_source="镜像",
        desc="precondition'关联项目处于已结束状态'",
        source_ref="20.5.1.1",
    )

    # x12: 镜像 - t41/t40持有指向是否需要还样分支的跨实体约束
    m.add_xc(
        xid="x12",
        source_entity="E-YP", source_transition="t39", source_state="已发样",
        target_entity="E-YP", target_dimension="样品状态",
        target_transition="t40",
        target_condition="已还样",
        xc_source="分支差异",
        desc="需还样项目样品状态由已发样变更为已还样；无需还样项目不经过此转换",
        source_ref="19.1",
    )

    # ---------- Business Rules (BR) ----------
    # b01: 实验室新增/修改后须经管理用户审核通过后方可用于项目报名
    m.add_br(
        bid="b01", category="validation",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-LAB", "E-BM"],
        constrained_entity="E-LAB",
        source_ref="20.3.1", signal_type="restrictive",
        note={"comment": "代表实体E-LAB；约束实验室须经审核通过方可被报名引用"},
    )

    # b02: 15天内发布的通知标注"new"标识
    m.add_br(
        bid="b02", category="timing",
        desc="15天内发布的通知在内容前标注\"new\"标识；超过15天后此标识自动隐藏",
        entities_involved=["E-MSG"],
        source_ref="20.2.1", signal_type="field_constraint",
    )

    # b03: 含有子项的测试项不允许删除
    m.add_br(
        bid="b03", category="validation",
        desc="含有子项的测试项记录不允许删除",
        entities_involved=["E-TEST", "E-CTEST"],
        constrained_entity="E-TEST",
        source_ref="20.4.2.10；20.4.3.4", signal_type="restrictive",
        note={"comment": "代表实体E-TEST；删除前会做前置判断，存在子项的数据不可以删除"},
    )

    # b04: 状态为待审核的实验室才显示审核按钮
    m.add_br(
        bid="b04", category="display",
        desc="状态为\"待审核\"的实验室记录才显示【审核】按钮",
        entities_involved=["E-LAB"],
        source_ref="20.4.1.2", signal_type="display",
    )

    # b05: 已结束的项目才提供文件整理按钮
    m.add_br(
        bid="b05", category="validation",
        desc="项目状态为\"已结束\"的项目记录才提供【文件整理】按钮",
        entities_involved=["E-PTXM", "E-MAXM", "E-WJZL"],
        constrained_entity="E-WJZL",
        source_ref="20.5.1.1；20.6.1.1", signal_type="restrictive",
        note={"comment": "代表实体E-WJZL；操作对象是文件整理任务"},
    )

    # b06: 证书到期前30天邮件提醒
    m.add_br(
        bid="b06", category="notification",
        desc="证书到期前30天通过邮件方式提醒用户证书即将到期，并抄送项目管理员",
        entities_involved=["E-ZS"],
        source_ref="20.5.2.3；20.6.2.3", signal_type="restrictive",
    )

    # b07: 接收人1和接收人2不能同时为空
    m.add_br(
        bid="b07", category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-PTXM", "E-MAXM"],
        constrained_entity="E-PTXM",
        source_ref="20.5.1.4；20.6.1.2", signal_type="restrictive",
        note={"comment": "代表实体E-PTXM；消息发送校验"},
    )

    # b08: 系统每天上午9点对证书信息进行查询
    m.add_br(
        bid="b08", category="timing",
        desc="系统在每天上午9点对系统中的证书信息进行查询",
        entities_involved=["E-ZS"],
        source_ref="20.5.2.3；20.6.2.3", signal_type="field_constraint",
    )

    # b09: 退款金额不能大于当前缴费金额
    m.add_br(
        bid="b09", category="validation",
        desc="退款金额不能大于当前缴费金额",
        entities_involved=["E-TK", "E-FY"],
        constrained_entity="E-TK",
        source_ref="20.10.2.3", signal_type="field_constraint",
        note={"comment": "代表实体E-TK；退款操作的对象是退款记录"},
    )

    # b10: 退款金额大于0时显示红色字体
    m.add_br(
        bid="b10", category="display",
        desc="退款金额使用红色字体且大于0时显示",
        entities_involved=["E-TK"],
        source_ref="20.10.2.3", signal_type="display",
    )

    # b11: 系统根据任务节点类型及内容判断是否可被批量处理
    m.add_br(
        bid="b11", category="validation",
        desc="系统根据任务节点的类型及内容判断当前节点是否可以被批量处理",
        entities_involved=["E-SP"],
        source_ref="20.9.1.4", signal_type="restrictive",
    )

    # b12: 评价人员只能修改自己的评价结果
    m.add_br(
        bid="b12", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"],
        source_ref="20.7.1.2", signal_type="restrictive",
    )

    # b13: 已上传对应文件且未提交审核的记录才可以被选定
    m.add_br(
        bid="b13", category="validation",
        desc="只有已上传对应文件且未提交审核的记录才可以被选定进行批量提交审核",
        entities_involved=["E-PTXM", "E-BM"],
        constrained_entity="E-BM",
        source_ref="20.5.1.3", signal_type="restrictive",
        note={"comment": "代表实体E-BM；批量处理提交审核校验"},
    )

    # b14: 关键操作进行留痕处理
    m.add_br(
        bid="b14", category="usability",
        desc="对关键操作进行留痕处理，系统自动记录操作者身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-SP"],
        source_ref="20.11", signal_type="usability",
    )

    # b15: 付款金额-退款金额=实际付款
    m.add_br(
        bid="b15", category="computation",
        desc="实际付款=付款金额-退款金额；多次退款金额做累加处理",
        entities_involved=["E-FK", "E-TK", "E-FY"],
        constrained_entity="E-FY",
        source_ref="20.10.2.3", signal_type="field_constraint",
        note={"comment": "代表实体E-FY；费用计算规则"},
    )

    # b16: 只有系统管理员和项目管理员可以查看信息发送记录
    m.add_br(
        bid="b16", category="authorization",
        desc="只有系统管理员和项目管理员可以查看信息发送记录",
        entities_involved=["E-MSG"],
        source_ref="20.4.4.1", signal_type="restrictive",
    )

    # b17: 历史数据可导入到系统中
    m.add_br(
        bid="b17", category="usability",
        desc="对往年项目数据进行分析整理并导入到系统中为数据分析提供关键数据",
        entities_involved=["E-PTXM"],
        source_ref="20.11", signal_type="usability",
    )

    # b18: 默认填充技术主管/实验室负责人/授权签字人
    m.add_br(
        bid="b18", category="usability",
        desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-PTXM", "E-MAXM"],
        constrained_entity="E-PTXM",
        source_ref="20.5.1.6；20.6.1.4", signal_type="usability",
        note={"comment": "代表实体E-PTXM；项目新增表单默认填充规则"},
    )

    # b19: 短信通知负责人新审核任务
    m.add_br(
        bid="b19", category="notification",
        desc="用户通过表单或审核已存在任务生成新审核任务时系统发送短信通知相关负责人，内容为\"您有一个新的xxx审核任务，请及时处理\"",
        entities_involved=["E-SP"],
        source_ref="20.9.1.3", signal_type="restrictive",
    )

    # b20: 操作节点短信通知用户
    m.add_br(
        bid="b20", category="notification",
        desc="管理人员对用户报名项目操作后对于需要告知用户的节点增加短信提醒功能，包含报名审核通过/退回、发样通知、测试结果审核通过/退回、结果通知单发布等节点",
        entities_involved=["E-BM", "E-YP", "E-JG"],
        constrained_entity="E-BM",
        source_ref="20.5.3.2；20.6.3.2", signal_type="restrictive",
        note={"comment": "代表实体E-BM；多个操作节点触发短信"},
    )

    return m
