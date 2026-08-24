# -*- coding: utf-8 -*-

from srs_pipeline import DomainModel, N, attr, op, precond, state_ref
m = DomainModel(
    source="网数中心能力验证服务平台升级维护项目-需求分析与设计",
    document_scope="19.1-19.5 系统流程分析；20.2-20.11 系统功能需求分析；非功能性（21）不在范围"
)
"""
数据文件本体：网数中心能力验证服务平台升级维护项目-需求分析与设计
事件台账置于 build() 之前，构成数据文件本体。
"""

# ============================================================================
# 事件台账（§2）——通读全文登记的状态变更事件
# ----------------------------------------------------------------------------
# 编号规则：e01…（小写无横线）；执行者为 system 时不登记角色
# ============================================================================

# e01 | 主体=项目 | 动作=项目立项 | 执行者=项目管理员 | 前置=无 | 后果=项目状态=待开始 | 19.1项目准备阶段
# e02 | 主体=项目 | 动作=任务通知书编制 | 执行者=策划人员 | 前置=项目已立项 | 后果=附件新增任务通知书 | 19.1项目准备阶段
# e03 | 主体=项目 | 动作=设计方案编制 | 执行者=策划人员 | 前置=项目已立项 | 后果=项目状态=待开始 | 19.1方案设计阶段
# e04 | 主体=项目 | 动作=能力验证计划发布 | 执行者=项目管理员 | 前置=设计方案已编制 | 后果=项目状态=报名中 | 19.1实施阶段
# e05 | 主体=报名记录 | 动作=报名 | 执行者=能力验证参加者 | 前置=项目状态=报名中 | 后果=报名记录状态=报名待审核；费用状态=待缴费；发票状态=待开票 | 19.1实施阶段
# e06 | 主体=报名记录 | 动作=报名审核通过 | 执行者=项目管理员 | 前置=报名记录状态=报名待审核 | 后果=报名记录状态=报名成功；预通知状态=已发送 | 19.1实施阶段
# e07 | 主体=报名记录 | 动作=报名审核退回 | 执行者=项目管理员 | 前置=报名记录状态=报名待审核 | 后果=报名记录状态=报名退回 | 19.1实施阶段
# e08 | 主体=报名记录 | 动作=缴费 | 执行者=能力验证参加者 | 前置=报名记录状态=报名成功 | 后果=费用状态=已缴费 | 19.1实施阶段
# e09 | 主体=报名记录 | 动作=发票开具 | 执行者=财务管理人员 | 前置=报名记录状态=报名成功 | 后果=发票状态=已开票 | 19.1实施阶段
# e10 | 主体=报名记录 | 动作=能力验证预通知 | 执行者=项目管理员 | 前置=报名记录状态=报名成功 | 后果=预通知状态=已发送；报名记录状态=结果待提交 | 19.1实施阶段
# e11 | 主体=项目 | 动作=样品核查 | 执行者=样品管理员 | 前置=样品状态=待核查 | 后果=样品状态=已核查 | 19.1实施阶段
# e12 | 主体=项目 | 动作=样品发放 | 执行者=项目管理员 | 前置=样品状态=已核查 | 后果=样品状态=已发样；预通知状态=已确认 | 19.1实施阶段
# e13 | 主体=报名记录 | 动作=提交结果报告 | 执行者=能力验证参加者 | 前置=报名记录状态=结果待提交 | 后果=报名记录状态=结果已提交 | 19.1实施阶段
# e14 | 主体=报名记录 | 动作=结果退回修改 | 执行者=项目管理员 | 前置=报名记录状态=结果已提交 | 后果=报名记录状态=结果退回修改 | 19.1报告编制和结果通知
# e15 | 主体=报名记录 | 动作=编制结果报告 | 执行者=策划人员 | 前置=评价完成 | 后果=报名记录状态=报告/证书审核中 | 19.1报告编制和结果通知
# e16 | 主体=报名记录 | 动作=技术主管审核报告通过 | 执行者=技术主管 | 前置=报名记录状态=报告/证书审核中 | 后果=报名记录状态=报告/证书审核中 | 19.1报告编制和结果通知
# e17 | 主体=报名记录 | 动作=报告批准 | 执行者=授权签字人 | 前置=技术主管审核通过 | 后果=报名记录状态=报告/证书审核中 | 19.1报告编制和结果通知
# e18 | 主体=报名记录 | 动作=发放结果报告和证书 | 执行者=项目管理员 | 前置=报告已批准 | 后果=报名记录状态=报告/证书已发布 | 19.1报告编制和结果通知
# e19 | 主体=报名记录 | 动作=撤销报名 | 执行者=能力验证参加者 | 前置=报名记录状态=报名成功 | 后果=报名记录状态=已撤销 | 19.3项目状态分析
# e20 | 主体=项目 | 动作=进入实施 | 执行者=项目管理员 | 前置=项目状态=报名中 | 后果=项目状态=进行中 | 19.3项目状态分析（inferred：表19.1未显式列写但枚举中存在进行中态）
# e21 | 主体=项目 | 动作=进入报告审核 | 执行者=项目管理员 | 前置=项目状态=进行中 | 后果=项目状态=报告审核中 | 19.3项目状态分析（inferred：表19.1未显式列写但枚举中存在报告审核中态）
# e22 | 主体=项目 | 动作=项目结束 | 执行者=项目管理员 | 前置=项目状态=报告审核中 | 后果=项目状态=已结束 | 19.3项目状态分析（inferred：表19.1未显式列写但枚举中存在已结束态）
# e23 | 主体=实验室 | 动作=实验室新增 | 执行者=能力验证参加者 | 前置=无 | 后果=实验室状态=待审核 | 20.4.1.1实验室列表与查询
# e24 | 主体=实验室 | 动作=实验室审核通过 | 执行者=系统管理人员 | 前置=实验室状态=待审核 | 后果=实验室状态=启用；生成快照 | 20.4.1.2实验室审核
# e25 | 主体=实验室 | 动作=实验室审核退回 | 执行者=系统管理人员 | 前置=实验室状态=待审核 | 后果=实验室状态=已退回 | 20.4.1.2实验室审核
# e26 | 主体=实验室 | 动作=实验室修改重提 | 执行者=能力验证参加者 | 前置=实验室状态=已退回 | 后果=实验室状态=待审核 | 20.4.1.3实验室修改
# e27 | 主体=实验室 | 动作=实验室停用 | 执行者=系统管理人员 | 前置=实验室状态=启用 | 后果=实验室状态=停用 | 20.4.1实验室管理
# e28 | 主体=实验室 | 动作=实验室启用 | 执行者=系统管理人员 | 前置=实验室状态=停用 | 后果=实验室状态=启用 | 20.4.1实验室管理
# e29 | 主体=标准库 | 动作=标准库新增 | 执行者=系统管理人员 | 前置=无 | 后果=标准库状态=启用 | 20.4.2.2新增标准库
# e30 | 主体=标准库 | 动作=标准库停用 | 执行者=系统管理人员 | 前置=标准库状态=启用 | 后果=标准库状态=停用 | 20.4.2.5停用/启用标准库
# e31 | 主体=标准库 | 动作=标准库启用 | 执行者=系统管理人员 | 前置=标准库状态=停用 | 后果=标准库状态=启用 | 20.4.2.5停用/启用标准库
# e32 | 主体=评价项 | 动作=协同评价 | 执行者=评价人员 | 前置=评价细则已完善 | 后果=评价完成 | 20.7.1.2协同评价
# e33 | 主体=评价项 | 动作=评价确认 | 执行者=评价组长 | 前置=评价完成 | 后果=评价确认 | 20.7.1.3评价确认
# e34 | 主体=评价项 | 动作=评价退回修改 | 执行者=评价组长 | 前置=评价完成 | 后果=开启下一轮评价 | 20.7.1.3评价确认
# e35 | 主体=审核任务 | 动作=审核通过 | 执行者=审核人 | 前置=审核任务待审核 | 后果=审核通过 | 20.9.1流程审批
# e36 | 主体=审核任务 | 动作=审核退回 | 执行者=审核人 | 前置=审核任务待审核 | 后果=审核退回 | 20.9.1流程审批
# e37 | 主体=缴费记录 | 动作=缴费退款 | 执行者=财务管理人员 | 前置=已缴费用 | 后果=退款金额累加；项目费用更新为实际付款金额 | 20.10.2.3缴费单退款
# e38 | 主体=缴费记录 | 动作=多次付款 | 执行者=能力验证参加者 | 前置=报名记录状态=报名成功 | 后果=新增付款记录（不校验金额） | 20.5.2.1已报名项目增加多次付款功能
# e39 | 主体=证书 | 动作=证书到期提醒 | 执行者=system | 前置=证书距到期时间=30天 | 后果=邮件提醒用户并抄送项目管理员 | 20.5.2.3证书到期前30天提醒
# e40 | 主体=项目 | 动作=文件整理 | 执行者=system | 前置=项目状态=已结束 | 后果=归档任务开启 | 20.5.1.1文件整理
# e41 | 主体=项目 | 动作=测量审核受理 | 执行者=项目管理员 | 前置=用户报名待审核 | 后果=项目状态=报名中；报名记录状态=报名待审核 | 19.2测量审核提供者流程
# e42 | 主体=报名记录 | 动作=证书批准 | 执行者=实验室负责人 | 前置=报名记录状态=报告/证书审核中；技术主管审核报告通过 | 后果=报名记录状态=报告/证书审核中；附件新增'能力验证合格证书' | 19.1报告编制和结果通知


# ============================================================================
# 注释版结构概览（可选；大文档导读）
# ----------------------------------------------------------------------------
# 主体名词 → E-ID 映射：
#   项目 → E-XM     样品 → E-YP        报名记录 → E-BMJL
#   实验室 → E-SYS  标准库 → E-BZK     测试项 → E-CSX
#   子领域 → E-ZLY  评价项 → E-PJX     审核任务 → E-SHRW
#   缴费记录 → E-JF 发票 → E-FP         证书 → E-ZS
#   常用项 → E-CYX  信息发送记录 → E-XXJL
# 角色映射：r01–r14（详见 add_role）
# ============================================================================


