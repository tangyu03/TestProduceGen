"""网数中心能力验证服务平台升级维护项目 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116",
        document_scope="§19.1能力验证提供者流程（完整台账）+ §19.3项目状态分析枚举 + §20状态相关功能需求（实验室/标准库/评价/审核任务/财务退款/系统行为BR）。§19.2测量审核提供者流程结构平行，关键差异：项目创建顺序为受理报名→设计方案编制（非设计方案编制→计划发布→报名），含作业指导书编制审核环节，未完整建模。",
    )
    # ===== 事件台账（§2）=====
    # §19.1 方案设计阶段
    m.add_event("e01", entity="E-XM", dimension="项目状态", action="设计方案编制", actor="策划人员", precondition="初始", consequence="待开始", source_ref="19.1方案设计阶段")
    # §19.1 实施阶段：能力验证计划发布（一动作多状态面→拆行）
    m.add_event("e02", entity="E-XM", dimension="项目状态", action="能力验证计划发布", actor="项目管理员", precondition="待开始", consequence="报名中", source_ref="19.1实施阶段")
    m.add_event("e03", entity="E-YTZ", dimension="通知状态", action="能力验证计划发布", actor="项目管理员", precondition="初始", consequence="未发送", source_ref="19.1实施阶段")
    # §19.1 实施阶段：报名（一动作多状态面→拆行；缴费通知单/费用/发票为系统自动初始化，inferred）
    m.add_event("e04", entity="E-BM", dimension="报名记录状态", action="报名", actor="能力验证参加者", precondition="None；E-XM.报名中", consequence="报名待审核", source_ref="19.1实施阶段")
    m.add_event("e05", entity="E-JFTZ", dimension="缴费通知单状态", action="报名", actor="能力验证参加者", precondition="初始", consequence="未发送", source_ref="19.1实施阶段；inferred:报名记录创建后系统自动初始化缴费通知单")
    m.add_event("e06", entity="E-FY", dimension="费用状态", action="报名", actor="能力验证参加者", precondition="初始", consequence="待缴费", source_ref="19.1实施阶段；inferred:报名记录创建后系统自动初始化费用记录")
    m.add_event("e07", entity="E-FP", dimension="发票状态", action="报名", actor="能力验证参加者", precondition="初始", consequence="待开票", source_ref="19.1实施阶段；inferred:报名记录创建后系统自动初始化发票记录")
    # §19.1 实施阶段：报名审核（通过/退回分支；通过时缴费通知单自动发送）
    m.add_event("e08", entity="E-BM", dimension="报名记录状态", action="报名审核", actor="项目管理员", precondition="报名待审核", consequence="报名成功", source_ref="19.1实施阶段")
    m.add_event("e09", entity="E-BM", dimension="报名记录状态", action="报名审核", actor="项目管理员", precondition="报名待审核", consequence="报名退回", source_ref="19.1实施阶段")
    m.add_event("e10", entity="E-JFTZ", dimension="缴费通知单状态", action="报名审核", actor="项目管理员", precondition="未发送", consequence="已发送", source_ref="19.1实施阶段；inferred:报名审核通过后系统自动发送缴费通知单")
    # §19.1 实施阶段：缴费
    m.add_event("e11", entity="E-FY", dimension="费用状态", action="缴费", actor="能力验证参加者", precondition="待缴费", consequence="已缴费", source_ref="19.1实施阶段")
    # §19.1 实施阶段：样品制备（inferred: 缴费行样品状态=待核查，推导样品制备为创建动作）
    m.add_event("e12", entity="E-YP", dimension="样品状态", action="样品制备", actor="样品制备人员", precondition="初始", consequence="待核查", source_ref="19.1实施阶段；inferred:缴费行已显示样品状态=待核查")
    # §19.1 实施阶段：发票开具
    m.add_event("e13", entity="E-FP", dimension="发票状态", action="发票开具", actor="财务管理人员", precondition="待开票", consequence="已开票", source_ref="19.1实施阶段")
    # §19.1 实施阶段：能力验证预通知（一动作多状态面→拆行；报名记录状态报名成功→结果待提交）
    m.add_event("e14", entity="E-YTZ", dimension="通知状态", action="能力验证预通知", actor="项目管理员", precondition="未发送", consequence="已发送", source_ref="19.1实施阶段")
    m.add_event("e15", entity="E-BM", dimension="报名记录状态", action="能力验证预通知", actor="项目管理员", precondition="报名成功", consequence="结果待提交", source_ref="19.1实施阶段")
    # §19.1 实施阶段：预通知确认（inferred: §19.4参加者流程，状态列由已发送变为已确认）
    m.add_event("e16", entity="E-YTZ", dimension="通知状态", action="预通知确认", actor="能力验证参加者", precondition="已发送", consequence="已确认", source_ref="19.4参加者流程；inferred:状态列由已发送/待确认变为已确认")
    # §19.1 实施阶段：样品核查（样品状态待核查→已核查，并进入待发样）
    m.add_event("e17", entity="E-YP", dimension="样品状态", action="样品核查", actor="样品管理员", precondition="待核查", consequence="已核查", source_ref="19.1实施阶段")
    m.add_event("e18", entity="E-YP", dimension="样品状态", action="样品核查", actor="样品管理员", precondition="已核查", consequence="待发样", source_ref="19.1实施阶段；inferred:核查后进入待发样（状态列显示已核查、待发样）")
    # §19.1 实施阶段：样品发放,作业指导书发送
    m.add_event("e19", entity="E-YP", dimension="样品状态", action="样品发放", actor="项目管理员", precondition="待发样", consequence="已发样", source_ref="19.1实施阶段")
    # §19.1 实施阶段：参加者测试与结果提交（样品已发样→已还样；报名记录结果待提交→结果已提交）
    m.add_event("e20", entity="E-BM", dimension="报名记录状态", action="参加者测试与结果提交", actor="能力验证参加者", precondition="结果待提交", consequence="结果已提交", source_ref="19.1实施阶段")
    m.add_event("e21", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交", actor="能力验证参加者", precondition="已发样", consequence="已还样", source_ref="19.1实施阶段；inferred:参加者测试后还样（状态列显示已还样）")
    # §19.1 报告编制和结果通知：结果报告回收（结果已提交/结果退回修改）
    m.add_event("e22", entity="E-BM", dimension="报名记录状态", action="结果报告回收", actor="项目管理员", precondition="结果已提交", consequence="结果退回修改", source_ref="19.1报告编制和结果通知；分支:结果退回修改")
    # §20.7.1.1 评价组长完善测试项目及评价细则（评价创建→待完善→待评价）
    m.add_event("e23", entity="E-PJ", dimension="评价状态", action="评价组长完善", actor="评价人员", precondition="初始", consequence="待完善", source_ref="20.7.1.1测试项目评价细则完善；inferred:评价组长为评价人员角色")
    m.add_event("e24", entity="E-PJ", dimension="评价状态", action="评价组长完善", actor="评价人员", precondition="待完善", consequence="待评价", source_ref="20.7.1.1测试项目评价细则完善")
    # §19.1/§20.7.1.2 评价人员进行评价（precondition含跨主体门禁E-BM.结果已提交）
    m.add_event("e25", entity="E-PJ", dimension="评价状态", action="评价人员评价", actor="评价人员", precondition="待评价；E-BM.结果已提交", consequence="评价中", source_ref="20.7.1.2协同评价")
    # §20.7.1.2 评价人员提交评价结果（inferred:评价完成后提交至待确认）
    m.add_event("e26", entity="E-PJ", dimension="评价状态", action="评价人员提交", actor="评价人员", precondition="评价中", consequence="待确认", source_ref="20.7.1.2协同评价；inferred:评价完成后提交至组长确认")
    # §19.1 报告编制和结果通知：对评价进行统计
    m.add_event("e27", entity="E-PJ", dimension="评价状态", action="评价统计", actor="统计人员", precondition="评价中", consequence="评价中", source_ref="19.1报告编制和结果通知；自环:统计不改变评价状态")
    # §20.7.1.3 评价组长确认（确认→已确认；退回修改→重新评价）
    m.add_event("e28", entity="E-PJ", dimension="评价状态", action="评价组长确认", actor="评价人员", precondition="待确认", consequence="已确认", source_ref="20.7.1.3评价确认；inferred:评价组长为评价人员角色")
    m.add_event("e29", entity="E-PJ", dimension="评价状态", action="退回修改", actor="评价人员", precondition="待确认", consequence="评价中", source_ref="20.7.1.3评价确认")
    # §19.1 报告编制和结果通知：编制结果报告（报名记录→报告/证书审核中）
    m.add_event("e30", entity="E-BM", dimension="报名记录状态", action="编制结果报告", actor="策划人员", precondition="结果已提交", consequence="报告/证书审核中", source_ref="19.1报告编制和结果通知")
    # §19.1/§20.9 技术主管审核报告（审核任务创建→待审核→已通过）
    m.add_event("e31", entity="E-TASK", dimension="审核任务状态", action="提交审核", actor="策划人员", precondition="初始", consequence="待审核", source_ref="19.1报告编制和结果通知；inferred:编制结果报告后提交审核")
    m.add_event("e32", entity="E-TASK", dimension="审核任务状态", action="技术主管审核", actor="技术主管", precondition="待审核", consequence="已通过", source_ref="19.1报告编制和结果通知")
    m.add_event("e33", entity="E-TASK", dimension="审核任务状态", action="技术主管审核", actor="技术主管", precondition="待审核", consequence="已退回", source_ref="19.1报告编制和结果通知；分支:审核退回")
    # §19.1 报告编制和结果通知：授权签字人批准报告/结果通知单
    m.add_event("e34", entity="E-TASK", dimension="审核任务状态", action="授权签字人批准", actor="授权签字人", precondition="待审核", consequence="已通过", source_ref="19.1报告编制和结果通知")
    # §19.1 报告编制和结果通知：实验室负责人批准证书
    m.add_event("e35", entity="E-TASK", dimension="审核任务状态", action="实验室负责人批准", actor="实验室负责人", precondition="待审核", consequence="已通过", source_ref="19.1报告编制和结果通知")
    # §19.1 报告编制和结果通知：发放结果报告和证书（报名记录→报告/证书已发布）
    m.add_event("e36", entity="E-BM", dimension="报名记录状态", action="发放结果报告和证书", actor="项目管理员", precondition="报告/证书审核中", consequence="报告/证书已发布", source_ref="19.1报告编制和结果通知")
    # §19.3 项目状态枚举推进（inferred: 阶段表未显式标注后续项目状态迁移，按枚举顺序推导）
    m.add_event("e37", entity="E-XM", dimension="项目状态", action="进入实施", actor="项目管理员", precondition="报名中", consequence="进行中", source_ref="19.3项目状态分析；inferred:报名结束后进入进行中")
    m.add_event("e38", entity="E-XM", dimension="项目状态", action="进入报告审核", actor="策划人员", precondition="进行中", consequence="报告审核中", source_ref="19.3项目状态分析；inferred:编制结果报告时进入报告审核中")
    m.add_event("e39", entity="E-XM", dimension="项目状态", action="项目结束", actor="项目管理员", precondition="报告审核中", consequence="已结束", source_ref="19.3项目状态分析；inferred:发放结果报告和证书后项目结束")
    # §19.1 实施阶段：参加者撤销报名（状态列显示已撤销）
    m.add_event("e40", entity="E-BM", dimension="报名记录状态", action="撤销报名", actor="能力验证参加者", precondition="报名待审核", consequence="已撤销", source_ref="19.1实施阶段；inferred:状态列显示报名待审核/已撤销")
    # §20.3.1/20.4.1 实验室信息状态流转
    m.add_event("e41", entity="E-LAB", dimension="实验室状态", action="实验室新增", actor="系统管理人员", precondition="初始", consequence="待审核", source_ref="20.3.1实验室信息；20.4.1.2实验室审核")
    m.add_event("e42", entity="E-LAB", dimension="实验室状态", action="实验室审核", actor="系统管理人员", precondition="待审核", consequence="启用", source_ref="20.4.1.2实验室审核；分支:审核通过")
    m.add_event("e43", entity="E-LAB", dimension="实验室状态", action="实验室审核", actor="系统管理人员", precondition="待审核", consequence="已退回", source_ref="20.4.1.2实验室审核；分支:退回修改")
    m.add_event("e44", entity="E-LAB", dimension="实验室状态", action="停用实验室", actor="系统管理人员", precondition="启用", consequence="停用", source_ref="20.4.1.1实验室列表与查询")
    m.add_event("e45", entity="E-LAB", dimension="实验室状态", action="启用实验室", actor="系统管理人员", precondition="停用", consequence="启用", source_ref="20.4.1.1实验室列表与查询")
    m.add_event("e46", entity="E-LAB", dimension="实验室状态", action="实验室修改", actor="系统管理人员", precondition="启用", consequence="待审核", source_ref="20.4.1.3实验室修改；inferred:修改后需重新审核")
    # §20.4.2 标准库状态流转
    m.add_event("e47", entity="E-STD", dimension="标准库状态", action="新增标准库", actor="系统管理人员", precondition="初始", consequence="启用", source_ref="20.4.2.2新增标准库")
    m.add_event("e48", entity="E-STD", dimension="标准库状态", action="停用标准库", actor="系统管理人员", precondition="启用", consequence="停用", source_ref="20.4.2.5停用启用标准库")
    m.add_event("e49", entity="E-STD", dimension="标准库状态", action="启用标准库", actor="系统管理人员", precondition="停用", consequence="启用", source_ref="20.4.2.5停用启用标准库")
    # §20.10.2.3 缴费单退款（费用已缴费→已退款，inferred:退款后费用状态变更）
    m.add_event("e50", entity="E-FY", dimension="费用状态", action="缴费单退款", actor="财务管理人员", precondition="已缴费", consequence="已退款", source_ref="20.10.2.3缴费单退款；inferred:退款后费用状态变为已退款")
    # §20.9.1.4 任务批量处理（批量审核通过/退回）
    m.add_event("e51", entity="E-TASK", dimension="审核任务状态", action="批量审核", actor="技术主管", precondition="待审核", consequence="已通过", source_ref="20.9.1.4任务批量处理；分支:同意")
    m.add_event("e52", entity="E-TASK", dimension="审核任务状态", action="批量审核", actor="技术主管", precondition="待审核", consequence="已退回", source_ref="20.9.1.4任务批量处理；分支:退回")
    # §20.5.2.1 已报名项目增加多次付款功能（自环:已缴费→已缴费，不对付款金额校验）
    m.add_event("e53", entity="E-FY", dimension="费用状态", action="多次付款", actor="能力验证参加者", precondition="已缴费", consequence="已缴费", source_ref="20.5.2.1已报名项目增加多次付款功能")
    # §20.10.2.2 修改发票上传功能支持多次分批上传（自环:已开票→已开票）
    m.add_event("e54", entity="E-FP", dimension="发票状态", action="分批上传发票", actor="财务管理人员", precondition="已开票", consequence="已开票", source_ref="20.10.2.2修改发票上传功能")

    # ===== Step 1: 实体 =====
    # --- 1.0 词表 ---
    m.set_prohibition_config(config={
        "action_verbs": ["编制", "发布", "报名", "审核", "缴费", "开具", "发放", "核查", "制备", "提交", "评价", "确认", "统计", "批准", "退回", "停用", "启用", "修改", "删除", "新增", "导入", "上传", "下载", "导出", "撤销", "退款", "整理", "发送", "选择", "跳转", "查看", "查询", "重置", "保存", "填充", "批量处理", "签章", "提醒"],
        "prohibit_keywords": ["不允许删除含有子项的记录", "不可直接编辑", "不可被选择", "不能为大于当前缴费金额", "不可以从", "未结束的项目可以进行消息发送"],
    })
    # --- 1.1 角色（来源: §5-18 用户角色分析 + §3.2） ---
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
    m.add_role(id="r12", name="系统管理人员")
    m.add_role(id="r13", name="能力验证参加者")
    m.add_role(id="r14", name="超级管理员")
    # --- 1.1 权限 ---
    m.add_permission(role="项目管理员", operations=["查询项目", "查看详情", "下载文件", "上传文件", "导出数据"])
    m.add_permission(role="系统管理人员", operations=["查询用户", "查询角色", "配置角色", "查询实验室", "查询标准库", "查询信息发送记录"])
    m.add_permission(role="评价人员", operations=["查询评价", "导出评价结果", "下载评价表"])
    m.add_permission(role="财务管理人员", operations=["查询缴费信息", "导出缴费信息", "查询收入统计"])
    m.add_permission(role="能力验证参加者", operations=["查询项目", "查看详情", "下载文件", "上传文件"])
    m.add_permission(role="统计人员", operations=["查询统计", "导出统计"])
    m.add_permission(role="质量专员", operations=["查询报告统计"])
    # --- 1.4 实体 ---
    m.add_entity(
        id="E-XM", name="能力验证项目",
        desc="能力验证提供者创建并管理的主业务对象，承载项目全生命周期状态",
        type="core",
        tags=["multi-state", "approvable", "collaborative"],
        attributes=[attr(name="项目编号", desc="项目唯一标识"), attr(name="项目名称", desc="项目名称"), attr(name="产品类型", desc="项目所属产品类型", is_config=True), attr(name="项目类型", desc="能力验证/测量审核", is_config=True), attr(name="所属年度", desc="项目年度"), attr(name="监督员", desc="新增监督员字段"), attr(name="技术主管", desc="项目技术主管"), attr(name="实验室负责人", desc="项目实验室负责人"), attr(name="授权签字人", desc="项目授权签字人"), attr(name="项目费用", desc="项目费用金额"), attr(name="财务备注", desc="财务备注字段")],
        state_dimensions=[
            {"dimension_name": "项目状态", "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
             "initial": "待开始", "terminal": ["已结束"],
             "inferred": [], "note": {"comment": "§19.3项目状态分析枚举；序判依据19.1阶段表"}},
        ],
        operations=[
            op(name="任务通知书编制", category="file", expected_results=["生成任务通知书文件"], source_ref="19.1项目准备阶段", note={"role": ["策划人员"], "comment": "无状态落点，文件操作"}),
            op(name="文件整理", category="file", expected_results=["归档任务已开启，请稍后查看", "整理完成后显示查看归档按钮"], source_ref="20.5.1.1文件整理", note={"role": ["项目管理员"], "comment": "仅已结束项目可整理"}),
            op(name="机构代码导入", category="file", expected_results=["导入报名机构三方代码成功"], source_ref="20.5.1.2机构代码导入", note={"role": ["项目管理员"]}),
            op(name="项目批量操作", category="ui", expected_results=["跳转至报名信息批量处理页面"], source_ref="20.5.1.3项目批量操作", note={"role": ["项目管理员"]}),
            op(name="消息发送", category="ui", expected_results=["消息按选择方式发送成功"], source_ref="20.5.1.4优化消息发送功能", note={"role": ["项目管理员"], "comment": "未结束项目可发送"}),
            op(name="查询项目", category="query", expected_results=["分页展示符合条件的项目列表"], source_ref="20.8.3.1项目查询与统计", note={"role": ["项目管理员", "系统管理人员"]}),
        ],
    )
    m.add_entity(
        id="E-BM", name="报名记录",
        desc="参加者报名能力验证项目的记录，承载报名到结果发布的全流程状态",
        type="core",
        tags=["multi-state", "approvable", "expirable", "collaborative"],
        attributes=[attr(name="报名编号", desc="报名记录唯一标识"), attr(name="统一社会信用代码", desc="报名机构代码"), attr(name="实验室名称", desc="报名实验室"), attr(name="报名时间", desc="报名时间"), attr(name="机构代码", desc="导入的三方代码")],
        state_dimensions=[
            {"dimension_name": "报名记录状态",
             "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
             "initial": "报名待审核", "terminal": ["报告/证书已发布", "已撤销"],
             "inferred": [], "note": {"comment": "§19.3报名记录状态枚举"}},
            {"dimension_name": "报名记录样品状态",
             "states": ["待发样", "待收样", "已收样", "已确认"],
             "initial": "待发样", "terminal": ["已确认"],
             "inferred": [], "note": {"comment": "§19.3报名记录样品状态枚举；台账中样品状态变更落E-YP，本维度为报名记录视角的样品状态"}},
        ],
        operations=[
            op(name="查看报名详情", category="query", expected_results=["展示报名信息详情页"], source_ref="20.5.2已报名项目", note={"role": ["项目管理员", "能力验证参加者"]}),
            op(name="预通知文件下载", category="file", expected_results=["下载预通知文件"], source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载", note={"role": ["项目管理员", "能力验证参加者"]}),
        ],
    )
    m.add_entity(
        id="E-YP", name="样品",
        desc="能力验证物品，承载制备、核查、发放、还样的全生命周期",
        type="core",
        tags=["multi-state", "expirable"],
        attributes=[attr(name="样品编号", desc="样品唯一标识"), attr(name="核查记录", desc="样品核查记录表"), attr(name="快递单号", desc="样品发放快递单号"), attr(name="软件访问路径", desc="软件样品访问路径")],
        state_dimensions=[
            {"dimension_name": "样品状态",
             "states": ["待核查", "已核查", "待发样", "已发样", "已还样", "无需还样"],
             "initial": "待核查", "terminal": ["已还样", "无需还样"],
             "inferred": ["待发样", "已发样", "已还样", "无需还样"],
             "note": {"comment": "§19.3枚举仅列待核查/已核查，待发样/已发样/已还样/无需还样据§19.1阶段表样品状态列推导补入"}},
        ],
        operations=[
            op(name="样品出入库登记", category="ui", expected_results=["登记样品出入库记录"], source_ref="12样品管理员库存管理", note={"role": ["样品管理员"]}),
            op(name="样品借出归还记录", category="ui", expected_results=["记录样品借出归还信息"], source_ref="3.2功能要求样品管理", note={"role": ["样品管理员"]}),
            op(name="查询样品", category="query", expected_results=["分页展示样品列表"], source_ref="20.4.1实验室管理", note={"role": ["样品管理员", "项目管理员"]}),
        ],
    )
    m.add_entity(
        id="E-YTZ", name="预通知",
        desc="能力验证计划预通知，承载发送、确认的交付生命周期",
        type="core",
        tags=["multi-state"],
        attributes=[attr(name="预通知文件", desc="预通知文件附件"), attr(name="用户信息表", desc="随预通知发送的用户信息表")],
        state_dimensions=[
            {"dimension_name": "通知状态",
             "states": ["未发送", "已发送", "待确认", "已确认", "待审核", "退回", "已审核", "已批准"],
             "initial": "未发送", "terminal": ["已确认", "已批准"],
             "inferred": ["已发送", "已确认"],
             "note": {"comment": "§19.3枚举列未发送/待确认/待审核/退回/已审核/已批准；已发送/已确认据§19.1阶段表预通知状态列补入；待审核/退回/已审核/已批准主要用于§19.2测量审核作业指导书审核"}},
        ],
        operations=[],
    )
    m.add_entity(
        id="E-JFTZ", name="缴费通知单",
        desc="报名审核通过后系统自动发送的缴费通知单",
        type="core",
        tags=[],
        attributes=[attr(name="缴费通知书", desc="缴费通知书文件")],
        state_dimensions=[
            {"dimension_name": "缴费通知单状态",
             "states": ["未发送", "已发送"],
             "initial": "未发送", "terminal": ["已发送"],
             "inferred": [], "note": {"comment": "§19.1阶段表缴费通知单列推导；报名记录创建时自动初始化为未发送，审核通过后自动发送为已发送"}},
        ],
        operations=[],
    )
    m.add_entity(
        id="E-FY", name="费用",
        desc="报名记录关联的费用记录，支持多次付款和退款",
        type="core",
        tags=["multi-state"],
        attributes=[attr(name="应付金额", desc="项目费用金额"), attr(name="实付金额", desc="实际付款金额"), attr(name="退款金额", desc="累计退款金额"), attr(name="管理备注", desc="退款原因等备注")],
        state_dimensions=[
            {"dimension_name": "费用状态",
             "states": ["待缴费", "已缴费", "已退款"],
             "initial": "待缴费", "terminal": ["已退款"],
             "inferred": ["已退款"],
             "note": {"comment": "§19.3枚举列待缴费/已缴费；已退款据§20.10.2.3缴费单退款补入"}},
        ],
        operations=[
            op(name="上传付款单", category="file", expected_results=["付款记录保存成功"], source_ref="20.5.2.1已报名项目增加多次付款功能", note={"role": ["能力验证参加者"], "comment": "支持多次付款，不对付款金额校验"}),
            op(name="缴费单退款", category="ui", expected_results=["退款成功，实际付款金额更新"], source_ref="20.10.2.3缴费单退款", note={"role": ["财务管理人员"], "comment": "退款金额不能大于当前缴费金额"}),
            op(name="修改财务备注", category="ui", expected_results=["财务备注修改成功"], source_ref="20.10.2.1项目列表增加财务备注字段", note={"role": ["财务管理人员"]}),
            op(name="查询缴费信息", category="query", expected_results=["分页展示缴费信息列表"], source_ref="20.10.1.1缴费信息查询与管理", note={"role": ["财务管理人员"]}),
        ],
    )
    m.add_entity(
        id="E-FP", name="发票",
        desc="报名记录关联的发票记录，支持多次分批上传",
        type="core",
        tags=["multi-state"],
        attributes=[attr(name="开票时间", desc="最后一次开票时间"), attr(name="开票类型", desc="电子专票/电子普票", is_config=True), attr(name="发票文件", desc="电子发票文件")],
        state_dimensions=[
            {"dimension_name": "发票状态",
             "states": ["待开票", "已开票"],
             "initial": "待开票", "terminal": ["已开票"],
             "inferred": [], "note": {"comment": "§19.3发票状态枚举"}},
        ],
        operations=[
            op(name="发票上传", category="file", expected_results=["发票上传成功，显示在发票列表"], source_ref="20.10.2.2修改发票上传功能", note={"role": ["财务管理人员"], "comment": "支持多次分批上传"}),
        ],
    )
    m.add_entity(
        id="E-PJ", name="评价",
        desc="对报名项目结果进行评价的对象，支持分值和权重两种评分方式及协同评价",
        type="core",
        tags=["multi-state", "approvable", "collaborative", "configurable"],
        attributes=[attr(name="评分方式", desc="分值/权重", is_config=True), attr(name="及格分", desc="及格分数"), attr(name="评价组长", desc="第一个被选择的评价人员默认为组长"), attr(name="评价项目", desc="测试项目及评价细则"), attr(name="历史记录", desc="评价历史结果")],
        state_dimensions=[
            {"dimension_name": "评价状态",
             "states": ["待完善", "待评价", "评价中", "待确认", "已确认"],
             "initial": "待完善", "terminal": ["已确认"],
             "inferred": ["待完善", "待评价", "评价中", "待确认", "已确认"],
             "note": {"comment": "§20.7未显式枚举评价状态，据20.7.1.1-20.7.1.3流程推导: 评价组长完善→待评价→评价人员评价→评价中→提交→待确认→确认→已确认"}},
        ],
        operations=[
            op(name="导出评价结果", category="file", expected_results=["下载评价结果文件"], source_ref="20.7.1.4评价结果导出", note={"role": ["评价人员"]}),
            op(name="保存历史", category="ui", expected_results=["当前评价结果保存为历史结果"], source_ref="20.7.1.3评价确认", note={"role": ["评价人员"], "comment": "评价组长操作"}),
            op(name="调整细则", category="ui", expected_results=["打开评价细节完善页面"], source_ref="20.7.1.3评价确认", note={"role": ["评价人员"], "comment": "评价组长操作"}),
            op(name="配置统计规则", category="config", expected_results=["统计规则配置保存成功"], source_ref="20.7.1.3评价确认", note={"role": ["评价人员"], "comment": "评价组长配置成绩区间统计规则"}),
        ],
    )
    m.add_entity(
        id="E-TASK", name="审核任务",
        desc="流程审批任务，承载报告/通知单/证书的审核流转，支持批量处理和自定义流程",
        type="core",
        tags=["multi-state", "approvable", "collaborative"],
        attributes=[attr(name="任务类型", desc="结果通知单审核/报告审核/证书审核等", is_config=True), attr(name="创建时间", desc="任务创建时间"), attr(name="审核意见", desc="审核反馈意见"), attr(name="签章位置", desc="预置电子签章位置信息"), attr(name="审批顺序", desc="提交申请时签字人的选择顺序")],
        state_dimensions=[
            {"dimension_name": "审核任务状态",
             "states": ["待审核", "已通过", "已退回"],
             "initial": "待审核", "terminal": ["已通过", "已退回"],
             "inferred": [], "note": {"comment": "§20.9业务审核推导"}},
        ],
        operations=[
            op(name="批量审核", category="ui", expected_results=["所选任务批量审核完成"], source_ref="20.9.1.4任务批量处理", note={"role": ["技术主管", "授权签字人", "实验室负责人"], "comment": "系统判断节点是否可批量处理"}),
            op(name="导出审批流程", category="file", expected_results=["导出满足查询条件的数据"], source_ref="20.9.1.5审批流程列表导出", note={"role": ["技术主管", "系统管理人员"]}),
            op(name="查询审批流程", category="query", expected_results=["分页展示审批流程列表"], source_ref="20.9.1.5审批流程列表导出", note={"role": ["技术主管", "系统管理人员"]}),
            op(name="自定义流程", category="config", expected_results=["选择并提交自定义流程"], source_ref="20.9.1.6增加自定义流程", note={"role": ["策划人员"], "comment": "系统预设4个以内自定义流程"}),
        ],
    )
    m.add_entity(
        id="E-LAB", name="实验室",
        desc="参加者实验室基础信息，新增/修改后需经管理用户审核通过方可用于项目报名",
        type="managed",
        tags=["multi-state", "approvable", "configurable"],
        attributes=[attr(name="实验室名称", desc="实验室名称"), attr(name="统一社会信用代码", desc="统一社会信用代码"), attr(name="CNAS", desc="已获CNAS认可"), attr(name="CMA", desc="已获CMA认可"), attr(name="默认实验室", desc="默认实验室标识"), attr(name="证明文件", desc="营业执照或其他证书材料")],
        state_dimensions=[
            {"dimension_name": "实验室状态",
             "states": ["待审核", "启用", "停用", "已退回"],
             "initial": "待审核", "terminal": [],
             "inferred": [], "note": {"comment": "§20.3.1实验室信息新增状态字段"}},
        ],
        operations=[
            op(name="修改实验室", category="ui", expected_results=["实验室信息修改成功，状态变为待审核"], source_ref="20.4.1.3实验室修改", note={"role": ["系统管理人员"]}),
            op(name="删除实验室", category="crud", expected_results=["实验室记录删除"], source_ref="20.4.1.1实验室列表与查询", note={"role": ["系统管理人员"]}),
            op(name="查询实验室", category="query", expected_results=["分页展示符合条件的数据记录"], source_ref="20.4.1.1实验室列表与查询", note={"role": ["系统管理人员"]}),
        ],
    )
    m.add_entity(
        id="E-STD", name="标准库",
        desc="标准库基础数据及其下属测试项和参数的全生命周期管理",
        type="managed",
        tags=["multi-state", "configurable"],
        attributes=[attr(name="标准库编号", desc="标准库编号"), attr(name="标准库名称", desc="标准库名称"), attr(name="描述", desc="标准库描述")],
        state_dimensions=[
            {"dimension_name": "标准库状态",
             "states": ["启用", "停用"],
             "initial": "启用", "terminal": [],
             "inferred": [], "note": {"comment": "§20.4.2标准库管理；停用的标准库在项目创建等环节不可被选择"}},
        ],
        operations=[
            op(name="新增标准库", category="crud", expected_results=["标准库创建成功"], source_ref="20.4.2.2新增标准库", note={"role": ["系统管理人员"]}),
            op(name="修改标准库", category="crud", expected_results=["标准库修改成功"], source_ref="20.4.2.3修改标准库", note={"role": ["系统管理人员"]}),
            op(name="删除标准库", category="crud", expected_results=["标准库删除成功"], source_ref="20.4.2.4删除标准库", note={"role": ["系统管理人员"], "comment": "含有子项的记录不允许删除"}),
            op(name="管理测试项", category="ui", expected_results=["进入标准库专属测试项管理界面"], source_ref="20.4.2.6进入测试项管理界面", note={"role": ["系统管理人员"]}),
            op(name="新增测试项", category="crud", expected_results=["测试项新增成功"], source_ref="20.4.2.8新增测试项", note={"role": ["系统管理人员"]}),
            op(name="修改测试项", category="crud", expected_results=["测试项修改成功"], source_ref="20.4.2.9修改测试项", note={"role": ["系统管理人员"]}),
            op(name="删除测试项", category="crud", expected_results=["测试项删除成功"], source_ref="20.4.2.10删除测试项", note={"role": ["系统管理人员"], "comment": "含有子项的记录不允许删除"}),
            op(name="查询标准库", category="query", expected_results=["分页展示符合条件的数据记录"], source_ref="20.4.2.1标准库列表与查询", note={"role": ["系统管理人员"]}),
        ],
    )
    m.add_entity(
        id="E-ZS", name="证书",
        desc="能力验证合格证书，由实验室负责人签发，含到期提醒",
        type="core",
        tags=["expirable"],
        attributes=[attr(name="证书编号", desc="证书唯一编号"), attr(name="到期时间", desc="证书到期时间"), attr(name="签发人", desc="实验室负责人"), attr(name="证书文件", desc="证书文件附件")],
        state_dimensions=[],
        operations=[
            op(name="下载证书", category="file", expected_results=["下载证书文件"], source_ref="20.5.2已报名项目", note={"role": ["能力验证参加者"]}),
            op(name="上传证书", category="file", expected_results=["证书上传成功"], source_ref="20.5.1.3项目批量操作", note={"role": ["项目管理员"]}),
        ],
    )
    m.add_entity(
        id="E-MSG", name="信息发送记录",
        desc="系统信息发送历史记录，包含发送方式、接收人、发送时间等",
        type="managed",
        tags=[],
        attributes=[attr(name="接收号码", desc="接收人号码"), attr(name="发送方式", desc="短信/邮件/站内信"), attr(name="发送时间", desc="发送时间"), attr(name="发送人", desc="发送人"), attr(name="发送结果", desc="发送结果"), attr(name="消息标题", desc="消息标题"), attr(name="消息内容", desc="消息内容")],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query", expected_results=["分页展示信息发送记录"], source_ref="20.4.4.1信息发送记录", note={"role": ["系统管理人员", "项目管理员"], "comment": "只有系统管理员和项目管理员可以查看"}),
            op(name="查看消息详情", category="query", expected_results=["展示消息详细内容"], source_ref="20.4.4.1信息发送记录", note={"role": ["系统管理人员", "项目管理员"]}),
        ],
    )
    # --- 1.5 结构关系 ---
    m.add_structural(frm="E-XM", to="E-BM", relation_type="composition", cardinality="1:N", ownership_dimension="business_ownership", desc="能力验证项目包含多个报名记录，报名记录无独立创建流程（由参加者在项目报名中状态下创建）", confidence="high", note={"comment": "判(c): B有独立创建流程但E-XM为core流程实体且为其业务归属容器；dependent=有"})
    m.add_structural(frm="E-XM", to="E-YP", relation_type="composition", cardinality="1:N", ownership_dimension="business_ownership", desc="能力验证项目包含多个样品，样品在项目实施阶段制备创建", confidence="high", note={"comment": "判(c): E-YP为core流程实体，E-XM为其业务归属容器；dependent=有"})
    m.add_structural(frm="E-XM", to="E-YTZ", relation_type="composition", cardinality="1:1", ownership_dimension="business_ownership", desc="能力验证计划发布时自动创建预通知，每条项目必有预通知", confidence="high", note={"comment": "判(b): E-YTZ无独立创建流程，E-XM能力验证计划发布时自动创建；每条A必有B"})
    m.add_structural(frm="E-BM", to="E-JFTZ", relation_type="composition", cardinality="1:1", ownership_dimension="business_ownership", desc="报名记录创建后系统自动初始化缴费通知单", confidence="high", note={"comment": "判(b): E-JFTZ无独立创建流程，报名记录创建时自动初始化；每条A必有B"})
    m.add_structural(frm="E-BM", to="E-FY", relation_type="composition", cardinality="1:1", ownership_dimension="business_ownership", desc="报名记录创建后系统自动初始化费用记录", confidence="high", note={"comment": "判(b): E-FY无独立创建流程，报名记录创建时自动初始化；每条A必有B"})
    m.add_structural(frm="E-BM", to="E-FP", relation_type="composition", cardinality="1:1", ownership_dimension="business_ownership", desc="报名记录创建后系统自动初始化发票记录", confidence="high", note={"comment": "判(b): E-FP无独立创建流程，报名记录创建时自动初始化；每条A必有B"})
    m.add_structural(frm="E-XM", to="E-PJ", relation_type="composition", cardinality="1:1", ownership_dimension="business_ownership", desc="能力验证项目包含一个评价对象，覆盖所有参加者的评价结果", confidence="high", note={"comment": "判(b): E-PJ由评价组长在项目实施后创建，无独立创建流程脱离项目；每条A必有B"})
    m.add_structural(frm="E-XM", to="E-TASK", relation_type="reference", cardinality="1:N", ownership_dimension="configuration_source", desc="能力验证项目在报告编制阶段产生多个审核任务（报告审核、通知单批准、证书批准）", confidence="high", note={"comment": "判(d): E-TASK有独立创建流程（提交审核），可能多个，不满足(c)"})
    m.add_structural(frm="E-BM", to="E-ZS", relation_type="reference", cardinality="1:1", ownership_dimension="configuration_source", desc="报名记录在报告/证书发布后关联合格证书", confidence="high", note={"comment": "判(d): E-ZS有独立创建流程（发放结果报告和证书）"})
    m.add_structural(frm="E-XM", to="E-LAB", relation_type="reference", cardinality="M:N", ownership_dimension="configuration_source", desc="实验室参与多个能力验证项目报名，项目接受多个实验室报名", confidence="medium", note={"comment": "判(d): 多对多关系；management_dimension复核：E-LAB为独立参加者实体，E-XM为项目容器"})

    # ===== Step 2: 分支 =====
    m.add_branch_dimension(
        dimension="评分方式", entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="评价人员评价转换的得分计算方式: 分值按累加计算，权重按加权计算",
        evidence="①配置型；§20.7.1项目列表: 支持分值和权重两种评价方式；is_config=True",
        branches=[
            {"value": "分值", "target_transition": "评价人员评价转换", "desc": "分值方式按累加计算得分"},
            {"value": "权重", "target_transition": "评价人员评价转换", "desc": "权重方式按加权计算得分"},
        ],
    )
    m.add_branch_dimension(
        dimension="项目类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="项目创建路径分歧: 能力验证为设计方案编制→计划发布→报名；测量审核为受理报名→设计方案编制",
        evidence="①配置型；§19.1/§19.2流程差异；§20.5/§20.6模块平行；is_config=True",
        branches=[
            {"value": "能力验证", "target_transition": "设计方案编制转换", "desc": "能力验证: 先创建项目(待开始)再发布计划(报名中)"},
            {"value": "测量审核", "target_transition": "受理报名转换", "desc": "测量审核: 先受理报名(报名中)再创建项目(待开始)；含作业指导书编制审核环节"},
        ],
    )
    m.add_branch_dimension(
        dimension="审核结果", entity="E-TASK",
        values=["通过", "退回"],
        impact_scope="审核任务状态落点分歧: 通过→已通过(推进流程)；退回→已退回(回退)",
        evidence="②运行时选择型；§19.1报告编制: 审核结果通过/退回；§20.9.1.4批量审核: 同意/退回",
        branches=[
            {"value": "通过", "target_transition": "技术主管审核转换", "desc": "审核通过，任务状态变为已通过，推进下一审批环节"},
            {"value": "退回", "target_transition": "技术主管审核转换", "desc": "审核退回，任务状态变为已退回，回退至编制人修改"},
        ],
    )

    # ===== Step 3: 转换与因果 =====
    # --- 3.1 转换 ---
    m.add_trans(tid="t01", entity="E-XM", dimension="项目状态", frm=None, to="待开始", action="设计方案编制", role="策划人员", preconditions=[], expected_results=["项目创建，项目状态变为待开始"], traits=[], direction="forward", priority="P0", source_ref="19.1方案设计阶段", note={"comment": "源自 e01；⓪frm=None→forward；创建转换"})
    m.add_trans(tid="t02", entity="E-XM", dimension="项目状态", frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员", preconditions=[precond(text="项目处于待开始状态", ptype="state_ref", ref=state_ref("E-XM", "项目状态", "待开始"))], expected_results=["项目状态变为报名中，同步创建预通知为未发送"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e02；③frm先于to→forward；一动作多状态面见 t06"})
    m.add_trans(tid="t03", entity="E-XM", dimension="项目状态", frm="报名中", to="进行中", action="进入实施", role="项目管理员", preconditions=[precond(text="项目处于报名中状态", ptype="state_ref", ref=state_ref("E-XM", "项目状态", "报名中"))], expected_results=["项目状态变为进行中"], traits=[], direction="forward", priority="P0", source_ref="19.3项目状态分析", note={"inferred": True, "comment": "源自 e37；③；inferred:报名结束后进入进行中，枚举序判推导"})
    m.add_trans(tid="t04", entity="E-XM", dimension="项目状态", frm="进行中", to="报告审核中", action="进入报告审核", role="策划人员", preconditions=[precond(text="项目处于进行中状态", ptype="state_ref", ref=state_ref("E-XM", "项目状态", "进行中"))], expected_results=["项目状态变为报告审核中"], traits=[], direction="forward", priority="P0", source_ref="19.3项目状态分析", note={"inferred": True, "comment": "源自 e38；③；inferred:编制结果报告时进入报告审核中"})
    m.add_trans(tid="t05", entity="E-XM", dimension="项目状态", frm="报告审核中", to="已结束", action="项目结束", role="项目管理员", preconditions=[precond(text="项目处于报告审核中状态", ptype="state_ref", ref=state_ref("E-XM", "项目状态", "报告审核中"))], expected_results=["项目状态变为已结束"], traits=[], direction="forward", priority="P0", source_ref="19.3项目状态分析", note={"inferred": True, "comment": "源自 e39；③；inferred:发放结果报告和证书后项目结束"})
    m.add_trans(tid="t06", entity="E-YTZ", dimension="通知状态", frm=None, to="未发送", action="能力验证计划发布", role="项目管理员", preconditions=[precond(text="项目处于待开始状态", ptype="state_ref", ref=state_ref("E-XM", "项目状态", "待开始"))], expected_results=["预通知创建，状态为未发送"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e03；⓪frm=None→forward；创建转换，一动作多状态面见 t02"})
    m.add_trans(tid="t07", entity="E-YTZ", dimension="通知状态", frm="未发送", to="已发送", action="能力验证预通知", role="项目管理员", preconditions=[precond(text="预通知处于未发送状态", ptype="state_ref", ref=state_ref("E-YTZ", "通知状态", "未发送"))], expected_results=["预通知状态变为已发送"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e14；③；inferred:已发送据阶段表补入，§19.3枚举缺失"})
    m.add_trans(tid="t08", entity="E-YTZ", dimension="通知状态", frm="已发送", to="已确认", action="预通知确认", role="能力验证参加者", preconditions=[precond(text="预通知处于已发送状态", ptype="state_ref", ref=state_ref("E-YTZ", "通知状态", "已发送"))], expected_results=["预通知状态变为已确认"], traits=[], direction="forward", priority="P1", source_ref="19.4参加者流程", note={"inferred": True, "comment": "源自 e16；③；inferred:参加者确认接收，§19.4流程"})
    m.add_trans(tid="t09", entity="E-BM", dimension="报名记录状态", frm=None, to="报名待审核", action="报名", role="能力验证参加者", preconditions=[precond(text="项目处于报名中状态", ptype="state_ref", ref=state_ref("E-XM", "项目状态", "报名中"))], expected_results=["报名记录创建，状态为报名待审核；同时初始化缴费通知单、费用、发票"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e04；⓪frm=None→forward；创建转换，跨主体门禁E-XM.报名中落state_ref；一动作多状态面见 t18/t20/t24"})
    m.add_trans(tid="t10", entity="E-BM", dimension="报名记录状态", frm="报名待审核", to="报名成功", action="报名审核", role="项目管理员", preconditions=[precond(text="报名记录处于报名待审核状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报名待审核"))], expected_results=["报名记录状态变为报名成功"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e08；③；分支②运行时选择型-通过路径"})
    m.add_trans(tid="t11", entity="E-BM", dimension="报名记录状态", frm="报名待审核", to="报名退回", action="报名审核", role="项目管理员", preconditions=[precond(text="报名记录处于报名待审核状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报名待审核"))], expected_results=["报名记录状态变为报名退回"], traits=["rollback"], direction="backward", priority="P1", source_ref="19.1实施阶段", note={"comment": "源自 e09；①退回→backward；分支②运行时选择型-退回路径"})
    m.add_trans(tid="t12", entity="E-BM", dimension="报名记录状态", frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员", preconditions=[precond(text="报名记录处于报名成功状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报名成功"))], expected_results=["报名记录状态变为结果待提交"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e15；③；一动作多状态面见 t07"})
    m.add_trans(tid="t13", entity="E-BM", dimension="报名记录状态", frm="结果待提交", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者", preconditions=[precond(text="报名记录处于结果待提交状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "结果待提交"))], expected_results=["报名记录状态变为结果已提交"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e20；③；一动作多状态面见 t31"})
    m.add_trans(tid="t14", entity="E-BM", dimension="报名记录状态", frm="结果已提交", to="结果退回修改", action="结果报告回收", role="项目管理员", preconditions=[precond(text="报名记录处于结果已提交状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "结果已提交"))], expected_results=["报名记录状态变为结果退回修改"], traits=["rollback"], direction="backward", priority="P1", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e22；①退回→backward；分支:结果退回修改"})
    m.add_trans(tid="t15", entity="E-BM", dimension="报名记录状态", frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员", preconditions=[precond(text="报名记录处于结果已提交状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "结果已提交"))], expected_results=["报名记录状态变为报告/证书审核中"], traits=[], direction="forward", priority="P0", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e30；③"})
    m.add_trans(tid="t16", entity="E-BM", dimension="报名记录状态", frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员", preconditions=[precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中")), precond(text="审核任务已通过", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "已通过"))], expected_results=["报名记录状态变为报告/证书已发布"], traits=[], direction="forward", priority="P0", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e36；③；跨主体门禁E-TASK.已通过落state_ref"})
    m.add_trans(tid="t17", entity="E-BM", dimension="报名记录状态", frm="报名待审核", to="已撤销", action="撤销报名", role="能力验证参加者", preconditions=[precond(text="报名记录处于报名待审核状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报名待审核"))], expected_results=["报名记录状态变为已撤销"], traits=["rollback"], direction="lateral", priority="P1", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e40；①撤销→lateral；inferred:状态列显示报名待审核/已撤销"})
    m.add_trans(tid="t18", entity="E-JFTZ", dimension="缴费通知单状态", frm=None, to="未发送", action="报名", role="能力验证参加者", preconditions=[], expected_results=["缴费通知单创建，状态为未发送"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e05；⓪frm=None→forward；inferred:报名记录创建后系统自动初始化；一动作多状态面见 t09"})
    m.add_trans(tid="t19", entity="E-JFTZ", dimension="缴费通知单状态", frm="未发送", to="已发送", action="报名审核", role="项目管理员", preconditions=[precond(text="缴费通知单处于未发送状态", ptype="state_ref", ref=state_ref("E-JFTZ", "缴费通知单状态", "未发送")), precond(text="报名记录处于报名待审核状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报名待审核"))], expected_results=["缴费通知单状态变为已发送"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e10；③；inferred:报名审核通过后系统自动发送缴费通知单；跨主体门禁E-BM.报名待审核"})
    m.add_trans(tid="t20", entity="E-FY", dimension="费用状态", frm=None, to="待缴费", action="报名", role="能力验证参加者", preconditions=[], expected_results=["费用记录创建，状态为待缴费"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e06；⓪frm=None→forward；inferred:报名记录创建后系统自动初始化"})
    m.add_trans(tid="t21", entity="E-FY", dimension="费用状态", frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者", preconditions=[precond(text="费用处于待缴费状态", ptype="state_ref", ref=state_ref("E-FY", "费用状态", "待缴费"))], expected_results=["费用状态变为已缴费"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e11；③"})
    m.add_trans(tid="t22", entity="E-FY", dimension="费用状态", frm="已缴费", to="已退款", action="缴费单退款", role="财务管理人员", preconditions=[precond(text="费用处于已缴费状态", ptype="state_ref", ref=state_ref("E-FY", "费用状态", "已缴费")), precond(text="退款金额不能大于当前缴费金额", ptype="constraint", note={"inferred": True, "comment": "§20.10.2.3限制"})], expected_results=["费用状态变为已退款，实际付款金额更新为付款金额减退款金额"], traits=["rollback"], direction="backward", priority="P1", source_ref="20.10.2.3缴费单退款", note={"comment": "源自 e50；①退款→backward；inferred:已退款状态据退款功能补入"})
    m.add_trans(tid="t23", entity="E-FY", dimension="费用状态", frm="已缴费", to="已缴费", action="多次付款", role="能力验证参加者", preconditions=[precond(text="费用处于已缴费状态", ptype="state_ref", ref=state_ref("E-FY", "费用状态", "已缴费"))], expected_results=["付款记录保存成功，不对付款金额进行校验限制"], traits=[], direction="forward", priority="P2", source_ref="20.5.2.1已报名项目增加多次付款功能", note={"inferred": True, "comment": "源自 e53；⑤自环→forward+inferred"})
    m.add_trans(tid="t24", entity="E-FP", dimension="发票状态", frm=None, to="待开票", action="报名", role="能力验证参加者", preconditions=[], expected_results=["发票记录创建，状态为待开票"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e07；⓪frm=None→forward；inferred:报名记录创建后系统自动初始化"})
    m.add_trans(tid="t25", entity="E-FP", dimension="发票状态", frm="待开票", to="已开票", action="发票开具", role="财务管理人员", preconditions=[precond(text="发票处于待开票状态", ptype="state_ref", ref=state_ref("E-FP", "发票状态", "待开票"))], expected_results=["发票状态变为已开票"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e13；③"})
    m.add_trans(tid="t26", entity="E-FP", dimension="发票状态", frm="已开票", to="已开票", action="分批上传发票", role="财务管理人员", preconditions=[precond(text="发票处于已开票状态", ptype="state_ref", ref=state_ref("E-FP", "发票状态", "已开票"))], expected_results=["发票上传成功，显示在发票列表中"], traits=[], direction="forward", priority="P2", source_ref="20.10.2.2修改发票上传功能", note={"inferred": True, "comment": "源自 e54；⑤自环→forward+inferred；支持多次分批上传"})
    m.add_trans(tid="t27", entity="E-YP", dimension="样品状态", frm=None, to="待核查", action="样品制备", role="样品制备人员", preconditions=[], expected_results=["样品创建，状态为待核查"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e12；⓪frm=None→forward；inferred:缴费行样品状态=待核查，推导样品制备为创建动作"})
    m.add_trans(tid="t28", entity="E-YP", dimension="样品状态", frm="待核查", to="已核查", action="样品核查", role="样品管理员", preconditions=[precond(text="样品处于待核查状态", ptype="state_ref", ref=state_ref("E-YP", "样品状态", "待核查"))], expected_results=["样品状态变为已核查"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e17；③"})
    m.add_trans(tid="t29", entity="E-YP", dimension="样品状态", frm="已核查", to="待发样", action="样品核查", role="样品管理员", preconditions=[precond(text="样品处于已核查状态", ptype="state_ref", ref=state_ref("E-YP", "样品状态", "已核查"))], expected_results=["样品状态变为待发样"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e18；③；inferred:核查后进入待发样（状态列显示已核查、待发样）"})
    m.add_trans(tid="t30", entity="E-YP", dimension="样品状态", frm="待发样", to="已发样", action="样品发放", role="项目管理员", preconditions=[precond(text="样品处于待发样状态", ptype="state_ref", ref=state_ref("E-YP", "样品状态", "待发样"))], expected_results=["样品状态变为已发样"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"comment": "源自 e19；③"})
    m.add_trans(tid="t31", entity="E-YP", dimension="样品状态", frm="已发样", to="已还样", action="参加者测试与结果提交", role="能力验证参加者", preconditions=[precond(text="样品处于已发样状态", ptype="state_ref", ref=state_ref("E-YP", "样品状态", "已发样"))], expected_results=["样品状态变为已还样"], traits=[], direction="forward", priority="P0", source_ref="19.1实施阶段", note={"inferred": True, "comment": "源自 e21；③；inferred:参加者测试后还样；一动作多状态面见 t13"})
    m.add_trans(tid="t32", entity="E-PJ", dimension="评价状态", frm=None, to="待完善", action="评价组长完善", role="评价人员", preconditions=[], expected_results=["评价创建，状态为待完善"], traits=[], direction="forward", priority="P0", source_ref="20.7.1.1测试项目评价细则完善", note={"inferred": True, "comment": "源自 e23；⓪frm=None→forward；inferred:评价组长为评价人员角色；评价状态据20.7流程推导"})
    m.add_trans(tid="t33", entity="E-PJ", dimension="评价状态", frm="待完善", to="待评价", action="评价组长完善", role="评价人员", preconditions=[precond(text="评价处于待完善状态", ptype="state_ref", ref=state_ref("E-PJ", "评价状态", "待完善"))], expected_results=["评价状态变为待评价"], traits=[], direction="forward", priority="P0", source_ref="20.7.1.1测试项目评价细则完善", note={"comment": "源自 e24；③"})
    m.add_trans(tid="t34", entity="E-PJ", dimension="评价状态", frm="待评价", to="评价中", action="评价人员评价", role="评价人员", preconditions=[precond(text="评价处于待评价状态", ptype="state_ref", ref=state_ref("E-PJ", "评价状态", "待评价")), precond(text="报名记录处于结果已提交状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "结果已提交"))], expected_results=["若评分方式=分值，则按累加计算得分，评价状态变为评价中", "若评分方式=权重，则按加权计算得分，评价状态变为评价中"], traits=["branch"], direction="forward", priority="P0", source_ref="20.7.1.2协同评价", note={"branch_dimension": "评分方式", "comment": "源自 e25；③；跨主体门禁E-BM.结果已提交落state_ref；结果差异型分支:落点唯一，仅计算方式不同"})
    m.add_trans(tid="t35", entity="E-PJ", dimension="评价状态", frm="评价中", to="待确认", action="评价人员提交", role="评价人员", preconditions=[precond(text="评价处于评价中状态", ptype="state_ref", ref=state_ref("E-PJ", "评价状态", "评价中"))], expected_results=["评价状态变为待确认"], traits=[], direction="forward", priority="P0", source_ref="20.7.1.2协同评价", note={"inferred": True, "comment": "源自 e26；③；inferred:评价完成后提交至组长确认"})
    m.add_trans(tid="t36", entity="E-PJ", dimension="评价状态", frm="评价中", to="评价中", action="评价统计", role="统计人员", preconditions=[precond(text="评价处于评价中状态", ptype="state_ref", ref=state_ref("E-PJ", "评价状态", "评价中"))], expected_results=["评价统计完成，评价状态不变"], traits=[], direction="forward", priority="P2", source_ref="19.1报告编制和结果通知", note={"inferred": True, "comment": "源自 e27；⑤自环→forward+inferred；统计不改变评价状态"})
    m.add_trans(tid="t37", entity="E-PJ", dimension="评价状态", frm="待确认", to="已确认", action="评价组长确认", role="评价人员", preconditions=[precond(text="评价处于待确认状态", ptype="state_ref", ref=state_ref("E-PJ", "评价状态", "待确认"))], expected_results=["评价状态变为已确认，项目评价状态关闭"], traits=[], direction="forward", priority="P0", source_ref="20.7.1.3评价确认", note={"inferred": True, "comment": "源自 e28；③；inferred:评价组长为评价人员角色"})
    m.add_trans(tid="t38", entity="E-PJ", dimension="评价状态", frm="待确认", to="评价中", action="退回修改", role="评价人员", preconditions=[precond(text="评价处于待确认状态", ptype="state_ref", ref=state_ref("E-PJ", "评价状态", "待确认"))], expected_results=["评价结果保存为历史，开启下一轮评价，状态变为评价中"], traits=["rollback"], direction="backward", priority="P1", source_ref="20.7.1.3评价确认", note={"comment": "源自 e29；①退回→backward；退回修改开启下一轮评价"})
    m.add_trans(tid="t39", entity="E-TASK", dimension="审核任务状态", frm=None, to="待审核", action="提交审核", role="策划人员", preconditions=[precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref", ref=state_ref("E-BM", "报名记录状态", "报告/证书审核中"))], expected_results=["审核任务创建，状态为待审核"], traits=[], direction="forward", priority="P0", source_ref="19.1报告编制和结果通知", note={"inferred": True, "comment": "源自 e31；⓪frm=None→forward；inferred:编制结果报告后提交审核；跨主体门禁E-BM.报告/证书审核中"})
    m.add_trans(tid="t40", entity="E-TASK", dimension="审核任务状态", frm="待审核", to="已通过", action="技术主管审核", role="技术主管", preconditions=[precond(text="审核任务处于待审核状态", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "待审核"))], expected_results=["审核任务状态变为已通过"], traits=[], direction="forward", priority="P0", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e32；③；分支②运行时选择型-通过路径"})
    m.add_trans(tid="t41", entity="E-TASK", dimension="审核任务状态", frm="待审核", to="已退回", action="技术主管审核", role="技术主管", preconditions=[precond(text="审核任务处于待审核状态", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "待审核"))], expected_results=["审核任务状态变为已退回"], traits=["rollback"], direction="backward", priority="P1", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e33；①退回→backward；分支②运行时选择型-退回路径"})
    m.add_trans(tid="t42", entity="E-TASK", dimension="审核任务状态", frm="待审核", to="已通过", action="授权签字人批准", role="授权签字人", preconditions=[precond(text="审核任务处于待审核状态", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "待审核")), precond(text="技术主管审核已通过", ptype="event_ref")], expected_results=["审核任务状态变为已通过"], traits=[], direction="forward", priority="P0", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e34；③；前置:技术主管审核通过"})
    m.add_trans(tid="t43", entity="E-TASK", dimension="审核任务状态", frm="待审核", to="已通过", action="实验室负责人批准", role="实验室负责人", preconditions=[precond(text="审核任务处于待审核状态", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "待审核")), precond(text="技术主管审核已通过", ptype="event_ref")], expected_results=["审核任务状态变为已通过"], traits=[], direction="forward", priority="P0", source_ref="19.1报告编制和结果通知", note={"comment": "源自 e35；③；证书批准，前置:技术主管审核通过"})
    m.add_trans(tid="t44", entity="E-TASK", dimension="审核任务状态", frm="待审核", to="已通过", action="批量审核", role="技术主管", preconditions=[precond(text="审核任务处于待审核状态", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "待审核"))], expected_results=["所选任务批量审核完成，状态变为已通过"], traits=[], direction="forward", priority="P1", source_ref="20.9.1.4任务批量处理", note={"comment": "源自 e51；③；分支:同意"})
    m.add_trans(tid="t45", entity="E-TASK", dimension="审核任务状态", frm="待审核", to="已退回", action="批量审核", role="技术主管", preconditions=[precond(text="审核任务处于待审核状态", ptype="state_ref", ref=state_ref("E-TASK", "审核任务状态", "待审核"))], expected_results=["所选任务批量审核完成，状态变为已退回"], traits=["rollback"], direction="backward", priority="P1", source_ref="20.9.1.4任务批量处理", note={"comment": "源自 e52；①退回→backward；分支:退回"})
    m.add_trans(tid="t46", entity="E-LAB", dimension="实验室状态", frm=None, to="待审核", action="实验室新增", role="系统管理人员", preconditions=[], expected_results=["实验室创建，状态为待审核"], traits=[], direction="forward", priority="P0", source_ref="20.4.1.2实验室审核", note={"comment": "源自 e41；⓪frm=None→forward"})
    m.add_trans(tid="t47", entity="E-LAB", dimension="实验室状态", frm="待审核", to="启用", action="实验室审核", role="系统管理人员", preconditions=[precond(text="实验室处于待审核状态", ptype="state_ref", ref=state_ref("E-LAB", "实验室状态", "待审核"))], expected_results=["实验室状态变为启用，生成数据快照记录"], traits=[], direction="forward", priority="P0", source_ref="20.4.1.2实验室审核", note={"comment": "源自 e42；③；分支:审核通过"})
    m.add_trans(tid="t48", entity="E-LAB", dimension="实验室状态", frm="待审核", to="已退回", action="实验室审核", role="系统管理人员", preconditions=[precond(text="实验室处于待审核状态", ptype="state_ref", ref=state_ref("E-LAB", "实验室状态", "待审核"))], expected_results=["实验室状态变为已退回"], traits=["rollback"], direction="backward", priority="P1", source_ref="20.4.1.2实验室审核", note={"comment": "源自 e43；①退回→backward；分支:退回修改"})
    m.add_trans(tid="t49", entity="E-LAB", dimension="实验室状态", frm="启用", to="停用", action="停用实验室", role="系统管理人员", preconditions=[precond(text="实验室处于启用状态", ptype="state_ref", ref=state_ref("E-LAB", "实验室状态", "启用"))], expected_results=["实验室状态变为停用"], traits=[], direction="lateral", priority="P1", source_ref="20.4.1.1实验室列表与查询", note={"comment": "源自 e44；①停用→lateral"})
    m.add_trans(tid="t50", entity="E-LAB", dimension="实验室状态", frm="停用", to="启用", action="启用实验室", role="系统管理人员", preconditions=[precond(text="实验室处于停用状态", ptype="state_ref", ref=state_ref("E-LAB", "实验室状态", "停用"))], expected_results=["实验室状态变为启用"], traits=[], direction="resume", priority="P1", source_ref="20.4.1.1实验室列表与查询", note={"comment": "源自 e45；①启用→resume"})
    m.add_trans(tid="t51", entity="E-LAB", dimension="实验室状态", frm="启用", to="待审核", action="实验室修改", role="系统管理人员", preconditions=[precond(text="实验室处于启用状态", ptype="state_ref", ref=state_ref("E-LAB", "实验室状态", "启用"))], expected_results=["实验室状态变为待审核"], traits=[], direction="forward", priority="P1", source_ref="20.4.1.3实验室修改", note={"inferred": True, "comment": "源自 e46；序判④(启用→待审核回退)，语义forward（修改后需重新审核），语义优先；inferred"})
    m.add_trans(tid="t52", entity="E-STD", dimension="标准库状态", frm=None, to="启用", action="新增标准库", role="系统管理人员", preconditions=[], expected_results=["标准库创建，状态为启用"], traits=[], direction="forward", priority="P0", source_ref="20.4.2.2新增标准库", note={"comment": "源自 e47；⓪frm=None→forward"})
    m.add_trans(tid="t53", entity="E-STD", dimension="标准库状态", frm="启用", to="停用", action="停用标准库", role="系统管理人员", preconditions=[precond(text="标准库处于启用状态", ptype="state_ref", ref=state_ref("E-STD", "标准库状态", "启用"))], expected_results=["标准库状态变为停用"], traits=[], direction="lateral", priority="P1", source_ref="20.4.2.5停用启用标准库", note={"comment": "源自 e48；①停用→lateral"})
    m.add_trans(tid="t54", entity="E-STD", dimension="标准库状态", frm="停用", to="启用", action="启用标准库", role="系统管理人员", preconditions=[precond(text="标准库处于停用状态", ptype="state_ref", ref=state_ref("E-STD", "标准库状态", "停用"))], expected_results=["标准库状态变为启用"], traits=[], direction="resume", priority="P1", source_ref="20.4.2.5停用启用标准库", note={"comment": "源自 e49；①启用→resume"})
    # --- 3.3 自检 ---
    # crud操作对应转换: 上传付款单→t21/t23; 缴费单退款→t22; 发票上传→t25/t26; 修改实验室→t51; 删除实验室→无对应转换(纯CRUD无状态迁移)
    # 评价导出→无对应转换(纯文件操作); 保存历史→t37/t38的附属操作; 批量审核→t44/t45
    # --- 3.4 因果 ---
    m.add_causal(
        frm="E-BM", to="E-JFTZ",
        desc="报名记录创建后系统自动初始化缴费通知单为未发送；报名审核通过后系统自动发送缴费通知单",
        trigger="报名记录创建/报名审核通过后缴费通知自动初始化与发送",
        trigger_source="expected_results",
        evidence_transitions=["t09", "t18", "t10", "t19"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1: E-BM创建直接致E-JFTZ初始化(系统自动)，Y无需额外操作→因果；门禁对照: 报名审核通过后缴费通知发送非Y侧precondition独立表达"},
    )
    m.add_causal(
        frm="E-BM", to="E-FY",
        desc="报名记录创建后系统自动初始化费用记录为待缴费",
        trigger="报名记录创建后费用记录自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t09", "t20"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1: E-BM创建直接致E-FY初始化(系统自动)，Y无需额外操作→因果"},
    )
    m.add_causal(
        frm="E-BM", to="E-FP",
        desc="报名记录创建后系统自动初始化发票记录为待开票",
        trigger="报名记录创建后发票记录自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t09", "t24"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1: E-BM创建直接致E-FP初始化(系统自动)，Y无需额外操作→因果"},
    )
    m.add_causal(
        frm="E-XM", to="E-YTZ",
        desc="能力验证计划发布时系统自动创建预通知并初始化为未发送",
        trigger="项目计划发布时预通知自动创建",
        trigger_source="expected_results",
        evidence_transitions=["t02", "t06"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1: E-XM计划发布直接致E-YTZ创建(系统自动)，Y无需额外操作→因果"},
    )

    # ===== Step 4: 约束 =====
    # --- 4.1 invalid ---
    # 文档未显式声明'不允许/不可以从X到Y'的状态转换禁止，无 add_invalid
    # --- 4.2 XC（跨实体约束） ---
    m.add_xc(xid="x01", source_entity="E-XM", source_transition="t02", source_state="报名中", target_entity="E-BM", target_dimension="报名记录状态", target_transition="t09", target_condition="报名待审核", xc_source="镜像", desc="项目进入报名中后联动开启报名记录创建，新记录初始化为报名待审核", source_ref="19.1实施阶段")
    m.add_xc(xid="x02", source_entity="E-BM", source_transition="t10", source_state="报名成功", target_entity="E-JFTZ", target_dimension="缴费通知单状态", target_transition="t19", target_condition="已发送", xc_source="联动", desc="报名审核通过后联动发送缴费通知单，缴费通知单状态变为已发送", source_ref="19.1实施阶段")
    m.add_xc(xid="x03", source_entity="E-BM", source_transition="t13", source_state="结果已提交", target_entity="E-PJ", target_dimension="评价状态", target_transition="t34", target_condition="评价中", xc_source="镜像", desc="报名记录结果已提交后联动开启评价，评价状态变为评价中", source_ref="19.1报告编制和结果通知；20.7.1.2协同评价")
    m.add_xc(xid="x04", source_entity="E-BM", source_transition="t15", source_state="报告/证书审核中", target_entity="E-TASK", target_dimension="审核任务状态", target_transition="t39", target_condition="待审核", xc_source="镜像", desc="报名记录进入报告/证书审核中后联动创建审核任务", source_ref="19.1报告编制和结果通知")
    m.add_xc(xid="x05", source_entity="E-TASK", source_transition="t42", source_state="已通过", target_entity="E-BM", target_dimension="报名记录状态", target_transition="t16", target_condition="报告/证书已发布", xc_source="4.5判", desc="审核任务通过后允许发放结果报告和证书，报名记录状态变为报告/证书已发布", source_ref="19.1报告编制和结果通知；3.4鉴别判为约束")
    m.add_xc(xid="x06", source_entity="E-YTZ", source_transition="t08", source_state="已确认", target_entity="E-BM", target_dimension="报名记录状态", target_transition="t13", target_condition="结果已提交", xc_source="4.5判", desc="预通知确认后参加者可提交测试结果，报名记录状态变为结果已提交", source_ref="19.1实施阶段；19.4参加者流程")
    # --- 4.3 BR（业务规则） ---
    m.add_br(bid="b01", category="notification", desc="系统每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则通过邮件方式对用户进行提醒并抄送项目管理员，提醒标题为证书到期提醒，内容为证书编号xxxx将于具体日期到期", entities_involved=["E-ZS"], source_ref="20.5.2.3增加证书到期前30天提醒功能", restrictive=True, note={"comment": "signal_type命中每天上午9点(时间触发)；category判通知；无状态落点，不入台账/operations"})
    m.add_br(bid="b02", category="notification", desc="报名审核通过后系统发送短信通知用户: 您xxx项目的报名信息审核通过，请知悉", entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知", restrictive=True, note={"comment": "signal_type命中审核通过后(时间触发)；category判通知"})
    m.add_br(bid="b03", category="notification", desc="报名审核退回修改后系统发送短信通知用户: 您xxx项目的报名信息审核未通过，请知悉", entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知", restrictive=True, note={"comment": "signal_type命中退回修改后；category判通知"})
    m.add_br(bid="b04", category="notification", desc="样品发放后系统发送短信通知用户: 您xxxx项目的样品已发出，请知悉", entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知", restrictive=True, note={"comment": "signal_type命中发样后；category判通知"})
    m.add_br(bid="b05", category="notification", desc="测试结果审核通过后系统发送短信通知用户: 您xxxx项目的测试报告审核通过，请知悉", entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知", restrictive=True, note={"comment": "signal_type命中审核通过；category判通知"})
    m.add_br(bid="b06", category="notification", desc="测试结果审核退回后系统发送短信通知用户: 您xxxx项目测试报告审核未通过，请知悉", entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知", restrictive=True, note={"comment": "signal_type命中审核未通过；category判通知"})
    m.add_br(bid="b07", category="notification", desc="结果通知单发布后系统发送短信通知用户: 您xxx项目的结果通知单已发布，请知悉", entities_involved=["E-BM"], source_ref="20.5.3.2操作节点增加用户短信通知", restrictive=True, note={"comment": "signal_type命中发布后；category判通知"})
    m.add_br(bid="b08", category="notification", desc="用户通过表单或审核一个已存在的任务生成新审核任务后，系统发送短信通知相关负责人: 您有一个新的xxx审核任务，请及时处理", entities_involved=["E-TASK"], source_ref="20.9.1.3增加任务提醒", restrictive=True, note={"comment": "signal_type命中生成新任务后(时间触发)；category判通知；无状态落点"})
    m.add_br(bid="b09", category="computation", desc="评价支持分值和权重两种方式，分值按累加计算得分，权重按加权计算得分", entities_involved=["E-PJ"], source_ref="20.7.1项目列表", enforcement="mandatory", note={"role": ["评价人员"], "comment": "signal_type命中两种(取值范围)；category判计算衍生"}, branch_dimensions=["评分方式"])
    m.add_br(bid="b10", category="display", desc="15天内发布的通知在内容前标注new标识，超过15天后此标识自动隐藏", entities_involved=[], source_ref="20.2.1通知公告", restrictive=True, note={"comment": "signal_type命中15天内(时间限制)；category判显示"})
    m.add_br(bid="b11", category="validation", desc="含有子项的记录不允许删除，删除前系统做前置判断", entities_involved=["E-STD"], source_ref="20.4.2.10删除测试项；20.4.3.4删除测试项", enforcement="mandatory", note={"comment": "signal_type命中不允许(禁止)；category判校验"}, constrained_entity="E-STD")
    m.add_br(bid="b12", category="validation", desc="退款金额不能为大于当前缴费金额，多次退款金额做累加处理", entities_involved=["E-FY"], source_ref="20.10.2.3缴费单退款", restrictive=True, note={"comment": "signal_type命中不能大于(限制)；category判校验"}, constrained_entity="E-FY")
    m.add_br(bid="b13", category="usability", desc="未结束的项目可以进行消息发送，已结束项目不可发送消息", entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能", restrictive=True, note={"comment": "signal_type命中未结束(条件限制)；category判可用性"}, constrained_entity="E-XM")
    m.add_br(bid="b14", category="validation", desc="消息发送时接收人1和接收人2不能同时为空", entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能", restrictive=True, note={"comment": "signal_type命中不能同时为空(禁止)；category判校验"}, constrained_entity="E-XM")
    m.add_br(bid="b15", category="validation", desc="批量处理中只有已上传对应文件且未提交审核的记录才可以被选定", entities_involved=["E-BM"], source_ref="20.5.1.3项目批量操作", restrictive=True, note={"comment": "signal_type命中只有...才可以(条件限制)；category判校验"}, constrained_entity="E-BM")
    m.add_br(bid="b16", category="authorization", desc="机构新增或修改实验室信息后需经管理用户审核通过后方可用于项目报名", entities_involved=["E-LAB"], source_ref="20.3.1实验室信息", enforcement="mandatory", note={"role": ["系统管理人员"], "comment": "signal_type命中后方可(条件限制)；category判授权"}, constrained_entity="E-LAB")
    m.add_br(bid="b17", category="validation", desc="停用的标准库在项目创建等环节不可被选择", entities_involved=["E-STD"], source_ref="20.4.2.5停用启用标准库", restrictive=True, note={"comment": "signal_type命中不可被选择(禁止)；category判校验"}, constrained_entity="E-STD")
    m.add_br(bid="b18", category="authorization", desc="信息发送记录只有系统管理员和项目管理员可以查看", entities_involved=["E-MSG"], source_ref="20.4.4.1信息发送记录", restrictive=True, note={"role": ["系统管理人员", "项目管理员"], "comment": "signal_type命中只有(权限限制)；category判授权"}, constrained_entity="E-MSG")
    m.add_br(bid="b19", category="authorization", desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果", entities_involved=["E-PJ"], source_ref="20.7.1.2协同评价", restrictive=True, note={"role": ["评价人员"], "comment": "signal_type命中只能/不能(权限限制)；category判授权"}, constrained_entity="E-PJ")
    m.add_br(bid="b20", category="authorization", desc="新建项目时第一个被选择的评价人员默认作为评价组长，评价组长可以在评价结果确认页面查看各评价人员的评价结果并对最终结果进行确认", entities_involved=["E-PJ"], source_ref="20.7.1项目列表", enforcement="mandatory", note={"role": ["评价人员"], "comment": "signal_type命中默认(规则)；category判授权"}, constrained_entity="E-PJ")
    m.add_br(bid="b21", category="usability", desc="并发100时每个页面响应时间不超过5秒，单次报名操作成功率应达到95%以上，支持至少300个同时在线用户数", entities_involved=[], source_ref="3.4性能要求；21.3性能要求", restrictive=True, note={"comment": "signal_type命中不超过/达到(指标限制)；category判可用性"})
    m.add_br(bid="b22", category="authorization", desc="对关键操作实施留痕机制，系统自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志", entities_involved=[], source_ref="20.11.1.2安全性相关内容优化", enforcement="mandatory", note={"comment": "signal_type命中自动记录(规则)；category判授权/审计"})
    m.add_br(bid="b23", category="usability", desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值", entities_involved=["E-XM"], source_ref="20.5.1.6默认填充技术主管实验室负责人授权签字人", enforcement="mandatory", note={"comment": "signal_type命中有且仅有一个时默认填充(规则)；category判可用性"}, constrained_entity="E-XM")
    m.add_br(bid="b24", category="usability", desc="系统内增加电子签章位置信息，当进行签章操作时自动代入此位置信息减少手动调整操作", entities_involved=["E-TASK"], source_ref="20.9.1.2预置签章位置信息", enforcement="mandatory", note={"comment": "signal_type命中自动代入(规则)；category判可用性"}, constrained_entity="E-TASK")
    m.add_br(bid="b25", category="usability", desc="测量审核结果通知单审批流程合并为一个流程，流程处理人审批顺序为提交申请时签字人的选择顺序", entities_involved=["E-TASK"], source_ref="20.9.1.1测量审核结果通知单审核流程优化", enforcement="mandatory", note={"comment": "signal_type命中合并为/为(规则)；category判可用性"}, constrained_entity="E-TASK")

    return m
