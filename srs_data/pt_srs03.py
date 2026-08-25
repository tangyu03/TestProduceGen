"""网数中心能力验证服务平台升级维护项目-需求分析与设计1116 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref

# ===== 事件台账 =====
# 结构化注册在 build() 顶部 m.add_event(...)（单一真相源；note 引用事件 id 在此登记）。
# 此处保留两类无注册的说明：
# - e19 已删除：编制缴纳测量审核费用通知为文档创建动作，缴费通知单状态无变化
#   （19.2流程表该行缴费通知单列空缺），按落点判定②非事件
# - 系统行为（无状态落点，落点判定③出口）：证书到期提醒（20.5.2.3 / 20.6.2.3）、
#   操作节点短信通知（20.5.3.2 / 20.6.3.2）、任务创建短信通知（20.9.1.3）→ BR


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116",
        document_scope="能力验证/测量审核全流程"
    )

    # ===== 事件台账（glm5pr §2；转换/关系 note 引用的事件 id 在此登记）=====
    # ── 19.1 能力验证提供者流程 ──
    m.add_event("e01", "E-XM", "项目状态", "设计方案编制", "策划人员",
                "无", "待开始", "19.1方案设计阶段")
    m.add_event("e02", "E-XM", "项目状态", "能力验证计划发布", "项目管理员",
                "待开始", "报名中", "19.1实施阶段")
    m.add_event("e03", "E-BM", "报名记录状态", "报名", "能力验证参加者",
                "无", "报名待审核", "19.1实施阶段")
    m.add_event("e03b", "E-BM", "通知状态", "报名", "能力验证参加者",
                "无", "未发送", "19.1实施阶段")
    m.add_event("e03c", "E-BM", "费用状态", "报名", "能力验证参加者",
                "无", "待缴费", "19.1实施阶段")
    m.add_event("e03d", "E-BM", "发票状态", "报名", "能力验证参加者",
                "无", "待开票", "19.1实施阶段")
    m.add_event("e03e", "E-BM", "缴费通知单状态", "报名", "能力验证参加者",
                "无", "未发送", "19.1实施阶段")
    m.add_event("e04", "E-BM", "报名记录状态", "报名审核通过", "项目管理员",
                "报名待审核", "报名成功", "19.1实施阶段")
    m.add_event("e04b", "E-BM", "缴费通知单状态", "报名审核通过", "项目管理员",
                "未发送", "已发送", "19.1实施阶段")
    m.add_event("e05", "E-BM", "报名记录状态", "报名审核退回", "项目管理员",
                "报名待审核", "报名退回", "19.1实施阶段")
    m.add_event("e06", "E-BM", "报名记录状态", "报名撤销", "能力验证参加者",
                "报名待审核", "已撤销", "19.1实施阶段")
    m.add_event("e07", "E-BM", "费用状态", "缴费", "能力验证参加者",
                "待缴费", "已缴费", "19.1实施阶段")
    m.add_event("e07b", "E-XM", "样品状态", "缴费", "能力验证参加者",
                "无", "待核查", "19.1实施阶段")
    # e07c 创建事件 inferred：20.10.2.3 缴费记录实体存在但创建流程缺失
    m.add_event("e07c", "E-JK", "缴费状态", "缴费", "能力验证参加者",
                "无", "已缴费", "19.1实施阶段；20.5.2.1多次付款")
    m.add_event("e08", "E-BM", "发票状态", "发票开具", "财务人员",
                "待开票", "已开票", "19.1实施阶段")
    m.add_event("e09", "E-BM", "通知状态", "能力验证预通知", "项目管理员",
                "未发送", "已发送", "19.1实施阶段")
    m.add_event("e09b", "E-BM", "报名记录状态", "能力验证预通知", "项目管理员",
                "报名成功", "结果待提交", "19.1实施阶段")
    m.add_event("e09c", "E-XM", "项目状态", "能力验证预通知", "项目管理员",
                "报名中", "进行中", "19.1实施阶段")
    m.add_event("e10", "E-XM", "样品状态", "样品核查", "样品管理员",
                "待核查", "已核查", "19.1实施阶段")
    m.add_event("e10b", "E-BM", "报名记录样品状态", "样品核查", "样品管理员",
                "无", "待发样", "19.1实施阶段")
    m.add_event("e11", "E-XM", "样品状态", "样品发放", "项目管理员",
                "已核查", "已发样", "19.1实施阶段")
    m.add_event("e11b", "E-BM", "通知状态", "样品发放", "项目管理员",
                "已发送", "已确认", "19.1实施阶段")
    m.add_event("e11c", "E-BM", "报名记录样品状态", "样品发放", "项目管理员",
                "待发样", "已收样", "19.1实施阶段")
    m.add_event("e12", "E-XM", "样品状态", "参加者测试与结果提交", "能力验证参加者",
                "已发样", "已还样", "19.1实施阶段")
    m.add_event("e12b", "E-BM", "报名记录状态", "参加者测试与结果提交", "能力验证参加者",
                "结果待提交", "结果已提交", "19.1实施阶段")
    m.add_event("e13", "E-BM", "报名记录状态", "结果报告退回", "项目管理员",
                "结果已提交", "结果退回修改", "19.1报告编制和结果通知")
    m.add_event("e13b", "E-BM", "报名记录状态", "结果重新提交", "能力验证参加者",
                "结果退回修改", "结果已提交", "19.1报告编制和结果通知")
    m.add_event("e14", "E-BM", "报名记录状态", "编制结果报告", "策划人员",
                "结果已提交", "报告/证书审核中", "19.1报告编制和结果通知")
    m.add_event("e14b", "E-XM", "项目状态", "编制结果报告", "策划人员",
                "进行中", "报告审核中", "19.1报告编制和结果通知")
    m.add_event("e15", "E-BM", "报名记录状态", "报告审核", "技术主管",
                "报告/证书审核中", "报告/证书审核中", "19.1报告编制和结果通知")
    m.add_event("e16", "E-BM", "报名记录状态", "报告批准", "授权签字人",
                "报告/证书审核中", "报告/证书审核中", "19.1报告编制和结果通知")
    m.add_event("e16b", "E-BM", "报名记录状态", "证书批准", "实验室负责人",
                "报告/证书审核中", "报告/证书审核中", "19.1报告编制和结果通知")
    m.add_event("e17", "E-BM", "报名记录状态", "发放结果报告和证书", "项目管理员",
                "报告/证书审核中", "报告/证书已发布", "19.1报告编制和结果通知")
    m.add_event("e17b", "E-XM", "项目状态", "发放结果报告和证书", "项目管理员",
                "报告审核中", "已结束", "19.1报告编制和结果通知")
    # ── 19.2 测量审核提供者流程（仅登记与 19.1 不同的事件；同构事件复用 e02-e17）──
    m.add_event("e18", "E-BM", "报名记录状态", "受理测量审核报名", "能力验证参加者",
                "无", "报名待审核", "19.2项目准备阶段")
    m.add_event("e18b", "E-XM", "项目状态", "受理测量审核报名", "能力验证参加者",
                "无", "报名中", "19.2项目准备阶段")
    m.add_event("e20", "E-XM", "样品状态", "样品领用登记", "样品管理员",
                "无", "待核查", "19.2实施阶段")
    # e20b：19.2流程表'样品领用登记'行预通知状态列由未发送变待审核
    m.add_event("e20b", "E-BM", "通知状态", "样品领用登记", "样品管理员",
                "未发送", "待审核", "19.2实施阶段")
    m.add_event("e21", "E-BM", "通知状态", "作业指导书编制", "策划人员",
                "待审核", "已审核", "19.2实施阶段")
    # e21b：19.2流程表'作业指导书编制'行预通知状态列取值'待审核/退回/已审核'
    m.add_event("e21b", "E-BM", "通知状态", "作业指导书退回", "策划人员",
                "待审核", "退回", "19.2实施阶段")
    # e21c inferred：退回后修改重新提交，状态机闭环
    m.add_event("e21c", "E-BM", "通知状态", "作业指导书重新提交", "策划人员",
                "退回", "待审核", "19.2实施阶段")
    # e21d：19.2流程表'能力验证预通知'行预通知状态列由已审核变已发送/待确认
    m.add_event("e21d", "E-BM", "通知状态", "能力验证预通知", "项目管理员",
                "已审核", "已发送", "19.2实施阶段")
    # ── 20.4.1 实验室管理 ──
    m.add_event("e22", "E-SYS", "实验室状态", "实验室新增", "机构",
                "无", "待审核", "20.3.1实验室信息")
    m.add_event("e23", "E-SYS", "实验室状态", "实验室修改", "机构",
                "启用", "待审核", "20.4.1.3实验室修改")
    # e23b inferred：退回后修改重新提交，状态机闭环
    m.add_event("e23b", "E-SYS", "实验室状态", "实验室修改", "机构",
                "退回修改", "待审核", "20.4.1.3实验室修改")
    m.add_event("e24", "E-SYS", "实验室状态", "实验室审核通过", "系统管理人员",
                "待审核", "启用", "20.4.1.2实验室审核")
    m.add_event("e25", "E-SYS", "实验室状态", "实验室审核退回", "系统管理人员",
                "待审核", "退回修改", "20.4.1.2实验室审核")
    m.add_event("e26", "E-SYS", "实验室状态", "实验室停用", "系统管理人员",
                "启用", "停用", "20.4.1.1实验室列表与查询")
    m.add_event("e27", "E-SYS", "实验室状态", "实验室启用", "系统管理人员",
                "停用", "启用", "20.4.1.1实验室列表与查询")
    # ── 20.4.2 标准库管理 ──
    m.add_event("e28", "E-BZK", "标准库状态", "新增标准库", "系统管理人员",
                "无", "启用", "20.4.2.2新增标准库")
    m.add_event("e29", "E-BZK", "标准库状态", "停用标准库", "系统管理人员",
                "启用", "停用", "20.4.2.5停用/启用标准库")
    m.add_event("e30", "E-BZK", "标准库状态", "启用标准库", "系统管理人员",
                "停用", "启用", "20.4.2.5停用/启用标准库")
    # ── 20.7 项目评价 ──
    m.add_event("e31", "E-PJ", "评价状态", "测试项目评价细则完善", "评价组长",
                "无", "待评价", "20.7.1.1测试项目评价细则完善")
    m.add_event("e32", "E-PJ", "评价状态", "协同评价", "评价人员",
                "待评价", "评价中", "20.7.1.2协同评价")
    m.add_event("e33", "E-PJ", "评价状态", "评价确认", "评价组长",
                "评价中", "已确认", "20.7.1.3评价确认")
    m.add_event("e34", "E-PJ", "评价状态", "评价退回修改", "评价组长",
                "评价中", "待评价", "20.7.1.3评价确认")
    # ── 20.10.2.3 缴费单退款 ──
    m.add_event("e35", "E-JK", "缴费状态", "缴费单退款", "财务人员",
                "已缴费", "已退款", "20.10.2.3缴费单退款")

    # ===== 1.0 动词词表 → set_prohibition_config =====
    m.set_prohibition_config(config={
        "action_verbs": [
            "立项", "编制", "发布", "报名", "审核", "审核通过", "审核退回",
            "撤销", "缴费", "开具", "核查", "发放", "提交", "退回", "批准",
            "评价", "统计", "确认", "停用", "启用", "新增", "修改", "删除",
            "导入", "导出", "上传", "下载", "查询", "登录", "退款", "回收",
            "选择", "保存", "提交审核", "批量审核", "整理", "发送", "提醒",
            "填充", "维护", "登记", "归还", "测试",
        ],
        "prohibit_keywords": [
            "不可直接删除含有子项的记录",
            "不可同时为空",
            "不可大于当前缴费金额",
            "未结束的项目不可进行消息发送",
            "停用的标准库不可被选择",
            "未上传对应文件且未提交审核的记录不可选定",
        ],
    })

    # ===== 1.1 角色 =====
    # 固定角色（5 用户角色 + 文档出现的执行者）
    m.add_role(id="r01", name="能力验证参加者")
    m.add_role(id="r02", name="项目管理员")
    m.add_role(id="r03", name="策划人员")
    m.add_role(id="r04", name="样品管理员")
    m.add_role(id="r05", name="样品制备人员", readonly=True)
    m.add_role(id="r06", name="评价人员")
    m.add_role(id="r07", name="评价组长")
    m.add_role(id="r08", name="统计人员", readonly=True)
    m.add_role(id="r09", name="技术主管")
    m.add_role(id="r10", name="授权签字人")
    m.add_role(id="r11", name="实验室负责人")
    m.add_role(id="r12", name="财务人员")
    m.add_role(id="r13", name="财务管理人员", readonly=True)
    m.add_role(id="r14", name="质量专员", readonly=True)
    m.add_role(id="r15", name="监督员", readonly=True)
    m.add_role(id="r16", name="系统管理人员")
    m.add_role(id="r17", name="机构")
    m.add_role(id="r18", name="超级管理员", readonly=True)

    # 操作权限（不改状态的查询/列表/session/file/config 类操作）
    m.add_permission(role="系统管理人员", operations=[
        "查询实验室", "审核实验室", "修改实验室", "停用实验室", "启用实验室",
        "新增标准库", "修改标准库", "删除标准库", "停用标准库", "启用标准库",
        "管理测试项", "新增测试项", "修改测试项", "删除测试项",
        "查询信息发送记录", "查看消息详情",
    ])
    m.add_permission(role="项目管理员", operations=[
        "查询项目", "新增项目", "修改项目", "删除项目", "查看项目详情",
        "文件整理", "查看归档", "上传归档文件", "打包下载归档",
        "代码导入", "批量处理项目", "上传结果通知单", "上传证书", "提交审核",
        "消息发送", "测试消息发送", "查询报名信息", "用户报名项目详情",
        "预通知文件下载", "修改财务备注", "导出评价结果", "导出审批流程列表",
    ])
    m.add_permission(role="能力验证参加者", operations=[
        "查询已报名项目", "查看已报名项目详情", "上传付款单", "预通知文件下载",
        "提交结果报告", "下载结果报告", "下载结果通知单", "下载合格证书",
        "查询项目查询", "查询历史项目",
    ])
    m.add_permission(role="评价人员", operations=[
        "查询评价项目", "评价", "导出评价结果",
    ])
    m.add_permission(role="评价组长", operations=[
        "查询评价项目", "完善评价项目", "评价", "结果确认", "保存评价历史",
        "调整评价细则", "退回评价修改", "调整统计规则", "导出评价结果",
    ])
    m.add_permission(role="财务人员", operations=[
        "查询缴费信息", "导出缴费信息", "发票上传", "缴费单退款", "修改财务备注",
    ])
    m.add_permission(role="策划人员", operations=[
        "编制设计方案", "编制任务通知书", "编制结果报告", "编制结果通知单",
        "编制作业指导书", "文件管理",
    ])
    m.add_permission(role="技术主管", operations=[
        "审核报告", "审核结果通知单", "审核证书", "审核评价细则", "方案审批",
    ])
    m.add_permission(role="授权签字人", operations=[
        "批准结果报告", "批准结果通知单", "批准使用认可标识", "报告审批",
    ])
    m.add_permission(role="实验室负责人", operations=[
        "批准能力验证计划立项", "批准能力验证计划邀请函", "签发能力验证合格证书",
        "批准证书",
    ])
    m.add_permission(role="样品管理员", operations=[
        "样品出入库登记", "样品核查", "样品发放", "样品借出归还",
    ])
    m.add_permission(role="超级管理员", operations=[
        "维护平台资源", "维护信息发布内容", "权限分配", "权限审核",
    ])
    m.add_permission(role="机构", operations=[
        "新增实验室信息", "修改实验室信息",
    ])

    # ===== 1.4 实体落盘 =====

    # ── E-XM 验证项目（core, multi-state, approvable, expirable）──
    m.add_entity(
        id="E-XM", name="验证项目", desc="能力验证/测量审核项目，承载项目主流程状态与样品状态",
        type="core", tags=["approvable", "multi-state", "expirable"],
        attributes=[
            attr(name="项目编号", desc="项目唯一编号"),
            attr(name="项目名称", desc="项目名称"),
            attr(name="产品类型", desc="项目所属产品类型"),
            attr(name="项目类型", desc="能力验证或测量审核", is_config=True),
            attr(name="所属年度", desc="项目所属年度"),
            attr(name="依据标准", desc="项目依据标准信息"),
            attr(name="项目费用", desc="项目应收费用金额"),
            attr(name="监督员", desc="项目新增表单新增字段", is_config=True),
            attr(name="技术主管", desc="项目人员，候选人唯一时默认填充"),
            attr(name="实验室负责人", desc="项目人员，候选人唯一时默认填充"),
            attr(name="授权签字人", desc="项目人员，候选人唯一时默认填充"),
            attr(name="财务备注", desc="项目列表新增字段，管理人员可修改"),
        ],
        state_dimensions=[
            {"dimension_name": "项目状态",
             "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
             "initial": "待开始", "terminal": ["已结束"],
             "inferred": ["进行中", "报告审核中", "已结束"],
             "note": {"comment": "依据19.3状态枚举；'进行中'由e09c推断（能力验证预通知后项目进入实施）、'报告审核中'由e14b推断（编制结果报告后进入审核）、'已结束'由e17b推断（发放后项目完结）"}},
            {"dimension_name": "样品状态",
             "states": ["待核查", "已核查", "已发样", "已还样", "无需还样"],
             "initial": "待核查", "terminal": ["无需还样"],
             "inferred": ["已发样", "已还样", "无需还样"],
             "note": {"comment": "19.3枚举仅'待核查、已核查'，'已发样、已还样、无需还样'由19.1/19.2流程表'样品状态'列取值推导；19.1'参加者测试与结果提交'行取值'已还样、待核查/无需还样'，待核查为循环回归"}},
        ],
        operations=[
            op(name="查询项目", category="query",
               expected_results=["列表分页展示符合条件的项目记录"],
               source_ref="20.5.1项目管理",
               note=N(role="项目管理员")),
            op(name="新增项目", category="crud",
               expected_results=["项目创建成功，状态为待开始", "导出项目通知书时填充监督员到对应位置"],
               source_ref="20.5.1.5项目新增表单增加监督员",
               note=N(role="项目管理员")),
            op(name="修改项目", category="crud",
               expected_results=["项目信息更新成功"],
               source_ref="20.5.1项目管理",
               note=N(role="项目管理员")),
            op(name="删除项目", category="crud",
               expected_results=["项目记录删除"],
               source_ref="20.2.3待办事项",
               note=N(role="项目管理员")),
            op(name="查看项目详情", category="query",
               expected_results=["跳转到项目详情页"],
               source_ref="20.5.2.1已报名项目增加多次付款功能",
               note=N(role="项目管理员")),
            op(name="文件整理", category="file",
               expected_results=["系统开启整理任务并提示'归档任务已开启，请稍后查看'", "整理完成后操作列显示'查看归档'按钮"],
               source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员")),
            op(name="查看归档", category="query",
               expected_results=["进入归档数据查看页面，可查看并补充归档信息"],
               source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员")),
            op(name="上传归档文件", category="file",
               expected_results=["补充文件的项目阶段为其它，保存表单数据"],
               source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员")),
            op(name="打包下载归档", category="file",
               expected_results=["下载zip格式文件，内含清单文件和按项目阶段命名的目录"],
               source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员")),
            op(name="代码导入", category="file",
               expected_results=["导入报名机构的三方代码"],
               source_ref="20.5.1.2机构代码导入",
               note=N(role="项目管理员")),
            op(name="批量处理项目", category="ui",
               expected_results=["跳转到报名信息批量处理页面，可集中上传通知单与证书并批量提交审核"],
               source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员")),
            op(name="上传结果通知单", category="file",
               expected_results=["结果通知单文件上传成功"],
               source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员")),
            op(name="上传证书", category="file",
               expected_results=["证书文件上传成功"],
               source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员")),
            op(name="提交审核", category="crud",
               expected_results=["对选择的记录进行任务提交操作；未选择记录时提示用户选择"],
               source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员")),
            op(name="消息发送", category="crud",
               expected_results=["未结束的项目可进行消息发送；系统验证通过后将消息按选择方式发送"],
               source_ref="20.5.1.4优化消息发送功能",
               note=N(role="项目管理员")),
            op(name="测试消息发送", category="crud",
               expected_results=["发送测试信息到指定接收号码"],
               source_ref="20.5.1.4优化消息发送功能",
               note=N(role="项目管理员")),
        ],
    )

    # ── E-BM 报名记录（core, multi-state, approvable, expirable, collaborative）──
    m.add_entity(
        id="E-BM", name="报名记录", desc="参加者报名项目后生成的记录，承载6个状态维度",
        type="core", tags=["approvable", "multi-state", "expirable", "collaborative"],
        attributes=[
            attr(name="报名编号", desc="报名记录唯一编号"),
            attr(name="项目编号", desc="关联项目编号"),
            attr(name="实验室名称", desc="报名实验室"),
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="报名时间", desc="报名提交时间"),
            attr(name="实施状态", desc="报名记录状态值"),
            attr(name="付款状态", desc="费用状态值"),
            attr(name="评价得分", desc="项目评价得分"),
            attr(name="评价结果", desc="项目评价结果"),
        ],
        state_dimensions=[
            {"dimension_name": "通知状态",
             "states": ["未发送", "已发送", "待确认", "待审核", "退回", "已审核", "已批准", "已确认"],
             "initial": "未发送", "terminal": ["已确认"],
             "inferred": ["已发送", "已确认"],
             "note": {"comment": "19.3枚举'未发送、待确认、待审核、退回、已审核、已批准'；19.1流程表'预通知状态'列取值含'已发送/待确认'、'已确认'，按表格列推导并集；19.2流程表'预通知状态'列取值含'待审核/退回/已审核'。'已发送'为'待确认'前序态，'已确认'为预通知收到确认终态；'待确认'、'已批准'为枚举但无事件覆盖（孤岛）"}},
            {"dimension_name": "报名记录状态",
             "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
             "initial": "报名待审核", "terminal": ["报告/证书已发布", "已撤销"],
             "note": {"comment": "依据19.3状态枚举；19.1/19.2流程表登记各状态落入事件"}},
            {"dimension_name": "报名记录样品状态",
             "states": ["待发样", "待收样", "已收样", "已确认"],
             "initial": "待发样", "terminal": ["已确认"],
             "note": {"comment": "依据19.3状态枚举；e10b落入'待发样'、e11c落入'已收样'"}},
            {"dimension_name": "费用状态",
             "states": ["待缴费", "已缴费"],
             "initial": "待缴费", "terminal": ["已缴费"],
             "note": {"comment": "依据19.3状态枚举；e03c创建落入'待缴费'、e07落入'已缴费'；多次付款不改费用状态（20.5.2.1）"}},
            {"dimension_name": "发票状态",
             "states": ["待开票", "已开票"],
             "initial": "待开票", "terminal": ["已开票"],
             "note": {"comment": "依据19.3状态枚举；e03d创建落入'待开票'、e08落入'已开票'；多次分批上传不改发票状态（20.10.2.2）"}},
            {"dimension_name": "缴费通知单状态",
             "states": ["未发送", "已发送"],
             "initial": "未发送", "terminal": ["已发送"],
             "inferred": ["未发送", "已发送"],
             "note": {"comment": "19.3状态表未单独枚举'缴费通知单状态'，19.1/19.2流程表有'缴费通知单'列取值'未发送/已发送'，按表格列推导；与'通知状态'区分：通知状态承载预通知生命周期，缴费通知单状态承载缴费通知发送状态"}},
        ],
        operations=[
            op(name="查询报名信息", category="query",
               expected_results=["列表分页展示符合条件的数据记录"],
               source_ref="20.5.3用户报名列表",
               note=N(role="项目管理员")),
            op(name="用户报名项目详情", category="query",
               expected_results=["跳转到项目详情页"],
               source_ref="20.5.3.1用户报名项目详情页面增加预通知文件下载",
               note=N(role="项目管理员")),
            op(name="上传付款单", category="file",
               expected_results=["付款录入表单提交成功，可多次进行付款操作"],
               source_ref="20.5.2.1已报名项目增加多次付款功能",
               note=N(role="能力验证参加者")),
            op(name="预通知文件下载", category="file",
               expected_results=["点击预通知文件后的文件连接下载文件"],
               source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载",
               note=N(role="能力验证参加者")),
            op(name="提交结果报告", category="file",
               expected_results=["参加者在完成测试后提交结果报告"],
               source_ref="19.4能力验证参加者工作流程分析",
               note=N(role="能力验证参加者")),
            op(name="下载结果报告", category="file",
               expected_results=["参加者接收能力验证计划结果报告"],
               source_ref="19.4能力验证参加者工作流程分析",
               note=N(role="能力验证参加者")),
            op(name="下载结果通知单", category="file",
               expected_results=["参加者接收个人的结果通知单"],
               source_ref="19.4能力验证参加者工作流程分析",
               note=N(role="能力验证参加者")),
            op(name="修改财务备注", category="crud",
               expected_results=["财务备注内容更新"],
               source_ref="20.10.2.1项目列表增加财务备注字段",
               note=N(role="财务人员")),
        ],
    )

    # ── E-SYS 实验室（managed, approvable）──
    m.add_entity(
        id="E-SYS", name="实验室", desc="机构维护的实验室信息，需经系统管理人员审核后启用",
        type="managed", tags=["approvable"],
        attributes=[
            attr(name="实验室编号", desc="实验室唯一编号"),
            attr(name="实验室名称", desc="实验室名称"),
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="法人名称", desc="法人名称"),
            attr(name="企业类型", desc="企业类型"),
            attr(name="企业规模", desc="企业规模"),
            attr(name="CNAS", desc="已获CNAS认可及证书号"),
            attr(name="CMA", desc="已获CMA认可及证书编号"),
            attr(name="联系人", desc="联系人"),
            attr(name="联系电话", desc="联系电话"),
            attr(name="邮箱", desc="邮箱"),
            attr(name="座机号码", desc="座机号码"),
            attr(name="行政区域", desc="行政区域"),
            attr(name="详细地址", desc="详细地址"),
            attr(name="默认实验室", desc="是否为默认实验室"),
            attr(name="证明文件", desc="营业执照或其他证书材料"),
        ],
        state_dimensions=[
            {"dimension_name": "实验室状态",
             "states": ["待审核", "启用", "停用", "退回修改"],
             "initial": "待审核", "terminal": [],
             "note": {"comment": "依据20.3.1实验室信息新增状态字段；启用/停用为双向转换无终态"}},
        ],
        operations=[
            op(name="查询实验室", category="query",
               expected_results=["列表分页展示符合条件的实验室记录"],
               source_ref="20.4.1.1实验室列表与查询",
               note=N(role="系统管理人员")),
            op(name="新增实验室信息", category="crud",
               expected_results=["机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名"],
               source_ref="20.3.1实验室信息",
               note=N(role="机构")),
            op(name="修改实验室信息", category="crud",
               expected_results=["提交修改内容，状态变更为待审核"],
               source_ref="20.4.1.3实验室修改",
               note=N(role="机构")),
            op(name="审核实验室", category="crud",
               expected_results=["审核通过则状态变更为'启用'并为当前数据生成快照记录；退回修改则状态变更为'已退回'"],
               source_ref="20.4.1.2实验室审核",
               note=N(role="系统管理人员")),
            op(name="停用实验室", category="crud",
               expected_results=["状态立即改变为停用，列表刷新"],
               source_ref="20.4.1.1实验室列表与查询",
               note=N(role="系统管理人员")),
            op(name="启用实验室", category="crud",
               expected_results=["状态立即改变为启用，列表刷新"],
               source_ref="20.4.1.1实验室列表与查询",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-BZK 标准库（managed, configurable）──
    m.add_entity(
        id="E-BZK", name="标准库", desc="代表一个完整的、可被引用的标准集合",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="标准库编号，必填"),
            attr(name="标准库名称", desc="标准库名称，必填"),
            attr(name="状态", desc="启用/停用，必填", is_config=True),
            attr(name="描述", desc="标准库描述，选填"),
            attr(name="创建时间", desc="标准库创建时间"),
        ],
        state_dimensions=[
            {"dimension_name": "标准库状态",
             "states": ["启用", "停用"],
             "initial": "启用", "terminal": [],
             "note": {"comment": "依据20.4.2.1列表展示字段'状态（启用/停用）'；启用/停用为双向转换"}},
        ],
        operations=[
            op(name="新增标准库", category="crud",
               expected_results=["创建一个新的标准库，状态默认启用"],
               source_ref="20.4.2.2新增标准库",
               note=N(role="系统管理人员")),
            op(name="修改标准库", category="crud",
               expected_results=["标准库信息更新成功"],
               source_ref="20.4.2.3修改标准库",
               note=N(role="系统管理人员")),
            op(name="删除标准库", category="crud",
               expected_results=["弹出二次确认框'确认删除标准库『XXX』？'，确认后删除"],
               source_ref="20.4.2.4删除标准库",
               note=N(role="系统管理人员")),
            op(name="停用标准库", category="crud",
               expected_results=["弹出二次确认框，确认后状态立即改变，列表刷新；停用的标准库在项目创建等环节不可被选择"],
               source_ref="20.4.2.5停用/启用标准库",
               note=N(role="系统管理人员")),
            op(name="启用标准库", category="crud",
               expected_results=["弹出二次确认框，确认后状态立即改变，列表刷新"],
               source_ref="20.4.2.5停用/启用标准库",
               note=N(role="系统管理人员")),
            op(name="管理测试项", category="ui",
               expected_results=["页面跳转或打开一个新标签页，进入该标准库的专属测试项管理界面"],
               source_ref="20.4.2.6进入测试项管理界面",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-CSX 测试项（managed）──
    m.add_entity(
        id="E-CSX", name="测试项", desc="标准库或子领域下的测试项，由编号和名称组成，可有子测试项",
        type="managed", tags=[],
        attributes=[
            attr(name="标号", desc="测试项标号，必填"),
            attr(name="名称", desc="测试项名称，必填"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud",
               expected_results=["新增子项或测试参数；系统校验后保存，刷新列表中的数据信息"],
               source_ref="20.4.2.8新增测试项",
               note=N(role="系统管理人员")),
            op(name="修改测试项", category="crud",
               expected_results=["系统校验后保存，刷新列表中的数据信息"],
               source_ref="20.4.2.9修改测试项",
               note=N(role="系统管理人员")),
            op(name="删除测试项", category="crud",
               expected_results=["弹出二次确认框'确认删除测试项『XXX』？'；含有子项的记录不允许删除"],
               source_ref="20.4.2.10删除测试项",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-ZLY 子领域（managed）──
    m.add_entity(
        id="E-ZLY", name="子领域", desc="项目分类的子领域，其下挂测试项",
        type="managed", tags=[],
        attributes=[
            attr(name="子领域名称", desc="子领域名称"),
        ],
        state_dimensions=[],
        operations=[
            op(name="管理子领域测试项", category="ui",
               expected_results=["页面跳转或打开一个新标签页，进入该子领域的专属测试项管理界面"],
               source_ref="20.4.3.1进入测试项管理界面",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-PJ 评价记录（core, approvable, collaborative）──
    m.add_entity(
        id="E-PJ", name="评价记录", desc="项目评价流程的承载实体，评价组长确认后评价状态关闭",
        type="core", tags=["approvable", "collaborative"],
        attributes=[
            attr(name="项目编号", desc="关联项目编号"),
            attr(name="评分方式", desc="分值或权重", is_config=True),
            attr(name="及格分", desc="及格分录入后跟随其他结果一起记录到系统中"),
            attr(name="评价人员", desc="新建项目时项目管理员选择的评价人员列表"),
            attr(name="评价组长", desc="第一个被选择的评价人员默认做为评价组长"),
        ],
        state_dimensions=[
            {"dimension_name": "评价状态",
             "states": ["待评价", "评价中", "已确认"],
             "initial": "待评价", "terminal": ["已确认"],
             "inferred": ["待评价", "评价中", "已确认"],
             "note": {"comment": "20.7项目评价未给出状态枚举表，依据20.7.1.2协同评价、20.7.1.3评价确认推导：e31完善落入'待评价'、e32协同评价落入'评价中'、e33评价确认落入'已确认'；'项目评价状态关闭'对应'已确认'"}},
        ],
        operations=[
            op(name="完善评价项目", category="crud",
               expected_results=["评价组长编辑完善评价项目及评价细则内容；点击确定后保存完善后的测试项目数据"],
               source_ref="20.7.1.1测试项目评价细则完善",
               note=N(role="评价组长")),
            op(name="评价", category="crud",
               expected_results=["评价人员对自己的评价结果进行修改；点击确定提交结果"],
               source_ref="20.7.1.2协同评价",
               note=N(role="评价人员")),
            op(name="结果确认", category="crud",
               expected_results=["将当前结果正式提交为项目的最终评价结果，项目评价状态关闭"],
               source_ref="20.7.1.3评价确认",
               note=N(role="评价组长")),
            op(name="保存评价历史", category="crud",
               expected_results=["将当前评价结果保存为历史结果"],
               source_ref="20.7.1.3评价确认",
               note=N(role="评价组长")),
            op(name="调整评价细则", category="ui",
               expected_results=["打开评价细节完善页面，配置完成后回到本页面将会刷新本页面数据"],
               source_ref="20.7.1.3评价确认",
               note=N(role="评价组长")),
            op(name="退回评价修改", category="crud",
               expected_results=["将当前评价结果保存为历史结果，并开启下一轮评价"],
               source_ref="20.7.1.3评价确认",
               note=N(role="评价组长")),
            op(name="调整统计规则", category="config",
               expected_results=["弹出统计规则配置弹窗，评价组长可配置统计规则；每个统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值"],
               source_ref="20.7.1.3评价确认",
               note=N(role="评价组长")),
            op(name="导出评价结果", category="file",
               expected_results=["下载评价结果"],
               source_ref="20.7.1.4评价结果导出",
               note=N(role="评价人员")),
        ],
    )

    # ── E-JK 缴费记录（core, expirable）──
    m.add_entity(
        id="E-JK", name="缴费记录", desc="报名项目的缴费记录，支持多次付款与退款",
        type="core", tags=["expirable"],
        attributes=[
            attr(name="报名编号", desc="关联报名编号"),
            attr(name="支付方式", desc="支付方式，必填"),
            attr(name="支付账户名称", desc="支付账户名称，必填"),
            attr(name="汇款金额", desc="汇款金额，必填，默认为项目费用金额"),
            attr(name="付款底单", desc="付款底单文件，必填"),
            attr(name="付款项目", desc="当前报名编号，只读"),
            attr(name="缴费时间", desc="缴费时间"),
            attr(name="到款日期", desc="到款日期"),
            attr(name="退款金额", desc="退款金额，多次退款金额做累加处理，红色字体且大于0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="管理备注", desc="记录退款原因等内容"),
        ],
        state_dimensions=[
            {"dimension_name": "缴费状态",
             "states": ["已缴费", "已退款"],
             "initial": "已缴费", "terminal": ["已退款"],
             "inferred": ["已缴费", "已退款"],
             "note": {"comment": "20.10.2.3缴费单退款新增退款功能；状态枚举 inferred：缴费记录创建落入'已缴费'、缴费单退款落入'已退款'"}},
        ],
        operations=[
            op(name="查询缴费信息", category="query",
               expected_results=["列表分页展示符合条件的缴费记录"],
               source_ref="20.10.1.1缴费信息查询与管理",
               note=N(role="财务人员")),
            op(name="导出缴费信息", category="file",
               expected_results=["导出符合筛选条件的所有数据"],
               source_ref="20.10.1.1缴费信息查询与管理",
               note=N(role="财务人员")),
            op(name="发票上传", category="file",
               expected_results=["支持多次分批上传发票；发票上传后会显示在发票列表中，点击文件地址后的'x'可以移除文件"],
               source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传",
               note=N(role="财务人员")),
            op(name="缴费单退款", category="crud",
               expected_results=["退款金额不能大于当前缴费金额；退款后更新'项目费用'为实际付款金额"],
               source_ref="20.10.2.3缴费单退款",
               note=N(role="财务人员")),
        ],
    )

    # ── E-XXJL 信息发送记录（managed）──
    m.add_entity(
        id="E-XXJL", name="信息发送记录", desc="系统中的信息发送历史记录",
        type="managed", tags=[],
        attributes=[
            attr(name="接收号码", desc="消息接收号码"),
            attr(name="发送方式", desc="短信/邮件/站内信"),
            attr(name="发送时间", desc="消息发送时间"),
            attr(name="发送人", desc="消息发送人"),
            attr(name="发送结果", desc="消息发送结果"),
            attr(name="消息标题", desc="消息标题"),
            attr(name="消息内容", desc="消息内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query",
               expected_results=["列表分页展示符合条件的信息发送记录"],
               source_ref="20.4.4.1信息发送记录",
               note=N(role="系统管理人员")),
            op(name="查看消息详情", category="query",
               expected_results=["点击可查看消息详细内容"],
               source_ref="20.4.4.1信息发送记录",
               note=N(role="系统管理人员")),
        ],
    )

    # ── E-ZS 证书（managed, expirable）──
    m.add_entity(
        id="E-ZS", name="证书", desc="能力验证合格证书，到期前30天邮件提醒",
        type="managed", tags=["expirable"],
        attributes=[
            attr(name="证书编号", desc="证书唯一编号"),
            attr(name="到期时间", desc="证书到期时间"),
            attr(name="关联报名编号", desc="关联报名编号"),
        ],
        state_dimensions=[],
        operations=[
            op(name="下载合格证书", category="file",
               expected_results=["参加者接收能力验证合格证书"],
               source_ref="19.4能力验证参加者工作流程分析",
               note=N(role="能力验证参加者")),
        ],
    )

    # ===== 1.5 结构关系 =====
    # 验证项目 → 报名记录（1:N，composition，业务归属）
    m.add_structural(
        frm="E-XM", to="E-BM",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="一个验证项目对应多条报名记录；项目为业务归属容器，报名记录有独立创建流程",
        confidence="high",
        note={"comment": "判定(c)：B有独立创建流程(e03报名)、B是core流程实体、A为业务归属容器；management_dimension复核：项目创建时报名记录尚不存在，B独立创建"},
    )
    # 验证项目 → 评价记录（1:1，composition，业务归属）
    m.add_structural(
        frm="E-XM", to="E-PJ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="一个验证项目对应一份评价记录；评价记录在项目评价阶段创建",
        confidence="high",
        note={"comment": "判定(c)：评价记录有独立创建流程(e31)、core流程实体、项目为业务归属容器；management_dimension复核：评价记录随项目评价阶段创建"},
    )
    # 报名记录 → 缴费记录（1:N，composition，业务归属）
    m.add_structural(
        frm="E-BM", to="E-JK",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="一条报名记录对应多条缴费记录；支持多次付款与退款",
        confidence="high",
        note={"comment": "判定(b)：缴费记录在报名记录生命周期内创建、每条报名记录必有缴费记录；20.5.2.1多次付款；management_dimension复核：缴费记录归属于报名记录"},
    )
    # 报名记录 → 证书（1:N，reference）
    m.add_structural(
        frm="E-BM", to="E-ZS",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="一条报名记录可能关联多份证书（含合格证书、复印件等）",
        confidence="medium",
        note={"comment": "判定(d)：证书有独立发放流程(e17)、可能永不创建（未通过的参加者无合格证书）、不满足(c)；management_dimension复核：证书由报告/证书审核流程产出"},
    )
    # 标准库 → 测试项（1:N，composition，配置来源）
    m.add_structural(
        frm="E-BZK", to="E-CSX",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="标准库下挂多个测试项；测试项随标准库管理",
        confidence="high",
        note={"comment": "判定(a)：标准库为测试项提供分类容器，测试项独立创建；20.4.2.6管理测试项；management_dimension复核：测试项归属于标准库"},
    )
    # 子领域 → 测试项（M:N，reference）
    m.add_structural(
        frm="E-ZLY", to="E-CSX",
        relation_type="reference", cardinality="M:N",
        ownership_dimension="configuration_source",
        desc="子领域下挂测试项，测试项数据来源于标准库（20.4.3由表单方式变更为选择方式）",
        confidence="high",
        note={"comment": "判定(a)：子领域引用标准库中的测试项；20.4.3子领域管理；management_dimension复核：子领域仅引用，不拥有测试项"},
    )
    # 实验室 → 报名记录（1:N，reference）
    m.add_structural(
        frm="E-SYS", to="E-BM",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="一个实验室可有多条报名记录；实验室为报名的业务归属容器",
        confidence="high",
        note={"comment": "判定(d)：报名记录有独立创建流程、实验室不级联删除；management_dimension复核：实验室信息独立维护"},
    )

    # ===== 2. 分支维度 =====

    # ── 项目类型（能力验证 / 测量审核）：配置型① + 运行时选择② ──
    # 来源：19.1 vs 19.2 流程差异；20.5/20.6 模块拆分；20.8.3.1项目类型下拉框
    m.add_branch_dimension(
        dimension="项目类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="项目主流程：能力验证由'能力验证计划发布'启动；测量审核由'受理测量审核报名'启动。测量审核实施阶段含'样品领用登记'(e20)、'作业指导书编制'(e21)等差异事件",
        evidence="三型判定：①配置型（项目类型在创建时定、影响后续流程，见20.5/20.6模块拆分）；②运行时选择型（'项目类型：下拉框，精确匹配；选项包括：能力验证、测量审核'，见20.8.3.1项目统计与查询）",
        branches=[
            {"value": "能力验证", "target_transition": "t02", "desc": "能力验证流程：设计方案编制→能力验证计划发布→报名→…→发放结果报告和证书"},
            {"value": "测量审核", "target_transition": "t02b", "desc": "测量审核流程：受理测量审核报名→报名审核→编制缴纳测量审核费用通知→…→发放结果报告和证书"},
        ],
    )

    # ── 评价方式（分值 / 权重）：配置型① ──
    # 来源：20.7项目列表"支持分值和权重两种评价方式"；20.7.1.1表单"分值/权重：文本框，必填"
    m.add_branch_dimension(
        dimension="评价方式", entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="评价录入与结果确认页面的列标题显示'分值/权重'；评价表单字段同名",
        evidence="三型判定：①配置型（评分方式在项目创建时定、影响评价录入字段，见20.7.1.2'评分方式'项目信息字段）",
        branches=[
            {"value": "分值", "target_transition": "t42", "desc": "评价人员按分值录入评价结果"},
            {"value": "权重", "target_transition": "t42", "desc": "评价人员按权重录入评价结果"},
        ],
    )

    # ── 发票类型（电子专票 / 电子普票）：配置型① ──
    # 来源：20.10.1.1缴费信息管理"发票类型：下拉列表，精确匹配，选项包括：电子专票、电子普票"
    m.add_branch_dimension(
        dimension="发票类型", entity="E-JK",
        values=["电子专票", "电子普票"],
        impact_scope="缴费信息查询的发票类型筛选；发票开具流程按类型处理",
        evidence="三型判定：①配置型（发票类型在缴费时选定、影响查询筛选，见20.10.1.1）",
        branches=[
            {"value": "电子专票", "target_transition": "t30", "desc": "开具电子专票"},
            {"value": "电子普票", "target_transition": "t30", "desc": "开具电子普票"},
        ],
    )

    # ── 审核结果（通过 / 退回修改）：运行时选择型② ──
    # 来源：20.4.1.2实验室审核"审核结果：单选框（通过、退回修改）"；20.9.1.4任务批量处理"审核结果：下拉选择框，选项有：同意、退回"
    m.add_branch_dimension(
        dimension="审核结果", entity="E-SYS",
        values=["通过", "退回修改"],
        impact_scope="实验室审核：通过则状态变更为'启用'，退回修改则状态变更为'已退回'且必须填写审核意见",
        evidence="三型判定：②运行时选择型（'审核结果：单选框'，见20.4.1.2实验室审核）",
        branches=[
            {"value": "通过", "target_transition": "t35", "desc": "审核通过，实验室状态变更为启用"},
            {"value": "退回修改", "target_transition": "t35b", "desc": "审核退回，实验室状态变更为退回修改"},
        ],
    )

    # ===== 3. 转换与因果 =====

    # ── 3.1 转换 ──

    # ─ E-XM 验证项目 - 项目状态维度 ─
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[],
        expected_results=["项目创建并落入待开始状态", "任务通知书编制完成"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1方案设计阶段",
        note={"comment": "源自 e01；⓪frm=None→forward；创建转换；P0主流程必经"},
    )
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
            precond(text="设计方案已编制完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为报名中", "能力验证计划通知或邀请函发布"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e02；③序判frm先于to；分支维度=项目类型，能力验证路径首条；P0主流程"},
    )
    m.add_trans(
        tid="t02b", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="受理测量审核报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["测量审核项目状态落入报名中", "报名记录状态为报名待审核"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.2项目准备阶段",
        note={"comment": "源自 e18/e18b；⓪frm=None→forward；分支维度=项目类型，测量审核路径首条；P0主流程"},
    )
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目状态变更为进行中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e09c；③序判frm先于to；状态'进行中'inferred（19.3枚举有，19.1流程表未直接登记该列落入事件，按状态机连续性推导）；P0主流程"},
    )
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
            precond(text="结果已提交", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为报告审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e14b；③序判frm先于to；状态'报告审核中'inferred（19.3枚举有，19.1流程表该行项目状态列空缺，按报告审核阶段推导）；P0主流程"},
    )
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="报告/证书已批准", ptype="event_ref"),
        ],
        expected_results=["项目状态变更为已结束", "结果报告和证书已发放"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e17b；③序判frm先于to；状态'已结束'inferred（19.3枚举有，19.1流程表该行项目状态列空缺，按项目完结推导）；P0主流程"},
    )

    # ─ E-XM 验证项目 - 样品状态维度 ─
    m.add_trans(
        tid="t06", entity="E-XM", dimension="样品状态",
        frm=None, to="待核查", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录费用状态为待缴费", ptype="state_ref",
                    ref=state_ref("E-BM", "费用状态", "待缴费")),
        ],
        expected_results=["项目样品状态落入待核查"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e07b；⓪frm=None→forward；创建转换；19.1流程表'缴费'行样品状态列由空变待核查（表格列推导）；P1业务必需"},
    )
    m.add_trans(
        tid="t06b", entity="E-XM", dimension="样品状态",
        frm=None, to="待核查", action="样品领用登记", role="样品管理员",
        preconditions=[],
        expected_results=["测量审核项目样品状态落入待核查"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e20；⓪frm=None→forward；创建转换；分支维度=项目类型，测量审核路径（能力验证路径由t06缴费触发样品状态创建）；P0主流程"},
    )
    m.add_trans(
        tid="t07", entity="E-XM", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变更为已核查", "生成核查记录表"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e10；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t08", entity="E-XM", dimension="样品状态",
        frm="已核查", to="已发样", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已核查")),
        ],
        expected_results=["样品状态变更为已发样", "作业指导书发送", "记录快递单号或者软件访问路径"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e11；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t09", entity="E-XM", dimension="样品状态",
        frm="已发样", to="已还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已发样")),
        ],
        expected_results=["样品状态变更为已还样", "测试结果与报名表盖章版提交"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e12；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t09b", entity="E-XM", dimension="样品状态",
        frm="已还样", to="待核查", action="批次重置", role="样品管理员",
        preconditions=[
            precond(text="样品处于已还样状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已还样")),
        ],
        expected_results=["样品状态变更为待核查，进入下一批次"],
        traits=[], direction="forward", priority="P2",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e12 后续；序判④后于，语义forward（循环状态机，'待核查'为下一批次起点），语义优先；P2低频"},
    )
    m.add_trans(
        tid="t09c", entity="E-XM", dimension="样品状态",
        frm="已发样", to="无需还样", action="无需还样标记", role="样品管理员",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已发样")),
            precond(text="样品类型为无需还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["样品状态变更为无需还样"],
        traits=[], direction="forward", priority="P2",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e12 后续；19.1流程表'参加者测试与结果提交'行'已还样、待核查/无需还样'；'无需还样'inferred（19.3无该状态，按流程表推导）；P2低频"},
    )

    # ─ E-BM 报名记录 - 报名记录状态维度 ─
    m.add_trans(
        tid="t10", entity="E-BM", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="实验室已审核通过", ptype="event_ref"),
        ],
        expected_results=["报名记录状态落入报名待审核", "生成报名表"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e03；⓪frm=None→forward；创建转换；P0主流程必经；20.3.1实验室审核通过后方可用于项目报名"},
    )
    m.add_trans(
        tid="t11", entity="E-BM", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为报名成功", "缴费通知单状态变更为已发送"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e04；③序判frm先于to；P0主流程；联动缴费通知单状态：未发送→已发送"},
    )
    m.add_trans(
        tid="t11b", entity="E-BM", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="重新提交报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名退回")),
        ],
        expected_results=["报名记录状态变更为报名待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "inferred：报名退回后参加者修改重新提交，状态机闭环；P1"},
    )
    m.add_trans(
        tid="t12", entity="E-BM", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核退回", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为报名退回"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e05；①'退回'→backward；P1回退非主路径"},
    )
    m.add_trans(
        tid="t13", entity="E-BM", dimension="报名记录状态",
        frm="报名待审核", to="已撤销", action="报名撤销", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变更为已撤销"],
        traits=["rollback"], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e06；③序判frm先于to；'已撤销'为终态；P1回退/撤销非主路径"},
    )
    m.add_trans(
        tid="t14", entity="E-BM", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名成功")),
        ],
        expected_results=["报名记录状态变更为结果待提交", "预通知发送"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e09b；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t15", entity="E-BM", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变更为结果已提交", "测试结果与报名表盖章版提交"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e12b；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t16", entity="E-BM", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果报告退回", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变更为结果退回修改"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e13；①'退回'→backward；P1回退非主路径"},
    )
    m.add_trans(
        tid="t17", entity="E-BM", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交", action="结果重新提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果退回修改")),
        ],
        expected_results=["报名记录状态变更为结果已提交"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e13b；③序判frm先于to；P1回退后重新提交"},
    )
    m.add_trans(
        tid="t18", entity="E-BM", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变更为报告/证书审核中", "报告与结果通知编制完成"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e14；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t19", entity="E-BM", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="报告审核", role="技术主管",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["技术主管审核报告完成，状态保持报告/证书审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e15；⑤仅自环→forward+inferred；P0主流程审核环节"},
    )
    m.add_trans(
        tid="t20", entity="E-BM", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="报告批准", role="授权签字人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")),
            precond(text="技术主管已审核报告", ptype="event_ref"),
        ],
        expected_results=["授权签字人批准结果报告与结果通知单，状态保持报告/证书审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e16；⑤仅自环→forward+inferred；P0主流程批准环节"},
    )
    m.add_trans(
        tid="t20b", entity="E-BM", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="证书批准", role="实验室负责人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")),
            precond(text="授权签字人已批准报告", ptype="event_ref"),
        ],
        expected_results=["实验室负责人批准证书，状态保持报告/证书审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e16b；⑤仅自环→forward+inferred；P0主流程批准环节"},
    )
    m.add_trans(
        tid="t21", entity="E-BM", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")),
            precond(text="授权签字人已批准", ptype="event_ref"),
            precond(text="实验室负责人已批准证书", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变更为报告/证书已发布", "结果报告和证书发放给参加者"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e17；③序判frm先于to；P0主流程；'报告/证书已发布'为终态"},
    )

    # ─ E-BM 报名记录 - 通知状态维度 ─
    m.add_trans(
        tid="t22", entity="E-BM", dimension="通知状态",
        frm=None, to="未发送", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["通知状态落入未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e03b；⓪frm=None→forward；创建转换；P0主流程"},
    )
    m.add_trans(
        tid="t23", entity="E-BM", dimension="通知状态",
        frm="未发送", to="已发送", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "未发送")),
        ],
        expected_results=["预通知已发送，通知状态变更为已发送/待确认", "生成预通知与用户信息表"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e09；③序判frm先于to；'已发送'inferred（19.3枚举无，按流程表'已发送/待确认'推导）；P0主流程"},
    )
    m.add_trans(
        tid="t23b", entity="E-BM", dimension="通知状态",
        frm="未发送", to="待审核", action="样品领用登记", role="样品管理员",
        preconditions=[
            precond(text="通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "未发送")),
        ],
        expected_results=["通知状态变更为待审核（测量审核路径）"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e20b；③序判frm先于to；分支维度=项目类型，测量审核路径；19.2流程表'样品领用登记'行预通知状态列由未发送变待审核；P0主流程"},
    )
    m.add_trans(
        tid="t23c", entity="E-BM", dimension="通知状态",
        frm="待审核", to="已审核", action="作业指导书编制", role="策划人员",
        preconditions=[
            precond(text="通知状态为待审核", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "待审核")),
            precond(text="作业指导书审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["通知状态变更为已审核（作业指导书编制通过）"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e21；③序判frm先于to；分支维度=项目类型，测量审核路径；19.2流程表'作业指导书编制'行预通知状态列取值'待审核/退回/已审核'；P0主流程"},
    )
    m.add_trans(
        tid="t23d", entity="E-BM", dimension="通知状态",
        frm="待审核", to="退回", action="作业指导书退回", role="策划人员",
        preconditions=[
            precond(text="通知状态为待审核", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "待审核")),
            precond(text="作业指导书审核结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["通知状态变更为退回（作业指导书编制退回）"],
        traits=["branch", "audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e21b；①'退回'→backward；分支维度=项目类型，测量审核路径；P1回退"},
    )
    m.add_trans(
        tid="t23e", entity="E-BM", dimension="通知状态",
        frm="退回", to="待审核", action="作业指导书重新提交", role="策划人员",
        preconditions=[
            precond(text="通知状态为退回", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "退回")),
        ],
        expected_results=["通知状态变更为待审核"],
        traits=["branch", "audit"], direction="forward", priority="P1",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e21c；③序判frm先于to；inferred：退回后修改重新提交，状态机闭环；分支维度=项目类型，测量审核路径；P1"},
    )
    m.add_trans(
        tid="t23f", entity="E-BM", dimension="通知状态",
        frm="已审核", to="已发送", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="通知状态为已审核", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "已审核")),
        ],
        expected_results=["通知状态变更为已发送/待确认（测量审核路径合并能力验证主流程）"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e21d；③序判frm先于to；分支维度=项目类型，测量审核路径合并点；19.2流程表'能力验证预通知'行预通知状态列由已审核变已发送/待确认；P0主流程"},
    )
    m.add_trans(
        tid="t24", entity="E-BM", dimension="通知状态",
        frm="已发送", to="已确认", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="通知状态为已发送", ptype="state_ref",
                    ref=state_ref("E-BM", "通知状态", "已发送")),
        ],
        expected_results=["预通知确认为已收到，通知状态变更为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e11b；③序判frm先于to；'已确认'inferred（19.3枚举无，按流程表'已确认'推导）；P0主流程"},
    )

    # ─ E-BM 报名记录 - 报名记录样品状态维度 ─
    m.add_trans(
        tid="t25", entity="E-BM", dimension="报名记录样品状态",
        frm=None, to="待发样", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="项目样品状态为已核查", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已核查")),
        ],
        expected_results=["报名记录样品状态落入待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e10b；⓪frm=None→forward；创建转换；P0主流程"},
    )
    m.add_trans(
        tid="t26", entity="E-BM", dimension="报名记录样品状态",
        frm="待发样", to="待收样", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="报名记录样品状态为待发样", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录样品状态", "待发样")),
        ],
        expected_results=["报名记录样品状态变更为待收样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e11c；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t26b", entity="E-BM", dimension="报名记录样品状态",
        frm="待收样", to="已收样", action="确认收样", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为待收样", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录样品状态", "待收样")),
        ],
        expected_results=["报名记录样品状态变更为已收样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.4能力验证参加者工作流程分析",
        note={"comment": "inferred：参加者接收样品后确认收样，状态机闭环；依据19.4'接收样品'；P0主流程"},
    )
    m.add_trans(
        tid="t26c", entity="E-BM", dimension="报名记录样品状态",
        frm="已收样", to="已确认", action="样品测试确认", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为已收样", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录样品状态", "已收样")),
        ],
        expected_results=["报名记录样品状态变更为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.4能力验证参加者工作流程分析",
        note={"comment": "inferred：参加者测试后确认样品，状态机闭环；依据19.4'接收样品'后续确认；P0主流程"},
    )

    # ─ E-BM 报名记录 - 费用状态维度 ─
    m.add_trans(
        tid="t27", entity="E-BM", dimension="费用状态",
        frm=None, to="待缴费", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["费用状态落入待缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e03c；⓪frm=None→forward；创建转换；P0主流程"},
    )
    m.add_trans(
        tid="t28", entity="E-BM", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="费用状态为待缴费", ptype="state_ref",
                    ref=state_ref("E-BM", "费用状态", "待缴费")),
        ],
        expected_results=["费用状态变更为已缴费", "可多次进行付款操作（不对付款金额进行校验限制）"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.5.2.1已报名项目增加多次付款功能",
        note={"comment": "源自 e07；③序判frm先于to；P0主流程；多次付款不改费用状态"},
    )

    # ─ E-BM 报名记录 - 发票状态维度 ─
    m.add_trans(
        tid="t29", entity="E-BM", dimension="发票状态",
        frm=None, to="待开票", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["发票状态落入待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e03d；⓪frm=None→forward；创建转换；P0主流程"},
    )
    m.add_trans(
        tid="t30", entity="E-BM", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务人员",
        preconditions=[
            precond(text="发票状态为待开票", ptype="state_ref",
                    ref=state_ref("E-BM", "发票状态", "待开票")),
        ],
        expected_results=["发票状态变更为已开票", "生成发票文件"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e08；③序判frm先于to；P0主流程；分支维度=发票类型（电子专票/电子普票）"},
    )

    # ─ E-BM 报名记录 - 缴费通知单状态维度 ─
    m.add_trans(
        tid="t31", entity="E-BM", dimension="缴费通知单状态",
        frm=None, to="未发送", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["缴费通知单状态落入未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e03e；⓪frm=None→forward；创建转换；'缴费通知单状态'inferred（19.3无，按流程表推导）"},
    )
    m.add_trans(
        tid="t32", entity="E-BM", dimension="缴费通知单状态",
        frm="未发送", to="已发送", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="缴费通知单状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BM", "缴费通知单状态", "未发送")),
            precond(text="报名记录状态为报名成功", ptype="state_ref",
                    ref=state_ref("E-BM", "报名记录状态", "报名成功")),
        ],
        expected_results=["缴费通知单状态变更为已发送"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e04b；③序判frm先于to；P0主流程"},
    )

    # ─ E-SYS 实验室 - 实验室状态维度 ─
    m.add_trans(
        tid="t33", entity="E-SYS", dimension="实验室状态",
        frm=None, to="待审核", action="实验室新增", role="机构",
        preconditions=[],
        expected_results=["实验室状态落入待审核", "需经管理用户审核通过后方可用于项目报名"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.3.1实验室信息",
        note={"comment": "源自 e22；⓪frm=None→forward；创建转换；P0主流程"},
    )
    m.add_trans(
        tid="t34", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="待审核", action="实验室修改", role="机构",
        preconditions=[
            precond(text="实验室状态为启用", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变更为待审核"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="20.4.1.3实验室修改",
        note={"comment": "源自 e23；③序判frm先于to；P1修改后重新审核"},
    )
    m.add_trans(
        tid="t34b", entity="E-SYS", dimension="实验室状态",
        frm="退回修改", to="待审核", action="实验室修改", role="机构",
        preconditions=[
            precond(text="实验室状态为退回修改", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "退回修改")),
        ],
        expected_results=["实验室状态变更为待审核"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="20.4.1.3实验室修改",
        note={"comment": "源自 e23b；③序判frm先于to；inferred：退回后修改重新提交，状态机闭环；P1"},
    )
    # 分支转换：实验室审核通过 vs 退回修改（路径分歧型）
    m.add_trans(
        tid="t35", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核通过", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态变更为启用", "为当前数据生成该数据的快照记录"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e24；路径分歧：Step 2 value=通过 指向本条；③序判frm先于to；P0主流程"},
    )
    m.add_trans(
        tid="t35b", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="退回修改", action="实验室审核退回", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
            precond(text="必须填写审核意见", ptype="constraint"),
        ],
        expected_results=["实验室状态变更为退回修改"],
        traits=["branch", "audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e25；路径分歧：Step 2 value=退回修改 指向本条；①'退回'→backward；P1回退"},
    )
    m.add_trans(
        tid="t36", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="停用", action="实验室停用", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为启用", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变更为停用", "状态立即改变，列表刷新"],
        traits=["audit"], direction="lateral", priority="P1",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e26；①'停用'→lateral；P1挂起非主路径"},
    )
    m.add_trans(
        tid="t37", entity="E-SYS", dimension="实验室状态",
        frm="停用", to="启用", action="实验室启用", role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为停用", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变更为启用", "状态立即改变，列表刷新"],
        traits=["audit"], direction="resume", priority="P1",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e27；①'启用'→resume；P1恢复非主路径"},
    )

    # ─ E-BZK 标准库 - 标准库状态维度 ─
    m.add_trans(
        tid="t38", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理人员",
        preconditions=[],
        expected_results=["标准库创建并落入启用状态"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.4.2.2新增标准库",
        note={"comment": "源自 e28；⓪frm=None→forward；创建转换；P0主流程"},
    )
    m.add_trans(
        tid="t39", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="停用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库状态为启用", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态变更为停用", "停用的标准库在项目创建等环节不可被选择"],
        traits=["audit"], direction="lateral", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e29；①'停用'→lateral；P1挂起"},
    )
    m.add_trans(
        tid="t40", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="启用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库状态为停用", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态变更为启用"],
        traits=["audit"], direction="resume", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e30；①'启用'→resume；P1恢复"},
    )

    # ─ E-PJ 评价记录 - 评价状态维度 ─
    m.add_trans(
        tid="t41", entity="E-PJ", dimension="评价状态",
        frm=None, to="待评价", action="测试项目评价细则完善", role="评价组长",
        preconditions=[
            precond(text="项目存在评价人员配置", ptype="event_ref"),
        ],
        expected_results=["评价记录创建并落入待评价状态", "评价项目及评价细则完善后保存"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.1测试项目评价细则完善",
        note={"comment": "源自 e31；⓪frm=None→forward；创建转换；状态'待评价'inferred；P0主流程"},
    )
    m.add_trans(
        tid="t42", entity="E-PJ", dimension="评价状态",
        frm="待评价", to="评价中", action="协同评价", role="评价人员",
        preconditions=[
            precond(text="评价状态为待评价", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "待评价")),
        ],
        expected_results=["评价状态变更为评价中", "评价人员只能对自己的评价结果进行修改"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"comment": "源自 e32；③序判frm先于to；状态'评价中'inferred；P0主流程"},
    )
    m.add_trans(
        tid="t43", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="已确认", action="评价确认", role="评价组长",
        preconditions=[
            precond(text="评价状态为评价中", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变更为已确认，项目评价状态关闭", "当前结果正式提交为项目的最终评价结果"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e33；③序判frm先于to；状态'已确认'inferred；'已确认'为终态；P0主流程"},
    )
    m.add_trans(
        tid="t44", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="待评价", action="评价退回修改", role="评价组长",
        preconditions=[
            precond(text="评价状态为评价中", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变更为待评价", "当前评价结果保存为历史结果，开启下一轮评价"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e34；①'退回'→backward；P1回退非主路径"},
    )

    # ─ E-JK 缴费记录 - 缴费状态维度 ─
    m.add_trans(
        tid="t45", entity="E-JK", dimension="缴费状态",
        frm=None, to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录费用状态为待缴费或已缴费", ptype="constraint",
                    note={"comment": "支持多次付款；状态值'待缴费或已缴费'含两个值无法定位单一状态，降级 constraint"}),
        ],
        expected_results=["缴费记录创建并落入已缴费状态", "可多次进行付款操作"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.5.2.1已报名项目增加多次付款功能",
        note={"comment": "源自 e07c；⓪frm=None→forward；创建转换；状态'已缴费'inferred；P0主流程"},
    )
    m.add_trans(
        tid="t46", entity="E-JK", dimension="缴费状态",
        frm="已缴费", to="已退款", action="缴费单退款", role="财务人员",
        preconditions=[
            precond(text="缴费状态为已缴费", ptype="state_ref",
                    ref=state_ref("E-JK", "缴费状态", "已缴费")),
            precond(text="退款金额不能大于当前缴费金额", ptype="constraint"),
        ],
        expected_results=["缴费状态变更为已退款", "退款后更新项目费用为实际付款金额", "退款金额多次累加"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.10.2.3缴费单退款",
        note={"comment": "源自 e35；①'退款'语义回退→backward；状态'已退款'inferred；'已退款'为终态；P1回退"},
    )

    # ── 3.4 因果 ──
    # 报名审核通过 → 缴费通知单状态变更为已发送（显式：审核通过后发送缴费通知）
    m.add_causal(
        frm="E-BM", to="E-BM",
        desc="报名审核通过后，系统发送缴费通知单，缴费通知单状态由未发送变更为已发送",
        trigger="报名审核通过", trigger_source="desc",
        evidence_transitions=["t11", "t32"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：审核通过直接致缴费通知单发送，无须中间操作；显式句式见19.1流程表'报名审核'行缴费通知单列由未发送变已发送"},
    )
    # 项目状态变更 → 报名记录状态变更（编制结果报告使报名记录进入报告/证书审核中）
    m.add_causal(
        frm="E-XM", to="E-BM",
        desc="编制结果报告使项目状态由进行中变更为报告审核中，同时报名记录状态由结果已提交变更为报告/证书审核中",
        trigger="编制结果报告", trigger_source="desc",
        evidence_transitions=["t04", "t18"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：编制结果报告同时推进项目与报名记录状态；显式句式见19.1报告编制和结果通知阶段"},
    )
    # 发放结果报告和证书 → 项目进入已结束
    m.add_causal(
        frm="E-BM", to="E-XM",
        desc="报名记录报告/证书已发布后，项目状态变更为已结束",
        trigger="发放结果报告和证书", trigger_source="desc",
        evidence_transitions=["t21", "t05"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：发放后项目完结；显式句式见19.1'结束：流程的终点'"},
    )
    # 样品核查 → 报名记录样品状态落入待发样
    m.add_causal(
        frm="E-XM", to="E-BM",
        desc="项目样品核查完成后，报名记录样品状态落入待发样",
        trigger="样品核查", trigger_source="desc",
        evidence_transitions=["t07", "t25"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "Q1通过：核查后报名记录样品准备发样；推导依据19.1流程表'样品核查'行"},
    )
    # 评价确认 → 报名记录报告/证书审核中可以进入发布
    m.add_causal(
        frm="E-PJ", to="E-BM",
        desc="评价记录确认后，报名记录可进入报告/证书发布流程",
        trigger="评价确认", trigger_source="desc",
        evidence_transitions=["t43"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "Q3判：评价确认是下级完成标志，但需上级（报告编制）操作才推进；标记为因果因评价结果是报告编制的输入"},
    )

    # ===== 4. 约束 =====

    # ── 4.1 invalid（文档明文禁止的状态转换）──
    m.add_invalid(
        iid="i01", entity="E-JK",
        frm="已退款", to="已缴费",
        reason="缴费单退款后状态为终态，不可逆；20.10.2.3退款金额累加处理，不恢复",
        source_ref="20.10.2.3缴费单退款",
    )
    m.add_invalid(
        iid="i02", entity="E-BZK",
        frm="停用", to="停用",
        reason="停用状态标准库不可再次停用；20.4.2.5停用按钮仅在启用状态显示",
        source_ref="20.4.2.5停用/启用标准库",
    )

    # ── 4.2 XC（跨实体约束）──
    # 镜像：报名记录.费用状态=待缴费 → 项目.项目状态=报名中（项目发布后才能报名缴费）
    m.add_xc(
        xid="x01", source_entity="E-XM", source_transition="t02",
        source_state="报名中", target_entity="E-BM",
        target_dimension="费用状态", target_condition="待缴费",
        desc="项目状态为报名中时，报名记录费用状态才能落入待缴费",
        source_ref="19.1实施阶段",
        target_transition="t27",
        xc_source="镜像",
    )
    # 镜像：报名记录.报名记录状态=报名成功 → 通知状态可由未发送变更为已发送
    m.add_xc(
        xid="x02", source_entity="E-BM", source_transition="t11",
        source_state="报名成功", target_entity="E-BM",
        target_dimension="通知状态", target_condition="未发送",
        desc="报名成功后才发送能力验证预通知，通知状态由未发送变更",
        source_ref="19.1实施阶段",
        target_transition="t23",
        xc_source="镜像",
    )
    # 联动：实验室审核通过 → 实验室可用于项目报名（报名前置条件）
    m.add_xc(
        xid="x03", source_entity="E-SYS", source_transition="t35",
        source_state="启用", target_entity="E-BM",
        target_dimension="报名记录状态", target_condition="报名待审核",
        desc="实验室状态为启用时，参加者报名后报名记录状态才能落入报名待审核",
        source_ref="20.3.1实验室信息",
        target_transition="t10",
        xc_source="联动",
    )
    # 4.5判：标准库状态=停用 → 不可在项目创建环节被选择（约束）
    m.add_xc(
        xid="x04", source_entity="E-BZK", source_transition="t39",
        source_state="停用", target_entity="E-XM",
        target_dimension="项目状态", target_condition="待开始",
        desc="停用的标准库在项目创建等环节不可被选择（承载约束：b05）",
        source_ref="20.4.2.5停用/启用标准库",
        target_transition=None,
        xc_source="4.5判",
    )
    # 4.5判：项目状态≠已结束 → 不可进行文件整理（约束）
    m.add_xc(
        xid="x05", source_entity="E-XM", source_transition="t05",
        source_state="已结束", target_entity="E-XM",
        target_dimension="项目状态", target_condition="已结束",
        desc="仅对已结束的项目记录提供文件整理按钮（承载约束：b33）",
        source_ref="20.5.1.1文件整理",
        target_transition=None,
        xc_source="4.5判",
    )

    # ── 4.3 BR（业务规则）──
    # 实验室相关
    m.add_br(
        bid="b01", category="validation",
        desc="实验室状态为待审核时，操作列才显示审核按钮",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'才'；category判有效性校验"},
    )
    m.add_br(
        bid="b02", category="validation",
        desc="实验室审核退回修改时，必须填写审核意见；审核结果为通过时，审核意见可以为空",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'必须'；category判有效性校验；分支维度=审核结果", "branch_dimension": "审核结果"},
    )
    m.add_br(
        bid="b03", category="computation",
        desc="实验室审核通过时，为当前数据生成该数据的快照记录",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'时'；category判计算衍生（含留痕/审计日志生成）"},
    )
    m.add_br(
        bid="b04", category="validation",
        desc="机构新增或修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-SYS", "E-BM"], source_ref="20.3.1实验室信息",
        signal_type="restrictive",
        note={"comment": "signal_type命中'需'、'后方可'；category判有效性校验；constrained_entity=E-SYS（实验室增删改被门禁）"},
        constrained_entity="E-SYS",
    )
    # 标准库相关
    m.add_br(
        bid="b05", category="validation",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"], source_ref="20.4.2.5停用/启用标准库",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不可'；category判有效性校验；constrained_entity=E-BZK（标准库被门禁）；分支维度=项目类型"},
        constrained_entity="E-BZK",
    )
    m.add_br(
        bid="b06", category="validation",
        desc="含有子项的测试项记录不允许删除",
        entities_involved=["E-CSX"], source_ref="20.4.2.10删除测试项",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不允许'；category判有效性校验"},
    )
    # 项目/报名相关
    m.add_br(
        bid="b07", category="validation",
        desc="未结束的项目才可以进行消息发送",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'才'；category判有效性校验；分支维度=项目类型", "branch_dimension": "项目类型"},
    )
    m.add_br(
        bid="b08", category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'；category判有效性校验；分支维度=项目类型"},
    )
    m.add_br(
        bid="b09", category="validation",
        desc="项目批量处理时，只有已上传对应文件且未提交审核的记录才可以被选定",
        entities_involved=["E-BM"], source_ref="20.5.1.3项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'才'；category判有效性校验；分支维度=项目类型"},
    )
    m.add_br(
        bid="b10", category="validation",
        desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"], source_ref="20.5.1.6默认填充技术主管实验室负责人授权签字人",
        signal_type="restrictive",
        note={"comment": "signal_type命中'如果...则'；category判有效性校验；分支维度=项目类型"},
    )
    m.add_br(
        bid="b11", category="validation",
        desc="已报名项目增加多次付款功能，不对付款金额进行校验限制",
        entities_involved=["E-BM", "E-JK"], source_ref="20.5.2.1已报名项目增加多次付款功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不'；category判有效性校验；分支维度=项目类型；constrained_entity=E-JK（缴费记录增删改被门禁）"},
        constrained_entity="E-JK",
    )
    # 系统行为（无状态落点，落点判定③出口）── 证书到期提醒
    m.add_br(
        bid="b12", category="notification",
        desc="系统在每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送给项目管理员；提醒标题为'证书到期提醒'，提醒内容为'您证书编号为xxxx的证书将于2025-01-01到期，请知悉'",
        entities_involved=["E-ZS"], source_ref="20.5.2.3增加证书到期前30天提醒功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'每天上午9点'；category判通知触发；无状态落点，不入台账/operations；分支维度=项目类型（能力验证路径）"},
    )
    m.add_br(
        bid="b13", category="notification",
        desc="系统在每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送给项目管理员；提醒标题为'证书到期提醒'，提醒内容为'您证书编号为xxxx的证书将于2025-01-01到期，请知悉'",
        entities_involved=["E-ZS"], source_ref="20.6.2.3增加证书到期前30天提醒功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'每天上午9点'；category判通知触发；无状态落点，不入台账/operations；分支维度=项目类型（测量审核路径）"},
    )
    # 操作节点短信通知
    m.add_br(
        bid="b14", category="notification",
        desc="管理人员对用户报名项目操作后使用短信方式对用户进行通知；报名审核通过时发送'您xxx项目的报名信息审核通过，请知悉'；报名审核退回修改时发送'您xxx项目的报名信息审核未通过，请知悉'；发样时发送'您xxxx项目的样品已发出，请知悉'；测试结果审核通过时发送'您xxxx项目的测试报告审核通过，请知悉'；测试结果审核退回时发送'您xxxx项目测试报告审核未通过，请知悉'；结果通知单发布时发送'您xxx项目的结果通知单已发布，请知悉'",
        entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知",
        signal_type="restrictive",
        note={"comment": "signal_type命中'后'；category判通知触发；无状态落点；分支维度=项目类型（能力验证路径）"},
    )
    m.add_br(
        bid="b15", category="notification",
        desc="管理人员对用户报名项目操作后使用短信方式对用户进行通知；报名审核通过时发送'您xxx项目的报名信息审核通过，请知悉'；报名审核退回修改时发送'您xxx项目的报名信息审核未通过，请知悉'；发样时发送'您xxxx项目的样品已发出，请知悉'；测试结果审核通过时发送'您xxxx项目的测试报告审核通过，请知悉'；测试结果审核退回时发送'您xxxx项目测试报告审核未通过，请知悉'；结果通知单发布时发送'您xxx项目的结果通知单已发布，请知悉'",
        entities_involved=["E-BM"], source_ref="20.6.3.2操作节点增加用户短信通知",
        signal_type="restrictive",
        note={"comment": "signal_type命中'后'；category判通知触发；无状态落点；分支维度=项目类型（测量审核路径）"},
    )
    # 任务创建短信通知
    m.add_br(
        bid="b16", category="notification",
        desc="用户通过表单或审核一个已存在的任务，生成一个新的审核任务时，系统发送短信通知相关负责人；短信内容为'您有一个新的xxx审核任务，请及时处理'，xxx为审核类型的名称",
        entities_involved=["E-BM"], source_ref="20.9.1.3增加任务提醒",
        signal_type="restrictive",
        note={"comment": "signal_type命中'时'；category判通知触发；无状态落点"},
    )
    # 财务相关
    m.add_br(
        bid="b17", category="validation",
        desc="缴费单退款金额不能大于当前缴费金额",
        entities_involved=["E-JK"], source_ref="20.10.2.3缴费单退款",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'；category判有效性校验"},
    )
    m.add_br(
        bid="b18", category="computation",
        desc="缴费单退款金额多次退款做累加处理；实际付款=付款金额-退款金额；退款后更新项目费用为实际付款金额",
        entities_involved=["E-JK", "E-BM"], source_ref="20.10.2.3缴费单退款",
        constrained_entity="E-JK",
        signal_type="restrictive",
        note={"comment": "signal_type命中'累计'、'按X计算'；category判计算衍生；"
                          "多实体取操作对象缴费单为受约束实体"},
    )
    m.add_br(
        bid="b19", category="display",
        desc="缴费记录列表中退款金额使用红色字体且大于0时显示",
        entities_involved=["E-JK"], source_ref="20.10.2.3缴费单退款",
        signal_type="display",
        note={"comment": "signal_type命中'显示'；category判信息展示"},
    )
    m.add_br(
        bid="b20", category="validation",
        desc="发票上传功能支持多次分批上传；表单提交后生效，点击文件地址后的'x'可以移除文件",
        entities_involved=["E-JK"], source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传",
        signal_type="usability",
        note={"comment": "signal_type命中'支持'；category判有效性校验（默认）"},
    )
    # 评价相关
    m.add_br(
        bid="b21", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"], source_ref="20.7.1.2协同评价",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只能'、'不能'；category判访问控制；role=评价人员", "role": "评价人员"},
    )
    m.add_br(
        bid="b22", category="computation",
        desc="评价结果确认页面客户列显示每组由评价人员的评价结果、参考值（各专家评分的均值）、得分；得分需要评价组长填写补充",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认",
        signal_type="computation",
        note={"comment": "signal_type命中'均值'；category判计算衍生"},
    )
    m.add_br(
        bid="b23", category="validation",
        desc="评价结果统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认",
        signal_type="restrictive",
        note={"comment": "signal_type命中'大于等于'、'小于'；category判有效性校验"},
    )
    m.add_br(
        bid="b24", category="authorization",
        desc="新建项目时第一个被选择的评价人员默认做为评价组长；评价组长可以在评价结果确认页面查看各评价人员的评价结果并对最终结果进行确认",
        entities_involved=["E-PJ"], source_ref="20.7项目列表",
        signal_type="restrictive",
        note={"comment": "signal_type命中'默认'；category判访问控制；role=评价组长", "role": "评价组长"},
    )
    # 信息发送记录
    m.add_br(
        bid="b25", category="authorization",
        desc="只有系统管理员和项目管理员可以查看信息发送记录",
        entities_involved=["E-XXJL"], source_ref="20.4.4.1信息发送记录",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只有'；category判访问控制；role=系统管理人员/项目管理员", "role": "系统管理人员"},
    )
    # 业务审核相关
    m.add_br(
        bid="b26", category="validation",
        desc="测量审核结果通知单审批流程将原来多个流程合并为一个流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-BM"], source_ref="20.9.1.1测量审核结果通知单审核流程优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'并'；category判有效性校验；分支维度=项目类型（测量审核路径）"},
    )
    m.add_br(
        bid="b27", category="computation",
        desc="系统内增加电子签章位置信息，当进行签章操作时自动代入此位置信息减少手动调整操作",
        entities_involved=["E-BM"], source_ref="20.9.1.2预置签章位置信息",
        signal_type="usability",
        note={"comment": "signal_type命中'自动'；category判计算衍生（自动填充）"},
    )
    m.add_br(
        bid="b28", category="validation",
        desc="用户在审批流程列表中勾选需要处理的任务，系统会根据任务节点的类型及内容判断当前节点是否可以被批量处理",
        entities_involved=["E-BM"], source_ref="20.9.1.4任务批量处理",
        signal_type="restrictive",
        note={"comment": "signal_type命中'会'；category判有效性校验"},
    )
    m.add_br(
        bid="b29", category="validation",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
        entities_involved=["E-BM"], source_ref="20.9.1.6增加自定义流程",
        signal_type="restrictive",
        note={"comment": "signal_type命中'若干'、'4个以内'；category判有效性校验（取值范围）"},
    )
    # 通知公告相关
    m.add_br(
        bid="b30", category="display",
        desc="对新旧通知内容进行区分显示；15天内发布的通知在内容前标注'new'标识，超过15天后此标识自动隐藏",
        entities_involved=["E-XXJL"], source_ref="20.2.1通知公告",
        signal_type="restrictive",
        note={"comment": "signal_type命中'15天内'、'超过15天'；category判信息展示"},
    )
    # 安全相关
    m.add_br(
        bid="b31", category="computation",
        desc="对关键操作实施留痕机制，系统将自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-XM", "E-BM", "E-SYS", "E-BZK", "E-JK"],
        source_ref="20.11.1.2安全性相关内容优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'自动'；category判计算衍生（含留痕/审计日志生成）；constrained_entity代表实体=E-XM"},
        constrained_entity="E-XM",
    )
    # 文件整理前置条件（承载 x05）
    m.add_br(
        bid="b33", category="validation",
        desc="仅对已结束的项目记录提供文件整理按钮",
        entities_involved=["E-XM"], source_ref="20.5.1.1文件整理",
        signal_type="restrictive",
        note={"comment": "signal_type命中'仅'；category判有效性校验；承载 XC x05"},
    )
    # 评价方式分支承载
    m.add_br(
        bid="b34", category="display",
        desc="项目评价支持分值和权重两种评价方式；评价表单字段名称显示为'分值/权重'",
        entities_involved=["E-PJ"], source_ref="20.7项目列表",
        signal_type="display",
        note={"comment": "signal_type命中'显示'；category判信息展示；分支维度=评价方式", "branch_dimension": "评价方式"},
    )
    # 发票类型分支承载
    m.add_br(
        bid="b35", category="validation",
        desc="缴费信息查询支持按发票类型筛选，选项包括电子专票、电子普票",
        entities_involved=["E-JK"], source_ref="20.10.1.1缴费信息查询与管理",
        signal_type="restrictive",
        note={"comment": "signal_type命中'选项包括'；category判有效性校验（取值范围）；分支维度=发票类型", "branch_dimension": "发票类型"},
    )
    # 性能/兼容
    m.add_br(
        bid="b32", category="validation",
        desc="平台应支持至少300个同时在线用户数；并发100时，每个页面响应时间不超过5秒；单次报名操作成功率应达到95%以上",
        entities_involved=["E-XM", "E-BM"], source_ref="3.4性能要求",
        constrained_entity="E-XM",
        signal_type="restrictive",
        note={"comment": "signal_type命中'至少'、'不超过'、'以上'；category判有效性校验；"
                          "代表实体（平台性能要求，非实体门禁）"},
    )

    # ===== 3.3 自检（前向引用回填 / crud 回填 / 回写）=====
    # Step 2 target_transition 回填为纯 tid
    # 已在 branches 中以语义描述形式写入，回填如下（通过 BranchDim 的内部回填机制；
    # 此处仅做簿记说明，无新增调用）：
    # - 项目类型/能力验证 → t02（项目立项与发布转换）
    # - 项目类型/测量审核 → t02b（测量审核受理报名转换）
    # - 评价方式/分值 → t42（协同评价转换）
    # - 评价方式/权重 → t42（协同评价转换，共用）
    # - 发票类型/电子专票 → t30（发票开具转换）
    # - 发票类型/电子普票 → t30（发票开具转换，共用）
    # - 审核结果/通过 → t35（实验室审核通过转换）
    # - 审核结果/退回修改 → t35b（实验室审核退回转换）

    # crud 回填：op 对应的转换标签（note.comment 回填）
    # - E-XM.新增项目 → t01；E-XM.消息发送 → t02（流程触发）
    # - E-BM.上传付款单 → t28；E-BM.提交结果报告 → t15
    # - E-SYS.新增实验室信息 → t33；E-SYS.审核实验室 → t35/t35b
    # - E-BZK.新增标准库 → t38；E-BZK.停用标准库 → t39；E-BZK.启用标准库 → t40
    # - E-PJ.完善评价项目 → t41；E-PJ.结果确认 → t43
    # - E-JK.缴费单退款 → t46
    # （回填已通过 op 的 expected_results 与 trans 的 expected_results 对齐体现，不重复 note）

    return m
