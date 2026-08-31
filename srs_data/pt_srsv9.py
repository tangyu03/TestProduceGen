"""网数中心能力验证服务平台升级维护项目-需求分析与设计 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704.md",
        document_scope="§3.4；§5；§19.1；§19.2（平行流程，差异：编制结果通知单取代编制结果报告；结果通知单审批合并；作业指导书单独走通知状态机；差异在相关转换 note 中标注）；§19.3；§19.4；§20.2；§20.3；§20.4；§20.5；§20.6（测量审核平行模块）；§20.7；§20.9；§20.10；§20.11；§21.3",
    )
    # ===== 事件台账（§2）=====
    m.set_prohibition_config(config={
        "action_verbs": [
            "编制", "审核", "批准", "发布", "报名", "缴费", "开具", "核查",
            "发放", "发送", "提交", "评价", "统计", "整理", "导入", "上传",
            "下载", "修改", "删除", "新增", "停用", "启用", "退回", "撤销",
            "回收", "确认", "测试", "还样", "发样", "收样", "退款", "借出",
            "归还", "维护", "签发", "导出", "选择", "跳转", "回收",
        ],
        "prohibit_keywords": [
            "接收人1和接收人2不能同时为空",
            "含有子项的记录不允许删除",
            "存在子项的数据不可以删除",
            "停用的标准库在项目创建等环节不可被选择",
            "退款金额不能大于当前缴费金额",
            "评价人员只能对自己的评价结果进行修改",
            "未结束的项目可以进行消息发送",
            "仅收集完成业务所必需的最少个人信息",
        ],
    })

    # ===== §19.1 能力验证提供者流程 → 事件台账 =====
    # 行1 任务通知书编制：仅创建任务通知书文件，无状态面变化 → 非事件（入 operations）
    # 行2 设计方案编制 → 项目状态创建（initial=待开始）
    m.add_event(eid="e01", entity="E-XM", dimension="项目状态", action="设计方案编制",
                actor="策划人员", precondition="初始", consequence="待开始",
                source_ref="19.1方案设计阶段")
    # 行3 能力验证计划发布 → 项目状态 报名中；预通知创建（未发送）
    m.add_event(eid="e02", entity="E-XM", dimension="项目状态", action="能力验证计划发布",
                actor="项目管理员", precondition="待开始", consequence="报名中",
                source_ref="19.1实施阶段")
    m.add_event(eid="e03", entity="E-YT", dimension="通知状态", action="能力验证计划发布",
                actor="项目管理员", precondition="初始", consequence="未发送",
                source_ref="19.1实施阶段")
    # 行4 报名 → 报名记录创建（报名待审核/已撤销分支）；缴费通知单创建（未发送）；费用创建（待缴费）；发票创建（待开票）
    m.add_event(eid="e04", entity="E-BMJL", dimension="报名记录状态", action="报名",
                actor="能力验证参加者", precondition="初始", consequence="报名待审核",
                source_ref="19.1实施阶段")
    m.add_event(eid="e04b", entity="E-BMJL", dimension="报名记录状态", action="报名",
                actor="能力验证参加者", precondition="初始", consequence="已撤销",
                source_ref="19.1实施阶段")
    m.add_event(eid="e05", entity="E-JFTZ", dimension="缴费通知单状态", action="报名",
                actor="system", precondition="初始", consequence="未发送",
                source_ref="19.1实施阶段")
    m.add_event(eid="e06", entity="E-FY", dimension="费用状态", action="报名",
                actor="system", precondition="初始", consequence="待缴费",
                source_ref="19.1实施阶段")
    m.add_event(eid="e07", entity="E-FP", dimension="发票状态", action="报名",
                actor="system", precondition="初始", consequence="待开票",
                source_ref="19.1实施阶段")
    # 行5 报名审核 → 报名记录 报名退回/报名成功（分支）；缴费通知单 已发送（仅审核通过分支）
    m.add_event(eid="e08", entity="E-BMJL", dimension="报名记录状态", action="报名审核",
                actor="项目管理员", precondition="报名待审核", consequence="报名退回",
                source_ref="19.1实施阶段")
    m.add_event(eid="e08b", entity="E-BMJL", dimension="报名记录状态", action="报名审核",
                actor="项目管理员", precondition="报名待审核", consequence="报名成功",
                source_ref="19.1实施阶段")
    m.add_event(eid="e09", entity="E-JFTZ", dimension="缴费通知单状态", action="报名审核",
                actor="system", precondition="未发送；E-BMJL.报名成功", consequence="已发送",
                source_ref="19.1实施阶段")
    # 行6 缴费 → 样品创建（待核查）；费用 已缴费
    m.add_event(eid="e10", entity="E-YP", dimension="样品状态", action="缴费",
                actor="样品制备人员", precondition="初始；E-BMJL.报名成功", consequence="待核查",
                source_ref="19.1实施阶段")
    m.add_event(eid="e11", entity="E-FY", dimension="费用状态", action="缴费",
                actor="能力验证参加者", precondition="待缴费", consequence="已缴费",
                source_ref="19.1实施阶段")
    # 行7 发票开具 → 发票 已开票（费用状态 self-loop 已缴费/未缴费，依业务对象维度不立事件）
    m.add_event(eid="e12", entity="E-FP", dimension="发票状态", action="发票开具",
                actor="财务管理人员", precondition="待开票", consequence="已开票",
                source_ref="19.1实施阶段")
    # 行9 能力验证预通知 → 通知状态 已发送/待确认（分支）；报名记录 结果待提交
    m.add_event(eid="e13", entity="E-YT", dimension="通知状态", action="能力验证预通知",
                actor="项目管理员", precondition="未发送", consequence="已发送",
                source_ref="19.1实施阶段")
    m.add_event(eid="e13b", entity="E-YT", dimension="通知状态", action="能力验证预通知",
                actor="项目管理员", precondition="未发送", consequence="待确认",
                source_ref="19.1实施阶段")
    m.add_event(eid="e14", entity="E-BMJL", dimension="报名记录状态", action="能力验证预通知",
                actor="项目管理员", precondition="报名成功", consequence="结果待提交",
                source_ref="19.1实施阶段")
    # 行10 样品核查 → 样品状态 已核查、待发样（顿号快照，逐值落点）
    m.add_event(eid="e15", entity="E-YP", dimension="样品状态", action="样品核查",
                actor="样品管理员", precondition="待核查", consequence="已核查",
                source_ref="19.1实施阶段")
    m.add_event(eid="e16", entity="E-YP", dimension="样品状态", action="样品核查",
                actor="样品管理员", precondition="已核查", consequence="待发样",
                source_ref="19.1实施阶段")
    # 行11 样品发放,作业指导书发送 → 样品状态 已发样；通知状态 已确认
    m.add_event(eid="e17", entity="E-YP", dimension="样品状态", action="样品发放,作业指导书发送",
                actor="项目管理员", precondition="待发样", consequence="已发样",
                source_ref="19.1实施阶段")
    m.add_event(eid="e18", entity="E-YT", dimension="通知状态", action="样品发放,作业指导书发送",
                actor="能力验证参加者", precondition="已发送", consequence="已确认",
                source_ref="19.1实施阶段")
    m.add_event(eid="e18b", entity="E-YT", dimension="通知状态", action="样品发放,作业指导书发送",
                actor="能力验证参加者", precondition="待确认", consequence="已确认",
                source_ref="19.1实施阶段")
    # 行12 参加者测试与结果提交 → 样品状态 已还样、待核查/无需还样（顿号+斜杠混合）；
    # 报名记录 结果已提交
    m.add_event(eid="e19", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="已发样", consequence="已还样",
                source_ref="19.1实施阶段")
    m.add_event(eid="e20", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="样品管理员", precondition="已还样", consequence="待核查",
                source_ref="19.1实施阶段")
    m.add_event(eid="e20b", entity="E-YP", dimension="样品状态", action="参加者测试与结果提交",
                actor="样品管理员", precondition="已还样", consequence="无需还样",
                source_ref="19.1实施阶段")
    m.add_event(eid="e21", entity="E-BMJL", dimension="报名记录状态", action="参加者测试与结果提交",
                actor="能力验证参加者", precondition="结果待提交", consequence="结果已提交",
                source_ref="19.1实施阶段")
    # 行13 结果报告回收 → 报名记录 结果已提交/结果退回修改（分支）
    m.add_event(eid="e22", entity="E-BMJL", dimension="报名记录状态", action="结果报告回收",
                actor="项目管理员", precondition="结果已提交", consequence="结果退回修改",
                source_ref="19.1报告编制和结果通知")
    # 行14 评价人员进行评价 → 报名记录 结果已提交（结果退回修改→结果已提交再提交，自环或回退）；
    # 评价创建（待评价→评价中）
    m.add_event(eid="e23", entity="E-BMJL", dimension="报名记录状态", action="评价人员进行评价",
                actor="能力验证参加者", precondition="结果退回修改", consequence="结果已提交",
                source_ref="19.1报告编制和结果通知")
    m.add_event(eid="e24", entity="E-PJ", dimension="评价状态", action="评价人员进行评价",
                actor="评价人员", precondition="初始", consequence="待评价",
                source_ref="19.1报告编制和结果通知；20.7.1.2协同评价")
    m.add_event(eid="e25", entity="E-PJ", dimension="评价状态", action="评价人员进行评价",
                actor="评价人员", precondition="待评价", consequence="评价中",
                source_ref="20.7.1.2协同评价")
    # 行14b 评价人员提交评价结果 → 评价状态 评价确认
    m.add_event(eid="e26", entity="E-PJ", dimension="评价状态", action="评价人员提交评价结果",
                actor="评价人员", precondition="评价中", consequence="评价确认",
                source_ref="20.7.1.2协同评价")
    # 行14c 评价组长确认 → 评价状态 已确认（或退回修改回评价中）
    m.add_event(eid="e27", entity="E-PJ", dimension="评价状态", action="评价组长确认",
                actor="评价组长", precondition="评价确认", consequence="已确认",
                source_ref="20.7.1.3评价确认")
    m.add_event(eid="e28", entity="E-PJ", dimension="评价状态", action="评价组长退回修改",
                actor="评价组长", precondition="评价确认", consequence="评价中",
                source_ref="20.7.1.3评价确认")
    # 行15 对评价进行统计 → 无状态变化（操作，入 E-PJ.operations）
    # 行16 编制结果报告 → 报名记录 报告/证书审核中
    m.add_event(eid="e29", entity="E-BMJL", dimension="报名记录状态", action="编制结果报告",
                actor="策划人员", precondition="结果已提交；E-PJ.已确认", consequence="报告/证书审核中",
                source_ref="19.1报告编制和结果通知")
    # 行17 技术主管审核报告 → 审核任务创建（待审核→通过/退回分支）
    m.add_event(eid="e30", entity="E-TASK", dimension="任务审核状态", action="技术主管审核报告",
                actor="策划人员", precondition="初始；E-BMJL.报告/证书审核中", consequence="待审核",
                source_ref="19.1报告编制和结果通知")
    m.add_event(eid="e31", entity="E-TASK", dimension="任务审核状态", action="技术主管审核报告",
                actor="技术主管", precondition="待审核", consequence="通过",
                source_ref="19.1报告编制和结果通知；20.9业务审核")
    m.add_event(eid="e31b", entity="E-TASK", dimension="任务审核状态", action="技术主管审核报告",
                actor="技术主管", precondition="待审核", consequence="退回",
                source_ref="19.1报告编制和结果通知；20.9业务审核")
    # 行18 报告/结果通知单授权签字人/证书实验室负责人批准 → 审核任务 通过（授权签字人批报告/通知单，
    # 实验室负责人批证书）
    m.add_event(eid="e32", entity="E-TASK", dimension="任务审核状态", action="授权签字人批准报告和结果通知单",
                actor="授权签字人", precondition="待审核；E-TASK.通过", consequence="通过",
                source_ref="19.1报告编制和结果通知")
    m.add_event(eid="e33", entity="E-TASK", dimension="任务审核状态", action="实验室负责人批准证书",
                actor="实验室负责人", precondition="待审核；E-TASK.通过", consequence="通过",
                source_ref="19.1报告编制和结果通知")
    # 行19 发放结果报告和证书 → 报名记录 报告/证书已发布
    m.add_event(eid="e34", entity="E-BMJL", dimension="报名记录状态", action="发放结果报告和证书",
                actor="项目管理员", precondition="报告/证书审核中；E-TASK.通过", consequence="报告/证书已发布",
                source_ref="19.1报告编制和结果通知")

    # ===== §19.4 能力验证参加者流程 → 已被 §19.1 覆盖（actor=能力验证参加者） =====

    # ===== §20.4.1 实验室管理 → 事件台账 =====
    # §20.3.1 实验室信息新增/修改后需经审核通过后方可用于项目报名
    m.add_event(eid="e35", entity="E-SYS", dimension="实验室状态", action="机构新增实验室信息",
                actor="机构", precondition="初始", consequence="待审核",
                source_ref="20.3.1实验室信息；20.4.1.2实验室审核")
    m.add_event(eid="e36", entity="E-SYS", dimension="实验室状态", action="机构修改实验室信息",
                actor="机构", precondition="启用", consequence="待审核",
                source_ref="20.3.1实验室信息；20.4.1.3实验室修改")
    # §20.4.1.2 审核通过 → 启用；退回修改 → 已退回
    m.add_event(eid="e37", entity="E-SYS", dimension="实验室状态", action="实验室审核通过",
                actor="系统管理人员", precondition="待审核", consequence="启用",
                source_ref="20.4.1.2实验室审核")
    m.add_event(eid="e38", entity="E-SYS", dimension="实验室状态", action="实验室审核退回",
                actor="系统管理人员", precondition="待审核", consequence="已退回",
                source_ref="20.4.1.2实验室审核")
    # §20.4.1.1 停用/启用按钮
    m.add_event(eid="e39", entity="E-SYS", dimension="实验室状态", action="实验室停用",
                actor="系统管理人员", precondition="启用", consequence="停用",
                source_ref="20.4.1.1实验室列表与查询")
    m.add_event(eid="e40", entity="E-SYS", dimension="实验室状态", action="实验室启用",
                actor="系统管理人员", precondition="停用", consequence="启用",
                source_ref="20.4.1.1实验室列表与查询")
    # 已退回可重新提交（机构修改后回到待审核，e36 覆盖此路径，precondition 增加 已退回）
    m.add_event(eid="e40b", entity="E-SYS", dimension="实验室状态", action="机构修改实验室信息",
                actor="机构", precondition="已退回", consequence="待审核",
                source_ref="20.4.1.3实验室修改")

    # ===== §20.4.2 标准库管理 → 事件台账 =====
    m.add_event(eid="e41", entity="E-BZK", dimension="标准库状态", action="新增标准库",
                actor="系统管理人员", precondition="初始", consequence="启用",
                source_ref="20.4.2.2新增标准库")
    m.add_event(eid="e42", entity="E-BZK", dimension="标准库状态", action="停用标准库",
                actor="系统管理人员", precondition="启用", consequence="停用",
                source_ref="20.4.2.5停用启用标准库")
    m.add_event(eid="e43", entity="E-BZK", dimension="标准库状态", action="启用标准库",
                actor="系统管理人员", precondition="停用", consequence="启用",
                source_ref="20.4.2.5停用启用标准库")

    # ===== §20.5.1.1 文件整理 → 事件台账 =====
    m.add_event(eid="e44", entity="E-WJD", dimension="归档状态", action="开启整理任务",
                actor="system", precondition="初始；E-XM.已结束", consequence="整理中",
                source_ref="20.5.1.1文件整理")
    m.add_event(eid="e45", entity="E-WJD", dimension="归档状态", action="整理完成",
                actor="system", precondition="整理中", consequence="已归档",
                source_ref="20.5.1.1文件整理")

    # ===== §20.9.1 业务审核 → 事件台账 =====
    # §20.9.1.3 任务创建（用户通过表单或审核已存在任务，生成新的审核任务）
    m.add_event(eid="e46", entity="E-TASK", dimension="任务审核状态", action="任务创建",
                actor="system", precondition="初始", consequence="待审核",
                source_ref="20.9.1.3增加任务提醒")
    # §20.9.1.4 批量审核
    m.add_event(eid="e47", entity="E-TASK", dimension="任务审核状态", action="批量审核同意",
                actor="系统管理人员", precondition="待审核", consequence="通过",
                source_ref="20.9.1.4任务批量处理")
    m.add_event(eid="e47b", entity="E-TASK", dimension="任务审核状态", action="批量审核退回",
                actor="系统管理人员", precondition="待审核", consequence="退回",
                source_ref="20.9.1.4任务批量处理")

    # ===== §20.10.2.3 缴费单退款 → 事件台账（费用状态回退，inferred） =====
    m.add_event(eid="e48", entity="E-FY", dimension="费用状态", action="缴费单退款",
                actor="财务管理人员", precondition="已缴费", consequence="待缴费",
                source_ref="20.10.2.3缴费单退款")

    # ===== §19.1 项目状态推断过渡（待开始→报名中显式；报名中→进行中→报告审核中→已结束 inferred） =====
    m.add_event(eid="e49", entity="E-XM", dimension="项目状态", action="项目进入实施阶段",
                actor="system", precondition="报名中；E-BMJL.报名成功", consequence="进行中",
                source_ref="19.3项目状态分析；19.1实施阶段")
    m.add_event(eid="e50", entity="E-XM", dimension="项目状态", action="项目进入报告审核阶段",
                actor="system", precondition="进行中；E-BMJL.结果已提交", consequence="报告审核中",
                source_ref="19.3项目状态分析；19.1报告编制和结果通知")
    m.add_event(eid="e51", entity="E-XM", dimension="项目状态", action="项目结束",
                actor="system", precondition="报告审核中；E-BMJL.报告/证书已发布", consequence="已结束",
                source_ref="19.3项目状态分析；19.1报告编制和结果通知")

    # ===== §19.2 测量审核平行流程 → 关键差异事件（合并入同一实体，分支维度=业务类型） =====
    # §19.2 测量审核：先受理报名→设计方案→实施→报告编制；编制结果通知单（而非结果报告）
    m.add_event(eid="e52", entity="E-BMJL", dimension="报名记录状态", action="编制结果通知单",
                actor="策划人员", precondition="结果已提交；E-PJ.已确认", consequence="报告/证书审核中",
                source_ref="19.2测量审核提供者流程；19.3项目状态分析")
    # §20.9.1.1 测量审核结果通知单审批流程合并为一个流程
    m.add_event(eid="e53", entity="E-TASK", dimension="任务审核状态", action="测量审核结果通知单合并审批",
                actor="授权签字人", precondition="待审核", consequence="通过",
                source_ref="20.9.1.1测量审核结果通知单审核流程优化")

    # ===== Step 1 实体 =====

    # ----- 1.0 词表补充（动词/禁止短语回写，源自 Step 1-4 发现） -----
    m.add_action_verbs(verbs=["开启", "批准", "整理", "受理"])
    m.add_prohibit_keywords(keywords=[
        "未结束的项目可以进行消息发送",
        "只有已上传对应文件且未提交审核的记录才可以被选定",
        "审核结果为通过时可以为空",
        "退回修改必须填写审核意见",
    ])

    # ----- 1.1 角色 -----
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
    m.add_role(id="r14", name="评价组长", readonly=False)
    m.add_role(id="r15", name="监督员", readonly=False)
    m.add_role(id="r16", name="机构", readonly=False)

    # ----- 1.1 权限（operations 限 session/ui/file/query/config 及不改状态 crud） -----
    m.add_permission(role="项目管理员", operations=["查询项目", "新增项目", "文件整理", "代码导入", "批量处理", "消息发送", "上传结果通知单", "上传证书", "提交审核"])
    m.add_permission(role="策划人员", operations=["查询项目", "编制文件", "上传文件", "下载文件"])
    m.add_permission(role="技术主管", operations=["查询项目", "审核报告"])
    m.add_permission(role="实验室负责人", operations=["查询项目", "批准证书"])
    m.add_permission(role="授权签字人", operations=["查询项目", "批准报告"])
    m.add_permission(role="评价人员", operations=["查询项目", "评价录入", "导出评价结果"])
    m.add_permission(role="评价组长", operations=["查询项目", "完善评价细则", "结果确认", "保存历史", "调整细则", "退回修改", "调整统计规则", "导出评价结果"])
    m.add_permission(role="样品管理员", operations=["查询样品", "样品出入库登记", "样品核查"])
    m.add_permission(role="样品制备人员", operations=["查询样品", "样品制备", "样品配置"])
    m.add_permission(role="财务管理人员", operations=["查询缴费", "发票上传", "缴费单退款", "修改备注", "导出缴费信息"])
    m.add_permission(role="系统管理人员", operations=["查询用户", "新增用户", "修改用户", "删除用户", "查询角色", "新增角色", "修改角色", "查询机构", "查询实验室", "审核实验室", "停用实验室", "启用实验室", "修改实验室", "查询标准库", "新增标准库", "修改标准库", "删除标准库", "停用标准库", "启用标准库", "查询信息发送记录", "批量审核"])
    m.add_permission(role="能力验证参加者", operations=["查询项目", "报名", "上传付款单", "下载预通知", "提交结果", "上传结果通知单", "上传证书", "下载文件"])
    m.add_permission(role="统计人员", operations=["查询项目", "查询统计", "导出统计"])
    m.add_permission(role="质量专员", operations=["查询项目", "查询报告统计"])
    m.add_permission(role="机构", operations=["查询实验室", "新增实验室", "修改实验室"])
    m.add_permission(role="监督员", operations=["查询项目"])

    # ----- 1.2/1.3/1.4 实体定义 -----
    # E-XM 能力验证项目
    m.add_entity(
        id="E-XM", name="能力验证项目", desc="能力验证/测量审核业务的载体，承载项目级状态流转",
        type="core", tags=["multi-state", "approvable", "expirable"],
        attributes=[
            attr(name="项目编号", desc="项目唯一标识"),
            attr(name="项目名称", desc="项目名称"),
            attr(name="产品类型", desc="项目所属产品类型"),
            attr(name="项目类型", desc="能力验证或测量审核", is_config=True),
            attr(name="子领域", desc="项目所属子领域"),
            attr(name="项目费用", desc="项目应收金额"),
            attr(name="所属年度", desc="项目所属年度"),
            attr(name="监督员", desc="项目新增表单新增字段"),
            attr(name="技术主管", desc="项目人员，唯一时默认填充"),
            attr(name="实验室负责人", desc="项目人员，唯一时默认填充"),
            attr(name="授权签字人", desc="项目人员，唯一时默认填充"),
            attr(name="财务备注", desc="项目列表新增字段"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": ["进行中", "报告审核中", "已结束"],
                "note": {"comment": "§19.3枚举5值；§19.1表格仅显式覆盖待开始/报名中；进行中/报告审核中/已结束依据§19.3枚举+§19.1阶段名（实施阶段/报告编制和结果通知/结束）推导"},
            },
        ],
        operations=[
            op(name="任务通知书编制", category="file", expected_results=["生成任务通知书文件"], source_ref="19.1项目准备阶段",
               note={"role": ["策划人员"], "comment": "表格行1，无状态面变化，非事件（无对应转换，不登记 op 关联）"}),
            op(name="设计方案编制", category="file", expected_results=["生成设计方案文件"], source_ref="19.1方案设计阶段",
               note={"role": ["策划人员"]}),
            op(name="文件整理", category="file", expected_results=["归档任务已开启，请稍后查看"], source_ref="20.5.1.1文件整理",
               note={"role": ["项目管理员"], "comment": "已结束项目可触发；触发 E-WJD 创建"}),
            op(name="代码导入", category="file", expected_results=["报名机构三方代码导入成功"], source_ref="20.5.1.2机构代码导入",
               note={"role": ["项目管理员"], "comment": "导入报名机构三方代码；无状态变化"}),
            op(name="批量处理", category="ui", expected_results=["跳转到报名信息批量处理页面"], source_ref="20.5.1.3项目批量操作",
               note={"role": ["项目管理员"], "comment": "入口操作；具体上传/提交审核在 E-BMJL 侧"}),
            op(name="消息发送", category="ui", expected_results=["消息按选择方式发送"], source_ref="20.5.1.4优化消息发送功能",
               note={"role": ["项目管理员"], "comment": "未结束项目可发送；接收人1和接收人2不能同时为空"}),
            op(name="机构代码批量导入", category="file", expected_results=["批量导入机构代码"], source_ref="20.5.1项目管理",
               note={"role": ["项目管理员"], "comment": "新增能力；无状态变化"}),
            op(name="项目批量操作", category="ui", expected_results=["批量处理入口"], source_ref="20.5.1项目管理",
               note={"role": ["项目管理员"], "comment": "无状态变化"}),
        ],
    )

    # E-YP 项目样品
    m.add_entity(
        id="E-YP", name="项目样品", desc="能力验证项目中的样品流转载体",
        type="core", tags=["multi-state"],
        attributes=[
            attr(name="样品编号", desc="样品唯一标识"),
            attr(name="批次", desc="样品批次"),
            attr(name="核查记录表", desc="样品核查记录"),
        ],
        state_dimensions=[
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查", "待发样", "已发样", "已还样", "无需还样"],
                "initial": "待核查",
                "terminal": ["无需还样"],
                "inferred": ["待发样", "已发样", "已还样", "无需还样"],
                "note": {"comment": "§19.3枚举仅列待核查/已核查；待发样/已发样/已还样/无需还样依据§19.1表格『样品状态』列实际取值推导；§19.1表格行12『已还样、待核查/无需还样』体现循环状态机（已还样→待核查）"},
            },
        ],
        operations=[
            op(name="样品制备", category="file", expected_results=["生成样品制备方案"], source_ref="5.11样品制备人员",
               note={"role": ["样品制备人员"], "comment": "样品制备人员编制方案；无状态变化"}),
            op(name="样品出入库登记", category="file", expected_results=["样品出入库记录更新"], source_ref="5.12样品管理员",
               note={"role": ["样品管理员"], "comment": "样品管理员库存管理"}),
        ],
    )

    # E-YT 预通知
    m.add_entity(
        id="E-YT", name="预通知", desc="能力验证计划预通知、作业指导书等通知类载体",
        type="core", tags=[],
        attributes=[
            attr(name="通知编号", desc="通知唯一标识"),
            attr(name="通知类型", desc="预通知/作业指导书/结果通知单等"),
            attr(name="用户信息表", desc="预通知附带用户信息表"),
        ],
        state_dimensions=[
            {
                "dimension_name": "通知状态",
                "states": ["未发送", "已发送", "待确认", "已确认", "待审核", "退回", "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已确认", "已批准"],
                "inferred": ["已发送", "已确认"],
                "note": {
                    "comment": "§19.3枚举6值（未发送/待确认/待审核/退回/已审核/已批准）；§19.1台账覆盖未发送→已发送/待确认→已确认流转；待审核/退回/已审核/已批准在§19.1台账无事件覆盖（孤岛，§19.2作业指导书审核可能覆盖，本DSL未展开）",
                    "ambiguity": "§19.3通知状态枚举与§19.1预通知状态列实际取值口径不一致：§19.3偏审核语义（待审核/已审核/已批准），§19.1偏投递语义（已发送/待确认/已确认），两口径并列保留",
                },
            },
        ],
        operations=[],
    )

    # E-BMJL 报名记录
    m.add_entity(
        id="E-BMJL", name="报名记录", desc="参加者报名能力验证项目的记录，承载多维度状态",
        type="core", tags=["multi-state", "collaborative"],
        attributes=[
            attr(name="报名编号", desc="报名记录唯一标识"),
            attr(name="实验室", desc="报名实验室引用"),
            attr(name="机构代码", desc="报名机构三方代码"),
            attr(name="报名时间", desc="报名提交时间"),
            attr(name="报名表", desc="报名表文件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "inferred": [],
                "note": {"comment": "§19.3枚举9值，§19.1台账全覆盖"},
            },
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "inferred": [],
                "note": {"comment": "§19.3枚举4值；§19.1台账无事件覆盖（孤岛，参加者侧样品流转状态，可能由§19.4参加者流程承载，本DSL未展开参加者侧状态机）"},
            },
        ],
        operations=[
            op(name="上传付款单", category="file", expected_results=["付款记录保存，可多次付款"], source_ref="20.5.2.1已报名项目增加多次付款功能",
               note={"role": ["能力验证参加者"], "comment": "多次付款不对金额校验限制"}),
            op(name="下载预通知文件", category="file", expected_results=["预通知文件下载"], source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载",
               note={"role": ["能力验证参加者"], "comment": "文件下载Tab下新增"}),
            op(name="上传结果通知单", category="file", expected_results=["结果通知单文件上传"], source_ref="20.5.1.3项目批量操作",
               note={"role": ["项目管理员"], "comment": "批量处理页面操作"}),
            op(name="上传证书", category="file", expected_results=["证书文件上传"], source_ref="20.5.1.3项目批量操作",
               note={"role": ["项目管理员"], "comment": "批量处理页面操作"}),
            op(name="提交审核", category="ui", expected_results=["选中记录批量提交审核"], source_ref="20.5.1.3项目批量操作",
               note={"role": ["项目管理员"], "comment": "需先选择记录；未选择则提示"}),
        ],
    )

    # E-JFTZ 缴费通知单
    m.add_entity(
        id="E-JFTZ", name="缴费通知单", desc="报名后系统自动生成/发送的缴费通知",
        type="core", tags=[],
        attributes=[
            attr(name="通知单编号", desc="缴费通知单唯一标识"),
            attr(name="应收金额", desc="应缴费用金额"),
        ],
        state_dimensions=[
            {
                "dimension_name": "缴费通知单状态",
                "states": ["未发送", "已发送"],
                "initial": "未发送",
                "terminal": ["已发送"],
                "inferred": [],
                "note": {"comment": "§19.1表格『缴费通知单』列实际取值；§19.3未单独枚举此维度，依据§19.1推导"},
            },
        ],
        operations=[],
    )

    # E-FY 费用
    m.add_entity(
        id="E-FY", name="费用", desc="报名记录对应的费用记录",
        type="core", tags=["expirable"],
        attributes=[
            attr(name="付款金额", desc="累计付款金额"),
            attr(name="退款金额", desc="累计退款金额，红色字体且大于0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="管理备注", desc="退款原因等"),
        ],
        state_dimensions=[
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "§19.3枚举2值；§19.1表格行7『已缴费/未缴费』中未缴费按§19.3统一为待缴费；§20.10.2.3退款可触发已缴费→待缴费回退"},
            },
        ],
        operations=[
            op(name="缴费单退款", category="ui", expected_results=["退款金额累加，实际付款更新"], source_ref="20.10.2.3缴费单退款",
               note={"role": ["财务管理人员"], "comment": "退款金额不能大于当前缴费金额"}),
        ],
    )

    # E-FP 发票
    m.add_entity(
        id="E-FP", name="发票", desc="报名记录对应的发票记录，支持多次分批上传",
        type="core", tags=[],
        attributes=[
            attr(name="开票时间", desc="最后一次开票时间"),
            attr(name="电子发票", desc="发票文件，支持多个"),
            attr(name="开票类型", desc="电子专票/电子普票"),
        ],
        state_dimensions=[
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "inferred": [],
                "note": {"comment": "§19.3枚举2值；§20.10.2.2支持多次分批上传"},
            },
        ],
        operations=[
            op(name="发票上传", category="file", expected_results=["发票文件保存到发票列表"], source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传",
               note={"role": ["财务管理人员"], "comment": "支持多次分批上传；可移除文件"}),
        ],
    )

    # E-SYS 实验室
    m.add_entity(
        id="E-SYS", name="实验室", desc="参加者机构实验室信息，新增/修改需审核通过后方可用于项目报名",
        type="core", tags=["approvable", "configurable"],
        attributes=[
            attr(name="实验室编号", desc="实验室唯一标识"),
            attr(name="实验室名称", desc="实验室名称"),
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="法人名称", desc="法人名称"),
            attr(name="企业类型", desc="企业类型"),
            attr(name="企业规模", desc="企业规模"),
            attr(name="CNAS", desc="已获CNAS认可及证书号"),
            attr(name="CMA", desc="已获CMA认可及证书编号"),
            attr(name="邮箱", desc="联系邮箱"),
            attr(name="座机号码", desc="座机号码"),
            attr(name="地址", desc="行政区域+详细地址"),
            attr(name="联系人", desc="联系人"),
            attr(name="联系电话", desc="联系电话"),
            attr(name="默认实验室", desc="是否默认实验室"),
            attr(name="证明文件", desc="营业执照或其他证书材料"),
            attr(name="快照记录", desc="审核通过时生成的数据快照"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "启用", "停用", "已退回"],
                "initial": "待审核",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "§20.3.1/§20.4.1.1/§20.4.1.2一致枚举4值；§20.3.1称『退回修改』为描述，正式状态值取§20.4.1.2『已退回』"},
            },
        ],
        operations=[
            op(name="审核实验室", category="ui", expected_results=["弹出审核窗口，提交审核结果"], source_ref="20.4.1.2实验室审核",
               note={"role": ["系统管理人员"], "comment": "审核通过生成快照；退回修改必须填写审核意见"}),
            op(name="修改实验室", category="ui", expected_results=["修改内容保存，状态变为待审核"], source_ref="20.4.1.3实验室修改",
               note={"role": ["机构", "系统管理人员"], "comment": "机构修改后需重新审核"}),
        ],
    )

    # E-BZK 标准库
    m.add_entity(
        id="E-BZK", name="标准库", desc="标准库基础数据，下属测试项和参数，分层级维护",
        type="managed", tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="标准库唯一标识"),
            attr(name="标准库名称", desc="标准库名称"),
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
                "note": {"comment": "§20.4.2.1列表展示字段；§20.4.2.5停用后项目创建等环节不可被选择"},
            },
        ],
        operations=[
            op(name="新增标准库", category="ui", expected_results=["标准库创建，状态默认启用"], source_ref="20.4.2.2新增标准库",
               note={"role": ["系统管理人员"]}),
            op(name="修改标准库", category="ui", expected_results=["标准库信息更新"], source_ref="20.4.2.3修改标准库",
               note={"role": ["系统管理人员"], "comment": "无状态变化"}),
            op(name="删除标准库", category="ui", expected_results=["标准库删除，含子项的记录不允许删除"], source_ref="20.4.2.4删除标准库",
               note={"role": ["系统管理人员"], "comment": "二次确认；含子项不允许删除"}),
            op(name="管理测试项", category="ui", expected_results=["跳转至测试项管理界面"], source_ref="20.4.2.6进入测试项管理界面",
               note={"role": ["系统管理人员"], "comment": "导航操作"}),
            op(name="新增测试项", category="ui", expected_results=["测试项加入列表"], source_ref="20.4.2.8新增测试项",
               note={"role": ["系统管理人员"], "comment": "标号+名称"}),
            op(name="修改测试项", category="ui", expected_results=["测试项信息更新，列表刷新"], source_ref="20.4.2.9修改测试项",
               note={"role": ["系统管理人员"], "comment": "无状态变化"}),
            op(name="删除测试项", category="ui", expected_results=["测试项删除；含子项的记录不允许删除"], source_ref="20.4.2.10删除测试项",
               note={"role": ["系统管理人员"], "comment": "含子项不允许删除"}),
        ],
    )

    # E-PJ 项目评价
    m.add_entity(
        id="E-PJ", name="项目评价", desc="对报名项目结果进行评价的载体，支持分值/权重两种方式，协同评价",
        type="core", tags=["approvable", "multi-state", "collaborative"],
        attributes=[
            attr(name="评分方式", desc="分值或权重", is_config=True),
            attr(name="及格分", desc="评价组长录入"),
            attr(name="评价结果", desc="最终评价结果"),
            attr(name="评价历史", desc="历次评价结果历史记录"),
            attr(name="成绩区间统计规则", desc="低值/高值组成，大于等于低值小于高值"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["待评价", "评价中", "评价确认", "已确认"],
                "initial": "待评价",
                "terminal": ["已确认"],
                "inferred": ["待评价", "评价中", "评价确认", "已确认"],
                "note": {"comment": "§19.3未枚举；依据§20.7.1.2协同评价+§20.7.1.3评价确认推导；评价组长可在评价确认→已确认（确认）或评价确认→评价中（退回修改）"},
            },
        ],
        operations=[
            op(name="完善评价细则", category="ui", expected_results=["评价项目及评价细则内容保存"], source_ref="20.7.1.1测试项目评价细则完善",
               note={"role": ["评价组长"], "comment": "评价组长编辑"}),
            op(name="评价录入", category="ui", expected_results=["评价分数提交"], source_ref="20.7.1.2协同评价",
               note={"role": ["评价人员"], "comment": "评价人员只能修改自己的评价结果"}),
            op(name="保存历史", category="ui", expected_results=["当前评价结果保存为历史结果"], source_ref="20.7.1.3评价确认",
               note={"role": ["评价组长"], "comment": "评价组长操作"}),
            op(name="调整细则", category="ui", expected_results=["打开评价细节完善页面"], source_ref="20.7.1.3评价确认",
               note={"role": ["评价组长"], "comment": "评价组长操作"}),
            op(name="调整统计规则", category="ui", expected_results=["统计规则配置保存"], source_ref="20.7.1.3评价确认",
               note={"role": ["评价组长"], "comment": "配置成绩区间统计规则"}),
            op(name="导出评价结果", category="file", expected_results=["评价结果文件下载"], source_ref="20.7.1.4评价结果导出",
               note={"role": ["评价人员"], "comment": "导出评价结果"}),
        ],
    )

    # E-TASK 审核任务
    m.add_entity(
        id="E-TASK", name="审核任务", desc="业务审核流程中的任务载体，承载报告/证书/通知单等审批",
        type="core", tags=["approvable", "multi-state"],
        attributes=[
            attr(name="任务类型", desc="结果通知单审核/报告审核/证书审核等"),
            attr(name="审批流程", desc="自定义流程（4个以内预设）", is_config=True),
            attr(name="签章位置", desc="电子签章位置信息"),
            attr(name="创建时间", desc="任务创建时间"),
            attr(name="审核意见", desc="审核反馈意见"),
            attr(name="签字人顺序", desc="提交申请时签字人选择顺序"),
        ],
        state_dimensions=[
            {
                "dimension_name": "任务审核状态",
                "states": ["待审核", "通过", "退回"],
                "initial": "待审核",
                "terminal": ["通过", "退回"],
                "inferred": ["待审核", "通过", "退回"],
                "note": {"comment": "§19.3未枚举；依据§20.9业务审核+§19.1报告编制阶段推导；§20.9.1.1测量审核结果通知单审批合并为一个流程，签字人顺序为提交申请时选择顺序"},
            },
        ],
        operations=[
            op(name="批量审核", category="ui", expected_results=["选中任务批量审核操作"], source_ref="20.9.1.4任务批量处理",
               note={"role": ["系统管理人员"], "comment": "系统根据节点类型及内容判断是否可批量"}),
            op(name="导出审批流程", category="file", expected_results=["满足查询条件的数据导出"], source_ref="20.9.1.5审批流程列表导出",
               note={"role": ["系统管理人员"], "comment": "新增创建时间查询参数"}),
            op(name="预置签章位置", category="config", expected_results=["签章操作时自动代入位置信息"], source_ref="20.9.1.2预置签章位置信息",
               note={"role": ["系统管理人员"], "comment": "系统配置；无状态变化"}),
        ],
    )

    # E-WJD 文件归档
    m.add_entity(
        id="E-WJD", name="文件归档", desc="已结束项目的文件归档任务，含分类整理与数字化存储",
        type="managed", tags=[],
        attributes=[
            attr(name="项目阶段", desc="归档文件所属项目阶段"),
            attr(name="文件名称", desc="归档文件名称"),
            attr(name="份数", desc="文件份数"),
            attr(name="页数", desc="文件页数"),
            attr(name="备注", desc="文件备注"),
        ],
        state_dimensions=[
            {
                "dimension_name": "归档状态",
                "states": ["整理中", "已归档"],
                "initial": "整理中",
                "terminal": ["已归档"],
                "inferred": ["整理中", "已归档"],
                "note": {"comment": "§19.3未枚举；依据§20.5.1.1/§20.6.1.1文件整理推导；整理完成后显示查看归档按钮"},
            },
        ],
        operations=[
            op(name="上传归档文件", category="file", expected_results=["补充文件保存，项目阶段为其它"], source_ref="20.5.1.1文件整理",
               note={"role": ["项目管理员"], "comment": "归档数据查看页面操作"}),
            op(name="打包下载", category="file", expected_results=["归档文件打包下载为zip"], source_ref="20.5.1.1文件整理",
               note={"role": ["项目管理员"], "comment": "zip内含清单文件和按项目阶段命名的目录"}),
        ],
    )

    # ----- 1.5 结构关系 -----
    # (c) 判定：B 有独立创建流程，B 是 core 流程实体，A 为业务归属容器
    m.add_structural(frm="E-XM", to="E-BMJL", relation_type="composition", cardinality="1:N",
                     ownership_dimension="business_ownership",
                     desc="能力验证项目包含多条报名记录，报名记录有独立创建流程（报名动作），为 core 流程实体",
                     confidence="high",
                     note={"comment": "判(c)；项目为业务归属容器；management_dimension=业务归属（项目），comment: 报名记录归属项目"})
    m.add_structural(frm="E-XM", to="E-YP", relation_type="composition", cardinality="1:1",
                     ownership_dimension="business_ownership",
                     desc="项目包含一个样品（制备+流转），样品在缴费阶段独立创建",
                     confidence="high",
                     note={"comment": "判(c)；样品 core 多状态；management_dimension=业务归属（项目），comment: 样品归属项目"})
    m.add_structural(frm="E-XM", to="E-YT", relation_type="composition", cardinality="1:N",
                     ownership_dimension="business_ownership",
                     desc="项目可发出多个预通知（计划通知/预通知/作业指导书等）",
                     confidence="high",
                     note={"comment": "判(c)；预通知 core 多状态；management_dimension=业务归属（项目），comment: 预通知归属项目"})
    m.add_structural(frm="E-XM", to="E-PJ", relation_type="composition", cardinality="1:1",
                     ownership_dimension="business_ownership",
                     desc="项目对应一个项目评价，评价在评价阶段独立创建",
                     confidence="high",
                     note={"comment": "判(c)；评价 core 多状态含审批；management_dimension=业务归属（项目），comment: 评价归属项目"})
    # (d) 判定：B 有独立创建流程/可能永不创建
    m.add_structural(frm="E-XM", to="E-WJD", relation_type="reference", cardinality="1:1",
                     ownership_dimension="configuration_source",
                     desc="项目结束后可触发文件整理任务生成归档，归档为可选流程",
                     confidence="high",
                     note={"comment": "判(d)；归档需用户触发，可能永不创建；management_dimension=配置来源（项目），comment: 归档由项目触发"})
    m.add_structural(frm="E-XM", to="E-TASK", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="项目关联多个审核任务（报告/证书/通知单审批），任务按需创建",
                     confidence="medium",
                     note={"comment": "判(d)；任务按需创建，可能永不创建（无需审批时）；management_dimension=配置来源（项目），comment: 任务由项目审批流程触发；confidence=medium因dependent未直写"})
    # (b) 判定：A 创建时 B 自动入 initial，每条 A 必有 B
    m.add_structural(frm="E-BMJL", to="E-FY", relation_type="composition", cardinality="1:1",
                     ownership_dimension="business_ownership",
                     desc="报名记录创建时自动生成费用记录，初始待缴费",
                     confidence="high",
                     note={"comment": "判(b)；§19.1行4报名时费用=待缴费；management_dimension=业务归属（报名记录），comment: 费用归属报名记录"})
    m.add_structural(frm="E-BMJL", to="E-FP", relation_type="composition", cardinality="1:N",
                     ownership_dimension="business_ownership",
                     desc="报名记录创建时自动生成发票记录，初始待开票，支持多次分批上传",
                     confidence="high",
                     note={"comment": "判(b)；§19.1行4报名时发票=待开票；§20.10.2.2支持多次分批；management_dimension=业务归属（报名记录），comment: 发票归属报名记录"})
    m.add_structural(frm="E-BMJL", to="E-JFTZ", relation_type="composition", cardinality="1:1",
                     ownership_dimension="business_ownership",
                     desc="报名记录创建时自动生成缴费通知单，初始未发送",
                     confidence="high",
                     note={"comment": "判(b)；§19.1行4报名时缴费通知单=未发送；management_dimension=业务归属（报名记录），comment: 缴费通知单归属报名记录"})
    # (d) 判定：B 有独立创建流程，A 为 B 的引用源
    m.add_structural(frm="E-SYS", to="E-BMJL", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="实验室是报名记录的引用源，实验室独立创建并审核，报名记录引用实验室",
                     confidence="high",
                     note={"comment": "判(d)；实验室为master数据，独立审核流程；management_dimension=配置来源（实验室），comment: 实验室提供报名记录的实验室引用"})
    # (a) 判定：A 为 B 提供配置/分类
    m.add_structural(frm="E-BZK", to="E-XM", relation_type="reference", cardinality="1:N",
                     ownership_dimension="configuration_source",
                     desc="标准库为项目提供测试项依据标准，项目创建时引用标准库",
                     confidence="high",
                     note={"comment": "判(a)；标准库提供测试项/参数配置；management_dimension=配置来源（标准库），comment: 标准库为项目提供测试标准配置"})

    # ===== Step 2 分支 =====

    # ① 配置型分支：业务类型（能力验证/测量审核），创建时定，影响整个流程路径
    m.add_branch_dimension(
        dimension="业务类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="影响项目流程路径：能力验证走§19.1（编制结果报告）；测量审核走§19.2（编制结果通知单，审批合并）",
        evidence="①配置型：§19.1与§19.2平行流程；§20.8.3项目类型选项包括能力验证、测量审核；§20.10.1.1业务类型选项包括能力验证、测量审核",
        branches=[
            {"value": "能力验证", "target_transition": "编制结果报告转换", "note": "§19.1能力验证提供者流程"},
            {"value": "测量审核", "target_transition": "编制结果通知单转换", "note": "§19.2测量审核提供者流程，编制结果通知单取代编制结果报告"},
        ],
    )

    # ① 配置型分支：评分方式（分值/权重），创建时定，影响评价计算
    m.add_branch_dimension(
        dimension="评分方式", entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="影响评价结果计算方式：分值按累加计算；权重按加权计算",
        evidence="①配置型：§20.7项目列表『支持分值和权重两种评价方式』；§20.7.1.1项目信息展示区包含评分方式字段",
        branches=[
            {"value": "分值", "target_transition": "评价人员提交评价结果转换", "note": "分值按累加计算得分"},
            {"value": "权重", "target_transition": "评价人员提交评价结果转换", "note": "权重按加权计算得分；落点同，仅措辞异，结果差异型"},
        ],
    )

    # ② 运行时选择型分支：还样要求（需还样/无需还样），根据样品类型在参加者测试与结果提交时分支
    m.add_branch_dimension(
        dimension="还样要求", entity="E-YP",
        values=["需还样", "无需还样"],
        impact_scope="影响样品状态落点：需还样→待核查（进入下一批次循环）；无需还样→无需还样（terminal）",
        evidence="②运行时选择型：§19.1表格行12『已还样、待核查/无需还样』斜杠或语义分支",
        branches=[
            {"value": "需还样", "target_transition": "参加者测试与结果提交转换（需还样分支）", "note": "已还样→待核查，循环状态机"},
            {"value": "无需还样", "target_transition": "参加者测试与结果提交转换（无需还样分支）", "note": "已还样→无需还样，terminal"},
        ],
    )

    # ===== Step 3 转换与因果 =====

    # ----- 3.1 转换 → m.add_trans() -----
    # E-XM 项目状态转换
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[],
        expected_results=["项目状态变为待开始"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1方案设计阶段",
        note={"comment": "源自 e01；⓪ frm=None→forward；项目创建事件"},
    )
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[precond(text="项目处于待开始状态", ptype="state_ref",
                               ref=state_ref("E-XM", "项目状态", "待开始"))],
        expected_results=["项目状态变为报名中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e02；③frm先于to→forward"},
    )
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="项目进入实施阶段", role="system",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["项目状态变为进行中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析；19.1实施阶段",
        note={"comment": "源自 e49；③；推断过渡，§19.1表格未显式但§19.3枚举含进行中；inferred", "inferred": True},
    )
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="项目进入报告审核阶段", role="system",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["项目状态变为报告审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析；19.1报告编制和结果通知",
        note={"comment": "源自 e50；③；推断过渡；inferred", "inferred": True},
    )
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="项目结束", role="system",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="报名记录处于报告/证书已发布状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书已发布")),
        ],
        expected_results=["项目状态变为已结束"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析；19.1报告编制和结果通知",
        note={"comment": "源自 e51；③；推断过渡；terminal=已结束；inferred", "inferred": True},
    )

    # E-YT 通知状态转换
    m.add_trans(
        tid="t06", entity="E-YT", dimension="通知状态",
        frm=None, to="未发送", action="能力验证计划发布", role="项目管理员",
        preconditions=[],
        expected_results=["预通知创建，状态为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e03；⓪ frm=None→forward；预通知创建事件"},
    )
    # 行9 能力验证预通知：分支 已发送/待确认
    m.add_trans(
        tid="t07", entity="E-YT", dimension="通知状态",
        frm="未发送", to="已发送", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="预通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "未发送")),
            precond(text="还样要求=无需确认", ptype="constraint",
                    note={"comment": "分支值条件；无需参加者确认时直接已发送"}),
        ],
        expected_results=["预通知状态变为已发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "通知确认要求", "comment": "源自 e13；分支维度推断为通知确认要求；落点分歧"},
    )
    m.add_trans(
        tid="t07b", entity="E-YT", dimension="通知状态",
        frm="未发送", to="待确认", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="预通知处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "未发送")),
            precond(text="通知确认要求=需确认", ptype="constraint",
                    note={"comment": "分支值条件；需参加者确认时落待确认"}),
        ],
        expected_results=["预通知状态变为待确认"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "通知确认要求", "comment": "源自 e13b；分支维度推断为通知确认要求；落点分歧"},
    )
    # 行11 样品发放: 已发送→已确认 / 待确认→已确认
    m.add_trans(
        tid="t08", entity="E-YT", dimension="通知状态",
        frm="已发送", to="已确认", action="样品发放,作业指导书发送", role="能力验证参加者",
        preconditions=[
            precond(text="预通知处于已发送状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "已发送")),
        ],
        expected_results=["预通知状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e18；③；参加者确认"},
    )
    m.add_trans(
        tid="t08b", entity="E-YT", dimension="通知状态",
        frm="待确认", to="已确认", action="样品发放,作业指导书发送", role="能力验证参加者",
        preconditions=[
            precond(text="预通知处于待确认状态", ptype="state_ref",
                    ref=state_ref("E-YT", "通知状态", "待确认")),
        ],
        expected_results=["预通知状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e18b；③；参加者确认"},
    )

    # E-BMJL 报名记录状态转换
    # 行4 报名：分支 报名待审核/已撤销
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["报名记录创建，状态为报名待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e04；⓪ frm=None→forward；正常报名分支"},
    )
    m.add_trans(
        tid="t09b", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="已撤销", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["报名记录创建即为已撤销"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e04b；⓪ frm=None→forward；撤销分支；terminal=已撤销"},
    )
    # 行5 报名审核：分支 报名退回/报名成功
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="审核结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名退回"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "审核结果", "comment": "源自 e08；①『退回』→backward；分支路径分歧"},
    )
    m.add_trans(
        tid="t10b", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名成功"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "审核结果", "comment": "源自 e08b；③；分支路径分歧"},
    )
    # 报名退回→报名待审核（重新提交）
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名退回")),
        ],
        expected_results=["报名记录重新提交，状态变为报名待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "③；推断：报名退回后参加者可重新提交；inferred", "inferred": True},
    )
    # 行9 能力验证预通知：报名成功→结果待提交
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["报名记录状态变为结果待提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e14；③"},
    )
    # 行12 参加者测试与结果提交：结果待提交→结果已提交
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变为结果已提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e21；③"},
    )
    # 行13 结果报告回收：结果已提交→结果退回修改（分支）
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果报告回收", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="回收判定=退回修改", ptype="constraint",
                    note={"comment": "分支值条件；结果报告需退回修改时"}),
        ],
        expected_results=["报名记录状态变为结果退回修改"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"branch_dimension": "回收判定", "comment": "源自 e22；①『退回』→backward；分支路径分歧"},
    )
    # 结果退回修改→结果已提交（重新提交）
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交", action="评价人员进行评价", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果退回修改")),
        ],
        expected_results=["报名记录状态变为结果已提交"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e23；③；参加者重新提交结果"},
    )
    # 行16 编制结果报告：结果已提交→报告/证书审核中
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价处于已确认状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "已确认")),
        ],
        expected_results=["报名记录状态变为报告/证书审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"branch_dimension": "业务类型",
              "comment": "源自 e29；③；跨主体门禁 E-PJ.已确认 落 state_ref；能力验证分支（与 t16b 测量审核分支对称标注）"},
    )
    # §19.2 测量审核平行：编制结果通知单
    m.add_trans(
        tid="t16b", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果通知单", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价处于已确认状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "已确认")),
            precond(text="业务类型=测量审核", ptype="constraint",
                    note={"comment": "分支值条件；测量审核分支编制结果通知单"}),
        ],
        expected_results=["报名记录状态变为报告/证书审核中"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2测量审核提供者流程；19.3项目状态分析",
        note={"branch_dimension": "业务类型", "comment": "源自 e52；③；测量审核平行流程，编制结果通知单取代编制结果报告"},
    )
    # 行19 发放结果报告和证书：报告/证书审核中→报告/证书已发布
    m.add_trans(
        tid="t17", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="审核任务处于通过状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "通过")),
        ],
        expected_results=["报名记录状态变为报告/证书已发布"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e34；③；跨主体门禁 E-TASK.通过 落 state_ref；terminal=报告/证书已发布"},
    )

    # E-JFTZ 缴费通知单状态转换
    m.add_trans(
        tid="t18", entity="E-JFTZ", dimension="缴费通知单状态",
        frm=None, to="未发送", action="报名", role="system",
        preconditions=[],
        expected_results=["缴费通知单创建，状态为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e05；⓪ frm=None→forward；系统自动创建"},
    )
    m.add_trans(
        tid="t19", entity="E-JFTZ", dimension="缴费通知单状态",
        frm="未发送", to="已发送", action="报名审核", role="system",
        preconditions=[
            precond(text="缴费通知单处于未发送状态", ptype="state_ref",
                    ref=state_ref("E-JFTZ", "缴费通知单状态", "未发送")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["缴费通知单状态变为已发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e09；③；跨主体门禁 E-BMJL.报名成功 落 state_ref；系统自动发送"},
    )

    # E-FY 费用状态转换
    m.add_trans(
        tid="t20", entity="E-FY", dimension="费用状态",
        frm=None, to="待缴费", action="报名", role="system",
        preconditions=[],
        expected_results=["费用记录创建，状态为待缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e06；⓪ frm=None→forward；系统自动创建"},
    )
    m.add_trans(
        tid="t21", entity="E-FY", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "待缴费")),
        ],
        expected_results=["费用状态变为已缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e11；③；§20.5.2.1多次付款不对金额校验限制"},
    )
    # §20.10.2.3 缴费单退款：已缴费→待缴费（全额退款时）
    m.add_trans(
        tid="t22", entity="E-FY", dimension="费用状态",
        frm="已缴费", to="待缴费", action="缴费单退款", role="财务管理人员",
        preconditions=[
            precond(text="费用处于已缴费状态", ptype="state_ref",
                    ref=state_ref("E-FY", "费用状态", "已缴费")),
            precond(text="退款金额不能大于当前缴费金额", ptype="constraint"),
            precond(text="退款类型=全额退款", ptype="constraint",
                    note={"comment": "分支值条件；全额退款触发状态回退"}),
        ],
        expected_results=["费用状态变为待缴费，退款金额累加，实际付款更新"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="20.10.2.3缴费单退款",
        note={"branch_dimension": "退款类型", "comment": "源自 e48；①『退款』→backward；推断：全额退款才回退状态；inferred", "inferred": True},
    )

    # E-FP 发票状态转换
    m.add_trans(
        tid="t23", entity="E-FP", dimension="发票状态",
        frm=None, to="待开票", action="报名", role="system",
        preconditions=[],
        expected_results=["发票记录创建，状态为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e07；⓪ frm=None→forward；系统自动创建"},
    )
    m.add_trans(
        tid="t24", entity="E-FP", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务管理人员",
        preconditions=[
            precond(text="发票处于待开票状态", ptype="state_ref",
                    ref=state_ref("E-FP", "发票状态", "待开票")),
        ],
        expected_results=["发票状态变为已开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e12；③；§20.10.2.2支持多次分批上传"},
    )

    # E-YP 样品状态转换
    m.add_trans(
        tid="t25", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="缴费", role="样品制备人员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["样品创建，状态为待核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e10；⓪ frm=None→forward；跨主体门禁 E-BMJL.报名成功 落 state_ref"},
    )
    # 行10 样品核查：待核查→已核查（顿号快照第1落点）
    m.add_trans(
        tid="t26", entity="E-YP", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变为已核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e15；③；顿号快照第1落点"},
    )
    # 行10 样品核查：已核查→待发样（顿号快照第2落点）
    m.add_trans(
        tid="t27", entity="E-YP", dimension="样品状态",
        frm="已核查", to="待发样", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
        ],
        expected_results=["样品状态变为待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e16；③；顿号快照第2落点"},
    )
    # 行11 样品发放：待发样→已发样
    m.add_trans(
        tid="t28", entity="E-YP", dimension="样品状态",
        frm="待发样", to="已发样", action="样品发放,作业指导书发送", role="项目管理员",
        preconditions=[
            precond(text="样品处于待发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待发样")),
        ],
        expected_results=["样品状态变为已发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e17；③"},
    )
    # 行12 参加者测试与结果提交：已发样→已还样
    m.add_trans(
        tid="t29", entity="E-YP", dimension="样品状态",
        frm="已发样", to="已还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已发样")),
        ],
        expected_results=["样品状态变为已还样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e19；③；顿号快照第1落点"},
    )
    # 行12 已还样→待核查（需还样分支）
    m.add_trans(
        tid="t30", entity="E-YP", dimension="样品状态",
        frm="已还样", to="待核查", action="参加者测试与结果提交", role="样品管理员",
        preconditions=[
            precond(text="样品处于已还样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已还样")),
            precond(text="还样要求=需还样", ptype="constraint",
                    note={"comment": "分支值条件；需还样核查"}),
        ],
        expected_results=["样品状态变为待核查，进入下一批次"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "还样要求", "comment": "源自 e20；序判④（已还样后于待核查）但语义forward（循环状态机），语义优先，comment记'序判④，语义forward（循环状态机）'"},
    )
    # 行12 已还样→无需还样（无需还样分支，terminal）
    m.add_trans(
        tid="t30b", entity="E-YP", dimension="样品状态",
        frm="已还样", to="无需还样", action="参加者测试与结果提交", role="样品管理员",
        preconditions=[
            precond(text="样品处于已还样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已还样")),
            precond(text="还样要求=无需还样", ptype="constraint",
                    note={"comment": "分支值条件；无需还样"}),
        ],
        expected_results=["样品状态变为无需还样"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "还样要求", "comment": "源自 e20b；③；terminal=无需还样"},
    )

    # E-PJ 评价状态转换
    m.add_trans(
        tid="t31", entity="E-PJ", dimension="评价状态",
        frm=None, to="待评价", action="评价人员进行评价", role="评价人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["评价创建，状态为待评价"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；20.7.1.2协同评价",
        note={"comment": "源自 e24；⓪ frm=None→forward；跨主体门禁 E-BMJL.结果已提交 落 state_ref；inferred状态"},
    )
    m.add_trans(
        tid="t32", entity="E-PJ", dimension="评价状态",
        frm="待评价", to="评价中", action="评价人员进行评价", role="评价人员",
        preconditions=[
            precond(text="评价处于待评价状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "待评价")),
        ],
        expected_results=["评价状态变为评价中"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"comment": "源自 e25；③；inferred状态"},
    )
    # 评价人员提交评价结果：评价中→评价确认（结果差异型：分值/权重共用一条）
    m.add_trans(
        tid="t33", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价确认", action="评价人员提交评价结果", role="评价人员",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=[
            "若评分方式=分值，则评价分值按累加计算得分，提交后评价状态变为评价确认",
            "若评分方式=权重，则评价权重按加权计算得分，提交后评价状态变为评价确认",
        ],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"branch_dimension": "评分方式", "comment": "源自 e26；③；结果差异型：落点同（评价确认），仅计算措辞异，用『若』句式"},
    )
    # 评价组长确认：评价确认→已确认
    m.add_trans(
        tid="t34", entity="E-PJ", dimension="评价状态",
        frm="评价确认", to="已确认", action="评价组长确认", role="评价组长",
        preconditions=[
            precond(text="评价处于评价确认状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价确认")),
        ],
        expected_results=["评价状态变为已确认，项目评价状态关闭"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e27；③；terminal=已确认"},
    )
    # 评价组长退回修改：评价确认→评价中
    m.add_trans(
        tid="t35", entity="E-PJ", dimension="评价状态",
        frm="评价确认", to="评价中", action="评价组长退回修改", role="评价组长",
        preconditions=[
            precond(text="评价处于评价确认状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价确认")),
        ],
        expected_results=["当前评价结果保存为历史，评价状态变为评价中，开启下一轮评价"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e28；①『退回』→backward；traits含rollback"},
    )

    # E-TASK 任务审核状态转换
    # §19.1 行17 技术主管审核报告：任务创建（待审核）
    m.add_trans(
        tid="t36", entity="E-TASK", dimension="任务审核状态",
        frm=None, to="待审核", action="技术主管审核报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
        ],
        expected_results=["审核任务创建，状态为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e30；⓪ frm=None→forward；策划人员提交审核；跨主体门禁 E-BMJL.报告/证书审核中 落 state_ref"},
    )
    # 行17 技术主管审核报告：待审核→通过（分支）
    m.add_trans(
        tid="t37", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="通过", action="技术主管审核报告", role="技术主管",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态变为通过"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；20.9业务审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e31；③；分支路径分歧"},
    )
    # 行17 待审核→退回（分支）
    m.add_trans(
        tid="t37b", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="退回", action="技术主管审核报告", role="技术主管",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="审核结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态变为退回"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知；20.9业务审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e31b；①『退回』→backward；分支路径分歧"},
    )
    # 行18 授权签字人批准报告和结果通知单：待审核→通过
    m.add_trans(
        tid="t38", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="通过", action="授权签字人批准报告和结果通知单", role="授权签字人",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="技术主管审核已通过", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "通过")),
        ],
        expected_results=["审核任务状态变为通过（授权签字人批准）"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e32；③；跨主体门禁：技术主管通过后授权签字人方可批准；按E-TASK单实体建模，门禁以同实体state_ref表达（同实体前序转换结果）"},
    )
    # 行18 实验室负责人批准证书：待审核→通过
    m.add_trans(
        tid="t39", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="通过", action="实验室负责人批准证书", role="实验室负责人",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="技术主管审核已通过", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "通过")),
        ],
        expected_results=["审核任务状态变为通过（实验室负责人批准证书）"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e33；③；授权签字人批报告/通知单，实验室负责人批证书，分立转换；门禁以同实体state_ref表达"},
    )
    # §20.9.1.3 任务创建（业务审核模块独立任务）
    m.add_trans(
        tid="t40", entity="E-TASK", dimension="任务审核状态",
        frm=None, to="待审核", action="任务创建", role="system",
        preconditions=[],
        expected_results=["审核任务创建，状态为待审核；系统发送短信通知相关负责人"],
        traits=["time_sensitive"], direction="forward", priority="P0",
        source_ref="20.9.1.3增加任务提醒",
        note={"comment": "源自 e46；⓪ frm=None→forward；§20.9.1.3任务创建发送短信通知；traits含time_sensitive（短信即时触发）"},
    )
    # §20.9.1.4 批量审核同意
    m.add_trans(
        tid="t41", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="通过", action="批量审核同意", role="系统管理人员",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="审核结果=同意", ptype="constraint",
                    note={"comment": "分支值条件"}),
            precond(text="任务节点可被批量处理", ptype="constraint",
                    note={"comment": "系统根据任务节点类型及内容判断"}),
        ],
        expected_results=["选中任务批量状态变为通过"],
        traits=["branch"], direction="forward", priority="P1",
        source_ref="20.9.1.4任务批量处理",
        note={"branch_dimension": "审核结果", "comment": "源自 e47；③；批量审核分支"},
    )
    # §20.9.1.4 批量审核退回
    m.add_trans(
        tid="t41b", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="退回", action="批量审核退回", role="系统管理人员",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="审核结果=退回", ptype="constraint",
                    note={"comment": "分支值条件"}),
            precond(text="任务节点可被批量处理", ptype="constraint",
                    note={"comment": "系统根据任务节点类型及内容判断"}),
        ],
        expected_results=["选中任务批量状态变为退回"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="20.9.1.4任务批量处理",
        note={"branch_dimension": "审核结果", "comment": "源自 e47b；①『退回』→backward；批量审核分支"},
    )
    # §20.9.1.1 测量审核结果通知单合并审批
    m.add_trans(
        tid="t42", entity="E-TASK", dimension="任务审核状态",
        frm="待审核", to="通过", action="测量审核结果通知单合并审批", role="授权签字人",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-TASK", "任务审核状态", "待审核")),
            precond(text="业务类型=测量审核", ptype="constraint",
                    note={"comment": "分支值条件；测量审核分支"}),
        ],
        expected_results=["审核任务状态变为通过；测量审核结果通知单多个流程合并为一个"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="20.9.1.1测量审核结果通知单审核流程优化",
        note={"branch_dimension": "业务类型", "comment": "源自 e53；③；测量审核分支；签字人顺序为提交申请时选择顺序"},
    )

    # E-SYS 实验室状态转换
    m.add_trans(
        tid="t43", entity="E-SYS", dimension="实验室状态",
        frm=None, to="待审核", action="机构新增实验室信息", role="机构",
        preconditions=[],
        expected_results=["实验室创建，状态为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1实验室信息；20.4.1.2实验室审核",
        note={"comment": "源自 e35；⓪ frm=None→forward；机构新增"},
    )
    # 机构修改实验室信息：启用→待审核 / 已退回→待审核
    m.add_trans(
        tid="t44", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="待审核", action="机构修改实验室信息", role="机构",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变为待审核"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.3.1实验室信息；20.4.1.3实验室修改",
        note={"comment": "源自 e36；序判④（启用后于待审核）但语义backward（修改后需重新审核，回退到待审核），语义优先，comment记'序判④，语义backward（修改需重新审核）'"},
    )
    m.add_trans(
        tid="t44b", entity="E-SYS", dimension="实验室状态",
        frm="已退回", to="待审核", action="机构修改实验室信息", role="机构",
        preconditions=[
            precond(text="实验室处于已退回状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "已退回")),
        ],
        expected_results=["实验室状态变为待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3实验室修改",
        note={"comment": "源自 e40b；③；已退回修改后重新提交"},
    )
    # 审核通过：待审核→启用
    m.add_trans(
        tid="t45", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核通过", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态变为启用；为当前数据生成快照记录"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e37；③；traits含audit（生成快照）"},
    )
    # 审核退回：待审核→已退回
    m.add_trans(
        tid="t46", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="已退回", action="实验室审核退回", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
            precond(text="退回修改必须填写审核意见", ptype="constraint"),
        ],
        expected_results=["实验室状态变为已退回"],
        traits=["branch"], direction="backward", priority="P1",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e38；①『退回』→backward；退回修改必须填写审核意见"},
    )
    # 停用：启用→停用
    m.add_trans(
        tid="t47", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="停用", action="实验室停用", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变为停用"],
        traits=[], direction="lateral", priority="P2",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e39；①『停用』→lateral"},
    )
    # 启用：停用→启用
    m.add_trans(
        tid="t48", entity="E-SYS", dimension="实验室状态",
        frm="停用", to="启用", action="实验室启用", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变为启用"],
        traits=[], direction="resume", priority="P2",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e40；①『启用』→resume"},
    )

    # E-BZK 标准库状态转换
    m.add_trans(
        tid="t49", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理人员",
        preconditions=[],
        expected_results=["标准库创建，状态默认启用"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2新增标准库",
        note={"comment": "源自 e41；⓪ frm=None→forward；新增默认启用"},
    )
    m.add_trans(
        tid="t50", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="停用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态变为停用；停用后在项目创建等环节不可被选择"],
        traits=[], direction="lateral", priority="P2",
        source_ref="20.4.2.5停用启用标准库",
        note={"comment": "源自 e42；①『停用』→lateral"},
    )
    m.add_trans(
        tid="t51", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="启用标准库", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态变为启用"],
        traits=[], direction="resume", priority="P2",
        source_ref="20.4.2.5停用启用标准库",
        note={"comment": "源自 e43；①『启用』→resume"},
    )

    # E-WJD 归档状态转换
    m.add_trans(
        tid="t52", entity="E-WJD", dimension="归档状态",
        frm=None, to="整理中", action="开启整理任务", role="system",
        preconditions=[
            precond(text="项目处于已结束状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "已结束")),
        ],
        expected_results=["归档任务开启，提示'归档任务已开启，请稍后查看'"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.5.1.1文件整理",
        note={"comment": "源自 e44；⓪ frm=None→forward；跨主体门禁 E-XM.已结束 落 state_ref；系统自动开启"},
    )
    m.add_trans(
        tid="t53", entity="E-WJD", dimension="归档状态",
        frm="整理中", to="已归档", action="整理完成", role="system",
        preconditions=[
            precond(text="归档处于整理中状态", ptype="state_ref",
                    ref=state_ref("E-WJD", "归档状态", "整理中")),
        ],
        expected_results=["归档状态变为已归档；操作列显示查看归档按钮"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.5.1.1文件整理",
        note={"comment": "源自 e45；③；terminal=已归档；系统自动完成"},
    )

    # ----- 3.3 自检：crud 操作 → 转换关联（link_op_transition 结构化登记）-----
    # 有状态迁移语义的操作逐条登记（映射依据＝action 语义＋frm→to 方向，对照
    # 本实体 add_trans 声明）；无对应转换者不调用（任务通知书编制＝非事件，仅文件）。
    m.link_op_transition(entity="E-XM", op="设计方案编制", transitions=["t01"],
                         note={"comment": "项目状态创建边"})
    m.link_op_transition(entity="E-XM", op="文件整理", transitions=["t52"],
                         note={"comment": "触发 E-WJD 创建"})   # 跨实体，note 点名目标实体
    m.link_op_transition(entity="E-FY", op="缴费单退款", transitions=["t22"],
                         note={"comment": "费用状态回退，全额退款时"})
    m.link_op_transition(entity="E-TASK", op="批量审核", transitions=["t41", "t41b"])
    m.link_op_transition(entity="E-SYS", op="审核实验室", transitions=["t45", "t46"])
    m.link_op_transition(entity="E-SYS", op="修改实验室", transitions=["t44", "t44b"])
    m.link_op_transition(entity="E-BZK", op="新增标准库", transitions=["t49"])

    # ----- 3.4 因果 → m.add_causal() -----
    # Q1：X 变直接致 Y 变？Y 需额外操作 → 约束，标[待写入: Step4 XC]
    # Q2：门禁已由 Y 侧 precondition 或既有 XC 表达？已表达 → 止于 Q2，不写因果、不标记
    # Q3：上级作下级门禁 → 约束（标记[待写入]）；下级全完成上级自动推进 → 因果

    # 因果1：E-XM 项目状态变化 → E-BMJL 报名记录可被创建（联动 XC 已表达，止于 Q2）
    # 因果2：E-BMJL 报名成功 → E-JFTZ 缴费通知单自动发送（系统自动，写因果）
    m.add_causal(
        frm="E-BMJL", to="E-JFTZ",
        desc="报名记录审核通过后系统自动发送缴费通知单",
        trigger="报名审核通过后缴费通知自动发送",
        trigger_source="expected_results",
        evidence_transitions=["t19"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1判：X(报名记录)变直接致Y(缴费通知单)变，Y无需额外操作（系统自动）；evidence=t19；门禁对照：'报名成功后缴费通知单已发送'已由 t19 precondition 表达，但因果为系统自动推进，写因果"},
    )
    # 因果3：E-BMJL 报名创建 → E-FY/E-FP/E-JFTZ 自动创建（系统自动）
    m.add_causal(
        frm="E-BMJL", to="E-FY",
        desc="报名记录创建时系统自动初始化费用记录为待缴费",
        trigger="报名记录创建后费用记录自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t20"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1判：X(报名记录)变直接致Y(费用)变，Y无需额外操作；evidence=t20；structural(b)已表达组成关系"},
    )
    m.add_causal(
        frm="E-BMJL", to="E-FP",
        desc="报名记录创建时系统自动初始化发票记录为待开票",
        trigger="报名记录创建后发票记录自动初始化",
        trigger_source="expected_results",
        evidence_transitions=["t23"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1判：X(报名记录)变直接致Y(发票)变，Y无需额外操作；evidence=t23；structural(b)已表达组成关系"},
    )
    # 因果4：E-XM 项目进入已结束 → E-WJD 文件整理可触发（用户操作，止于 Q2，约束已表达）
    # 因果5：E-PJ 评价已确认 → E-BMJL 报名记录可进入报告/证书审核中（门禁已由 t16 precondition 表达，止于 Q2）
    # 因果6：E-BMJL 报告/证书已发布 → E-XM 项目进入已结束（系统自动推进，写因果）
    m.add_causal(
        frm="E-BMJL", to="E-XM",
        desc="报名记录报告/证书已发布后项目自动进入已结束",
        trigger="报名记录报告/证书已发布后项目状态自动推进为已结束",
        trigger_source="expected_results",
        evidence_transitions=["t17", "t05"],
        rollback_propagation=False, confidence="medium",
        note={"comment": "Q3判：下级全完成上级自动推进→因果；evidence=t17,t05；confidence=medium因§19.1表格未显式该过渡，依据§19.3枚举+阶段名推导"},
    )
    # 因果7：E-BMJL 结果已提交 → E-PJ 评价创建（系统自动，写因果）
    m.add_causal(
        frm="E-BMJL", to="E-PJ",
        desc="报名记录结果已提交后评价人员可发起评价，评价记录创建为待评价",
        trigger="结果已提交后评价创建",
        trigger_source="desc",
        evidence_transitions=["t13", "t31"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1判：X(报名记录)变直接致Y(评价)创建；evidence=t13,t31；门禁对照：'结果已提交后评价'已由 t31 precondition 表达，但因果为评价记录自动可创建，写因果；comment含BR标签b13"},
    )
    # 因果8：E-TASK 审核通过 → E-BMJL 报告/证书已发布（门禁已表达，止于 Q2，不写因果）
    # 因果9：E-BMJL 报名成功 → E-YP 样品创建（缴费触发，门禁已表达，止于 Q2）

    # ===== Step 4 约束 =====

    # ----- 4.1 invalid → m.add_invalid() -----
    # 文档未明文"不允许/不可以从X到Y"的状态转换禁止 → 不生成 invalid

    # ----- 4.2 XC → m.add_xc() -----
    # 镜像XC：E-XM.报名中 → E-BMJL.报名记录可创建（precondition 复制）
    m.add_xc(
        xid="x01", source_entity="E-XM",
        source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t09", target_condition="报名待审核",
        xc_source="镜像",
        desc="项目进入报名中后联动开启报名记录创建，新记录初始化为报名待审核",
        source_ref="19.1实施阶段",
    )
    # 联动XC：E-BMJL.报名成功 → E-JFTZ.缴费通知单 已发送（生产者≠持有者）
    m.add_xc(
        xid="x02", source_entity="E-BMJL",
        source_transition="t10b", source_state="报名成功",
        target_entity="E-JFTZ", target_dimension="缴费通知单状态",
        target_transition="t19", target_condition="已发送",
        xc_source="联动",
        desc="报名审核通过后联动发送缴费通知单，缴费通知单状态变为已发送",
        source_ref="19.1实施阶段",
    )
    # 联动XC：E-BMJL.报名成功 → E-YP.样品状态 创建（生产者≠持有者）
    m.add_xc(
        xid="x03", source_entity="E-BMJL",
        source_transition="t10b", source_state="报名成功",
        target_entity="E-YP", target_dimension="样品状态",
        target_transition="t25", target_condition="待核查",
        xc_source="联动",
        desc="报名成功后缴费时联动创建样品记录，初始化为待核查",
        source_ref="19.1实施阶段",
    )
    # 联动XC：E-BMJL.结果已提交 → E-PJ.评价状态 创建
    m.add_xc(
        xid="x04", source_entity="E-BMJL",
        source_transition="t13", source_state="结果已提交",
        target_entity="E-PJ", target_dimension="评价状态",
        target_transition="t31", target_condition="待评价",
        xc_source="联动",
        desc="报名记录结果已提交后联动创建评价记录，初始化为待评价",
        source_ref="19.1报告编制和结果通知；20.7.1.2协同评价",
    )
    # 联动XC：E-PJ.已确认 → E-BMJL.报告/证书审核中
    m.add_xc(
        xid="x05", source_entity="E-PJ",
        source_transition="t34", source_state="已确认",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t16", target_condition="报告/证书审核中",
        xc_source="联动",
        desc="评价确认后联动编制结果报告，报名记录状态变为报告/证书审核中",
        source_ref="19.1报告编制和结果通知",
    )
    # 4.5判XC：E-TASK.通过（技术主管） → E-TASK 可被授权签字人/实验室负责人批准（上级作下级门禁）
    m.add_xc(
        xid="x06", source_entity="E-TASK",
        source_transition="t37", source_state="通过",
        target_entity="E-TASK", target_dimension="任务审核状态",
        target_transition="t38", target_condition="通过",
        xc_source="4.5判",
        desc="技术主管审核通过后方可由授权签字人批准报告和结果通知单",
        source_ref="19.1报告编制和结果通知",
    )
    # 4.5判XC：E-TASK.通过（授权签字人/实验室负责人） → E-BMJL.报告/证书已发布
    m.add_xc(
        xid="x07", source_entity="E-TASK",
        source_transition="t38", source_state="通过",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t17", target_condition="报告/证书已发布",
        xc_source="4.5判",
        desc="审核任务通过后方可发放结果报告和证书，报名记录状态变为报告/证书已发布",
        source_ref="19.1报告编制和结果通知",
    )
    # 镜像XC：E-XM.已结束 → E-WJD.归档状态 可创建
    m.add_xc(
        xid="x08", source_entity="E-XM",
        source_transition="t05", source_state="已结束",
        target_entity="E-WJD", target_dimension="归档状态",
        target_transition="t52", target_condition="整理中",
        xc_source="镜像",
        desc="项目结束后方可触发文件整理任务，归档状态初始化为整理中",
        source_ref="20.5.1.1文件整理",
    )
    # 分支差异XC：业务类型=测量审核 → E-BMJL 编制结果通知单（取代编制结果报告）
    m.add_xc(
        xid="x09", source_entity="E-XM",
        source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t16b", target_condition="报告/证书审核中",
        xc_source="分支差异",
        desc="测量审核分支编制结果通知单取代编制结果报告，落点同为报告/证书审核中",
        source_ref="19.2测量审核提供者流程；19.3项目状态分析",
    )

    # ----- 4.3 BR → m.add_br() -----
    # §20.2.1 通知公告"new"标识
    m.add_br(
        bid="b01", category="display",
        desc="15天内发布的通知在内容前标注'new'标识，超过15天后此标识自动隐藏",
        entities_involved=["E-XM"], source_ref="20.2.1通知公告", restrictive=True,
        note={"comment": "signal_type命中'15天内'；category判显示；时间相关但本质为显示规则"},
    )
    # §20.4.1.2 实验室审核退回必须填写审核意见
    m.add_br(
        bid="b02", category="validation",
        desc="实验室审核结果为退回修改时必须填写审核意见，审核结果为通过时可以为空",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核", restrictive=True,
        note={"role": ["系统管理人员"], "comment": "signal_type命中'必须'；category判校验"},
    )
    # §20.4.1.2 实验室审核通过生成快照
    m.add_br(
        bid="b03", category="computation",
        desc="实验室审核结果为通过时为当前数据生成该数据的快照记录",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核",
        note={"role": ["系统管理人员"], "comment": "signal_type命中'生成'（取值范围衍生）；category判计算衍生"},
    )
    # §20.4.2.5 停用的标准库不可被选择
    m.add_br(
        bid="b04", category="restrictive",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"], source_ref="20.4.2.5停用启用标准库", restrictive=True,
        constrained_entity="E-BZK",
        note={"comment": "signal_type命中'不可被选择'；category判限制；多实体BR，constrained_entity=操作对象（标准库）"},
    )
    # §20.4.2.10 含有子项的记录不允许删除
    m.add_br(
        bid="b05", category="validation",
        desc="标准库测试项删除时含有子项的记录不允许删除",
        entities_involved=["E-BZK"], source_ref="20.4.2.10删除测试项", restrictive=True,
        note={"role": ["系统管理人员"], "comment": "signal_type命中'不允许'；category判校验"},
    )
    # §20.4.3.4 子领域测试项存在子项的数据不可以删除
    m.add_br(
        bid="b06", category="validation",
        desc="子领域测试项删除时存在子项的数据不可以删除",
        entities_involved=["E-BZK"], source_ref="20.4.3.4删除测试项", restrictive=True,
        note={"role": ["系统管理人员"], "comment": "signal_type命中'不可以'；category判校验"},
    )
    # §20.5.1.1 文件整理：已结束项目可触发
    m.add_br(
        bid="b07", category="display",
        desc="项目管理数据列表的操作列仅为已结束的项目记录提供文件整理按钮",
        entities_involved=["E-XM", "E-WJD"], source_ref="20.5.1.1文件整理", restrictive=True,
        constrained_entity="E-XM",
        note={"comment": "signal_type命中'仅为已结束'；category判显示；多实体BR，constrained_entity=操作对象（项目）"},
    )
    # §20.5.1.3 批量提交审核校验
    m.add_br(
        bid="b08", category="validation",
        desc="批量提交审核时只有已上传对应文件且未提交审核的记录才可以被选定，如没有选择记录将提示用户选择记录信息",
        entities_involved=["E-BMJL"], source_ref="20.5.1.3项目批量操作", restrictive=True,
        note={"role": ["项目管理员"], "comment": "signal_type命中'只有'；category判校验"},
    )
    # §20.5.1.4 消息发送接收人校验
    m.add_br(
        bid="b09", category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能", restrictive=True,
        note={"role": ["项目管理员"], "comment": "signal_type命中'不能同时为空'；category判校验"},
    )
    # §20.5.1.4 未结束项目可消息发送
    m.add_br(
        bid="b10", category="usability",
        desc="未结束的项目可以进行消息发送",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能", restrictive=True,
        note={"role": ["项目管理员"], "comment": "signal_type命中'未结束'；category判可用性"},
    )
    # §20.5.1.6 候选人单一时默认填充
    m.add_br(
        bid="b11", category="computation",
        desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"], source_ref="20.5.1.6默认填充技术主管实验室负责人授权签字人",
        note={"role": ["项目管理员"], "comment": "signal_type命中'有且仅有一个'（取值范围衍生）；category判计算衍生"},
    )
    # §20.5.2.1 多次付款不对金额校验限制
    m.add_br(
        bid="b12", category="validation",
        desc="已报名项目支持多次付款，不对付款金额进行校验限制",
        entities_involved=["E-FY"], source_ref="20.5.2.1已报名项目增加多次付款功能", restrictive=True,
        note={"role": ["能力验证参加者"], "comment": "signal_type命中'不对'；category判校验；§20.6.2.1同规则"},
    )
    # §20.5.2.3 / §20.6.2.3 证书到期前30天提醒（系统行为）
    m.add_br(
        bid="b13", category="notification",
        desc="系统每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送项目管理员",
        entities_involved=["E-XM"], source_ref="20.5.2.3增加证书到期前30天提醒功能；20.6.2.3", restrictive=True,
        note={"comment": "signal_type命中'每天上午9点'+'等于30天'；category判通知；无状态落点，不入台账/operations；系统行为BR；§20.5.2.3和§20.6.2.3同规则合并"},
    )
    # §20.5.3.2 / §20.6.3.2 操作节点短信通知
    m.add_br(
        bid="b14", category="notification",
        desc="管理人员对用户报名项目操作后使用短信方式对用户进行通知：报名审核通过/退回修改、发样通知、测试结果审核通过/退回、结果通知单发布",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2操作节点增加用户短信通知；20.6.3.2", restrictive=True,
        note={"comment": "signal_type命中'使用短信方式'；category判通知；系统行为BR；§20.5.3.2和§20.6.3.2同规则合并"},
    )
    # §20.7.1.2 协同评价权限控制
    m.add_br(
        bid="b15", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"], source_ref="20.7.1.2协同评价", restrictive=True,
        note={"role": ["评价人员"], "comment": "signal_type命中'只能'+'不能'；category判授权"},
    )
    # §20.7.1.2 第一个评价人员默认为评价组长
    m.add_br(
        bid="b16", category="computation",
        desc="新建项目时第一个被选择的评价人员默认做为评价组长",
        entities_involved=["E-PJ"], source_ref="20.7.1项目列表",
        note={"comment": "signal_type命中'第一个'（取值范围衍生）；category判计算衍生"},
    )
    # §20.7.1.3 评价确认统计规则
    m.add_br(
        bid="b17", category="validation",
        desc="每个统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认",
        note={"role": ["评价组长"], "comment": "signal_type命中'大于等于'+'小于'（取值范围）；category判校验"},
    )
    # §20.7.1.3 评价组长确认后评价状态关闭
    m.add_br(
        bid="b18", category="restrictive",
        desc="评价组长点击确认后将当前结果正式提交为项目的最终评价结果，项目评价状态关闭",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认", restrictive=True,
        note={"role": ["评价组长"], "comment": "signal_type命中'正式提交'；category判限制"},
    )
    # §20.7.1 评分方式两种
    m.add_br(
        bid="b19", category="computation",
        desc="评价支持分值和权重两种方式，分值按累加计算得分，权重按加权计算得分",
        entities_involved=["E-PJ"], source_ref="20.7.1项目列表",
        note={"role": ["评价人员"], "comment": "signal_type命中'两种'（取值范围）；category判计算衍生"},
        branch_dimensions=["评分方式"],
    )
    # §20.9.1.1 测量审核结果通知单审批合并
    m.add_br(
        bid="b20", category="restrictive",
        desc="测量审核结果通知单审批流程将原来多个流程合并为一个流程，流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-TASK"], source_ref="20.9.1.1测量审核结果通知单审核流程优化", restrictive=True,
        note={"comment": "signal_type命中'合并为一个'；category判限制"},
        branch_dimensions=["业务类型"],
    )
    # §20.9.1.3 任务创建短信通知
    m.add_br(
        bid="b21", category="notification",
        desc="用户通过表单或审核一个已存在的任务生成新的审核任务后，系统发送短信通知相关负责人，短信内容：您有一个新的xxx审核任务，请及时处理",
        entities_involved=["E-TASK"], source_ref="20.9.1.3增加任务提醒", restrictive=True,
        note={"comment": "signal_type命中'发送短信'；category判通知；系统行为BR"},
    )
    # §20.9.1.4 批量审核节点判断
    m.add_br(
        bid="b22", category="validation",
        desc="系统会根据任务节点的类型及内容判断当前节点是否可以被批量处理",
        entities_involved=["E-TASK"], source_ref="20.9.1.4任务批量处理",
        note={"role": ["系统管理人员"], "comment": "signal_type命中'判断'（取值范围衍生）；category判校验"},
    )
    # §20.9.1.6 自定义流程预设
    m.add_br(
        bid="b23", category="validation",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
        entities_involved=["E-TASK"], source_ref="20.9.1.6增加自定义流程", restrictive=True,
        note={"comment": "signal_type命中'4个以内'（取值范围）；category判字段约束"},
    )
    # §20.10.2.3 退款金额不能大于当前缴费金额
    m.add_br(
        bid="b24", category="validation",
        desc="缴费单退款金额不能大于当前缴费金额，多次退款金额做累加处理",
        entities_involved=["E-FY"], source_ref="20.10.2.3缴费单退款", restrictive=True,
        note={"role": ["财务管理人员"], "comment": "signal_type命中'不能大于'；category判校验"},
    )
    # §20.10.2.3 退款实际付款计算
    m.add_br(
        bid="b25", category="computation",
        desc="实际付款=付款金额-退款金额，退款金额使用红色字体且大于0时显示",
        entities_involved=["E-FY"], source_ref="20.10.2.3缴费单退款",
        note={"role": ["财务管理人员"], "comment": "signal_type命中'='（计算公式）；category判计算衍生；退款后更新项目费用为实际付款金额"},
    )
    # §20.11.1.2 关键操作留痕
    m.add_br(
        bid="b26", category="authorization",
        desc="系统对关键操作实施留痕机制，自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-XM"], source_ref="20.11.1.2安全性相关内容优化", restrictive=True,
        note={"comment": "signal_type命中'自动记录'；category判授权（审计）；系统行为BR"},
    )
    # §3.4 性能要求
    m.add_br(
        bid="b27", category="restrictive",
        desc="平台应支持至少300个同时在线用户数；并发100时每个页面响应时间不超过5秒；单次报名操作成功率应达到95%以上",
        entities_involved=["E-XM"], source_ref="3.4性能要求；21.3性能要求", restrictive=True,
        note={"comment": "signal_type命中'至少'+'不超过'+'以上'；category判限制；性能非功能性要求"},
    )
    # §20.10.2.2 发票多次分批上传
    m.add_br(
        bid="b28", category="restrictive",
        desc="发票上传支持多次分批上传，点击文件地址后的x可以移除文件（表单提交后生效）",
        entities_involved=["E-FP"], source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传", restrictive=True,
        note={"role": ["财务管理人员"], "comment": "signal_type命中'多次分批'；category判限制"},
    )

    # §19.1 能力验证提供者流程 行12：参加者测试与结果提交后按还样要求分支
    m.add_br(
        bid="b29", category="computation",
        desc="参加者测试与结果提交后按还样要求分支：需还样则样品归还后样品状态落'待核查'（进入下一批次），无需还样则落'无需还样'（终态）",
        entities_involved=["E-YP"], source_ref="19.1能力验证提供者流程",
        note={"role": ["能力验证参加者"], "comment": "signal_type命中'按…分支'（运行时选择）；category判计算（结果差异型）"},
        branch_dimensions=["还样要求"],
    )

    return m