def build() -> DomainModel:
    
    # ============================================================
    # §0 总则 — 动词词表与禁止关键字
    # ------------------------------------------------------------
    # action_verbs：初始收台账动作列去宾语去重的词根；操作动词经回写补入
    # ============================================================
    m.set_prohibition_config(config={
        "action_verbs": [
            "项目立项", "任务通知书编制", "设计方案编制", "能力验证计划发布",
            "报名", "报名审核通过", "报名审核退回", "缴费", "发票开具",
            "能力验证预通知", "样品核查", "样品发放", "提交结果报告",
            "结果退回修改", "编制结果报告", "技术主管审核报告通过", "报告批准",
            "发放结果报告和证书", "撤销报名", "进入实施", "进入报告审核",
            "项目结束", "实验室新增", "实验室审核通过", "实验室审核退回",
            "实验室修改重提", "实验室停用", "实验室启用",
            "标准库新增", "标准库停用", "标准库启用",
            "协同评价", "评价确认", "评价退回修改",
            "审核通过", "审核退回", "缴费退款", "多次付款",
            "证书到期提醒", "文件整理", "测量审核受理",
            # 来源 Step 1.4 operations 回写
            "新增", "修改", "删除", "查询", "重置", "导出", "上传", "下载",
            "打包下载", "代码导入", "提交审核", "消息发送", "测试", "另存常用",
            "查看", "查看归档", "进入", "审核",
        ],
        "prohibit_keywords": [
            # 仅收带量化/条件/复合动词组合的复杂否定短语
            "不能连续3天",   # 占位示例：本文档无此形态，留空可
        ],
    })

    # ============================================================
    # Step 1.1 — 角色
    # ------------------------------------------------------------
    # 来源：§5 用户角色分析 + §3.2 功能要求角色枚举
    # 固定角色与非固定角色区分；id 与 name 并用，name 为引用键
    # ============================================================
    m.add_role(id="r01", name="实验室负责人", readonly=False)
    m.add_role(id="r02", name="技术主管", readonly=False)
    m.add_role(id="r03", name="授权签字人", readonly=False)  # 非固定角色
    m.add_role(id="r04", name="策划人员", readonly=False)
    m.add_role(id="r05", name="项目管理员", readonly=False)
    m.add_role(id="r06", name="样品制备人员", readonly=False)  # 非固定角色
    m.add_role(id="r07", name="样品管理员", readonly=False)
    m.add_role(id="r08", name="评价人员", readonly=False)  # 非固定角色
    m.add_role(id="r09", name="统计人员", readonly=False)  # 非固定角色
    m.add_role(id="r10", name="质量专员", readonly=False)
    m.add_role(id="r11", name="财务管理人员", readonly=False)
    m.add_role(id="r12", name="系统管理人员", readonly=False)
    m.add_role(id="r13", name="能力验证参加者", readonly=False)
    m.add_role(id="r14", name="监督员", readonly=True)  # 非固定角色，文档未明确具体操作

    # 权限：仅声明 session/ui/file/query/config 及不改状态的 crud
    # 转换型操作由 transitions.role 承载；范围约束由 authorization BR 承载
    m.add_permission(role="系统管理人员", operations=["用户&角色管理", "机构管理", "内容管理", "通知管理", "意见反馈", "系统运维", "查询", "新增", "修改", "删除", "停用", "启用", "导出"])
    m.add_permission(role="项目管理员", operations=["项目管理", "参加者管理", "物品管理", "通知管理", "查询", "新增", "修改", "删除", "审核", "消息发送", "导出", "代码导入", "提交审核", "批量处理", "上传", "下载", "打包下载", "文件整理"])
    m.add_permission(role="能力验证参加者", operations=["报名缴费", "报告提交接收", "查询", "新增", "修改", "上传", "下载", "缴费"])
    m.add_permission(role="财务管理人员", operations=["缴费管理", "发票管理", "费用统计", "查询", "修改", "导出", "发票开具", "缴费退款"])
    m.add_permission(role="样品管理员", operations=["库存管理", "样品核查", "查询", "新增", "修改"])
    m.add_permission(role="评价人员", operations=["评价管理", "统计分析", "查询", "协同评价", "导出"])
    m.add_permission(role="统计人员", operations=["统计分析", "查询"])
    m.add_permission(role="质量专员", operations=["报告统计", "查询"])
    m.add_permission(role="策划人员", operations=["文件管理", "查询", "新增", "修改", "编制"])
    m.add_permission(role="实验室负责人", operations=["项目管理", "证书管理", "查询", "签发"])
    m.add_permission(role="技术主管", operations=["方案审批", "项目管理", "证书管理", "查询", "审核"])
    m.add_permission(role="授权签字人", operations=["报告审批", "查询", "批准"])
    m.add_permission(role="样品制备人员", operations=["样品制备", "样品管理", "查询", "新增", "修改"])

    # ============================================================
    # Step 1.4 — 实体落盘
    # ------------------------------------------------------------
    # 分类：core＝状态枚举/多步骤多角色流程/状态自主/多角色审批链/独立业务载体/可独立循环
    #        managed＝管理员 CRUD/配置字典/状态简单
    # tags：approvable/multi-state/expirable/collaborative/configurable
    # ============================================================

    # --- E-XM 项目（core） ---
    # 多角色审批链、多状态维度（项目状态+样品状态）、独立业务载体
    m.add_entity(
        id="E-XM", name="项目",
        desc="能力验证或测量审核项目；承载项目状态、样品状态、项目人员配置；项目状态覆盖待开始→报名中→进行中→报告审核中→已结束全生命周期",
        type="core",
        tags=["approvable", "multi-state", "expirable", "collaborative", "configurable"],
        attributes=[
            attr(name="项目编号", desc="项目唯一标识；必填；唯一"),
            attr(name="项目名称", desc="项目名称；必填"),
            attr(name="项目类型", desc="能力验证/测量审核；创建时定、互斥、影响后续流转；is_config", is_config=True),
            attr(name="产品类型", desc="项目所属产品类型；创建时定；is_config", is_config=True),
            attr(name="所属年度", desc="项目所属年度；创建时定；is_config", is_config=True),
            attr(name="子领域", desc="项目所属子领域；引用 E-ZLY"),
            attr(name="依据标准", desc="项目依据标准信息；可多选"),
            attr(name="项目费用", desc="项目应收金额；可被退款功能更新为实际付款金额"),
            attr(name="财务备注", desc="项目财务备注；管理人员可修改；20.10.2.1新增字段"),
            attr(name="技术主管", desc="项目技术主管；候选人唯一时默认填充；非固定角色"),
            attr(name="实验室负责人", desc="项目实验室负责人；候选人唯一时默认填充"),
            attr(name="授权签字人", desc="项目授权签字人；候选人唯一时默认填充；非固定角色"),
            attr(name="评价人员", desc="项目评价人员列表；首位被选者为评价组长；非固定角色"),
            attr(name="统计人员", desc="项目统计人员；非固定角色"),
            attr(name="样品制备人员", desc="项目样品制备人员；非固定角色"),
            attr(name="监督员", desc="项目监督员；20.5.1.5新增字段；可为空"),
            attr(name="评分方式", desc="分值/权重；is_config；影响评价计算", is_config=True),
            attr(name="及格分", desc="评价及格分；评价组长录入"),
            attr(name="任务通知书", desc="任务通知书附件"),
            attr(name="设计方案", desc="设计方案附件"),
            attr(name="能力验证计划通知", desc="能力验证计划通知或邀请函附件"),
            attr(name="作业指导书", desc="作业指导书附件"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": ["进行中", "报告审核中", "已结束"],
                "note": {"comment": "依据§19.3项目状态枚举；§19.1动作表仅显式列写到'报名中'，'进行中/报告审核中/已结束'由枚举推导为后续状态，入 inferred"},
            },
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查", "已发样"],
                "initial": "待核查",
                "terminal": [],
                "inferred": ["已发样"],
                "note": {"comment": "依据§19.1动作表'样品核查→已核查'、'样品发放→已发样'；§19.3枚举仅列'待核查/已核查'两值，'已发样'由动作表补充入 states＋inferred"},
            },
        ],
        operations=[
            op(name="查询", category="query", expected_results=["按项目编号/名称/产品类型/项目类型/年度筛选并分页展示"], source_ref="20.8.3.1项目查询与统计", note={"role": ["项目管理员", "系统管理人员"], "comment": "通用操作；F6 覆盖"}),
            op(name="新增", category="crud", expected_results=["创建项目，状态初始化为待开始"], source_ref="20.5.1项目管理", note={"role": "项目管理员", "comment": "新增表单含监督员字段；技术主管/实验室负责人/授权签字人候选人唯一时默认填充"}),
            op(name="修改", category="crud", expected_results=["更新项目基础信息"], source_ref="20.5项目管理", note={"role": "项目管理员"}),
            op(name="删除", category="crud", expected_results=["删除项目记录；操作前提示警示框二次确认"], source_ref="20.2.3待办事项", note={"role": "系统管理人员", "comment": "20.2.3 管理侧'能力验证项目删除'待办"}),
            op(name="文件整理", category="file", expected_results=["对已结束项目文件分类整理、归档、结构化分析、数字化存储；提示'归档任务已开启，请稍后查看'"], source_ref="20.5.1.1文件整理", note={"role": "项目管理员", "comment": "前置：项目状态=已结束；整理完成后显示'查看归档'按钮"}),
            op(name="查看归档", category="ui", expected_results=["进入归档数据查看页面；支持上传/打包下载归档文件"], source_ref="20.5.1.1文件整理", note={"role": "项目管理员"}),
            op(name="代码导入", category="file", expected_results=["导入报名机构三方代码"], source_ref="20.5.1.2机构代码导入", note={"role": "项目管理员"}),
            op(name="批量处理", category="ui", expected_results=["跳转报名信息批量处理页面，集中上传通知单与证书并批量提交审核"], source_ref="20.5.1.3项目批量操作", note={"role": "项目管理员"}),
            op(name="消息发送", category="ui", expected_results=["进入消息发送页面，按短信/邮件/站内信方式发送；接收人1和接收人2不能同时为空"], source_ref="20.5.1.4优化消息发送功能", note={"role": "项目管理员", "comment": "前置：项目未结束；项目状态=待开始/报名中时接收人为所有实验室，其他状态为报名实验室"}),
            op(name="另存常用", category="crud", expected_results=["保存常用测试项组合"], source_ref="20.5.1.7常用子领域测试项编辑能力", note={"role": "项目管理员"}),
            op(name="打包下载", category="file", expected_results=["归档文件打包为zip下载，目录按项目阶段命名"], source_ref="20.5.1.1文件整理", note={"role": "项目管理员"}),
            op(name="上传付款单", category="file", expected_results=["多次录入付款信息，不校验金额"], source_ref="20.5.2.1已报名项目增加多次付款功能", note={"role": "能力验证参加者", "comment": "通用操作；默认汇款金额=项目费用"}),
            op(name="预通知文件下载", category="file", expected_results=["下载预通知文件"], source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载", note={"role": "能力验证参加者"}),
        ],
    )

    # --- E-BMJL 报名记录（core） ---
    # 多维度状态机、多角色协同（参加者+项目管理员+技术主管+授权签字人+策划人员+财务管理人员）
    m.add_entity(
        id="E-BMJL", name="报名记录",
        desc="参加者对项目的报名记录；承载报名记录状态、报名记录样品状态、费用状态、发票状态、预通知状态五个维度",
        type="core",
        tags=["multi-state", "collaborative", "expirable"],
        attributes=[
            attr(name="报名编号", desc="报名记录唯一标识；必填；唯一"),
            attr(name="项目编号", desc="关联项目；引用 E-XM"),
            attr(name="实验室", desc="报名实验室；引用 E-SYS"),
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="报名时间", desc="报名时间"),
            attr(name="报名表", desc="报名表附件"),
            attr(name="缴费证明", desc="缴费证明附件"),
            attr(name="测试结果", desc="参加者提交的测试结果附件"),
            attr(name="结果通知单", desc="结果通知单附件"),
            attr(name="证书", desc="能力验证合格证书附件"),
            attr(name="预通知文件", desc="预通知文件附件"),
            attr(name="评价得分", desc="评价得分"),
            attr(name="评价结果", desc="评价结果"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "inferred": [],
                "note": {"comment": "依据§19.3报名记录状态枚举；初始态为报名事件落入的'报名待审核'"},
            },
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "inferred": [],
                "note": {"comment": "依据§19.3报名记录样品状态枚举"},
            },
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "inferred": [],
                "note": {"comment": "依据§19.3费用状态枚举；支持多次付款（e38）"},
            },
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "inferred": [],
                "note": {"comment": "依据§19.3发票状态枚举；支持分批上传（20.10.2.2）"},
            },
            {
                "dimension_name": "预通知状态",
                "states": ["未发送", "待确认", "待审核", "退回", "已审核", "已批准", "已发送"],
                "initial": "未发送",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "依据§19.3通知状态枚举+'已发送'来自§19.1动作表'能力验证预通知→已发送/待确认'"},
            },
        ],
        operations=[
            op(name="查询", category="query", expected_results=["按项目编号/名称/地域/报名时间筛选"], source_ref="20.8.3.2报名信息统计", note={"role": ["项目管理员", "系统管理人员"], "comment": "通用操作"}),
            op(name="详情", category="ui", expected_results=["查看报名详情，含文件下载Tab"], source_ref="20.5.2已报名项目", note={"role": ["能力验证参加者", "项目管理员"]}),
            op(name="上传付款单", category="file", expected_results=["多次付款，不校验金额"], source_ref="20.5.2.1已报名项目增加多次付款功能", note={"role": "能力验证参加者"}),
            op(name="预通知文件下载", category="file", expected_results=["下载预通知文件"], source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载", note={"role": "能力验证参加者"}),
            op(name="消息发送", category="ui", expected_results=["进入消息发送页面"], source_ref="20.6.1.2优化消息发送功能", note={"role": "项目管理员", "comment": "测量审核项目专用；接收人1为必填"}),
            op(name="提交审核", category="crud", expected_results=["批量提交已上传通知单/证书的记录至审核"], source_ref="20.5.1.3项目批量操作", note={"role": "项目管理员"}),
            op(name="上传结果通知单", category="file", expected_results=["上传结果通知单附件"], source_ref="20.5.1.3项目批量操作", note={"role": "项目管理员"}),
            op(name="上传证书", category="file", expected_results=["上传证书附件"], source_ref="20.5.1.3项目批量操作", note={"role": "项目管理员"}),
        ],
    )

    # --- E-SYS 实验室（core） ---
    # 含审核流程；状态变更事件多
    m.add_entity(
        id="E-SYS", name="实验室",
        desc="参加者实验室信息；机构新增/修改后需经管理用户审核通过方可用于项目报名",
        type="core",
        tags=["approvable", "configurable"],
        attributes=[
            attr(name="实验室编号", desc="实验室编号；模糊查询"),
            attr(name="实验室名称", desc="实验室名称；必填；模糊查询"),
            attr(name="统一社会信用代码", desc="统一社会信用代码；必填"),
            attr(name="法人名称", desc="法人名称"),
            attr(name="企业类型", desc="企业类型"),
            attr(name="企业规模", desc="企业规模"),
            attr(name="CNAS", desc="是否已获CNAS认可"),
            attr(name="CNAS证书号", desc="CNAS证书号"),
            attr(name="CMA", desc="是否已获CMA认可"),
            attr(name="CMA证书编号", desc="CMA证书编号"),
            attr(name="邮箱", desc="邮箱"),
            attr(name="座机号码", desc="座机号码"),
            attr(name="行政区域", desc="行政区域"),
            attr(name="详细地址", desc="详细地址"),
            attr(name="联系人", desc="联系人"),
            attr(name="联系电话", desc="联系电话"),
            attr(name="默认实验室", desc="是否默认实验室"),
            attr(name="证明文件", desc="营业执照或其他证书材料；可下载"),
        ],
        state_dimensions=[
            {
                "dimension_name": "实验室状态",
                "states": ["待审核", "启用", "停用", "已退回"],
                "initial": "待审核",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "依据§20.3.1实验室信息新增状态字段；§20.4.1.1列表查询选项为'待审核/启用/停用/已退回'，与§20.3.1'退回修改'同一状态，按§19.1动作表'报名退回'命名规范取'已退回'"},
            },
        ],
        operations=[
            op(name="查询", category="query", expected_results=["按实验室编号/名称/状态筛选并分页展示"], source_ref="20.4.1.1实验室列表与查询", note={"role": ["系统管理人员", "能力验证参加者"]}),
            op(name="新增", category="crud", expected_results=["提交后状态=待审核"], source_ref="20.4.1实验室管理", note={"role": "能力验证参加者"}),
            op(name="修改", category="crud", expected_results=["修改已退回状态的实验室信息后状态回到待审核"], source_ref="20.4.1.3实验室修改", note={"role": "能力验证参加者"}),
            op(name="删除", category="crud", expected_results=["删除实验室记录"], source_ref="20.3.1实验室信息", note={"role": "能力验证参加者"}),
            op(name="审核", category="crud", expected_results=["弹出审核窗口，选择通过或退回修改；通过则生成快照"], source_ref="20.4.1.2实验室审核", note={"role": "系统管理人员"}),
            op(name="停用", category="config", expected_results=["状态变更为停用"], source_ref="20.4.1实验室管理", note={"role": "系统管理人员"}),
            op(name="启用", category="config", expected_results=["状态变更为启用"], source_ref="20.4.1实验室管理", note={"role": "系统管理人员"}),
        ],
    )

    # --- E-BZK 标准库（managed） ---
    # CRUD + 启用/停用 状态简单
    m.add_entity(
        id="E-BZK", name="标准库",
        desc="标准库基础数据，可被项目和子领域引用；下属测试项以嵌套树结构组织",
        type="managed",
        tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="标准库编号；必填；模糊查询"),
            attr(name="标准库名称", desc="标准库名称；必填；模糊查询"),
            attr(name="描述", desc="标准库描述；选填"),
            attr(name="创建时间", desc="创建时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "标准库状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "inferred": [],
                "note": {"comment": "依据§20.4.2.1列表状态选项为'启用/停用'"},
            },
        ],
        operations=[
            op(name="查询", category="query", expected_results=["按编号/名称/状态筛选并分页展示"], source_ref="20.4.2.1标准库列表与查询", note={"role": "系统管理人员"}),
            op(name="新增", category="crud", expected_results=["创建标准库，状态默认启用"], source_ref="20.4.2.2新增标准库", note={"role": "系统管理人员"}),
            op(name="修改", category="crud", expected_results=["更新标准库信息"], source_ref="20.4.2.3修改标准库", note={"role": "系统管理人员"}),
            op(name="删除", category="crud", expected_results=["删除标准库；二次确认"], source_ref="20.4.2.4删除标准库", note={"role": "系统管理人员"}),
            op(name="停用", category="config", expected_results=["状态变更为停用；停用的标准库在项目创建等环节不可选择"], source_ref="20.4.2.5停用/启用标准库", note={"role": "系统管理人员"}),
            op(name="启用", category="config", expected_results=["状态变更为启用"], source_ref="20.4.2.5停用/启用标准库", note={"role": "系统管理人员"}),
            op(name="管理测试项", category="ui", expected_results=["进入该标准库的专属测试项管理界面"], source_ref="20.4.2.6进入测试项管理界面", note={"role": "系统管理人员"}),
        ],
    )

    # --- E-CSX 测试项（managed，结构子节点） ---
    # 嵌套树结构；可被标准库和子领域引用
    m.add_entity(
        id="E-CSX", name="测试项",
        desc="标准库或子领域下的测试项；可嵌套子项；标号+名称+操作",
        type="managed",
        tags=[],
        attributes=[
            attr(name="标号", desc="测试项标号；必填"),
            attr(name="名称", desc="测试项名称；必填"),
            attr(name="父测试项", desc="父测试项；引用 E-CSX；用于嵌套树"),
            attr(name="所属标准库", desc="引用 E-BZK；可为空（子领域选择时填）"),
            attr(name="所属子领域", desc="引用 E-ZLY；可为空"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询", category="query", expected_results=["按子领域筛选并分页展示"], source_ref="20.4.3.2测试项列表与结构展示", note={"role": "系统管理人员"}),
            op(name="新增", category="crud", expected_results=["新增测试项或子测试项；标准库下可直接新增，子领域下需从标准库选择"], source_ref="20.4.2.8新增测试项", note={"role": "系统管理人员"}),
            op(name="修改", category="crud", expected_results=["更新测试项信息"], source_ref="20.4.2.9修改测试项", note={"role": "系统管理人员"}),
            op(name="删除", category="crud", expected_results=["删除测试项；含子项的不允许删除"], source_ref="20.4.2.10删除测试项", note={"role": "系统管理人员", "comment": "F9：'删除'已在 action_verbs 中"}),
        ],
    )

    # --- E-ZLY 子领域（managed，结构子节点） ---
    m.add_entity(
        id="E-ZLY", name="子领域",
        desc="项目子领域；通过选择标准库测试项关联",
        type="managed",
        tags=["configurable"],
        attributes=[
            attr(name="子领域编号", desc="子领域编号；必填；唯一"),
            attr(name="子领域名称", desc="子领域名称；必填"),
            attr(name="状态", desc="启用/停用；is_config", is_config=True),
        ],
        state_dimensions=[],
        operations=[
            op(name="管理测试项", category="ui", expected_results=["进入该子领域的专属测试项管理界面"], source_ref="20.4.3.1进入测试项管理界面", note={"role": "系统管理人员"}),
            op(name="新增测试项", category="crud", expected_results=["从标准库选择测试项填充到子领域"], source_ref="20.4.3.3新增测试项", note={"role": "系统管理人员"}),
            op(name="删除测试项", category="crud", expected_results=["删除子领域下测试项；含子项不可删除"], source_ref="20.4.3.4删除测试项", note={"role": "系统管理人员"}),
        ],
    )

    # --- E-PJX 评价项（core） ---
    # 协同评价流程；多评价人员+组长
    m.add_entity(
        id="E-PJX", name="评价项",
        desc="项目评价项及评价细则；评价组长完善后由评价人员协同评价，最终由评价组长确认或退回修改",
        type="core",
        tags=["approvable", "collaborative", "configurable"],
        attributes=[
            attr(name="标号", desc="评价项标号；必填"),
            attr(name="名称", desc="评价项名称；必填"),
            attr(name="分值/权重", desc="分值或权重；必填；与评分方式对应", is_config=True),
            attr(name="说明/评分细则", desc="评分细则说明；选填"),
            attr(name="显示顺序", desc="展示顺序；必填"),
            attr(name="所属项目", desc="引用 E-XM"),
            attr(name="调整", desc="是否需要修改评分；评价组长标记"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["待完善", "评价中", "评价完成", "评价确认", "评价退回修改"],
                "initial": "待完善",
                "terminal": ["评价确认"],
                "inferred": ["评价中", "评价完成", "评价确认", "评价退回修改"],
                "note": {"comment": "依据§20.7.1项目评价；§19.1动作表'评价人员进行评价→结果已提交'表示评价完成；§20.7.1.3'确认'为终态、'退回修改'开启下一轮；状态命名按§1.3三级优先取语义命名＋inferred"},
            },
        ],
        operations=[
            op(name="完善", category="crud", expected_results=["评价组长编辑完善评价项目及评价细则"], source_ref="20.7.1.1测试项目、评价细则完善", note={"role": "评价人员", "comment": "操作者为评价组长（评价人员组长角色）"}),
            op(name="协同评价", category="crud", expected_results=["评价人员对各自评价结果录入；不可查看/修改其他评价人员结果"], source_ref="20.7.1.2协同评价", note={"role": "评价人员"}),
            op(name="结果确认", category="crud", expected_results=["评价组长确认评价结果为最终；评价状态关闭"], source_ref="20.7.1.3评价确认", note={"role": "评价人员", "comment": "操作者为评价组长"}),
            op(name="保存历史", category="crud", expected_results=["当前评价结果保存为历史结果"], source_ref="20.7.1.3评价确认", note={"role": "评价人员", "comment": "操作者为评价组长"}),
            op(name="调整细则", category="ui", expected_results=["打开评价细节完善页面，配置完成后回到本页面刷新数据"], source_ref="20.7.1.3评价确认", note={"role": "评价人员"}),
            op(name="退回修改", category="crud", expected_results=["当前评价结果保存为历史，开启下一轮评价"], source_ref="20.7.1.3评价确认", note={"role": "评价人员", "comment": "操作者为评价组长"}),
            op(name="导出", category="file", expected_results=["下载评价结果"], source_ref="20.7.1.4评价结果导出", note={"role": "评价人员"}),
            op(name="另存常用", category="crud", expected_results=["将测试项列表数据保存为常用组合"], source_ref="20.7.1.1测试项目、评价细则完善", note={"role": "评价人员", "comment": "操作者为评价组长"}),
            op(name="调整统计规则", category="config", expected_results=["配置成绩区间统计规则；低值≤x<高值"], source_ref="20.7.1.3评价确认", note={"role": "评价人员", "comment": "操作者为评价组长"}),
        ],
    )

    # --- E-SHRW 审核任务（core） ---
    # 多类型审核任务（结果通知单/报告/证书）；批量审核
    m.add_entity(
        id="E-SHRW", name="审核任务",
        desc="业务审核流程任务；测量审核结果通知单审核流程已重构合并为单流程；处理人审批顺序按提交申请时签字人选择顺序",
        type="core",
        tags=["approvable", "multi-state", "collaborative"],
        attributes=[
            attr(name="任务类型", desc="审核类型；如结果通知单审核、报告审核、证书审核"),
            attr(name="处理人顺序", desc="提交申请时签字人选择顺序；自定义流程"),
            attr(name="审核意见", desc="审核反馈；退回时必填"),
            attr(name="关联报名记录", desc="引用 E-BMJL"),
            attr(name="创建时间", desc="任务创建时间；用于查询"),
            attr(name="签章位置", desc="电子签章位置信息；自动代入"),
        ],
        state_dimensions=[
            {
                "dimension_name": "审核任务状态",
                "states": ["待审核", "审核通过", "审核退回"],
                "initial": "待审核",
                "terminal": ["审核通过", "审核退回"],
                "inferred": [],
                "note": {"comment": "依据§20.9.1.4批量审核结果选项'同意/退回'；§20.9.1.1测量审核结果通知单审核流程优化；§19.1动作表'技术主管审核报告'为审核通过/退回动作"},
            },
        ],
        operations=[
            op(name="查询", category="query", expected_results=["按任务类型/创建时间筛选"], source_ref="20.9.1.5审批流程列表导出", note={"role": ["项目管理员", "技术主管", "授权签字人", "实验室负责人"]}),
            op(name="审核", category="crud", expected_results=["提交审核结果，通过或退回；测量审核结果通知单按合并后单流程处理"], source_ref="20.9.1.1测量审核结果通知单审核流程优化", note={"role": ["技术主管", "授权签字人", "实验室负责人"], "comment": "角色依据任务类型；测量审核结果通知单流程处理人按签字人选择顺序"}),
            op(name="批量审核", category="crud", expected_results=["勾选多个任务批量审核，选择同意或退回"], source_ref="20.9.1.4任务批量处理", note={"role": ["技术主管", "授权签字人", "实验室负责人"]}),
            op(name="导出", category="file", expected_results=["导出满足查询条件的审批流程数据"], source_ref="20.9.1.5审批流程列表导出", note={"role": ["项目管理员", "技术主管", "授权签字人", "实验室负责人"]}),
        ],
    )

    # --- E-JF 缴费记录（managed） ---
    m.add_entity(
        id="E-JF", name="缴费记录",
        desc="项目缴费信息；支持多次分批付款和退款；退款后项目费用更新为实际付款金额",
        type="managed",
        tags=["expirable"],
        attributes=[
            attr(name="关联报名记录", desc="引用 E-BMJL"),
            attr(name="支付方式", desc="支付方式；必填"),
            attr(name="支付账户名称", desc="支付账户名称；必填"),
            attr(name="汇款金额", desc="汇款金额；必填；默认为项目费用金额"),
            attr(name="付款底单", desc="付款底单附件；必填"),
            attr(name="付款项目", desc="当前报名编号；只读"),
            attr(name="备注", desc="备注；选填"),
            attr(name="缴费时间", desc="缴费时间；查询条件"),
            attr(name="到款时间", desc="到款日期"),
            attr(name="退款金额", desc="退款金额；多次退款累加；红色字体且>0时显示"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="管理备注", desc="退款原因等内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询", category="query", expected_results=["按报名编号/缴费时间/业务类型/发票类型筛选并分页展示"], source_ref="20.10.1.1缴费信息查询与管理", note={"role": "财务管理人员"}),
            op(name="导出", category="file", expected_results=["导出符合筛选条件的缴费数据"], source_ref="20.10.1.1缴费信息查询与管理", note={"role": "财务管理人员"}),
            op(name="上传付款单", category="file", expected_results=["多次录入付款信息，不校验金额"], source_ref="20.5.2.1已报名项目增加多次付款功能", note={"role": "能力验证参加者"}),
            op(name="退款", category="crud", expected_results=["对缴费记录退款；退款金额不大于当前缴费金额；累加到退款金额；项目费用更新为实际付款金额"], source_ref="20.10.2.3缴费单退款", note={"role": "财务管理人员"}),
        ],
    )

    # --- E-FP 发票（managed） ---
    m.add_entity(
        id="E-FP", name="发票",
        desc="项目发票；支持分批上传；包含电子专票/电子普票两种类型",
        type="managed",
        tags=[],
        attributes=[
            attr(name="开票类型", desc="电子专票/电子普票"),
            attr(name="开票时间", desc="最后一次开票时间"),
            attr(name="电子发票", desc="电子发票文件"),
            attr(name="关联项目", desc="项目报名编号；只读"),
            attr(name="项目金额", desc="项目费用；只读"),
        ],
        state_dimensions=[
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "inferred": [],
                "note": {"comment": "依据§19.3发票状态枚举；与 E-BMJL 发票状态维度同枚举，但建在不同实体上以满足不同视角（项目级 vs 报名记录级）"},
            },
        ],
        operations=[
            op(name="发票上传", category="file", expected_results=["多次分批上传发票；表单提交后生效"], source_ref="20.10.2.2修改发票上传功能使其支持多次分批上传", note={"role": "财务管理人员"}),
            op(name="移除文件", category="crud", expected_results=["点击文件地址后'x'移除发票文件；表单提交后生效"], source_ref="20.10.2.2修改发票上传功能", note={"role": "财务管理人员"}),
        ],
    )

    # --- E-ZS 证书（managed，过期触发系统事件） ---
    m.add_entity(
        id="E-ZS", name="证书",
        desc="能力验证合格证书；距到期时间=30天时系统自动邮件提醒用户并抄送项目管理员",
        type="managed",
        tags=["expirable"],
        attributes=[
            attr(name="证书编号", desc="证书唯一编号；唯一"),
            attr(name="关联报名记录", desc="引用 E-BMJL"),
            attr(name="到期时间", desc="证书到期时间；用于30天提醒"),
            attr(name="签发人", desc="实验室负责人签发"),
            attr(name="审核人", desc="技术主管审核"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询", category="query", expected_results=["按证书编号等筛选"], source_ref="20.8.4项目查询", note={"role": ["能力验证参加者", "项目管理员"]}),
            op(name="证书到期提醒", category="config", expected_results=["每日9点扫描证书；距到期=30天则发邮件给用户并抄送项目管理员"], source_ref="20.5.2.3增加证书到期前30天提醒功能", note={"role": "system", "comment": "系统自动触发；traits 含 time_sensitive"}),
            op(name="下载", category="file", expected_results=["下载证书"], source_ref="20.8.4项目查询", note={"role": "能力验证参加者"}),
        ],
    )

    # --- E-CYX 常用项（managed） ---
    m.add_entity(
        id="E-CYX", name="常用项",
        desc="常用测试项组合；按子领域保存；可被项目和评价项录入时引用",
        type="managed",
        tags=[],
        attributes=[
            attr(name="名称", desc="常用项名称；必填"),
            attr(name="所属子领域", desc="引用 E-ZLY"),
            attr(name="测试项列表", desc="保存的测试项组合数据"),
        ],
        state_dimensions=[],
        operations=[
            op(name="另存常用", category="crud", expected_results=["将当前测试项列表保存为常用项"], source_ref="20.5.1.7增加常用子领域测试项编辑能力", note={"role": "项目管理员"}),
            op(name="选择常用", category="ui", expected_results=["选择常用项将测试项填充到表单"], source_ref="20.5.1.7增加常用子领域测试项编辑能力", note={"role": "项目管理员"}),
            op(name="删除常用", category="crud", expected_results=["删除常用项"], source_ref="20.5.1.7增加常用子领域测试项编辑能力", note={"role": "项目管理员"}),
        ],
    )

    # --- E-XXJL 信息发送记录（managed） ---
    m.add_entity(
        id="E-XXJL", name="信息发送记录",
        desc="系统信息发送历史；记录发送方式、接收人、发送时间、发送人、发送结果；仅系统管理人员和项目管理员可查看",
        type="managed",
        tags=[],
        attributes=[
            attr(name="接收号码", desc="接收号码；模糊匹配"),
            attr(name="发送方式", desc="短信/邮件/站内信；精确匹配"),
            attr(name="发送时间", desc="发送时间；范围查询"),
            attr(name="发送人", desc="发送人"),
            attr(name="发送结果", desc="发送结果"),
            attr(name="消息标题", desc="消息标题"),
            attr(name="消息内容", desc="消息内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询", category="query", expected_results=["按接收号码/发送时间/发送方式筛选并分页展示"], source_ref="20.4.4.1信息发送记录", note={"role": ["系统管理人员", "项目管理员"], "comment": "仅系统管理人员和项目管理员可查看"}),
            op(name="消息详情", category="ui", expected_results=["查看消息详细内容"], source_ref="20.4.4.1信息发送记录", note={"role": ["系统管理人员", "项目管理员"]}),
        ],
    )

    # ============================================================
    # Step 1.5 — 结构关系 add_structural
    # ------------------------------------------------------------
    # 判定 a→d 首条命中；cardinality 父→子视角；永不 N:1
    # ============================================================
    # (b) 项目无独立创建时报名记录自动入 initial？实际报名由参加者发起，B 有独立创建 → 走 (d)
    m.add_structural(
        frm="E-XM", to="E-BMJL",
        relation_type="reference",
        cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="项目包含多个报名记录；报名记录由参加者独立创建，删除项目不级联删除报名记录",
        confidence="high",
        note={"comment": "判(d)：B(报名记录)有独立创建流程；A(项目)为业务归属容器；排除：A为B的业务归属而非创建者"},
    )
    # (a) 项目提供配置（项目类型/产品类型/依据标准），子领域独立创建 → reference
    m.add_structural(
        frm="E-ZLY", to="E-XM",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="M:N",
        desc="子领域为项目提供配置分类；项目引用子领域，子领域独立管理",
        confidence="high",
        note={"comment": "判(a)：A(子领域)为B(项目)提供配置/分类，B独立创建"},
    )
    # (a) 标准库为子领域提供测试项模板，子领域独立选择
    m.add_structural(
        frm="E-BZK", to="E-ZLY",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="M:N",
        desc="标准库为子领域提供测试项模板；子领域通过选择标准库测试项关联",
        confidence="high",
        note={"comment": "判(a)：A(标准库)为B(子领域)提供配置/模板，B独立创建"},
    )
    # (b) 标准库创建时测试项作为其结构子节点，每条标准库可有测试项
    m.add_structural(
        frm="E-BZK", to="E-CSX",
        relation_type="composition",
        ownership_dimension="business_ownership",
        cardinality="1:N",
        desc="标准库下属测试项以嵌套树结构组织；测试项隶属标准库",
        confidence="high",
        note={"comment": "判(b)：B(测试项)无独立创建，A(标准库)创建时B自动入树结构；每条A必有B"},
    )
    # (a) 子领域选择测试项（来自标准库）；子领域独立
    m.add_structural(
        frm="E-ZLY", to="E-CSX",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="子领域下的测试项通过选择标准库测试项关联；子领域可管理其测试项",
        confidence="high",
        note={"comment": "判(a)：A(子领域)为B(测试项)提供选择来源，B在子领域下被关联"},
    )
    # (d) 评价项隶属项目；项目为业务归属容器
    m.add_structural(
        frm="E-XM", to="E-PJX",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="项目包含多个评价项；评价组长完善后由评价人员协同评价",
        confidence="high",
        note={"comment": "判(d)：B(评价项)有独立创建流程（评价组长完善），不满足(c)的dependent条件；A(项目)为业务归属容器"},
    )
    # (d) 审核任务关联报名记录；报名记录为业务归属容器
    m.add_structural(
        frm="E-BMJL", to="E-SHRW",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="报名记录关联多个审核任务（结果通知单/报告/证书审核）",
        confidence="high",
        note={"comment": "判(d)：B(审核任务)有独立创建流程（提交审核触发），A(报名记录)为业务归属容器"},
    )
    # (d) 缴费记录隶属报名记录
    m.add_structural(
        frm="E-BMJL", to="E-JF",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="报名记录关联多条缴费记录；支持多次付款",
        confidence="high",
        note={"comment": "判(d)：B(缴费记录)有独立创建流程（多次付款），A(报名记录)为业务归属容器"},
    )
    # (d) 发票隶属项目；项目业务归属
    m.add_structural(
        frm="E-XM", to="E-FP",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="项目关联多张发票；支持分批上传",
        confidence="high",
        note={"comment": "判(d)：B(发票)有独立创建流程（发票上传），A(项目)为业务归属容器"},
    )
    # (d) 证书隶属报名记录
    m.add_structural(
        frm="E-BMJL", to="E-ZS",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="报名记录关联证书；证书到期触发系统提醒",
        confidence="high",
        note={"comment": "判(d)：B(证书)由审核流程签发，A(报名记录)为业务归属容器"},
    )
    # (a) 项目提供常用项配置（按子领域）
    m.add_structural(
        frm="E-ZLY", to="E-CYX",
        relation_type="composition",
        ownership_dimension="business_ownership",
        cardinality="1:N",
        desc="子领域保存常用项；常用项隶属子领域",
        confidence="high",
        note={"comment": "判(b)：B(常用项)无独立创建，A(子领域)创建/选择时B自动入关联；每条A可有B"},
    )
    # (d) 实验室隶属参加者；CRUD操作
    m.add_structural(
        frm="E-SYS", to="E-BMJL",
        relation_type="reference",
        ownership_dimension="configuration_source",
        cardinality="1:N",
        desc="实验室关联多条报名记录；报名时选择实验室",
        confidence="high",
        note={"comment": "判(d)：B(报名记录)有独立创建流程，A(实验室)为业务归属容器；删A不级联删B"},
    )

    # ============================================================
    # Step 2 — 分支维度 add_branch_dimension
    # ------------------------------------------------------------
    # 三型：配置型 / 运行时选择型 / 隐式分支
    # target_transition 前向引用先用语义描述，3.3 回填 tid
    # ============================================================

    # --- 分支维度 1：业务类型（路径分歧型）---
    # 依据§19.1 vs §19.2 PT/MA 流程对比：实施阶段路径不同
    #   PT 路径：项目立项→设计方案编制→能力验证计划发布→报名→...
    #   MA 路径：受理用户测量审核报名→...（项目状态从报名中开始）
    m.add_branch_dimension(
        dimension="业务类型",
        entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="项目创建、实施阶段路径、报告编制阶段",
        evidence="三型判定：①配置型（项目新增时定、互斥、影响后续流转；见§20.5/§20.6分章叙述）；同时具备路径分歧（§19.1 vs §19.2 实施阶段动作序列不同）特征",
        branches=[
            {"value": "能力验证", "target_transition": "能力验证计划发布转换", "desc": "PT 路径：项目立项后经设计方案编制、能力验证计划发布进入报名中"},
            {"value": "测量审核", "target_transition": "测量审核受理转换", "desc": "MA 路径：直接受理用户测量审核报名进入报名中，无独立立项"},
        ],
    )

    # --- 分支维度 2：评分方式（结果差异型）---
    # 依据§20.7 项目列表："支持分值和权重两种评价方式"
    # 不影响路径，仅影响评价结果描述（分值 vs 权重）
    m.add_branch_dimension(
        dimension="评分方式",
        entity="E-PJX",
        values=["分值", "权重"],
        impact_scope="评价项录入、评价结果计算",
        evidence="三型判定：①配置型（项目新增时定、互斥、影响评价计算；§20.7.1项目列表'评分方式'字段）",
        branches=[
            {"value": "分值", "target_transition": "协同评价转换", "desc": "评价按分值累加计算"},
            {"value": "权重", "target_transition": "协同评价转换", "desc": "评价按权重加权计算"},
        ],
    )

    # --- 分支维度 3：审核结果（路径分歧型）---
    # 依据§20.4.1.2 实验室审核 + §20.7.1.3 评价确认 + §20.9.1.4 批量审核
    # 通过/退回 不同分支值导致后续状态不同
    m.add_branch_dimension(
        dimension="审核结果",
        entity="E-SHRW",
        values=["通过", "退回"],
        impact_scope="实验室审核、报名审核、结果审核、评价确认、流程审批",
        evidence="三型判定：②运行时选择型（§20.4.1.2'审核结果单选框：通过/退回修改'；§20.9.1.4'审核结果选项：同意/退回'）",
        branches=[
            {"value": "通过", "target_transition": "审核通过转换", "desc": "通过路径：状态变为审核通过/启用/成功"},
            {"value": "退回", "target_transition": "审核退回转换", "desc": "退回路径：状态变为审核退回/已退回/报名退回"},
        ],
    )

    # ============================================================
    # Step 3.1 — 转换 add_trans
    # ------------------------------------------------------------
    # 台账每条事件一条转换；frm=前置情形所属状态，to=后果情形所属状态
    # direction：⓪frm=None→forward；①回退/暂停/恢复；②侧挂；③frm先于to→forward；
    #            ④后于→backward；⑤仅自环→forward+inferred
    # priority：P0主流程必经；P1分支/回退/驳回；P2辅助/低频
    # ============================================================

    # === E-XM 项目状态维度 ===
    # e01 项目立项（能力验证路径，初始）
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="项目立项", role="项目管理员",
        preconditions=[
            precond(text="项目类型=能力验证", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["项目创建完成，项目状态初始化为待开始"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1项目准备阶段",
        note={"branch_dimension": "业务类型", "comment": "源自 e01；能力验证路径：Step 2 value=能力验证 指向本条；⓪frm=None→forward"},
    )

    # e03 设计方案编制
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
        ],
        expected_results=["设计方案编制完成；项目状态维持待开始"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1方案设计阶段",
        note={"comment": "源自 e03；⑤仅自环→forward+inferred（状态不变）"},
    )

    # e04 能力验证计划发布
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
            precond(text="设计方案已编制完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变为报名中；附件新增'能力验证计划通知或邀请函'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e04；③frm先于to→forward；Step 2 业务类型=能力验证 value 指向本转换（语义已落入 t03；Step 2 此处描述'能力验证计划发布转换'＝t03）"},
    )

    # e20 进入实施
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="进入实施", role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["项目状态变为进行中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"inferred": True, "comment": "源自 e20；§19.1动作表未显式列写'进行中'转换，由§19.3枚举推导；③frm先于to→forward"},
    )

    # e21 进入报告审核
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="进入报告审核", role="项目管理员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
            precond(text="评价完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变为报告审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"inferred": True, "comment": "源自 e21；§19.1动作表未显式列写'报告审核中'转换，由§19.3枚举推导；③frm先于to→forward"},
    )

    # e22 项目结束
    m.add_trans(
        tid="t06", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="项目结束", role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="报告已批准且结果通知单已发放", ptype="event_ref"),
        ],
        expected_results=["项目状态变为已结束（终态）"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3项目状态分析",
        note={"inferred": True, "comment": "源自 e22；§19.1动作表'发放结果报告和证书'后未列项目状态变更，由§19.3枚举推导终态'已结束'；③frm先于to→forward"},
    )

    # e41 测量审核受理（MA 路径，分支）
    m.add_trans(
        tid="t01b", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="测量审核受理", role="项目管理员",
        preconditions=[
            precond(text="项目类型=测量审核", ptype="constraint", note={"comment": "分支值条件"}),
            precond(text="用户测量审核报名已受理", ptype="event_ref"),
        ],
        expected_results=["测量审核项目创建，项目状态初始化为报名中；报名记录状态=报名待审核"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2测量审核提供者流程",
        note={"branch_dimension": "业务类型", "comment": "源自 e41；MA 路径：frm=None→forward；Step 2 value=测量审核 指向本条；与 t01 同根后缀 b"},
    )

    # === E-XM 样品状态维度 ===
    # e11 样品核查
    m.add_trans(
        tid="t07", entity="E-XM", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变为已核查、待发样；附件新增'核查记录表'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e11；③frm先于to→forward"},
    )

    # e12 样品发放
    m.add_trans(
        tid="t08", entity="E-XM", dimension="样品状态",
        frm="已核查", to="已发样", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "已核查")),
        ],
        expected_results=["样品状态变为已发样；预通知状态变为已确认；附件新增'快递单号或软件访问路径'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e12；③frm先于to→forward"},
    )

    # === E-BMJL 报名记录状态维度 ===
    # e05 报名（PT 路径触发）
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目状态=报名中", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["报名记录创建，状态=报名待审核；费用状态=待缴费；发票状态=待开票；附件新增'报名表'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e05；⓪frm=None→forward；初始化多维度状态"},
    )

    # e06 报名审核通过（路径分歧型分支；分支=审核结果=通过）
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="审核结果=通过", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名成功；预通知状态=已发送；缴费通知单=已发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "审核结果", "comment": "源自 e06；③frm先于to→forward；Step 2 业务类型=能力验证 value 指向'审核通过转换'本条"},
    )

    # e07 报名审核退回（路径分歧型分支；分支=审核结果=退回）
    m.add_trans(
        tid="t10b", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核退回", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="审核结果=退回", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["报名记录状态变为报名退回；短信通知用户'报名信息审核未通过'"],
        traits=["branch", "rollback"], direction="backward", priority="P1",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "审核结果", "comment": "源自 e07；①'退回'→backward；Step 2 业务类型=能力验证 value 指向'审核退回转换'本条"},
    )

    # e08 缴费
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录状态=报名成功", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="费用处于待缴费状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "待缴费")),
        ],
        expected_results=["费用状态变为已缴费；附件新增'缴费证明'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e08；③frm先于to→forward；支持多次付款（e38 不改变费用状态，仅记录多次付款）"},
    )

    # e09 发票开具
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务管理人员",
        preconditions=[
            precond(text="报名记录状态=报名成功", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["发票状态变为已开票；附件新增'发票'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e09；③frm先于to→forward；支持分批上传（20.10.2.2）"},
    )

    # e10 能力验证预通知
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["预通知状态=已发送；报名记录状态变为结果待提交；附件新增'预通知、用户信息表'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e10；③frm先于to→forward；同时联动预通知状态维度"},
    )

    # e13 提交结果报告
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="提交结果报告", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变为结果已提交；附件新增'测试结果、报名表盖章版'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e13；③frm先于to→forward"},
    )

    # e14 结果退回修改
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果退回修改", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变为结果退回修改；短信通知用户'测试报告审核未通过'"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e14；①'退回'→backward"},
    )

    # e15 编制结果报告
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价完成", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书审核中；附件新增'报告、结果通知'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e15；③frm先于to→forward；frm 也可是'结果退回修改'回退后的状态，按业务语义合并为同一转换"},
    )

    # e16 技术主管审核报告通过
    m.add_trans(
        tid="t17", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="技术主管审核报告通过", role="技术主管",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="审核结果=通过", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["技术主管审核通过；状态维持报告/证书审核中，流转至授权签字人批准"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"branch_dimension": "审核结果", "comment": "源自 e16；⑤仅自环→forward+inferred；技术主管通过后状态不变但流转下一节点"},
    )

    # e17 报告批准
    m.add_trans(
        tid="t18", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="报告批准", role="授权签字人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="技术主管审核报告通过", ptype="event_ref"),
        ],
        expected_results=["授权签字人批准报告；状态维持报告/证书审核中，附件新增'证书'"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e17；⑤仅自环→forward+inferred；批准后流转至项目管理员发放"},
    )

    # e18 发放结果报告和证书
    m.add_trans(
        tid="t19", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="报告已批准", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书已发布（终态）；短信通知用户'结果通知单已发布'"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e18；③frm先于to→forward；终态"},
    )

    # e19 撤销报名
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="已撤销", action="撤销报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["报名记录状态变为已撤销（终态）"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.3项目状态分析",
        note={"comment": "源自 e19；§19.1动作表'报名'后果列已含'已撤销'；③frm先于to→forward；终态"},
    )

    # === E-SYS 实验室状态维度 ===
    # e23 实验室新增
    m.add_trans(
        tid="t21", entity="E-SYS", dimension="实验室状态",
        frm=None, to="待审核", action="实验室新增", role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室状态初始化为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e23；⓪frm=None→forward"},
    )

    # e24 实验室审核通过
    m.add_trans(
        tid="t22", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核通过", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态变为启用；生成该数据快照记录"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e24；③frm先于to→forward；Step 2 value=通过 指向本条；role='系统管理人员'为r12已登记name（§5 catalog原文'17 系统管理人员'；§20.4.x原文'系统管理员'为同义简称，按§5统一）"},
    )

    # e25 实验室审核退回
    m.add_trans(
        tid="t22b", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="已退回", action="实验室审核退回", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=退回", ptype="constraint", note={"comment": "分支值条件"}),
            precond(text="必须填写审核意见", ptype="constraint"),
        ],
        expected_results=["实验室状态变为已退回"],
        traits=["branch", "rollback"], direction="backward", priority="P1",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e25；①'退回'→backward；Step 2 value=退回 指向本条"},
    )

    # e26 实验室修改重提
    m.add_trans(
        tid="t23", entity="E-SYS", dimension="实验室状态",
        frm="已退回", to="待审核", action="实验室修改重提", role="能力验证参加者",
        preconditions=[
            precond(text="实验室处于已退回状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "已退回")),
        ],
        expected_results=["实验室状态回到待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3实验室修改",
        note={"comment": "源自 e26；④frm后于to→backward，但语义为'重提/恢复'→语义优先 forward；comment 记序判④语义forward（修改后重新进入审核流程）"},
    )

    # e27 实验室停用
    m.add_trans(
        tid="t24", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="停用", action="实验室停用", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变为停用"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.1实验室管理",
        note={"comment": "源自 e27；①'停用'→lateral；启用↔停用为可逆横向挂起"},
    )

    # e28 实验室启用
    m.add_trans(
        tid="t25", entity="E-SYS", dimension="实验室状态",
        frm="停用", to="启用", action="实验室启用", role="系统管理人员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.1实验室管理",
        note={"comment": "源自 e28；①'启用'→resume；从停用恢复到启用"},
    )

    # === E-BZK 标准库状态维度 ===
    # e29 标准库新增
    m.add_trans(
        tid="t26", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="标准库新增", role="系统管理人员",
        preconditions=[],
        expected_results=["标准库创建，状态默认启用"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2新增标准库",
        note={"comment": "源自 e29；⓪frm=None→forward"},
    )

    # e30 标准库停用
    m.add_trans(
        tid="t27", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="标准库停用", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态变为停用；停用的标准库在项目创建等环节不可选择"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e30；①'停用'→lateral"},
    )

    # e31 标准库启用
    m.add_trans(
        tid="t28", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="标准库启用", role="系统管理人员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态变为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e31；①'启用'→resume"},
    )

    # === E-PJX 评价状态维度 ===
    # e32 协同评价
    m.add_trans(
        tid="t29", entity="E-PJX", dimension="评价状态",
        frm="待完善", to="评价完成", action="协同评价", role="评价人员",
        preconditions=[
            precond(text="评价项处于待完善状态", ptype="state_ref",
                    ref=state_ref("E-PJX", "评价状态", "待完善")),
            precond(text="评价细则已完善", ptype="event_ref"),
        ],
        expected_results=["评价状态变为评价完成；各评价人员评价结果录入，不可查看/修改他人结果"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"comment": "源自 e32；③frm先于to→forward；'评价完成'为inferred语义命名+inferred标注成对"},
    )

    # e33 评价确认
    m.add_trans(
        tid="t30", entity="E-PJX", dimension="评价状态",
        frm="评价完成", to="评价确认", action="评价确认", role="评价人员",
        preconditions=[
            precond(text="评价项处于评价完成状态", ptype="state_ref",
                    ref=state_ref("E-PJX", "评价状态", "评价完成")),
        ],
        expected_results=["评价状态变为评价确认（终态）；评价结果正式提交为项目最终评价结果，评价状态关闭"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e33；③frm先于to→forward；操作者为评价组长；终态"},
    )

    # e34 评价退回修改
    m.add_trans(
        tid="t31", entity="E-PJX", dimension="评价状态",
        frm="评价完成", to="评价退回修改", action="评价退回修改", role="评价人员",
        preconditions=[
            precond(text="评价项处于评价完成状态", ptype="state_ref",
                    ref=state_ref("E-PJX", "评价状态", "评价完成")),
        ],
        expected_results=["评价状态变为评价退回修改；当前评价结果保存为历史结果；开启下一轮评价"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e34；①'退回'→backward；操作者为评价组长；评价退回修改非终态，开启下一轮评价回 评价中"},
    )

    # 评价退回修改 → 评价中（下一轮评价）
    m.add_trans(
        tid="t32", entity="E-PJX", dimension="评价状态",
        frm="评价退回修改", to="评价完成", action="协同评价", role="评价人员",
        preconditions=[
            precond(text="评价项处于评价退回修改状态", ptype="state_ref",
                    ref=state_ref("E-PJX", "评价状态", "评价退回修改")),
        ],
        expected_results=["评价状态回到评价完成（开启下一轮）"],
        traits=["collaborative"], direction="forward", priority="P1",
        source_ref="20.7.1.3评价确认",
        note={"inferred": True, "comment": "推导：'开启下一轮评价'即回到评价中再至评价完成；按业务语义直接落到评价完成；frm后于to判backward，但语义为'重新评价'→语义优先 forward"},
    )

    # === E-SHRW 审核任务状态维度 ===
    # e35 审核通过
    m.add_trans(
        tid="t33", entity="E-SHRW", dimension="审核任务状态",
        frm="待审核", to="审核通过", action="审核通过", role="技术主管",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SHRW", "审核任务状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态变为审核通过（终态）"],
        traits=["branch", "audit"], direction="forward", priority="P0",
        source_ref="20.9.1流程审批",
        note={"branch_dimension": "审核结果", "comment": "源自 e35；③frm先于to→forward；Step 2 value=通过 指向本条；角色按任务类型可变化（技术主管/授权签字人/实验室负责人）"},
    )

    # e36 审核退回
    m.add_trans(
        tid="t33b", entity="E-SHRW", dimension="审核任务状态",
        frm="待审核", to="审核退回", action="审核退回", role="技术主管",
        preconditions=[
            precond(text="审核任务处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SHRW", "审核任务状态", "待审核")),
            precond(text="审核结果=退回", ptype="constraint", note={"comment": "分支值条件"}),
        ],
        expected_results=["审核任务状态变为审核退回（终态）"],
        traits=["branch", "audit", "rollback"], direction="backward", priority="P1",
        source_ref="20.9.1流程审批",
        note={"branch_dimension": "审核结果", "comment": "源自 e36；①'退回'→backward；Step 2 value=退回 指向本条"},
    )

    # === E-XM 文件整理（已结束态触发） ===
    # e40 文件整理
    m.add_trans(
        tid="t35", entity="E-XM", dimension="项目状态",   # 修改为有效维度
        frm="已结束", to="已结束", action="文件整理", role="system",
        preconditions=[
        precond(text="项目处于已结束状态", ptype="state_ref",
                ref=state_ref("E-XM", "项目状态", "已结束")),
        ],
        expected_results=["归档任务开启；提示'归档任务已开启，请稍后查看'；完成后显示'查看归档'按钮"],
        traits=[], direction="forward", priority="P2",
        source_ref="20.5.1.1文件整理",
        note={"comment": "源自 e40；⑤仅自环→forward+inferred；项目状态不变，触发归档任务"},
    )

    # === E-JF 缴费记录（退款操作） ===
    # e37 缴费退款


    # e42 证书批准（实验室负责人；§19.1 报告、结果通知单授权签字人/证书实验室负责人批准）
    # 拆分自原 e17：授权签字人批准报告/结果通知单（t18），实验室负责人批准证书（t18b）
    m.add_trans(
        tid="t18b", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书审核中", action="证书批准", role="实验室负责人",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="技术主管审核报告通过", ptype="event_ref"),
        ],
        expected_results=["实验室负责人批准证书；状态维持报告/证书审核中，附件新增'能力验证合格证书'"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e42；⑤仅自环→forward+inferred；与 t18 同根后缀 b；§6实验室负责人'签发能力验证合格证书'即此批准动作；批准后流转至项目管理员发放"},
    )

    # ============================================================
    # Step 3.3 — 自检（写入前簿记回填）
    # ------------------------------------------------------------
    # 前向引用回填：Step 2 target_transition 语义描述与转换匹配回填
    #   "能力验证计划发布转换" → t03
    #   "测量审核受理转换" → t01b
    #   "协同评价转换" → t29
    #   "审核通过转换" → t33
    #   "审核退回转换" → t33b
    # crud 回填：op 对应转换标签
    #   "文件整理" → t35
    #   "上传付款单" → t11 (多次付款关联 e08)
    #   "审核" → t22/t22b (实验室审核) / t33/t33b (审核任务)
    #   "证书到期提醒" → t34
    #   "退款" → t36
    #   "停用/启用" → t24/t25 (实验室) / t27/t28 (标准库)
    #   "协同评价" → t29
    #   "结果确认" → t30
    #   "退回修改" → t31 (评价)
    # 回写：本节无新动词/新角色补入（动词已在 set_prohibition_config 中收齐）
    # ============================================================

    # ============================================================
    # Step 3.4 — 因果 add_causal
    # ------------------------------------------------------------
    # 约束 ≠ 因果；门禁/前置不是因果；过 Q1→Q2→Q3
    # ============================================================

    # 因果 1：项目立项 → 触发报名记录创建（项目状态=报名中作为门禁）
    # Q1: 项目进入报名中后参加者报名需参加者主动操作 → 不是直接因果
    # Q2: 报名 precondition 已表达 state_ref(项目状态=报名中) → 不写因果，标记约束 [待写入: Step4 XC]
    # 实际：项目进入'报名中'是参加者报名的前置，非因果

    # 因果 2：报名审核通过 → 触发预通知状态=已发送（联动）
    # Q1: 报名审核通过直接联动预通知状态变化（无需额外操作）→ 是因果（联动型）
    # 但 §19.1 表显示'报名审核'动作后预通知状态=已发送，是同一动作后果，非因果
    # → 不写因果

    # 因果 3：评价完成 → 触发报名记录状态可进入报告/证书审核中
    # Q1: 评价完成后仍需策划人员编制结果报告 → 需额外操作 → 约束，不写因果
    # → 标记 [待写入: Step4 XC]

    # 因果 4：报告批准 → 可发放
    # Q1: 报告批准后仍需项目管理员操作发放 → 需额外操作 → 约束
    # → 标记 [待写入: Step4 XC]

    # 因果 5：测量审核受理 → 报名记录状态=报名待审核
    # §19.2: 测量审核受理后报名记录状态=报名待审核，是同一动作后果，非因果
    # → 不写因果

    # 显式句式因果（§19.1）："项目进入报名中后自动开启报名"——报名记录创建
    # 但是报名由参加者发起，非自动；只有当§19.1说"自动开启"时才是联动
    # 实际§19.1仅说"能力验证计划发布→项目状态=报名中"，参加者报名是后续独立动作
    # → 不写因果

    # 显式句式因果（§20.5.2.3）：证书距到期=30天 → 系统邮件提醒
    # Q1: 系统每日9点扫描后自动发邮件，无需额外操作 → 是因果
    m.add_causal(
        frm="t34", to="t34",
        desc="证书距到期时间=30天则系统自动邮件提醒用户并抄送项目管理员",
        trigger="证书距到期时间=30天则通知邮件方式对用户进行提醒，并抄送项目管理员",
        trigger_source="desc",
        evidence_transitions=["t34"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "显式句式（§20.5.2.3）；frm/to 同为本系统触发的 t34 自身；Q1 通过：无须中间操作"},
    )

    # 显式句式因果（§20.9.1.3）：审核任务创建 → 系统短信通知相关负责人
    # §20.9.1.3: "用户通过表单或审核一个已存在的任务，生成一个新的审核任务，系统发送短信通知相关负责人"
    m.add_causal(
        frm="t33", to="t33",
        desc="生成一个新的审核任务后，系统发送短信通知相关负责人",
        trigger="用户通过表单或审核一个已存在的任务，生成一个新的审核任务，系统发送短信通知相关负责人",
        trigger_source="desc",
        evidence_transitions=["t33", "t33b"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "显式句式（§20.9.1.3）；frm/to 同为审核任务节点本身；短信内容'您有一个新的xxx审核任务，请及时处理'"},
    )

    # 显式句式因果（§19.1）：样品发放 → 参加者接收 → 后续测试
    # §19.1动作表'样品发放'后果：样品状态=已发样，预通知状态=已确认
    # 这是同一动作的后果，非因果
    # → 不写因果

    # 显式句式因果（§20.5.3.2 / §20.6.3.2）：管理用户对报名信息操作 → 短信通知用户
    # 报名审核/发样/测试结果审核/结果通知单发布 → 短信通知
    m.add_causal(
        frm="t10", to="t10",
        desc="管理用户对报名信息操作后使用短信方式对用户进行通知",
        trigger="管理人员对用户报名项目操作后使用短信方式对用户进行通知",
        trigger_source="desc",
        evidence_transitions=["t10", "t10b", "t08", "t15", "t19"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "显式句式（§20.5.3.2/§20.6.3.2）；frm/to 同为报名审核相关节点；通知节点：报名审核通过/退回、发样、测试结果审核通过/退回、结果通知单发布"},
    )

    # 显式句式因果（§20.7.1.3）：评价组长确认 → 评价状态关闭
    # 评价组长点击确认后当前结果正式提交为最终评价结果，评价状态关闭
    # Q1: 评价组长点击确认 → 评价状态直接关闭（同动作后果） → 非因果
    # → 不写因果

    # bidirectional coupling (§19.1)：项目状态变更 ↔ 报名记录状态变更
    # 项目进入'报名中'是参加者报名的前置（state_ref 已表达），不写因果
    # 项目进入'已结束'前需要所有报名记录流转到'报告/证书已发布'——这是约束
    # → 标记 [待写入: Step4 XC]

    # ============================================================
    # Step 4 — 约束
    # ------------------------------------------------------------
    # 动笔前回访：①检索 [待写入 逐条兑现；②核对 prohibit_keywords
    # ============================================================

    # === add_invalid ===
    # 仅文档明确禁止的状态转换；终态不可回退属状态机常识，不作生成依据
    # 文档未发现明确"不允许从X到Y"的转换禁止句式
    # → 无 invalid 生成

    # === add_xc 跨实体约束 ===
    # xc_source ∈ {镜像, 联动, 4.5判, 分支差异}
    # source_transition 填生产者转换（source_entity 上到达 source_state 的转换）

    # XC 1：能力验证计划发布（项目→报名中）联动报名记录可被创建
    # §19.1: 项目状态=报名中是报名的前置
    # 已由 t09.preconditions[0] state_ref 表达 → 镜像 XC
    m.add_xc(
        xid="x01",
        source_entity="E-XM", source_transition="t03", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名待审核",
        target_transition="t09",
        xc_source="镜像",
        desc="项目进入报名中后参加者方可发起报名，新报名记录初始化为报名待审核",
        source_ref="19.1实施阶段",
    )

    # XC 2：报名审核通过联动预通知状态=已发送（同一动作对多维度影响）
    # §19.1: '报名审核'动作后果：预通知状态=已发送
    # 这是同一动作对多维度的影响，非典型联动；按联动 XC 写
    m.add_xc(
        xid="x02",
        source_entity="E-BMJL", source_transition="t10", source_state="报名成功",
        target_entity="E-BMJL", target_dimension="预通知状态",
        target_condition="已发送",
        target_transition="t10",
        xc_source="联动",
        desc="报名审核通过后预通知状态自动联动为已发送",
        source_ref="19.1实施阶段",
    )

    # XC 3：样品发放联动预通知状态=已确认
    # §19.1: '样品发放'后果：预通知状态=已确认
    # 但预通知状态在 E-BMJL 维度，样品状态在 E-XM 维度，跨实体
    m.add_xc(
        xid="x03",
        source_entity="E-XM", source_transition="t08", source_state="已发样",
        target_entity="E-BMJL", target_dimension="预通知状态",
        target_condition="已确认",
        target_transition="t13",
        xc_source="联动",
        desc="项目样品发放后联动报名记录预通知状态变为已确认",
        source_ref="19.1实施阶段",
    )

    # XC 4：测量审核受理联动报名记录创建
    # §19.2: 测量审核受理动作后果：报名记录状态=报名待审核
    # 项目与报名记录跨实体联动
    m.add_xc(
        xid="x04",
        source_entity="E-XM", source_transition="t01b", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名待审核",
        target_transition="t09",
        xc_source="联动",
        desc="测量审核受理后联动创建报名记录并初始化为报名待审核",
        source_ref="19.2测量审核提供者流程",
    )

    # XC 5：评价完成后方可编制结果报告（4.5判 - 约束）
    # §19.1: 编制结果报告前置：评价完成
    # 已由 t16.preconditions[1] event_ref 表达 → 4.5判 XC
    m.add_xc(
        xid="x05",
        source_entity="E-PJX", source_transition="t29", source_state="评价完成",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报告/证书审核中",
        target_transition="t16",
        xc_source="4.5判",
        desc="评价完成后方可编制结果报告，将报名记录状态推进至报告/证书审核中",
        source_ref="19.1报告编制和结果通知",
    )

    # XC 6：报告已批准后方可发放结果报告和证书（4.5判 - 约束）
    # §19.1: 发放结果报告和证书前置：报告已批准
    # 已由 t19.preconditions[1] event_ref 表达 → 4.5判 XC
    m.add_xc(
        xid="x06",
        source_entity="E-BMJL", source_transition="t18", source_state="报告/证书审核中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报告/证书已发布",
        target_transition="t19",
        xc_source="4.5判",
        desc="报告批准后方可发放结果报告和证书，将报名记录状态推进至报告/证书已发布",
        source_ref="19.1报告编制和结果通知",
    )

    # XC 7：项目结束前所有报名记录流转到报告/证书已发布（4.5判 - 约束）
    # §19.3: 项目状态=已结束 是终态
    # 推导：项目结束前需所有报名记录流转到报告/证书已发布
    # t06.preconditions[1] event_ref 已表达 → 4.5判 XC
    m.add_xc(
        xid="x07",
        source_entity="E-BMJL", source_transition="t19", source_state="报告/证书已发布",
        target_entity="E-XM", target_dimension="项目状态",
        target_condition="已结束",
        target_transition="t06",
        xc_source="4.5判",
        desc="所有报名记录流转到报告/证书已发布后项目方可进入已结束",
        source_ref="19.3项目状态分析",
    )

    # XC 8：分支差异 - 业务类型=测量审核 项目无独立立项（分支差异）
    # §19.2: 测量审核项目状态直接从报名中开始，不经过待开始
    m.add_xc(
        xid="x08",
        source_entity="E-XM", source_transition="t01b", source_state="报名中",
        target_entity="E-XM", target_dimension="项目状态",
        target_condition="报名中",
        target_transition="t01b",
        xc_source="分支差异",
        desc="业务类型=测量审核时项目状态直接从报名中开始，不经过待开始状态",
        source_ref="19.2测量审核提供者流程",
    )

    # === add_br 业务规则 ===
    # 两步判定：① signal_type（口吻）② category（管什么）
    # 时间/次数/通知/计算属于②，永不进①

    # BR 1：实验室新增/修改后需审核通过方可用于项目报名（restrictive + authorization）
    m.add_br(
        bid="b01",
        category="authorization",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-SYS"],
        source_ref="20.3.1实验室信息",
        signal_type="restrictive",
        note={"role": "系统管理人员", "comment": "signal_type命中'需'；category判访问控制：审核门禁"},
    )

    # BR 2：审核退回必须填写审核意见（restrictive + validation）
    m.add_br(
        bid="b02",
        category="validation",
        desc="实验室审核结果为退回修改时必须填写审核意见",
        entities_involved=["E-SYS"],
        source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'必须'；category判有效性校验"},
    )

    # BR 3：审核通过生成数据快照（restrictive + computation）
    m.add_br(
        bid="b03",
        category="computation",
        desc="审核结果为通过时为当前数据生成该数据的快照记录",
        entities_involved=["E-SYS"],
        source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'为...生成'；category判计算衍生：快照生成"},
    )

    # BR 4：含子项的测试项不允许删除（restrictive + validation）
    m.add_br(
        bid="b04",
        category="validation",
        desc="含有子项的测试项记录不允许删除",
        entities_involved=["E-CSX"],
        source_ref="20.4.2.10删除测试项",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不允许'；category判有效性校验"},
    )

    # BR 5：停用的标准库不可在项目创建等环节选择（restrictive + validation）
    m.add_br(
        bid="b05",
        category="validation",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK"],
        source_ref="20.4.2.5停用/启用标准库",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不可'；category判有效性校验"},
    )

    # BR 6：消息发送接收人1和接收人2不能同时为空（restrictive + validation）
    m.add_br(
        bid="b06",
        category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-XXJL"],
        source_ref="20.5.1.4优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'；category判有效性校验"},
    )

    # BR 7：项目未结束方可进行消息发送（restrictive + validation）
    m.add_br(
        bid="b07",
        category="validation",
        desc="未结束的项目可以进行消息发送",
        entities_involved=["E-XM"],
        source_ref="20.5.1.4优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'可以'但隐含'未结束'前置；category判有效性校验"},
    )

    # BR 8：未结束项目方可上传付款单（多次付款）（restrictive + validation）
    m.add_br(
        bid="b08",
        category="validation",
        desc="已报名项目支持多次付款操作且不对付款金额进行校验限制",
        entities_involved=["E-JF"],
        source_ref="20.5.2.1已报名项目增加多次付款功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不对...校验限制'；category判有效性校验：金额不校验"},
    )

    # BR 9：证书距到期=30天系统每日9点邮件提醒（restrictive + timing）
    m.add_br(
        bid="b09",
        category="timing",
        desc="系统在每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则通知邮件方式对用户进行提醒，并抄送项目管理员",
        entities_involved=["E-ZS"],
        source_ref="20.5.2.3增加证书到期前30天提醒功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'每天上午9点'量化措辞；category判时间约束；每日触发"},
    )

    # BR 10：未结束项目方可进行消息发送（测量审核）（restrictive + validation）
    m.add_br(
        bid="b10",
        category="validation",
        desc="测量审核未结束的项目可以进行消息发送",
        entities_involved=["E-XM"],
        source_ref="20.6.1.2优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'可以'但隐含'未结束'前置；category判有效性校验；与 b07 同类（通用操作）"},
    )

    # BR 11：测量审核消息发送接收人1为必填（restrictive + validation）
    m.add_br(
        bid="b11",
        category="validation",
        desc="测量审核消息发送接收人1为必填",
        entities_involved=["E-XXJL"],
        source_ref="20.6.1.2优化消息发送功能",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'必填'；category判有效性校验；与 b06 不同：MA 路径接收人1必填"},
    )

    # BR 12：评价人员只能修改自己的评价结果（restrictive + authorization）
    m.add_br(
        bid="b12",
        category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJX"],
        source_ref="20.7.1.2协同评价",
        signal_type="restrictive",
        note={"role": "评价人员", "comment": "signal_type命中'只能'+'不能'；category判访问控制；constrained_entity 隐含为评价人员"},
    )

    # BR 13：评价组长首位确定（restrictive + computation）
    m.add_br(
        bid="b13",
        category="computation",
        desc="新建项目时第一个被选择的评价人员默认作为评价组长",
        entities_involved=["E-PJX"],
        source_ref="20.7.1项目列表",
        signal_type="restrictive",
        note={"comment": "signal_type命中'默认'；category判计算衍生：组长自动赋值"},
    )

    # BR 14：评价确认将当前结果正式提交为项目的最终评价结果（restrictive + computation）
    m.add_br(
        bid="b14",
        category="computation",
        desc="点击确认将当前结果正式提交为项目的最终评价结果，项目评价状态关闭",
        entities_involved=["E-PJX"],
        source_ref="20.7.1.3评价确认",
        signal_type="restrictive",
        note={"comment": "signal_type命中'正式提交'；category判计算衍生：最终结果固化"},
    )

    # BR 15：评价退回修改开启下一轮评价（restrictive + computation）
    m.add_br(
        bid="b15",
        category="computation",
        desc="点击退回修改将当前评价结果保存为历史结果并开启下一轮评价",
        entities_involved=["E-PJX"],
        source_ref="20.7.1.3评价确认",
        signal_type="restrictive",
        note={"comment": "signal_type命中'保存为历史'；category判计算衍生：历史结果保存+新一轮开启"},
    )

    # BR 16：调整统计规则低值≤x<高值（field_constraint + validation）
    m.add_br(
        bid="b16",
        category="validation",
        desc="每个统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值",
        entities_involved=["E-PJX"],
        source_ref="20.7.1.3评价确认",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'大于等于...小于...'取值范围；category判有效性校验：区间规则"},
    )

    # BR 17：测量审核结果通知单审核流程合并为单流程，处理人顺序按签字人选择顺序（restrictive + computation）
    m.add_br(
        bid="b17",
        category="computation",
        desc="测量审核结果通知单审核流程合并为一个流程，流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-SHRW"],
        source_ref="20.9.1.1测量审核结果通知单审核流程优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'合并为'+'为...顺序'；category判计算衍生：审批顺序固化"},
    )

    # BR 18：自定义流程≤4个（restrictive + validation）
    m.add_br(
        bid="b18",
        category="validation",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程",
        entities_involved=["E-SHRW"],
        source_ref="20.9.1.6增加自定义流程",
        signal_type="restrictive",
        note={"comment": "signal_type命中'4个以内'量化措辞；category判有效性校验：流程数量上限"},
    )

    # BR 19：批量审核任务系统根据节点类型及内容判断是否可批量处理（restrictive + validation）
    m.add_br(
        bid="b19",
        category="validation",
        desc="系统会根据任务节点的类型及内容判断当前节点是否可以被批量处理",
        entities_involved=["E-SHRW"],
        source_ref="20.9.1.4任务批量处理",
        signal_type="restrictive",
        note={"comment": "signal_type命中'判断'；category判有效性校验：批量处理前置判断"},
    )

    # BR 20：批量审核需选择记录，无选择提示（restrictive + usability）
    m.add_br(
        bid="b20",
        category="usability",
        desc="提交审核时如没有选择记录将提示用户选择记录信息",
        entities_involved=["E-SHRW"],
        source_ref="20.5.1.3项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'将提示'；category判易用功能：操作提示"},
    )

    # BR 21：退款金额不大于当前缴费金额（field_constraint + validation）
    m.add_br(
        bid="b21",
        category="validation",
        desc="退款金额不能为大于当前缴费金额",
        entities_involved=["E-JF"],
        source_ref="20.10.2.3缴费单退款",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'不能为大于'取值范围；category判有效性校验：退款金额上限"},
    )

    # BR 22：退款后项目费用更新为实际付款金额（restrictive + computation）
    m.add_br(
        bid="b22",
        category="computation",
        desc="退款后更新项目费用为实际付款金额（付款金额-退款金额）",
        entities_involved=["E-JF", "E-XM"],
        source_ref="20.10.2.3缴费单退款",
        signal_type="restrictive",
        note={"comment": "signal_type命中'更新...为'；category判计算衍生：项目费用回算；多实体 BR，constrained_entity 默认为 E-JF"},
    )

    # BR 23：发票支持多次分批上传（usability + validation）
    m.add_br(
        bid="b23",
        category="usability",
        desc="发票上传支持多次分批上传，发票上传后会显示在发票列表中",
        entities_involved=["E-FP"],
        source_ref="20.10.2.2修改发票上传功能",
        signal_type="usability",
        note={"comment": "signal_type命中'支持'；category判易用功能：分批上传"},
    )

    # BR 24：移除发票文件表单提交后生效（restrictive + validation）
    m.add_br(
        bid="b24",
        category="validation",
        desc="点击文件地址后的x可以移除文件，表单提交后生效",
        entities_involved=["E-FP"],
        source_ref="20.10.2.2修改发票上传功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'表单提交后生效'；category判有效性校验：移除延迟生效"},
    )

    # BR 25：信息发送记录仅系统管理人员和项目管理员可查看（restrictive + authorization）
    m.add_br(
        bid="b25",
        category="authorization",
        desc="信息发送记录只有系统管理人员和项目管理员可以查看",
        entities_involved=["E-XXJL"],
        source_ref="20.4.4.1信息发送记录",
        signal_type="restrictive",
        note={"role": ["系统管理人员", "项目管理员"], "comment": "signal_type命中'只有'；category判访问控制"},
    )

    # BR 26：删除操作需二次确认（restrictive + usability）
    m.add_br(
        bid="b26",
        category="usability",
        desc="删除操作时系统提示警示框，用户点击确认后才执行删除操作",
        entities_involved=["E-XM", "E-SYS", "E-BZK", "E-CSX"],
        source_ref="3.6可用性要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'点击确认后才'；category判易用功能：删除二次确认；多实体通用规则"},
    )

    # BR 27：通知公告15天内显示new标识（restrictive + display）
    m.add_br(
        bid="b27",
        category="display",
        desc="15天内发布的通知在内容前标注new标识，超过15天后此标识自动隐藏",
        entities_involved=["E-XXJL"],
        source_ref="20.2.1通知公告",
        signal_type="restrictive",
        note={"comment": "signal_type命中'15天内'量化措辞；category判信息展示：标识显示"},
    )

    # BR 28：操作完成时统一规范提示信息（usability + display）
    m.add_br(
        bid="b28",
        category="display",
        desc="操作完成时有统一规范的提示信息",
        entities_involved=["E-XM", "E-SYS", "E-BZK"],
        source_ref="3.6可用性要求",
        signal_type="usability",
        note={"comment": "signal_type命中'应'；category判信息展示：统一提示"},
    )

    # BR 29：关键操作留痕机制（restrictive + computation）
    m.add_br(
        bid="b29",
        category="computation",
        desc="对关键操作实施留痕机制，系统将自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-XXJL"],
        source_ref="20.11.1.2安全性相关内容优化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'自动记录'；category判计算衍生：审计日志生成"},
    )

    # BR 30：每年9点扫描证书（已与 b09 同义，跳过合并去重）
    # BR 31：历史数据迁移至系统（restrictive + computation）
    m.add_br(
        bid="b30",
        category="computation",
        desc="应将历史用户及项目数据迁移至系统，并确保历史数据在系统正常使用",
        entities_involved=["E-XM", "E-SYS"],
        source_ref="3.7集成部署要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'应'；category判计算衍生：历史数据迁移"},
    )

    # BR 32：项目批量操作选择列只有已上传对应文件且未提交审核的记录才可被选定（restrictive + validation）
    m.add_br(
        bid="b31",
        category="validation",
        desc="只有已上传对应文件且未提交审核的记录才可以被选定进行批量提交审核",
        entities_involved=["E-BMJL"],
        source_ref="20.5.1.3项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只有...才可以'；category判有效性校验：选定前置"},
    )

    # BR 33：上传按钮根据处理内容和是否已上传两个条件判定是否显示（restrictive + display）
    m.add_br(
        bid="b32",
        category="display",
        desc="上传结果通知单/上传证书按钮会根据处理内容和是否已上传两个条件判定是否需要显示",
        entities_involved=["E-BMJL"],
        source_ref="20.5.1.3项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'判定'；category判信息展示：按钮显隐"},
    )

    # BR 34：项目新增表单技术主管/实验室负责人/授权签字人唯一时默认填充（restrictive + usability）
    m.add_br(
        bid="b33",
        category="usability",
        desc="技术主管、实验室负责人、授权签字人如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"],
        source_ref="20.5.1.6默认填充技术主管、实验室负责人、授权签字人",
        signal_type="restrictive",
        note={"comment": "signal_type命中'有且仅有一个时默认填充'；category判易用功能：默认值填充"},
    )

    # BR 35：分支承载 - 业务类型为能力验证时按 PT 流程（restrictive + validation）
    m.add_br(
        bid="b34",
        category="validation",
        desc="业务类型=能力验证时项目按PT流程：项目立项→设计方案编制→能力验证计划发布",
        entities_involved=["E-XM"],
        source_ref="19.1能力验证提供者流程",
        signal_type="restrictive",
        note={"branch_dimension": "业务类型", "comment": "分支承载：业务类型=能力验证；desc含'业务类型=能力验证'字面量"},
    )

    # BR 36：分支承载 - 业务类型为测量审核时按 MA 流程（restrictive + validation）
    m.add_br(
        bid="b35",
        category="validation",
        desc="业务类型=测量审核时项目按MA流程：直接受理用户测量审核报名进入报名中",
        entities_involved=["E-XM"],
        source_ref="19.2测量审核提供者流程",
        signal_type="restrictive",
        note={"branch_dimension": "业务类型", "comment": "分支承载：业务类型=测量审核；desc含'业务类型=测量审核'字面量"},
    )

    # BR 37：分支承载 - 评分方式为分值时按分值累加（restrictive + computation）
    m.add_br(
        bid="b36",
        category="computation",
        desc="评分方式=分值时评价按分值累加计算",
        entities_involved=["E-PJX"],
        source_ref="20.7.1项目列表",
        signal_type="restrictive",
        note={"branch_dimension": "评分方式", "comment": "分支承载：评分方式=分值；desc含'评分方式=分值'字面量"},
    )

    # BR 38：分支承载 - 评分方式为权重时按权重加权（restrictive + computation）
    m.add_br(
        bid="b37",
        category="computation",
        desc="评分方式=权重时评价按权重加权计算",
        entities_involved=["E-PJX"],
        source_ref="20.7.1项目列表",
        signal_type="restrictive",
        note={"branch_dimension": "评分方式", "comment": "分支承载：评分方式=权重；desc含'评分方式=权重'字面量"},
    )

    # BR 39：分支承载 - 审核结果为通过时状态推进（restrictive + validation）
    m.add_br(
        bid="b38",
        category="validation",
        desc="审核结果=通过时状态推进至通过分支（启用/报名成功/审核通过/报告/证书审核中流转下一节点）",
        entities_involved=["E-SHRW", "E-SYS", "E-BMJL"],
        source_ref="20.4.1.2实验室审核；20.9.1.4任务批量处理",
        signal_type="restrictive",
        note={"branch_dimension": "审核结果", "comment": "分支承载：审核结果=通过；desc含'审核结果=通过'字面量"},
    )

    # BR 40：分支承载 - 审核结果为退回时状态回退（restrictive + validation）
    m.add_br(
        bid="b39",
        category="validation",
        desc="审核结果=退回时状态回退至退回分支（已退回/报名退回/审核退回）",
        entities_involved=["E-SHRW", "E-SYS", "E-BMJL"],
        source_ref="20.4.1.2实验室审核；20.9.1.4任务批量处理",
        signal_type="restrictive",
        note={"branch_dimension": "审核结果", "comment": "分支承载：审核结果=退回；desc含'审核结果=退回'字面量"},
    )

    # BR 41：缴费时间筛选支持本月/本季/本年单选+时间选择（field_constraint + usability）
    m.add_br(
        bid="b40",
        category="usability",
        desc="缴费时间筛选提供本月、本季、本年三个单选按钮，点击设置后面时间选择组件时间范围",
        entities_involved=["E-JF"],
        source_ref="20.10.1.1缴费信息查询与管理",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'本月/本季/本年'选项；category判易用功能：时间快速录入"},
    )

    # BR 42：客户统计时间参数支持月度/季度/年度快速录入（field_constraint + usability）
    m.add_br(
        bid="b41",
        category="usability",
        desc="客户统计列表录入时间增加月度、季度、年度三个单选按钮的快速录入",
        entities_involved=["E-SYS"],
        source_ref="20.8.6.1优化客户统计列表查询参数时间参数快速录入",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'月度/季度/年度'选项；category判易用功能：时间快速录入"},
    )

    # BR 43：实验室名称可跳转至报名信息统计（usability + display）
    m.add_br(
        bid="b42",
        category="usability",
        desc="实验室名称增加跳转功能，点击此列可以跳转到报名信息统计页面查看此实验室报表的所有项目信息",
        entities_involved=["E-SYS", "E-BMJL"],
        source_ref="20.8.6.1优化客户统计列表查询参数时间参数快速录入",
        signal_type="usability",
        note={"comment": "signal_type命中'增加'；category判易用功能：跳转导航"},
    )

    # BR 44：移动端兼容性（restrictive + validation）
    m.add_br(
        bid="b43",
        category="validation",
        desc="移动端应兼容安卓系统（骁龙680以上/4G以上/8.0以上）、iOS系统（A11以上/2GB以上/iOS 11以上）、鸿蒙系统（麒麟9000以上/4G以上/HarmonyOS 2.0以上）",
        entities_involved=[],
        source_ref="3.5兼容性要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'应兼容'；category判有效性校验：终端兼容性"},
    )

    # BR 45：平台支持至少300个同时在线用户数（restrictive + validation）
    m.add_br(
        bid="b44",
        category="validation",
        desc="平台应支持至少300个同时在线用户数；并发100时每个页面响应时间不超过5秒；单次报名操作成功率应达到95%以上",
        entities_involved=[],
        source_ref="3.4性能要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'至少/不超过/以上'量化措辞；category判有效性校验：性能指标"},
    )

    # BR 46：等保二级合规（restrictive + validation）
    m.add_br(
        bid="b45",
        category="validation",
        desc="系统设计开发部署应符合等保二级要求",
        entities_involved=[],
        source_ref="3.3安全要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'应符合'；category判有效性校验：合规要求"},
    )

    # BR 47：敏感数据加密存储（restrictive + validation）
    m.add_br(
        bid="b46",
        category="validation",
        desc="对敏感数据进行加密存储，使用强加密标准（如AES）；使用TLS/SSL加密数据传输",
        entities_involved=[],
        source_ref="21.2.2数据安全",
        signal_type="restrictive",
        note={"comment": "signal_type命中'对...加密'；category判有效性校验：数据加密"},
    )

    # BR 48：数据最小化原则（restrictive + validation）
    m.add_br(
        bid="b47",
        category="validation",
        desc="仅收集完成业务所必需的最少个人信息",
        entities_involved=[],
        source_ref="21.2.4数据最小化",
        signal_type="restrictive",
        note={"comment": "signal_type命中'仅'；category判有效性校验：信息收集"},
    )

    # ============================================================
    # 回写 — 动词词表追加（来源 Step 1.4/3.3）
    # ------------------------------------------------------------
    # F9 词根校验：op name 词根须 ∈ action_verbs
    # §0 回写协议：遗漏动词按 add_action_verbs 追加去重
    # ============================================================
    # 来源 Step 1.4：op 名"批量处理/详情/管理测试项/结果确认/保存历史/调整细则/调整统计规则/批量审核/移除文件/选择常用/消息详情/完善/证书批准"词根未在初始 action_verbs 中
    m.add_action_verbs([
        "批量处理", "详情", "管理测试项", "结果确认", "保存历史",
        "调整细则", "调整统计规则", "批量审核", "移除文件",
        "选择常用", "消息详情", "完善", "证书批准",
    ])

    # ============================================================
    # F11 角色覆盖裁决（已登记角色未现于 transitions.role 的情况）
    # ------------------------------------------------------------
    # 已登记角色 14 个；以下角色未现于 transitions.role，附裁决理由：
    #   r01 实验室负责人：已在 t18b（证书批准）承载，§6'签发能力验证合格证书'即此动作
    #   r06 样品制备人员：§5 仅'样品制备/样品管理'，样品状态流转（t07 样品核查）由 r07 样品管理员承载；
    #                    样品制备本身不产生状态变更，仅生成制备记录附件，无转换可承载 → 不入 transitions.role
    #   r09 统计人员：§5 仅'统计分析'，为查询/计算操作，无状态变更，无转换可承载 → 不入 transitions.role
    #   r10 质量专员：§5 仅'报告统计'，为查询操作，无状态变更，无转换可承载 → 不入 transitions.role
    #   r14 监督员：§5 非固定角色，文档未明确具体操作，readonly=True；
    #             §20.5.1.5/§20.6.1.3 仅作为项目新增表单字段被引用，无转换可承载 → 不入 transitions.role
    # 其余角色（r02/r03/r04/r05/r07/r08/r11/r12/r13）均已在 transitions.role 中出现 ≥1 次
    # ============================================================
    return m
