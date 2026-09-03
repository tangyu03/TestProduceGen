"""网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref

def build() -> DomainModel:
    m = DomainModel(source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704",
                    document_scope="§3.2；§3.6；§5–§18；§19.1；§19.2；§19.3；§19.4；§20.2–§20.11；§21.3。平行流程差异说明：§19.1能力验证与§19.2/§19.3测量审核为平行流程，收缩为同一组实体承载，差异经项目类型分支（能力验证/测量审核）与转换分立承载；测量审核预通知含审核环节（待审核/退回/已审核/退回闭环），能力验证预通知未体现审核环节；能力验证样品含还样分支（已还样/无需还样，归还落'已还样'独立状态），测量审核默认返样落'已还样'并于结果报告回收行复核（已还样→已核查）；测量审核项目先受理报名（报名中）后经设计方案编制转待开始，能力验证项目经设计方案编制创建（待开始）后计划发布转报名中；角色章节§6–§18为正文标题序号；§5修复C32：通知状态（流程表列称'预通知状态'）经19.1首现行'能力验证计划发布'（行3，值未发送）判定为项目级状态面，承载实体由E-BMJL迁至E-XM，创建转换t07动作锚定'能力验证计划发布'")
    # ===== 事件台账（§2）=====
    m.set_prohibition_config(config={
        "action_verbs": ["编制", "发布", "报名", "审核", "审批", "批准", "缴费", "开具", "核查", "发放", "发送",
                          "提交", "回收", "评价", "统计", "确认", "撤销", "停用", "启用", "修改", "删除", "新增",
                          "导入", "整理", "上传", "下载", "导出", "退回", "登记", "制备", "领用", "归还", "接收",
                          "选择", "生成"],
        "prohibit_keywords": ["不能同时为空", "不允许删除", "不可以删除", "不可被选择", "不能大于当前缴费金额",
                               "不能查看和修改其他评价人员的评价结果", "操作不可恢复"],
    })
    # —— 能力验证主流程（19.1表）与共用维度 ——
    m.add_event(eid="e01", entity="E-XM", dimension="项目状态", action="设计方案编制",
                actor="策划人员", precondition="初始", consequence="待开始",
                source_ref="19.1方案设计阶段")
    m.add_event(eid="e02", entity="E-XM", dimension="项目状态", action="能力验证计划发布",
                actor="项目管理员", precondition="待开始", consequence="报名中",
                source_ref="19.1实施阶段")
    m.add_event(eid="e03", entity="E-BMJL", dimension="报名记录状态", action="报名",
                actor="能力验证参加者", precondition="初始；E-XM.报名中；E-LAB.启用", consequence="报名待审核",
                source_ref="19.1实施阶段")
    m.add_event(eid="e04", entity="E-BMJL", dimension="费用状态", action="报名",
                actor="能力验证参加者", precondition="初始", consequence="待缴费",
                source_ref="19.1实施阶段")
    m.add_event(eid="e05", entity="E-BMJL", dimension="发票状态", action="报名",
                actor="能力验证参加者", precondition="初始", consequence="待开票",
                source_ref="19.1实施阶段")
    m.add_event(eid="e06", entity="E-JFTZ", dimension="缴费通知单状态", action="报名",
                actor="能力验证参加者", precondition="初始", consequence="未发送",
                source_ref="19.1实施阶段")
    m.add_event(eid="e07", entity="E-XM", dimension="通知状态", action="能力验证计划发布",
                actor="项目管理员", precondition="初始", consequence="未发送",
                source_ref="19.1实施阶段")
    m.add_event(eid="e08", entity="E-BMJL", dimension="报名记录状态", action="报名审核",
                actor="项目管理员", precondition="报名待审核；E-XM.报名中", consequence="报名成功",
                source_ref="19.1实施阶段")
    m.add_event(eid="e09", entity="E-BMJL", dimension="报名记录状态", action="报名审核",
                actor="项目管理员", precondition="报名待审核；E-XM.报名中", consequence="报名退回",
                source_ref="19.1实施阶段")
    m.add_event(eid="e10", entity="E-JFTZ", dimension="缴费通知单状态", action="发送缴费通知",
                actor="system", precondition="未发送；E-BMJL.报名成功", consequence="已发送",
                source_ref="19.1实施阶段；10项目管理员")
    m.add_event(eid="e11", entity="E-BMJL", dimension="费用状态", action="缴费",
                actor="能力验证参加者", precondition="待缴费；E-BMJL.报名成功", consequence="已缴费",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e12", entity="E-YP", dimension="样品状态", action="样品制备",
                actor="样品制备人员", precondition="初始", consequence="待核查",
                source_ref="19.1实施阶段；11样品制备人员")
    m.add_event(eid="e13", entity="E-BMJL", dimension="发票状态", action="发票开具",
                actor="财务管理人员", precondition="待开票；E-BMJL.报名成功", consequence="已开票",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e14", entity="E-XM", dimension="通知状态", action="能力验证预通知",
                actor="项目管理员", precondition="未发送", consequence="待确认",
                source_ref="19.1实施阶段")
    m.add_event(eid="e15", entity="E-BMJL", dimension="报名记录状态", action="能力验证预通知",
                actor="项目管理员", precondition="报名成功", consequence="结果待提交",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e16", entity="E-XM", dimension="项目状态", action="能力验证预通知",
                actor="项目管理员", precondition="报名中", consequence="进行中",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e17", entity="E-YP", dimension="样品状态", action="样品核查",
                actor="样品制备人员", precondition="待核查", consequence="已核查",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e18", entity="E-BMJL", dimension="报名记录样品状态", action="样品核查",
                actor="样品制备人员", precondition="初始；E-BMJL.结果待提交", consequence="待发样",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e19", entity="E-XM", dimension="通知状态", action="接收能力验证计划并确认",
                actor="能力验证参加者", precondition="待确认", consequence="已确认",
                source_ref="19.1实施阶段；19.4能力验证参加者工作流程分析")
    m.add_event(eid="e20", entity="E-BMJL", dimension="报名记录样品状态", action="样品发放,作业指导书发送",
                actor="项目管理员", precondition="待发样；E-BMJL.已确认", consequence="待收样",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e21", entity="E-BMJL", dimension="报名记录状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="结果待提交", consequence="结果已提交",
                source_ref="19.1实施阶段；19.3项目状态分析")
    m.add_event(eid="e22", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="已核查", consequence="已还样",
                source_ref="19.1实施阶段")
    m.add_event(eid="e23", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="已核查", consequence="已核查",
                source_ref="19.1实施阶段")
    m.add_event(eid="e24", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交，返样",
                actor="能力验证参加者", precondition="已核查", consequence="已还样",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e25", entity="E-BMJL", dimension="报名记录状态", action="结果报告回收",
                actor="项目管理员", precondition="结果已提交", consequence="结果已提交",
                source_ref="19.1报告编制和结果通知；19.3项目状态分析")
    m.add_event(eid="e26", entity="E-BMJL", dimension="报名记录状态", action="结果报告回收",
                actor="项目管理员", precondition="结果已提交", consequence="结果退回修改",
                source_ref="19.1报告编制和结果通知；19.3项目状态分析")
    m.add_event(eid="e27", entity="E-BMJL", dimension="报名记录状态", action="重新提交结果",
                actor="能力验证参加者", precondition="结果退回修改", consequence="结果已提交",
                source_ref="19.1报告编制和结果通知")
    m.add_event(eid="e28", entity="E-YP", dimension="样品状态", action="结果报告回收",
                actor="项目管理员", precondition="已还样", consequence="已核查",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e29", entity="E-BMJL", dimension="报名记录状态", action="撤销报名",
                actor="能力验证参加者", precondition="报名待审核", consequence="已撤销",
                source_ref="19.1实施阶段")
    m.add_event(eid="e30", entity="E-BMJL", dimension="报名记录状态", action="重新提交报名",
                actor="能力验证参加者", precondition="报名退回", consequence="报名待审核",
                source_ref="19.1实施阶段")
    # —— 项目评价（20.7）——
    m.add_event(eid="e31", entity="E-PJ", dimension="评价状态", action="选择评价人员",
                actor="项目管理员", precondition="初始", consequence="待评价",
                source_ref="20.7.1.2协同评价")
    m.add_event(eid="e32", entity="E-PJ", dimension="评价状态", action="评价人员评价",
                actor="评价人员", precondition="待评价；E-BMJL.结果已提交", consequence="评价中",
                source_ref="20.7.1.2协同评价")
    m.add_event(eid="e33", entity="E-PJ", dimension="评价状态", action="提交评价结果",
                actor="评价人员", precondition="评价中", consequence="评价中",
                source_ref="20.7.1.2协同评价")
    m.add_event(eid="e34", entity="E-PJ", dimension="评价状态", action="确认评价结果",
                actor="评价组长", precondition="评价中", consequence="已关闭",
                source_ref="20.7.1.3评价确认")
    m.add_event(eid="e35", entity="E-PJ", dimension="评价状态", action="退回修改",
                actor="评价组长", precondition="评价中", consequence="评价中",
                source_ref="20.7.1.3评价确认")
    # —— 报告编制与结果通知（19.1表）——
    m.add_event(eid="e36", entity="E-BMJL", dimension="报名记录状态", action="编制结果报告",
                actor="策划人员", precondition="结果已提交", consequence="报告/证书审核中",
                source_ref="19.1报告编制和结果通知")
    m.add_event(eid="e37", entity="E-XM", dimension="项目状态", action="编制结果报告",
                actor="策划人员", precondition="进行中", consequence="报告审核中",
                source_ref="19.1报告编制和结果通知；19.3项目状态分析")
    m.add_event(eid="e38", entity="E-BMJL", dimension="报名记录状态", action="发放结果报告和证书",
                actor="项目管理员", precondition="报告/证书审核中；E-TASK.审批通过", consequence="报告/证书已发布",
                source_ref="19.1报告编制和结果通知；19.3项目状态分析")
    m.add_event(eid="e39", entity="E-XM", dimension="项目状态", action="发放结果报告和证书",
                actor="项目管理员", precondition="报告审核中", consequence="已结束",
                source_ref="19.1报告编制和结果通知；19.3项目状态分析")
    # —— 测量审核平行流程差异事件（19.3表）——
    m.add_event(eid="e40", entity="E-XM", dimension="项目状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="初始；E-LAB.启用", consequence="报名中",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e41", entity="E-BMJL", dimension="报名记录状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="初始；E-LAB.启用", consequence="报名待审核",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e42", entity="E-BMJL", dimension="费用状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="初始", consequence="待缴费",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e43", entity="E-BMJL", dimension="发票状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="初始", consequence="待开票",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e44", entity="E-XM", dimension="项目状态", action="设计方案编制",
                actor="策划人员", precondition="报名中", consequence="待开始",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e45", entity="E-YP", dimension="样品状态", action="样品领用登记",
                actor="样品管理员", precondition="初始", consequence="待核查",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e46", entity="E-XM", dimension="通知状态", action="作业指导书编制",
                actor="策划人员", precondition="未发送", consequence="待审核",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e47", entity="E-XM", dimension="通知状态", action="审核预通知",
                actor="技术主管", precondition="待审核", consequence="已审核",
                source_ref="19.3项目状态分析；7技术主管")
    m.add_event(eid="e48", entity="E-XM", dimension="通知状态", action="退回预通知",
                actor="技术主管", precondition="待审核", consequence="退回",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e49", entity="E-XM", dimension="通知状态", action="修改预通知",
                actor="策划人员", precondition="退回", consequence="待审核",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e50", entity="E-XM", dimension="通知状态", action="能力验证预通知",
                actor="项目管理员", precondition="已审核", consequence="待确认",
                source_ref="19.3项目状态分析")
    # —— 实验室（20.3.1/20.4.1）——
    m.add_event(eid="e51", entity="E-LAB", dimension="实验室状态", action="机构新增实验室信息",
                actor="公众客户", precondition="初始", consequence="待审核",
                source_ref="20.3.1实验室信息")
    m.add_event(eid="e52", entity="E-LAB", dimension="实验室状态", action="机构修改实验室信息",
                actor="公众客户", precondition="启用", consequence="待审核",
                source_ref="20.3.1实验室信息；20.4.1.3实验室修改")
    m.add_event(eid="e53", entity="E-LAB", dimension="实验室状态", action="机构修改实验室信息",
                actor="公众客户", precondition="退回修改", consequence="待审核",
                source_ref="20.3.1实验室信息；20.4.1.3实验室修改")
    m.add_event(eid="e54", entity="E-LAB", dimension="实验室状态", action="实验室审核",
                actor="系统管理人员", precondition="待审核", consequence="启用",
                source_ref="20.4.1.2实验室审核")
    m.add_event(eid="e55", entity="E-LAB", dimension="实验室状态", action="实验室审核",
                actor="系统管理人员", precondition="待审核", consequence="退回修改",
                source_ref="20.4.1.2实验室审核")
    m.add_event(eid="e56", entity="E-LAB", dimension="实验室状态", action="停用实验室",
                actor="系统管理人员", precondition="启用", consequence="停用",
                source_ref="20.4.1.1实验室列表与查询")
    m.add_event(eid="e57", entity="E-LAB", dimension="实验室状态", action="启用实验室",
                actor="系统管理人员", precondition="停用", consequence="启用",
                source_ref="20.4.1.1实验室列表与查询")
    # —— 标准库（20.4.2）——
    m.add_event(eid="e58", entity="E-BZ", dimension="标准库状态", action="新增标准库",
                actor="系统管理人员", precondition="初始", consequence="启用",
                source_ref="20.4.2.2新增标准库")
    m.add_event(eid="e59", entity="E-BZ", dimension="标准库状态", action="停用标准库",
                actor="系统管理人员", precondition="启用", consequence="停用",
                source_ref="20.4.2.5停用/启用标准库")
    m.add_event(eid="e60", entity="E-BZ", dimension="标准库状态", action="启用标准库",
                actor="系统管理人员", precondition="停用", consequence="启用",
                source_ref="20.4.2.5停用/启用标准库")
    # —— 流程审批任务（20.9）——
    m.add_event(eid="e61", entity="E-TASK", dimension="任务状态", action="生成审核任务",
                actor="system", precondition="初始", consequence="待审批",
                source_ref="20.9.1.3增加任务提醒")
    m.add_event(eid="e62", entity="E-TASK", dimension="任务状态", action="批量审核",
                actor="审核人员", precondition="待审批", consequence="审批通过",
                source_ref="20.9.1.4任务批量处理")
    m.add_event(eid="e63", entity="E-TASK", dimension="任务状态", action="批量审核",
                actor="审核人员", precondition="待审批", consequence="审批退回",
                source_ref="20.9.1.4任务批量处理")
    m.add_event(eid="e64", entity="E-TASK", dimension="任务状态", action="重新提交任务",
                actor="策划人员", precondition="审批退回", consequence="待审批",
                source_ref="20.9.1.4任务批量处理")
    # —— 测量审核项目状态补链（19.3表实施阶段）——
    m.add_event(eid="e65", entity="E-XM", dimension="项目状态", action="能力验证预通知",
                actor="项目管理员", precondition="待开始", consequence="进行中",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e66", entity="E-BMJL", dimension="报名记录状态", action="编制结果通知单",
                actor="策划人员", precondition="结果已提交", consequence="报告/证书审核中",
                source_ref="19.3项目状态分析")
    m.add_event(eid="e67", entity="E-XM", dimension="项目状态", action="编制结果通知单",
                actor="策划人员", precondition="进行中", consequence="报告审核中",
                source_ref="19.3项目状态分析")
    # —— 报名记录样品状态补链（19.3枚举+19.4参加者流程）——
    m.add_event(eid="e68", entity="E-BMJL", dimension="报名记录样品状态", action="接收样品",
                actor="能力验证参加者", precondition="待收样", consequence="已收样",
                source_ref="19.4能力验证参加者工作流程分析")
    m.add_event(eid="e69", entity="E-BMJL", dimension="报名记录样品状态", action="确认收样",
                actor="能力验证参加者", precondition="已收样", consequence="已确认",
                source_ref="19.3项目状态分析")
    # ===== Step 1：实体 =====
    # 1.1 角色（来源 actor ∪ 3.2功能要求权限章节；name＝原文逐字；system不入roles；评价组长为20.7台账actor随台账推导入列）
    m.add_role(id="r01", name="公众客户")
    m.add_role(id="r02", name="超级管理员")
    m.add_role(id="r03", name="项目管理员")
    m.add_role(id="r04", name="评价人员")
    m.add_role(id="r05", name="审核人员")
    m.add_role(id="r06", name="财务人员")
    m.add_role(id="r07", name="实验室负责人")
    m.add_role(id="r08", name="技术主管")
    m.add_role(id="r09", name="授权签字人")
    m.add_role(id="r10", name="策划人员")
    m.add_role(id="r11", name="样品制备人员")
    m.add_role(id="r12", name="样品管理员")
    m.add_role(id="r13", name="统计人员")
    m.add_role(id="r14", name="质量专员", readonly=True)
    m.add_role(id="r15", name="财务管理人员")
    m.add_role(id="r16", name="系统管理人员")
    m.add_role(id="r17", name="能力验证参加者")
    m.add_role(id="r18", name="监督员", readonly=True)
    m.add_role(id="r19", name="评价组长")
    # 1.1 权限（operations限查询/文件/界面/配置及不改状态操作；状态变更操作由转换承载）
    m.add_permission(role="项目管理员", operations=["查询项目", "新增项目", "文件整理", "代码导入", "批量处理", "消息发送", "导出数据", "打包下载", "查询统计数据"])
    m.add_permission(role="系统管理人员", operations=["查询实验室", "下载证明文件", "查询标准库", "查询信息发送记录", "查看消息详情", "导入历史数据", "查询历史项目"])
    m.add_permission(role="能力验证参加者", operations=["查询项目", "下载文件", "上传缴费证明", "上传结果报告", "意见反馈"])
    m.add_permission(role="评价人员", operations=["查询项目", "导出评价结果"])
    m.add_permission(role="评价组长", operations=["查询项目", "下载历史记录"])
    m.add_permission(role="财务人员", operations=["查询缴费信息", "导出缴费数据", "查询收入统计"])
    m.add_permission(role="财务管理人员", operations=["查询缴费信息", "导出缴费数据", "发票下载"])
    m.add_permission(role="超级管理员", operations=["维护通知公告", "权限分配", "查询信息发送记录"])
    m.add_permission(role="统计人员", operations=["查询统计数据", "导出统计数据"])
    m.add_permission(role="技术主管", operations=["查询审核任务", "导出审批列表"])
    m.add_permission(role="实验室负责人", operations=["查询审核任务"])
    m.add_permission(role="授权签字人", operations=["查询审核任务", "导出审批列表"])
    m.add_permission(role="审核人员", operations=["查询审核任务", "导出审批列表"])
    m.add_permission(role="策划人员", operations=["查询项目", "下载文件"])
    m.add_permission(role="样品制备人员", operations=["查询样品"])
    m.add_permission(role="样品管理员", operations=["查询样品", "出入库登记"])
    m.add_permission(role="公众客户", operations=["查询项目", "浏览通知公告", "意见反馈"])
    m.add_permission(role="质量专员", operations=["查询统计数据"])
    m.add_permission(role="监督员", operations=[])
    # 1.2/1.3/1.4 分组与状态推导（entity列即分组结果；状态面唯一承载：流程表'样品状态'列物流值并入E-BMJL.报名记录样品状态）
    m.add_entity(
        id="E-XM", name="项目", desc="能力验证/测量审核项目载体，承载项目状态流转、项目级预通知状态、评价、报告与证书发放",
        type="core", tags=["approvable", "multi-state", "collaborative", "configurable"],
        attributes=[
            attr("项目类型", desc="能力验证/测量审核（20.8.3.1项目类型选项）"),
            attr("产品类型", desc="下拉选项为系统内所有的产品信息（20.8.3.1）"),
            attr("项目名称", desc="项目名称（20.8.3.1）"),
            attr("子领域", desc="项目所属子领域（20.7.1.2）"),
            attr("评分方式", desc="支持分值和权重两种评价方式（20.7.1）", is_config=True),
            attr("依据标准", desc="项目依据标准（20.7.1.2）"),
            attr("监督员", desc="项目新增表单新增监督员字段，导出项目通知书时填充到对应位置（20.5.1.5）"),
            attr("技术主管", desc="项目人员信息字段，备选人有且仅有一个时默认填充（20.5.1.6）"),
            attr("实验室负责人", desc="项目人员信息字段，备选人有且仅有一个时默认填充（20.5.1.6）"),
            attr("授权签字人", desc="项目人员信息字段，备选人有且仅有一个时默认填充（20.5.1.6）"),
            attr("项目费用", desc="项目费用金额，退款后更新为实际付款金额（20.8.4.1；20.10.2.3）"),
            attr("所属年度", desc="项目所属年度（20.8.3.1）"),
        ],
        state_dimensions=[
            {"dimension_name": "项目状态", "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
             "initial": "待开始", "terminal": ["已结束"], "inferred": [],
             "note": {"comment": "状态值与顺序取自19.3枚举表；报名中→进行中→报告审核中→已结束链路无显式台账行，由e16/e37/e39（能力验证）与e65/e67/e39（测量审核）推断补链，见转换note；测量审核侧先受理报名（报名中）后经设计方案编制转待开始（序判④语义优先）"}},
            {"dimension_name": "通知状态", "states": ["未发送", "待确认", "待审核", "退回", "已审核", "已批准", "已确认"],
             "initial": "未发送", "terminal": ["已确认"], "inferred": [],
             "note": {"comment": "枚举取19.3通知状态（流程表列称'预通知状态'，两口径并列）；'已确认'为台账推导值（19.1/19.3样品发放行预通知状态列），追加于枚举之后；'已批准'枚举但无事件覆盖，孤岛原样保留（框架降级警告）；§5修复C32：本维度自E-BMJL迁至E-XM项目级——19.1流程表预通知状态列首现于'能力验证计划发布'行（行3，值未发送），早于报名记录创建（行4），报名记录尚不存在不能承载初始化，状态面出生点锚定首现动作（t07，action=能力验证计划发布），E-BMJL不再承载初始化；19.3枚举将通知状态列为报名记录子状态类型，与流程表首现行矛盾，本裁决以流程表首现行为准（文档即数据，矛盾已按C32框架裁决消解）"}},
        ],
        operations=[
            op("新增项目", "crud", ["项目创建并进入状态流转，初始状态为待开始（推断）"], "20.5.1.5项目新增表单增加监督员",
               note=N(role=["项目管理员"], comment="点击菜单或项目列表页'新增'进入项目新增表单页面；项目状态创建落点由台账e01设计方案编制承载")),
            op("删除项目", "crud", ["项目记录删除（推断）"], "20.2.3待办事项",
               note=N(role=["项目管理员", "超级管理员"], comment="管理侧待办'能力验证项目删除'")),
            op("设计方案编制", "crud", ["编制和更新设计方案等文件（9策划人员文件管理）"], "19.1方案设计阶段",
               note=N(role=["策划人员"], comment="台账e01创建事件对应操作")),
            op("文件整理", "file", ["系统开启整理任务并提示用户'归档任务已开启，请稍后查看'", "整理完成后操作列会显示【查看归档】按钮"], "20.5.1.1文件整理",
               note=N(role=["项目管理员"], comment="category①file；已结束的项目记录可操作；20.6.1.1测量审核同机制")),
            op("代码导入", "file", ["导入报名机构的三方代码"], "20.5.1.2机构代码导入",
               note=N(role=["项目管理员"], comment="category①file")),
            op("批量处理", "ui", ["点击操作列中的'批量处理'按钮跳转到报名信息批量处理页面"], "20.5.1.3项目批量操作",
               note=N(role=["项目管理员"], comment="category③ui；集中完成通知单与证书上传后可批量提交审核")),
            op("消息发送", "ui", ["如系统验证通过则将消息按选择的方式进行发送"], "20.5.1.4优化消息发送功能",
               note=N(role=["项目管理员"], comment="category③ui；未结束的项目可以进行消息发送；发送留痕落E-JL信息发送记录")),
            op("查询项目", "query", ["查询并在列表中分页展示所有符合条件的数据记录"], "20.8.3.1项目查询与统计",
               note=N(role=["项目管理员", "策划人员", "评价人员", "评价组长", "能力验证参加者"], comment="多模块列表查询通用操作")),
            op("上传结果通知单", "file", ["结果通知单上传成功，可批量提交审核（推断）"], "20.5.1.3项目批量操作",
               note=N(role=["项目管理员"], comment="category①file；按处理内容与是否已上传判定按钮显示")),
            op("上传证书", "file", ["证书上传成功，可批量提交审核（推断）"], "20.5.1.3项目批量操作",
               note=N(role=["项目管理员"], comment="category①file；按处理内容与是否已上传判定按钮显示")),
            op("导出数据", "file", ["点击'导出'按钮，导出满足当前查询条件的数据"], "20.9.1.5审批流程列表导出",
               note=N(role=["项目管理员"], comment="category①file；统计与列表导出通用操作（20.8/20.10多模块）")),
            op("导入历史数据", "file", ["对往年项目数据进行分析整理，并导入到系统中为数据分析提供关键数据"], "20.11其他",
               note=N(role=["系统管理人员"], comment="category①file")),
            op("查询历史项目", "query", ["查询并在列表中分页展示所有符合条件的数据记录"], "20.11.1.1历史数据列表",
               note=N(role=["系统管理人员"], comment="列表中的数据除系统启用后的数据外还包含往年的历史数据（20.8.4.1同口径）")),
            op("查询统计数据", "query", ["点击相应的菜单，进入到相应的统计页面，进行相应的操作"], "20.8统计分析",
               note=N(role=["项目管理员", "统计人员", "质量专员"], comment="项目总览/数据看板/项目统计与查询/收入统计/统计对比/业务上报统计/项目上报等模块")),
        ],
    )
    m.add_entity(
        id="E-BMJL", name="报名记录", desc="参加者对项目的报名记录，承载报名审核、结果提交、报告/证书发布、费用与发票、样品物流（预通知确认状态面经§5修复C32迁E-XM项目级）",
        type="core", tags=["approvable", "multi-state", "collaborative", "expirable"],
        attributes=[
            attr("报名编号", desc="报名记录编号（20.8.3.2）"),
            attr("统一社会信用代码", desc="报名实验室统一社会信用代码（20.8.3.2）"),
            attr("实验室名称", desc="报名实验室名称（20.8.3.2）"),
            attr("行政区划", desc="报名实验室行政区划（20.8.3.2）"),
            attr("报名时间", desc="报名时间（20.8.3.2）"),
            attr("评价得分", desc="评价得分（20.8.4.1）"),
            attr("评价结果", desc="评价结果（20.8.4.1）"),
            attr("证书编号", desc="证书编号（20.8.4.1；20.11.1.1）"),
            attr("证书时间", desc="证书时间（20.11.1.1）"),
            attr("财务备注", desc="财务备注字段，管理人员可修改备注内容（20.10.2.1）"),
        ],
        state_dimensions=[
            {"dimension_name": "报名记录状态", "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
             "initial": "报名待审核", "terminal": ["报告/证书已发布", "已撤销"], "inferred": [],
             "note": {"comment": "状态值与顺序取自19.3枚举表；'已撤销'经报名行斜杠分支值补链（t29）；报名退回→报名待审核重新提交补链（t30，图完整性闭合）"}},
            {"dimension_name": "报名记录样品状态", "states": ["待发样", "待收样", "已收样", "已确认"],
             "initial": "待发样", "terminal": ["已确认"], "inferred": [],
             "note": {"comment": "19.3枚举；维度首落点为样品核查行'已核查、待发样'顿号快照第二值（t18创建转换即该落点）；流程表'样品状态'列'待发样''已发样'等物流值并入本维度承载（状态面唯一承载），'已发样'与'待收样'同节点两口径并列；已收样→已确认由t69推断补链"}},
            {"dimension_name": "费用状态", "states": ["待缴费", "已缴费"],
             "initial": "待缴费", "terminal": ["已缴费"], "inferred": [],
             "note": {"comment": "19.3枚举；退款仅更新项目费用属性为实际付款金额，不改变费用状态（20.10.2.3）"}},
            {"dimension_name": "发票状态", "states": ["待开票", "已开票"],
             "initial": "待开票", "terminal": ["已开票"], "inferred": [],
             "note": {"comment": "19.3枚举；20.10.2.2发票上传支持多次分批上传，落点同为已开票"}},
        ],
        operations=[
            op("发票上传", "file", ["发票上传后会显示在此列表中，点击文件地址后的'x'可以移除文件（表单提交后生效）"], "20.10.2.2修改发票上传功能",
               note=N(role=["财务人员", "财务管理人员"], comment="category①file；支持多次分批上传")),
            op("修改备注", "crud", ["点击提交表单保存财务备注"], "20.10.2.1项目列表增加财务备注字段",
               note=N(role=["财务人员"], comment="报名编号只读显示当前项目的报名编号")),
            op("提交结果报告", "file", ["参加者在完成测试后，提交结果报告"], "19.4能力验证参加者工作流程分析",
               note=N(role=["能力验证参加者"], comment="category①file；结果填写&上传（3.2功能要求客户业务）；转换落点t21")),
            op("上传缴费证明", "file", ["参加者上传缴费证明"], "18能力验证参加者",
               note=N(role=["能力验证参加者"], comment="category①file；报名缴费职责'进行缴费，上传缴费证明。接收发票'；转换落点t11")),
        ],
    )
    m.add_entity(
        id="E-YP", name="样品", desc="能力验证物品/样品及其制备、核查、发放与还样复核",
        type="core", tags=["collaborative"],
        attributes=[],
        state_dimensions=[
            {"dimension_name": "样品状态", "states": ["待核查", "已核查", "已还样"],
             "initial": "待核查", "terminal": [], "inferred": [],
             "note": {"comment": "19.3枚举'待核查，已核查'；19.1流程表'已还样、待核查/无需还样'快照限定词'已还样'立为独立状态（返样/归还后待复核，与首次'待核查'区分——19.3返样行'待核查'即此义）；发放前核查（待核查→已核查）与还样后复核（已还样→已核查，t28测量审核）构成批次循环，无终态；流程表'样品状态'列状态值由本维度承载，物流值并入E-BMJL.报名记录样品状态"}},
        ],
        operations=[
            op("样品制备", "crud", ["编制样品制备方案，执行样品制备"], "11样品制备人员",
               note=N(role=["样品制备人员"], comment="台账e12创建事件对应操作")),
            op("样品核查", "crud", ["负责样品的配置、核查和一致性测试，生成核查记录表"], "19.1实施阶段",
               note=N(role=["样品制备人员"], comment="核查落点t17（E-YP样品状态）与t18（E-BMJL报名记录样品状态）")),
            op("样品领用登记", "crud", ["样品领用出库登记，样品状态为待核查"], "19.3项目状态分析",
               note=N(role=["样品管理员"], comment="测量审核侧样品创建（t45）；库存管理'样品出入库登记和管理'")),
            op("样品发放", "crud", ["您xxxx项目的样品已发出，请知悉"], "20.5.3.2操作节点增加用户短信通知",
               note=N(role=["项目管理员"], comment="发样短信通知；转换落点t20在E-BMJL.报名记录样品状态（跨实体）")),
            op("出入库登记", "crud", ["样品出入库登记和管理（推断）"], "12样品管理员",
               note=N(role=["样品管理员"], comment="库存管理职责，无状态面落点，不入转换")),
            op("查询样品", "query", ["查询样品信息（推断）"], "12样品管理员",
               note=N(inferred=True, role=["样品管理员", "样品制备人员"], comment="据库存管理职责推断的查询操作")),
        ],
    )
    m.add_entity(
        id="E-PJ", name="评价", desc="项目评价任务，承载协同评价、评价确认与评价结果导出",
        type="core", tags=["collaborative"],
        attributes=[
            attr("及格分", desc="及格分录入后跟随其他结果一起记录到系统中（20.7.1.3）"),
            attr("统计规则", desc="每个统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值（20.7.1.3）"),
        ],
        state_dimensions=[
            {"dimension_name": "评价状态", "states": ["待评价", "评价中", "已关闭"],
             "initial": "待评价", "terminal": ["已关闭"], "inferred": ["待评价", "评价中", "已关闭"],
             "note": {"comment": "文档未枚举评价状态，三值均为语义命名（inferred成对标注）：'待评价'为评价任务建立后、评价动作开始前的待操作情形（20.7.1.2协同评价页面提供分数录入入口），'评价中'为评价人员进行输入/调整分数的动作进行中情形（20.7.1.2），'已关闭'据'项目评价状态关闭'（20.7.1.3）语义命名；§5修复C16：'待评价''评价中'经原文全文检索无逐字命中，补入inferred声明并修正原note'散见于20.7.1.2'的不实表述"}},
        ],
        operations=[
            op("评价", "crud", ["评价人员找到评价项对应单元格可以输入或调整评价分数", "确定：按钮，点击提交结果"], "20.7.1.2协同评价",
               note=N(role=["评价人员"], comment="此页面只显示评价人员自己的评价结果")),
            op("结果确认", "crud", ["点击后将当前结果正式提交为项目的最终评价结果，项目评价状态关闭"], "20.7.1.3评价确认",
               note=N(role=["评价组长"], comment="转换落点t34")),
            op("完善评价细则", "crud", ["确定：按钮，点击后保存完善后的测试项目数据"], "20.7.1.1测试项目、评价细则完善",
               note=N(role=["评价组长"], comment="评价组长点击'编辑'按钮进入完善页面；完善完成作为t32的event_ref前置信号")),
            op("导出评价结果", "file", ["评价人员点击项目列表操作列中的'导出'按钮，下载评价结果"], "20.7.1.4评价结果导出",
               note=N(role=["评价人员"], comment="category①file")),
            op("保存历史", "crud", ["将当前评价结果保存为历史结果"], "20.7.1.3评价确认",
               note=N(role=["评价组长"])),
            op("调整细则", "ui", ["点击打开评价细节完善页面，配置完成后回到本页面将会刷新本页面数据"], "20.7.1.3评价确认",
               note=N(role=["评价组长"], comment="category③ui")),
            op("配置统计规则", "config", ["评价组长可在此弹窗中配置统计规则"], "20.7.1.3评价确认",
               note=N(role=["评价组长"], comment="category④config；成绩区间统计区调整统计规则")),
            op("统计分析", "query", ["对评价进行统计，生成评价统计表（推断）"], "19.1报告编制和结果通知",
               note=N(role=["统计人员", "评价人员"], comment="与统计人员合作，进行结果的统计分析（13评价人员统计分析职责）")),
            op("下载历史记录", "file", ["点击文件链接即可下载评价历史结果"], "20.7.1.3评价确认",
               note=N(role=["评价组长"], comment="category①file；历史记录下载区")),
        ],
    )
    m.add_entity(
        id="E-TASK", name="审核任务", desc="流程审批任务，覆盖通知/报告/证书等文档审核与批量处理",
        type="core", tags=["approvable", "collaborative"],
        attributes=[
            attr("任务类型", desc="审核类型名称，如结果通知单审核（20.9.1.3）"),
            attr("创建时间", desc="审批流程列表创建时间查询参数（20.9.1.5）"),
            attr("审核意见", desc="批量审核表单审核意见，选填（20.9.1.4）"),
            attr("签章位置信息", desc="系统内增加电子签章位置信息，签章操作时自动代入（20.9.1.2）"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态", "states": ["待审批", "审批通过", "审批退回"],
             "initial": "待审批", "terminal": ["审批通过"], "inferred": ["待审批", "审批通过", "审批退回"],
             "note": {"comment": "文档未枚举任务状态值；据20.9.1.4审核结果选项'同意、退回'及'生成一个新的审核任务'语义命名，inferred成对标注；20.9.1.7以不同颜色标记各状态节点佐证状态多样"}},
        ],
        operations=[
            op("批量审核", "crud", ["点击进行批量审核操作，所选任务按审核结果更新（推断）"], "20.9.1.4任务批量处理",
               note=N(role=["审核人员", "技术主管", "授权签字人", "实验室负责人"], comment="系统会根据任务节点的类型及内容判断当前节点是否可以被批量处理；转换落点t62/t63")),
            op("提交审核", "crud", ["对选择记录进行任务提交操作，如没有选择记录将提示用户选择记录信息"], "20.5.1.3项目批量操作",
               note=N(role=["项目管理员"], comment="E-XM批量处理页面入口，跨实体生成E-TASK审核任务（t61）")),
            op("查询审核任务", "query", ["查询审批流程列表数据（推断）"], "20.9.1.5审批流程列表导出",
               note=N(role=["审核人员", "技术主管", "授权签字人", "实验室负责人"])),
            op("导出审批列表", "file", ["点击'导出'按钮，导出满足当前查询条件的数据"], "20.9.1.5审批流程列表导出",
               note=N(role=["审核人员", "技术主管", "授权签字人", "实验室负责人"], comment="category①file")),
            op("签章", "crud", ["进行签章操作时自动代入预置签章位置信息，减少手动调整操作"], "20.9.1.2预置签章位置信息",
               note=N(role=["授权签字人", "实验室负责人"])),
        ],
    )
    m.add_entity(
        id="E-JFTZ", name="缴费通知单", desc="随报名记录自动初始化的缴费通知单，承载发送状态",
        type="managed", tags=[],
        attributes=[],
        state_dimensions=[
            {"dimension_name": "缴费通知单状态", "states": ["未发送", "已发送"],
             "initial": "未发送", "terminal": ["已发送"], "inferred": [],
             "note": {"comment": "19.1/19.3流程表'缴费通知单'列取值；报名记录创建后系统自动初始化为未发送，报名审核通过后系统自动发送（见因果E-BMJL→E-JFTZ）"}},
        ],
        operations=[
            op("编制缴费通知", "crud", ["编制缴纳测量审核费用通知，生成缴费通知书"], "19.3项目状态分析",
               note=N(role=["项目管理员"], comment="仅编制文件，无状态落点，不入转换")),
        ],
    )
    m.add_entity(
        id="E-FY", name="缴费单", desc="参加者付款记录，支持多次付款与退款冲抵",
        type="managed", tags=[],
        attributes=[
            attr("支付方式", desc="下拉选择框，必填（20.5.2.1）"),
            attr("支付账户名称", desc="文本输入框，必填（20.5.2.1）"),
            attr("汇款金额", desc="文本输入框，必填，默认为项目费用金额（20.5.2.1）"),
            attr("付款底单", desc="文件选择框，必填（20.5.2.1）"),
            attr("付款项目", desc="文本输入框，只读，内容为当前报名编号（20.5.2.1）"),
            attr("退款金额", desc="多次退款金额做累加处理，退款金额使用红色字体且大于0时显示（20.10.2.3）"),
            attr("实际付款", desc="付款金额-退款金额=实际付款（20.10.2.3）"),
            attr("管理备注", desc="用于记录退款原因等内容（20.10.2.3）"),
        ],
        state_dimensions=[],
        operations=[
            op("上传付款单", "file", ["点击提交表单，录入付款信息并上传付款底单"], "20.5.2.1已报名项目增加多次付款功能",
               note=N(role=["能力验证参加者"], comment="category①file；可多次进行付款操作，不对付款金额进行校验限制；触发E-BMJL费用状态缴费转换t11（跨实体）")),
            op("缴费单退款", "crud", ["退款后更新'项目费用'为实际付款金额"], "20.10.2.3缴费单退款",
               note=N(role=["财务人员"], comment="缴费记录中增加退款功能；仅属性变更，无状态落点，无对应转换不调用link_op_transition")),
        ],
    )
    m.add_entity(
        id="E-LAB", name="实验室", desc="机构实验室信息，承载新增/修改送审、审核、停用启用",
        type="core", tags=["approvable", "collaborative"],
        attributes=[
            attr("实验室编号", desc="文本输入框，模糊查询（20.4.1.1）"),
            attr("实验室名称", desc="实验室名称（20.3.1）"),
            attr("统一社会信用代码", desc="统一社会信用代码（20.3.1）"),
            attr("法人名称", desc="法人名称（20.3.1）"),
            attr("企业类型", desc="企业类型（20.3.1）"),
            attr("企业规模", desc="企业规模（20.3.1）"),
            attr("CNAS", desc="已获CNAS认可及证书号（20.4.1.3）"),
            attr("CMA", desc="已获CMA认可及证书编号（20.4.1.3）"),
            attr("邮箱", desc="邮箱（20.3.1）"),
            attr("座机号码", desc="座机号码（20.3.1）"),
            attr("地址", desc="行政区域、详细地址（20.4.1.3）"),
            attr("联系人", desc="联系人（20.3.1）"),
            attr("联系电话", desc="联系电话（20.3.1）"),
            attr("默认实验室", desc="默认实验室标识（20.3.1）"),
            attr("证明文件", desc="证明文件表单提示：请上传营业执照或其他证书材料（20.3.1）"),
        ],
        state_dimensions=[
            {"dimension_name": "实验室状态", "states": ["待审核", "启用", "停用", "退回修改"],
             "initial": "待审核", "terminal": [], "inferred": [],
             "note": {"comment": "20.3.1枚举'状态包括：待审核、启用、停用、退回修改'；20.4.1.2审核退回落点原文'已退回'与枚举'退回修改'两口径并列，取枚举值；停用经启用实验室（t57）有出边，无终态；启用后方可用于项目报名（b02门禁）"}},
        ],
        operations=[
            op("审核实验室", "crud", ["如果审核结果为通过，实验室状态变更为'启用'，并为当前数据生成该数据的快照记录"], "20.4.1.2实验室审核",
               note=N(role=["系统管理人员"], comment="原文'使用人员对机构提交的新增或修改的实验室信息进行审核'，按模块归属系统管理人员；转换落点t54/t55")),
            op("修改实验室", "crud", ["【确认】按钮：提交修改内容"], "20.4.1.3实验室修改",
               note=N(role=["公众客户"], comment="提交后需经管理用户审核（t52/t53）")),
            op("删除实验室", "crud", ["删除实验室信息记录（推断）"], "20.3.1实验室信息",
               note=N(role=["公众客户"], comment="20.3.1操作：修改、删除")),
            op("停用实验室", "crud", ["停用（启用状态显示）按钮，状态立即改变"], "20.4.1.1实验室列表与查询",
               note=N(role=["系统管理人员"], comment="转换落点t56")),
            op("启用实验室", "crud", ["启用（停用状态显示）按钮，状态立即改变"], "20.4.1.1实验室列表与查询",
               note=N(role=["系统管理人员"], comment="转换落点t57")),
            op("查询实验室", "query", ["查询并在列表中分页展示所有符合条件的数据记录"], "20.4.1.1实验室列表与查询",
               note=N(role=["系统管理人员", "公众客户"])),
        ],
    )
    m.add_entity(
        id="E-BZ", name="标准库", desc="标准集合基础数据，为项目与子领域测试项提供配置来源",
        type="managed", tags=[],
        attributes=[
            attr("标准库编号", desc="文本输入框，必填（20.4.2.2）"),
            attr("标准库名称", desc="文本输入框，必填（20.4.2.2）"),
            attr("描述", desc="文本输入框，选填（20.4.2.2）"),
        ],
        state_dimensions=[
            {"dimension_name": "标准库状态", "states": ["启用", "停用"],
             "initial": "启用", "terminal": [], "inferred": [],
             "note": {"comment": "20.4.2.1列表'状态（启用/停用）'；新增表单状态单选含停用（20.4.2.2），创建转换缺省取启用；停用/启用互转构成闭环，无终态；停用后项目创建等环节不可被选择（b04）"}},
        ],
        operations=[
            op("新增标准库", "crud", ["点击提交表单，创建标准库"], "20.4.2.2新增标准库",
               note=N(role=["系统管理人员"], comment="转换落点t58")),
            op("修改标准库", "crud", ["点击提交表单保存修改"], "20.4.2.3修改标准库",
               note=N(role=["系统管理人员"], comment="编辑表单含状态单选，可联动停用/启用")),
            op("删除标准库", "crud", ["点击确定，进行删除操作"], "20.4.2.4删除标准库",
               note=N(role=["系统管理人员"], comment="二次确认框：'确认删除标准库『XXX』？'")),
            op("停用标准库", "crud", ["确认后状态立即改变，列表刷新"], "20.4.2.5停用/启用标准库",
               note=N(role=["系统管理人员"], comment="转换落点t59")),
            op("启用标准库", "crud", ["确认后状态立即改变，列表刷新"], "20.4.2.5停用/启用标准库",
               note=N(role=["系统管理人员"], comment="转换落点t60")),
            op("管理测试项", "ui", ["点击后，页面跳转或打开一个新标签页，进入该标准库的专属测试项管理界面"], "20.4.2.6进入测试项管理界面",
               note=N(role=["系统管理人员"], comment="category③ui")),
            op("查询标准库", "query", ["查询并在列表中分页展示所有符合条件的数据记录"], "20.4.2.1标准库列表与查询",
               note=N(role=["系统管理人员"])),
            op("新增测试项", "crud", ["点击提交表单，新增测试项"], "20.4.2.8新增测试项",
               note=N(role=["系统管理人员"], comment="测试项下可以有子测试项；此处只能新增一级测试项目（b16同口径约束见20.7.1.1）")),
            op("修改测试项", "crud", ["点击提交表单，系统校验后保存，刷新列表中的数据信息"], "20.4.2.9修改测试项",
               note=N(role=["系统管理人员"])),
            op("删除测试项", "crud", ["点击【确定】按钮进行删除操作，含有子项的记录不允许删除"], "20.4.2.10删除测试项",
               note=N(role=["系统管理人员"], comment="删除禁令见b05；无状态落点，不入转换")),
        ],
    )
    m.add_entity(
        id="E-ZLY", name="子领域", desc="子领域基础数据及其测试项选择管理（由表单方式变更为选择方式，数据来源于标准库）",
        type="managed", tags=[],
        attributes=[],
        state_dimensions=[],
        operations=[
            op("管理测试项", "ui", ["点击后，页面跳转或打开一个新标签页，进入该子领域的专属测试项管理界面"], "20.4.3.1进入测试项管理界面",
               note=N(role=["系统管理人员"], comment="category③ui")),
            op("新增测试项", "crud", ["点击提交表单，系统校验后保存，新标准库出现在列表中"], "20.4.3.3新增测试项",
               note=N(role=["系统管理人员"], comment="标准库下拉必填，变更后数据树会做数据更新；测试项为树形数据必填")),
            op("删除测试项", "crud", ["点击【确定】按钮，删除数据。数据删除前会做前置判断，存在子项的数据不可以删除"], "20.4.3.4删除测试项",
               note=N(role=["系统管理人员"], comment="删除禁令见b06")),
            op("查询测试项", "query", ["查询并在列表中分页展示所有符合条件的数据记录"], "20.4.3.2测试项列表与结构展示",
               note=N(role=["系统管理人员"], comment="展开的树形表格展示")),
        ],
    )
    m.add_entity(
        id="E-CYX", name="常用测试项", desc="用户另存保存的常用测试项/评价细则组合，降低项目录入难度",
        type="managed", tags=[],
        attributes=[
            attr("名称", desc="常用项名称，文件输入框必填（20.5.1.7）"),
        ],
        state_dimensions=[],
        operations=[
            op("另存常用", "crud", ["点击保存常用项数据"], "20.5.1.7增加常用子领域测试项编辑能力",
               note=N(role=["项目管理员", "评价组长"], comment="检测项目录入区域'新增'按钮后增加'另存常用'按钮；20.7.1.1评价完善页同机制保存测试项/评价细则组合")),
            op("删除常用项", "crud", ["选择常用项下列表中的项目后的'删除'图标可以删除此常用项"], "20.5.1.7增加常用子领域测试项编辑能力",
               note=N(role=["项目管理员", "评价组长"])),
        ],
    )
    m.add_entity(
        id="E-TZGG", name="通知公告", desc="平台信息发布内容，超级管理员维护，首页区分新旧显示",
        type="managed", tags=[],
        attributes=[
            attr("标题", desc="通知标题（推断）"),
            attr("内容", desc="通知内容（推断）"),
            attr("发布时间", desc="15天内发布的通知标注new标识的计时基准（20.2.1）"),
        ],
        state_dimensions=[],
        operations=[
            op("维护通知公告", "crud", ["对信息发布的内容进行维护，包括通知信息"], "3.2功能要求",
               note=N(role=["超级管理员"], comment="超级管理员对平台资源进行日常维护")),
        ],
    )
    m.add_entity(
        id="E-JL", name="信息发送记录", desc="系统信息发送历史记录，仅系统管理员和项目管理员可查看",
        type="managed", tags=[],
        attributes=[
            attr("接收号码", desc="文本输入框，模糊匹配（20.4.4.1）"),
            attr("发送方式", desc="下拉选项：短信，邮件，站内信（20.4.4.1）"),
            attr("发送时间", desc="时间范围选择框，精确匹配（20.4.4.1）"),
            attr("发送人", desc="发送记录内容（20.4.4）"),
            attr("发送结果", desc="发送记录内容（20.4.4）"),
            attr("消息标题", desc="列表展示字段（20.4.4.1）"),
            attr("消息内容", desc="列表展示字段（20.4.4.1）"),
        ],
        state_dimensions=[],
        operations=[
            op("查询发送记录", "query", ["点击查询数据"], "20.4.4.1信息发送记录",
               note=N(role=["系统管理人员", "项目管理员"], comment="只有系统管理员和项目管理员可以查看（b07）")),
            op("查看消息详情", "query", ["点击可查看消息详细内容"], "20.4.4.1信息发送记录",
               note=N(role=["系统管理人员", "项目管理员"])),
        ],
    )
    # 1.5 结构关系（四元判定自报；父→子视角；management_dimension复核注于comment）
    m.add_structural(frm="E-XM", to="E-BMJL", relation_type="composition", cardinality="1:N",
                     ownership_dimension="business_ownership",
                     desc="项目为报名记录的业务归属容器：项目发布后参加者报名生成报名记录，每条报名记录隶属于一个项目",
                     confidence="high",
                     note={"comment": "判定(c)：报名记录有独立创建流程（报名/受理用户测量审核报名），为core流程实体且dependent成立（缴费通知单/缴费单随记录建立，见19.3列结构与20.10缴费信息）；management_dimension复核：报名记录由项目管理员维护跟踪（10项目管理员'对用户报名记录状态、用户缴费情况等进行的维护与跟踪'）；§5修复C08：组合判定维持（修法a）——E-BMJL创建转换t03已携指向父实体E-XM的state_ref前置（E-XM.项目状态=报名中，端点由E-PJ同步更正见t03 note），E-LAB.启用为第三方参与资格门禁，仅约束哪些实验室可报名，不影响项目对报名记录的业务归属"})
    m.add_structural(frm="E-BMJL", to="E-JFTZ", relation_type="composition", cardinality="1:1",
                     ownership_dimension="business_ownership",
                     desc="报名记录创建后系统自动初始化缴费通知单，每条报名记录必有缴费通知单",
                     confidence="high",
                     note={"comment": "判定(b)：缴费通知单无独立创建，随报名记录自动入initial（未发送）；判(b)且1:1，复核'每条A必有B'成立；management_dimension：缴费通知单发送状态由系统维护"})
    m.add_structural(frm="E-BMJL", to="E-FY", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="缴费单记录参加者的付款，支持多次付款，可能永不创建",
                     confidence="medium",
                     note={"comment": "判定(d)：缴费单有独立创建前提（缴费动作）且可能永不创建，不满足(c)（managed非core）；management_dimension：付款/退款由参加者录入、财务人员退款维护"})
    m.add_structural(frm="E-XM", to="E-YP", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="样品随项目实施制备/领用并发放至参加实验室，业务上隶属项目批次",
                     confidence="medium",
                     note={"comment": "判定(d)：样品有独立创建流程（样品制备/样品领用登记），因E-YP的dependent未获文档直写按三步判定②降(d)＋medium；management_dimension：样品由样品制备人员/样品管理员管理（11/12）"})
    m.add_structural(frm="E-XM", to="E-PJ", relation_type="reference", cardinality="1:1",
                     ownership_dimension="configuration_source",
                     desc="新建项目时选择评价人员生成评价，评价隶属项目，多轮评价经历史结果承载",
                     confidence="medium",
                     note={"comment": "判定(d)：评价有独立创建流程（选择评价人员），因E-PJ的dependent未获文档直写按三步判定②降(d)＋medium；management_dimension：评价由评价组长确认维护（20.7.1.3）"})
    m.add_structural(frm="E-BZ", to="E-XM", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="标准库为项目检测项目录入提供测试项选择来源，项目独立创建",
                     confidence="high",
                     note={"comment": "判定(a)：标准库为项目提供配置/模板（测试项），项目独立创建；management_dimension：标准库由系统管理人员维护（20.4.2）"})
    m.add_structural(frm="E-BZ", to="E-ZLY", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="子领域测试项管理由表单方式变更为选择方式，选择数据来源于标准库",
                     confidence="high",
                     note={"comment": "判定(a)：标准库为子领域提供测试项配置来源，子领域独立存在；management_dimension：子领域测试项由系统管理人员维护（20.4.3）"})
    m.add_structural(frm="E-LAB", to="E-BMJL", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="实验室（机构）为报名的发起主体，每条报名记录关联一个实验室",
                     confidence="high",
                     note={"comment": "判定(d)：实验室仅为报名记录的发起人/持有人，按'A仅为B发起人降(d)'；management_dimension：实验室信息由公众客户维护、系统管理人员审核"})
    m.add_structural(frm="E-YP", to="E-BMJL", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="样品经核查后发放至报名记录对应的参加实验室（待发样→待收样）",
                     confidence="medium",
                     note={"comment": "判定(d)：样品与报名记录为发放关联，报名记录独立创建且可能不涉及样品（无需还样）；management_dimension：发样由项目管理员执行、接收由参加者确认"})
    # ===== Step 2：分支（准入判据＝可锚定转换；各value台账锚点已自查：均指向台账既有事件落点）=====
    m.add_branch_dimension(dimension="项目类型", entity="E-XM", values=["能力验证", "测量审核"],
                           impact_scope="E-XM.项目状态、E-BMJL.报名记录状态、E-XM.通知状态、E-YP.样品状态路径分立",
                           evidence="③；隐式分支：19.1能力验证与19.3测量审核平行流程表格列体现，20.8.3.1项目类型下拉选项'能力验证、测量审核'命名",
                           branches=[
                               {"value": "能力验证", "target_transition": "设计方案编制创建转换（E-XM.项目状态 初始→待开始）"},
                               {"value": "测量审核", "target_transition": "受理用户测量审核报名创建转换（E-XM.项目状态 初始→报名中）"},
                           ])
    m.add_branch_dimension(dimension="报名审核结果", entity="E-BMJL", values=["通过", "退回修改"],
                           impact_scope="E-BMJL.报名记录状态报名审核落点分立（报名成功/报名退回）",
                           evidence="②；运行时选择型：20.5.3.2报名审核短信节点'通过/退回修改'命名",
                           branches=[
                               {"value": "通过", "target_transition": "报名审核转换（报名待审核→报名成功）"},
                               {"value": "退回修改", "target_transition": "报名审核退回转换（报名待审核→报名退回）"},
                           ])
    m.add_branch_dimension(dimension="测试结果审核", entity="E-BMJL", values=["通过", "退回"],
                           impact_scope="E-BMJL.报名记录状态结果报告回收落点分立（自环/结果退回修改）",
                           evidence="②；运行时选择型：20.5.3.2测试结果审核节点'通过/退回'命名",
                           branches=[
                               {"value": "通过", "target_transition": "结果报告回收转换（结果已提交自环）"},
                               {"value": "退回", "target_transition": "结果报告回收退回转换（结果已提交→结果退回修改）"},
                           ])
    m.add_branch_dimension(dimension="还样情况", entity="E-YP", values=["已还样", "无需还样"],
                           impact_scope="E-YP.样品状态参加者测试落点分立（已还样/已核查自环）",
                           evidence="③；隐式分支：19.1参加者测试与结果提交行样品状态列斜杠'已还样、待核查/无需还样'，维度名为语义命名，分支值取表格原文",
                           branches=[
                               {"value": "已还样", "target_transition": "参加者测试与结果提交转换（已核查→已还样）"},
                               {"value": "无需还样", "target_transition": "参加者测试与结果提交自环转换（已核查→已核查）"},
                           ])
    m.add_branch_dimension(dimension="审核结果", entity="E-LAB", values=["通过", "退回修改"],
                           impact_scope="E-LAB.实验室状态审核落点分立（启用/退回修改）",
                           evidence="②；运行时选择型：20.4.1.2审核结果单选框'通过/退回修改'",
                           branches=[
                               {"value": "通过", "target_transition": "实验室审核转换（待审核→启用）"},
                               {"value": "退回修改", "target_transition": "实验室审核退回转换（待审核→退回修改）"},
                           ])
    m.add_branch_dimension(dimension="通知审核结果", entity="E-XM", values=["通过", "退回"],
                           impact_scope="E-XM.通知状态预通知审核落点分立（已审核/退回）",
                           evidence="③；隐式分支：19.3作业指导书行预通知状态列'待审核/退回/已审核'斜杠取值维度体现；§5修复C32：维度随E-XM.通知状态迁项目级",
                           branches=[
                               {"value": "通过", "target_transition": "审核预通知转换（待审核→已审核）"},
                               {"value": "退回", "target_transition": "退回预通知转换（待审核→退回）"},
                           ])
    m.add_branch_dimension(dimension="评分方式", entity="E-XM", values=["分值", "权重"],
                           impact_scope="E-PJ.评价状态评价计算结果差异（路径与落点相同，共用转换，expected_results若句式承载）",
                           evidence="①；配置型：创建时定、互斥、影响后续计算，20.7.1.2项目信息含评分方式字段，20.7.1'支持分值和权重两种评价方式'",
                           branches=[
                               {"value": "分值", "target_transition": "评价人员评价转换（待评价→评价中，共用）"},
                               {"value": "权重", "target_transition": "评价人员评价转换（待评价→评价中，共用）"},
                           ])
    m.add_branch_dimension(dimension="审核结果", entity="E-TASK", values=["同意", "退回"],
                           impact_scope="E-TASK.任务状态批量审核落点分立（审批通过/审批退回）",
                           evidence="②；运行时选择型：20.9.1.4审核结果下拉'同意、退回'",
                           branches=[
                               {"value": "同意", "target_transition": "批量审核转换（待审批→审批通过）"},
                               {"value": "退回", "target_transition": "批量审核退回转换（待审批→审批退回）"},
                           ])
    # ===== Step 3：转换与因果 =====
    # 3.1 转换（台账每条事件落一条转换；direction/priority判定自报于note）
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[],
        expected_results=["项目创建，项目状态为待开始（推断）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1方案设计阶段",
        note={"branch_dimension": "项目类型", "comment": "源自e01；⓪创建转换；能力验证分支（与t40受理用户测量审核报名创建分立），Step2 value=能力验证→本条；示例e01对齐"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
        ],
        expected_results=["项目状态变为报名中", "发布能力验证计划通知或邀请函"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自e02；③；项目进入报名中联动开启报名记录创建（XC x01）"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t03", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["报名记录创建，状态为报名待审核", "生成报名表"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自e03；⓪创建转换；跨主体门禁落state_ref（项目报名中为流程表驻留值门禁；实验室启用门禁依据20.3.1'需经管理用户审核通过后方可用于项目报名'，镜像XC由框架补）；能力验证分支（与t41分立），Step2 value=能力验证→本条；§5修复C03/C08：门禁端点由E-PJ更正为E-XM（项目状态维度建模于E-XM，E-PJ仅建模评价状态），同步更正e03/e08/e09台账简写；本条为E-BMJL创建转换，现携指向父实体E-XM的state_ref前置，C08组合判定维持（E-LAB.启用为第三方业务门禁，不影响业务归属组合判定）"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t04", entity="E-BMJL", dimension="费用状态",
        frm=None, to="待缴费", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["费用状态初始化为待缴费"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自e04；⓪创建转换；e03同动作拆行（一动作多状态面），能力验证分支"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t05", entity="E-BMJL", dimension="发票状态",
        frm=None, to="待开票", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["发票状态初始化为待开票"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自e05；⓪创建转换；e03同动作拆行（一动作多状态面），能力验证分支"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t06", entity="E-JFTZ", dimension="缴费通知单状态",
        frm=None, to="未发送", action="报名", role="system",
        preconditions=[],
        expected_results=["缴费通知单自动初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自e06；⓪创建转换；报名记录创建后系统自动初始化缴费通知单为未发送（联动，见因果E-BMJL→E-JFTZ），role=system；台账行actor为报名动作主体；两流程共用"},
    )
    m.add_trans(
        tid="t07", entity="E-XM", dimension="通知状态",
        frm=None, to="未发送", action="能力验证计划发布", role="项目管理员",
        preconditions=[],
        expected_results=["通知状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自e07；⓪创建转换；与t02同动作拆行（一动作多状态面）；测量审核共用（19.3发票开具行预通知状态列'未发送'为驻留值）；维度名19.3枚举称'通知状态'、流程表列称'预通知状态'，两口径并列；§5修复C32：本条原为E-BMJL创建（action=报名，行4），19.1预通知状态列首现于'能力验证计划发布'行（行3，值未发送）早于报名记录创建，出生点被后移，故维度迁E-XM项目级、动作改锚首现动作'能力验证计划发布'，E-BMJL不再承载初始化（e07/t07同步改写）"},
    )
    m.add_trans(
        tid="t08", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="报名审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名成功", "短信通知：您xxx项目的报名信息审核通过，请知悉"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；20.5.3.2操作节点增加用户短信通知",
        note={"branch_dimension": "报名审核结果", "comment": "源自e08；③；路径分歧：通过分支，Step2 value=通过→本条；两流程共用；缴费通知单联动发送见t10"},
    )
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="报名审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名退回", "短信通知：您xxx项目的报名信息审核未通过，请知悉"],
        traits=["branch", "audit", "rollback"], direction="forward", priority="P1",
        source_ref="19.1实施阶段；20.5.3.2操作节点增加用户短信通知",
        note={"branch_dimension": "报名审核结果", "comment": "源自e09；③；路径分歧：退回修改分支，Step2 value=退回修改→本条；两流程共用；退回后重新提交见t30"},
    )
    m.add_trans(
        tid="t10", entity="E-JFTZ", dimension="缴费通知单状态",
        frm="未发送", to="已发送", action="发送缴费通知", role="system",
        preconditions=[
            precond(text="缴费通知单处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-JFTZ", "缴费通知单状态", "未发送")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["缴费通知单变为已发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；10项目管理员",
        note={"comment": "源自e10；③；跨主体门禁落state_ref（门禁值取同动作拆行事件e08对应分支consequence'报名成功'）；报名审核通过后系统自动发送缴费通知单（role=system）；动作短语取10项目管理员职责'发送缴费通知'；两流程共用（19.3报名审核行同落点）"},
    )
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "待缴费")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["费用状态变为已缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "源自e11；③；同实体跨维度门禁（报名记录状态=报名成功）落state_ref；支持多次付款（20.5.2.1），已缴费后重复付款不改变状态；'审核通过后方可缴费'门禁已表达，不写因果；两流程共用"},
    )
    m.add_trans(
        tid="t12", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="样品制备", role="样品制备人员",
        preconditions=[],
        expected_results=["样品制备完成，样品状态为待核查（推断）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；11样品制备人员",
        note={"branch_dimension": "项目类型", "inferred": True, "comment": "源自e12；⓪创建转换；样品状态'待核查'首现于19.1缴费行，结合11样品制备人员职责'编制样品制备方案，执行样品制备'补创建事件；能力验证分支（与t45样品领用登记分立）"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务管理人员",
        preconditions=[
            precond(text="发票处于待开票状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "发票状态", "待开票")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["发票状态变为已开票", "生成发票"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "源自e13；③；同行费用状态列原文'已缴费/未缴费'为或值驻留，不构成门禁；20.10.2.2发票上传支持多次分批上传（op发票上传关联本条）；两流程共用"},
    )
    m.add_trans(
        tid="t14", entity="E-XM", dimension="通知状态",
        frm="未发送", to="待确认", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "未发送")),
        ],
        expected_results=["预通知发送，通知状态变为待确认", "生成预通知、用户信息表"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自e14；③；能力验证分支（与t50已审核→待确认分立，同action不同frm），Step2 value=能力验证→本条；歧义：原文'已发送/待确认'，19.3枚举值'待确认'，两口径并列取枚举值；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["报名记录状态变为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "源自e15；③；两流程共用（19.1/19.3能力验证预通知行同落点）"},
    )
    m.add_trans(
        tid="t16", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目状态变为进行中（推断）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"branch_dimension": "项目类型", "inferred": True, "comment": "源自e16；③；19.3枚举含'进行中'，19.1实施阶段自预通知起进入参加者测试，项目状态列此后未再标注，据阶段语义补链；能力验证分支（与t65待开始→进行中分立）"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t17", entity="E-YP", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品制备人员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["样品状态变为已核查", "生成核查记录表"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "源自e17；③；跨主体门禁落state_ref（流程表样品核查行报名记录状态列'结果待提交'驻留值门禁）；留痕要求：核查记录表；两流程共用"},
    )
    m.add_trans(
        tid="t18", entity="E-BMJL", dimension="报名记录样品状态",
        frm=None, to="待发样", action="样品核查", role="样品制备人员",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录样品状态初始化为待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "源自e18；⓪创建转换；本维度创建转换即样品核查行'已核查、待发样'顿号快照的第二落点（逐值登记）；维度初值=待发样；两流程共用"},
    )
    m.add_trans(
        tid="t19", entity="E-XM", dimension="通知状态",
        frm="待确认", to="已确认", action="接收能力验证计划并确认", role="能力验证参加者",
        preconditions=[
            precond(text="通知处于待确认状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "待确认")),
        ],
        expected_results=["通知状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.4能力验证参加者工作流程分析",
        note={"comment": "源自e19；③；落点值取19.1/19.3样品发放行预通知状态列'已确认'，动作短语取19.4参加者流程；两流程共用；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
    )
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待发样", to="待收样", action="样品发放,作业指导书发送", role="项目管理员",
        preconditions=[
            precond(text="报名记录样品处于待发样状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待发样")),
            precond(text="通知处于已确认状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "已确认")),
        ],
        expected_results=["样品发出，报名记录样品状态变为待收样", "记录快递单号或者软件访问路径", "短信通知：您xxxx项目的样品已发出，请知悉"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析；20.5.3.2操作节点增加用户短信通知",
        note={"comment": "源自e20；③；跨维度门禁：19.1样品发放行预通知状态列'已确认'（通知状态）落state_ref；歧义：原文列值'已发样'与枚举值'待收样'同节点两口径并列取枚举；两流程共用"},
    )
    m.add_trans(
        tid="t21", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变为结果已提交", "提交测试结果、报名表盖章版"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.3项目状态分析",
        note={"comment": "源自e21；③；测量审核行action为'参加者测试与结果提交，返样'，同节点并列口径；样品侧落点分立见t22/t23/t24"},
    )
    m.add_trans(
        tid="t22", entity="E-YP", dimension="样品状态",
        frm="已核查", to="已还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
            precond(text="还样情况=已还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["样品归还后状态变为已还样，待复核"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "还样情况", "comment": "源自e22；序判④，语义forward（还样复核循环），语义优先；路径分歧：已还样分支，Step2 value=已还样→本条；19.1表格'已还样、待核查'快照限定词'已还样'立为独立状态（与首次待核查区分），复核落点见t28；还样情况维度名为语义命名，分支值取表格原文；19.4'归还样品：参加者归还样品'"},
    )
    m.add_trans(
        tid="t23", entity="E-YP", dimension="样品状态",
        frm="已核查", to="已核查", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
            precond(text="还样情况=无需还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["无需还样，样品状态保持已核查"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "还样情况", "inferred": True, "comment": "源自e23；⑤自环forward＋inferred；路径分歧：无需还样分支，Step2 value=无需还样→本条"},
    )
    m.add_trans(
        tid="t24", entity="E-YP", dimension="样品状态",
        frm="已核查", to="已还样", action="参加者测试与结果提交，返样", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
        ],
        expected_results=["返样后样品状态变为已还样，待复核"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e24；序判④，语义forward（返样复核循环），语义优先；测量审核分支（与t22能力验证已还样分支同落点）；19.3返样行'待核查'按'已还样'立态（返样待复核，与首次待核查区分），复核落点t28"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t25", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果已提交", action="结果报告回收", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="测试结果审核=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["测试报告审核通过，结果保持已提交"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.3项目状态分析",
        note={"branch_dimension": "测试结果审核", "inferred": True, "comment": "源自e25；⑤自环forward＋inferred；路径分歧：通过分支，Step2 value=通过→本条；原文'结果已提交/结果退回修改'斜杠或值逐值拆行；两流程共用"},
    )
    m.add_trans(
        tid="t26", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果报告回收", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="测试结果审核=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["测试报告审核未通过，结果退回修改", "短信通知：您xxxx项目测试报告审核未通过，请知悉"],
        traits=["branch", "rollback"], direction="forward", priority="P1",
        source_ref="19.1报告编制和结果通知；19.3项目状态分析；20.5.3.2操作节点增加用户短信通知",
        note={"branch_dimension": "测试结果审核", "comment": "源自e26；③；路径分歧：退回分支，Step2 value=退回→本条；退回后重新提交见t27；两流程共用"},
    )
    m.add_trans(
        tid="t27", entity="E-BMJL", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交", action="重新提交结果", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果退回修改")),
        ],
        expected_results=["重新提交后结果已提交（推断）"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"inferred": True, "comment": "源自e27；序判④，语义forward（退回修改后重新提交），语义优先；据20.5.3.2测试结果审核通过/退回循环及'结果已提交/结果退回修改'并列口径补链"},
    )
    m.add_trans(
        tid="t28", entity="E-YP", dimension="样品状态",
        frm="已还样", to="已核查", action="结果报告回收", role="项目管理员",
        preconditions=[
            precond(text="样品处于已还样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已还样")),
        ],
        expected_results=["回收复核后样品状态变为已核查"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"comment": "源自e28；③；测量审核结果报告回收行样品状态列'已核查'（已还样复核）；能力验证同行列空缺，按平行流程共用"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t29", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="已撤销", action="撤销报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变为已撤销（推断）"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"inferred": True, "comment": "源自e29；③；报名行'报名待审核/已撤销'斜杠分支值'已撤销'，原文无显式动作短语，按语义补最小链"},
    )
    m.add_trans(
        tid="t30", entity="E-BMJL", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="重新提交报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名退回")),
        ],
        expected_results=["重新提交后回到报名待审核（推断）"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"inferred": True, "comment": "源自e30；序判④，语义forward（退回修改后重新提交进入审核），语义优先；报名退回无出边，按图完整性补链"},
    )
    m.add_trans(
        tid="t31", entity="E-PJ", dimension="评价状态",
        frm=None, to="待评价", action="选择评价人员", role="项目管理员",
        preconditions=[],
        expected_results=["评价任务初始化为待评价（推断）"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"inferred": True, "comment": "源自e31；⓪创建转换；'新建项目时项目管理员可以选择评价人员'，评价任务随评价人员选择初始化为待评价；联动XC x02（E-XM待开始→E-PJ待评价）"},
    )
    m.add_trans(
        tid="t32", entity="E-PJ", dimension="评价状态",
        frm="待评价", to="评价中", action="评价人员评价", role="评价人员",
        preconditions=[
            precond(text="评价处于待评价状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "待评价")),
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价组长已完善测试项目及评价细则", ptype="event_ref"),
        ],
        expected_results=["评价状态变为评价中", "若评分方式=分值，则按累加计算得分", "若评分方式=权重，则按加权计算得分"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价；20.7.1项目列表",
        note={"branch_dimension": "评分方式", "comment": "源自e32；③；跨主体门禁落state_ref；结果差异型：评分方式分值/权重路径与落点相同共用本条，expected_results逐值若句式；event_ref为一次性完成信号（完善评价细则）"},
    )
    m.add_trans(
        tid="t33", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价中", action="提交评价结果", role="评价人员",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["点击提交结果，评价分数记录到系统"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"inferred": True, "comment": "源自e33；⑤自环forward＋inferred；确定按钮提交本人评价结果，状态停留评价中；评价人员只能对自己的评价结果进行修改（b16）"},
    )
    m.add_trans(
        tid="t34", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="已关闭", action="确认评价结果", role="评价组长",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["点击后将当前结果正式提交为项目的最终评价结果，项目评价状态关闭"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自e34；③；落点'已关闭'据'项目评价状态关闭'语义命名（维度inferred成对标注）；关键操作留痕（b27）"},
    )
    m.add_trans(
        tid="t35", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价中", action="退回修改", role="评价组长",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["点击后将当前评价结果保存为历史结果，并开启下一轮评价"],
        traits=["rollback"], direction="forward", priority="P1",
        source_ref="20.7.1.3评价确认",
        note={"inferred": True, "comment": "源自e35；⑤自环forward＋inferred；开启下一轮评价，状态停留评价中"},
    )
    m.add_trans(
        tid="t36", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报告、结果通知编制，报名记录状态变为报告/证书审核中"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"branch_dimension": "项目类型", "comment": "源自e36；③；能力验证分支（与t66编制结果通知单分立），Step2 value=能力验证→本条"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t37", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
        ],
        expected_results=["项目状态变为报告审核中（推断）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.3项目状态分析",
        note={"branch_dimension": "项目类型", "inferred": True, "comment": "源自e37；③；19.3枚举含'报告审核中'，与报告编制审核阶段（技术主管审核、授权签字人批准）对应，据枚举与阶段语义补链；能力验证分支（与t67分立）"},
        branch_values=["能力验证"],
    )
    m.add_trans(
        tid="t38", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="审核任务处于审批通过状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务状态", "审批通过")),
        ],
        expected_results=["报名记录状态变为报告/证书已发布", "发放结果报告和证书", "短信通知：您xxx项目的结果通知单已发布，请知悉"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.3项目状态分析；20.5.3.2操作节点增加用户短信通知",
        note={"comment": "源自e38；③；跨主体门禁落state_ref（技术主管审核与授权签字人/实验室负责人批准任务完成，19.1'技术主管审核，授权签字人批准…项目管理员发放结果通知单和证书'）；两流程共用"},
    )
    m.add_trans(
        tid="t39", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
        ],
        expected_results=["项目状态变为已结束（推断）"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.3项目状态分析",
        note={"inferred": True, "comment": "源自e39；③；19.3枚举'已结束'与流程终点对应，20.5.1.1已结束项目可文件整理，据枚举与阶段语义补链；两流程共用"},
    )
    m.add_trans(
        tid="t40", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["测量审核项目创建，项目状态为报名中"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e40；⓪创建转换；测量审核分支（先受理报名后立项，与t01分立），Step2 value=测量审核→本条"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t41", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["报名记录创建，状态为报名待审核", "生成报名表"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e41；⓪创建转换；跨主体门禁落state_ref；测量审核分支（与t03报名分立），Step2 value=测量审核→本条；§5修复C08同族自报：本条不携E-XM state_ref前置系诚实建模——测量审核流程中受理报名为首个动作，E-XM.项目状态'报名中'由同动作t40（E-XM 初始→报名中）建立，动作前项目尚不存在（19.3枚举无'初始'值），加门禁将时序倒置；父实体绑定由t40/t41同动作共创建承载，与t03前置门禁同为组合归属表达"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t42", entity="E-BMJL", dimension="费用状态",
        frm=None, to="待缴费", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[],
        expected_results=["费用状态初始化为待缴费"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e42；⓪创建转换；e41同动作拆行（一动作多状态面），测量审核分支"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t43", entity="E-BMJL", dimension="发票状态",
        frm=None, to="待开票", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[],
        expected_results=["发票状态初始化为待开票"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e43；⓪创建转换；e41同动作拆行（一动作多状态面），测量审核分支"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t44", entity="E-XM", dimension="项目状态",
        frm="报名中", to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目状态变为待开始"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e44；序判④，语义forward（测量审核先受理报名后方案设计立项），语义优先；测量审核分支"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t45", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="样品领用登记", role="样品管理员",
        preconditions=[],
        expected_results=["样品领用出库登记，样品状态为待核查"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e45；⓪创建转换；测量审核分支（库存领用，与t12样品制备分立）；12样品管理员'样品出入库登记和管理'"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t46", entity="E-XM", dimension="通知状态",
        frm="未发送", to="待审核", action="作业指导书编制", role="策划人员",
        preconditions=[
            precond(text="通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "未发送")),
        ],
        expected_results=["作业指导书/预通知编制完成，提交审核，通知状态变为待审核（推断）", "生成作业指导书"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "inferred": True, "comment": "源自e46；③；通知状态'待审核'首现于19.3样品领用登记行，编制动作取同行组'作业指导书编制'，据列值与动作补链；测量审核分支（预通知含审核环节）；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t47", entity="E-XM", dimension="通知状态",
        frm="待审核", to="已审核", action="审核预通知", role="技术主管",
        preconditions=[
            precond(text="通知处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "待审核")),
            precond(text="通知审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["预通知审核通过，通知状态变为已审核（推断）"],
        traits=["branch", "audit"], direction="forward", priority="P1",
        source_ref="19.3项目状态分析；7技术主管",
        note={"branch_dimension": "通知审核结果", "inferred": True, "comment": "源自e47；③；19.3作业指导书行'待审核/退回/已审核'斜杠分支值拆行；动作据7技术主管职责'审核能力验证计划邀请函或通知'命名；Step2 value=通过→本条；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t48", entity="E-XM", dimension="通知状态",
        frm="待审核", to="退回", action="退回预通知", role="技术主管",
        preconditions=[
            precond(text="通知处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "待审核")),
            precond(text="通知审核结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["预通知审核退回，通知状态变为退回（推断）"],
        traits=["branch", "rollback"], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "通知审核结果", "inferred": True, "comment": "源自e48；③；分支值'退回'取19.3通知状态列原文；Step2 value=退回→本条；退回后修改重提见t49；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t49", entity="E-XM", dimension="通知状态",
        frm="退回", to="待审核", action="修改预通知", role="策划人员",
        preconditions=[
            precond(text="通知处于退回状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "退回")),
        ],
        expected_results=["修改后重新提交审核（推断）"],
        traits=["rollback"], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"inferred": True, "comment": "源自e49；序判④，语义forward（退回后修改重提进入审核循环），语义优先；审核循环闭合补链；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t50", entity="E-XM", dimension="通知状态",
        frm="已审核", to="待确认", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="通知处于已审核状态", ptype="state_ref",
                    ref=state_ref("E-XM", "通知状态", "已审核")),
        ],
        expected_results=["预通知发送，通知状态变为待确认"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e50；序判④，语义forward（审核通过后发送预通知），语义优先；测量审核分支（与t14未发送→待确认分立，同action不同frm）；§5修复C32：随维度迁E-XM（项目级预通知状态面）"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t51", entity="E-LAB", dimension="实验室状态",
        frm=None, to="待审核", action="机构新增实验室信息", role="公众客户",
        preconditions=[],
        expected_results=["实验室信息提交，状态为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1实验室信息",
        note={"comment": "源自e51；⓪创建转换；动作短语保留原文主语线索'机构新增实验室信息'；审核通过后方可用于项目报名（b02/t03/t41门禁）"},
    )
    m.add_trans(
        tid="t52", entity="E-LAB", dimension="实验室状态",
        frm="启用", to="待审核", action="机构修改实验室信息", role="公众客户",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["修改提交后重新进入审核（推断）"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.3.1实验室信息；20.4.1.3实验室修改",
        note={"comment": "源自e52；序判④，语义forward（修改后重新进入审核），语义优先；'机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名'"},
    )
    m.add_trans(
        tid="t53", entity="E-LAB", dimension="实验室状态",
        frm="退回修改", to="待审核", action="机构修改实验室信息", role="公众客户",
        preconditions=[
            precond(text="实验室处于退回修改状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "退回修改")),
        ],
        expected_results=["修改重提后进入待审核（推断）"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.3.1实验室信息；20.4.1.3实验室修改",
        note={"inferred": True, "comment": "源自e53；序判④，语义forward（退回后修改重提），语义优先；审核循环闭合补链"},
    )
    m.add_trans(
        tid="t54", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态变更为'启用'", "如果审核结果为通过，为当前数据生成该数据的快照记录"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自e54；③；路径分歧：通过分支，Step2 value=通过→本条；原文'使用人员'按模块归属系统管理人员；关键操作留痕"},
    )
    m.add_trans(
        tid="t55", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="退回修改", action="实验室审核", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
            precond(text="审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态变更为'退回修改'，必须填写'审核意见'"],
        traits=["branch", "audit", "rollback"], direction="forward", priority="P1",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自e55；③；路径分歧：退回修改分支，Step2 value=退回修改→本条；歧义：原文落点'已退回'与20.3.1枚举'退回修改'两口径并列取枚举；退回后修改重提见t53"},
    )
    m.add_trans(
        tid="t56", entity="E-LAB", dimension="实验室状态",
        frm="启用", to="停用", action="停用实验室", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["停用（启用状态显示）按钮，状态立即改变为停用"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自e56；②to为侧挂状态（停用）→lateral"},
    )
    m.add_trans(
        tid="t57", entity="E-LAB", dimension="实验室状态",
        frm="停用", to="启用", action="启用实验室", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "停用")),
        ],
        expected_results=["启用（停用状态显示）按钮，状态立即改变为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自e57；②frm为侧挂状态（停用）→resume"},
    )
    m.add_trans(
        tid="t58", entity="E-BZ", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理人员",
        preconditions=[],
        expected_results=["点击提交表单，创建标准库"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.2.2新增标准库",
        note={"comment": "源自e58；⓪创建转换；表单状态单选含启用/停用（必填），缺省取启用，停用创建为表单分支差异经属性承载"},
    )
    m.add_trans(
        tid="t59", entity="E-BZ", dimension="标准库状态",
        frm="启用", to="停用", action="停用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-BZ", "标准库状态", "启用")),
        ],
        expected_results=["确认后状态立即改变为停用，列表刷新"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自e59；②to为侧挂状态（停用）→lateral；停用的标准库在项目创建等环节不可被选择（b04）"},
    )
    m.add_trans(
        tid="t60", entity="E-BZ", dimension="标准库状态",
        frm="停用", to="启用", action="启用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-BZ", "标准库状态", "停用")),
        ],
        expected_results=["确认后状态立即改变为启用，列表刷新"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自e60；②frm为侧挂状态（停用）→resume"},
    )
    m.add_trans(
        tid="t61", entity="E-TASK", dimension="任务状态",
        frm=None, to="待审批", action="生成审核任务", role="system",
        preconditions=[],
        expected_results=["用户通过表单或审核一个已存在的任务，生成一个新的审核任务", "系统发送短信通知相关负责人：您有一个新的xxx审核任务，请及时处理"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.9.1.3增加任务提醒",
        note={"comment": "源自e61；⓪创建转换；系统自动生成（role=system）；流程处理人审批顺序为提交申请时签字人的选择顺序（b19）；任务创建短信提醒见b18"},
    )
    m.add_trans(
        tid="t62", entity="E-TASK", dimension="任务状态",
        frm="待审批", to="审批通过", action="批量审核", role=["技术主管", "授权签字人", "实验室负责人", "审核人员"],
        preconditions=[
            precond(text="任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务状态", "待审批")),
            precond(text="审核结果=同意", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["点击进行批量审核操作，所选任务审批通过（推断）"],
        traits=["branch", "audit", "data_constraint"], direction="forward", priority="P0",
        source_ref="20.9.1.4任务批量处理",
        note={"branch_dimension": "审核结果", "comment": "源自e62；③；路径分歧：同意分支，Step2 value=同意→本条；data_constraint：系统会根据任务节点的类型及内容判断当前节点是否可以被批量处理；多执行者写role列表（collaborative）"},
    )
    m.add_trans(
        tid="t63", entity="E-TASK", dimension="任务状态",
        frm="待审批", to="审批退回", action="批量审核", role=["技术主管", "授权签字人", "实验室负责人", "审核人员"],
        preconditions=[
            precond(text="任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务状态", "待审批")),
            precond(text="审核结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["点击进行批量审核操作，所选任务审批退回（推断）"],
        traits=["branch", "audit", "rollback", "data_constraint"], direction="forward", priority="P1",
        source_ref="20.9.1.4任务批量处理",
        note={"branch_dimension": "审核结果", "comment": "源自e63；③；路径分歧：退回分支，Step2 value=退回→本条；退回后重新提交见t64"},
    )
    m.add_trans(
        tid="t64", entity="E-TASK", dimension="任务状态",
        frm="审批退回", to="待审批", action="重新提交任务", role=["策划人员", "项目管理员"],
        preconditions=[
            precond(text="任务处于审批退回状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务状态", "审批退回")),
        ],
        expected_results=["修改后重新提交审批（推断）"],
        traits=["rollback"], direction="forward", priority="P1",
        source_ref="20.9.1.4任务批量处理",
        note={"inferred": True, "comment": "源自e64；序判④，语义forward（退回后修改重提），语义优先；审批循环闭合补链"},
    )
    m.add_trans(
        tid="t65", entity="E-XM", dimension="项目状态",
        frm="待开始", to="进行中", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
        ],
        expected_results=["项目状态变为进行中（推断）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "inferred": True, "comment": "源自e65；③；测量审核分支（实施阶段开始，与t16报名中→进行中分立，同action不同frm）；19.3枚举含'进行中'，据阶段语义补链"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t66", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果通知单", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["结果通知单编制，报名记录状态变为报告/证书审核中"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "comment": "源自e66；③；测量审核分支（与t36编制结果报告分立），Step2 value=测量审核→本条"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t67", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="编制结果通知单", role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
        ],
        expected_results=["项目状态变为报告审核中（推断）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"branch_dimension": "项目类型", "inferred": True, "comment": "源自e67；③；测量审核分支（与t37分立）；19.3枚举含'报告审核中'，据枚举与阶段语义补链"},
        branch_values=["测量审核"],
    )
    m.add_trans(
        tid="t68", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待收样", to="已收样", action="接收样品", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品处于待收样状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待收样")),
        ],
        expected_results=["参加者接收样品，状态变为已收样（推断）"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.4能力验证参加者工作流程分析",
        note={"inferred": True, "comment": "源自e68；③；19.4参加者流程'接收样品：参加者接收样品'，19.3枚举含'已收样'，补链"},
    )
    m.add_trans(
        tid="t69", entity="E-BMJL", dimension="报名记录样品状态",
        frm="已收样", to="已确认", action="确认收样", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品处于已收样状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "已收样")),
        ],
        expected_results=["收样确认后状态变为已确认（推断）"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"inferred": True, "comment": "源自e69；③；19.3枚举'已确认'为报名记录样品状态终值，与预通知确认机制对齐，收样确认补链"},
    )
    # 3.3 自检：op-转换关联（对照add_trans逐条登记，映射依据＝action语义＋frm→to方向；无对应者不调用）
    m.link_op_transition(entity="E-XM", op="设计方案编制", transitions=["t01"])
    m.link_op_transition(entity="E-BMJL", op="上传缴费证明", transitions=["t11"])
    m.link_op_transition(entity="E-BMJL", op="提交结果报告", transitions=["t21"])
    m.link_op_transition(entity="E-BMJL", op="发票上传", transitions=["t13"])
    m.link_op_transition(entity="E-FY", op="上传付款单", transitions=["t11"],
                         note=N(comment="跨实体：E-FY付款录入触发E-BMJL.费用状态缴费转换"))
    m.link_op_transition(entity="E-YP", op="样品制备", transitions=["t12"])
    m.link_op_transition(entity="E-YP", op="样品核查", transitions=["t17", "t18"],
                         note=N(comment="t18落点在E-BMJL.报名记录样品状态（跨实体点名）"))
    m.link_op_transition(entity="E-YP", op="样品领用登记", transitions=["t45"])
    m.link_op_transition(entity="E-YP", op="样品发放", transitions=["t20"],
                         note=N(comment="跨实体：转换落点在E-BMJL.报名记录样品状态"))
    m.link_op_transition(entity="E-PJ", op="评价", transitions=["t32"])
    m.link_op_transition(entity="E-PJ", op="结果确认", transitions=["t34"])
    m.link_op_transition(entity="E-TASK", op="提交审核", transitions=["t61"],
                         note=N(comment="跨实体：E-XM批量处理页面提交审核，生成E-TASK审核任务"))
    m.link_op_transition(entity="E-TASK", op="批量审核", transitions=["t62", "t63"])
    m.link_op_transition(entity="E-LAB", op="审核实验室", transitions=["t54", "t55"])
    m.link_op_transition(entity="E-LAB", op="修改实验室", transitions=["t52", "t53"])
    m.link_op_transition(entity="E-LAB", op="停用实验室", transitions=["t56"])
    m.link_op_transition(entity="E-LAB", op="启用实验室", transitions=["t57"])
    m.link_op_transition(entity="E-BZ", op="新增标准库", transitions=["t58"])
    m.link_op_transition(entity="E-BZ", op="停用标准库", transitions=["t59"])
    m.link_op_transition(entity="E-BZ", op="启用标准库", transitions=["t60"])
    # 回写（Step 3.3）：20.5/20.7/20.9/20.11 章节操作动词补入（追加去重）
    m.add_action_verbs(verbs=["归档", "另存", "签章", "填充"])
    # 3.4 因果鉴别（Q1→Q2→Q3依序；Q1命中[Y需额外操作]两处已兑现为Step4 XC x01/x02；其余门禁均由Y侧precondition表达，止于Q2不标记）
    m.add_causal(frm="E-BMJL", to="E-JFTZ",
                 desc="报名记录创建后系统自动初始化缴费通知单为未发送；报名审核通过后系统自动发送缴费通知单",
                 trigger="报名记录创建/报名审核通过后缴费通知单自动初始化与发送",
                 trigger_source="expected_results",
                 evidence_transitions=["t03", "t08", "t06", "t10"],
                 rollback_propagation=False, confidence="high",
                 note={"comment": "流程表'缴费通知单'列明写：报名行=未发送、报名审核行=已发送；门禁对照：'审核通过后方可缴费'不写因果（Y需操作且precondition已表达）"})
    # ===== Step 4：约束 =====
    # 回访①：3.4 [待写入: Step4 XC] 检索兑现——Q1命中两处（E-XM→E-BMJL报名记录创建需参加者操作、E-XM→E-PJ评价创建随项目建立）兑现为下方x01/x02
    # invalid：全文无明文禁止的状态转换（'不允许/不可以从X到Y'仅出现于删除/查看等非转换禁令），零声明
    # 镜像XC（t03/t41实验室与项目门禁、t10/t11/t13/t17/t20/t32/t38跨主体门禁）由框架从precondition自动镜像补齐，作者免写
    m.add_xc(xid="x01", source_entity="E-XM",
             source_transition="t02", source_state="报名中",
             target_entity="E-BMJL", target_dimension="报名记录状态",
             target_transition="t03", target_condition="报名待审核",
             xc_source="联动",
             desc="项目进入报名中后联动开启报名记录创建，新记录初始化为报名待审核",
             source_ref="19.1实施阶段")
    m.add_xc(xid="x02", source_entity="E-XM",
             source_transition="t01", source_state="待开始",
             target_entity="E-PJ", target_dimension="评价状态",
             target_transition="t31", target_condition="待评价",
             xc_source="联动",
             desc="新建项目时项目管理员选择评价人员，联动初始化评价任务为待评价",
             source_ref="20.7.1.2协同评价")
    # BR（仅规范性约束句生成；一句一BR；restrictive命中词注于note；enforcement免传由框架派生）
    m.add_br(bid="b01", category="display",
             desc="对新旧通知内容进行区分显示，15天内发布的通知在内容前标注'new'标识，超过15天后此标识自动隐藏",
             entities_involved=["E-TZGG"], source_ref="20.2.1通知公告", restrictive=True,
             note={"comment": "restrictive命中'15天内'/'超过15天'（量化强制）；category判显示"})
    m.add_br(bid="b02", category="validation",
             desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
             entities_involved=["E-LAB", "E-BMJL"], source_ref="20.3.1实验室信息", restrictive=True,
             constrained_entity="E-LAB",
             note={"comment": "restrictive命中'需经…审核通过后方可'（仅当类强制门禁）；跨主体门禁已落t03/t41 precondition state_ref（Q2止，不另写因果）"})
    m.add_br(bid="b03", category="validation",
             desc="【确认】按钮提交审核结果，如果审核结果为通过，为当前数据生成该数据的快照记录",
             entities_involved=["E-LAB"], source_ref="20.4.1.2实验室审核", restrictive=False,
             note={"comment": "条件性系统行为，无强制措辞；§5修复C20：desc'审核结果为通过'逐字命中分支值'通过'，挂E-LAB[审核结果]（通过/退回修改）；'提交审核结果'隐含二值判定，退回修改值由20.4.1.2审核结果单选框承载（Step2 evidence已引）"},
             branch_dimensions=["审核结果"])
    m.add_br(bid="b04", category="validation",
             desc="停用的标准库在项目创建等环节不可被选择",
             entities_involved=["E-BZ", "E-XM"], source_ref="20.4.2.5停用/启用标准库", restrictive=True,
             constrained_entity="E-BZ",
             note={"comment": "restrictive命中'不可'；category判数据校验"})
    m.add_br(bid="b05", category="validation",
             desc="点击【确定】按钮进行删除操作，含有子项的记录不允许删除",
             entities_involved=["E-BZ"], source_ref="20.4.2.10删除测试项", restrictive=True,
             constrained_entity="E-BZ",
             note={"comment": "restrictive命中'不允许'"})
    m.add_br(bid="b06", category="validation",
             desc="点击【确定】按钮删除数据，数据删除前会做前置判断，存在子项的数据不可以删除",
             entities_involved=["E-ZLY"], source_ref="20.4.3.4删除测试项", restrictive=True,
             constrained_entity="E-ZLY",
             note={"comment": "restrictive命中'不可以'"})
    m.add_br(bid="b07", category="authorization",
             desc="信息发送记录只有系统管理员和项目管理员可以查看",
             entities_involved=["E-JL"], source_ref="20.4.4.1信息发送记录", restrictive=True,
             note={"role": ["系统管理人员", "项目管理员"], "comment": "restrictive命中'只有'；category判授权"})
    m.add_br(bid="b08", category="validation",
             desc="能力验证消息发送页面接收人1和接收人2不能同时为空",
             entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能", restrictive=True,
             constrained_entity="E-XM",
             note={"comment": "restrictive命中'不能'；§5修复C20：desc'能力验证'逐字命中E-XM[项目类型]分支值，本条承载能力验证值（与b10测量审核值分值承载，两值差异见desc/来源章节差异）"},
             branch_dimensions=["项目类型"])
    m.add_br(bid="b09", category="validation",
             desc="未结束的项目可以进行消息发送",
             entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能", restrictive=False,
             constrained_entity="E-XM",
             note={"comment": "条件限定（未结束项目方可发送），无强制措辞原词命中，restrictive缺省False"})
    m.add_br(bid="b10", category="validation",
             desc="测量审核消息发送页面接收人1必填",
             entities_involved=["E-XM"], source_ref="20.6.1.2优化消息发送功能", restrictive=True,
             constrained_entity="E-XM",
             note={"comment": "restrictive命中'必填'（必须类）；与b08能力验证口径差异（接收人1单独必填 vs 接收人1/2不能同时为空）；§5修复C20：desc'测量审核'逐字命中E-XM[项目类型]分支值，本条承载测量审核值"},
             branch_dimensions=["项目类型"])
    m.add_br(bid="b11", category="usability",
             desc="在项目人员信息区域中的技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
             entities_involved=["E-XM"], source_ref="20.5.1.6默认填充技术主管、实验室负责人、授权签字人；20.6.1.4默认填充技术主管、实验室负责人、授权签字人", restrictive=False,
             note={"comment": "支持性规则（默认填充），无强制原词；category判易用性"})
    m.add_br(bid="b12", category="validation",
             desc="修改已报名项目的付款验证，可以多次进行付款操作，不对付款金额进行校验限制",
             entities_involved=["E-FY"], source_ref="20.5.2.1已报名项目增加多次付款功能；20.6.2.1已报名项目增加多次付款功能", restrictive=False,
             note={"comment": "支持性规则，明示免除金额校验；category判数据校验"})
    m.add_br(bid="b13", category="notification",
             desc="系统在每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则以邮件方式对用户进行提醒，并抄送项目管理员",
             entities_involved=["E-BMJL"], source_ref="20.5.2.3增加证书到期前30天提醒功能；20.6.2.3增加证书到期前30天提醒功能", restrictive=True,
             note={"comment": "restrictive命中'每天上午9点'/'等于30天'（量化强制触发）；category判通知；无状态落点，不入台账/operations"})
    m.add_br(bid="b14", category="notification",
             desc="管理用户对报名信息操作后使用短信方式对用户进行通知：报名审核通过/退回修改、样品已发出、测试报告审核通过/未通过、结果通知单已发布节点",
             entities_involved=["E-BMJL"], source_ref="20.5.3.2操作节点增加用户短信通知；20.6.3.2操作节点增加用户短信通知", restrictive=False,
             note={"comment": "支持性规则，无强制原词；category判通知；各节点对应t08/t09/t20/t25/t26/t38；§5修复C20×3：①desc'报名审核通过/退回修改'逐字命中[报名审核结果]值域；②desc'测试报告审核通过/未通过'钩子对应[测试结果审核]（'未通过'≈分支值'退回'，通知文案与分支值同义映射，值域锚点即t25/t26）；③[通知审核结果]（预通知审核 通过/退回，锚点t47/t48，19.3作业指导书行预通知状态列'待审核/退回/已审核'）挂本条依据——desc节点族（报名审核、测试报告审核）与预通知审核同属审核结果通知节点族，且source_ref已含测量审核侧20.6.3.2（预通知审核仅存在于测量审核流程）；§5修复C32后预通知审核状态面锚定E-XM项目级，本条作为唯一通知类BR仍为该维度承载（维度名不变，挂载有效）；b02/b03虽含审核语义但作用对象为E-LAB跨实体，故不取"},
             branch_dimensions=["报名审核结果", "测试结果审核", "通知审核结果"])
    m.add_br(bid="b15", category="computation",
             desc="评价支持分值和权重两种方式，分值按累加计算得分，权重按加权计算得分",
             entities_involved=["E-PJ"], source_ref="20.7.1项目列表", restrictive=False,
             note={"role": ["评价人员"], "comment": "支持性规则，restrictive缺省；category判计算衍生"},
             branch_dimensions=["评分方式"])
    m.add_br(bid="b16", category="authorization",
             desc="新建项目时项目管理员可以选择评价人员，评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
             entities_involved=["E-PJ"], source_ref="20.7.1.2协同评价", restrictive=True,
             constrained_entity="E-PJ",
             note={"role": ["评价人员"], "comment": "restrictive命中'只能'/'不能'；category判授权"})
    m.add_br(bid="b17", category="validation",
             desc="评价完善页面此处只能新增一级测试项目",
             entities_involved=["E-PJ"], source_ref="20.7.1.1测试项目、评价细则完善", restrictive=True,
             constrained_entity="E-PJ",
             note={"comment": "restrictive命中'只能'"})
    m.add_br(bid="b18", category="notification",
             desc="用户通过表单或审核一个已存在的任务生成一个新的审核任务时，系统发送短信通知相关负责人：您有一个新的xxx审核任务，请及时处理",
             entities_involved=["E-TASK"], source_ref="20.9.1.3增加任务提醒", restrictive=False,
             note={"comment": "支持性规则，无强制原词；category判通知；对应t61"})
    m.add_br(bid="b19", category="authorization",
             desc="重构测量审核结果通知单审批流程，将原来多个流程合并为一个流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序",
             entities_involved=["E-TASK"], source_ref="20.9.1.1测量审核结果通知单审核流程优化", restrictive=False,
             note={"comment": "支持性规则（流程设定）；category判授权；§5修复C20：E-TASK[审核结果]（批量审核分支，值域同意/退回，锚点t62/t63）挂本条依据——b19为审批流程结构性规则（流程合并+处理人审批顺序），批量审核即该审批流程的执行环节，语义最近；b18为新任务短信提醒、b20为自定义流程预设，均不承载审批结果分立；与E-LAB同名维度[审核结果]（挂b03）按实体区分，值域亦不同（同意/退回 vs 通过/退回修改）"},
             branch_dimensions=["审核结果"])
    m.add_br(bid="b20", category="restrictive",
             desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
             entities_involved=["E-TASK"], source_ref="20.9.1.6增加自定义流程", restrictive=True,
             note={"comment": "restrictive命中'4个以内'（量化）；纯限制性规则不属业务域，category=restrictive"})
    m.add_br(bid="b21", category="usability",
             desc="系统内增加电子签章位置信息，当进行签章操作时自动代入此位置信息减少手动调整操作",
             entities_involved=["E-TASK"], source_ref="20.9.1.2预置签章位置信息", restrictive=False,
             note={"comment": "支持性规则；category判易用性"})
    m.add_br(bid="b22", category="display",
             desc="优化审核流程详情的显示效果，在页面上完整展示审核流程，并用不同的颜色对各个状态的节点进行标记",
             entities_involved=["E-TASK"], source_ref="20.9.1.7优化流程信息展示效果", restrictive=False,
             note={"comment": "支持性规则；category判显示"})
    m.add_br(bid="b23", category="validation",
             desc="退款金额必填，不能为大于当前缴费金额",
             entities_involved=["E-FY"], source_ref="20.10.2.3缴费单退款", restrictive=True,
             constrained_entity="E-FY",
             note={"comment": "restrictive命中'不能'"})
    m.add_br(bid="b24", category="computation",
             desc="退款金额多次退款做累加处理，付款金额-退款金额=实际付款，退款后更新项目费用为实际付款金额",
             entities_involved=["E-FY"], source_ref="20.10.2.3缴费单退款", restrictive=False,
             note={"comment": "支持性规则；category判计算"})
    m.add_br(bid="b25", category="restrictive",
             desc="在网络和服务器正常运行的情况下，平台应支持至少300个同时在线用户数；并发100时，每个页面响应时间不超过5秒；单次报名操作成功率应达到95%以上",
             entities_involved=["E-BMJL"], source_ref="21.3性能要求", restrictive=True,
             note={"comment": "restrictive命中'至少'/'不超过'/'95%以上'（量化）；纯限制性规则，category=restrictive；平台级性能约束以报名操作为代表实体"})
    m.add_br(bid="b26", category="usability",
             desc="操作完成时有统一规范的提示信息，例如删除操作时系统可提示警示框'您确认删除记录吗？操作不可恢复！'，用户点击确认后平台才执行删除操作",
             entities_involved=["E-BZ", "E-ZLY"], source_ref="3.6可用性要求", restrictive=True,
             constrained_entity="E-BZ",
             note={"comment": "restrictive命中'不可（恢复）'与确认后方执行（仅当类）；category判易用性；E-BZ为代表实体（删除确认场景见20.4.2.4/20.4.3.4）"})
    m.add_br(bid="b27", category="validation",
             desc="对关键操作进行留痕处理，系统将自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志，确保所有操作均可追踪和复核",
             entities_involved=["E-BMJL", "E-YP", "E-PJ", "E-LAB", "E-TASK"], source_ref="20.11.1.2安全性相关内容优化；20.11其他", restrictive=False,
             constrained_entity="E-BMJL",
             note={"comment": "'不可篡改'为日志属性描述非禁止措辞，不判强制；平台级留痕机制，作用目标覆盖全部关键操作；§5修复C24：entities_involved补为audit traits覆盖实体（t08/t38→E-BMJL、t17→E-YP、t34→E-PJ、t54→E-LAB、t62→E-TASK）；全局审计规则无单一操作对象，constrained_entity取E-BMJL为代表实体（t08/t38两条审计转换落点，与b25代表实体口径一致）"})
    # —— §5修复新增（C20）：[还样情况]分支维度BR承载 ——
    # 裁决依据（二选一之「保留维度+新建BR」）：[还样情况]由t22（已核查→已还样）/t23（已核查自环）锚定，
    # 属19.1表格'参加者测试与结果提交'行样品状态列斜杠'/'体现的真实流转路径分歧（非配置项、非快照并列），
    # 降级为属性将丢失t22/t23的路径分歧语义，故保留add_branch_dimension声明、新建b28承载；
    # t22/t23的note.branch_dimension标注已存在，无需同步改动。
    m.add_br(bid="b28", category="validation",
             desc="参加者测试与结果提交节点样品流转分已还样/无需还样两种情形：已还样的样品归还后状态由已核查变为已还样（返样待复核），测量审核经结果报告回收复核转已核查；无需还样的样品不归还、状态保持已核查",
             entities_involved=["E-YP"], source_ref="19.1实施阶段；19.4能力验证参加者工作流程分析；19.3项目状态分析", restrictive=False,
             note={"inferred": True, "comment": "§5修复C20新增：综合19.1表格'参加者测试与结果提交'行样品状态列斜杠'已还样、待核查/无需还样'、19.4'归还样品：参加者归还样品'流程步骤与19.3平行行'参加者测试与结果提交，返样'→已还样（返样待复核，测量审核默认返样）合成，非原文规范性成句故inferred标注；支持性流转规则无强制措辞，restrictive缺省False；category判数据校验（流转情形判定）"},
             branch_dimensions=["还样情况"])
    # 回访②：prohibit_keywords核对——7条短语均有产物source_ref可定位（b08不能同时为空/b05不允许删除/b06不可以删除/b04不可被选择/b23不能大于当前缴费金额/b16不能查看和修改其他评价人员的评价结果/b26操作不可恢复）
    # 回访③：document_scope核对——全部产物source_ref均落在声明章节内（§3.2/§3.6/§5–§18/§19.1–§19.4/§20.2–§20.11/§21.3）
    return m
