"""网数中心能力验证服务平台升级维护项目-需求分析与设计1116 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116",
        document_scope="能力验证/测量审核主流程、实验室与标准库管理、项目评价、业务审核、财务缴费及证书到期提醒等状态相关模块；非功能性需求（§3/§8/§21）、纯统计查询模块（§20.8）不入台账",
    )

    # ===== 事件台账（§2）=====
    # 能力验证主流程事件（§19.1 + §19.3）
    # e01–e05：E-XM 项目状态
    m.add_event("e01", entity="E-XM", dimension="项目状态", action="设计方案编制",
                actor="策划人员", precondition="初始", consequence="待开始",
                source_ref="19.1方案设计阶段；19.3项目状态分析")
    m.add_event("e02", entity="E-XM", dimension="项目状态", action="能力验证计划发布",
                actor="项目管理员", precondition="待开始", consequence="报名中",
                source_ref="19.1实施阶段")
    m.add_event("e03", entity="E-XM", dimension="项目状态", action="报名截止进入实施",
                actor="system", precondition="报名中", consequence="进行中",
                source_ref="19.3项目状态分析")
    m.add_event("e04", entity="E-XM", dimension="项目状态", action="进入报告编制阶段",
                actor="system", precondition="进行中", consequence="报告审核中",
                source_ref="19.3项目状态分析；19.1报告编制和结果通知")
    m.add_event("e05", entity="E-XM", dimension="项目状态", action="发放结果报告和证书",
                actor="项目管理员", precondition="报告审核中；E-BMJL.报告/证书已发布",
                consequence="已结束",
                source_ref="19.1报告编制和结果通知；19.3项目状态分析")

    # e06–e10：E-BMJL 报名记录状态（创建 + 报名分支）
    m.add_event("e06", entity="E-BMJL", dimension="报名记录状态", action="参加者报名",
                actor="能力验证参加者",
                precondition="E-XM.报名中", consequence="报名待审核",
                source_ref="19.1实施阶段-报名行")
    m.add_event("e07", entity="E-BMJL", dimension="报名记录状态", action="参加者报名撤销",
                actor="能力验证参加者",
                precondition="报名待审核", consequence="已撤销",
                source_ref="19.1实施阶段-报名行（已撤销分支）")
    m.add_event("e08", entity="E-BMJL", dimension="报名记录状态", action="报名审核通过",
                actor="项目管理员",
                precondition="报名待审核", consequence="报名成功",
                source_ref="19.1实施阶段-报名审核行（成功分支）")
    m.add_event("e09", entity="E-BMJL", dimension="报名记录状态", action="报名审核退回",
                actor="项目管理员",
                precondition="报名待审核", consequence="报名退回",
                source_ref="19.1实施阶段-报名审核行（退回分支）")
    m.add_event("e10", entity="E-BMJL", dimension="报名记录状态", action="退回后重新提交",
                actor="能力验证参加者",
                precondition="报名退回", consequence="报名待审核",
                source_ref="19.1实施阶段-报名审核行（隐含重报）")

    # e11–e13：结果相关
    m.add_event("e11", entity="E-BMJL", dimension="报名记录状态", action="预通知后进入结果提交阶段",
                actor="system",
                precondition="报名成功；E-YT.已发送", consequence="结果待提交",
                source_ref="19.1实施阶段-能力验证预通知行")
    m.add_event("e12", entity="E-BMJL", dimension="报名记录状态", action="参加者提交结果",
                actor="能力验证参加者",
                precondition="结果待提交", consequence="结果已提交",
                source_ref="19.1实施阶段-参加者测试与结果提交行")
    m.add_event("e13", entity="E-BMJL", dimension="报名记录状态", action="结果退回修改",
                actor="项目管理员",
                precondition="结果已提交", consequence="结果退回修改",
                source_ref="19.1报告编制和结果通知-结果报告回收行（退回分支）")

    # e14–e17：报告/证书审核阶段
    m.add_event("e14", entity="E-BMJL", dimension="报名记录状态", action="编制结果报告",
                actor="策划人员",
                precondition="结果已提交", consequence="报告/证书审核中",
                source_ref="19.1报告编制和结果通知-编制结果报告行")
    m.add_event("e15", entity="E-BMJL", dimension="报名记录状态", action="技术主管审核通过",
                actor="技术主管",
                precondition="报告/证书审核中", consequence="报告/证书审核中",
                source_ref="19.1报告编制和结果通知-技术主管审核报告行")
    m.add_event("e16", entity="E-BMJL", dimension="报名记录状态", action="授权签字人/实验室负责人批准",
                actor="授权签字人",
                precondition="报告/证书审核中", consequence="报告/证书审核中",
                source_ref="19.1报告编制和结果通知-报告结果通知单批准行")
    m.add_event("e17", entity="E-BMJL", dimension="报名记录状态", action="发放结果报告和证书",
                actor="项目管理员",
                precondition="报告/证书审核中", consequence="报告/证书已发布",
                source_ref="19.1报告编制和结果通知-发放结果报告和证书行")

    # e18–e20：E-YP 项目样品状态
    m.add_event("e18", entity="E-YP", dimension="样品状态", action="样品制备并登记",
                actor="样品制备人员",
                precondition="E-XM.报名中", consequence="待核查",
                source_ref="19.1实施阶段-缴费行（样品状态首次出现待核查）；19.3样品状态")
    m.add_event("e19", entity="E-YP", dimension="样品状态", action="样品核查",
                actor="样品管理员",
                precondition="待核查", consequence="已核查",
                source_ref="19.1实施阶段-样品核查行；19.3样品状态")
    m.add_event("e20", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="能力验证参加者",
                precondition="已核查", consequence="已还样",
                source_ref="19.1实施阶段-参加者测试与结果提交行（已还样分支）")
    m.add_event("e20b", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交（无需还样分支）",
                actor="能力验证参加者",
                precondition="已核查", consequence="无需还样",
                source_ref="19.1实施阶段-参加者测试与结果提交行（无需还样分支，inferred状态）")

    # e21：E-BMYP 报名记录样品状态
    m.add_event("e21", entity="E-BMYP", dimension="报名记录样品状态", action="样品发放",
                actor="样品管理员",
                precondition="待发样", consequence="已确认",
                source_ref="19.1实施阶段-样品发放行；19.3报名记录样品状态")

    # e22–e24：E-YT 预通知状态
    m.add_event("e22", entity="E-YT", dimension="预通知状态", action="能力验证计划发布预通知初始化",
                actor="system",
                precondition="E-XM.报名中", consequence="未发送",
                source_ref="19.1实施阶段-能力验证计划发布行（预通知状态列未发送）")
    m.add_event("e23", entity="E-YT", dimension="预通知状态", action="能力验证预通知发送",
                actor="项目管理员",
                precondition="未发送", consequence="已发送",
                source_ref="19.1实施阶段-能力验证预通知行（已发送分支）")
    m.add_event("e24", entity="E-YT", dimension="预通知状态", action="预通知待确认",
                actor="能力验证参加者",
                precondition="已发送", consequence="待确认",
                source_ref="19.1实施阶段-能力验证预通知行（待确认分支）")

    # e25–e28：E-JFTZ 缴费通知单、E-FY 费用状态、E-FP 发票状态
    m.add_event("e25", entity="E-JFTZ", dimension="缴费通知单状态", action="报名创建缴费通知单",
                actor="system",
                precondition="E-BMJL.报名待审核", consequence="未发送",
                source_ref="19.1实施阶段-报名行（缴费通知单列）")
    m.add_event("e26", entity="E-JFTZ", dimension="缴费通知单状态", action="报名审核后发送缴费通知",
                actor="system",
                precondition="未发送；E-BMJL.报名成功", consequence="已发送",
                source_ref="19.1实施阶段-报名审核行（缴费通知单列已发送）")
    m.add_event("e27", entity="E-FY", dimension="费用状态", action="报名创建费用记录",
                actor="system",
                precondition="E-BMJL.报名待审核", consequence="待缴费",
                source_ref="19.1实施阶段-报名行（费用状态列）")
    m.add_event("e28", entity="E-FY", dimension="费用状态", action="参加者缴费",
                actor="能力验证参加者",
                precondition="待缴费", consequence="已缴费",
                source_ref="19.1实施阶段-缴费行")
    m.add_event("e29", entity="E-FP", dimension="发票状态", action="报名创建发票记录",
                actor="system",
                precondition="E-BMJL.报名待审核", consequence="待开票",
                source_ref="19.1实施阶段-报名行（发票状态列）")
    m.add_event("e30", entity="E-FP", dimension="发票状态", action="发票开具",
                actor="财务管理人员",
                precondition="待开票", consequence="已开票",
                source_ref="19.1实施阶段-发票开具行")

    # 实验室管理事件（§20.4.1）
    m.add_event("e31", entity="E-LAB", dimension="实验室状态", action="机构提交实验室信息",
                actor="能力验证参加者",
                precondition="初始", consequence="待审核",
                source_ref="20.3.1实验室信息；20.4.1.2实验室审核")
    m.add_event("e32", entity="E-LAB", dimension="实验室状态", action="审核通过",
                actor="系统管理人员",
                precondition="待审核", consequence="启用",
                source_ref="20.4.1.2实验室审核（通过分支）")
    m.add_event("e33", entity="E-LAB", dimension="实验室状态", action="审核退回修改",
                actor="系统管理人员",
                precondition="待审核", consequence="已退回",
                source_ref="20.4.1.2实验室审核（退回修改分支）")
    m.add_event("e34", entity="E-LAB", dimension="实验室状态", action="机构修改后重新提交",
                actor="能力验证参加者",
                precondition="已退回", consequence="待审核",
                source_ref="20.4.1.3实验室修改；20.4.1.2隐含重审")
    m.add_event("e35", entity="E-LAB", dimension="实验室状态", action="停用实验室",
                actor="系统管理人员",
                precondition="启用", consequence="停用",
                source_ref="20.4.1.1实验室列表与查询（停用按钮）")
    m.add_event("e36", entity="E-LAB", dimension="实验室状态", action="启用实验室",
                actor="系统管理人员",
                precondition="停用", consequence="启用",
                source_ref="20.4.1.1实验室列表与查询（启用按钮）")

    # 标准库管理事件（§20.4.2）
    m.add_event("e37", entity="E-STD", dimension="标准库状态", action="新增标准库",
                actor="系统管理人员",
                precondition="初始", consequence="启用",
                source_ref="20.4.2.2新增标准库（状态含启用/停用，新增默认启用推断）")
    m.add_event("e38", entity="E-STD", dimension="标准库状态", action="停用标准库",
                actor="系统管理人员",
                precondition="启用", consequence="停用",
                source_ref="20.4.2.5停用/启用标准库")
    m.add_event("e39", entity="E-STD", dimension="标准库状态", action="启用标准库",
                actor="系统管理人员",
                precondition="停用", consequence="启用",
                source_ref="20.4.2.5停用/启用标准库")

    # 项目评价事件（§20.7）
    m.add_event("e40", entity="E-PJ", dimension="评价状态", action="评价组长完善测试项目及评价细则",
                actor="评价人员",
                precondition="E-BMJL.结果已提交", consequence="待评价",
                source_ref="20.7.1.1测试项目评价细则完善")
    m.add_event("e41", entity="E-PJ", dimension="评价状态", action="评价人员开始评价",
                actor="评价人员",
                precondition="待评价；E-BMJL.结果已提交", consequence="评价中",
                source_ref="20.7.1.2协同评价")
    m.add_event("e42", entity="E-PJ", dimension="评价状态", action="评价组长确认结果",
                actor="评价人员",
                precondition="评价中", consequence="已评价",
                source_ref="20.7.1.3评价确认（确认按钮）")
    m.add_event("e43", entity="E-PJ", dimension="评价状态", action="评价组长退回修改",
                actor="评价人员",
                precondition="评价中", consequence="待评价",
                source_ref="20.7.1.3评价确认（退回修改按钮，开启下一轮评价）")

    # 审批任务事件（§20.9）
    m.add_event("e44", entity="E-TASK", dimension="审核任务状态", action="提交审核任务",
                actor="项目管理员",
                precondition="初始", consequence="待审核",
                source_ref="20.9.1.3增加任务提醒；20.5.1.3项目批量操作（提交审核）")
    m.add_event("e45", entity="E-TASK", dimension="审核任务状态", action="审核通过",
                actor="审核人员",
                precondition="待审核", consequence="已审核",
                source_ref="20.9.1.4任务批量处理（同意分支）")
    m.add_event("e46", entity="E-TASK", dimension="审核任务状态", action="审核退回",
                actor="审核人员",
                precondition="待审核", consequence="已退回",
                source_ref="20.9.1.4任务批量处理（退回分支）")

    # 财务退款事件（§20.10.2.3）
    m.add_event("e47", entity="E-FY", dimension="费用状态", action="缴费单退款",
                actor="财务管理人员",
                precondition="已缴费", consequence="已缴费",
                source_ref="20.10.2.3缴费单退款（退款后实际付款=付款-退款；状态不变）")

    # 测量审核差异事件（§19.2 - 与能力验证不同的路径）
    m.add_event("e48", entity="E-XM", dimension="项目状态", action="测量审核受理报名",
                actor="项目管理员",
                precondition="初始", consequence="报名中",
                source_ref="19.2项目准备阶段-受理用户测量审核报名行（测量审核项目初始即为报名中）")
    m.add_event("e49", entity="E-YT", dimension="预通知状态", action="作业指导书审核",
                actor="技术主管",
                precondition="待审核", consequence="已审核",
                source_ref="19.2实施阶段-作业指导书编制行（已审核分支）")
    m.add_event("e50", entity="E-YT", dimension="预通知状态", action="作业指导书退回",
                actor="技术主管",
                precondition="待审核", consequence="退回",
                source_ref="19.2实施阶段-作业指导书编制行（退回分支）")

    # ===== Step 1: 实体 =====

    # 1.0 词表
    m.set_prohibition_config(config={
        "action_verbs": [
            "编制", "发布", "审核", "批准", "发放", "提交", "缴费", "开具",
            "核查", "发放", "测试", "回收", "评价", "统计", "确认", "退回",
            "撤销", "停用", "启用", "删除", "修改", "新增", "导入", "导出",
            "上传", "下载", "整理", "归档", "签发", "批准", "审批", "退款",
            "受理", "登记", "领用", "归还", "发送", "提醒",
        ],
        "prohibit_keywords": [
            "不允许", "不可以", "不得", "禁止",
            "不可同时为空",
            "不可删除含有子项",
            "未结束的项目不可",
            "停用的标准库不可被选择",
        ],
    })

    # 1.1 角色
    m.add_role(id="r01", name="实验室负责人", readonly=False)
    m.add_role(id="r02", name="技术主管", readonly=False)
    m.add_role(id="r03", name="授权签字人", readonly=False)
    m.add_role(id="r04", name="策划人员", readonly=False)
    m.add_role(id="r05", name="项目管理员", readonly=False)
    m.add_role(id="r06", name="样品制备人员", readonly=False)
    m.add_role(id="r07", name="样品管理员", readonly=False)
    m.add_role(id="r08", name="评价人员", readonly=False)
    m.add_role(id="r09", name="统计人员", readonly=False)
    m.add_role(id="r10", name="质量专员", readonly=False)
    m.add_role(id="r11", name="财务管理人员", readonly=False)
    m.add_role(id="r12", name="系统管理人员", readonly=False)
    m.add_role(id="r13", name="能力验证参加者", readonly=False)
    m.add_role(id="r14", name="审核人员", readonly=False)

    m.add_permission(role="r01", operations=[])
    m.add_permission(role="r02", operations=[])
    m.add_permission(role="r03", operations=[])
    m.add_permission(role="r04", operations=["file:编制报告", "file:编制通知单"])
    m.add_permission(role="r05", operations=["crud:项目管理", "file:任务通知书", "session:项目状态流转", "config:消息发送"])
    m.add_permission(role="r06", operations=["file:样品制备方案"])
    m.add_permission(role="r07", operations=["crud:样品管理", "file:核查记录表"])
    m.add_permission(role="r08", operations=["crud:评价", "file:评价表"])
    m.add_permission(role="r09", operations=["file:评价统计表"])
    m.add_permission(role="r10", operations=["file:报告统计数据"])
    m.add_permission(role="r11", operations=["crud:缴费记录", "file:发票", "crud:退款"])
    m.add_permission(role="r12", operations=["crud:用户角色", "crud:实验室", "crud:标准库", "crud:子领域", "crud:测试项", "crud:常用测试项", "query:信息发送记录"])
    m.add_permission(role="r13", operations=["crud:报名", "file:上传缴费证明", "file:上传结果报告", "file:上传报名表", "query:证书下载", "query:报告下载"])
    m.add_permission(role="r14", operations=["session:审批", "file:签章"])

    # 1.3/1.4 实体
    m.add_entity(
        id="E-XM", name="能力验证/测量审核项目",
        desc="能力验证或测量审核项目主对象，承载项目生命周期状态。来源 §19.1/§19.2/§19.3。",
        type="core",
        tags=["multi-state", "approvable", "collaborative"],
        attributes=[
            attr(name="项目编号", desc="项目唯一编号"),
            attr(name="项目名称", desc="项目名称"),
            attr(name="产品类型", desc="项目所属产品类型"),
            attr(name="项目类型", desc="能力验证或测量审核", is_config=True),
            attr(name="所属年度", desc="项目年度"),
            attr(name="项目费用", desc="项目应收金额"),
            attr(name="子领域", desc="项目所属子领域"),
            attr(name="依据标准", desc="项目依据标准"),
            attr(name="技术主管", desc="项目技术主管人员"),
            attr(name="实验室负责人", desc="项目实验室负责人"),
            attr(name="授权签字人", desc="项目授权签字人"),
            attr(name="监督员", desc="项目监督员（§20.5.1.5新增字段）"),
            attr(name="评价组长", desc="第一个被选择的评价人员默认作为评价组长"),
            attr(name="财务备注", desc="§20.10.2.1新增字段"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": [],
                "note": {"comment": "状态枚举源自 §19.3 项目状态分析；§19.1 流程表未在实施阶段显式标记 项目状态→进行中 的转换动作，e03/e04 为按 §19.3 枚举补的 inferred 转换"},
            },
        ],
        operations=[
            op(name="查询项目", category="query",
               expected_results=["按筛选条件分页返回项目列表"],
               source_ref="20.5.1项目管理",
               note={"role": ["r05", "r12"]}),
            op(name="新增项目", category="crud",
               expected_results=["创建项目并进入项目新增表单", "技术主管/实验室负责人/授权签字人字段在唯一候选人时默认填充", "评价人员列表首个被选者默认作为评价组长"],
               source_ref="20.5.1.5；20.5.1.6；20.7.1项目列表",
               note={"role": ["r05"]}),
            op(name="修改项目", category="crud",
               expected_results=["更新项目基础信息"],
               source_ref="20.5.1项目管理",
               note={"role": ["r05"]}),
            op(name="删除项目", category="crud",
               expected_results=["删除项目记录"],
               source_ref="20.2.3待办事项（能力验证项目删除）",
               note={"role": ["r05", "r12"]}),
            op(name="文件整理", category="file",
               expected_results=["为已结束项目开启归档任务", "归档完成后显示查看归档按钮"],
               source_ref="20.5.1.1文件整理",
               note={"role": ["r05"]}),
            op(name="机构代码导入", category="file",
               expected_results=["导入报名机构三方代码"],
               source_ref="20.5.1.2机构代码导入",
               note={"role": ["r05"]}),
            op(name="项目批量处理", category="ui",
               expected_results=["跳转到报名信息批量处理页面", "支持批量上传结果通知单/证书并提交审核"],
               source_ref="20.5.1.3项目批量操作",
               note={"role": ["r05"]}),
            op(name="消息发送", category="config",
               expected_results=["按选择方式向接收人发送消息", "未结束项目可发送"],
               source_ref="20.5.1.4优化消息发送功能",
               note={"role": ["r05"]}),
            op(name="导出项目通知书", category="file",
               expected_results=["导出含监督员字段的项目通知书"],
               source_ref="20.5.1.5项目新增表单增加监督员",
               note={"role": ["r05"]}),
            op(name="上传付款单", category="file",
               expected_results=["多次付款记录创建", "不校验付款金额限制"],
               source_ref="20.5.2.1已报名项目增加多次付款功能",
               note={"role": ["r13"]}),
            op(name="下载预通知文件", category="file",
               expected_results=["下载预通知文件"],
               source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载",
               note={"role": ["r05", "r13"]}),
            op(name="上传结果通知单", category="file",
               expected_results=["上传结果通知单文件"],
               source_ref="20.5.1.3项目批量操作",
               note={"role": ["r05"]}),
            op(name="上传证书", category="file",
               expected_results=["上传证书文件"],
               source_ref="20.5.1.3项目批量操作",
               note={"role": ["r05"]}),
            op(name="导出评价结果", category="file",
               expected_results=["下载评价结果"],
               source_ref="20.7.1.4评价结果导出",
               note={"role": ["r08"]}),
        ],
    )

    m.add_entity(
        id="E-YP", name="项目样品",
        desc="项目级验证样品（区别于报名记录样品 E-BMYP）。来源 §19.3 样品状态 + §19.1 流程表。",
        type="core",
        tags=["multi-state"],
        attributes=[
            attr(name="样品编号", desc="样品唯一编号"),
            attr(name="制备方案", desc="样品制备方案"),
            attr(name="核查记录", desc="样品核查记录表"),
        ],
        state_dimensions=[
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查", "已还样", "无需还样"],
                "initial": "待核查",
                "terminal": ["已还样", "无需还样"],
                "inferred": ["已还样", "无需还样"],
                "note": {"comment": "§19.3 枚举仅含 待核查/已核查；§19.1 参加者测试与结果提交行 样品状态列出现 已还样、待核查/无需还样，按 inferred 增补 已还样/无需还样 终态；§19.1 表 样品状态列与 报名记录样品状态列存在混用（如 已发样 实属 E-BMYP），此处仅取 E-YP 语义值"},
            },
        ],
        operations=[
            op(name="样品制备", category="file",
               expected_results=["编制样品制备方案并执行样品制备"],
               source_ref="11样品制备人员",
               note={"role": ["r06"]}),
            op(name="样品核查", category="file",
               expected_results=["样品状态变为已核查", "生成核查记录表"],
               source_ref="19.1实施阶段-样品核查行",
               note={"role": ["r07"]}),
            op(name="样品配置一致性测试", category="crud",
               expected_results=["完成样品配置核查与一致性测试"],
               source_ref="11样品制备人员-样品管理",
               note={"role": ["r06"]}),
        ],
    )

    m.add_entity(
        id="E-BMJL", name="报名记录",
        desc="参加者对项目的报名记录，承载报名/结果/报告证书全链路状态。来源 §19.3 报名记录状态。",
        type="core",
        tags=["multi-state", "approvable", "expirable", "collaborative"],
        attributes=[
            attr(name="报名编号", desc="报名记录唯一编号"),
            attr(name="统一社会信用代码", desc="参加者实验室统一社会信用代码"),
            attr(name="实验室名称", desc="参加者实验室名称"),
            attr(name="报名表", desc="参加者上传的报名表文件"),
            attr(name="测试结果", desc="参加者提交的测试结果文件"),
            attr(name="报名表盖章版", desc="盖章版报名表"),
            attr(name="结果通知单", desc="结果通知单文件"),
            attr(name="证书", desc="能力验证合格证书文件"),
            attr(name="实施状态", desc="参加者实施状态"),
            attr(name="评价得分", desc="参加者最终评价得分"),
            attr(name="评价结果", desc="参加者评价结果"),
            attr(name="行政区划", desc="参加者行政区划"),
            attr(name="报名时间", desc="报名时间"),
            attr(name="到款时间", desc="到款时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交",
                           "结果已提交", "结果退回修改", "报告/证书审核中",
                           "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "inferred": [],
                "note": {"comment": "状态枚举源自 §19.3 报名记录状态；initial 取创建事件 e06 落点 报名待审核"},
            },
        ],
        operations=[
            op(name="查询报名信息", category="query",
               expected_results=["按筛选条件分页返回报名信息"],
               source_ref="20.8.3.2报名信息统计",
               note={"role": ["r05", "r12"]}),
            op(name="上传报名表", category="file",
               expected_results=["报名记录创建并进入报名待审核状态"],
               source_ref="19.1实施阶段-报名行",
               note={"role": ["r13"]}),
            op(name="上传缴费证明", category="file",
               expected_results=["保存缴费凭证"],
               source_ref="18能力验证参加者-报名缴费",
               note={"role": ["r13"]}),
            op(name="上传测试结果", category="file",
               expected_results=["报名记录状态变为结果已提交", "保存测试结果文件与报名表盖章版"],
               source_ref="19.1实施阶段-参加者测试与结果提交行",
               note={"role": ["r13"]}),
            op(name="下载结果报告", category="file",
               expected_results=["下载能力验证计划结果报告"],
               source_ref="18能力验证参加者-报告提交接收",
               note={"role": ["r13"]}),
            op(name="下载结果通知单", category="file",
               expected_results=["下载个人结果通知单"],
               source_ref="18能力验证参加者-报告提交接收",
               note={"role": ["r13"]}),
            op(name="下载合格证书", category="file",
               expected_results=["下载能力验证合格证书"],
               source_ref="18能力验证参加者-报告提交接收",
               note={"role": ["r13"]}),
            op(name="批量提交审核", category="ui",
               expected_results=["对已上传文件且未提交审核的记录批量提交审核任务"],
               source_ref="20.5.1.3项目批量操作",
               note={"role": ["r05"]}),
        ],
    )

    m.add_entity(
        id="E-BMYP", name="报名记录样品",
        desc="参加者收到的样品记录（区别于项目级样品 E-YP）。来源 §19.3 报名记录样品状态。",
        type="core",
        tags=[],
        attributes=[
            attr(name="快递单号", desc="样品快递单号"),
            attr(name="软件访问路径", desc="电子样品软件访问路径"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "inferred": [],
                "note": {"comment": "状态枚举源自 §19.3 报名记录样品状态；§19.1 样品发放行 报名记录样品状态列显示 已确认"},
            },
        ],
        operations=[
            op(name="样品发放", category="crud",
               expected_results=["报名记录样品状态变为已确认", "记录快递单号或软件访问路径"],
               source_ref="19.1实施阶段-样品发放行",
               note={"role": ["r07"]}),
            op(name="样品归还登记", category="crud",
               expected_results=["登记样品归还信息"],
               source_ref="12样品管理员-库存管理",
               note={"role": ["r07"]}),
        ],
    )

    m.add_entity(
        id="E-YT", name="预通知",
        desc="项目实施前的预通知记录。来源 §19.3 通知状态。",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="预通知文件", desc="预通知文件"),
            attr(name="用户信息表", desc="用户信息表附件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "预通知状态",
                "states": ["未发送", "待确认", "已发送", "待审核", "退回", "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已批准"],
                "inferred": [],
                "note": {"comment": "状态枚举源自 §19.3 通知状态；§19.2 作业指导书编制行引入 待审核/退回/已审核 路径，属测量审核分支"},
            },
        ],
        operations=[
            op(name="发送预通知", category="config",
               expected_results=["预通知状态由未发送变为已发送", "生成预通知文件与用户信息表"],
               source_ref="19.1实施阶段-能力验证预通知行",
               note={"role": ["r05"]}),
        ],
    )

    m.add_entity(
        id="E-JFTZ", name="缴费通知单",
        desc="参加者报名后系统生成的缴费通知单。来源 §19.1 缴费通知单列。",
        type="core",
        tags=[],
        attributes=[
            attr(name="缴费通知书", desc="缴费通知书文件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "缴费通知单状态",
                "states": ["未发送", "已发送"],
                "initial": "未发送",
                "terminal": ["已发送"],
                "inferred": [],
                "note": {"comment": "状态源自 §19.1 流程表 缴费通知单列；§19.2 称为 缴纳测量审核费用通知"},
            },
        ],
        operations=[],
    )

    m.add_entity(
        id="E-FY", name="费用",
        desc="参加者报名项目的费用记录。来源 §19.3 费用状态 + §20.10 财务管理。",
        type="core",
        tags=["expirable"],
        attributes=[
            attr(name="应收金额", desc="项目应收金额"),
            attr(name="付款金额", desc="累计付款金额（支持多次付款）"),
            attr(name="退款金额", desc="累计退款金额，红色字体且大于0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="支付方式", desc="支付方式"),
            attr(name="支付账户名称", desc="支付账户名称"),
            attr(name="付款底单", desc="付款底单文件"),
            attr(name="到款日期", desc="到款日期"),
            attr(name="管理备注", desc="退款原因等"),
        ],
        state_dimensions=[
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "inferred": [],
                "note": {"comment": "状态枚举源自 §19.3 费用状态；§20.10.2.3 退款不改变状态，仅累加退款金额"},
            },
        ],
        operations=[
            op(name="上传付款单", category="file",
               expected_results=["创建多次付款记录", "不校验付款金额限制"],
               source_ref="20.5.2.1已报名项目增加多次付款功能",
               note={"role": ["r13"]}),
            op(name="缴费单退款", category="crud",
               expected_results=["累加退款金额", "实际付款=付款-退款", "退款金额不可大于当前缴费金额"],
               source_ref="20.10.2.3缴费单退款",
               note={"role": ["r11"]}),
            op(name="修改财务备注", category="crud",
               expected_results=["更新项目财务备注"],
               source_ref="20.10.2.1项目列表增加财务备注字段",
               note={"role": ["r11", "r12"]}),
        ],
    )

    m.add_entity(
        id="E-FP", name="发票",
        desc="参加者缴费后开具的发票。来源 §19.3 发票状态 + §20.10.2.2。",
        type="core",
        tags=[],
        attributes=[
            attr(name="开票时间", desc="最后一次开票时间"),
            attr(name="电子发票", desc="电子发票文件，支持多次分批上传"),
            attr(name="开票类型", desc="电子专票/电子普票"),
            attr(name="关联报名编号", desc="关联项目报名编号"),
            attr(name="项目金额", desc="项目费用"),
        ],
        state_dimensions=[
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "inferred": [],
                "note": {"comment": "状态枚举源自 §19.3 发票状态；§20.10.2.2 支持多次分批上传"},
            },
        ],
        operations=[
            op(name="发票上传", category="file",
               expected_results=["支持多次分批上传发票", "发票列表显示已上传文件", "可移除文件（提交后生效）"],
               source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传",
               note={"role": ["r11"]}),
        ],
    )

    m.add_entity(
        id="E-LAB", name="实验室",
        desc="参加者实验室信息。来源 §20.3.1/§20.4.1。",
        type="core",
        tags=["approvable", "multi-state"],
        attributes=[
            attr(name="实验室编号", desc="实验室编号"),
            attr(name="实验室名称", desc="实验室名称"),
            attr(name="统一社会信用代码", desc="统一社会信用代码"),
            attr(name="法人名称", desc="法人名称"),
            attr(name="企业类型", desc="企业类型"),
            attr(name="企业规模", desc="企业规模"),
            attr(name="CNAS", desc="已获CNAS认可"),
            attr(name="CNAS证书号", desc="CNAS证书号"),
            attr(name="CMA", desc="已获CMA认可"),
            attr(name="CMA证书编号", desc="CMA证书编号"),
            attr(name="邮箱", desc="邮箱"),
            attr(name="座机号码", desc="座机号码"),
            attr(name="地址", desc="行政区域+详细地址"),
            attr(name="联系人", desc="联系人"),
            attr(name="联系电话", desc="联系电话"),
            attr(name="默认实验室", desc="是否默认实验室"),
            attr(name="证明文件", desc="营业执照或其他证书材料"),
            attr(name="审核意见", desc="审核反馈意见"),
            attr(name="快照记录", desc="审核通过时生成的数据快照"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "启用", "停用", "已退回"],
                "initial": "待审核",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "状态源自 §20.3.1 实验室信息新增状态字段（含 待审核/启用/停用/退回修改）；§20.4.1.1 状态下拉选项为 待审核/启用/停用/已退回，与 §20.3.1 退回修改 文字略有差异，按 §20.4.1.1 取已退回"},
            },
        ],
        operations=[
            op(name="新增实验室", category="crud",
               expected_results=["实验室记录创建并进入待审核状态"],
               source_ref="20.4.1实验室管理",
               note={"role": ["r13"]}),
            op(name="修改实验室", category="crud",
               expected_results=["修改后状态变为待审核", "弹出修改窗口显示实验室字段"],
               source_ref="20.4.1.3实验室修改",
               note={"role": ["r13"]}),
            op(name="审核实验室", category="crud",
               expected_results=["弹出审核窗口只读显示实验室内容", "通过则状态变为启用并生成快照", "退回修改则状态变为已退回且必须填写审核意见"],
               source_ref="20.4.1.2实验室审核",
               note={"role": ["r12"]}),
            op(name="停用实验室", category="crud",
               expected_results=["状态变为停用", "弹出二次确认框"],
               source_ref="20.4.1.1实验室列表与查询",
               note={"role": ["r12"]}),
            op(name="启用实验室", category="crud",
               expected_results=["状态变为启用", "弹出二次确认框"],
               source_ref="20.4.1.1实验室列表与查询",
               note={"role": ["r12"]}),
            op(name="查询实验室", category="query",
               expected_results=["按编号/名称/状态独立或组合查询"],
               source_ref="20.4.1.1实验室列表与查询",
               note={"role": ["r12"]}),
        ],
    )

    m.add_entity(
        id="E-STD", name="标准库",
        desc="标准库基础数据。来源 §20.4.2 标准库管理。",
        type="managed",
        tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="标准库编号", is_config=True),
            attr(name="标准库名称", desc="标准库名称"),
            attr(name="描述", desc="描述"),
            attr(name="创建时间", desc="创建时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "标准库状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "状态源自 §20.4.2.1 列表展示字段（启用/停用）；新增时状态必填，默认启用推断"},
            },
        ],
        operations=[
            op(name="新增标准库", category="crud",
               expected_results=["弹出表单对话框", "标准库编号/名称/状态必填"],
               source_ref="20.4.2.2新增标准库",
               note={"role": ["r12"]}),
            op(name="修改标准库", category="crud",
               expected_results=["弹出编辑表单对话框", "刷新列表"],
               source_ref="20.4.2.3修改标准库",
               note={"role": ["r12"]}),
            op(name="删除标准库", category="crud",
               expected_results=["弹出二次确认框", "确认后删除记录"],
               source_ref="20.4.2.4删除标准库",
               note={"role": ["r12"]}),
            op(name="停用标准库", category="config",
               expected_results=["状态变为停用", "项目创建环节不可被选择"],
               source_ref="20.4.2.5停用/启用标准库",
               note={"role": ["r12"]}),
            op(name="启用标准库", category="config",
               expected_results=["状态变为启用"],
               source_ref="20.4.2.5停用/启用标准库",
               note={"role": ["r12"]}),
            op(name="查询标准库", category="query",
               expected_results=["按编号/名称/状态独立或组合查询"],
               source_ref="20.4.2.1标准库列表与查询",
               note={"role": ["r12"]}),
            op(name="管理测试项", category="ui",
               expected_results=["进入标准库专属测试项管理界面"],
               source_ref="20.4.2.6进入测试项管理界面",
               note={"role": ["r12"]}),
        ],
    )

    m.add_entity(
        id="E-CS", name="测试项",
        desc="标准库下的测试项/测试参数，可嵌套子项。来源 §20.4.2.7–20.4.2.10。",
        type="managed",
        tags=[],
        attributes=[
            attr(name="标号", desc="测试项标号"),
            attr(name="名称", desc="测试项名称"),
            attr(name="父测试项", desc="父测试项引用"),
            attr(name="所属标准库", desc="所属标准库"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud",
               expected_results=["标号/名称必填", "新增的为子级测试项或评价细则"],
               source_ref="20.4.2.8新增测试项",
               note={"role": ["r12"]}),
            op(name="修改测试项", category="crud",
               expected_results=["刷新列表数据信息"],
               source_ref="20.4.2.9修改测试项",
               note={"role": ["r12"]}),
            op(name="删除测试项", category="crud",
               expected_results=["弹出二次确认框", "含有子项的记录不允许删除"],
               source_ref="20.4.2.10删除测试项",
               note={"role": ["r12"]}),
        ],
    )

    m.add_entity(
        id="E-ZLY", name="子领域",
        desc="子领域及其测试项。来源 §20.4.3 子领域管理。",
        type="managed",
        tags=[],
        attributes=[
            attr(name="子领域名称", desc="子领域名称"),
            attr(name="测试项列表", desc="关联的测试项列表（来源标准库选择）"),
        ],
        state_dimensions=[],
        operations=[
            op(name="管理子领域测试项", category="ui",
               expected_results=["进入子领域专属测试项管理界面"],
               source_ref="20.4.3.1进入测试项管理界面",
               note={"role": ["r12"]}),
            op(name="新增子领域测试项", category="crud",
               expected_results=["选择标准库与测试项", "新标准库出现在列表中"],
               source_ref="20.4.3.3新增测试项",
               note={"role": ["r12"]}),
            op(name="删除子领域测试项", category="crud",
               expected_results=["弹出二次确认框", "存在子项的数据不可以删除"],
               source_ref="20.4.3.4删除测试项",
               note={"role": ["r12"]}),
        ],
    )

    m.add_entity(
        id="E-CY", name="常用测试项组合",
        desc="项目录入时保存的常用子领域测试项组合。来源 §20.5.1.7/§20.6.1.5。",
        type="managed",
        tags=[],
        attributes=[
            attr(name="名称", desc="常用项名称"),
            attr(name="所属子领域", desc="所属子领域"),
            attr(name="测试项快照", desc="保存的测试项组合"),
        ],
        state_dimensions=[],
        operations=[
            op(name="另存常用", category="crud",
               expected_results=["保存常用项数据"],
               source_ref="20.5.1.7增加常用子领域测试项编辑能力",
               note={"role": ["r05"]}),
            op(name="选择常用项填充", category="ui",
               expected_results=["将常用项内容填充到测试项表单"],
               source_ref="20.5.1.7增加常用子领域测试项编辑能力",
               note={"role": ["r05"]}),
            op(name="删除常用项", category="crud",
               expected_results=["从下拉列表删除常用项"],
               source_ref="20.5.1.7增加常用子领域测试项编辑能力",
               note={"role": ["r05"]}),
        ],
    )

    m.add_entity(
        id="E-PJ", name="项目评价",
        desc="对参加者结果的评价记录，支持分值/权重两种评价方式与协同评价。来源 §20.7 项目评价。",
        type="core",
        tags=["approvable", "collaborative", "multi-state"],
        attributes=[
            attr(name="评分方式", desc="分值或权重", is_config=True),
            attr(name="及格分", desc="及格分，评价组长录入"),
            attr(name="评价项目", desc="测试项目及评价细则"),
            attr(name="评价结果", desc="最终评价结果"),
            attr(name="历史结果", desc="评价历史结果文件"),
            attr(name="统计规则", desc="成绩区间统计规则"),
            attr(name="评价组长", desc="评价组长（首个被选评价人员）"),
            attr(name="评价人员列表", desc="参与评价的评价人员列表"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["待评价", "评价中", "已评价"],
                "initial": "待评价",
                "terminal": ["已评价"],
                "inferred": [],
                "note": {"comment": "状态源自 §20.7 项目评价语义推导：评价组长完善→待评价；评价人员开始评价→评价中；评价组长确认→已评价；§20.7.1.3 退回修改开启下一轮评价→待评价"},
            },
        ],
        operations=[
            op(name="完善测试项目及评价细则", category="crud",
               expected_results=["评价组长可编辑评价项目及评价细则", "支持另存常用与常用项选择填充"],
               source_ref="20.7.1.1测试项目评价细则完善",
               note={"role": ["r08"]}),
            op(name="协同评价", category="crud",
               expected_results=["评价人员只能查看/修改自己的评价结果", "对评价项单元格输入或调整评价分数"],
               source_ref="20.7.1.2协同评价",
               note={"role": ["r08"]}),
            op(name="评价结果确认", category="crud",
               expected_results=["提交为项目最终评价结果", "评价状态关闭"],
               source_ref="20.7.1.3评价确认",
               note={"role": ["r08"]}),
            op(name="保存历史", category="file",
               expected_results=["将当前评价结果保存为历史结果"],
               source_ref="20.7.1.3评价确认-保存历史按钮",
               note={"role": ["r08"]}),
            op(name="调整细则", category="ui",
               expected_results=["打开评价细节完善页面", "返回后刷新页面数据"],
               source_ref="20.7.1.3评价确认-调整细则按钮",
               note={"role": ["r08"]}),
            op(name="退回修改", category="crud",
               expected_results=["当前评价结果保存为历史", "开启下一轮评价"],
               source_ref="20.7.1.3评价确认-退回修改按钮",
               note={"role": ["r08"]}),
            op(name="调整统计规则", category="config",
               expected_results=["弹出统计规则配置弹窗", "配置成绩区间低值/高值"],
               source_ref="20.7.1.3评价确认-调整统计规则按钮",
               note={"role": ["r08"]}),
            op(name="导出评价结果", category="file",
               expected_results=["下载评价结果"],
               source_ref="20.7.1.4评价结果导出",
               note={"role": ["r08"]}),
        ],
    )

    m.add_entity(
        id="E-ZS", name="证书",
        desc="能力验证合格证书。来源 §20.5.2.3/§20.6.2.3 证书到期提醒。",
        type="core",
        tags=["expirable"],
        attributes=[
            attr(name="证书编号", desc="证书唯一编号"),
            attr(name="到期时间", desc="证书到期时间"),
            attr(name="持有人", desc="持有人参加者"),
            attr(name="关联报名记录", desc="关联报名记录"),
        ],
        # （证书状态 维度已撤销：值=到期时间 属性的时间派生，非工作流状态机；
        #   到期提醒需求由 BR b05 承载——同 E-CAR 移交/留存 属性级操作非状态判例，消除 C02 假阳性）
        operations=[
            op(name="发放证书", category="file",
               expected_results=["证书文件生成并发给参加者"],
               source_ref="19.1报告编制和结果通知-发放结果报告和证书行",
               note={"role": ["r05"]}),
        ],
    )

    m.add_entity(
        id="E-TASK", name="审批任务",
        desc="业务审核流程中的审批任务。来源 §20.9 业务审核。",
        type="core",
        tags=["approvable", "multi-state"],
        attributes=[
            attr(name="任务类型", desc="审核类型名称，如结果通知单审核"),
            attr(name="处理人顺序", desc="提交申请时签字人选择顺序"),
            attr(name="创建时间", desc="任务创建时间"),
            attr(name="签章位置", desc="电子签章位置信息"),
            attr(name="流程节点状态", desc="用不同颜色标记各状态节点"),
        ],
        state_dimensions=[
            {
                "dimension_name": "审核任务状态",
                "states": ["待审核", "已审核", "已退回"],
                "initial": "待审核",
                "terminal": ["已审核", "已退回"],
                "inferred": [],
                "note": {"comment": "状态源自 §20.9.1.4 任务批量处理 审核结果（同意/退回）语义推导；§20.9.1.1 测量审核结果通知单审批流程合并为单一流程"},
            },
        ],
        operations=[
            op(name="提交审核任务", category="crud",
               expected_results=["生成新的审核任务", "短信通知相关负责人：您有一个新的xxx审核任务，请及时处理"],
               source_ref="20.9.1.3增加任务提醒",
               note={"role": ["r05", "r04"]}),
            op(name="批量审核", category="ui",
               expected_results=["系统根据任务节点类型及内容判断是否可批量处理", "审核结果为同意或退回"],
               source_ref="20.9.1.4任务批量处理",
               note={"role": ["r14"]}),
            op(name="审批列表导出", category="file",
               expected_results=["导出满足查询条件的数据", "支持按创建时间筛选"],
               source_ref="20.9.1.5审批流程列表导出",
               note={"role": ["r14", "r12"]}),
            op(name="电子签章", category="config",
               expected_results=["自动代入签章位置信息"],
               source_ref="20.9.1.2预置签章位置信息",
               note={"role": ["r14"]}),
            op(name="自定义流程提交", category="config",
               expected_results=["选择预设4个以内自定义流程提交文档审核", "支持相应签章"],
               source_ref="20.9.1.6增加自定义流程",
               note={"role": ["r14"]}),
        ],
    )

    m.add_entity(
        id="E-MSG", name="信息发送记录",
        desc="系统信息发送历史记录。来源 §20.4.4 信息发送记录。",
        type="managed",
        tags=[],
        attributes=[
            attr(name="接收号码", desc="接收人号码"),
            attr(name="发送方式", desc="短信/邮件/站内信"),
            attr(name="发送时间", desc="发送时间"),
            attr(name="发送人", desc="发送人"),
            attr(name="发送结果", desc="发送结果"),
            attr(name="消息标题", desc="消息标题"),
            attr(name="消息内容", desc="消息内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query",
               expected_results=["按接收号码/发送时间/发送方式独立或组合查询"],
               source_ref="20.4.4.1信息发送记录",
               note={"role": ["r12", "r05"]}),
            op(name="查看消息详情", category="query",
               expected_results=["查看消息详细内容"],
               source_ref="20.4.4.1信息发送记录-消息详情",
               note={"role": ["r12", "r05"]}),
        ],
    )

    # 1.5 结构关系
    m.add_structural(
        frm="E-XM", to="E-BMJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="一个项目下有多条报名记录；项目创建后参加者报名生成报名记录，承载项目流转",
        confidence="high",
        note={"comment": "判 (c) 组合：B(报名记录)有独立创建流程，且属 core 流程实体；A(项目)为其业务归属容器；cardinality 1:N 一个项目对应多条报名记录"},
    )
    m.add_structural(
        frm="E-XM", to="E-YP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每个项目制备一份项目级样品；样品核查、参加者测试围绕项目样品展开",
        confidence="high",
        note={"comment": "判 (b) 组合：B(项目样品)无独立创建流程，A(项目)创建后样品自动进入 initial(待核查)；每条 A 必有 B"},
    )
    m.add_structural(
        frm="E-BMJL", to="E-BMYP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录对应一份待发样品（与项目级样品 E-YP 区分）",
        confidence="high",
        note={"comment": "判 (b) 组合：报名记录创建后自动生成待发样记录；cardinality 1:1"},
    )
    m.add_structural(
        frm="E-BMJL", to="E-FY",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录对应一份费用记录；支持多次付款与退款",
        confidence="high",
        note={"comment": "判 (b) 组合：报名记录创建后系统初始化费用为待缴费"},
    )
    m.add_structural(
        frm="E-BMJL", to="E-FP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录对应一份发票记录；支持多次分批上传",
        confidence="high",
        note={"comment": "判 (b) 组合：报名记录创建后发票为待开票"},
    )
    m.add_structural(
        frm="E-BMJL", to="E-JFTZ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每条报名记录对应一份缴费通知单",
        confidence="high",
        note={"comment": "判 (b) 组合：报名记录创建后系统自动初始化缴费通知单为未发送"},
    )
    m.add_structural(
        frm="E-XM", to="E-YT",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每个项目对应一份预通知；能力验证计划发布时初始化为未发送",
        confidence="high",
        note={"comment": "判 (b) 组合：项目发布后预通知自动创建为未发送"},
    )
    m.add_structural(
        frm="E-XM", to="E-PJ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="每个项目对应一份评价记录；评价组长由第一个被选择的评价人员默认担任",
        confidence="high",
        note={"comment": "判 (b) 组合：项目进入评价阶段后评价记录创建为待评价"},
    )
    m.add_structural(
        frm="E-BMJL", to="E-ZS",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="一条报名记录可对应多份证书（含历史证书）",
        confidence="medium",
        note={"comment": "判 (d) 引用：证书有独立发放流程且可能由其他流程触发；按 (d) reference + confidence=medium"},
    )
    m.add_structural(
        frm="E-XM", to="E-TASK",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="项目报告/通知单/证书审核任务由项目流程触发，但任务有独立审批流程",
        confidence="high",
        note={"comment": "判 (d) 引用：审批任务有独立创建流程，不属 core 流程实体的下级；A 仅为发起人"},
    )
    m.add_structural(
        frm="E-LAB", to="E-BMJL",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="实验室为报名记录提供参加者主体信息；实验室需启用状态方可用于项目报名",
        confidence="high",
        note={"comment": "判 (a) 引用：实验室为报名记录提供配置信息（参加者主体），报名记录独立创建"},
    )
    m.add_structural(
        frm="E-STD", to="E-CS",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="标准库下有多个测试项，测试项可嵌套子项；测试项无独立创建流程",
        confidence="high",
        note={"comment": "判 (b) 组合：测试项由标准库管理，无独立创建流程；管理测试项即标准库的子项管理"},
    )
    m.add_structural(
        frm="E-ZLY", to="E-CS",
        relation_type="reference", cardinality="M:N",
        ownership_dimension="configuration_source",
        desc="子领域通过选择标准库中的测试项建立关联；同一测试项可被多个子领域引用",
        confidence="high",
        note={"comment": "判 (a) 引用：子领域选择标准库测试项作为配置来源；§20.4.3 由表单改为选择方式"},
    )
    m.add_structural(
        frm="E-ZLY", to="E-CY",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="子领域下保存的常用测试项组合",
        confidence="high",
        note={"comment": "判 (b) 组合：常用项归属于子领域，无独立创建流程"},
    )

    # ===== Step 2: 分支 =====
    # ① 配置型：评分方式（分值/权重，§20.7.1项目列表评分方式）
    m.add_branch_dimension(
        dimension="评分方式", entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="影响评价录入字段与评价结果计算口径",
        evidence="①③配置型/隐式分支：§20.7项目列表-支持分值和权重两种评价方式；§20.7.1.1表单含 分值/权重 字段",
        branches=[
            {"value": "分值", "target_transition": "评价人员开始评价（分值录入）"},
            {"value": "权重", "target_transition": "评价人员开始评价（权重录入）"},
        ],
    )
    # ① 配置型：项目类型（能力验证/测量审核，影响初始状态与流程顺序）
    m.add_branch_dimension(
        dimension="项目类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="影响E-XM初始状态（能力验证经待开始，测量审核直接进入报名中）与流程顺序（测量审核任务通知书在缴费后编制）",
        evidence="①③配置型/隐式分支：§19.1能力验证提供者流程 vs §19.2测量审核提供者流程",
        branches=[
            {"value": "能力验证", "target_transition": "设计方案编制（待开始→报名中路径）"},
            {"value": "测量审核", "target_transition": "测量审核受理报名（直接→报名中路径）"},
        ],
    )
    # ② 运行时选择型：报名审核结果
    m.add_branch_dimension(
        dimension="报名审核结果", entity="E-BMJL",
        values=["通过", "退回修改"],
        impact_scope="影响E-BMJL报名记录状态落点（报名成功 vs 报名退回）",
        evidence="②运行时选择型：§19.1实施阶段-报名审核行 报名记录状态列 报名退回/成功",
        branches=[
            {"value": "通过", "target_transition": "报名审核通过"},
            {"value": "退回修改", "target_transition": "报名审核退回"},
        ],
    )
    # （样品归还方式/预通知确认结果 已撤销：glm5pr:110 状态落点值不作分支值，
    #   值=标注转换 to 落点态，分歧由转换分立承载，非分支维度；precondition 分支值条件保留）
    # ② 运行时选择型：实验室审核结果
    m.add_branch_dimension(
        dimension="实验室审核结果", entity="E-LAB",
        values=["通过", "退回修改"],
        impact_scope="影响E-LAB实验室状态落点（启用 vs 已退回）",
        evidence="②运行时选择型：§20.4.1.2实验室审核 审核结果单选框 通过/退回修改",
        branches=[
            {"value": "通过", "target_transition": "实验室审核通过"},
            {"value": "退回修改", "target_transition": "实验室审核退回修改"},
        ],
    )
    # ② 运行时选择型：审核任务结果
    m.add_branch_dimension(
        dimension="审核任务结果", entity="E-TASK",
        values=["同意", "退回"],
        impact_scope="影响E-TASK审核任务状态落点（已审核 vs 已退回）",
        evidence="②运行时选择型：§20.9.1.4任务批量处理 审核结果下拉选项 同意/退回",
        branches=[
            {"value": "同意", "target_transition": "审核任务审核通过"},
            {"value": "退回", "target_transition": "审核任务审核退回"},
        ],
    )

    # ===== Step 3: 转换与因果 =====

    # 3.1 转换 - E-XM 项目状态
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[],
        expected_results=["项目创建并进入待开始状态", "项目状态为待开始"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1方案设计阶段；19.3项目状态分析",
        note={"comment": "源自 e01；⓪frm=None→forward；能力验证路径 initial=待开始"},
    )
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
            precond(text="项目类型=能力验证", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["项目状态由待开始变为报名中", "能力验证计划通知或邀请函生成"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段-能力验证计划发布行",
        note={"branch_dimension": "项目类型", "comment": "源自 e02；③frm先于to→forward；能力验证分支：路径分歧"},
    )
    m.add_trans(
        tid="t02b", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="测量审核受理报名", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["测量审核项目创建并直接进入报名中状态"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2项目准备阶段-受理用户测量审核报名行",
        note={"branch_dimension": "项目类型", "comment": "源自 e48；⓪frm=None→forward；测量审核分支：路径分歧，跳过待开始状态直接进入报名中"},
    )
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="报名截止进入实施", role="system",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目状态由报名中变为进行中"],
        traits=["time_sensitive"], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"inferred": True, "comment": "源自 e03；③frm先于to→forward；inferred：§19.1 流程表未在实施阶段显式标记 项目状态→进行中 的转换动作，按 §19.3 枚举补"},
    )
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="进入报告编制阶段", role="system",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
            precond(text="结果报告回收完成", ptype="event_ref"),
        ],
        expected_results=["项目状态由进行中变为报告审核中"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.3项目状态分析；19.1报告编制和结果通知",
        note={"inferred": True, "comment": "源自 e04；③frm先于to→forward；inferred：§19.1 流程表未显式标记此转换，按 §19.3 枚举与报告编制阶段语义补"},
    )
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="报名记录已发布报告/证书", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书已发布")),
        ],
        expected_results=["项目状态由报告审核中变为已结束"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知-发放结果报告和证书行；19.3项目状态分析",
        note={"comment": "源自 e05；③frm先于to→forward；跨主体门禁 E-BMJL.报告/证书已发布 落 state_ref"},
    )

    # E-BMJL 报名记录状态
    m.add_trans(
        tid="t06", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="参加者报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["报名记录创建并进入报名待审核状态", "报名表附件上传"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-报名行",
        note={"comment": "源自 e06；⓪frm=None→forward；跨主体门禁 E-XM.报名中 与 E-LAB.启用 落 state_ref"},
    )
    m.add_trans(
        tid="t07", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="已撤销", action="参加者报名撤销", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态由报名待审核变为已撤销"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段-报名行（已撤销分支）",
        note={"comment": "源自 e07；③frm先于to→forward；分支值 报名审核结果 不适用，此为参加者主动撤销"},
    )
    m.add_trans(
        tid="t08", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="报名审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态由报名待审核变为报名成功", "短信通知参加者审核通过"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段-报名审核行",
        note={"branch_dimension": "报名审核结果", "comment": "源自 e08；③frm先于to→forward；路径分歧：通过分支"},
    )
    m.add_trans(
        tid="t08b", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核退回", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="报名审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态由报名待审核变为报名退回", "短信通知参加者审核未通过"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="19.1实施阶段-报名审核行",
        note={"branch_dimension": "报名审核结果", "comment": "源自 e09；①退回→backward；路径分歧：退回分支"},
    )
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="退回后重新提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名退回")),
        ],
        expected_results=["报名记录状态由报名退回变为报名待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段-报名审核行（隐含重报）",
        note={"inferred": True, "comment": "源自 e10；③frm先于to→forward；inferred：§19.1 表未显式列出退回后重报动作，按流程语义补"},
    )
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="预通知后进入结果提交阶段", role="system",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="预通知已发送", ptype="state_ref",
                    ref=state_ref("E-YT", "预通知状态", "已发送")),
        ],
        expected_results=["报名记录状态由报名成功变为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-能力验证预通知行",
        note={"comment": "源自 e11；③frm先于to→forward；跨主体门禁 E-YT.已发送 落 state_ref"},
    )
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="参加者提交结果", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态由结果待提交变为结果已提交", "保存测试结果文件与报名表盖章版"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-参加者测试与结果提交行",
        note={"comment": "源自 e12；③frm先于to→forward"},
    )
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果退回修改", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态由结果已提交变为结果退回修改"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知-结果报告回收行",
        note={"comment": "源自 e13；①退回→backward"},
    )
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价已完成", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "已评价")),
        ],
        expected_results=["报名记录状态由结果已提交变为报告/证书审核中", "结果报告与结果通知生成"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知-编制结果报告行",
        note={"comment": "源自 e14；③frm先于to→forward；跨主体门禁 E-PJ.已评价 落 state_ref"},
    )
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="技术主管审核报告", role="技术主管",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["技术主管审核通过后状态仍为报告/证书审核中", "生成审核留痕"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知-技术主管审核报告行",
        note={"comment": "源自 e15；⑤自环frm==to→forward；技术主管审核为审核环节内部留痕，状态不迁移"},
    )
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="授权签字人/实验室负责人批准", role="授权签字人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["批准后状态仍为报告/证书审核中", "生成批准留痕"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知-报告结果通知单批准行",
        note={"comment": "源自 e16；⑤自环frm==to→forward；授权签字人批准结果通知单/实验室负责人批准证书，为审核环节内部留痕"},
    )
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["报名记录状态由报告/证书审核中变为报告/证书已发布", "结果报告与证书发放给参加者"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知-发放结果报告和证书行",
        note={"comment": "源自 e17；③frm先于to→forward"},
    )

    # E-YP 项目样品状态
    m.add_trans(
        tid="t17", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="样品制备并登记", role="样品制备人员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目样品创建并进入待核查状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-缴费行（样品状态首次出现待核查）；19.3样品状态",
        note={"inferred": True, "comment": "源自 e18；⓪frm=None→forward；inferred：§19.1 表未显式列出样品创建动作，按 缴费行 样品状态=待核查 推导样品已创建"},
    )
    m.add_trans(
        tid="t18", entity="E-YP", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
        ],
        expected_results=["样品状态由待核查变为已核查", "核查记录表生成"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段-样品核查行",
        note={"comment": "源自 e19；③frm先于to→forward"},
    )
    m.add_trans(
        tid="t19", entity="E-YP", dimension="样品状态",
        frm="已核查", to="已还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
            precond(text="样品归还方式=已还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["样品状态由已核查变为已还样"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段-参加者测试与结果提交行",
        note={"comment": "源自 e20；③frm先于to→forward；路径分歧：已还样分支"},
    )
    m.add_trans(
        tid="t19b", entity="E-YP", dimension="样品状态",
        frm="已核查", to="无需还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
            precond(text="样品归还方式=无需还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["样品状态由已核查变为无需还样"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1实施阶段-参加者测试与结果提交行",
        note={"inferred": True, "comment": "源自 e20b；③frm先于to→forward；inferred 状态 无需还样 由 §19.1 推导"},
    )

    # E-BMYP 报名记录样品状态
    m.add_trans(
        tid="t20", entity="E-BMYP", dimension="报名记录样品状态",
        frm=None, to="待发样", action="报名记录样品初始化", role="system",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["报名记录样品创建并进入待发样状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3报名记录样品状态",
        note={"inferred": True, "comment": "⓪frm=None→forward；inferred：报名记录样品由报名记录创建时系统自动初始化为待发样"},
    )
    m.add_trans(
        tid="t21", entity="E-BMYP", dimension="报名记录样品状态",
        frm="待发样", to="已确认", action="样品发放", role="样品管理员",
        preconditions=[
            precond(text="报名记录样品处于待发样状态", ptype="state_ref",
                    ref=state_ref("E-BMYP", "报名记录样品状态", "待发样")),
            precond(text="项目样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
        ],
        expected_results=["报名记录样品状态由待发样变为已确认", "记录快递单号或软件访问路径"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-样品发放行",
        note={"comment": "源自 e21；③frm先于to→forward；跨主体门禁 E-YP.已核查 落 state_ref"},
    )

    # E-YT 预通知状态
    m.add_trans(
        tid="t22", entity="E-YT", dimension="预通知状态",
        frm=None, to="未发送", action="能力验证计划发布预通知初始化", role="system",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["预通知创建并进入未发送状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-能力验证计划发布行（预通知状态列未发送）",
        note={"comment": "源自 e22；⓪frm=None→forward"},
    )
    m.add_trans(
        tid="t23", entity="E-YT", dimension="预通知状态",
        frm="未发送", to="已发送", action="能力验证预通知发送", role="项目管理员",
        preconditions=[
            precond(text="预通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "预通知状态", "未发送")),
            precond(text="预通知确认结果=已发送", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["预通知状态由未发送变为已发送", "预通知文件与用户信息表生成"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段-能力验证预通知行",
        note={"comment": "源自 e23；③frm先于to→forward；路径分歧：已发送分支"},
    )
    m.add_trans(
        tid="t23b", entity="E-YT", dimension="预通知状态",
        frm="未发送", to="待确认", action="预通知待确认", role="能力验证参加者",
        preconditions=[
            precond(text="预通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "预通知状态", "未发送")),
            precond(text="预通知确认结果=待确认", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["预通知状态由未发送变为待确认"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1实施阶段-能力验证预通知行",
        note={"comment": "源自 e24；③frm先于to→forward；路径分歧：待确认分支"},
    )
    m.add_trans(
        tid="t24", entity="E-YT", dimension="预通知状态",
        frm="待审核", to="已审核", action="作业指导书审核", role="技术主管",
        preconditions=[
            precond(text="预通知/作业指导书处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-YT", "预通知状态", "待审核")),
        ],
        expected_results=["预通知状态由待审核变为已审核"],
        traits=["audit", "branch"], direction="forward", priority="P1",
        source_ref="19.2实施阶段-作业指导书编制行",
        note={"branch_dimension": "项目类型", "comment": "源自 e49；③frm先于to→forward；测量审核分支：作业指导书审核"},
    )
    m.add_trans(
        tid="t24b", entity="E-YT", dimension="预通知状态",
        frm="待审核", to="退回", action="作业指导书退回", role="技术主管",
        preconditions=[
            precond(text="预通知/作业指导书处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-YT", "预通知状态", "待审核")),
        ],
        expected_results=["预通知状态由待审核变为退回"],
        traits=["rollback", "branch"], direction="backward", priority="P1",
        source_ref="19.2实施阶段-作业指导书编制行",
        note={"branch_dimension": "项目类型", "comment": "源自 e50；①退回→backward；测量审核分支：作业指导书退回"},
    )

    # E-JFTZ 缴费通知单
    m.add_trans(
        tid="t25", entity="E-JFTZ", dimension="缴费通知单状态",
        frm=None, to="未发送", action="报名创建缴费通知单", role="system",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["缴费通知单创建并进入未发送状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-报名行（缴费通知单列）",
        note={"comment": "源自 e25；⓪frm=None→forward"},
    )
    m.add_trans(
        tid="t26", entity="E-JFTZ", dimension="缴费通知单状态",
        frm="未发送", to="已发送", action="报名审核后发送缴费通知", role="system",
        preconditions=[
            precond(text="缴费通知单处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-JFTZ", "缴费通知单状态", "未发送")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["缴费通知单状态由未发送变为已发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-报名审核行（缴费通知单列已发送）",
        note={"comment": "源自 e26；③frm先于to→forward；跨主体门禁 E-BMJL.报名成功 落 state_ref"},
    )

    # E-FY 费用状态
    m.add_trans(
        tid="t27", entity="E-FY", dimension="费用状态",
        frm=None, to="待缴费", action="报名创建费用记录", role="system",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["费用记录创建并进入待缴费状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-报名行（费用状态列）",
        note={"comment": "源自 e27；⓪frm=None→forward"},
    )
    m.add_trans(
        tid="t28", entity="E-FY", dimension="费用状态",
        frm="待缴费", to="已缴费", action="参加者缴费", role="能力验证参加者",
        preconditions=[
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "待缴费")),
            precond(text="缴费通知单已发送", ptype="state_ref",
                    ref=state_ref("E-JFTZ", "缴费通知单状态", "已发送")),
        ],
        expected_results=["费用状态由待缴费变为已缴费", "支持多次付款记录累加"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-缴费行",
        note={"comment": "源自 e28；③frm先于to→forward；跨主体门禁 E-JFTZ.已发送 落 state_ref"},
    )
    m.add_trans(
        tid="t29", entity="E-FY", dimension="费用状态",
        frm="已缴费", to="已缴费", action="缴费单退款", role="财务管理人员",
        preconditions=[
            precond(text="费用处于已缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "已缴费")),
            precond(text="退款金额不可大于当前缴费金额", ptype="constraint"),
        ],
        expected_results=["累加退款金额", "实际付款=付款金额-退款金额", "状态保持已缴费"],
        traits=["data_constraint"], direction="forward", priority="P1",
        source_ref="20.10.2.3缴费单退款",
        note={"comment": "源自 e47；⑤自环frm==to→forward；退款不改状态仅累加金额；不可大于当前缴费金额 落 constraint"},
    )

    # E-FP 发票状态
    m.add_trans(
        tid="t30", entity="E-FP", dimension="发票状态",
        frm=None, to="待开票", action="报名创建发票记录", role="system",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["发票记录创建并进入待开票状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-报名行（发票状态列）",
        note={"comment": "源自 e29；⓪frm=None→forward"},
    )
    m.add_trans(
        tid="t31", entity="E-FP", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务管理人员",
        preconditions=[
            precond(text="发票处于待开票状态", ptype="state_ref",
                    ref=state_ref("E-FP", "发票状态", "待开票")),
            precond(text="费用已缴费", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "已缴费")),
        ],
        expected_results=["发票状态由待开票变为已开票", "支持多次分批上传发票文件"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段-发票开具行；20.10.2.2修改发票上传功能",
        note={"comment": "源自 e30；③frm先于to→forward；跨主体门禁 E-FY.已缴费 落 state_ref"},
    )

    # E-LAB 实验室状态
    m.add_trans(
        tid="t32", entity="E-LAB", dimension="实验室状态",
        frm=None, to="待审核", action="机构提交实验室信息", role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室记录创建并进入待审核状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1实验室信息；20.4.1.2实验室审核",
        note={"comment": "源自 e31；⓪frm=None→forward"},
    )
    m.add_trans(
        tid="t33", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="启用", action="审核通过", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
            precond(text="实验室审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态由待审核变为启用", "生成数据快照记录"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2实验室审核（通过分支）",
        note={"branch_dimension": "实验室审核结果", "comment": "源自 e32；③frm先于to→forward；路径分歧：通过分支"},
    )
    m.add_trans(
        tid="t33b", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="已退回", action="审核退回修改", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
            precond(text="实验室审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
            precond(text="审核意见必须填写", ptype="constraint"),
        ],
        expected_results=["实验室状态由待审核变为已退回"],
        traits=["branch", "audit"], direction="backward", priority="P1",
        source_ref="20.4.1.2实验室审核（退回修改分支）",
        note={"branch_dimension": "实验室审核结果", "comment": "源自 e33；①退回→backward；路径分歧：退回修改分支"},
    )
    m.add_trans(
        tid="t34", entity="E-LAB", dimension="实验室状态",
        frm="已退回", to="待审核", action="机构修改后重新提交", role="能力验证参加者",
        preconditions=[
            precond(text="实验室处于已退回状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "已退回")),
        ],
        expected_results=["实验室状态由已退回变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3实验室修改",
        note={"comment": "源自 e34；③frm先于to→forward"},
    )
    m.add_trans(
        tid="t35", entity="E-LAB", dimension="实验室状态",
        frm="启用", to="停用", action="停用实验室", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态由启用变为停用", "弹出二次确认框"],
        traits=[], direction="lateral", priority="P2",
        source_ref="20.4.1.1实验室列表与查询（停用按钮）",
        note={"comment": "源自 e35；①停用→lateral"},
    )
    m.add_trans(
        tid="t36", entity="E-LAB", dimension="实验室状态",
        frm="停用", to="启用", action="启用实验室", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态由停用变为启用", "弹出二次确认框"],
        traits=[], direction="resume", priority="P2",
        source_ref="20.4.1.1实验室列表与查询（启用按钮）",
        note={"comment": "源自 e36；①启用→resume"},
    )

    # E-STD 标准库状态
    m.add_trans(
        tid="t37", entity="E-STD", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理人员",
        preconditions=[],
        expected_results=["标准库创建并进入启用状态"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2新增标准库",
        note={"comment": "源自 e37；⓪frm=None→forward；新增默认启用为 inferred"},
    )
    m.add_trans(
        tid="t38", entity="E-STD", dimension="标准库状态",
        frm="启用", to="停用", action="停用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-STD", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态由启用变为停用", "项目创建环节不可被选择"],
        traits=[], direction="lateral", priority="P2",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e38；①停用→lateral"},
    )
    m.add_trans(
        tid="t39", entity="E-STD", dimension="标准库状态",
        frm="停用", to="启用", action="启用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-STD", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态由停用变为启用"],
        traits=[], direction="resume", priority="P2",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e39；①启用→resume"},
    )

    # E-PJ 评价状态
    m.add_trans(
        tid="t40", entity="E-PJ", dimension="评价状态",
        frm=None, to="待评价", action="评价组长完善测试项目及评价细则", role="评价人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["评价记录创建并进入待评价状态", "评价组长可编辑评价项目及评价细则"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.1测试项目评价细则完善",
        note={"comment": "源自 e40；⓪frm=None→forward；跨主体门禁 E-BMJL.结果已提交 落 state_ref"},
    )
    m.add_trans(
        tid="t41", entity="E-PJ", dimension="评价状态",
        frm="待评价", to="评价中", action="评价人员开始评价", role="评价人员",
        preconditions=[
            precond(text="评价处于待评价状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "待评价")),
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["评价状态由待评价变为评价中", "评价人员只能查看/修改自己的评价结果"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"comment": "源自 e41；③frm先于to→forward；跨主体门禁 E-BMJL.结果已提交 落 state_ref"},
    )
    m.add_trans(
        tid="t42", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="已评价", action="评价组长确认结果", role="评价人员",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态由评价中变为已评价", "提交为项目最终评价结果", "评价状态关闭"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3评价确认（确认按钮）",
        note={"comment": "源自 e42；③frm先于to→forward"},
    )
    m.add_trans(
        tid="t43", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="待评价", action="评价组长退回修改", role="评价人员",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态由评价中变为待评价", "当前评价结果保存为历史", "开启下一轮评价"],
        traits=["rollback", "branch"], direction="backward", priority="P1",
        source_ref="20.7.1.3评价确认（退回修改按钮）",
        note={"branch_dimension": "评分方式", "comment": "源自 e43；①退回→backward；退回修改开启下一轮评价，结果措辞差异由 评分方式 分支承载"},
    )

    # E-TASK 审核任务状态
    m.add_trans(
        tid="t44", entity="E-TASK", dimension="审核任务状态",
        frm=None, to="待审核", action="提交审核任务", role="项目管理员",
        preconditions=[],
        expected_results=["审核任务创建并进入待审核状态", "短信通知相关负责人"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.9.1.3增加任务提醒",
        note={"comment": "源自 e44；⓪frm=None→forward"},
    )
    m.add_trans(
        tid="t45", entity="E-TASK", dimension="审核任务状态",
        frm="待审核", to="已审核", action="审核通过", role="审核人员",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "审核任务状态", "待审核")),
            precond(text="审核任务结果=同意", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态由待审核变为已审核"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.9.1.4任务批量处理（同意分支）",
        note={"branch_dimension": "审核任务结果", "comment": "源自 e45；③frm先于to→forward；路径分歧：同意分支"},
    )
    m.add_trans(
        tid="t46", entity="E-TASK", dimension="审核任务状态",
        frm="待审核", to="已退回", action="审核退回", role="审核人员",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "审核任务状态", "待审核")),
            precond(text="审核任务结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态由待审核变为已退回"],
        traits=["branch", "audit"], direction="backward", priority="P1",
        source_ref="20.9.1.4任务批量处理（退回分支）",
        note={"branch_dimension": "审核任务结果", "comment": "源自 e46；①退回→backward；路径分歧：退回分支"},
    )

    # 3.3 自检：target_transition 回填
    # 已通过 tid 字符串精确匹配回填；分支 target_transition 描述已对齐 t02/t02b/t08/t08b/t19/t19b/t23/t23b/t33/t33b/t45/t46 等

    # 3.4 因果
    m.add_causal(
        frm="E-BMJL", to="E-JFTZ",
        desc="报名记录创建后系统自动初始化缴费通知单为未发送；报名审核通过后系统自动发送缴费通知单",
        trigger="报名记录创建/报名审核通过后缴费通知自动初始化与发送",
        trigger_source="expected_results",
        evidence_transitions=["t25", "t26", "t06", "t08"],
        rollback_propagation=False, confidence="high",
        note={"comment": "expected_results 与 §19.1 流程表明写'缴费通知单列由未发送→已发送'；门禁对照：'报名审核通过后方可发送缴费通知'由 t26.precondition state_ref(E-BMJL.报名成功) 表达，不写为约束"},
    )
    m.add_causal(
        frm="E-BMJL", to="E-FY",
        desc="报名记录创建后系统自动初始化费用为待缴费；参加者缴费后费用变为已缴费",
        trigger="报名记录创建后费用自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t27", "t28", "t06"],
        rollback_propagation=False, confidence="high",
        note={"comment": "§19.1 报名行 费用状态列 待缴费 首次出现；门禁对照：缴费前需缴费通知已发送由 t28.precondition state_ref(E-JFTZ.已发送) 表达"},
    )
    m.add_causal(
        frm="E-BMJL", to="E-FP",
        desc="报名记录创建后系统自动初始化发票为待开票；缴费后财务人员开具发票",
        trigger="报名记录创建后发票自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t30", "t31", "t06"],
        rollback_propagation=False, confidence="high",
        note={"comment": "§19.1 报名行 发票状态列 待开票 首次出现；门禁对照：开票前需已缴费由 t31.precondition state_ref(E-FY.已缴费) 表达"},
    )
    m.add_causal(
        frm="E-XM", to="E-YT",
        desc="能力验证计划发布后系统自动初始化预通知为未发送",
        trigger="能力验证计划发布后预通知自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t22", "t02"],
        rollback_propagation=False, confidence="high",
        note={"comment": "§19.1 能力验证计划发布行 预通知状态列 未发送 首次出现"},
    )
    m.add_causal(
        frm="E-BMJL", to="E-BMYP",
        desc="报名记录创建后系统自动初始化报名记录样品为待发样",
        trigger="报名记录创建后样品记录自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t20", "t06"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "inferred：§19.1 表未显式列出样品记录初始化动作，按 §19.3 报名记录样品状态枚举与流程语义推导；门禁对照：发放前需项目样品已核查由 t21.precondition state_ref(E-YP.已核查) 表达"},
    )
    m.add_causal(
        frm="E-XM", to="E-YP",
        desc="项目进入报名中阶段后样品制备人员创建项目样品并登记为待核查",
        trigger="项目报名中后样品制备并登记",
        trigger_source="expected_results",
        evidence_transitions=["t17", "t02"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "inferred：§19.1 表未显式列出样品创建动作，按 缴费行 样品状态=待核查 推导；门禁对照：样品核查前需待核查由 t18.precondition state_ref(E-YP.待核查) 表达"},
    )
    m.add_causal(
        frm="E-BMJL", to="E-PJ",
        desc="报名记录结果已提交后评价组长完善评价项目并启动评价",
        trigger="结果已提交后启动评价",
        trigger_source="expected_results",
        evidence_transitions=["t40", "t41", "t11"],
        rollback_propagation=False, confidence="high",
        note={"comment": "§20.7 项目评价语义明写'评价前评价组长需要完善'；门禁对照：评价前需结果已提交由 t40/t41.precondition state_ref(E-BMJL.结果已提交) 表达"},
    )
    m.add_causal(
        frm="E-PJ", to="E-BMJL",
        desc="评价完成后策划人员方可编制结果报告，报名记录进入报告/证书审核中",
        trigger="评价完成后进入报告编制",
        trigger_source="expected_results",
        evidence_transitions=["t13", "t42"],
        rollback_propagation=False, confidence="high",
        note={"comment": "§19.1 报告编制阶段位于评价之后；门禁对照：编制报告前需评价已完由 t13.precondition state_ref(E-PJ.已评价) 表达"},
    )

    # ===== Step 4: 约束 =====

    # invalid - 明文禁止的状态转换
    m.add_invalid(
        iid="i01", entity="E-STD",
        frm="启用", to="启用",
        reason="标准库启用状态下操作列不显示【启用】按钮，仅显示【停用】按钮",
        source_ref="20.4.2.5停用/启用标准库",
    )
    m.add_invalid(
        iid="i02", entity="E-STD",
        frm="停用", to="停用",
        reason="标准库停用状态下操作列不显示【停用】按钮，仅显示【启用】按钮",
        source_ref="20.4.2.5停用/启用标准库",
    )
    m.add_invalid(
        iid="i03", entity="E-LAB",
        frm="启用", to="启用",
        reason="实验室启用状态下操作列不显示【启用】按钮，仅显示【停用】按钮",
        source_ref="20.4.1.1实验室列表与查询",
    )
    m.add_invalid(
        iid="i04", entity="E-LAB",
        frm="停用", to="停用",
        reason="实验室停用状态下操作列不显示【停用】按钮，仅显示【启用】按钮",
        source_ref="20.4.1.1实验室列表与查询",
    )
    m.add_invalid(
        iid="i05", entity="E-LAB",
        frm="启用", to="待审核",
        reason="启用状态下不显示【审核】按钮，仅待审核状态显示【审核】按钮",
        source_ref="20.4.1.1实验室列表与查询；20.4.1.2实验室审核",
    )
 

    # XC - 跨实体约束
    # 镜像：E-BMJL.报名成功 → E-JFTZ.已发送 (生产者≠持有者，target_condition=新值)
    m.add_xc(
        xid="x01", source_entity="E-BMJL",
        source_transition="t08", source_state="报名成功",
        target_entity="E-JFTZ", target_dimension="缴费通知单状态",
        target_transition="t26", target_condition="已发送",
        xc_source="联动",
        desc="报名审核通过后联动发送缴费通知单，缴费通知单状态由未发送变为已发送",
        source_ref="19.1实施阶段-报名审核行（缴费通知单列已发送）",
    )
    # 镜像：E-XM.报名中 → E-BMJL.报名待审核 (target_condition=新值)
    m.add_xc(
        xid="x02", source_entity="E-XM",
        source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t06", target_condition="报名待审核",
        xc_source="联动",
        desc="能力验证项目进入报名中后联动开启报名记录创建，新记录初始化为报名待审核",
        source_ref="19.1实施阶段-能力验证计划发布行；19.1实施阶段-报名行",
    )
    # 镜像：E-XM.报名中 → E-YT.未发送
    m.add_xc(
        xid="x03", source_entity="E-XM",
        source_transition="t02", source_state="报名中",
        target_entity="E-YT", target_dimension="预通知状态",
        target_transition="t22", target_condition="未发送",
        xc_source="联动",
        desc="能力验证计划发布后联动初始化预通知为未发送",
        source_ref="19.1实施阶段-能力验证计划发布行（预通知状态列未发送）",
    )
    # 镜像：E-XM.报名中 → E-YP.待核查
    m.add_xc(
        xid="x04", source_entity="E-XM",
        source_transition="t02", source_state="报名中",
        target_entity="E-YP", target_dimension="样品状态",
        target_transition="t17", target_condition="待核查",
        xc_source="联动",
        desc="项目进入报名中后联动创建项目样品并初始化为待核查",
        source_ref="19.1实施阶段-缴费行（样品状态首次出现待核查）",
    )
    # 镜像：E-BMJL.报名待审核 → E-JFTZ.未发送
    m.add_xc(
        xid="x05", source_entity="E-BMJL",
        source_transition="t06", source_state="报名待审核",
        target_entity="E-JFTZ", target_dimension="缴费通知单状态",
        target_transition="t25", target_condition="未发送",
        xc_source="联动",
        desc="报名记录创建后联动初始化缴费通知单为未发送",
        source_ref="19.1实施阶段-报名行（缴费通知单列）",
    )
    # 镜像：E-BMJL.报名待审核 → E-FY.待缴费
    m.add_xc(
        xid="x06", source_entity="E-BMJL",
        source_transition="t06", source_state="报名待审核",
        target_entity="E-FY", target_dimension="费用状态",
        target_transition="t27", target_condition="待缴费",
        xc_source="联动",
        desc="报名记录创建后联动初始化费用记录为待缴费",
        source_ref="19.1实施阶段-报名行（费用状态列）",
    )
    # 镜像：E-BMJL.报名待审核 → E-FP.待开票
    m.add_xc(
        xid="x07", source_entity="E-BMJL",
        source_transition="t06", source_state="报名待审核",
        target_entity="E-FP", target_dimension="发票状态",
        target_transition="t30", target_condition="待开票",
        xc_source="联动",
        desc="报名记录创建后联动初始化发票记录为待开票",
        source_ref="19.1实施阶段-报名行（发票状态列）",
    )
    # 镜像：E-BMJL.报名成功 → E-BMYP.待发样
    m.add_xc(
        xid="x08", source_entity="E-BMJL",
        source_transition="t08", source_state="报名成功",
        target_entity="E-BMYP", target_dimension="报名记录样品状态",
        target_transition="t20", target_condition="待发样",
        xc_source="联动",
        desc="报名审核通过后联动初始化报名记录样品为待发样",
        source_ref="19.3报名记录样品状态",
    )
    # 4.5判：E-PJ.已评价 → E-BMJL.报告/证书审核中 (因果 Q1: X 变直接致 Y 变，Y 需操作但已由 precondition 表达)
    m.add_xc(
        xid="x09", source_entity="E-PJ",
        source_transition="t42", source_state="已评价",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t13", target_condition="报告/证书审核中",
        xc_source="4.5判",
        desc="评价完成后策划人员方可编制结果报告，使报名记录进入报告/证书审核中",
        source_ref="19.1报告编制和结果通知-编制结果报告行；20.7.1.3评价确认",
    )
    # 4.5判：E-YP.已核查 → E-BMYP.已确认 (因果 Q1: 已由 t21.precondition 表达)
    m.add_xc(
        xid="x10", source_entity="E-YP",
        source_transition="t18", source_state="已核查",
        target_entity="E-BMYP", target_dimension="报名记录样品状态",
        target_transition="t21", target_condition="已确认",
        xc_source="4.5判",
        desc="项目样品核查完成后方可发放报名记录样品，报名记录样品状态变为已确认",
        source_ref="19.1实施阶段-样品发放行",
    )
    # 4.5判：E-FY.已缴费 → E-FP.已开票
    m.add_xc(
        xid="x11", source_entity="E-FY",
        source_transition="t28", source_state="已缴费",
        target_entity="E-FP", target_dimension="发票状态",
        target_transition="t31", target_condition="已开票",
        xc_source="4.5判",
        desc="参加者缴费完成后方可开具发票，发票状态由待开票变为已开票",
        source_ref="19.1实施阶段-发票开具行",
    )
    # 4.5判：E-JFTZ.已发送 → E-FY.已缴费
    m.add_xc(
        xid="x12", source_entity="E-JFTZ",
        source_transition="t26", source_state="已发送",
        target_entity="E-FY", target_dimension="费用状态",
        target_transition="t28", target_condition="已缴费",
        xc_source="4.5判",
        desc="缴费通知单发送后方可进行缴费，费用状态由待缴费变为已缴费",
        source_ref="19.1实施阶段-缴费行",
    )
    # 4.5判：E-YT.已发送 → E-BMJL.结果待提交
    m.add_xc(
        xid="x13", source_entity="E-YT",
        source_transition="t23", source_state="已发送",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t10", target_condition="结果待提交",
        xc_source="4.5判",
        desc="预通知发送后报名记录进入结果待提交阶段",
        source_ref="19.1实施阶段-能力验证预通知行",
    )
    # 4.5判：E-BMJL.报告/证书已发布 → E-XM.已结束
    m.add_xc(
        xid="x14", source_entity="E-BMJL",
        source_transition="t16", source_state="报告/证书已发布",
        target_entity="E-XM", target_dimension="项目状态",
        target_transition="t05", target_condition="已结束",
        xc_source="4.5判",
        desc="报名记录报告/证书发布后项目方可结束",
        source_ref="19.1报告编制和结果通知-发放结果报告和证书行",
    )
    # 4.5判：E-LAB.启用 → E-BMJL.报名待审核 (实验室启用为报名前置条件)
    m.add_xc(
        xid="x15", source_entity="E-LAB",
        source_transition="t33", source_state="启用",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t06", target_condition="报名待审核",
        xc_source="4.5判",
        desc="实验室启用后方可用于项目报名",
        source_ref="20.3.1实验室信息（机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名）",
    )
    # 分支差异：项目类型=测量审核 → 跳过待开始状态
    m.add_xc(
        xid="x16", source_entity="E-XM",
        source_transition="t02b", source_state="报名中",
        target_entity="E-XM", target_dimension="项目状态",
        target_transition="t02b", target_condition="报名中",
        xc_source="分支差异",
        desc="测量审核分支下项目创建即进入报名中，跳过待开始状态",
        source_ref="19.2项目准备阶段-受理用户测量审核报名行",
    )

    # BR - 业务规则
    m.add_br(
        bid="b01", category="notification",
        desc="报名审核通过后退回修改均需向参加者发送短信：通过则发送'您xxx项目的报名信息审核通过，请知悉'；退回修改则发送'您xxx项目的报名信息审核未通过，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2操作节点增加用户短信通知",
        note={"role": "r05", "comment": "signal_type 命中'操作节点...通知'；category 判通知；constrained_entity=E-BMJL"},
        branch_dimensions=["报名审核结果"],
        constrained_entity="E-BMJL",
    )
    m.add_br(
        bid="b02", category="notification",
        desc="发样后向参加者发送短信'您xxxx项目的样品已发出，请知悉'",
        entities_involved=["E-BMYP"], source_ref="20.5.3.2操作节点增加用户短信通知",
        note={"role": "r07", "comment": "category 判通知；constrained_entity=E-BMYP"},
        constrained_entity="E-BMYP",
    )
    m.add_br(
        bid="b03", category="notification",
        desc="测试结果审核通过/退回均需向参加者发送短信：通过则发送'您xxxx项目的测试报告审核通过，请知悉'；退回则发送'您xxxx项目测试报告审核未通过，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2操作节点增加用户短信通知",
        note={"role": "r05", "comment": "category 判通知；constrained_entity=E-BMJL"},
        constrained_entity="E-BMJL",
    )
    m.add_br(
        bid="b04", category="notification",
        desc="结果通知单发布后向参加者发送短信'您xxx项目的结果通知单已发布，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2操作节点增加用户短信通知",
        note={"role": "r05", "comment": "category 判通知；constrained_entity=E-BMJL"},
        constrained_entity="E-BMJL",
    )
    m.add_br(
        bid="b05", category="notification",
        desc="系统每天上午9点对系统中的证书信息进行查询，距到期时间等于30天时通过邮件方式对用户进行提醒，并抄送项目管理员；提醒标题为'证书到期提醒'，提醒内容为'您证书编号为xxxx的证书将于2025-01-01到期，请知悉'",
        entities_involved=["E-ZS"], source_ref="20.5.2.3增加证书到期前30天提醒功能；20.6.2.3",
        restrictive=True,
        note={"comment": "signal_type 命中'每天上午9点'；category 判通知；系统行为 BR，entities_involved=作用目标 E-ZS"},
    )
    m.add_br(
        bid="b06", category="notification",
        desc="用户通过表单或审核一个已存在的任务时生成新的审核任务，系统发送短信通知相关负责人；短信内容'您有一个新的xxx审核任务，请及时处理'，xxx为审核类型名称",
        entities_involved=["E-TASK"], source_ref="20.9.1.3增加任务提醒",
        note={"comment": "signal_type 命中'发送短信通知'；category 判通知；系统行为 BR"},
        branch_dimensions=["审核任务结果"],
    )
    m.add_br(
        bid="b07", category="display",
        desc="对新旧通知内容进行区分显示，15天内发布的通知在内容前标注'new'标识，超过15天后此标识自动隐藏",
        entities_involved=["E-MSG"], source_ref="20.2.1通知公告",

        note={"comment": "signal_type 命中'15天内...标注'；category 判 display；constrained_entity=E-MSG"},
        constrained_entity="E-MSG",
    )
    m.add_br(
        bid="b08", category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能",
        restrictive=True,
        note={"role": "r05", "comment": "signal_type 命中'不可同时为空'；category 判 validation；constrained_entity=E-XM"},
        constrained_entity="E-XM",
    )
    m.add_br(
        bid="b09", category="validation",
        desc="消息发送时未结束的项目才可以进行消息发送",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能",
        restrictive=True,
        note={"role": "r05", "comment": "signal_type 命中'未结束的项目...才可'；category 判 validation；constrained_entity=E-XM"},
        constrained_entity="E-XM",
    )
    m.add_br(
        bid="b10", category="validation",
        desc="删除测试项前会做前置判断，含有子项的数据不可以删除",
        entities_involved=["E-CS", "E-ZLY"], source_ref="20.4.2.10删除测试项；20.4.3.4删除测试项",
        restrictive=True,
        note={"role": "r12", "comment": "signal_type 命中'不可以删除'；category 判 validation；多实体 BR 对称规则，constrained_entity 任一代表实体"},
        constrained_entity="E-CS",
    )
    m.add_br(
        bid="b11", category="validation",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-STD"], source_ref="20.4.2.5停用/启用标准库",
        restrictive=True,
        note={"role": "r12", "comment": "signal_type 命中'停用...不可被选择'；category 判 validation；constrained_entity=E-STD"},
        constrained_entity="E-STD",
    )
    m.add_br(
        bid="b12", category="validation",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-LAB", "E-BMJL"], source_ref="20.3.1实验室信息",
        restrictive=True,
        note={"role": "r12", "comment": "signal_type 命中'需经...审核通过后方可'；category 判 validation；多实体 BR，constrained_entity=E-LAB"},
        constrained_entity="E-LAB",
    )
    m.add_br(
        bid="b13", category="validation",
        desc="实验室审核退回修改时必须填写审核意见",
        entities_involved=["E-LAB"], source_ref="20.4.1.2实验室审核",
        restrictive=True,
        note={"role": "r12", "comment": "signal_type 命中'必须填写'；category 判 validation；constrained_entity=E-LAB"},
        branch_dimensions=["实验室审核结果"],
        constrained_entity="E-LAB",
    )
    m.add_br(
        bid="b14", category="computation",
        desc="退款金额不可大于当前缴费金额；退款金额做累加处理；实际付款=付款金额-退款金额；退款金额使用红色字体且大于0时显示",
        entities_involved=["E-FY"], source_ref="20.10.2.3缴费单退款",
        restrictive=True,
        note={"role": "r11", "comment": "signal_type 命中'不可大于'；category 判 computation（含累计计算）；constrained_entity=E-FY"},
        constrained_entity="E-FY",
    )
    m.add_br(
        bid="b15", category="validation",
        desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"], source_ref="20.5.1.6默认填充技术主管实验室负责人授权签字人；20.6.1.4",
        note={"role": "r05", "comment": "signal_type 命中'有且仅有一个时默认填充'；category 判 validation；constrained_entity=E-XM"},
        constrained_entity="E-XM",
    )
    m.add_br(
        bid="b16", category="authorization",
        desc="新建项目时第一个被选择的评价人员默认作为评价组长；评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"], source_ref="20.7项目列表；20.7.1.2协同评价",
        restrictive=True,
        note={"role": "r08", "comment": "signal_type 命中'只能...不能'；category 判 authorization；constrained_entity=E-PJ"},
        constrained_entity="E-PJ",
    )
    m.add_br(
        bid="b17", category="validation",
        desc="项目批量处理时只有已上传对应文件且未提交审核的报名记录才可以被选定提交审核",
        entities_involved=["E-BMJL"], source_ref="20.5.1.3项目批量操作",
        restrictive=True,
        note={"role": "r05", "comment": "signal_type 命中'只有...才可'；category 判 validation；constrained_entity=E-BMJL"},
        constrained_entity="E-BMJL",
    )
    m.add_br(
        bid="b18", category="validation",
        desc="为已结束的项目记录提供文件整理按钮；整理完成后显示查看归档按钮",
        entities_involved=["E-XM"], source_ref="20.5.1.1文件整理；20.6.1.1文件整理",
        restrictive=True,
        note={"role": "r05", "comment": "signal_type 命中'为已结束...提供'；category 判 validation；constrained_entity=E-XM"},
        constrained_entity="E-XM",
    )
    m.add_br(
        bid="b19", category="validation",
        desc="已报名项目支持多次付款，不对付款金额进行校验限制",
        entities_involved=["E-FY"], source_ref="20.5.2.1已报名项目增加多次付款功能；20.6.2.1",
        note={"role": "r13", "comment": "signal_type 命中'不对...进行校验限制'；category 判 validation；constrained_entity=E-FY"},
        constrained_entity="E-FY",
    )
    m.add_br(
        bid="b20", category="validation",
        desc="发票上传支持多次分批上传；可移除文件（表单提交后生效）",
        entities_involved=["E-FP"], source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传",
        note={"role": "r11", "comment": "category 判 validation；constrained_entity=E-FP"},
        constrained_entity="E-FP",
    )
    m.add_br(
        bid="b21", category="authorization",
        desc="信息发送记录只有系统管理员和项目管理员可以查看",
        entities_involved=["E-MSG"], source_ref="20.4.4.1信息发送记录",
        restrictive=True,
        note={"role": "r12, r05", "comment": "signal_type 命中'只有...可以'；category 判 authorization；constrained_entity=E-MSG"},
        constrained_entity="E-MSG",
    )
    m.add_br(
        bid="b22", category="usability",
        desc="删除操作时系统提示警示框'您确认删除记录吗？操作不可恢复！'，用户点击确认后才执行删除",
        entities_involved=["E-LAB", "E-STD", "E-CS", "E-ZLY"], source_ref="3.6可用性要求-完备提示信息",

        note={"comment": "signal_type 命中'提示信息...确认后...执行'；category 判 usability；多实体对称规则，constrained_entity=E-LAB 为代表实体"},
        constrained_entity="E-LAB",
    )
    m.add_br(
        bid="b23", category="computation",
        desc="评价结果统计规则由低值与高值组成，判断规则为大于等于低值、小于高值；用于动态统计报名实验室得分的区间分布",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认-调整统计规则",
        note={"role": "r08", "comment": "signal_type 命中'大于等于...小于'；category 判 computation；constrained_entity=E-PJ；含 评分方式 分支维度"},
        branch_dimensions=["评分方式"],
        constrained_entity="E-PJ",
    )
    m.add_br(
        bid="b24", category="validation",
        desc="测量审核结果通知单审批流程合并为一个流程，流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-TASK"], source_ref="20.9.1.1测量审核结果通知单审核流程优化",
        note={"role": "r14", "comment": "category 判 validation；constrained_entity=E-TASK；含 项目类型 分支维度"},
        branch_dimensions=["项目类型"],
        constrained_entity="E-TASK",
    )
    m.add_br(
        bid="b25", category="authorization",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
        entities_involved=["E-TASK"], source_ref="20.9.1.6增加自定义流程",
        restrictive=True,
        note={"role": "r14", "comment": "signal_type 命中'4个以内'；category 判 authorization；constrained_entity=E-TASK"},
        constrained_entity="E-TASK",
    )
    m.add_br(
        bid="b26", category="validation",
        desc="审核流程列表查询区域支持按任务类型与创建时间筛选，并支持结果导出",
        entities_involved=["E-TASK"], source_ref="20.9.1.5审批流程列表导出",
        note={"role": "r14", "comment": "category 判 validation；constrained_entity=E-TASK"},
        constrained_entity="E-TASK",
    )
    m.add_br(
        bid="b27", category="validation",
        desc="审核流程详情页完整展示审核流程，并用不同的颜色对各个状态的节点进行标记",
        entities_involved=["E-TASK"], source_ref="20.9.1.7优化流程信息展示效果",

        note={"role": "r14", "comment": "signal_type 命中'不同颜色标记'；category 判 display；constrained_entity=E-TASK"},
        constrained_entity="E-TASK",
    )
    m.add_br(
        bid="b28", category="validation",
        desc="对关键操作实施留痕机制，系统自动记录操作者身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-XM", "E-BMJL", "E-LAB", "E-STD", "E-TASK"], source_ref="20.11.1.2安全性相关内容优化",
        restrictive=True,
        note={"comment": "signal_type 命中'不可篡改'；category 判 validation；多实体对称规则，constrained_entity=E-XM 为代表实体"},
        constrained_entity="E-XM",
    )
    m.add_br(
        bid="b29", category="validation",
        desc="对往年项目数据进行分析整理并导入到系统中为数据分析提供关键数据",
        entities_involved=["E-XM"], source_ref="20.11.1.1历史数据列表",
        note={"role": "r12", "comment": "category 判 validation；constrained_entity=E-XM"},
        constrained_entity="E-XM",
    )
    m.add_br(
        bid="b30", category="validation",
        desc="评价结果导出按钮位于项目列表操作列，评价人员点击后下载评价结果",
        entities_involved=["E-PJ"], source_ref="20.7.1.4评价结果导出",
        note={"role": "r08", "comment": "category 判 validation；constrained_entity=E-PJ"},
        constrained_entity="E-PJ",
    )

    return m

