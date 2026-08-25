"""网数中心能力验证服务平台升级维护项目 需求数据。

源文件: 网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704.md
覆盖范围: §3.2 功能要求；§5-§18 用户角色；§19 系统流程分析；§20.2-§20.11 系统功能需求；
         §21 非功能性需求中的约束性条款（仅落入 BR）。

结构概览（注释版，非正式编号）：
  主体分组（E-ID → 主体名词）：
    E-XM    = 项目（能力验证项目 / 测量审核项目，承载主流程）
    E-YP    = 样品（项目主样品，承载样品状态面）
    E-BMJL  = 报名记录（参加者报名记录，承载报名记录状态面）
    E-YTZ   = 预通知（项目预通知，承载预通知状态面）
    E-JFTZ  = 缴费通知单（承载缴费通知单状态面）
    E-FY    = 费用（承载费用状态面）
    E-FP    = 发票（承载发票状态面）
    E-BMYP  = 报名记录样品（承载报名记录样品状态面，§19.3 单列）
    E-ZYDS  = 作业指导书（测量审核特有，承载作业指导书状态面）
    E-LAB   = 实验室（承载实验室状态面）
    E-BZK   = 标准库（承载标准库状态面）
    E-CSS   = 测试项（标准库/子领域下的测试项，managed）
    E-ZLY   = 子领域（managed，与 E-BZK reference 关系）
    E-PJ    = 评价（承载评价状态面）
    E-TASK  = 审核任务（承载任务状态面）
    E-CW    = 缴费记录（承载缴费记录状态面）
    E-XX    = 信息发送记录（managed，无状态面）
    E-DAGD  = 档案归档（managed，承载文件整理操作）
    E-CJMM  = 常用测试项（managed，承载常用项配置）
    E-TJBB  = 统计报表（managed，承载各类查询/导出操作）
    E-MSG   = 消息（managed，承载消息发送操作）
    E-YJ    = 缴费信息（managed，§20.10.1 新增模块）
    E-FK    = 退款记录（managed，§20.10.2.3 新增退款记录）
    E-TZGG  = 通知公告（managed，§20.2.1）
    E-SJKB  = 数据看板（managed，§20.8.2 新增）

  状态维度（按主体事件组、按 §19.3 枚举 ∪ 台账推导）：
    E-XM/项目状态         : 待开始、报名中、进行中、报告审核中、已结束
    E-YP/样品状态         : 待核查、已核查、待发样、已发样、已还样、无需还样
    E-BMJL/报名记录状态   : 报名待审核、报名退回、报名成功、结果待提交、结果已提交、
                            结果退回修改、报告/证书审核中、报告/证书已发布、已撤销
    E-YTZ/预通知状态      : 未发送、已发送、待确认、已确认
    E-JFTZ/缴费通知单状态 : 未发送、已发送
    E-FY/费用状态         : 待缴费、已缴费
    E-FP/发票状态         : 待开票、已开票
    E-BMYP/报名记录样品状态: 待发样、待收样、已收样、已确认
    E-ZYDS/作业指导书状态  : 待审核、已审核、退回
    E-LAB/实验室状态       : 待审核、启用、停用、已退回
    E-BZK/标准库状态       : 启用、停用
    E-PJ/评价状态          : 评价中、评价关闭
    E-TASK/任务状态        : 待审核、审核通过、审核退回
    E-CW/缴费记录状态      : 待退款、已退款

  角色映射（id 直落盘，name 取原文逐字复制）：
    r01 实验室负责人 / r02 技术主管 / r03 授权签字人 / r04 策划人员 /
    r05 项目管理员 / r06 样品制备人员 / r07 样品管理员 / r08 评价人员 /
    r09 统计人员 / r10 质量专员 / r11 财务管理人员 / r12 系统管理人员 /
    r13 能力验证参加者 / r14 监督员 / r15 评价组长（inferred，§20.7 首段"第一个被选择的评价人员默认做为评价组长"）
"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704.md",
        document_scope="§3.2 功能要求；§5-§18 用户角色；§19 系统流程分析；§20.2-§20.11 系统功能需求；§21 非功能性约束",
    )

    # ============================================================
    # 事件台账（§2）—— m.add_event 调用序列，按当前文档登记
    # ============================================================
    # ---- §19.1 能力验证提供者流程 ----
    m.add_event(eid="e01", entity="E-XM", dimension="项目状态", action="设计方案编制",
                actor="策划人员", precondition="无", consequence="待开始",
                source_ref="19.1 项目准备阶段/方案设计阶段")
    m.add_event(eid="e02", entity="E-XM", dimension="项目状态", action="能力验证计划发布",
                actor="项目管理员", precondition="待开始", consequence="报名中",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e03", entity="E-YTZ", dimension="预通知状态", action="能力验证计划发布",
                actor="项目管理员", precondition="无", consequence="未发送",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e04", entity="E-BMJL", dimension="报名记录状态", action="报名",
                actor="能力验证参加者", precondition="无", consequence="报名待审核",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e05", entity="E-JFTZ", dimension="缴费通知单状态", action="报名",
                actor="能力验证参加者", precondition="无", consequence="未发送",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e06", entity="E-FY", dimension="费用状态", action="报名",
                actor="能力验证参加者", precondition="无", consequence="待缴费",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e07", entity="E-FP", dimension="发票状态", action="报名",
                actor="能力验证参加者", precondition="无", consequence="待开票",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e08", entity="E-BMJL", dimension="报名记录状态", action="报名审核",
                actor="项目管理员", precondition="报名待审核", consequence="报名退回",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e09", entity="E-BMJL", dimension="报名记录状态", action="报名审核",
                actor="项目管理员", precondition="报名待审核", consequence="报名成功",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e10", entity="E-JFTZ", dimension="缴费通知单状态", action="报名审核",
                actor="项目管理员", precondition="未发送", consequence="已发送",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e11", entity="E-YP", dimension="样品状态", action="缴费",
                actor="能力验证参加者", precondition="无", consequence="待核查",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e12", entity="E-FY", dimension="费用状态", action="缴费",
                actor="能力验证参加者", precondition="待缴费", consequence="已缴费",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e13", entity="E-FP", dimension="发票状态", action="发票开具",
                actor="财务管理人员", precondition="待开票", consequence="已开票",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e14", entity="E-YTZ", dimension="预通知状态", action="能力验证预通知",
                actor="项目管理员", precondition="未发送", consequence="待确认",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e15", entity="E-BMJL", dimension="报名记录状态", action="能力验证预通知",
                actor="项目管理员", precondition="报名成功", consequence="结果待提交",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e16", entity="E-YP", dimension="样品状态", action="样品核查",
                actor="样品管理员", precondition="待核查", consequence="待发样",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e17", entity="E-YP", dimension="样品状态", action="样品发放,作业指导书发送",
                actor="样品管理员", precondition="待发样", consequence="已发样",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e18", entity="E-YTZ", dimension="预通知状态", action="样品发放,作业指导书发送",
                actor="样品管理员", precondition="待确认", consequence="已确认",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e19", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="已发样", consequence="已还样",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e20", entity="E-BMJL", dimension="报名记录状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="结果待提交", consequence="结果已提交",
                source_ref="19.1 实施阶段")
    m.add_event(eid="e21", entity="E-BMJL", dimension="报名记录状态", action="结果报告回收",
                actor="项目管理员", precondition="结果已提交", consequence="结果退回修改",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e22", entity="E-BMJL", dimension="报名记录状态", action="评价人员进行评价",
                actor="评价人员", precondition="结果已提交", consequence="结果已提交",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e23", entity="E-BMJL", dimension="报名记录状态", action="对评价进行统计",
                actor="统计人员", precondition="结果已提交", consequence="结果已提交",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e24", entity="E-BMJL", dimension="报名记录状态", action="编制结果报告",
                actor="策划人员", precondition="结果已提交", consequence="报告/证书审核中",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e25", entity="E-XM", dimension="项目状态", action="编制结果报告",
                actor="策划人员", precondition="报名中", consequence="报告审核中",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e26", entity="E-BMJL", dimension="报名记录状态", action="技术主管审核报告",
                actor="技术主管", precondition="报告/证书审核中", consequence="报告/证书审核中",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e27", entity="E-BMJL", dimension="报名记录状态",
                action="报告、结果通知单授权签字人批准",
                actor="授权签字人", precondition="报告/证书审核中", consequence="报告/证书审核中",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e28", entity="E-BMJL", dimension="报名记录状态", action="证书实验室负责人批准",
                actor="实验室负责人", precondition="报告/证书审核中", consequence="报告/证书审核中",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e29", entity="E-BMJL", dimension="报名记录状态", action="发放结果报告和证书",
                actor="项目管理员", precondition="报告/证书审核中", consequence="报告/证书已发布",
                source_ref="19.1 报告编制和结果通知")
    m.add_event(eid="e30", entity="E-XM", dimension="项目状态", action="项目总结与归档",
                actor="策划人员", precondition="报告审核中", consequence="已结束",
                source_ref="19.1 项目验收总结")

    # ---- §19.2 测量审核提供者流程（与 §19.1 共用大部分事件，此处仅登记新增动作） ----
    m.add_event(eid="e31", entity="E-XM", dimension="项目状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="无", consequence="报名中",
                source_ref="19.2 项目准备阶段")
    m.add_event(eid="e32", entity="E-BMJL", dimension="报名记录状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="无", consequence="报名待审核",
                source_ref="19.2 项目准备阶段")
    m.add_event(eid="e33", entity="E-JFTZ", dimension="缴费通知单状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="无", consequence="未发送",
                source_ref="19.2 项目准备阶段")
    m.add_event(eid="e34", entity="E-FY", dimension="费用状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="无", consequence="待缴费",
                source_ref="19.2 项目准备阶段")
    m.add_event(eid="e35", entity="E-FP", dimension="发票状态", action="受理用户测量审核报名",
                actor="项目管理员", precondition="无", consequence="待开票",
                source_ref="19.2 项目准备阶段")
    m.add_event(eid="e36", entity="E-YP", dimension="样品状态", action="样品领用登记",
                actor="样品管理员", precondition="无", consequence="待核查",
                source_ref="19.2 实施阶段")
    m.add_event(eid="e37", entity="E-ZYDS", dimension="作业指导书状态", action="作业指导书编制",
                actor="策划人员", precondition="无", consequence="待审核",
                source_ref="19.2 实施阶段")
    m.add_event(eid="e38", entity="E-ZYDS", dimension="作业指导书状态", action="作业指导书审核通过",
                actor="技术主管", precondition="待审核", consequence="已审核",
                source_ref="19.2 实施阶段")
    m.add_event(eid="e39", entity="E-ZYDS", dimension="作业指导书状态", action="作业指导书退回",
                actor="技术主管", precondition="待审核", consequence="退回",
                source_ref="19.2 实施阶段")
    m.add_event(eid="e40", entity="E-ZYDS", dimension="作业指导书状态", action="作业指导书重新提交",
                actor="策划人员", precondition="退回", consequence="待审核",
                source_ref="19.2 实施阶段")

    # ---- §20.4.1 实验室管理 ----
    m.add_event(eid="e41", entity="E-LAB", dimension="实验室状态", action="实验室新增",
                actor="能力验证参加者", precondition="无", consequence="待审核",
                source_ref="20.3.1 实验室信息")
    m.add_event(eid="e42", entity="E-LAB", dimension="实验室状态", action="实验室审核通过",
                actor="系统管理人员", precondition="待审核", consequence="启用",
                source_ref="20.4.1.2 实验室审核")
    m.add_event(eid="e43", entity="E-LAB", dimension="实验室状态", action="实验室审核退回",
                actor="系统管理人员", precondition="待审核", consequence="已退回",
                source_ref="20.4.1.2 实验室审核")
    m.add_event(eid="e44", entity="E-LAB", dimension="实验室状态", action="实验室修改后重新提交",
                actor="能力验证参加者", precondition="已退回", consequence="待审核",
                source_ref="20.4.1.3 实验室修改")
    m.add_event(eid="e45", entity="E-LAB", dimension="实验室状态", action="实验室停用",
                actor="系统管理人员", precondition="启用", consequence="停用",
                source_ref="20.4.1.1 实验室列表与查询")
    m.add_event(eid="e46", entity="E-LAB", dimension="实验室状态", action="实验室启用",
                actor="系统管理人员", precondition="停用", consequence="启用",
                source_ref="20.4.1.1 实验室列表与查询")

    # ---- §20.4.2 标准库管理 ----
    m.add_event(eid="e47", entity="E-BZK", dimension="标准库状态", action="标准库新增",
                actor="系统管理人员", precondition="无", consequence="启用",
                source_ref="20.4.2.2 新增标准库")
    m.add_event(eid="e48", entity="E-BZK", dimension="标准库状态", action="标准库停用",
                actor="系统管理人员", precondition="启用", consequence="停用",
                source_ref="20.4.2.5 停用/启用标准库")
    m.add_event(eid="e49", entity="E-BZK", dimension="标准库状态", action="标准库启用",
                actor="系统管理人员", precondition="停用", consequence="启用",
                source_ref="20.4.2.5 停用/启用标准库")

    # ---- §20.7.1 评价管理 ----
    m.add_event(eid="e50", entity="E-PJ", dimension="评价状态", action="评价组长完善测试项目及评价细则",
                actor="评价组长", precondition="无", consequence="评价中",
                source_ref="20.7.1.1 测试项目、评价细则完善")
    m.add_event(eid="e51", entity="E-PJ", dimension="评价状态", action="评价人员评价",
                actor="评价人员", precondition="评价中", consequence="评价中",
                source_ref="20.7.1.2 协同评价")
    m.add_event(eid="e52", entity="E-PJ", dimension="评价状态", action="评价组长退回修改",
                actor="评价组长", precondition="评价中", consequence="评价中",
                source_ref="20.7.1.3 评价确认")
    m.add_event(eid="e53", entity="E-PJ", dimension="评价状态", action="评价组长结果确认",
                actor="评价组长", precondition="评价中", consequence="评价关闭",
                source_ref="20.7.1.3 评价确认")

    # ---- §20.9 业务审核 ----
    m.add_event(eid="e54", entity="E-TASK", dimension="任务状态", action="审核任务创建",
                actor="策划人员", precondition="无", consequence="待审核",
                source_ref="20.9.1.1 测量审核结果通知单审核流程优化")
    m.add_event(eid="e55", entity="E-TASK", dimension="任务状态", action="审核通过",
                actor="策划人员", precondition="待审核", consequence="审核通过",
                source_ref="20.9.1.4 任务批量处理")
    m.add_event(eid="e56", entity="E-TASK", dimension="任务状态", action="审核退回",
                actor="策划人员", precondition="待审核", consequence="审核退回",
                source_ref="20.9.1.4 任务批量处理")

    # ---- §20.5.2.1 上传付款单（创建缴费记录） ----
    m.add_event(eid="e57", entity="E-CW", dimension="缴费记录状态", action="上传付款单",
                actor="能力验证参加者", precondition="无", consequence="待退款",
                source_ref="20.5.2.1 已报名项目增加多次付款功能")

    # ---- §20.10.2.3 缴费单退款 ----
    m.add_event(eid="e58", entity="E-CW", dimension="缴费记录状态", action="缴费单退款",
                actor="财务管理人员", precondition="待退款", consequence="已退款",
                source_ref="20.10.2.3 缴费单退款")

    # ============================================================
    # Step 1 实体
    # ============================================================
    # ---- 1.0 动词词表 / 禁用关键字（§2 台账 action 列词根 + 回写补入；1.0 仅调一次） ----
    m.set_prohibition_config(config={
        "action_verbs": [
            "编制", "发布", "报名", "审核", "审核通过", "审核退回", "退回", "重新提交",
            "缴费", "开具", "预通知", "核查", "发放", "提交", "回收", "评价", "统计",
            "确认", "批准", "总结", "归档", "新增", "修改", "删除", "停用", "启用",
            "领用登记", "受理", "选入", "完善", "导入", "整理", "上传", "下载", "导出",
            "退款", "发送", "查询", "重置", "批量处理", "签章",
        ],
        "prohibit_keywords": [
            "不允许删除含有子项的记录",
            "不可直接编辑",
            "不能为大于当前缴费金额",
            "不可被选择",
            "不可以进行消息发送",
            "未结束的项目可以进行消息发送",
        ],
    })

    # ---- 1.1 角色（id 直落盘；name 取原文逐字复制 = 引用键） ----
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
    m.add_role(id="r14", name="监督员", readonly=True)
    m.add_role(id="r15", name="评价组长", readonly=False)

    # 权限：仅收 session/ui/file/query/config 类及不改状态的 crud 操作
    m.add_permission(role="项目管理员", operations=[
        "查询实验室", "查询项目", "查询报名记录", "查询标准库", "查询测试项",
        "查询子领域", "查询缴费记录", "查询信息发送记录", "查询统计报表",
        "查询历史项目", "查询数据看板", "查询缴费信息", "查询业务上报统计",
        "查询统计对比", "查询项目统计与查询", "查询报名信息统计", "查询收入统计",
        "查询项目查询", "查询客户查询", "查询任务", "导出评价结果",
        "导出审批流程列表", "导出统计对比", "导出业务上报统计", "导出项目上报",
        "导出缴费信息", "导出收入统计", "登录", "退出",
    ])
    m.add_permission(role="系统管理人员", operations=[
        "查询实验室", "修改实验室", "审核实验室", "停用实验室", "启用实验室",
        "查询标准库", "新增标准库", "修改标准库", "删除标准库", "停用标准库",
        "启用标准库", "管理测试项", "新增测试项", "修改测试项", "删除测试项",
        "管理子领域测试项", "新增子领域测试项", "删除子领域测试项",
        "查询信息发送记录", "查询消息详情", "查询用户角色", "配置用户角色",
        "查询机构", "管理内容", "查询通知管理", "查询意见反馈",
        "管理统计分析模板", "管理报告模板", "管理证书模板", "登录", "退出",
    ])
    m.add_permission(role="能力验证参加者", operations=[
        "新增实验室", "修改实验室", "查询项目", "查询已报名项目", "查询用户报名项目",
        "上传付款单", "下载预通知文件", "下载结果通知单", "下载证书",
        "提交测试结果", "提交报名", "查询通知公告", "查询常见问题", "查询待办事项",
        "意见反馈", "查询历史项目", "登录", "退出",
    ])
    m.add_permission(role="评价人员", operations=[
        "查询评价项目", "评价", "导出评价结果", "查询项目", "登录", "退出",
    ])
    m.add_permission(role="评价组长", operations=[
        "查询评价项目", "完善评价细则", "评价", "结果确认", "退回修改", "保存历史",
        "调整细则", "调整统计规则", "导出评价结果", "查询项目", "登录", "退出",
    ])
    m.add_permission(role="技术主管", operations=[
        "审核方案", "审核报告", "审核作业指导书", "审核结果通知单", "审核证书",
        "查询项目", "登录", "退出",
    ])
    m.add_permission(role="实验室负责人", operations=[
        "批准立项", "批准邀请函", "批准通知", "签发证书", "批准报告", "批准结果通知单",
        "查询项目", "登录", "退出",
    ])
    m.add_permission(role="授权签字人", operations=[
        "批准结果报告", "批准结果通知单", "批准使用认可标识",
        "查询项目", "登录", "退出",
    ])
    m.add_permission(role="策划人员", operations=[
        "编制设计方案", "编制作业指导书", "编制结果报告", "编制结果通知单",
        "编制任务通知书", "编制文件", "项目总结", "记录归档", "查询项目",
        "登录", "退出",
    ])
    m.add_permission(role="样品管理员", operations=[
        "查询样品", "样品出入库登记", "样品核查", "样品发放", "回收样品",
        "查询样品借出归还", "登录", "退出",
    ])
    m.add_permission(role="样品制备人员", operations=[
        "编制样品制备方案", "执行样品制备", "样品配置", "样品核查", "一致性测试",
        "登录", "退出",
    ])
    m.add_permission(role="统计人员", operations=[
        "结果统计分析", "查询统计报表", "查询项目统计与查询", "查询收入统计",
        "查询客户查询", "查询统计对比", "查询业务上报统计", "查询项目上报",
        "登录", "退出",
    ])
    m.add_permission(role="质量专员", operations=[
        "报告统计", "查询统计报表", "查询项目", "登录", "退出",
    ])
    m.add_permission(role="财务管理人员", operations=[
        "查询缴费信息", "导出缴费信息", "查询缴费记录", "退款", "上传发票",
        "修改财务备注", "查询收入统计", "财务统计", "查询项目", "登录", "退出",
    ])
    m.add_permission(role="监督员", operations=[
        "查询项目", "登录", "退出",
    ])

    # ---- 1.4 实体落盘 → m.add_entity() ----
    # E-XM 项目（core：状态枚举、多步骤多角色流程）
    m.add_entity(
        id="E-XM", name="项目", desc="能力验证或测量审核项目，承载主流程",
        type="core", tags=["multi-state", "approvable", "collaborative", "expirable"],
        attributes=[
            attr(name="项目编号", desc="项目唯一编号"),
            attr(name="项目名称", desc="项目名称"),
            attr(name="产品类型", desc="项目所属产品类型，is_config=True", is_config=True),
            attr(name="项目类型", desc="能力验证/测量审核，分支维度", is_config=True),
            attr(name="所属年度", desc="项目所属年度"),
            attr(name="子领域", desc="项目所属子领域"),
            attr(name="依据标准", desc="项目依据的标准"),
            attr(name="项目费用", desc="项目应收费用金额"),
            attr(name="项目负责人", desc="项目相关人员配置"),
            attr(name="技术主管", desc="项目技术主管，候选人唯一时默认填充"),
            attr(name="实验室负责人", desc="项目实验室负责人，候选人唯一时默认填充"),
            attr(name="授权签字人", desc="项目授权签字人，候选人唯一时默认填充"),
            attr(name="评价人员", desc="项目评价人员列表，首位默认为评价组长"),
            attr(name="监督员", desc="项目监督员，可为空"),
            attr(name="财务备注", desc="财务人员填写的备注"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": ["进行中"],
                "note": {"comment": "§19.3 枚举包含'进行中'，但 §19.1/§19.2 流程表未直接显示进入'进行中'的转换；推断'进行中'对应实施阶段样品发放后的中间态，但无显式动作触发，标为孤岛状态"},
            },
        ],
        operations=[
            op(name="项目新增", category="crud",
               expected_results=["项目记录创建，状态变为待开始；新增表单含监督员字段；技术主管/实验室负责人/授权签字人候选人唯一时默认填充"],
               source_ref="20.5.1.5 项目新增表单增加监督员；20.5.1.6 默认填充技术主管、实验室负责人、授权签字人",
               note=N(role="项目管理员", comment="项目管理员新建项目，回填对应转换 t01")),
            op(name="项目查询", category="query",
               expected_results=["按编号/名称/产品类型/项目类型/状态/年度条件分页展示项目列表"],
               source_ref="20.8.3.1 项目查询与统计",
               note=N(role="项目管理员")),
            op(name="项目列表批量处理", category="crud",
               expected_results=["跳转至报名信息批量处理页面，可批量上传结果通知单与证书并提交审核"],
               source_ref="20.5.1.3 项目批量操作",
               note=N(role="项目管理员", comment="回填对应转换 tXX（批量提交审核走 E-TASK 流程）")),
            op(name="机构代码导入", category="file",
               expected_results=["导入报名机构的三方代码，弹出代码导入表单窗口"],
               source_ref="20.5.1.2 机构代码导入",
               note=N(role="项目管理员")),
            op(name="文件整理", category="file",
               expected_results=["归档任务已开启；完成后操作列显示'查看归档'按钮；归档页面支持上传文件、打包下载、主子表查看"],
               source_ref="20.5.1.1 文件整理；20.6.1.1 文件整理",
               note=N(role="项目管理员", comment="对已结束项目操作，触发后端异步归档任务")),
            op(name="打包下载", category="file",
               expected_results=["下载 zip 格式归档文件，内含清单文件和按项目阶段命名的目录"],
               source_ref="20.5.1.1 文件整理；20.6.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="归档文件上传", category="file",
               expected_results=["归档数据列表新增一行，项目阶段为'其它'"],
               source_ref="20.5.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="归档文件编辑", category="crud",
               expected_results=["打开编辑表单弹窗，保存后刷新列表"],
               source_ref="20.5.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="归档文件下载", category="file",
               expected_results=["下载当前文件"],
               source_ref="20.5.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="消息发送", category="crud",
               expected_results=["表单验证通过后按选定方式发送消息；接收人1与接收人2不可同时为空；'待开始/报名中'状态下右侧实验室列表为所有实验室，其他状态为报名实验室"],
               source_ref="20.5.1.4 优化消息发送功能；20.6.1.2 优化消息发送功能",
               note=N(role="项目管理员", comment="未结束项目可进行消息发送；测试按钮可发送测试信息")),
            op(name="导出审批流程列表", category="file",
               expected_results=["导出满足当前查询条件的数据"],
               source_ref="20.9.1.5 审批流程列表导出",
               note=N(role="项目管理员")),
        ],
    )

    # E-YP 样品（core：状态枚举、多角色操作）
    m.add_entity(
        id="E-YP", name="样品", desc="项目主样品，承载样品状态面（区别于 E-BMYP 报名记录样品）",
        type="core", tags=["multi-state", "collaborative"],
        attributes=[
            attr(name="样品编号", desc="样品唯一编号"),
            attr(name="样品名称", desc="样品名称"),
            attr(name="所属项目", desc="归属的项目"),
            attr(name="制备方案", desc="样品制备方案"),
            attr(name="核查记录", desc="样品核查记录表"),
            attr(name="快递单号", desc="样品发放的快递单号或软件访问路径"),
        ],
        state_dimensions=[
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查", "待发样", "已发样", "已还样", "无需还样"],
                "initial": "待核查",
                "terminal": [],
                "inferred": ["已核查", "无需还样"],
                "note": {"comment": "§19.3 枚举仅含'待核查/已核查'两值；'待发样/已发样/已还样/无需还样'来自 §19.1/§19.2 流程表推导。'已核查'为 §19.3 枚举值但 §19.1 表格显示样品核查直接从待核查→待发样，推断'已核查'为瞬态或并入'待发样'，按孤岛保留"},
            },
        ],
        operations=[
            op(name="样品出入库登记", category="crud",
               expected_results=["样品出入库记录创建"],
               source_ref="12 库存管理",
               note=N(role="样品管理员")),
            op(name="样品借出归还记录", category="crud",
               expected_results=["记录样品借出/归还信息"],
               source_ref="3.2 功能要求表第23项",
               note=N(role="样品管理员")),
        ],
    )

    # E-BMJL 报名记录（core：状态枚举、多步骤多角色流程、独立业务载体）
    m.add_entity(
        id="E-BMJL", name="报名记录", desc="参加者提交的能力验证/测量审核报名记录",
        type="core", tags=["multi-state", "approvable", "collaborative", "expirable"],
        attributes=[
            attr(name="报名编号", desc="报名记录唯一编号"),
            attr(name="项目编号", desc="关联的项目编号"),
            attr(name="实验室名称", desc="报名实验室名称"),
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="报名时间", desc="报名提交时间"),
            attr(name="测试结果", desc="参加者提交的测试结果"),
            attr(name="评价得分", desc="评价人员给出的得分"),
            attr(name="评价结果", desc="评价确认后的最终结果"),
            attr(name="证书编号", desc="合格证书编号"),
            attr(name="证书到期时间", desc="合格证书到期时间，expirable 触发依据"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交",
                           "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "inferred": ["已撤销"],
                "note": {"comment": "§19.3 枚举包含'已撤销'但 §19.1/§19.2 流程表未显示进入'已撤销'的转换，按孤岛保留；其他状态均有台账事件覆盖"},
            },
        ],
        operations=[
            op(name="查询报名记录", category="query",
               expected_results=["按项目编号/名称/地域/报名时间等条件分页展示报名记录列表"],
               source_ref="20.8.3.2 报名信息统计",
               note=N(role="项目管理员")),
            op(name="上传付款单", category="file",
               expected_results=["付款录入表单提交成功；支持多次付款；不对付款金额进行校验限制"],
               source_ref="20.5.2.1 已报名项目增加多次付款功能；20.6.2.1",
               note=N(role="能力验证参加者", comment="多次付款功能：取消原付款金额校验，允许多次上传付款单")),
            op(name="下载预通知文件", category="file",
               expected_results=["下载当前报名所属项目的预通知文件"],
               source_ref="20.5.2.2 已报名项目详情页面增加预通知文件下载；20.5.3.1；20.6.2.2；20.6.3.1",
               note=N(role="能力验证参加者")),
            op(name="上传结果通知单", category="file",
               expected_results=["批量处理页面上传结果通知单文件，上传状态变为'已上传'"],
               source_ref="20.5.1.3 项目批量操作",
               note=N(role="项目管理员")),
            op(name="上传证书", category="file",
               expected_results=["批量处理页面上传证书文件，上传状态变为'已上传'"],
               source_ref="20.5.1.3 项目批量操作",
               note=N(role="项目管理员")),
            op(name="导出评价结果", category="file",
               expected_results=["下载评价结果文件"],
               source_ref="20.7.1.4 评价结果导出",
               note=N(role="评价人员")),
        ],
    )

    # E-YTZ 预通知（core：状态枚举）
    m.add_entity(
        id="E-YTZ", name="预通知", desc="能力验证预通知单，承载预通知状态面",
        type="core", tags=["multi-state"],
        attributes=[
            attr(name="预通知编号", desc="预通知单编号"),
            attr(name="所属项目", desc="归属的项目"),
            attr(name="预通知文件", desc="预通知文件附件"),
            attr(name="用户信息表", desc="随预通知发送的用户信息表"),
        ],
        state_dimensions=[
            {
                "dimension_name": "预通知状态",
                "states": ["未发送", "已发送", "待确认", "已确认"],
                "initial": "未发送",
                "terminal": ["已确认"],
                "inferred": [],
                "note": {"comment": "§19.3 通知状态枚举含'未发送/待确认/待审核/退回/已审核/已批准'，但 §19.1/§19.2 流程表显示预通知实际取值集合为'未发送/已发送/待确认/已确认'；'待审核/退回/已审核/已批准'为作业指导书状态面取值，落在 E-ZYDS。此处维度值与 §19.1/§19.2 表头'预通知状态'列对齐"},
            },
        ],
        operations=[],
    )

    # E-JFTZ 缴费通知单（core：状态枚举）
    m.add_entity(
        id="E-JFTZ", name="缴费通知单", desc="向参加者发送的缴费通知单",
        type="core", tags=["multi-state"],
        attributes=[
            attr(name="通知单编号", desc="通知单编号"),
            attr(name="所属项目", desc="归属项目"),
            attr(name="缴费金额", desc="通知缴费金额"),
        ],
        state_dimensions=[
            {
                "dimension_name": "缴费通知单状态",
                "states": ["未发送", "已发送"],
                "initial": "未发送",
                "terminal": ["已发送"],
                "inferred": [],
                "note": {"comment": "§19.1/§19.2 流程表中'缴费通知单'列取值"},
            },
        ],
        operations=[],
    )

    # E-FY 费用（core：状态枚举）
    m.add_entity(
        id="E-FY", name="费用", desc="报名记录对应的费用记录",
        type="core", tags=["multi-state"],
        attributes=[
            attr(name="费用编号", desc="费用记录编号"),
            attr(name="应缴金额", desc="项目费用金额"),
            attr(name="实缴金额", desc="已缴金额（多次付款累加）"),
            attr(name="退款金额", desc="累计退款金额"),
            attr(name="实际付款", desc="实缴-退款"),
        ],
        state_dimensions=[
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "inferred": [],
                "note": {"comment": "§19.3 枚举值"},
            },
        ],
        operations=[],
    )

    # E-FP 发票（core：状态枚举）
    m.add_entity(
        id="E-FP", name="发票", desc="向参加者开具的发票",
        type="core", tags=["multi-state", "expirable"],
        attributes=[
            attr(name="发票编号", desc="发票编号"),
            attr(name="开票类型", desc="电子专票/电子普票，is_config=True", is_config=True),
            attr(name="开票时间", desc="最后一次开票时间"),
            attr(name="关联项目", desc="关联的报名编号"),
            attr(name="项目金额", desc="项目费用"),
            attr(name="电子发票文件", desc="发票文件列表"),
        ],
        state_dimensions=[
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "inferred": [],
                "note": {"comment": "§19.3 枚举值"},
            },
        ],
        operations=[
            op(name="发票上传", category="file",
               expected_results=["支持多次分批上传发票；发票上传后显示在发票列表，可移除文件"],
               source_ref="20.10.2.2 修改发票上传功能使其支持多次分批上传",
               note=N(role="财务管理人员")),
            op(name="发票下载", category="file",
               expected_results=["下载电子发票文件"],
               source_ref="20.8.4.1 项目查询",
               note=N(role="能力验证参加者")),
        ],
    )

    # E-BMYP 报名记录样品（core：状态枚举）
    m.add_entity(
        id="E-BMYP", name="报名记录样品", desc="报名记录关联的样品收发状态，§19.3 单列",
        type="core", tags=["multi-state"],
        attributes=[
            attr(name="所属报名记录", desc="归属报名记录"),
            attr(name="收样时间", desc="样品收取时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "inferred": [],
                "note": {"comment": "§19.3 枚举值；本实体为孤岛——§19.1/§19.2 流程表未在该状态面承载独立事件，主流程样品状态面落在 E-YP；本实体保留以承载后续可能的扩展"},
            },
        ],
        operations=[],
    )

    # E-ZYDS 作业指导书（core：测量审核特有，状态枚举）
    m.add_entity(
        id="E-ZYDS", name="作业指导书", desc="测量审核项目的作业指导书，承载审核状态面",
        type="core", tags=["multi-state", "approvable"],
        attributes=[
            attr(name="所属项目", desc="归属的测量审核项目"),
            attr(name="指导书文件", desc="作业指导书文件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "作业指导书状态",
                "states": ["待审核", "已审核", "退回"],
                "initial": "待审核",
                "terminal": ["已审核"],
                "inferred": [],
                "note": {"comment": "§19.2 流程表'预通知状态'列在作业指导书编制行取值为'待审核/退回/已审核'；推断此处状态面属作业指导书，与 E-YTZ 预通知状态面分离"},
            },
        ],
        operations=[],
    )

    # E-LAB 实验室（core：状态枚举、审核链）
    m.add_entity(
        id="E-LAB", name="实验室", desc="参加者所属实验室，承载审核状态面",
        type="core", tags=["multi-state", "approvable", "expirable"],
        attributes=[
            attr(name="实验室编号", desc="实验室唯一编号"),
            attr(name="实验室名称", desc="实验室名称"),
            attr(name="统一社会信用代码", desc="统一社会信用代码"),
            attr(name="法人名称", desc="法人名称"),
            attr(name="企业类型", desc="企业类型"),
            attr(name="企业规模", desc="企业规模"),
            attr(name="CNAS", desc="已获CNAS认可标记"),
            attr(name="CNAS证书号", desc="CNAS证书号"),
            attr(name="CMA", desc="已获CMA认可标记"),
            attr(name="CMA证书编号", desc="CMA证书编号"),
            attr(name="邮箱", desc="联系邮箱"),
            attr(name="座机号码", desc="座机号码"),
            attr(name="联系人", desc="联系人"),
            attr(name="联系电话", desc="联系电话"),
            attr(name="行政区域", desc="行政区域"),
            attr(name="详细地址", desc="详细地址"),
            attr(name="默认实验室", desc="是否为默认实验室"),
            attr(name="证明文件", desc="营业执照或其他证书材料"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "启用", "停用", "已退回"],
                "initial": "待审核",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "§20.3.1/§20.4.1.1 枚举值；§20.4.1.1 列表查询的状态下拉选项中'已退回'写作'已退回'，与 §20.4.1.2 审核退回后变更状态一致；§20.3.1 提及'退回修改'与'已退回'同义，按枚举行原词取'已退回'"},
            },
        ],
        operations=[
            op(name="新增实验室", category="crud",
               expected_results=["实验室记录创建，状态为'待审核'；管理页面字段含状态列"],
               source_ref="20.3.1 实验室信息；20.4.1.1 实验室列表与查询",
               note=N(role="能力验证参加者", comment="回填对应转换 t37（创建转换 frm=None）")),
            op(name="修改实验室", category="crud",
               expected_results=["弹出修改窗口，可编辑实验室名称/统一社会信用代码/企业类型等字段；提交后保存修改"],
               source_ref="20.4.1.3 实验室修改",
               note=N(role="能力验证参加者")),
            op(name="删除实验室", category="crud",
               expected_results=["删除实验室记录"],
               source_ref="20.3.1 实验室信息",
               note=N(role="能力验证参加者")),
            op(name="查询实验室", category="query",
               expected_results=["按实验室编号/名称/状态条件分页展示实验室列表"],
               source_ref="20.4.1.1 实验室列表与查询",
               note=N(role="系统管理人员")),
            op(name="审核实验室", category="crud",
               expected_results=["弹出审核窗口，只读显示实验室内容；可填写审核结果与意见；通过则生成数据快照记录"],
               source_ref="20.4.1.2 实验室审核",
               note=N(role="系统管理人员", comment="回填对应转换 t38/t39（通过/退回两条分支）")),
        ],
    )

    # E-BZK 标准库（managed：CRUD/配置字典，含简单状态面）
    m.add_entity(
        id="E-BZK", name="标准库", desc="标准库基础数据，下属测试项/参数",
        type="managed", tags=["multi-state", "configurable"],
        attributes=[
            attr(name="标准库编号", desc="标准库编号，必填"),
            attr(name="标准库名称", desc="标准库名称，必填"),
            attr(name="状态", desc="启用/停用，is_config=True", is_config=True),
            attr(name="描述", desc="标准库描述"),
            attr(name="创建时间", desc="创建时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "标准库状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "§20.4.2 枚举值"},
            },
        ],
        operations=[
            op(name="新增标准库", category="crud",
               expected_results=["弹出新增表单对话框；标准库编号/名称/状态必填；提交后标准库出现在列表中"],
               source_ref="20.4.2.2 新增标准库",
               note=N(role="系统管理人员", comment="回填对应转换 t43")),
            op(name="修改标准库", category="crud",
               expected_results=["弹出编辑表单对话框；提交后保存修改"],
               source_ref="20.4.2.3 修改标准库",
               note=N(role="系统管理人员")),
            op(name="删除标准库", category="crud",
               expected_results=["弹出二次确认框；确认后删除；停用的标准库在项目创建等环节不可被选择"],
               source_ref="20.4.2.4 删除标准库；20.4.2.5 停用/启用标准库",
               note=N(role="系统管理人员")),
            op(name="管理测试项", category="ui",
               expected_results=["页面跳转或打开新标签页，进入该标准库的专属测试项管理界面"],
               source_ref="20.4.2.6 进入测试项管理界面",
               note=N(role="系统管理人员")),
            op(name="查询标准库", category="query",
               expected_results=["按标准库编号/名称/状态条件分页展示标准库列表"],
               source_ref="20.4.2.1 标准库列表与查询",
               note=N(role="系统管理人员")),
        ],
    )

    # E-CSS 测试项（managed：CRUD/树形结构）
    m.add_entity(
        id="E-CSS", name="测试项", desc="标准库或子领域下的测试项/参数，可嵌套",
        type="managed", tags=[],
        attributes=[
            attr(name="标号", desc="测试项标号，必填"),
            attr(name="名称", desc="测试项名称，必填"),
            attr(name="所属标准库", desc="归属的标准库"),
            attr(name="所属子领域", desc="归属的子领域"),
            attr(name="父测试项", desc="父测试项引用"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud",
               expected_results=["弹出新增表单对话框；标号/名称必填；提交后测试项出现在列表中"],
               source_ref="20.4.2.8 新增测试项；20.4.3.3 新增测试项",
               note=N(role="系统管理人员")),
            op(name="修改测试项", category="crud",
               expected_results=["弹出编辑表单对话框；提交后保存修改，刷新列表"],
               source_ref="20.4.2.9 修改测试项",
               note=N(role="系统管理人员")),
            op(name="删除测试项", category="crud",
               expected_results=["弹出二次确认框；含有子项的记录不允许删除"],
               source_ref="20.4.2.10 删除测试项；20.4.3.4 删除测试项",
               note=N(role="系统管理人员", comment="含有子项的数据不可以删除——落入 prohibit_keywords")),
            op(name="查询测试项", category="query",
               expected_results=["按子领域下拉条件分页展示测试项树形结构"],
               source_ref="20.4.3.2 测试项列表与结构展示",
               note=N(role="系统管理人员")),
        ],
    )

    # E-ZLY 子领域（managed：配置字典，与 E-BZK 关联）
    m.add_entity(
        id="E-ZLY", name="子领域", desc="子领域配置字典，下属测试项",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="子领域编号", desc="子领域编号"),
            attr(name="子领域名称", desc="子领域名称"),
        ],
        state_dimensions=[],
        operations=[
            op(name="管理子领域测试项", category="ui",
               expected_results=["页面跳转或打开新标签页，进入该子领域的专属测试项管理界面"],
               source_ref="20.4.3.1 进入测试项管理界面",
               note=N(role="系统管理人员")),
        ],
    )

    # E-PJ 评价（core：状态枚举、多角色协同评价）
    m.add_entity(
        id="E-PJ", name="评价", desc="项目评价工作，承载评价状态面",
        type="core", tags=["multi-state", "approvable", "collaborative"],
        attributes=[
            attr(name="所属项目", desc="归属项目"),
            attr(name="评分方式", desc="分值/权重两种方式，is_config=True", is_config=True),
            attr(name="评价细则", desc="评价细则内容"),
            attr(name="及格分", desc="及格分，评价组长录入"),
            attr(name="评价组长", desc="首位评价人员默认为组长"),
            attr(name="评价人员列表", desc="参与评价的评价人员集合"),
            attr(name="评价历史", desc="历史评价结果文件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["评价中", "评价关闭"],
                "initial": "评价中",
                "terminal": ["评价关闭"],
                "inferred": [],
                "note": {"comment": "§20.7.1 推导：评价组长结果确认后状态关闭；其他动作（评价人员评价/退回修改）均为评价中自环；§20.7.1.3'退回修改'开启下一轮评价，状态保持'评价中'"},
            },
        ],
        operations=[
            op(name="完善评价细则", category="crud",
               expected_results=["评价组长编辑完善评价项目及评价细则；测试项目列表新增/修改/删除；另存常用项"],
               source_ref="20.7.1.1 测试项目、评价细则完善",
               note=N(role="评价组长", comment="回填对应转换 t46")),
            op(name="评价", category="crud",
               expected_results=["评价人员输入或调整评价分数；只显示自己的评价结果；提交后保存评价结果"],
               source_ref="20.7.1.2 协同评价",
               note=N(role="评价人员", comment="回填对应转换 t47")),
            op(name="结果确认", category="crud",
               expected_results=["评价结果正式提交为最终评价结果，评价状态关闭"],
               source_ref="20.7.1.3 评价确认",
               note=N(role="评价组长", comment="回填对应转换 t49")),
            op(name="退回修改", category="crud",
               expected_results=["当前评价结果保存为历史结果，开启下一轮评价"],
               source_ref="20.7.1.3 评价确认",
               note=N(role="评价组长", comment="回填对应转换 t48（自环）")),
            op(name="保存历史", category="crud",
               expected_results=["当前评价结果保存为历史结果"],
               source_ref="20.7.1.3 评价确认",
               note=N(role="评价组长")),
            op(name="调整细则", category="crud",
               expected_results=["打开评价细节完善页面，配置完成后回到本页面将刷新数据"],
               source_ref="20.7.1.3 评价确认",
               note=N(role="评价组长")),
            op(name="调整统计规则", category="config",
               expected_results=["弹出统计规则配置弹窗；评价组长配置区间低值/高值；规则为大于等于低值小于高值"],
               source_ref="20.7.1.3 评价确认",
               note=N(role="评价组长", comment="category=④config，配置项变更")),
            op(name="下载评价历史", category="file",
               expected_results=["下载评价历史结果文件"],
               source_ref="20.7.1.3 评价确认",
               note=N(role="评价组长")),
        ],
    )

    # E-TASK 审核任务（core：审核流程）
    m.add_entity(
        id="E-TASK", name="审核任务", desc="业务审核流程中的审核任务（通知单/报告/证书审核）",
        type="core", tags=["multi-state", "approvable", "collaborative", "configurable"],
        attributes=[
            attr(name="任务编号", desc="任务唯一编号"),
            attr(name="任务类型", desc="结果通知单审核/报告审核/证书审核，is_config=True", is_config=True),
            attr(name="任务节点", desc="任务在审核流程中的节点"),
            attr(name="处理人顺序", desc="提交申请时签字人的选择顺序，is_config=True", is_config=True),
            attr(name="签章位置", desc="电子签章位置信息，自动代入"),
            attr(name="自定义流程", desc="系统预设≤4个自定义流程，is_config=True", is_config=True),
            attr(name="创建时间", desc="任务创建时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "任务状态",
                "states": ["待审核", "审核通过", "审核退回"],
                "initial": "待审核",
                "terminal": ["审核通过", "审核退回"],
                "inferred": [],
                "note": {"comment": "§20.9.1.4 批量审核表单审核结果选项为'同意/退回'，对应'审核通过/审核退回'状态值"},
            },
        ],
        operations=[
            op(name="批量审核", category="crud",
               expected_results=["勾选任务后弹出批量审核表单；可填写审核结果（同意/退回）与意见；批量执行"],
               source_ref="20.9.1.4 任务批量处理",
               note=N(role="项目管理员", comment="回填对应转换 t51/t52（通过/退回两条分支）")),
            op(name="查询任务", category="query",
               expected_results=["按任务类型/创建时间条件分页展示审批流程列表"],
               source_ref="20.9.1.5 审批流程列表导出",
               note=N(role="项目管理员")),
            op(name="导出审批流程列表", category="file",
               expected_results=["导出满足当前查询条件的数据"],
               source_ref="20.9.1.5 审批流程列表导出",
               note=N(role="项目管理员")),
            op(name="签章", category="crud",
               expected_results=["进行签章操作时自动代入预置的位置信息，减少手动调整"],
               source_ref="20.9.1.2 预置签章位置信息",
               note=N(role="项目管理员", comment="category=④config，配置项变更；自动代入位置信息")),
            op(name="选择自定义流程", category="config",
               expected_results=["选择并提交文档审核的自定义流程，并支持相应的签章"],
               source_ref="20.9.1.6 增加自定义流程",
               note=N(role="项目管理员", comment="系统预设≤4个自定义流程")),
        ],
    )

    # E-CW 缴费记录（managed：财务侧记录）
    m.add_entity(
        id="E-CW", name="缴费记录", desc="财务侧的缴费记录，承载退款状态",
        type="managed", tags=["expirable"],
        attributes=[
            attr(name="缴费记录编号", desc="缴费记录唯一编号"),
            attr(name="报名编号", desc="关联的报名编号"),
            attr(name="付款金额", desc="单次付款金额"),
            attr(name="退款金额", desc="累计退款金额，红色字体且大于0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="管理备注", desc="记录退款原因等内容"),
            attr(name="到款日期", desc="到款时间"),
            attr(name="缴费时间", desc="缴费时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "缴费记录状态",
                "states": ["待退款", "已退款"],
                "initial": "待退款",
                "terminal": ["已退款"],
                "inferred": [],
                "note": {"comment": "§20.10.2.3 推导：缴费记录创建后处于'待退款'；执行退款后变更为'已退款'；§20.10.2.3 列表新增'退款金额/实际付款/管理备注'列支持退款追踪"},
            },
        ],
        operations=[
            op(name="查询缴费记录", category="query",
               expected_results=["按报名编号条件分页展示缴费记录列表"],
               source_ref="20.10.2.3 缴费单退款",
               note=N(role="财务管理人员")),
            op(name="退款", category="crud",
               expected_results=["弹出付款单退款表单；退款金额不能大于当前缴费金额；提交后更新项目费用为实际付款金额"],
               source_ref="20.10.2.3 缴费单退款",
               note=N(role="财务管理人员", comment="回填对应转换 t53")),
        ],
    )

    # E-XX 信息发送记录（managed：无状态面，仅记录历史）
    m.add_entity(
        id="E-XX", name="信息发送记录", desc="系统中信息发送历史记录",
        type="managed", tags=[],
        attributes=[
            attr(name="接收号码", desc="接收人电话或邮箱"),
            attr(name="发送方式", desc="短信/邮件/站内信"),
            attr(name="发送时间", desc="发送时间"),
            attr(name="发送人", desc="发送操作人"),
            attr(name="发送结果", desc="发送结果状态"),
            attr(name="消息标题", desc="消息标题"),
            attr(name="消息内容", desc="消息正文"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query",
               expected_results=["按接收号码/发送时间/发送方式条件分页展示信息发送记录列表；仅系统管理员和项目管理员可查看"],
               source_ref="20.4.4.1 信息发送记录",
               note=N(role="系统管理人员", comment="仅系统管理员和项目管理员可以查看")),
            op(name="查看消息详情", category="query",
               expected_results=["查看消息详细内容"],
               source_ref="20.4.4.1 信息发送记录",
               note=N(role="系统管理人员")),
        ],
    )

    # E-DAGD 档案归档（managed：归档数据列表）
    m.add_entity(
        id="E-DAGD", name="档案归档", desc="项目文件整理与归档数据",
        type="managed", tags=[],
        attributes=[
            attr(name="所属项目", desc="归属项目"),
            attr(name="项目阶段", desc="归档文件所属项目阶段"),
            attr(name="文件名称", desc="归档文件名称"),
            attr(name="份数", desc="文件份数"),
            attr(name="页数", desc="文件页数"),
            attr(name="备注", desc="文件备注"),
            attr(name="实验室", desc="子表归属实验室"),
        ],
        state_dimensions=[],
        operations=[
            op(name="上传归档文件", category="file",
               expected_results=["弹出上传文件表单弹窗；文件名称必填；项目阶段为'其它'；保存后列表新增一行"],
               source_ref="20.5.1.1 文件整理；20.6.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="打包下载归档文件", category="file",
               expected_results=["下载 zip 格式归档文件，内含清单文件和按项目阶段命名的目录"],
               source_ref="20.5.1.1 文件整理；20.6.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="编辑归档文件", category="crud",
               expected_results=["打开编辑表单弹窗；保存后刷新列表"],
               source_ref="20.5.1.1 文件整理；20.6.1.1 文件整理",
               note=N(role="项目管理员")),
            op(name="下载归档文件", category="file",
               expected_results=["下载当前归档文件"],
               source_ref="20.5.1.1 文件整理；20.6.1.1 文件整理",
               note=N(role="项目管理员")),
        ],
    )

    # E-CJMM 常用测试项（managed：常用项配置）
    m.add_entity(
        id="E-CJMM", name="常用测试项", desc="项目新建页面的常用测试项组合配置",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="名称", desc="常用项名称，必填"),
            attr(name="所属子领域", desc="归属的子领域"),
            attr(name="测试项组合", desc="保存的测试项/评价细则组合"),
        ],
        state_dimensions=[],
        operations=[
            op(name="另存常用项", category="crud",
               expected_results=["弹出常用项新增表单；名称必填；保存常用项数据"],
               source_ref="20.5.1.7 增加常用子领域测试项编辑能力；20.6.1.5；20.7.1.1",
               note=N(role="项目管理员")),
            op(name="选择常用项", category="ui",
               expected_results=["将之前保存的测试项填充到测试项表单中"],
               source_ref="20.5.1.7；20.6.1.5；20.7.1.1",
               note=N(role="项目管理员", comment="category=③ui，展开/填充操作")),
            op(name="删除常用项", category="crud",
               expected_results=["删除当前常用项"],
               source_ref="20.5.1.7；20.6.1.5；20.7.1.1",
               note=N(role="项目管理员")),
        ],
    )

    # E-TJBB 统计报表（managed：各类统计查询报表）
    m.add_entity(
        id="E-TJBB", name="统计报表", desc="数据统计菜单下的各类统计查询报表",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="报表类型", desc="项目总览/项目查询/项目统计与查询/报名信息统计/收入统计/客户查询/统计对比/业务上报统计/项目上报/历史项目/数据看板，is_config=True", is_config=True),
            attr(name="查询条件", desc="各报表的查询条件集合"),
            attr(name="统计维度", desc="项目/时间/实验室/收入/数据上报维度，is_config=True", is_config=True),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询项目总览", category="query",
               expected_results=["展示关键性指标；点击客户数量/项目总数/进行中的项目/未付款的客户数/业务类型分布/当年产品类型分布/当年客户类型分布/本月付款情况统计结果可下钻到对应统计报表页面"],
               source_ref="20.8.1 项目总览",
               note=N(role="项目管理员", comment="数据下钻能力：点击关键指标跳转对应统计报表")),
            op(name="查询数据看板", category="query",
               expected_results=["展示实时监控（客户数量/项目数量/客户服务数量/合计收入/报告数据/证书数量）、趋势分析（近三年）、区域洞察（地图分布）、产品类型细分"],
               source_ref="20.8.2 数据看板",
               note=N(role="项目管理员")),
            op(name="查询项目统计与查询", category="query",
               expected_results=["按项目编号/名称/产品类型/项目类型/所属年度条件分页展示项目列表；点击查看可跳转到报名信息统计页面"],
               source_ref="20.8.3.1 项目查询与统计",
               note=N(role="项目管理员")),
            op(name="查询报名信息统计", category="query",
               expected_results=["按项目编号/名称/地域/报名时间条件分页展示报名信息列表"],
               source_ref="20.8.3.2 报名信息统计",
               note=N(role="项目管理员")),
            op(name="查询项目查询", category="query",
               expected_results=["按产品类型/项目类型/报名时间条件分页展示项目列表（含往年的历史数据）"],
               source_ref="20.8.4.1 项目查询",
               note=N(role="能力验证参加者")),
            op(name="查询收入统计", category="query",
               expected_results=["按项目编号/名称/产品类型/项目类型/收款时间条件分页展示收入列表；支持导出"],
               source_ref="20.8.5.1 收入统计",
               note=N(role="财务管理人员")),
            op(name="导出收入统计", category="file",
               expected_results=["导出符合筛选条件的所有数据"],
               source_ref="20.8.5.1 收入统计",
               note=N(role="财务管理人员")),
            op(name="查询客户查询", category="query",
               expected_results=["按时间（月度/季度/年度快速录入）条件分页展示客户统计列表；实验室名称列可跳转报名信息统计页面"],
               source_ref="20.8.6.1 优化客户统计列表查询参数时间参数快速录入",
               note=N(role="项目管理员", comment="时间快速录入：月度/季度/年度单选按钮")),
            op(name="查询统计对比", category="query",
               expected_results=["选择分组（年份/产品类型）、对比参数（项目数/客户数/收入/报告数）、业务类型进行数据综合对比分析；图表与表格两种表现形式"],
               source_ref="20.8.7.1 统计对比",
               note=N(role="项目管理员")),
            op(name="查询业务上报统计", category="query",
               expected_results=["按时间范围条件分页展示多表头统计列表（认证项目/报告统计/客户统计/收入）"],
               source_ref="20.8.8.1 业务上报统计",
               note=N(role="项目管理员")),
            op(name="导出业务上报统计", category="file",
               expected_results=["导出当前结果数据"],
               source_ref="20.8.8.1 业务上报统计",
               note=N(role="项目管理员")),
            op(name="查询项目上报", category="query",
               expected_results=["按产品类型/项目类型/报告时间条件分页展示项目统计列表（项目收入/报名数量/报告数量/证书数量）"],
               source_ref="20.8.9.1 项目上报",
               note=N(role="项目管理员")),
            op(name="导出项目上报", category="file",
               expected_results=["导出所有符合筛选条件的数据"],
               source_ref="20.8.9.1 项目上报",
               note=N(role="项目管理员")),
            op(name="查询历史项目", category="query",
               expected_results=["按项目名称/项目类型/子领域/所属年度条件分页展示历史项目列表"],
               source_ref="20.11.1.1 历史数据列表",
               note=N(role="项目管理员")),
        ],
    )

    # E-MSG 消息（managed：消息发送）
    m.add_entity(
        id="E-MSG", name="消息", desc="系统内消息发送对象，承载消息发送页面操作",
        type="managed", tags=[],
        attributes=[
            attr(name="接收人1", desc="数据列表选定的接收人"),
            attr(name="接收人2", desc="文本输入框输入的接收邮箱/电话，逗号分隔"),
            attr(name="标题", desc="消息标题"),
            attr(name="内容", desc="消息内容"),
            attr(name="发送方式", desc="短信/邮件/站内信"),
            attr(name="接收号码", desc="测试用接收号码"),
        ],
        state_dimensions=[],
        operations=[
            op(name="发送消息", category="crud",
               expected_results=["表单验证通过后按选定方式发送消息；接收人1和接收人2不能同时为空"],
               source_ref="20.5.1.4 优化消息发送功能；20.6.1.2 优化消息发送功能",
               note=N(role="项目管理员")),
            op(name="发送测试消息", category="crud",
               expected_results=["向指定接收号码发送测试信息"],
               source_ref="20.5.1.4 优化消息发送功能；20.6.1.2 优化消息发送功能",
               note=N(role="项目管理员")),
        ],
    )

    # E-YJ 缴费信息（managed：§20.10.1 缴费信息管理模块）
    m.add_entity(
        id="E-YJ", name="缴费信息", desc="财务管理下缴费信息管理模块，按时间/业务/发票类型维度筛选",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="实验室名称", desc="实验室名称"),
            attr(name="项目编号", desc="关联项目编号"),
            attr(name="项目类型", desc="能力验证/测量审核，is_config=True", is_config=True),
            attr(name="付款金额", desc="付款金额"),
            attr(name="开票类型", desc="电子专票/电子普票，is_config=True", is_config=True),
            attr(name="缴费时间", desc="缴费时间"),
            attr(name="到款日期", desc="到款日期"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询缴费信息", category="query",
               expected_results=["按缴费时间（月度/季度/年度快速录入）/业务类型/发票类型条件分页展示缴费信息列表"],
               source_ref="20.10.1.1 缴费信息查询与管理",
               note=N(role="财务管理人员")),
            op(name="导出缴费信息", category="file",
               expected_results=["导出符合筛选条件的所有数据"],
               source_ref="20.10.1.1 缴费信息查询与管理",
               note=N(role="财务管理人员")),
        ],
    )

    # E-FK 退款记录（managed：§20.10.2.3 缴费单退款）
    m.add_entity(
        id="E-FK", name="退款记录", desc="缴费单退款产生的记录",
        type="managed", tags=[],
        attributes=[
            attr(name="原缴费记录", desc="关联的原缴费记录"),
            attr(name="退款金额", desc="本次退款金额，不能大于当前缴费金额"),
            attr(name="备注", desc="退款备注"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增退款", category="crud",
               expected_results=["弹出付款单退款表单；退款金额必填且不能大于当前缴费金额；提交后更新项目费用为实际付款金额"],
               source_ref="20.10.2.3 缴费单退款",
               note=N(role="财务管理人员")),
        ],
    )

    # E-TZGG 通知公告（managed）
    m.add_entity(
        id="E-TZGG", name="通知公告", desc="首页通知公告模块",
        type="managed", tags=["expirable"],
        attributes=[
            attr(name="公告标题", desc="公告标题"),
            attr(name="公告内容", desc="公告内容"),
            attr(name="发布时间", desc="发布时间"),
            attr(name="是否为新", desc="15天内发布标注'new'标识，超过15天自动隐藏"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询通知公告", category="query",
               expected_results=["分页展示通知公告列表；15天内发布的通知在内容前标注'new'标识"],
               source_ref="20.2.1 通知公告",
               note=N(role="能力验证参加者", comment="15天内自动隐藏'new'标识——落入 BR")),
        ],
    )

    # E-SJKB 数据看板（managed：§20.8.2 专项可视化）
    m.add_entity(
        id="E-SJKB", name="数据看板", desc="专项可视化数据看板，展示关键运营指标",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="实时监控指标", desc="客户数量/项目数量/客户服务数量/合计收入/报告数据/证书数量"),
            attr(name="趋势分析维度", desc="近三年历史变化趋势，is_config=True", is_config=True),
            attr(name="区域洞察维度", desc="地图客户分布，按省份"),
            attr(name="历年/近三年切换", desc="维度切换按钮，is_config=True", is_config=True),
            attr(name="产品类型细分", desc="项目数量和收入情况按产品类型"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询历年数据", category="query",
               expected_results=["弹窗方式浮于页面中展示历年统计数据"],
               source_ref="20.8.2.1 数据看板",
               note=N(role="项目管理员")),
            op(name="查询近三年数据", category="query",
               expected_results=["弹窗方式浮于页面中展示近三年统计数据"],
               source_ref="20.8.2.1 数据看板",
               note=N(role="项目管理员")),
            op(name="区域信息提示", category="ui",
               expected_results=["鼠标移动到不同区域时以信息提示框方式显示当前区域的客户数量"],
               source_ref="20.8.2.1 数据看板",
               note=N(role="项目管理员", comment="category=③ui，信息提示框展示")),
        ],
    )

    # ---- 1.5 结构关系 → m.add_structural() ----
    # 四元判定：a/b/c/d 首条命中，dependent 判定按 ①/②/③
    # 实验室→参加者：实验室是参加者的属性集合，参加者注册即关联实验室，独立创建流程
    # → 判 (d) B 有独立创建流程，且不满足 (c)；confidence=medium
    m.add_structural(
        frm="E-LAB", to="E-BMJL",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="实验室作为报名记录的引用源（统一社会信用代码、实验室名称等基础信息）",
        confidence="medium",
        note={"comment": "判 (d)：报名记录有独立创建流程（用户报名触发），实验室不级联；dependent 推断为'有'但 §19 未直写下级实体，按 (d)+medium 处置；management_dimension 复核：实验室由系统管理人员管理（CRUD），属配置数据源"},
    )
    # 标准库→测试项：判 (b) 标准库创建时测试项不自动入 initial；但每条标准库必有测试项 → 复核每条 A 必有 B，可能无 B → 归 (d)
    m.add_structural(
        frm="E-BZK", to="E-CSS",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="标准库作为测试项的引用源，测试项独立创建并归属某标准库",
        confidence="medium",
        note={"comment": "判 (d) 复核：标准库可有空测试项（§20.4.2.2 新增标准库表单不强制测试项），且测试项有独立创建流程（§20.4.2.8 新增测试项）；§20.4.2.7 进入测试项管理后展示嵌套结构，A 不强制 B 存在；management_dimension 复核：标准库/测试项均由系统管理人员管理"},
    )
    # 子领域→测试项：判 (a) 子领域配置测试项时引用标准库下测试项，子领域独立创建
    m.add_structural(
        frm="E-ZLY", to="E-CSS",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="子领域引用标准库下测试项，作为项目录入时的选择数据源",
        confidence="high",
        note={"comment": "判 (a)：子领域提供测试项分类引用，§20.4.3.3 子领域新增测试项时选择标准库与测试项树；B（子领域下的测试项引用）独立创建；management_dimension 复核：子领域与测试项均由系统管理人员管理"},
    )
    # 项目→报名记录：判 (c) 报名记录有独立创建流程（用户报名），且为 core 流程实体，A 项目为业务归属容器
    m.add_structural(
        frm="E-XM", to="E-BMJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目包含多条报名记录；报名记录归属项目业务",
        confidence="high",
        note={"comment": "判 (c)：报名记录有独立创建流程（用户报名触发，e04），E-BMJL type=core 且为流程主体；E-XM 为业务归属容器；management_dimension 复核：项目由项目管理员管理，报名记录生命周期依附项目但不级联删除"},
    )
    # 项目→样品：判 (c) 样品有独立创建流程（缴费触发，e11；样品领用登记，e36）
    m.add_structural(
        frm="E-XM", to="E-YP",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目包含多个样品（每条报名记录对应一个样品）",
        confidence="high",
        note={"comment": "判 (c)：样品有独立创建流程（缴费触发 e11，样品领用登记 e36），E-YP type=core；A 项目为业务归属容器；management_dimension 复核：样品由样品管理员管理"},
    )
    # 报名记录→报名记录样品：判 (b) 报名记录创建时自动创建对应样品记录（待发样 initial）
    m.add_structural(
        frm="E-BMJL", to="E-BMYP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="报名记录与报名记录样品一一对应",
        confidence="medium",
        note={"comment": "判 (b) 复核：每条 A 必有 B；但 §19.1/§19.2 流程表中样品状态面落在 E-YP，E-BMYP 为 §19.3 单列的报名记录样品状态面，文档未直写两者关系；推断 1:1 composition，confidence=medium；management_dimension 复核：报名记录样品状态由样品管理员管理"},
    )
    # 报名记录→费用：判 (b) 报名记录创建时费用自动入 initial（待缴费）
    m.add_structural(
        frm="E-BMJL", to="E-FY",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="报名记录与费用一一对应",
        confidence="high",
        note={"comment": "判 (b)：报名动作（e04-e07）同时创建报名记录与费用记录（待缴费 initial），每条 A 必有 B；§19.1 流程表'报名'行同时显示报名记录与费用状态；management_dimension 复核：费用由财务管理人员与参加者共同操作"},
    )
    # 报名记录→缴费通知单：判 (b) 报名创建时缴费通知单自动入 initial（未发送）
    m.add_structural(
        frm="E-BMJL", to="E-JFTZ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="报名记录与缴费通知单一一对应",
        confidence="high",
        note={"comment": "判 (b)：报名动作同时创建缴费通知单（未发送 initial）；management_dimension 复核：缴费通知单由项目管理员发送"},
    )
    # 报名记录→发票：判 (b) 报名创建时发票自动入 initial（待开票）
    m.add_structural(
        frm="E-BMJL", to="E-FP",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="报名记录与发票一一对应",
        confidence="high",
        note={"comment": "判 (b)：报名动作同时创建发票记录（待开票 initial）；management_dimension 复核：发票由财务管理人员开具"},
    )
    # 报名记录→缴费记录：判 (d) 缴费记录有独立创建流程（用户上传付款单触发），可能多次创建
    m.add_structural(
        frm="E-BMJL", to="E-CW",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联多条缴费记录（多次付款）",
        confidence="high",
        note={"comment": "判 (d)：缴费记录有独立创建流程（§20.5.2.1 上传付款单），支持多次创建（多次付款功能），不满足 (c)；management_dimension 复核：缴费记录由财务管理人员管理"},
    )
    # 项目→预通知：判 (b) 项目发布时预通知自动入 initial（未发送）
    m.add_structural(
        frm="E-XM", to="E-YTZ",
        relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="项目与预通知一一对应",
        confidence="high",
        note={"comment": "判 (b)：能力验证计划发布（e03）创建预通知（未发送 initial），每条 A 必有 B；management_dimension 复核：预通知由项目管理员发送"},
    )
    # 项目→评价：判 (c) 评价有独立创建流程（评价组长完善细则触发，e50），评价为 core 流程实体
    m.add_structural(
        frm="E-XM", to="E-PJ",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目包含评价工作",
        confidence="high",
        note={"comment": "判 (c)：评价有独立创建流程（评价组长完善测试项目及评价细则 e50），E-PJ type=core，A 项目为业务归属容器；management_dimension 复核：评价由评价组长与评价人员共同操作"},
    )
    # 报名记录→审核任务：判 (d) 审核任务有独立创建流程（提交审核触发，e54）
    m.add_structural(
        frm="E-BMJL", to="E-TASK",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联多条审核任务（结果通知单/报告/证书审核）",
        confidence="high",
        note={"comment": "判 (d)：审核任务有独立创建流程（§20.9.1.1 测量审核结果通知单审核流程优化，e54 审核任务创建）；§20.9.1.4 任务批量处理显示一个报名可对应多个审核任务；management_dimension 复核：审核任务由项目管理员/技术主管/授权签字人/实验室负责人多角色操作"},
    )
    # 项目→作业指导书：判 (b) 项目创建时作业指导书不自动入 initial（仅测量审核项目涉及）→ 判 (d)
    m.add_structural(
        frm="E-XM", to="E-ZYDS",
        relation_type="reference", cardinality="1:1",
        ownership_dimension="configuration_source",
        desc="测量审核项目关联作业指导书",
        confidence="medium",
        note={"comment": "判 (d)：作业指导书有独立创建流程（e37 作业指导书编制），仅测量审核项目涉及，可能永不创建（能力验证项目无此实体）；不满足 (c)；confidence=medium；management_dimension 复核：作业指导书由策划人员编制、技术主管审核"},
    )
    # 标准库→子领域（无直接关系，子领域引用标准库下测试项）
    # 不建立 frm=标准库 to=子领域 的结构关系——两者通过测试项间接关联，无直接 ownership
    # 项目→档案归档：判 (d) 归档有独立创建流程（文件整理触发，异步任务）
    m.add_structural(
        frm="E-XM", to="E-DAGD",
        relation_type="reference", cardinality="1:1",
        ownership_dimension="configuration_source",
        desc="项目关联档案归档数据",
        confidence="medium",
        note={"comment": "判 (d)：归档有独立创建流程（§20.5.1.1 文件整理触发，仅已结束项目可触发，可能永不创建）；management_dimension 复核：档案归档由项目管理员管理"},
    )
    # 子领域→常用测试项：判 (a) 子领域作为常用项的引用源
    m.add_structural(
        frm="E-ZLY", to="E-CJMM",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="子领域作为常用测试项的归属维度",
        confidence="high",
        note={"comment": "判 (a)：子领域提供常用项分类引用（§20.5.1.7 选择子领域下之前保存的常用测试项组合）；management_dimension 复核：常用项由项目管理员保存"},
    )

    # ============================================================
    # Step 2 分支维度 → m.add_branch_dimension()
    # ============================================================
    # 分支维度 1：项目类型（路径分歧——能力验证走"设计方案编制→能力验证计划发布"，
    # 测量审核走"受理用户测量审核报名"）
    m.add_branch_dimension(
        dimension="项目类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="项目创建入口与初始状态：能力验证项目经设计方案编制进入待开始再发布至报名中；测量审核项目经受理用户报名直接进入报名中",
        evidence="三型判定：②运行时选择型（§3.2 功能要求明确区分能力验证与测量审核两类项目；§19.1 与 §19.2 流程分流；§20.6 测量审核与 §20.5 能力验证并列模块）",
        branches=[
            {"value": "能力验证", "target_transition": "t01 设计方案编制（创建转换）", "desc": "能力验证分支：策划人员编制设计方案→项目状态待开始"},
            {"value": "测量审核", "target_transition": "t03 受理用户测量审核报名（创建转换）", "desc": "测量审核分支：项目管理员受理用户报名→项目状态报名中"},
        ],
    )

    # 分支维度 2：报名审核结果（路径分歧——退回 vs 通过）
    m.add_branch_dimension(
        dimension="报名审核结果", entity="E-BMJL",
        values=["报名退回", "报名成功"],
        impact_scope="报名记录后续路径：报名退回需修改后重新提交；报名成功进入缴费/预通知阶段",
        evidence="三型判定：③隐式分支（§19.1 流程表'报名审核'行报名记录状态取值分裂为'报名退回/成功'）",
        branches=[
            {"value": "报名退回", "target_transition": "t11 报名审核（退回分支）", "desc": "审核未通过，报名记录状态变更为报名退回"},
            {"value": "报名成功", "target_transition": "t12 报名审核（通过分支）", "desc": "审核通过，报名记录状态变更为报名成功"},
        ],
    )

    # 分支维度 3：样品核查结果（结果差异——路径相同，结果描述不同）
    m.add_branch_dimension(
        dimension="样品核查结果", entity="E-YP",
        values=["已核查", "待发样"],
        impact_scope="样品核查后状态：§19.1 流程表'样品核查'行取值'已核查、待发样'为同一转换的不同结果描述",
        evidence="三型判定：③隐式分支（§19.1 流程表'样品核查'行样品状态取值'已核查、待发样'，§19.3 枚举仅含'待核查/已核查'，'待发样'来自台账推导）",
        branches=[
            {"value": "已核查", "target_transition": "t34 样品核查（共用一条）", "desc": "样品核查完成，状态变为已核查"},
            {"value": "待发样", "target_transition": "t34 样品核查（共用一条）", "desc": "样品核查完成，状态变为待发样"},
        ],
    )

    # 分支维度 4：参加者测试样品状态（结果差异）
    m.add_branch_dimension(
        dimension="参加者测试样品状态", entity="E-YP",
        values=["已还样", "待核查", "无需还样"],
        impact_scope="参加者测试与结果提交后样品状态；§19.1 流程表该行取值'已还样、待核查/无需还样'",
        evidence="三型判定：③隐式分支（§19.1 流程表'参加者测试与结果提交'行样品状态取值分裂）",
        branches=[
            {"value": "已还样", "target_transition": "t36 参加者测试与结果提交（共用一条）", "desc": "参加者归还样品，状态变为已还样"},
            {"value": "待核查", "target_transition": "t36 参加者测试与结果提交（共用一条）", "desc": "样品重新进入核查流程"},
            {"value": "无需还样", "target_transition": "t36 参加者测试与结果提交（共用一条）", "desc": "项目无需还样，状态变为无需还样"},
        ],
    )

    # 分支维度 5：评价人员角色（路径分歧——组长 vs 评价人员）
    m.add_branch_dimension(
        dimension="评价人员角色", entity="E-PJ",
        values=["评价组长", "评价人员"],
        impact_scope="评价操作权限：评价组长可结果确认/退回修改；评价人员仅评价自己的结果",
        evidence="三型判定：①配置型（§20.7.1 首段'第一个被选择的评价人员默认做为评价组长'，配置时确定，影响后续操作权限）",
        branches=[
            {"value": "评价组长", "target_transition": "t53 评价组长结果确认", "desc": "评价组长对评价结果进行确认"},
            {"value": "评价人员", "target_transition": "t51 评价人员评价", "desc": "评价人员对自己的评价结果进行评价"},
        ],
    )

    # 分支维度 6：缴费信息查询时间快速录入
    m.add_branch_dimension(
        dimension="缴费时间快速录入", entity="E-YJ",
        values=["月度", "季度", "年度"],
        impact_scope="缴费信息查询的时间范围参数",
        evidence="三型判定：①配置型（§20.10.1.1 三个单选按钮：本月/本季/本年，配置时影响时间选择组件范围）",
        branches=[
            {"value": "月度", "target_transition": "查询缴费信息（共用一条）", "desc": "时间选择组件范围为本月"},
            {"value": "季度", "target_transition": "查询缴费信息（共用一条）", "desc": "时间选择组件范围为本季"},
            {"value": "年度", "target_transition": "查询缴费信息（共用一条）", "desc": "时间选择组件范围为本年"},
        ],
    )

    # 分支维度 7：客户查询时间快速录入
    m.add_branch_dimension(
        dimension="客户查询时间快速录入", entity="E-TJBB",
        values=["月度", "季度", "年度"],
        impact_scope="客户查询的录入时间范围",
        evidence="三型判定：①配置型（§20.8.6.1 三个单选按钮：月度/季度/年度，时间选择框前增加）",
        branches=[
            {"value": "月度", "target_transition": "查询客户查询（共用一条）", "desc": "时间选择框内时间范围为本月"},
            {"value": "季度", "target_transition": "查询客户查询（共用一条）", "desc": "时间选择框内时间范围为本季"},
            {"value": "年度", "target_transition": "查询客户查询（共用一条）", "desc": "时间选择框内时间范围为本年"},
        ],
    )

    # 分支维度 8：统计对比分组
    m.add_branch_dimension(
        dimension="统计对比分组", entity="E-TJBB",
        values=["年份", "产品类型"],
        impact_scope="统计对比的展示维度，数据列表根据分组变化显示不同内容",
        evidence="三型判定：②运行时选择型（§20.8.7.1 '分组'下拉列表，必选，选项有年份、产品类型）",
        branches=[
            {"value": "年份", "target_transition": "查询统计对比（共用一条）", "desc": "按年份分组展示对比数据"},
            {"value": "产品类型", "target_transition": "查询统计对比（共用一条）", "desc": "按产品类型分组展示对比数据"},
        ],
    )

    # 分支维度 9：数据看板时间维度
    m.add_branch_dimension(
        dimension="数据看板时间维度", entity="E-SJKB",
        values=["历年", "近三年"],
        impact_scope="区域洞察模块的统计数据范围；点击按钮可查询对应统计数据，统计数据以弹窗方式浮于页面中",
        evidence="三型判定：②运行时选择型（§20.8.2.1 '历年'和'近三年'维度的专项统计功能按钮）",
        branches=[
            {"value": "历年", "target_transition": "查询历年数据（共用一条）", "desc": "弹窗方式展示历年统计数据"},
            {"value": "近三年", "target_transition": "查询近三年数据（共用一条）", "desc": "弹窗方式展示近三年统计数据"},
        ],
    )

    # 分支维度 10：批量处理内容
    m.add_branch_dimension(
        dimension="批量处理内容", entity="E-BMJL",
        values=["结果通知单", "证书"],
        impact_scope="批量处理页面操作列显示的上传按钮（上传结果通知单/上传证书）",
        evidence="三型判定：②运行时选择型（§20.5.1.3 '处理内容'单选按钮，包含结果通知单、证书两个选项，配合'上传状态'对列表内容进行筛选）",
        branches=[
            {"value": "结果通知单", "target_transition": "上传结果通知单操作（共用一条）", "desc": "操作列显示上传结果通知单按钮"},
            {"value": "证书", "target_transition": "上传证书操作（共用一条）", "desc": "操作列显示上传证书按钮"},
        ],
    )

    # 分支维度 11：批量审核结果（路径分歧——同意 vs 退回）
    m.add_branch_dimension(
        dimension="批量审核结果", entity="E-TASK",
        values=["同意", "退回"],
        impact_scope="审核任务状态变更：同意→审核通过；退回→审核退回",
        evidence="三型判定：②运行时选择型（§20.9.1.4 审核结果下拉选择框，选项有：同意、退回）",
        branches=[
            {"value": "同意", "target_transition": "t55 审核通过", "desc": "任务状态变更为审核通过"},
            {"value": "退回", "target_transition": "t56 审核退回", "desc": "任务状态变更为审核退回"},
        ],
    )

    # ============================================================
    # Step 3 转换与因果
    # ============================================================
    # ---- 3.1 转换 → m.add_trans() ----
    # 台账每条事件在其 (entity, dimension) 上落一条转换
    # ---- E-XM/项目状态 ----
    # t01: 设计方案编制（创建转换，能力验证分支入口）
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["项目记录创建，状态变为待开始；新增表单含监督员字段；技术主管/实验室负责人/授权签字人候选人唯一时默认填充"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 项目准备阶段/方案设计阶段；20.5.1.5 项目新增表单增加监督员；20.5.1.6 默认填充",
        note={"branch_dimension": "项目类型", "comment": "源自 e01；⓪序判frm=None；路径分歧：能力验证分支首条，Step 2 value=能力验证 指向本条；op 回填：项目新增"},
    )

    # t02: 能力验证计划发布（待开始→报名中）
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["项目状态变为报名中；同时创建预通知记录（状态为未发送）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e02；③序判frm先于to；路径分歧：能力验证分支后续转换；联动 e03 创建 E-YTZ"},
    )

    # t03: 受理用户测量审核报名（创建转换，测量审核分支入口）
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["项目记录创建，状态变为报名中；同时创建报名记录/缴费通知单/费用/发票记录"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 项目准备阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e31；⓪序判frm=None；路径分歧：测量审核分支首条，Step 2 value=测量审核 指向本条；联动 e32-e35 创建 E-BMJL/E-JFTZ/E-FY/E-FP"},
    )

    # t04: 编制结果报告（报名中→报告审核中，inferred——§19.3 枚举含'报告审核中'但 §19.1 表格未显示转换触发点）
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="报名中", to="报告审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["项目状态变为报告审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知",
        note={"inferred": True, "comment": "源自 e25；③序判frm先于to；§19.1 流程表未直写此项目状态转换，但 §19.3 枚举含'报告审核中'且 §19.1'编制结果报告'行报名记录状态变为'报告/证书审核中'，推断项目状态同步进入'报告审核中'"},
    )

    # t05: 项目总结与归档（报告审核中→已结束，inferred）
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="项目总结与归档", role="策划人员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="报名记录处于报告/证书已发布状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书已发布")),
        ],
        expected_results=["项目状态变为已结束；策划人员进行项目总结并记录归档"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1 项目验收总结",
        note={"inferred": True, "comment": "源自 e30；③序判frm先于to；§19.1 项目验收总结阶段描述'策划人员进行项目总结，记录归档'，但未直写项目状态转换；按 §19.3 枚举'已结束'为终态反推此转换存在；traits=audit 因'记录归档'留痕要求"},
    )

    # ---- E-YTZ/预通知状态 ----
    # t06: 能力验证计划发布（创建预通知记录）
    m.add_trans(
        tid="t06", entity="E-YTZ", dimension="预通知状态",
        frm=None, to="未发送", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["预通知记录创建，状态为未发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e03；⓪序判frm=None；与 t02 同 action，承担 E-YTZ 维度的转换"},
    )

    # t07: 能力验证预通知（未发送→待确认）
    m.add_trans(
        tid="t07", entity="E-YTZ", dimension="预通知状态",
        frm="未发送", to="待确认", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="预通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-YTZ", "预通知状态", "未发送")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["预通知状态变为待确认；同时报名记录状态变为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"comment": "源自 e14；③序判frm先于to；联动 e15 使 E-BMJL 报名成功→结果待提交"},
    )

    # t08: 样品发放,作业指导书发送（待确认→已确认）
    m.add_trans(
        tid="t08", entity="E-YTZ", dimension="预通知状态",
        frm="待确认", to="已确认", action="样品发放,作业指导书发送", role="样品管理员",
        preconditions=[
            precond(text="预通知处于待确认状态", ptype="state_ref",
                    ref=state_ref("E-YTZ", "预通知状态", "待确认")),
            precond(text="样品处于待发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待发样")),
        ],
        expected_results=["预通知状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"comment": "源自 e18；③序判frm先于to；联动 e17 使 E-YP 待发样→已发样"},
    )

    # ---- E-BMJL/报名记录状态 ----
    # t09: 报名（创建转换，能力验证分支）
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["报名记录创建，状态为报名待审核；同时创建缴费通知单（未发送）、费用（待缴费）、发票（待开票）"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e04；⓪序判frm=None；联动 e05-e07 创建 E-JFTZ/E-FY/E-FP"},
    )

    # t10: 受理用户测量审核报名（创建转换，测量审核分支）
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录创建，状态为报名待审核；同时创建缴费通知单/费用/发票记录"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 项目准备阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e32；⓪序判frm=None；与 t03 同 action，承担 E-BMJL 维度"},
    )

    # t11: 报名审核（退回分支）
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="报名审核结果=报名退回", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名退回；同时缴费通知单状态变为已发送；通过短信通知参加者'审核未通过'"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="19.1 实施阶段；20.5.3.2 操作节点增加用户短信通知",
        note={"branch_dimension": "报名审核结果", "comment": "源自 e08；①序判'退回'→backward；路径分歧：退回分支，Step 2 value=报名退回 指向本条；联动 e10 使 E-JFTZ 未发送→已发送；短信通知落入 BR"},
    )

    # t12: 报名审核（通过分支）
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="报名审核结果=报名成功", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名成功；同时缴费通知单状态变为已发送；通过短信通知参加者'审核通过'"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段；20.5.3.2 操作节点增加用户短信通知",
        note={"branch_dimension": "报名审核结果", "comment": "源自 e09；③序判frm先于to；路径分歧：通过分支，Step 2 value=报名成功 指向本条；联动 e10 使 E-JFTZ 未发送→已发送；短信通知落入 BR"},
    )

    # t13: 能力验证预通知（报名成功→结果待提交）
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="预通知处于未发送或待确认状态", ptype="state_ref",
                    ref=state_ref("E-YTZ", "预通知状态", "待确认")),
        ],
        expected_results=["报名记录状态变为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"comment": "源自 e15；③序判frm先于to；与 t07 同 action，承担 E-BMJL 维度"},
    )

    # t14: 参加者测试与结果提交（结果待提交→结果已提交）
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已发样")),
        ],
        expected_results=["报名记录状态变为结果已提交；同时样品状态变为已还样/待核查/无需还样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"comment": "源自 e20；③序判frm先于to；联动 e19 使 E-YP 已发样→已还样/待核查/无需还样（分支维度：参加者测试样品状态）"},
    )

    # t15: 结果报告回收（结果已提交→结果退回修改）
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果报告回收", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变为结果退回修改"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="19.1 报告编制和结果通知",
        note={"comment": "源自 e21；①序判'退回'→backward；§19.1 表格'结果报告回收'行显示取值'结果已提交/结果退回修改'，本条为退回分支"},
    )

    # t16: 评价人员进行评价（结果已提交→结果已提交，自环）
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果已提交", action="评价人员进行评价", role="评价人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["评价人员对参加者结果进行评价；评价表生成；报名记录状态保持结果已提交"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知；20.7.1.2 协同评价",
        note={"inferred": True, "comment": "源自 e22；⑤序判仅自环→forward+inferred；评价人员只能对自己的评价结果进行修改；traits=audit 因评价结果留痕"},
    )

    # t17: 对评价进行统计（结果已提交→结果已提交，自环）
    m.add_trans(
        tid="t17", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果已提交", action="对评价进行统计", role="统计人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["评价统计表生成；报名记录状态保持结果已提交"],
        traits=["audit"], direction="forward", priority="P1",
        source_ref="19.1 报告编制和结果通知",
        note={"inferred": True, "comment": "源自 e23；⑤序判仅自环→forward+inferred；评价统计表生成留痕"},
    )

    # t18: 编制结果报告（结果已提交→报告/证书审核中）
    m.add_trans(
        tid="t18", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变为报告/证书审核中；同时项目状态变为报告审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知",
        note={"comment": "源自 e24；③序判frm先于to；联动 e25/t04 使 E-XM 报名中→报告审核中"},
    )

    # t19: 技术主管审核报告（报告/证书审核中→报告/证书审核中，自环）
    m.add_trans(
        tid="t19", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="技术主管审核报告", role="技术主管",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["技术主管审核报告完成；报名记录状态保持报告/证书审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知",
        note={"inferred": True, "comment": "源自 e26；⑤序判仅自环→forward+inferred；技术主管审核留痕"},
    )

    # t20: 报告、结果通知单授权签字人批准（报告/证书审核中→报告/证书审核中，自环）
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中",
        action="报告、结果通知单授权签字人批准", role="授权签字人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="技术主管审核报告已完成", ptype="event_ref"),
        ],
        expected_results=["授权签字人批准报告/结果通知单；报名记录状态保持报告/证书审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知",
        note={"inferred": True, "comment": "源自 e27；⑤序判仅自环→forward+inferred；授权签字人批准留痕；event_ref 指向 t19 完成"},
    )

    # t21: 证书实验室负责人批准（报告/证书审核中→报告/证书审核中，自环）
    m.add_trans(
        tid="t21", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="证书实验室负责人批准", role="实验室负责人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="授权签字人批准已完成", ptype="event_ref"),
        ],
        expected_results=["实验室负责人批准证书；报名记录状态保持报告/证书审核中"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知",
        note={"inferred": True, "comment": "源自 e28；⑤序判仅自环→forward+inferred；实验室负责人批准留痕；event_ref 指向 t20 完成"},
    )

    # t22: 发放结果报告和证书（报告/证书审核中→报告/证书已发布）
    m.add_trans(
        tid="t22", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="实验室负责人批准证书已完成", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书已发布；通过短信通知参加者'结果通知单已发布'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 报告编制和结果通知；20.5.3.2 操作节点增加用户短信通知",
        note={"comment": "源自 e29；③序判frm先于to；event_ref 指向 t21 完成；短信通知落入 BR"},
    )

    # ---- E-JFTZ/缴费通知单状态 ----
    # t23: 报名（创建转换，能力验证分支）
    m.add_trans(
        tid="t23", entity="E-JFTZ", dimension="缴费通知单状态",
        frm=None, to="未发送", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["缴费通知单记录创建，状态为未发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e05；⓪序判frm=None；与 t09 同 action，承担 E-JFTZ 维度"},
    )

    # t24: 受理用户测量审核报名（创建转换，测量审核分支）
    m.add_trans(
        tid="t24", entity="E-JFTZ", dimension="缴费通知单状态",
        frm=None, to="未发送", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["缴费通知单记录创建，状态为未发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 项目准备阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e33；⓪序判frm=None；与 t03/t10 同 action"},
    )

    # t25: 报名审核（未发送→已发送）
    m.add_trans(
        tid="t25", entity="E-JFTZ", dimension="缴费通知单状态",
        frm="未发送", to="已发送", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="缴费通知单处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-JFTZ", "缴费通知单状态", "未发送")),
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["缴费通知单状态变为已发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"comment": "源自 e10；③序判frm先于to；与 t11/t12 同 action，承担 E-JFTZ 维度"},
    )

    # ---- E-FY/费用状态 ----
    # t26: 报名（创建转换，能力验证分支）
    m.add_trans(
        tid="t26", entity="E-FY", dimension="费用状态",
        frm=None, to="待缴费", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["费用记录创建，状态为待缴费"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e06；⓪序判frm=None；与 t09 同 action，承担 E-FY 维度"},
    )

    # t27: 受理用户测量审核报名（创建转换，测量审核分支）
    m.add_trans(
        tid="t27", entity="E-FY", dimension="费用状态",
        frm=None, to="待缴费", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["费用记录创建，状态为待缴费"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 项目准备阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e34；⓪序判frm=None；与 t03/t10 同 action"},
    )

    # t28: 缴费（待缴费→已缴费）
    m.add_trans(
        tid="t28", entity="E-FY", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "待缴费")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["费用状态变为已缴费；支持多次付款（不对付款金额进行校验限制）；同时样品状态变为待核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段；20.5.2.1 已报名项目增加多次付款功能",
        note={"comment": "源自 e12；③序判frm先于to；联动 e11 使 E-YP 无→待核查；多次付款通过 E-CW 上传付款单操作承载"},
    )

    # ---- E-FP/发票状态 ----
    # t29: 报名（创建转换，能力验证分支）
    m.add_trans(
        tid="t29", entity="E-FP", dimension="发票状态",
        frm=None, to="待开票", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["发票记录创建，状态为待开票"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e07；⓪序判frm=None；与 t09 同 action，承担 E-FP 维度"},
    )

    # t30: 受理用户测量审核报名（创建转换，测量审核分支）
    m.add_trans(
        tid="t30", entity="E-FP", dimension="发票状态",
        frm=None, to="待开票", action="受理用户测量审核报名", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["发票记录创建，状态为待开票"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 项目准备阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e35；⓪序判frm=None；与 t03/t10 同 action"},
    )

    # t31: 发票开具（待开票→已开票）
    m.add_trans(
        tid="t31", entity="E-FP", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务管理人员",
        preconditions=[
            precond(text="发票处于待开票状态", ptype="state_ref",
                    ref=state_ref("E-FP", "发票状态", "待开票")),
        ],
        expected_results=["发票状态变为已开票；支持多次分批上传发票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段；20.10.2.2 修改发票上传功能使其支持多次分批上传",
        note={"comment": "源自 e13；③序判frm先于to；多次分批上传通过 E-FP 发票上传操作承载"},
    )

    # ---- E-YP/样品状态 ----
    # t32: 缴费（创建转换，能力验证分支——缴费触发样品创建）
    m.add_trans(
        tid="t32", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "待缴费")),
        ],
        expected_results=["样品记录创建，状态为待核查"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e11；⓪序判frm=None；与 t28 同 action，承担 E-YP 维度；能力验证项目由缴费触发样品创建"},
    )

    # t33: 样品领用登记（创建转换，测量审核分支）
    m.add_trans(
        tid="t33", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="样品领用登记", role="样品管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["样品记录创建，状态为待核查"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e36；⓪序判frm=None；测量审核项目由样品管理员领用登记触发样品创建"},
    )

    # t34: 样品核查（待核查→待发样，结果差异型分支）
    m.add_trans(
        tid="t34", entity="E-YP", dimension="样品状态",
        frm="待核查", to="待发样", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
        ],
        expected_results=[
            "若样品核查结果=已核查，则样品状态变为已核查",
            "若样品核查结果=待发样，则样品状态变为待发样",
        ],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段；19.2 实施阶段",
        note={"branch_dimension": "样品核查结果", "comment": "源自 e16；③序判frm先于to；结果差异型分支，共用一条+'若'句式；§19.1 流程表'样品核查'行取值'已核查、待发样'"},
    )

    # t35: 样品发放,作业指导书发送（待发样→已发样）
    m.add_trans(
        tid="t35", entity="E-YP", dimension="样品状态",
        frm="待发样", to="已发样", action="样品发放,作业指导书发送", role="样品管理员",
        preconditions=[
            precond(text="样品处于待发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待发样")),
        ],
        expected_results=["样品状态变为已发样；通过短信通知参加者'样品已发出'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1 实施阶段；20.5.3.2 操作节点增加用户短信通知",
        note={"comment": "源自 e17；③序判frm先于to；短信通知落入 BR"},
    )

    # t36: 参加者测试与结果提交（已发样→已还样，结果差异型分支）
    m.add_trans(
        tid="t36", entity="E-YP", dimension="样品状态",
        frm="已发样", to="已还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已发样")),
        ],
        expected_results=[
            "若参加者测试样品状态=已还样，则样品状态变为已还样",
            "若参加者测试样品状态=待核查，则样品状态变为待核查",
            "若参加者测试样品状态=无需还样，则样品状态变为无需还样",
        ],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1 实施阶段",
        note={"branch_dimension": "参加者测试样品状态", "comment": "源自 e19；③序判frm先于to；结果差异型分支；§19.1 流程表'参加者测试与结果提交'行取值'已还样、待核查/无需还样'"},
    )

    # ---- E-ZYDS/作业指导书状态 ----
    # t37: 作业指导书编制（创建转换）
    m.add_trans(
        tid="t37", entity="E-ZYDS", dimension="作业指导书状态",
        frm=None, to="待审核", action="作业指导书编制", role="策划人员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["作业指导书记录创建，状态为待审核"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2 实施阶段",
        note={"branch_dimension": "项目类型", "comment": "源自 e37；⓪序判frm=None；作业指导书仅测量审核项目涉及"},
    )

    # t38: 作业指导书审核通过（待审核→已审核）
    m.add_trans(
        tid="t38", entity="E-ZYDS", dimension="作业指导书状态",
        frm="待审核", to="已审核", action="作业指导书审核通过", role="技术主管",
        preconditions=[
            precond(text="作业指导书处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-ZYDS", "作业指导书状态", "待审核")),
        ],
        expected_results=["作业指导书状态变为已审核"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.2 实施阶段",
        note={"comment": "源自 e38；③序判frm先于to；技术主管审核留痕"},
    )

    # t39: 作业指导书退回（待审核→退回）
    m.add_trans(
        tid="t39", entity="E-ZYDS", dimension="作业指导书状态",
        frm="待审核", to="退回", action="作业指导书退回", role="技术主管",
        preconditions=[
            precond(text="作业指导书处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-ZYDS", "作业指导书状态", "待审核")),
        ],
        expected_results=["作业指导书状态变为退回"],
        traits=["rollback", "audit"], direction="backward", priority="P1",
        source_ref="19.2 实施阶段",
        note={"comment": "源自 e39；①序判'退回'→backward；技术主管审核留痕"},
    )

    # t40: 作业指导书重新提交（退回→待审核）
    m.add_trans(
        tid="t40", entity="E-ZYDS", dimension="作业指导书状态",
        frm="退回", to="待审核", action="作业指导书重新提交", role="策划人员",
        preconditions=[
            precond(text="作业指导书处于退回状态", ptype="state_ref",
                    ref=state_ref("E-ZYDS", "作业指导书状态", "退回")),
        ],
        expected_results=["作业指导书状态变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.2 实施阶段",
        note={"comment": "源自 e40；③序判frm先于to；'退回'非侧挂状态（§19.2 明确为退回流程），按③序判 forward"},
    )

    # ---- E-LAB/实验室状态 ----
    # t41: 实验室新增（创建转换）
    m.add_trans(
        tid="t41", entity="E-LAB", dimension="实验室状态",
        frm=None, to="待审核", action="实验室新增", role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室记录创建，状态为待审核；机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1 实验室信息；20.4.1.1 实验室列表与查询",
        note={"comment": "源自 e41；⓪序判frm=None；op 回填：新增实验室"},
    )

    # t42: 实验室审核通过（待审核→启用）
    m.add_trans(
        tid="t42", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核通过", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
        ],
        expected_results=["实验室状态变为启用；为当前数据生成数据快照记录"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2 实验室审核",
        note={"comment": "源自 e42；③序判frm先于to；审核通过生成快照留痕；op 回填：审核实验室"},
    )

    # t43: 实验室审核退回（待审核→已退回）
    m.add_trans(
        tid="t43", entity="E-LAB", dimension="实验室状态",
        frm="待审核", to="已退回", action="实验室审核退回", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "待审核")),
            precond(text="必须填写审核意见", ptype="constraint", note={"comment": "§20.4.1.2 审核结果为退回修改时，必须填写'审核意见'"}),
        ],
        expected_results=["实验室状态变为已退回"],
        traits=["rollback", "audit"], direction="backward", priority="P1",
        source_ref="20.4.1.2 实验室审核",
        note={"comment": "源自 e43；①序判'退回'→backward；§20.4.1.2 退回修改必须填写审核意见"},
    )

    # t44: 实验室修改后重新提交（已退回→待审核）
    m.add_trans(
        tid="t44", entity="E-LAB", dimension="实验室状态",
        frm="已退回", to="待审核", action="实验室修改后重新提交", role="能力验证参加者",
        preconditions=[
            precond(text="实验室处于已退回状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "已退回")),
        ],
        expected_results=["实验室状态变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3 实验室修改",
        note={"comment": "源自 e44；③序判frm先于to；'已退回'非侧挂状态，按③序判 forward；op 回填：修改实验室"},
    )

    # t45: 实验室停用（启用→停用）
    m.add_trans(
        tid="t45", entity="E-LAB", dimension="实验室状态",
        frm="启用", to="停用", action="实验室停用", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变为停用；列表刷新"],
        traits=[], direction="lateral", priority="P2",
        source_ref="20.4.1.1 实验室列表与查询",
        note={"comment": "源自 e45；①序判'停用'→lateral；'停用'为侧挂状态（暂停语义）"},
    )

    # t46: 实验室启用（停用→启用）
    m.add_trans(
        tid="t46", entity="E-LAB", dimension="实验室状态",
        frm="停用", to="启用", action="实验室启用", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-LAB", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变为启用；列表刷新"],
        traits=[], direction="resume", priority="P2",
        source_ref="20.4.1.1 实验室列表与查询",
        note={"comment": "源自 e46；②序判frm为侧挂→resume；'停用'为侧挂状态"},
    )

    # ---- E-BZK/标准库状态 ----
    # t47: 标准库新增（创建转换）
    m.add_trans(
        tid="t47", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="标准库新增", role="系统管理人员",
        preconditions=[],
        expected_results=["标准库记录创建，状态为启用；标准库编号/名称/状态必填"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2 新增标准库",
        note={"comment": "源自 e47；⓪序判frm=None；op 回填：新增标准库"},
    )

    # t48: 标准库停用（启用→停用）
    m.add_trans(
        tid="t48", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="标准库停用", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态变为停用；停用的标准库在项目创建等环节不可被选择"],
        traits=[], direction="lateral", priority="P2",
        source_ref="20.4.2.5 停用/启用标准库",
        note={"comment": "源自 e48；①序判'停用'→lateral；'停用'为侧挂状态"},
    )

    # t49: 标准库启用（停用→启用）
    m.add_trans(
        tid="t49", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="标准库启用", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态变为启用；列表刷新"],
        traits=[], direction="resume", priority="P2",
        source_ref="20.4.2.5 停用/启用标准库",
        note={"comment": "源自 e49；②序判frm为侧挂→resume；'停用'为侧挂状态"},
    )

    # ---- E-PJ/评价状态 ----
    # t50: 评价组长完善测试项目及评价细则（创建转换）
    m.add_trans(
        tid="t50", entity="E-PJ", dimension="评价状态",
        frm=None, to="评价中", action="评价组长完善测试项目及评价细则", role="评价组长",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["评价记录创建，状态为评价中；评价组长编辑完善评价项目及评价细则"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.1 测试项目、评价细则完善",
        note={"comment": "源自 e50；⓪序判frm=None；op 回填：完善评价细则；§20.7.1 首段'第一个被选择的评价人员默认做为评价组长'"},
    )

    # t51: 评价人员评价（评价中→评价中，自环）
    m.add_trans(
        tid="t51", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价中", action="评价人员评价", role="评价人员",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价人员对自己的评价结果进行评价；只显示自己的评价结果；不能查看和修改其他评价人员的评价结果"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.2 协同评价",
        note={"inferred": True, "comment": "源自 e51；⑤序判仅自环→forward+inferred；op 回填：评价；协同评价限制：评价人员只能修改自己的评价结果"},
    )

    # t52: 评价组长退回修改（评价中→评价中，自环）
    m.add_trans(
        tid="t52", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价中", action="评价组长退回修改", role="评价组长",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["当前评价结果保存为历史结果；开启下一轮评价"],
        traits=["rollback"], direction="forward", priority="P1",
        source_ref="20.7.1.3 评价确认",
        note={"inferred": True, "comment": "源自 e52；⑤序判仅自环→forward+inferred；op 回填：退回修改；'退回修改'在评价场景下不改变状态，开启下一轮评价"},
    )

    # t53: 评价组长结果确认（评价中→评价关闭）
    m.add_trans(
        tid="t53", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价关闭", action="评价组长结果确认", role="评价组长",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变为评价关闭；评价结果正式提交为项目的最终评价结果；及格分录入后跟随其他结果一起记录"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3 评价确认",
        note={"comment": "源自 e53；③序判frm先于to；op 回填：结果确认；评价结果留痕"},
    )

    # ---- E-TASK/任务状态 ----
    # t54: 审核任务创建（创建转换）
    m.add_trans(
        tid="t54", entity="E-TASK", dimension="任务状态",
        frm=None, to="待审核", action="审核任务创建", role="策划人员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["审核任务记录创建，状态为待审核；系统发送短信通知相关负责人'您有一个新的xxx审核任务，请及时处理'"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.9.1.1 测量审核结果通知单审核流程优化；20.9.1.3 增加任务提醒",
        note={"comment": "源自 e54；⓪序判frm=None；流程处理人审批顺序为提交申请时签字人的选择顺序；短信通知落入 BR"},
    )

    # t55: 审核通过（待审核→审核通过，路径分歧：同意分支）
    m.add_trans(
        tid="t55", entity="E-TASK", dimension="任务状态",
        frm="待审核", to="审核通过", action="审核通过",
        role=["技术主管", "授权签字人", "实验室负责人"],
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务状态", "待审核")),
            precond(text="批量审核结果=同意", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态变为审核通过"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.9.1.4 任务批量处理",
        note={"branch_dimension": "批量审核结果", "comment": "源自 e55；③序判frm先于to；路径分歧：同意分支，Step 2 value=同意 指向本条；多角色 collaborative（技术主管/授权签字人/实验室负责人按审批顺序）"},
    )

    # t56: 审核退回（待审核→审核退回，路径分歧：退回分支）
    m.add_trans(
        tid="t56", entity="E-TASK", dimension="任务状态",
        frm="待审核", to="审核退回", action="审核退回",
        role=["技术主管", "授权签字人", "实验室负责人"],
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务状态", "待审核")),
            precond(text="批量审核结果=退回", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态变为审核退回"],
        traits=["branch", "rollback", "audit"], direction="backward", priority="P1",
        source_ref="20.9.1.4 任务批量处理",
        note={"branch_dimension": "批量审核结果", "comment": "源自 e56；①序判'退回'→backward；路径分歧：退回分支，Step 2 value=退回 指向本条"},
    )

    # ---- E-CW/缴费记录状态 ----
    # t57: 上传付款单（创建转换）
    m.add_trans(
        tid="t57", entity="E-CW", dimension="缴费记录状态",
        frm=None, to="待退款", action="上传付款单", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["缴费记录创建，状态为待退款；支持多次付款（不对付款金额进行校验限制）"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.5.2.1 已报名项目增加多次付款功能",
        note={"comment": "源自 e57；⓪序判frm=None；op 回填：上传付款单；多次付款通过本转换多次触发实现"},
    )

    # t58: 缴费单退款（待退款→已退款）
    m.add_trans(
        tid="t58", entity="E-CW", dimension="缴费记录状态",
        frm="待退款", to="已退款", action="缴费单退款", role="财务管理人员",
        preconditions=[
            precond(text="缴费记录处于待退款状态", ptype="state_ref",
                    ref=state_ref("E-CW", "缴费记录状态", "待退款")),
            precond(text="退款金额不能大于当前缴费金额", ptype="constraint", note={"comment": "§20.10.2.3 退款金额必填，不能为大于当前缴费金额"}),
        ],
        expected_results=["缴费记录状态变为已退款；更新'项目费用'为实际付款金额；退款金额累加处理"],
        traits=["rollback", "audit"], direction="forward", priority="P1",
        source_ref="20.10.2.3 缴费单退款",
        note={"comment": "源自 e58；③序判frm先于to；op 回填：退款；退款后更新项目费用；退款金额红色字体且大于0时显示"},
    )

    # ============================================================
    # Step 4 约束（invalid / XC / BR）
    # ============================================================
    # ---- 4.1 invalid → m.add_invalid() ----
    # 文档明确禁止的状态转换
    m.add_invalid(
        iid="i01", entity="E-LAB", frm="停用", to="已退回",
        reason="§20.4.1.1 实验室列表操作列：停用状态仅显示'启用'按钮，不存在停用→已退回的转换路径",
        source_ref="20.4.1.1 实验室列表与查询",
    )
    m.add_invalid(
        iid="i02", entity="E-LAB", frm="已退回", to="启用",
        reason="§20.4.1.1 实验室列表操作列：已退回状态无直接'启用'按钮，必须经修改后重新提交至待审核，再审核通过",
        source_ref="20.4.1.1 实验室列表与查询；20.4.1.2 实验室审核",
    )
    m.add_invalid(
        iid="i03", entity="E-LAB", frm="停用", to="待审核",
        reason="§20.4.1.1 实验室列表操作列：停用状态仅显示'启用'按钮，不直接进入待审核",
        source_ref="20.4.1.1 实验室列表与查询",
    )
    m.add_invalid(
        iid="i04", entity="E-BZK", frm="停用", to="停用",
        reason="§20.4.2.5 停用/启用标准库：停用状态仅显示'启用'按钮，不可重复停用",
        source_ref="20.4.2.5 停用/启用标准库",
    )

    # ---- 4.2 XC → m.add_xc() ----
    # XC1：能力验证预通知门禁——预通知须待确认方样品发放（镜像 XC，由框架自动补齐）
    m.add_xc(
        xid="x01",
        source_entity="E-YP", source_transition="t35",
        source_state="待发样",
        target_entity="E-YTZ", target_dimension="预通知状态",
        target_condition="待确认或已确认",
        desc="样品发放前，预通知须处于待确认或已确认状态",
        source_ref="19.1 实施阶段",
        target_transition="t08",
        xc_source="镜像",
    )

    # XC2：缴费门禁——能力验证预通知须报名成功（镜像）
    m.add_xc(
        xid="x02",
        source_entity="E-BMJL", source_transition="t13",
        source_state="报名成功",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名成功",
        desc="能力验证预通知前，报名记录须处于报名成功状态",
        source_ref="19.1 实施阶段",
        target_transition="t13",
        xc_source="镜像",
    )

    # XC3：缴费门禁——缴费须费用处于待缴费状态且报名成功（4.5判，落 BR b08）
    m.add_xc(
        xid="x03",
        source_entity="E-FY", source_transition="t28",
        source_state="待缴费",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名成功",
        desc="缴费前，报名记录须处于报名成功状态（约束承载 BR b08）",
        source_ref="19.1 实施阶段",
        target_transition="t28",
        xc_source="4.5判",
    )

    # XC4：联动——报名审核通过使报名记录状态变为报名成功，触发后续预通知门禁（联动）
    m.add_xc(
        xid="x04",
        source_entity="E-BMJL", source_transition="t12",
        source_state="报名成功",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名成功",
        desc="报名审核通过→报名记录状态变更为报名成功，开启预通知阶段",
        source_ref="19.1 实施阶段",
        target_transition="t13",
        xc_source="联动",
    )

    # XC5：联动——参加者测试与结果提交使报名记录状态变为结果已提交，触发评价阶段（联动）
    m.add_xc(
        xid="x05",
        source_entity="E-BMJL", source_transition="t14",
        source_state="结果已提交",
        target_entity="E-PJ", target_dimension="评价状态",
        target_condition="评价中",
        desc="参加者结果提交→报名记录状态变为结果已提交，开启评价阶段",
        source_ref="19.1 报告编制和结果通知；20.7.1.1",
        target_transition="t50",
        xc_source="联动",
    )

    # XC6：4.5判——审核任务创建须报名记录处于报告/证书审核中（落 BR b15）
    m.add_xc(
        xid="x06",
        source_entity="E-TASK", source_transition="t54",
        source_state="待审核",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报告/证书审核中",
        desc="审核任务创建前，报名记录须处于报告/证书审核中状态（约束承载 BR b15）",
        source_ref="20.9.1.1 测量审核结果通知单审核流程优化",
        target_transition="t54",
        xc_source="4.5判",
    )

    # XC7：分支差异——能力验证分支禁止走测量审核创建路径
    m.add_xc(
        xid="x07",
        source_entity="E-XM", source_transition="t01",
        source_state="待开始",
        target_entity="E-XM", target_dimension="项目状态",
        target_condition="项目类型=能力验证",
        desc="能力验证分支项目类型=能力验证时，项目状态经设计方案编制进入待开始；不可走测量审核路径",
        source_ref="19.1 项目准备阶段；19.2 项目准备阶段",
        target_transition="t01",
        xc_source="分支差异",
    )

    # ---- 4.3 BR → m.add_br() ----
    # BR1：通知公告15天标识（field_constraint）
    m.add_br(
        bid="b01", category="validation", desc="15天内发布的通知在内容前标注'new'标识；超过15天后此标识自动隐藏",
        entities_involved=["E-TZGG"], source_ref="20.2.1 通知公告",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'15天内'（取值范围）；category判有效性校验（默认）"},
    )

    # BR2：实验室证明文件提示
    m.add_br(
        bid="b02", category="display",
        desc="实验室证明文件表单下增加提示文字：请上传营业执照或其他证书材料",
        entities_involved=["E-LAB"], source_ref="20.3.1 实验室信息",
        signal_type="display",
        note={"comment": "signal_type命中'提示文字'（display）；category判信息展示"},
    )

    # BR3：实验室审核退回必须填写审核意见
    m.add_br(
        bid="b03", category="validation",
        desc="实验室审核结果为退回修改时，必须填写审核意见",
        entities_involved=["E-LAB"], source_ref="20.4.1.2 实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'必须'（restrictive）；category判有效性校验（默认）"},
    )

    # BR4：实验室审核通过生成快照
    m.add_br(
        bid="b04", category="computation",
        desc="实验室审核结果为通过时，为当前数据生成该数据的快照记录",
        entities_involved=["E-LAB"], source_ref="20.4.1.2 实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'为通过时'（restrictive，条件措辞）；category判计算衍生（快照生成）"},
    )

    # BR5：实验室修改后重新提交须经审核通过后方可用于项目报名
    m.add_br(
        bid="b05", category="validation",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-LAB", "E-BMJL"], source_ref="20.3.1 实验室信息",
        signal_type="restrictive",
        note={"comment": "signal_type命中'需经'（restrictive）；category判有效性校验；constrained_entity=E-LAB（被门禁的实体）"},
    )

    # BR6：标准库项目创建不可选择停用项
    m.add_br(
        bid="b06", category="validation",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"], source_ref="20.4.2.5 停用/启用标准库",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不可'（restrictive）；category判有效性校验；constrained_entity=E-BZK（被门禁的实体）"},
    )

    # BR7：测试项含子项不允许删除
    m.add_br(
        bid="b07", category="validation",
        desc="含有子项的测试项记录不允许删除",
        entities_involved=["E-CSS"], source_ref="20.4.2.10 删除测试项；20.4.3.4 删除测试项",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不允许'（restrictive）；prohibit_keywords 含'不允许删除含有子项的记录'；category判有效性校验"},
    )

    # BR8：缴费须报名成功（ XC3 联动 BR ）
    m.add_br(
        bid="b08", category="validation",
        desc="缴费前报名记录须处于报名成功状态",
        entities_involved=["E-BMJL", "E-FY"], source_ref="19.1 实施阶段",
        signal_type="restrictive",
        note={"comment": "signal_type命中'须'（restrictive）；constrained_entity=E-FY（缴费被门禁）；承载 XC x03"},
    )

    # BR9：未结束的项目可以进行消息发送
    m.add_br(
        bid="b09", category="authorization",
        desc="未结束的项目可以进行消息发送",
        entities_involved=["E-XM", "E-MSG"], source_ref="20.5.1.4 优化消息发送功能；20.6.1.2",
        signal_type="restrictive",
        note={"role": "项目管理员", "comment": "signal_type命中'可以'（restrictive 反向措辞）；prohibit_keywords 含'不可以进行消息发送'；category判访问控制；constrained_entity=E-MSG"},
    )

    # BR10：消息发送接收人1和接收人2不能同时为空
    m.add_br(
        bid="b10", category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-MSG"], source_ref="20.5.1.4 优化消息发送功能；20.6.1.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'（restrictive）；category判有效性校验"},
    )

    # BR11：项目新增表单技术主管/实验室负责人/授权签字人默认填充
    m.add_br(
        bid="b11", category="validation",
        desc="项目新增表单中技术主管/实验室负责人/授权签字人字段，候选人唯一时默认填充为备选值",
        entities_involved=["E-XM"], source_ref="20.5.1.6 默认填充技术主管、实验室负责人、授权签字人；20.6.1.4",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'默认填充'（默认值）；category判有效性校验"},
    )

    # BR12：项目新增表单新增监督员字段
    m.add_br(
        bid="b12", category="validation",
        desc="项目新增表单项目人员信息区域最后一行增加监督员字段（下拉框可以为空）；导出项目通知书时填充到对应位置",
        entities_involved=["E-XM"], source_ref="20.5.1.5 项目新增表单增加监督员；20.6.1.3",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'字段'（field）；category判有效性校验"},
    )

    # BR13：批量处理上传状态显示判定
    m.add_br(
        bid="b13", category="validation",
        desc="批量处理页面操作列'上传结果通知单/上传证书'按钮根据处理内容和是否已上传两个条件判定是否需要显示",
        entities_involved=["E-BMJL"], source_ref="20.5.1.3 项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'根据...判定'（restrictive，条件措辞）；category判有效性校验；branch_dimension=批量处理内容（分支承载）", "branch_dimension": "批量处理内容"},
    )

    # BR14：批量处理选择列限制
    m.add_br(
        bid="b14", category="validation",
        desc="批量处理页面选择列只有已上传对应文件且未提交审核的记录才可以被选定",
        entities_involved=["E-BMJL"], source_ref="20.5.1.3 项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只有...才'（restrictive）；category判有效性校验"},
    )

    # BR15：审核任务创建须报名记录处于报告/证书审核中（XC6 联动 BR）
    m.add_br(
        bid="b15", category="validation",
        desc="审核任务创建前报名记录须处于报告/证书审核中状态",
        entities_involved=["E-TASK", "E-BMJL"], source_ref="20.9.1.1 测量审核结果通知单审核流程优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'须'（restrictive）；constrained_entity=E-TASK；承载 XC x06"},
    )

    # BR16：审核任务创建短信通知
    m.add_br(
        bid="b16", category="notification",
        desc="用户通过表单或审核一个已存在的任务生成新的审核任务时，系统发送短信通知相关负责人；短信内容'您有一个新的xxx审核任务，请及时处理'",
        entities_involved=["E-TASK"], source_ref="20.9.1.3 增加任务提醒",
        signal_type="restrictive",
        note={"comment": "signal_type命中'生成新的审核任务时'（restrictive，时间措辞）；category判通知触发"},
    )

    # BR17：批量审核同意/退回
    m.add_br(
        bid="b17", category="validation",
        desc="批量审核表单审核结果下拉选择框选项为：同意、退回",
        entities_involved=["E-TASK"], source_ref="20.9.1.4 任务批量处理",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'选项'（取值范围）；category判有效性校验；branch_dimension=批量审核结果（分支承载）", "branch_dimension": "批量审核结果"},
    )

    # BR18：批量审核须选择记录
    m.add_br(
        bid="b18", category="validation",
        desc="批量审核时如没有选择记录，将提示用户选择记录信息",
        entities_involved=["E-TASK"], source_ref="20.9.1.4 任务批量处理",
        signal_type="restrictive",
        note={"comment": "signal_type命中'如没有...将提示'（restrictive，条件措辞）；category判有效性校验"},
    )

    # BR19：自定义流程预设4个以内
    m.add_br(
        bid="b19", category="validation",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程",
        entities_involved=["E-TASK"], source_ref="20.9.1.6 增加自定义流程",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'4个以内'（取值范围）；category判有效性校验"},
    )

    # BR20：电子签章位置信息自动代入
    m.add_br(
        bid="b20", category="computation",
        desc="系统内增加电子签章位置信息，当进行签章操作时自动代入此位置信息减少手动调整操作",
        entities_involved=["E-TASK"], source_ref="20.9.1.2 预置签章位置信息",
        signal_type="restrictive",
        note={"comment": "signal_type命中'自动代入'（restrictive，自动行为措辞）；category判计算衍生（自动代入）"},
    )

    # BR21：审批流程列表创建时间查询
    m.add_br(
        bid="b21", category="display",
        desc="审批流程列表查询区域'任务类型'查询参数后增加'创建时间'查询参数",
        entities_involved=["E-TASK"], source_ref="20.9.1.5 审批流程列表导出",
        signal_type="display",
        note={"comment": "signal_type命中'增加'（display）；category判信息展示"},
    )

    # BR22：审批流程列表显示效果
    m.add_br(
        bid="b22", category="display",
        desc="审核流程详情页完整展示审核流程，并用不同的颜色对各个状态的节点进行标记",
        entities_involved=["E-TASK"], source_ref="20.9.1.7 优化流程信息展示效果",
        signal_type="display",
        note={"comment": "signal_type命中'展示'（display）；category判信息展示"},
    )

    # BR23：证书到期前30天邮件提醒（系统行为，落点判定第③条出口）
    m.add_br(
        bid="b23", category="notification",
        desc="系统每天上午9点对系统中的证书信息进行查询，距到期时间等于30天时通过邮件方式对用户进行提醒并抄送项目管理员；提醒标题'证书到期提醒'；提醒内容'您证书编号为xxxx的证书将于2025-01-01到期，请知悉'",
        entities_involved=["E-FP", "E-BMJL"], source_ref="20.5.2.3 增加证书到期前30天提醒功能；20.6.2.3",
        signal_type="restrictive",
        note={"comment": "signal_type命中'每天上午9点'（restrictive，时间措辞）；category判通知触发；无状态落点，不入台账/operations"},
    )

    # BR24：报名审核通过短信通知
    m.add_br(
        bid="b24", category="notification",
        desc="报名审核通过后使用短信方式通知用户'您xxx项目的报名信息审核通过，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2 操作节点增加用户短信通知；20.6.3.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'审核通过后'（restrictive，时间措辞）；category判通知触发"},
    )

    # BR25：报名审核退回短信通知
    m.add_br(
        bid="b25", category="notification",
        desc="报名审核退回后使用短信方式通知用户'您xxx项目的报名信息审核未通过，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2 操作节点增加用户短信通知；20.6.3.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'退回修改'（restrictive）；category判通知触发"},
    )

    # BR26：发样通知短信
    m.add_br(
        bid="b26", category="notification",
        desc="样品发出后使用短信方式通知用户'您xxxx项目的样品已发出，请知悉'",
        entities_involved=["E-YP"], source_ref="20.5.3.2 操作节点增加用户短信通知；20.6.3.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'已发出'（restrictive，状态变化措辞）；category判通知触发"},
    )

    # BR27：测试结果审核通过短信
    m.add_br(
        bid="b27", category="notification",
        desc="测试结果审核通过后使用短信方式通知用户'您xxxx项目的测试报告审核通过，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2 操作节点增加用户短信通知；20.6.3.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'审核通过'（restrictive）；category判通知触发"},
    )

    # BR28：测试结果审核退回短信
    m.add_br(
        bid="b28", category="notification",
        desc="测试结果审核退回后使用短信方式通知用户'您xxxx项目测试报告审核未通过，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2 操作节点增加用户短信通知；20.6.3.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'审核未通过'（restrictive）；category判通知触发"},
    )

    # BR29：结果通知单发布短信
    m.add_br(
        bid="b29", category="notification",
        desc="结果通知单发布后使用短信方式通知用户'您xxx项目的结果通知单已发布，请知悉'",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2 操作节点增加用户短信通知；20.6.3.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'已发布'（restrictive，状态变化措辞）；category判通知触发"},
    )

    # BR30：多次付款不校验付款金额
    m.add_br(
        bid="b30", category="validation",
        desc="已报名项目付款支持多次操作，不对付款金额进行校验限制",
        entities_involved=["E-CW", "E-BMJL"], source_ref="20.5.2.1 已报名项目增加多次付款功能；20.6.2.1",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不对...校验限制'（restrictive，反向措辞）；category判有效性校验；constrained_entity=E-CW"},
    )

    # BR31：退款金额不能大于当前缴费金额
    m.add_br(
        bid="b31", category="validation",
        desc="缴费单退款时退款金额不能大于当前缴费金额；退款后更新'项目费用'为实际付款金额",
        entities_involved=["E-CW", "E-FK"], source_ref="20.10.2.3 缴费单退款",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能为大于'（restrictive）；prohibit_keywords 含'不能为大于当前缴费金额'；constrained_entity=E-FK；退款金额累加处理，红色字体且大于0时显示"},
    )

    # BR32：实际付款计算
    m.add_br(
        bid="b32", category="computation",
        desc="实际付款=付款金额-退款金额；退款金额使用红色字体且大于0时显示",
        entities_involved=["E-CW"], source_ref="20.10.2.3 缴费单退款",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'='（计算公式）；category判计算衍生；实际付款与退款金额为派生属性"},
    )

    # BR33：发票分批上传
    m.add_br(
        bid="b33", category="validation",
        desc="发票上传功能支持多次分批上传；发票上传后显示在发票列表，点击文件地址后的'x'可以移除文件（表单提交后生效）",
        entities_involved=["E-FP"], source_ref="20.10.2.2 修改发票上传功能使其支持多次分批上传",
        signal_type="restrictive",
        note={"comment": "signal_type命中'支持多次'（restrictive）；category判有效性校验"},
    )

    # BR34：财务备注修改
    m.add_br(
        bid="b34", category="validation",
        desc="项目列表增加'财务备注'列，操作列增加'修改备注'按钮，管理人员可以修改备注内容",
        entities_involved=["E-XM"], source_ref="20.10.2.1 项目列表增加财务备注字段",
        signal_type="display",
        note={"comment": "signal_type命中'增加'（display，信息展示）；category判信息展示；备注字段为可编辑属性"},
    )

    # BR35：数据看板历年/近三年维度
    m.add_br(
        bid="b35", category="display",
        desc="数据看板区域洞察报表右下角提供'历年'和'近三年'维度的专项统计功能；统计数据以弹窗的方式浮于页面中",
        entities_involved=["E-SJKB"], source_ref="20.8.2.1 数据看板",
        signal_type="display",
        note={"comment": "signal_type命中'提供'（display）；category判信息展示；branch_dimension=数据看板时间维度（分支承载）", "branch_dimension": "数据看板时间维度"},
    )

    # BR36：客户查询时间快速录入
    m.add_br(
        bid="b36", category="usability",
        desc="客户统计列表'录入时间'查询参数时间选择框前增加三个单选按钮：月度、季度、年度；月度点击设置时间范围为本月，季度为本季，年度为本年",
        entities_involved=["E-TJBB"], source_ref="20.8.6.1 优化客户统计列表查询参数时间参数快速录入",
        signal_type="usability",
        note={"comment": "signal_type命中'增加'（usability，易用功能）；category判易用功能；branch_dimension=客户查询时间快速录入（分支承载）", "branch_dimension": "客户查询时间快速录入"},
    )

    # BR37：客户查询实验室名称跳转
    m.add_br(
        bid="b37", category="usability",
        desc="客户查询'实验室名称'列增加跳转功能，点击此列可以跳转到报名信息统计页面查看此实验室报表的所有项目信息",
        entities_involved=["E-TJBB", "E-BMJL"], source_ref="20.8.6.1 优化客户统计列表查询参数时间参数快速录入",
        signal_type="usability",
        note={"comment": "signal_type命中'增加跳转功能'（usability）；category判易用功能"},
    )

    # BR38：缴费信息时间快速录入
    m.add_br(
        bid="b38", category="usability",
        desc="缴费信息查询'缴费时间'参数设置三个单选按钮：本月、本季、本年；点击设置后面时间选择组件时间范围",
        entities_involved=["E-YJ"], source_ref="20.10.1.1 缴费信息查询与管理",
        signal_type="usability",
        note={"comment": "signal_type命中'设置'（usability）；category判易用功能；branch_dimension=缴费时间快速录入（分支承载）", "branch_dimension": "缴费时间快速录入"},
    )

    # BR39：统计对比分组
    m.add_br(
        bid="b39", category="validation",
        desc="统计对比'分组'下拉列表必选，选项有年份、产品类型；对比参数下拉列表必选，可以选择多个参数",
        entities_involved=["E-TJBB"], source_ref="20.8.7.1 统计对比",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'必选'（必填）；category判有效性校验；branch_dimension=统计对比分组（分支承载）", "branch_dimension": "统计对比分组"},
    )

    # BR40：信息发送记录权限
    m.add_br(
        bid="b40", category="authorization",
        desc="信息发送记录仅系统管理员和项目管理员可以查看",
        entities_involved=["E-XX"], source_ref="20.4.4.1 信息发送记录",
        signal_type="restrictive",
        note={"role": "系统管理人员", "comment": "signal_type命中'仅'（restrictive，访问控制措辞）；category判访问控制；constrained_entity=E-XX"},
    )

    # BR41：评价人员仅评价自己的结果
    m.add_br(
        bid="b41", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"], source_ref="20.7.1.2 协同评价",
        signal_type="restrictive",
        note={"role": "评价人员", "comment": "signal_type命中'只能'（restrictive，访问控制措辞）；category判访问控制；constrained_entity=E-PJ；branch_dimension=评价人员角色（分支承载）", "branch_dimension": "评价人员角色"},
    )

    # BR42：评价组长可调整细则
    m.add_br(
        bid="b42", category="authorization",
        desc="评价组长可以在评价结果确认页面查看各评价人员的评价结果，并对最终结果进行确认",
        entities_involved=["E-PJ"], source_ref="20.7 项目评价",
        signal_type="restrictive",
        note={"role": "评价组长", "comment": "signal_type命中'可以'（restrictive 反向措辞）；category判访问控制；constrained_entity=E-PJ；branch_dimension=评价人员角色", "branch_dimension": "评价人员角色"},
    )

    # BR43：评价组长首位默认
    m.add_br(
        bid="b43", category="validation",
        desc="新建项目时第一个被选择的评价人员默认做为评价组长",
        entities_involved=["E-PJ", "E-XM"], source_ref="20.7 项目评价",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'默认'（默认值）；category判有效性校验；constrained_entity=E-PJ"},
    )

    # BR44：评价结果导出权限
    m.add_br(
        bid="b44", category="authorization",
        desc="评价人员点击项目列表操作列中的'导出'按钮可下载评价结果",
        entities_involved=["E-PJ"], source_ref="20.7.1.4 评价结果导出",
        signal_type="restrictive",
        note={"role": "评价人员", "comment": "signal_type命中'可'（restrictive 反向措辞）；category判访问控制"},
    )

    # BR45：评价细则调整标记
    m.add_br(
        bid="b45", category="display",
        desc="评价结果页面被标记为调整状态的评价细则将显示不同的背景颜色",
        entities_involved=["E-PJ"], source_ref="20.7.1.3 评价确认",
        signal_type="display",
        note={"comment": "signal_type命中'显示'（display）；category判信息展示"},
    )

    # BR46：成绩区间统计规则
    m.add_br(
        bid="b46", category="validation",
        desc="评价结果统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值",
        entities_involved=["E-PJ"], source_ref="20.7.1.3 评价确认",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'判断规则'（取值范围）；category判有效性校验"},
    )

    # BR47：历史数据导入
    m.add_br(
        bid="b47", category="computation",
        desc="对往年项目数据进行分析整理并导入到系统中为数据分析提供关键数据",
        entities_involved=["E-TJBB"], source_ref="20.11 其他",
        signal_type="restrictive",
        note={"comment": "signal_type命中'导入'（restrictive，导入操作）；category判计算衍生（数据迁移）"},
    )

    # BR48：关键操作留痕
    m.add_br(
        bid="b48", category="computation",
        desc="对关键操作进行留痕处理，系统自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志，确保所有操作均可追踪和复核",
        entities_involved=[], source_ref="20.11.1.2 安全性相关内容优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'自动记录'（restrictive，自动行为措辞）；category判计算衍生（审计日志生成）"},
    )

    # BR49：统一显示风格
    m.add_br(
        bid="b49", category="display",
        desc="统一系统的显示风格，消除系统中现有的风格差异；对不符合当前风格的页面进行调整，实现更加完整和统一的视觉体验",
        entities_involved=[], source_ref="20.11.1.3 系统UI风格优化",
        signal_type="display",
        note={"comment": "signal_type命中'显示风格'（display）；category判信息展示"},
    )

    # BR50：性能要求 - 在线用户数
    m.add_br(
        bid="b50", category="validation",
        desc="在网络和服务器正常运行的情况下，平台应支持至少300个同时在线用户数；并发100时每个页面响应时间不超过5秒；单次报名操作成功率应达到95%以上",
        entities_involved=[], source_ref="3.4 性能要求；21.3 性能要求",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'至少300'（取值范围）；category判有效性校验（默认）"},
    )

    # BR51：兼容性要求
    m.add_br(
        bid="b51", category="validation",
        desc="Web系统应兼容多个系统和浏览器使用，系统包含win7、win10及以上；浏览器应兼容Edge、chrome、火狐等主流浏览器",
        entities_involved=[], source_ref="3.5 兼容性要求；21.5 兼容性要求",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'兼容'（兼容性范围）；category判有效性校验"},
    )

    # BR52：等保二级安全要求
    m.add_br(
        bid="b52", category="validation",
        desc="能力验证服务平台的系统设计、开发、部署等应符合等保二级要求和网数中心应用系统设计开发安全管理规定",
        entities_involved=[], source_ref="3.3 安全要求；21.2 安全要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'应符合'（restrictive）；category判有效性校验"},
    )

    # BR53：数据加密
    m.add_br(
        bid="b53", category="validation",
        desc="对敏感数据进行加密存储，使用强加密标准（如AES）；使用TLS/SSL加密数据传输，确保数据在传输过程中的安全",
        entities_involved=[], source_ref="21.2.2 数据安全",
        signal_type="restrictive",
        note={"comment": "signal_type命中'使用'（restrictive，使用要求）；category判有效性校验"},
    )

    # BR54：数据备份
    m.add_br(
        bid="b54", category="computation",
        desc="定期备份数据，并确保可以迅速恢复，以防数据丢失或损坏",
        entities_involved=[], source_ref="21.2.2 数据安全",
        signal_type="restrictive",
        note={"comment": "signal_type命中'定期'（restrictive，时间措辞）；category判计算衍生（数据备份）"},
    )

    # BR55：个人信息保护
    m.add_br(
        bid="b55", category="validation",
        desc="仅收集完成业务所必需的最少个人信息；确保在收集和处理个人数据之前获得用户的明确同意",
        entities_involved=[], source_ref="21.2.3 个人信息保护；21.2.4 数据最小化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'仅'（restrictive，访问控制措辞）；category判有效性校验"},
    )

    # BR56：项目交付时间
    m.add_br(
        bid="b56", category="timing",
        desc="平台升级改造项目按照中心年度计划要求需要在2025年11月15日前完成相应的设计、开发、测试、部署、试运行等相关工作",
        entities_involved=[], source_ref="21.6 时间要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'2025年11月15日前'（restrictive，时间措辞）；category判时间/次数"},
    )

    # BR57：删除操作二次确认
    m.add_br(
        bid="b57", category="usability",
        desc="操作完成时有统一规范的提示信息，例如删除操作时系统提示警示框'您确认删除记录吗？操作不可恢复！'，用户点击确认后才执行删除操作",
        entities_involved=[], source_ref="3.6 可用性要求",
        signal_type="usability",
        note={"comment": "signal_type命中'提示信息'（usability，易用功能）；category判易用功能"},
    )

    # BR58：消息发送项目状态门禁
    m.add_br(
        bid="b58", category="validation",
        desc="消息发送时项目状态为'待开始'、'报名中'时右侧实验室列表为所有实验室，其他状态为报名实验室",
        entities_involved=["E-XM", "E-LAB", "E-MSG"], source_ref="20.5.1.4 优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'为'（restrictive，状态条件措辞）；category判有效性校验；constrained_entity=E-MSG"},
    )

    # BR59：接收人1不可直接编辑
    m.add_br(
        bid="b59", category="validation",
        desc="消息发送接收人1为数据列表，不可直接编辑，数据来源于右侧的实验室列表",
        entities_involved=["E-MSG", "E-LAB"], source_ref="20.5.1.4 优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不可'（restrictive）；prohibit_keywords 含'不可直接编辑'；constrained_entity=E-MSG"},
    )

    # BR60：批量处理上传按钮显示条件
    m.add_br(
        bid="b60", category="validation",
        desc="批量处理页面操作列'上传结果通知单/上传证书'按钮根据处理内容和是否已上传两个条件判定是否需要显示",
        entities_involved=["E-BMJL"], source_ref="20.5.1.3 项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'根据...判定'（restrictive，条件措辞）；constrained_entity=E-BMJL；branch_dimension=批量处理内容", "branch_dimension": "批量处理内容"},
    )

    # BR61：项目上报时间精确到月
    m.add_br(
        bid="b61", category="validation",
        desc="项目上报'报告时间'筛选条件时间范围选择框精确到月",
        entities_involved=["E-TJBB"], source_ref="20.8.9.1 项目上报",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'精确到月'（取值范围）；category判有效性校验"},
    )

    # BR62：业务上报统计多表头
    m.add_br(
        bid="b62", category="display",
        desc="业务上报统计列表采用多表头数据展示，一级表头：序号/认证项目/报告统计/客户统计/收入；二级表头：序号/认证项目/签发报告量/累计签发报告总量/新增客户/获新报告的老客户/现有客户总量；三级表头按年度对比",
        entities_involved=["E-TJBB"], source_ref="20.8.8.1 业务上报统计",
        signal_type="display",
        note={"comment": "signal_type命中'展示'（display）；category判信息展示"},
    )

    # BR63：能力验证计划发布报名状态门禁
    m.add_br(
        bid="b63", category="validation",
        desc="能力验证计划发布前项目须处于待开始状态",
        entities_involved=["E-XM"], source_ref="19.1 实施阶段",
        signal_type="restrictive",
        note={"comment": "signal_type命中'须'（restrictive）；constrained_entity=E-XM；与 t02 precondition 一致"},
    )

    # BR64：测量审核结果通知单审核流程合并
    m.add_br(
        bid="b64", category="validation",
        desc="测量审核结果通知单审批流程将原来多个流程合并为一个流程，流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-TASK"], source_ref="20.9.1.1 测量审核结果通知单审核流程优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'合并为一个流程'（restrictive，流程约束）；category判有效性校验；constrained_entity=E-TASK"},
    )

    # BR65：项目数据导入历史数据
    m.add_br(
        bid="b65", category="computation",
        desc="项目查询列表中的数据除系统启用后的数据外还包含了往年的历史数据",
        entities_involved=["E-TJBB"], source_ref="20.8.4.1 项目查询",
        signal_type="restrictive",
        note={"comment": "signal_type命中'包含'（restrictive，包含关系措辞）；category判计算衍生（数据合并）"},
    )

    return m
