"""网数中心能力验证服务平台升级维护项目 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref

# ===== 事件台账 =====
# 说明：本台账综合 §19.1 能力验证提供者流程、§19.2 测量审核提供者流程、§19.3 状态枚举、§20 功能要求推导。
#       PT/MA 重叠事件合并登记，差异由 note 互引；MA 独有动作单独编号。
# 编号规则：e## 顺序登记；同一动作跨多 (主体,维度) 时按主体维度拆行，note 互引。
# source_ref 引用 §19.x / §20.x 子项号；复合引用以 ； 分隔。
# 推断依据：§19.3 状态枚举列出但 §19.1/19.2 流程表未显式落点 → 标 inferred，依据写入维度级 note。

# ---- 项目维度事件 ----
# e01 | 主体=项目 | 维度=项目状态 | 动作=设计方案编制 | 执行者=策划人员 | 前置=无 | 后果=待开始 | 19.1方案设计阶段；19.2方案设计阶段
# e02 | 主体=项目 | 维度=项目状态 | 动作=能力验证计划发布 | 执行者=项目管理员 | 前置=待开始 | 后果=报名中 | 19.1实施阶段
# e03 | 主体=项目 | 维度=项目状态 | 动作=测量审核受理报名 | 执行者=项目管理员 | 前置=无 | 后果=报名中 | 19.2项目准备阶段
# e04 | 主体=项目 | 维度=项目状态 | 动作=进入实施 | 执行者=项目管理员 | 前置=报名中 | 后果=进行中 | 19.1实施阶段；19.2实施阶段
# e05 | 主体=项目 | 维度=项目状态 | 动作=进入报告审核 | 执行者=策划人员 | 前置=进行中 | 后果=报告审核中 | 19.1报告编制和结果通知；19.2报告编制和结果通知
# e06 | 主体=项目 | 维度=项目状态 | 动作=发放结果报告和证书 | 执行者=项目管理员 | 前置=报告审核中 | 后果=已结束 | 19.1报告编制和结果通知；19.2报告编制和结果通知
# ---- 样品维度事件 ----
# e07 | 主体=样品 | 维度=样品状态 | 动作=样品核查 | 执行者=样品管理员 | 前置=待核查 | 后果=已核查 | 19.1实施阶段；19.2实施阶段
# e08 | 主体=样品 | 维度=样品状态 | 动作=样品发放 | 执行者=项目管理员 | 前置=已核查 | 后果=已发样 | 19.1实施阶段；19.2实施阶段
# e09 | 主体=样品 | 维度=样品状态 | 动作=参加者测试与结果提交 | 执行者=能力验证参加者 | 前置=已发样 | 后果=已还样 | 19.1实施阶段
# e10 | 主体=样品 | 维度=样品状态 | 动作=无需还样 | 执行者=能力验证参加者 | 前置=已发样 | 后果=无需还样 | 19.1实施阶段（分支：测量审核样品不退）
# e11 | 主体=样品 | 维度=样品状态 | 动作=样品重置 | 执行者=样品管理员 | 前置=已核查 | 后果=待核查 | 19.1实施阶段（循环状态机：批次重置）
# e12 | 主体=样品 | 维度=样品状态 | 动作=样品领用登记 | 执行者=样品管理员 | 前置=无 | 后果=待核查 | 19.2实施阶段
# ---- 报名记录-报名记录状态维度事件 ----
# e13 | 主体=报名记录 | 维度=报名记录状态 | 动作=报名 | 执行者=能力验证参加者 | 前置=无 | 后果=报名待审核 | 19.1实施阶段；19.2项目准备阶段
# e14 | 主体=报名记录 | 维度=报名记录状态 | 动作=报名撤销 | 执行者=能力验证参加者 | 前置=报名待审核 | 后果=已撤销 | 19.1实施阶段
# e15 | 主体=报名记录 | 维度=报名记录状态 | 动作=报名审核通过 | 执行者=项目管理员 | 前置=报名待审核 | 后果=报名成功 | 19.1实施阶段；19.2项目准备阶段
# e16 | 主体=报名记录 | 维度=报名记录状态 | 动作=报名审核退回 | 执行者=项目管理员 | 前置=报名待审核 | 后果=报名退回 | 19.1实施阶段；19.2项目准备阶段
# e17 | 主体=报名记录 | 维度=报名记录状态 | 动作=能力验证预通知 | 执行者=项目管理员 | 前置=报名成功 | 后果=结果待提交 | 19.1实施阶段；19.2实施阶段
# e18 | 主体=报名记录 | 维度=报名记录状态 | 动作=参加者测试与结果提交 | 执行者=能力验证参加者 | 前置=结果待提交 | 后果=结果已提交 | 19.1实施阶段；19.2实施阶段
# e19 | 主体=报名记录 | 维度=报名记录状态 | 动作=结果退回修改 | 执行者=项目管理员 | 前置=结果已提交 | 后果=结果退回修改 | 19.1报告编制和结果通知
# e20 | 主体=报名记录 | 维度=报名记录状态 | 动作=编制结果报告 | 执行者=策划人员 | 前置=结果已提交 | 后果=报告/证书审核中 | 19.1报告编制和结果通知；19.2报告编制和结果通知
# e21 | 主体=报名记录 | 维度=报名记录状态 | 动作=发放结果报告和证书 | 执行者=项目管理员 | 前置=报告/证书审核中 | 后果=报告/证书已发布 | 19.1报告编制和结果通知；19.2报告编制和结果通知
# ---- 报名记录-通知状态维度事件（§19.3 枚举"通知状态"，§19.1/19.2 流程表"预通知状态"列同源）----
# e22 | 主体=报名记录 | 维度=通知状态 | 动作=能力验证预通知 | 执行者=项目管理员 | 前置=未发送 | 后果=已发送 | 19.1实施阶段；19.2实施阶段
# e23 | 主体=报名记录 | 维度=通知状态 | 动作=预通知待确认 | 执行者=系统 | 前置=已发送 | 后果=待确认 | 19.1实施阶段；19.2实施阶段
# e24 | 主体=报名记录 | 维度=通知状态 | 动作=样品发放 | 执行者=项目管理员 | 前置=待确认 | 后果=已确认 | 19.1实施阶段；19.2实施阶段
# e25 | 主体=报名记录 | 维度=通知状态 | 动作=作业指导书编制 | 执行者=策划人员 | 前置=未发送 | 后果=待审核 | 19.2实施阶段
# e26 | 主体=报名记录 | 维度=通知状态 | 动作=作业指导书审核退回 | 执行者=技术主管 | 前置=待审核 | 后果=退回 | 19.2实施阶段
# e27 | 主体=报名记录 | 维度=通知状态 | 动作=作业指导书审核通过 | 执行者=技术主管 | 前置=待审核 | 后果=已审核 | 19.2实施阶段
# e28 | 主体=报名记录 | 维度=通知状态 | 动作=结果通知单批准 | 执行者=授权签字人 | 前置=已审核 | 后果=已批准 | 19.3通知状态枚举
# ---- 报名记录-费用状态维度事件 ----
# e29 | 主体=报名记录 | 维度=费用状态 | 动作=报名 | 执行者=能力验证参加者 | 前置=无 | 后果=待缴费 | 19.1实施阶段；19.2项目准备阶段
# e30 | 主体=报名记录 | 维度=费用状态 | 动作=缴费 | 执行者=能力验证参加者 | 前置=待缴费 | 后果=已缴费 | 19.1实施阶段；19.2项目准备阶段
# e31 | 主体=报名记录 | 维度=费用状态 | 动作=缴费退款 | 执行者=财务人员 | 前置=已缴费 | 后果=待缴费 | 20.10.2.3缴费单退款
# ---- 报名记录-发票状态维度事件 ----
# e32 | 主体=报名记录 | 维度=发票状态 | 动作=报名 | 执行者=能力验证参加者 | 前置=无 | 后果=待开票 | 19.1实施阶段；19.2项目准备阶段
# e33 | 主体=报名记录 | 维度=发票状态 | 动作=发票开具 | 执行者=财务人员 | 前置=待开票 | 后果=已开票 | 19.1实施阶段；19.2项目准备阶段
# ---- 报名记录-缴费通知状态维度事件（inferred：§19.3 未列，由 §19.1/19.2 流程表"缴费通知单"列推导）----
# e34 | 主体=报名记录 | 维度=缴费通知状态 | 动作=报名 | 执行者=能力验证参加者 | 前置=无 | 后果=未发送 | 19.1实施阶段
# e35 | 主体=报名记录 | 维度=缴费通知状态 | 动作=报名审核通过 | 执行者=项目管理员 | 前置=未发送 | 后果=已发送 | 19.1实施阶段；19.2项目准备阶段
# ---- 报名记录-报名记录样品状态维度事件 ----
# e36 | 主体=报名记录 | 维度=报名记录样品状态 | 动作=样品发放 | 执行者=项目管理员 | 前置=待发样 | 后果=待收样 | 19.3报名记录样品状态枚举
# e37 | 主体=报名记录 | 维度=报名记录样品状态 | 动作=样品签收 | 执行者=能力验证参加者 | 前置=待收样 | 后果=已收样 | 19.3报名记录样品状态枚举
# e38 | 主体=报名记录 | 维度=报名记录样品状态 | 动作=样品确认 | 执行者=能力验证参加者 | 前置=已收样 | 后果=已确认 | 19.3报名记录样品状态枚举
# ---- 实验室信息状态事件 ----
# e39 | 主体=实验室信息 | 维度=实验室状态 | 动作=实验室新增/修改 | 执行者=能力验证参加者 | 前置=无 | 后果=待审核 | 20.3.1实验室信息；20.4.1.2实验室审核
# e40 | 主体=实验室信息 | 维度=实验室状态 | 动作=实验室审核通过 | 执行者=系统管理员 | 前置=待审核 | 后果=启用 | 20.4.1.2实验室审核
# e41 | 主体=实验室信息 | 维度=实验室状态 | 动作=实验室审核退回 | 执行者=系统管理员 | 前置=待审核 | 后果=退回修改 | 20.4.1.2实验室审核
# e42 | 主体=实验室信息 | 维度=实验室状态 | 动作=实验室停用 | 执行者=系统管理员 | 前置=启用 | 后果=停用 | 20.4.1.1实验室列表与查询
# e43 | 主体=实验室信息 | 维度=实验室状态 | 动作=实验室启用 | 执行者=系统管理员 | 前置=停用 | 后果=启用 | 20.4.1.1实验室列表与查询
# e44 | 主体=实验室信息 | 维度=实验室状态 | 动作=实验室修改 | 执行者=能力验证参加者 | 前置=启用 | 后果=待审核 | 20.4.1.3实验室修改
# ---- 标准库状态事件 ----
# e45 | 主体=标准库 | 维度=标准库状态 | 动作=新增标准库 | 执行者=系统管理员 | 前置=无 | 后果=启用 | 20.4.2.2新增标准库
# e46 | 主体=标准库 | 维度=标准库状态 | 动作=停用标准库 | 执行者=系统管理员 | 前置=启用 | 后果=停用 | 20.4.2.5停用/启用标准库
# e47 | 主体=标准库 | 维度=标准库状态 | 动作=启用标准库 | 执行者=系统管理员 | 前置=停用 | 后果=启用 | 20.4.2.5停用/启用标准库
# ---- 评价状态事件（§20.7 推导）----
# e48 | 主体=评价 | 维度=评价状态 | 动作=评价组长完善 | 执行者=评价组长 | 前置=无 | 后果=待评价 | 20.7.1.1测试项目、评价细则完善
# e49 | 主体=评价 | 维度=评价状态 | 动作=评价人员评价 | 执行者=评价人员 | 前置=待评价；报名记录.结果已提交 | 后果=评价中 | 20.7.1.2协同评价
# e50 | 主体=评价 | 维度=评价状态 | 动作=评价结果确认 | 执行者=评价组长 | 前置=评价中 | 后果=评价完成 | 20.7.1.3评价确认
# e51 | 主体=评价 | 维度=评价状态 | 动作=评价退回修改 | 执行者=评价组长 | 前置=评价中 | 后果=待评价 | 20.7.1.3评价确认


def build() -> DomainModel:
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计",
        document_scope="能力验证/测量审核项目全流程；实验室/标准库/评价/财务/统计子系统",
    )

    # ===== Step 1.0 动词词表 → set_prohibition_config =====
    m.set_prohibition_config(config={
        "action_verbs": [
            "编制", "发布", "报名", "审核通过", "审核退回", "审核", "缴费", "开具",
            "发放", "发送", "核查", "提交", "评价", "统计", "批准", "回收", "整理",
            "导入", "处理", "修改", "删除", "新增", "启用", "停用", "退回", "确认",
            "测试", "选入", "重置", "退款", "上传", "下载", "导出", "查询", "登录",
            "退出", "完善", "撤销", "签收", "领用", "归还", "审批", "受理",
            "进入实施", "无需还样", "预通知",
        ],
        "prohibit_keywords": [
            "不允许删除含有子项的测试项",
            "接收人1和接收人2不能同时为空",
            "退款金额不能大于当前缴费金额",
            "未结束的项目可以进行消息发送",
            "停用的标准库在项目创建等环节不可被选择",
            "机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
            "评价人员只能对自己的评价结果进行修改",
            "审核结果为通过时可以为空",
            "审核结果为退回修改必须填写审核意见",
            "含有子项的记录不允许删除",
            "只有已上传对应文件且未提交审核的记录才可以被选定",
            "退款金额使用红色字体且大于0时显示",
        ],
    })

    # ===== Step 1.1 角色 =====
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
    m.add_role(id="r11", name="财务人员")
    m.add_role(id="r12", name="系统管理员")
    m.add_role(id="r13", name="能力验证参加者")
    m.add_role(id="r14", name="监督员", readonly=True)
    m.add_role(id="r15", name="评价组长")
    # system 保留角色不入 roles

    # 操作权限（add_permission：operations 填具体操作名，仅收不改状态的 crud/query/session/ui/file/config 操作）
    m.add_permission(role="系统管理员", operations=[
        "查询实验室", "审核实验室", "停用实验室", "启用实验室", "修改实验室",
        "查询标准库", "新增标准库", "修改标准库", "删除标准库", "停用标准库", "启用标准库", "管理测试项",
        "查询信息发送记录", "查看消息详情",
        "查询用户", "新增用户", "修改用户", "删除用户", "配置角色",
        "查询机构", "新增机构", "修改机构", "删除机构",
        "查询通知管理", "发布通知", "查询内容管理", "维护内容管理",
        "查询统计模板", "定制统计模板", "查询报告模板", "定制报告模板", "查询证书模板", "定制证书模板",
        "查询意见反馈", "回复意见反馈",
    ])
    m.add_permission(role="项目管理员", operations=[
        "查询项目", "新增项目", "修改项目", "查询报名信息", "查询信息发送记录",
        "上传文件", "打包下载", "代码导入", "上传结果通知单", "上传证书", "提交审核",
        "消息发送", "测试发送", "上传付款单", "上传发票", "导出项目通知书", "修改财务备注",
        "查询待办", "处理待办",
    ])
    m.add_permission(role="能力验证参加者", operations=[
        "登录系统", "退出系统", "查询项目", "报名项目", "上传付款单", "上传测试结果",
        "下载预通知", "下载结果通知单", "下载证书", "上传缴费证明", "查询通知公告", "意见反馈提交",
        "查询已报名项目", "查询用户报名列表", "新增实验室信息", "修改实验室信息",
    ])
    m.add_permission(role="评价人员", operations=["查询评价", "评价录入", "导出评价结果"])
    m.add_permission(role="评价组长", operations=[
        "查询评价", "完善测试项目", "完善评价细则", "另存常用项", "删除常用项",
        "新增测试项", "修改测试项", "删除测试项", "评价结果确认", "退回评价修改",
        "保存评价历史", "调整评价细则", "调整统计规则", "导出评价结果",
    ])
    m.add_permission(role="技术主管", operations=["审核报告", "审核证书", "审核结果通知单"])
    m.add_permission(role="实验室负责人", operations=["批准证书", "批准结果通知单"])
    m.add_permission(role="授权签字人", operations=["批准结果报告", "批准结果通知单", "批准使用认可标识"])
    m.add_permission(role="策划人员", operations=[
        "编制设计方案", "编制作业指导书", "编制结果报告", "编制结果通知单",
        "编制任务通知书", "项目总结", "记录归档",
    ])
    m.add_permission(role="样品管理员", operations=[
        "查询样品", "样品入库", "样品出库", "样品核查", "样品归还记录", "样品领用登记",
    ])
    m.add_permission(role="样品制备人员", operations=[
        "编制样品制备方案", "执行样品制备", "样品配置", "样品一致性测试",
    ])
    m.add_permission(role="统计人员", operations=["查询统计", "评价统计分析"])
    m.add_permission(role="质量专员", operations=["查询报告统计"])
    m.add_permission(role="财务人员", operations=[
        "查询缴费记录", "确认付款", "开具发票", "退款操作", "修改财务备注",
        "上传发票", "查询收入统计", "查询缴费信息",
    ])

    # ===== Step 1.2-1.4 实体落盘 =====

    # E-XM 项目 (验证项目) - core, multi-state
    m.add_entity(
        id="E-XM", name="项目", desc="能力验证/测量审核项目主体记录", type="core",
        tags=["approvable", "multi-state", "expirable", "collaborative"],
        attributes=[
            attr(name="项目编号", desc="项目唯一编号"),
            attr(name="项目名称", desc="项目名称"),
            attr(name="业务类型", desc="能力验证或测量审核", is_config=True),
            attr(name="产品类型", desc="项目产品分类"),
            attr(name="项目类型", desc="能力验证/测量审核"),
            attr(name="所属年度", desc="项目所属年度"),
            attr(name="项目费用", desc="项目应收费用金额"),
            attr(name="子领域", desc="项目所属子领域"),
            attr(name="依据标准", desc="项目依据标准"),
            attr(name="技术主管", desc="项目技术主管"),
            attr(name="实验室负责人", desc="项目实验室负责人"),
            attr(name="授权签字人", desc="项目授权签字人"),
            attr(name="监督员", desc="项目监督员（新增字段）"),
            attr(name="评价人员", desc="项目评价人员列表"),
            attr(name="评价组长", desc="首位被选择的评价人员默认为组长"),
            attr(name="评分方式", desc="分值或权重", is_config=True),
            attr(name="项目人员信息", desc="项目人员配置"),
            attr(name="财务备注", desc="财务备注字段"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "inferred": ["进行中", "报告审核中"],
                "note": {"comment": "§19.3枚举5态全收；进行中、报告审核中由 §19.1/19.2 阶段切换推导（样品发放后进入实施、编制结果报告时进入审核）"},
            },
        ],
        operations=[
            op(name="查询项目", category="query", expected_results=["分页展示符合条件的项目记录"], source_ref="20.5.1项目管理；20.6.1项目管理",
               note=N(role="项目管理员", comment="列表查询")),
            op(name="新增项目", category="crud", expected_results=["项目创建成功并分配项目编号", "技术主管/实验室负责人/授权签字人字段默认填充唯一候选人", "监督员字段填入项目人员信息"], source_ref="20.5.1项目管理；20.5.1.5项目新增表单增加监督员；20.5.1.6默认填充",
               note=N(role="项目管理员", comment="CRUD创建；含子领域常用测试项管理")),
            op(name="修改项目", category="crud", expected_results=["项目信息更新成功"], source_ref="20.5.1项目管理",
               note=N(role="项目管理员", comment="CRUD修改")),
            op(name="上传文件", category="file", expected_results=["归档任务已开启，请稍后查看", "整理完成后操作列显示查看归档按钮"], source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员", comment="文件归集；含打包下载")),
            op(name="打包下载", category="file", expected_results=["下载zip格式归档文件，内含清单和按项目阶段命名的目录"], source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员", comment="归档文件打包下载")),
            op(name="代码导入", category="file", expected_results=["导入报名机构三方代码成功"], source_ref="20.5.1.2机构代码导入",
               note=N(role="项目管理员", comment="机构代码批量导入")),
            op(name="上传结果通知单", category="file", expected_results=["结果通知单文件上传成功"], source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员", comment="批量处理：根据处理内容和上传状态筛选")),
            op(name="上传证书", category="file", expected_results=["证书文件上传成功"], source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员", comment="批量处理：根据处理内容和上传状态筛选")),
            op(name="提交审核", category="crud", expected_results=["选定记录批量提交审核成功", "无选择记录时提示选择"], source_ref="20.5.1.3项目批量操作",
               note=N(role="项目管理员", comment="批量审核提交")),
            op(name="消息发送", category="crud", expected_results=["按选择方式发送消息", "未结束项目可发送"], source_ref="20.5.1.4优化消息发送功能",
               note=N(role="项目管理员", comment="详情页消息发送；接收人1和2不能同时为空")),
            op(name="测试发送", category="crud", expected_results=["发送测试信息成功"], source_ref="20.5.1.4优化消息发送功能",
               note=N(role="项目管理员", comment="消息发送测试")),
            op(name="导出项目通知书", category="file", expected_results=["导出项目通知书文件", "监督员字段填充到对应位置"], source_ref="20.5.1.5项目新增表单增加监督员",
               note=N(role="项目管理员", comment="项目通知书导出")),
            op(name="修改财务备注", category="crud", expected_results=["财务备注修改成功"], source_ref="20.10.2.1项目列表增加财务备注字段",
               note=N(role="财务人员", comment="财务备注字段修改")),
        ],
    )

    # E-YP 样品 - core
    m.add_entity(
        id="E-YP", name="样品", desc="能力验证/测量审核样品", type="core",
        tags=["collaborative"],
        attributes=[
            attr(name="样品编号", desc="样品唯一编号"),
            attr(name="样品名称", desc="样品名称"),
            attr(name="所属项目", desc="样品所属项目"),
            attr(name="制备方案", desc="样品制备方案"),
            attr(name="核查记录", desc="样品核查记录表"),
            attr(name="快递单号", desc="样品发放快递单号"),
            attr(name="软件访问路径", desc="软件访问路径"),
        ],
        state_dimensions=[
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查", "已发样", "已还样", "无需还样"],
                "initial": "待核查",
                "terminal": ["已还样", "无需还样"],
                "note": {"comment": "§19.3枚举仅含待核查、已核查；§19.1/19.2流程表追加已发样、已还样、无需还样"},
            },
        ],
        operations=[
            op(name="查询样品", category="query", expected_results=["分页展示样品记录"], source_ref="3.2功能要求样品管理",
               note=N(role="样品管理员", comment="样品查询")),
            op(name="样品入库", category="crud", expected_results=["样品入库登记成功"], source_ref="12库存管理",
               note=N(role="样品管理员", comment="库存入库登记")),
            op(name="样品出库", category="crud", expected_results=["样品出库登记成功"], source_ref="12库存管理",
               note=N(role="样品管理员", comment="库存出库登记")),
            op(name="样品领用登记", category="crud", expected_results=["样品领用登记成功"], source_ref="19.2实施阶段",
               note=N(role="样品管理员", comment="测量审核样品领用登记")),
            op(name="样品归还记录", category="crud", expected_results=["样品归还登记成功"], source_ref="3.2样品借出归还记录",
               note=N(role="样品管理员", comment="样品借出归还记录")),
            op(name="编制样品制备方案", category="crud", expected_results=["样品制备方案编制成功"], source_ref="11样品制备",
               note=N(role="样品制备人员", comment="制备方案编制")),
            op(name="执行样品制备", category="crud", expected_results=["样品制备执行完成"], source_ref="11样品制备",
               note=N(role="样品制备人员", comment="制备执行")),
            op(name="样品配置", category="crud", expected_results=["样品配置完成"], source_ref="11样品管理",
               note=N(role="样品制备人员", comment="样品配置")),
            op(name="样品一致性测试", category="crud", expected_results=["一致性测试完成"], source_ref="11样品管理",
               note=N(role="样品制备人员", comment="一致性测试")),
        ],
    )

    # E-BMJL 报名记录 - core, multi-state (6 dims)
    m.add_entity(
        id="E-BMJL", name="报名记录", desc="能力验证/测量审核参加者报名记录", type="core",
        tags=["approvable", "multi-state", "expirable", "collaborative"],
        attributes=[
            attr(name="报名编号", desc="报名记录唯一编号"),
            attr(name="项目编号", desc="关联项目编号"),
            attr(name="实验室编号", desc="报名实验室编号"),
            attr(name="统一社会信用代码", desc="实验室统一社会信用代码"),
            attr(name="实验室名称", desc="实验室名称"),
            attr(name="报名时间", desc="报名时间"),
            attr(name="评价得分", desc="实验室评价得分"),
            attr(name="评价结果", desc="评价结果"),
            attr(name="证书编号", desc="证书编号"),
            attr(name="应收金额", desc="应收费用金额"),
            attr(name="已收金额", desc="已收费用金额"),
            attr(name="退款金额", desc="退款金额（累加）"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="管理备注", desc="退款原因等管理备注"),
            attr(name="支付方式", desc="支付方式"),
            attr(name="支付账户名称", desc="支付账户名称"),
            attr(name="汇款金额", desc="汇款金额，默认项目费用金额"),
            attr(name="付款底单", desc="付款底单文件"),
            attr(name="开票类型", desc="电子专票/电子普票"),
            attr(name="到款日期", desc="到款日期"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交",
                           "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "note": {"comment": "§19.3枚举9态全收，顺序照原文"},
            },
            {
                "dimension_name": "通知状态",
                "states": ["未发送", "已发送", "待确认", "已确认", "待审核", "退回", "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已批准", "已确认"],
                "note": {"comment": "§19.3枚举'通知状态'与§19.1/19.2流程表'预通知状态'列同源；合并取并集"},
            },
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "note": {"comment": "§19.3枚举4态全收"},
            },
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": [],
                "note": {"comment": "§19.3枚举2态；§20.5.2.1多次付款不影响状态值，仅累计已收金额；t30退款已缴费→待缴费，已缴费非终态，状态机构成循环"},
            },
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "note": {"comment": "§19.3枚举2态；§20.10.2.2支持多次分批上传，状态不变"},
            },
            {
                "dimension_name": "缴费通知状态",
                "states": ["未发送", "已发送"],
                "initial": "未发送",
                "terminal": ["已发送"],
                "inferred": ["未发送", "已发送"],
                "note": {"comment": "§19.3未列，由§19.1/19.2流程表'缴费通知单'列推导；视为报名记录的子状态维度"},
            },
        ],
        operations=[
            op(name="查询报名信息", category="query", expected_results=["分页展示报名记录"], source_ref="20.5.1项目管理；20.6.1项目管理",
               note=N(role="项目管理员", comment="报名信息查询")),
            op(name="报名项目", category="crud", expected_results=["报名记录创建成功，状态为报名待审核"], source_ref="19.1实施阶段；19.2项目准备阶段",
               note=N(role="能力验证参加者", comment="CRUD创建；触发e13/e29/e32/e34")),
            op(name="上传付款单", category="file", expected_results=["付款单上传成功，可多次上传不对金额校验"], source_ref="20.5.2.1已报名项目增加多次付款功能",
               note=N(role="能力验证参加者", comment="多次付款；F9回写动作匹配'上传'")),
            op(name="上传测试结果", category="file", expected_results=["测试结果上传成功，状态变为结果已提交"], source_ref="19.1实施阶段；19.2实施阶段",
               note=N(role="能力验证参加者", comment="测试结果提交；触发e18")),
            op(name="上传缴费证明", category="file", expected_results=["缴费证明上传成功"], source_ref="18能力验证参加者报名缴费",
               note=N(role="能力验证参加者", comment="缴费证明上传")),
            op(name="下载预通知", category="file", expected_results=["预通知文件下载成功"], source_ref="20.5.2.2已报名项目详情页面增加预通知文件下载",
               note=N(role="能力验证参加者", comment="文件下载Tab下预通知下载")),
            op(name="下载结果通知单", category="file", expected_results=["结果通知单文件下载成功"], source_ref="18能力验证参加者报告提交接收",
               note=N(role="能力验证参加者", comment="结果通知单下载")),
            op(name="下载证书", category="file", expected_results=["合格证书文件下载成功"], source_ref="18能力验证参加者报告提交接收",
               note=N(role="能力验证参加者", comment="证书下载")),
            op(name="上传发票", category="file", expected_results=["发票上传成功，支持多次分批上传"], source_ref="20.10.2.2修改发票上传功能",
               note=N(role="财务人员", comment="多次分批上传发票")),
            op(name="确认付款", category="crud", expected_results=["付款信息确认成功"], source_ref="16财务管理人员财务统计",
               note=N(role="财务人员", comment="付款信息确认")),
            op(name="退款操作", category="crud", expected_results=["退款成功，退款金额累加，实际付款更新"], source_ref="20.10.2.3缴费单退款",
               note=N(role="财务人员", comment="退款操作；退款金额不能大于当前缴费金额")),
            op(name="查询缴费记录", category="query", expected_results=["分页展示缴费记录"], source_ref="20.10.1缴费信息管理",
               note=N(role="财务人员", comment="缴费信息查询")),
            op(name="查询收入统计", category="query", expected_results=["分页展示收入统计数据"], source_ref="20.8.5收入统计",
               note=N(role="财务人员", comment="收入统计查询")),
            op(name="查询缴费信息", category="query", expected_results=["分页展示缴费信息"], source_ref="20.10.1.1缴费信息查询与管理",
               note=N(role="财务人员", comment="缴费信息管理查询")),
        ],
    )

    # E-SYS 实验室信息 - core
    m.add_entity(
        id="E-SYS", name="实验室信息", desc="实验室信息记录，需审核通过方可用于项目报名", type="core",
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
                "states": ["待审核", "启用", "停用", "退回修改"],
                "initial": "待审核",
                "terminal": [],
                "note": {"comment": "§20.3.1枚举4态；§20.4.1.1查询选项列'已退回'与§20.3.1'退回修改'为同义，两口径并列：取§20.3.1为状态值，§20.4.1.1'已退回'视为查询别名"},
            },
        ],
        operations=[
            op(name="查询实验室", category="query", expected_results=["分页展示实验室记录"], source_ref="20.4.1.1实验室列表与查询",
               note=N(role="系统管理员", comment="支持实验室编号/名称/状态独立或组合查询")),
            op(name="新增实验室信息", category="crud", expected_results=["实验室信息新增成功，状态为待审核"], source_ref="20.3.1实验室信息",
               note=N(role="能力验证参加者", comment="机构新增实验室信息")),
            op(name="修改实验室信息", category="crud", expected_results=["修改后状态变为待审核"], source_ref="20.4.1.3实验室修改；20.3.1实验室信息",
               note=N(role="能力验证参加者", comment="启用状态修改后回到待审核")),
            op(name="审核实验室", category="crud", expected_results=["通过则状态变为启用并生成快照", "退回修改则状态变为退回修改，审核意见必填"], source_ref="20.4.1.2实验室审核",
               note=N(role="系统管理员", comment="实验室审核；审核结果为通过时审核意见可为空，退回修改必填")),
            op(name="停用实验室", category="crud", expected_results=["实验室状态变为停用"], source_ref="20.4.1.1实验室列表与查询",
               note=N(role="系统管理员", comment="启用状态可停用")),
            op(name="启用实验室", category="crud", expected_results=["实验室状态变为启用"], source_ref="20.4.1.1实验室列表与查询",
               note=N(role="系统管理员", comment="停用状态可启用")),
        ],
    )

    # E-BZK 标准库 - managed
    m.add_entity(
        id="E-BZK", name="标准库", desc="标准库基础数据，下属测试项和参数", type="managed",
        tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="标准库编号"),
            attr(name="标准库名称", desc="标准库名称"),
            attr(name="状态", desc="启用/停用", is_config=True),
            attr(name="描述", desc="标准库描述"),
            attr(name="创建时间", desc="创建时间"),
        ],
        state_dimensions=[
            {
                "dimension_name": "标准库状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "note": {"comment": "§20.4.2标准库管理2态；停用的标准库在项目创建等环节不可被选择"},
            },
        ],
        operations=[
            op(name="查询标准库", category="query", expected_results=["分页展示标准库记录"], source_ref="20.4.2.1标准库列表与查询",
               note=N(role="系统管理员", comment="支持编号/名称/状态独立或组合查询")),
            op(name="新增标准库", category="crud", expected_results=["标准库创建成功，默认启用"], source_ref="20.4.2.2新增标准库",
               note=N(role="系统管理员", comment="新增表单：编号/名称/状态/描述")),
            op(name="修改标准库", category="crud", expected_results=["标准库信息修改成功"], source_ref="20.4.2.3修改标准库",
               note=N(role="系统管理员", comment="修改表单：编号/名称/状态/描述")),
            op(name="删除标准库", category="crud", expected_results=["标准库删除成功"], source_ref="20.4.2.4删除标准库",
               note=N(role="系统管理员", comment="二次确认删除")),
            op(name="停用标准库", category="crud", expected_results=["标准库状态变为停用"], source_ref="20.4.2.5停用/启用标准库",
               note=N(role="系统管理员", comment="停用后项目创建环节不可选择")),
            op(name="启用标准库", category="crud", expected_results=["标准库状态变为启用"], source_ref="20.4.2.5停用/启用标准库",
               note=N(role="系统管理员", comment="启用状态恢复")),
            op(name="管理测试项", category="ui", expected_results=["跳转至标准库的测试项管理界面"], source_ref="20.4.2.6进入测试项管理界面",
               note=N(role="系统管理员", comment="UI导航")),
        ],
    )

    # E-CSX 测试项 (managed, under E-BZK)
    m.add_entity(
        id="E-CSX", name="测试项", desc="标准库下的测试项及子测试项、参数", type="managed",
        tags=[],
        attributes=[
            attr(name="标号", desc="测试项标号"),
            attr(name="名称", desc="测试项名称"),
            attr(name="所属标准库", desc="所属标准库"),
            attr(name="父测试项", desc="父级测试项"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增测试项", category="crud", expected_results=["测试项新增成功"], source_ref="20.4.2.8新增测试项",
               note=N(role="系统管理员", comment="新增子项或一级测试项")),
            op(name="修改测试项", category="crud", expected_results=["测试项修改成功"], source_ref="20.4.2.9修改测试项",
               note=N(role="系统管理员", comment="修改测试项/参数")),
            op(name="删除测试项", category="crud", expected_results=["测试项删除成功", "含有子项的记录不允许删除"], source_ref="20.4.2.10删除测试项",
               note=N(role="系统管理员", comment="含子项不可删除")),
        ],
    )

    # E-ZYL 子领域 (managed)
    m.add_entity(
        id="E-ZYL", name="子领域", desc="项目子领域，关联标准库测试项", type="managed",
        tags=[],
        attributes=[
            attr(name="子领域名称", desc="子领域名称"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询子领域测试项", category="query", expected_results=["树形展示子领域下测试项"], source_ref="20.4.3.2测试项列表与结构展示",
               note=N(role="系统管理员", comment="树形展示")),
            op(name="新增子领域测试项", category="crud", expected_results=["从标准库选择测试项添加到子领域"], source_ref="20.4.3.3新增测试项",
               note=N(role="系统管理员", comment="选择方式添加")),
            op(name="删除子领域测试项", category="crud", expected_results=["测试项从子领域移除"], source_ref="20.4.3.4删除测试项",
               note=N(role="系统管理员", comment="含子项不可删除")),
        ],
    )

    # E-PJ 评价 - core
    m.add_entity(
        id="E-PJ", name="评价", desc="项目评价记录，含协同评价与组长确认", type="core",
        tags=["approvable", "multi-state", "collaborative", "configurable"],
        attributes=[
            attr(name="项目编号", desc="关联项目"),
            attr(name="评分方式", desc="分值或权重", is_config=True),
            attr(name="评价人员", desc="评价人员列表"),
            attr(name="评价组长", desc="首位被选择的评价人员"),
            attr(name="及格分", desc="及格分"),
            attr(name="评价细则", desc="评价细则内容"),
            attr(name="测试项目", desc="评价测试项目"),
            attr(name="评价结果", desc="最终评价结果"),
            attr(name="历史结果", desc="评价历史结果文件"),
            attr(name="统计规则", desc="成绩区间统计规则"),
        ],
        state_dimensions=[
            {
                "dimension_name": "评价状态",
                "states": ["待评价", "评价中", "评价完成"],
                "initial": "待评价",
                "terminal": ["评价完成"],
                "inferred": ["待评价", "评价中", "评价完成"],
                "note": {"comment": "§20.7未显式枚举评价状态；由§20.7.1.1完善后→待评价、§20.7.1.2评价人员评价→评价中、§20.7.1.3结果确认→评价完成 推导"},
            },
        ],
        operations=[
            op(name="查询评价", category="query", expected_results=["展示评价项目列表"], source_ref="20.7.1项目列表",
               note=N(role="评价人员", comment="评价项目列表查询")),
            op(name="完善测试项目", category="crud", expected_results=["测试项目及评价细则完善成功"], source_ref="20.7.1.1测试项目、评价细则完善",
               note=N(role="评价组长", comment="组长完善")),
            op(name="完善评价细则", category="crud", expected_results=["评价细则配置成功"], source_ref="20.7.1.1测试项目、评价细则完善",
               note=N(role="评价组长", comment="评价细则编辑")),
            op(name="另存常用项", category="crud", expected_results=["常用测试项组合保存成功"], source_ref="20.7.1.1测试项目、评价细则完善",
               note=N(role="评价组长", comment="另存常用")),
            op(name="删除常用项", category="crud", expected_results=["常用项删除成功"], source_ref="20.7.1.1测试项目、评价细则完善",
               note=N(role="评价组长", comment="常用项删除")),
            op(name="评价录入", category="crud", expected_results=["评价人员提交自己的评价结果", "只能修改自己的评价结果"], source_ref="20.7.1.2协同评价",
               note=N(role="评价人员", comment="评价人员只能修改自己的评价结果")),
            op(name="评价结果确认", category="crud", expected_results=["当前结果提交为最终评价结果，项目评价状态关闭"], source_ref="20.7.1.3评价确认",
               note=N(role="评价组长", comment="组长确认最终结果")),
            op(name="退回评价修改", category="crud", expected_results=["当前评价结果保存为历史结果，开启下一轮评价"], source_ref="20.7.1.3评价确认",
               note=N(role="评价组长", comment="退回修改开启新一轮")),
            op(name="保存评价历史", category="crud", expected_results=["当前评价结果保存为历史结果"], source_ref="20.7.1.3评价确认",
               note=N(role="评价组长", comment="历史保存")),
            op(name="调整评价细则", category="crud", expected_results=["打开评价细节完善页面，配置完成回到本页刷新"], source_ref="20.7.1.3评价确认",
               note=N(role="评价组长", comment="调整细则")),
            op(name="调整统计规则", category="crud", expected_results=["统计规则配置成功"], source_ref="20.7.1.3评价确认",
               note=N(role="评价组长", comment="成绩区间统计规则配置")),
            op(name="导出评价结果", category="file", expected_results=["下载评价结果文件"], source_ref="20.7.1.4评价结果导出",
               note=N(role="评价人员", comment="评价结果导出")),
        ],
    )

    # E-FP 发票 (managed)
    m.add_entity(
        id="E-FP", name="发票", desc="项目发票记录，支持多次分批上传", type="managed",
        tags=[],
        attributes=[
            attr(name="发票编号", desc="发票编号"),
            attr(name="开票时间", desc="最后一次开票时间"),
            attr(name="电子发票", desc="电子发票文件"),
            attr(name="关联项目", desc="项目报名编号"),
            attr(name="项目金额", desc="项目费用"),
            attr(name="开票类型", desc="电子专票/电子普票", is_config=True),
        ],
        state_dimensions=[],
        operations=[
            op(name="开具发票", category="crud", expected_results=["发票上传成功，支持多次分批上传"], source_ref="20.10.2.2修改发票上传功能",
               note=N(role="财务人员", comment="多次分批上传")),
        ],
    )

    # E-JF 缴费记录 (managed)
    m.add_entity(
        id="E-JF", name="缴费记录", desc="项目缴费记录，含退款功能", type="managed",
        tags=["expirable"],
        attributes=[
            attr(name="缴费编号", desc="缴费记录编号"),
            attr(name="报名编号", desc="关联报名编号"),
            attr(name="付款金额", desc="付款金额"),
            attr(name="退款金额", desc="退款金额累加"),
            attr(name="实际付款", desc="付款金额-退款金额"),
            attr(name="到款时间", desc="到款日期"),
            attr(name="管理备注", desc="退款原因等"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询缴费记录", category="query", expected_results=["分页展示缴费记录"], source_ref="20.10.1缴费信息管理",
               note=N(role="财务人员", comment="缴费信息查询")),
            op(name="退款操作", category="crud", expected_results=["退款金额累加，实际付款更新"], source_ref="20.10.2.3缴费单退款",
               note=N(role="财务人员", comment="退款金额不能大于当前缴费金额")),
        ],
    )

    # E-XXJL 信息发送记录 (managed)
    m.add_entity(
        id="E-XXJL", name="信息发送记录", desc="系统信息发送历史记录", type="managed",
        tags=[],
        attributes=[
            attr(name="发送方式", desc="短信/邮件/站内信"),
            attr(name="接收人", desc="接收人"),
            attr(name="发送时间", desc="发送时间"),
            attr(name="发送人", desc="发送人"),
            attr(name="发送结果", desc="发送结果"),
            attr(name="消息标题", desc="消息标题"),
            attr(name="消息内容", desc="消息内容"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询信息发送记录", category="query", expected_results=["分页展示信息发送记录"], source_ref="20.4.4.1信息发送记录",
               note=N(role="系统管理员", comment="仅系统管理员和项目管理员可查")),
            op(name="查看消息详情", category="query", expected_results=["展示消息详细内容"], source_ref="20.4.4.1信息发送记录",
               note=N(role="系统管理员", comment="消息详情查看")),
        ],
    )

    # E-TZGG 通知公告 (managed)
    m.add_entity(
        id="E-TZGG", name="通知公告", desc="系统通知公告", type="managed",
        tags=[],
        attributes=[
            attr(name="标题", desc="通知标题"),
            attr(name="内容", desc="通知内容"),
            attr(name="发布时间", desc="发布时间"),
            attr(name="new标识", desc="15天内发布显示new标识"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询通知公告", category="query", expected_results=["展示通知公告列表", "15天内发布显示new标识"], source_ref="20.2.1通知公告",
               note=N(role="能力验证参加者", comment="公开查询")),
        ],
    )

    # E-CJWT 常见问题 (managed)
    m.add_entity(
        id="E-CJWT", name="常见问题", desc="高频咨询问题及典型误操作场景", type="managed",
        tags=[],
        attributes=[
            attr(name="问题标题", desc="问题标题"),
            attr(name="解决方案", desc="解决方案"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询常见问题", category="query", expected_results=["展示常见问题列表"], source_ref="20.2.2常见问题",
               note=N(role="能力验证参加者", comment="自助查询")),
        ],
    )

    # E-DAI 待办事项 (managed)
    m.add_entity(
        id="E-DAI", name="待办事项", desc="用户待办事项", type="managed",
        tags=[],
        attributes=[
            attr(name="待办内容", desc="待办内容"),
            attr(name="处理状态", desc="待处理/已处理"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询待办", category="query", expected_results=["展示待办事项列表"], source_ref="20.2.3待办事项",
               note=N(role="项目管理员", comment="管理侧待办")),
            op(name="处理待办", category="crud", expected_results=["待办处理完成"], source_ref="20.2.3待办事项",
               note=N(role="项目管理员", comment="待办处理")),
        ],
    )

    # E-XMWT 项目文件 (managed)
    m.add_entity(
        id="E-XMWT", name="项目文件", desc="项目归档文件，含主子表结构", type="managed",
        tags=[],
        attributes=[
            attr(name="文件名称", desc="文件名称"),
            attr(name="项目阶段", desc="项目阶段"),
            attr(name="份数", desc="份数"),
            attr(name="页数", desc="页数"),
            attr(name="备注", desc="备注"),
            attr(name="实验室", desc="子表所属实验室"),
        ],
        state_dimensions=[],
        operations=[
            op(name="上传文件", category="file", expected_results=["归档任务已开启，请稍后查看"], source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员", comment="归档文件上传")),
            op(name="打包下载", category="file", expected_results=["下载zip格式归档文件，内含清单和按项目阶段命名的目录"], source_ref="20.5.1.1文件整理",
               note=N(role="项目管理员", comment="归档文件打包下载")),
        ],
    )

    # ===== Step 1.5 结构关系 =====
    # 标准库 → 测试项：composition (B 无独立创建流程就随 A 创建；测试项必须依附标准库)
    m.add_structural(
        frm="E-BZK", to="E-CSX", relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="标准库下属测试项及参数，分层级维护；测试项必须依附标准库存在",
        confidence="high",
        note={"comment": "判定(b)：B(测试项)无独立创建流程，A(标准库)创建时B自动入initial；每条A可有多个B"},
    )
    # 标准库 → 子领域测试项：reference (子领域有独立管理流程)
    m.add_structural(
        frm="E-BZK", to="E-ZYL", relation_type="reference", cardinality="M:N",
        ownership_dimension="configuration_source",
        desc="子领域通过选择方式引用标准库的测试项，作为项目创建时数据源",
        confidence="high",
        note={"comment": "判定(d)：B(子领域)有独立管理流程，A(标准库)仅作为配置数据源；§20.4.3子领域管理由表单方式改为选择方式，选择数据来源于标准库"},
    )
    # 项目 → 报名记录：composition (报名记录依附项目)
    m.add_structural(
        frm="E-XM", to="E-BMJL", relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目下属报名记录，每个项目可有多个参加者报名记录",
        confidence="high",
        note={"comment": "判定(c)：B(报名记录)有独立创建流程，B是core流程实体；A(项目)为其业务归属容器"},
    )
    # 项目 → 样品：composition (样品依附项目)
    m.add_structural(
        frm="E-XM", to="E-YP", relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目下属样品，每个项目可有多个样品",
        confidence="high",
        note={"comment": "判定(b)：B(样品)随A(项目)创建自动入initial；样品制备由样品制备人员执行"},
    )
    # 项目 → 评价：composition (评价依附项目)
    m.add_structural(
        frm="E-XM", to="E-PJ", relation_type="composition", cardinality="1:1",
        ownership_dimension="business_ownership",
        desc="项目下属评价记录，每项目一个评价",
        confidence="high",
        note={"comment": "判定(b)：B(评价)随A(项目)创建自动入initial；§20.7评价功能调整"},
    )
    # 报名记录 → 缴费记录：reference (缴费记录有独立管理)
    m.add_structural(
        frm="E-BMJL", to="E-JF", relation_type="reference", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="报名记录关联缴费记录，支持多次付款与退款",
        confidence="high",
        note={"comment": "判定(d)：B(缴费记录)有独立管理流程；A(报名记录)为其业务归属；management_dimension复核：缴费记录由财务人员独立管理"},
    )
    # 报名记录 → 发票：reference (发票有独立管理)
    m.add_structural(
        frm="E-BMJL", to="E-FP", relation_type="reference", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="报名记录关联发票，支持多次分批上传",
        confidence="high",
        note={"comment": "判定(d)：B(发票)有独立管理流程；§20.10.2.2支持多次分批上传"},
    )
    # 项目 → 项目文件：composition (项目文件随项目归档)
    m.add_structural(
        frm="E-XM", to="E-XMWT", relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="项目下属归档文件，按项目阶段组织",
        confidence="high",
        note={"comment": "判定(b)：B(项目文件)随A(项目)归档自动生成；§20.5.1.1文件整理"},
    )
    # 能力验证参加者 → 实验室信息：reference (参加者管理自己的实验室信息)
    m.add_structural(
        frm="E-SYS", to="E-BMJL", relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="实验室信息用于项目报名，需审核通过方可用于报名",
        confidence="high",
        note={"comment": "判定(d)：B(报名记录)有独立创建流程；A(实验室信息)作为报名前置配置；§20.3.1实验室信息需审核通过后方可用于项目报名"},
    )

    # ===== Step 2 分支维度 =====

    # 业务类型分支：能力验证 vs 测量审核（is_config 属性，创建时定）
    m.add_branch_dimension(
        dimension="业务类型", entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="影响项目流程：能力验证需样品核查与发放、可无需还样分支；测量审核需作业指导书审核环节、领用登记",
        evidence="三型判定：①配置型（is_config 属性'业务类型'，创建时定、影响后续流程，见20.5.1项目管理；20.6.1项目管理）",
        branches=[
            {"value": "能力验证", "target_transition": "t02", "desc": "PT 路径：设计方案编制→能力验证计划发布→实施阶段含样品核查/发放/无需还样分支"},
            {"value": "测量审核", "target_transition": "t03", "desc": "MA 路径：测量审核受理报名→作业指导书编制审核→样品领用登记；不区分计划发布与受理报名，统一为创建"},
        ],
    )

    # 评分方式分支：分值 vs 权重（is_config 属性，评价配置）
    m.add_branch_dimension(
        dimension="评分方式", entity="E-PJ",
        values=["分值", "权重"],
        impact_scope="影响评价录入与结果统计：评价列表展示分值/权重列，得分计算方式不同",
        evidence="三型判定：①配置型（is_config 属性'评分方式'，项目创建时定，见20.7.1项目列表）",
        branches=[
            {"value": "分值", "target_transition": "t47", "desc": "分值方式：评价人员按分值打分，结果差异型共用转换"},
            {"value": "权重", "target_transition": "t47", "desc": "权重方式：评价人员按权重打分，结果差异型共用转换"},
        ],
    )

    # 审核结果分支：通过 vs 退回修改（运行时选择型，影响实验室/报名记录转换路径）
    m.add_branch_dimension(
        dimension="审核结果", entity="E-SYS",
        values=["通过", "退回修改"],
        impact_scope="影响实验室状态转换：通过→启用并生成快照；退回修改→退回修改状态且必须填写审核意见",
        evidence="三型判定：②运行时选择型（'审核结果单选框：通过/退回修改'，见20.4.1.2实验室审核）",
        branches=[
            {"value": "通过", "target_transition": "t39", "desc": "通过路径：状态变更为启用，生成快照记录"},
            {"value": "退回修改", "target_transition": "t39b", "desc": "退回修改路径：状态变更为退回修改，必须填写审核意见"},
        ],
    )

    # 样品归还分支：需还样 vs 无需还样（运行时选择型，影响样品状态转换路径）
    m.add_branch_dimension(
        dimension="样品归还方式", entity="E-YP",
        values=["需还样", "无需还样"],
        impact_scope="影响样品最终状态：需还样→已还样；无需还样→无需还样",
        evidence="三型判定：②运行时选择型（§19.1流程表'已还样、待核查/无需还样'分支，见19.1实施阶段）",
        branches=[
            {"value": "需还样", "target_transition": "t10", "desc": "需还样路径：参加者测试与结果提交后样品状态变为已还样"},
            {"value": "无需还样", "target_transition": "t10b", "desc": "无需还样路径：参加者测试与结果提交后样品状态变为无需还样"},
        ],
    )

    # ===== Step 3.1 转换 =====

    # ---- E-XM 项目 项目状态 ----
    # t01 创建转换：设计方案编制
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始", action="设计方案编制", role="策划人员",
        preconditions=[],
        expected_results=["项目创建成功，状态为待开始"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1方案设计阶段；19.2方案设计阶段",
        note={"comment": "源自 e01；⓪frm=None创建转换"},
    )
    # t02 能力验证计划发布
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中", action="能力验证计划发布", role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
            precond(text="设计方案已编制完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变为报名中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e02；③序判frm先于to；PT路径项目发布"},
    )
    # t03 测量审核受理报名（MA 路径）
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm=None, to="报名中", action="测量审核受理报名", role="项目管理员",
        preconditions=[],
        expected_results=["测量审核项目创建，状态为报名中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2项目准备阶段",
        note={"comment": "源自 e03；⓪frm=None创建转换；MA路径直接进入报名中"},
    )
    # t04 进入实施（inferred）
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中", action="进入实施", role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="样品已发放", ptype="event_ref"),
        ],
        expected_results=["项目状态变为进行中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e04；③序判frm先于to；inferred：§19.1/19.2实施阶段起始推导，状态枚举含'进行中'但流程表未显式落点"},
    )
    # t05 进入报告审核（inferred）
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中", action="进入报告审核", role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
            precond(text="评价结果已确认", ptype="event_ref"),
        ],
        expected_results=["项目状态变为报告审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.2报告编制和结果通知",
        note={"comment": "源自 e05；③序判frm先于to；inferred：状态枚举含'报告审核中'但流程表未显式落点，由报告编制阶段推导"},
    )
    # t06 发放结果报告和证书（项目结束）
    m.add_trans(
        tid="t06", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="结果报告和证书已批准", ptype="event_ref"),
        ],
        expected_results=["项目状态变为已结束"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.2报告编制和结果通知",
        note={"comment": "源自 e06；③序判frm先于to；终态：已结束"},
    )

    # ---- E-YP 样品 样品状态 ----
    # t07 样品领用登记（MA 路径创建转换）
    m.add_trans(
        tid="t07", entity="E-YP", dimension="样品状态",
        frm=None, to="待核查", action="样品领用登记", role="样品管理员",
        preconditions=[],
        expected_results=["样品状态变为待核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"comment": "源自 e12；⓪frm=None创建转换；MA路径样品领用"},
    )
    # t08 样品核查
    m.add_trans(
        tid="t08", entity="E-YP", dimension="样品状态",
        frm="待核查", to="已核查", action="样品核查", role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变为已核查"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e07；③序判frm先于to"},
    )
    # t09 样品发放（PT/MA 共用：已核查→已发样）
    m.add_trans(
        tid="t09", entity="E-YP", dimension="样品状态",
        frm="已核查", to="已发样", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
        ],
        expected_results=["样品状态变为已发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e08；③序判frm先于to；含作业指导书发送"},
    )
    # t10 参加者测试与结果提交（分支：需还样→已还样）
    m.add_trans(
        tid="t10", entity="E-YP", dimension="样品状态",
        frm="已发样", to="已还样", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已发样")),
            precond(text="样品归还方式=需还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["需还样样品状态变为已还样"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "样品归还方式", "comment": "源自 e09；路径分歧：Step 2 value=需还样 指向本条"},
    )
    # t10b 无需还样分支
    m.add_trans(
        tid="t10b", entity="E-YP", dimension="样品状态",
        frm="已发样", to="无需还样", action="无需还样", role="能力验证参加者",
        preconditions=[
            precond(text="样品处于已发样状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已发样")),
            precond(text="样品归还方式=无需还样", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["无需还样样品状态变为无需还样"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"branch_dimension": "样品归还方式", "comment": "源自 e10；路径分歧：Step 2 value=无需还样 指向本条"},
    )
    # t11 样品重置（循环状态机）
    m.add_trans(
        tid="t11", entity="E-YP", dimension="样品状态",
        frm="已核查", to="待核查", action="样品重置", role="样品管理员",
        preconditions=[
            precond(text="样品处于已核查状态", ptype="state_ref",
                    ref=state_ref("E-YP", "样品状态", "已核查")),
        ],
        expected_results=["样品状态变为待核查，进入下一批次"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e11；序判④，语义forward（循环状态机），语义优先"},
    )

    # ---- E-BMJL 报名记录 报名记录状态 ----
    # t12 报名（创建转换）
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["报名记录创建，状态为报名待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e13；⓪frm=None创建转换；跨主体门禁：项目.报名中 落 state_ref"},
    )
    # t13 报名撤销
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="已撤销", action="报名撤销", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变为已撤销"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e14；③序判frm先于to；终态：已撤销"},
    )
    # t14 报名审核通过
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
            precond(text="实验室信息处于启用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["报名记录状态变为报名成功，缴费通知状态变为已发送"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e15；③序判frm先于to；audit留痕；跨主体门禁：实验室信息.启用 落 state_ref；联动 e35 缴费通知状态→已发送"},
    )
    # t15 报名审核退回
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回", action="报名审核退回", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变为报名退回，向参加者发送'审核未通过'短信"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e16；①'退回'→backward；audit留痕；rollback回退；触发短信通知（b22）"},
    )
    # t16 能力验证预通知
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="样品已核查", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为结果待提交，通知状态变为已发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e17；③序判frm先于to；联动 e22 通知状态→已发送"},
    )
    # t17 参加者测试与结果提交
    m.add_trans(
        tid="t17", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
            precond(text="样品已发放", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为结果已提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e18；③序判frm先于to"},
    )
    # t18 结果退回修改
    m.add_trans(
        tid="t18", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改", action="结果退回修改", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变为结果退回修改，向参加者发送'测试报告审核未通过'短信"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "源自 e19；①'退回'→backward；audit留痕；rollback回退；触发短信通知（b22）"},
    )
    # t18b 结果重新提交（退回修改后参加者重新提交→结果已提交）
    m.add_trans(
        tid="t18b", entity="E-BMJL", dimension="报名记录状态",
        frm="结果退回修改", to="结果已提交", action="参加者测试与结果提交", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果退回修改状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果退回修改")),
        ],
        expected_results=["报名记录状态变为结果已提交"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "inferred：结果退回修改后参加者重新提交结果，与 t17 同动作不同frm；序判③frm先于to；图完整性补全"},
    )
    # t15b 报名重新提交（退回后参加者重新提交→报名待审核）
    m.add_trans(
        tid="t15b", entity="E-BMJL", dimension="报名记录状态",
        frm="报名退回", to="报名待审核", action="报名", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名退回状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名退回")),
        ],
        expected_results=["报名记录状态变为报名待审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "inferred：报名退回后参加者重新提交报名，与 t12 同动作不同frm；序判③frm先于to；图完整性补全"},
    )
    # t19 编制结果报告
    m.add_trans(
        tid="t19", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中", action="编制结果报告", role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价已完成", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书审核中"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.2报告编制和结果通知",
        note={"comment": "源自 e20；③序判frm先于to"},
    )
    # t20 发放结果报告和证书
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布", action="发放结果报告和证书", role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="结果通知单已授权签字人批准", ptype="event_ref"),
            precond(text="证书已实验室负责人批准", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书已发布，向参加者发送'结果通知单已发布'短信"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.2报告编制和结果通知",
        note={"comment": "源自 e21；③序判frm先于to；终态：报告/证书已发布；触发短信通知（b22）"},
    )

    # ---- E-BMJL 报名记录 通知状态 ----
    # t50 报名（通知状态创建转换，inferred：报名时通知状态初始化为未发送）
    m.add_trans(
        tid="t50", entity="E-BMJL", dimension="通知状态",
        frm=None, to="未发送", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["通知状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "inferred创建转换：§19.1/19.2流程表'报名'行'预通知状态'列驻留值'未发送'推导为创建时初始化；与 t12 同动作跨维度，note 互引"},
    )
    # t21 能力验证预通知（PT路径：通知状态维度 未发送→已发送）
    m.add_trans(
        tid="t21", entity="E-BMJL", dimension="通知状态",
        frm="未发送", to="已发送", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "未发送")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="业务类型=能力验证", ptype="constraint",
                    note={"comment": "分支值条件：PT路径直接未发送→已发送"}),
        ],
        expected_results=["通知状态变为已发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"branch_dimension": "业务类型", "comment": "源自 e22；③序判frm先于to；路径分歧：PT路径直接未发送→已发送，MA路径经作业指导书审核；与 t16 同动作跨维度，note 互引"},
    )
    # t21b 能力验证预通知（MA路径：已审核→已发送）
    m.add_trans(
        tid="t21b", entity="E-BMJL", dimension="通知状态",
        frm="已审核", to="已发送", action="能力验证预通知", role="项目管理员",
        preconditions=[
            precond(text="报名记录通知状态为已审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "已审核")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="业务类型=测量审核", ptype="constraint",
                    note={"comment": "分支值条件：MA路径已审核→已发送"}),
        ],
        expected_results=["通知状态变为已发送"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "业务类型", "comment": "源自 e22（MA分支）；③序判frm先于to；路径分歧：MA路径作业指导书审核通过后已审核→已发送"},
    )
    # t22 预通知待确认（system 触发）
    m.add_trans(
        tid="t22", entity="E-BMJL", dimension="通知状态",
        frm="已发送", to="待确认", action="预通知待确认", role="system",
        preconditions=[
            precond(text="报名记录通知状态为已发送", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "已发送")),
        ],
        expected_results=["通知状态变为待确认，等待参加者确认"],
        traits=["time_sensitive"], direction="forward", priority="P1",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e23；③序判frm先于to；system触发；§8专项判据：超时/自动触发且改变状态"},
    )
    # t23 样品发放（通知状态：待确认→已确认）
    m.add_trans(
        tid="t23", entity="E-BMJL", dimension="通知状态",
        frm="待确认", to="已确认", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="报名记录通知状态为待确认", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "待确认")),
        ],
        expected_results=["通知状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2实施阶段",
        note={"comment": "源自 e24；③序判frm先于to；与 t09 同动作跨维度，note 互引"},
    )
    # t24 作业指导书编制（MA 路径：未发送→待审核）
    m.add_trans(
        tid="t24", entity="E-BMJL", dimension="通知状态",
        frm="未发送", to="待审核", action="作业指导书编制", role="策划人员",
        preconditions=[
            precond(text="报名记录通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "未发送")),
            precond(text="业务类型=测量审核", ptype="constraint",
                    note={"comment": "分支值条件：MA路径特有"}),
        ],
        expected_results=["通知状态变为待审核"],
        traits=["branch"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"branch_dimension": "业务类型", "comment": "源自 e25；路径分歧：MA路径特有审核环节"},
    )
    # t25 作业指导书审核退回
    m.add_trans(
        tid="t25", entity="E-BMJL", dimension="通知状态",
        frm="待审核", to="退回", action="作业指导书审核退回", role="技术主管",
        preconditions=[
            precond(text="报名记录通知状态为待审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "待审核")),
        ],
        expected_results=["通知状态变为退回"],
        traits=["audit", "rollback"], direction="backward", priority="P1",
        source_ref="19.2实施阶段",
        note={"comment": "源自 e26；①'退回'→backward；audit留痕；rollback回退"},
    )
    # t26 作业指导书审核通过
    m.add_trans(
        tid="t26", entity="E-BMJL", dimension="通知状态",
        frm="待审核", to="已审核", action="作业指导书审核通过", role="技术主管",
        preconditions=[
            precond(text="报名记录通知状态为待审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "待审核")),
        ],
        expected_results=["通知状态变为已审核"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.2实施阶段",
        note={"comment": "源自 e27；③序判frm先于to；audit留痕"},
    )
    # t27 结果通知单/证书批准（授权签字人 + 实验室负责人 协同）
    m.add_trans(
        tid="t27", entity="E-BMJL", dimension="通知状态",
        frm="已审核", to="已批准", action="结果通知单批准",
        role=["授权签字人", "实验室负责人"],
        preconditions=[
            precond(text="报名记录通知状态为已审核", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "已审核")),
            precond(text="结果报告已编制完成", ptype="event_ref"),
            precond(text="技术主管已审核报告", ptype="event_ref"),
        ],
        expected_results=["通知状态变为已批准，结果报告和证书完成批准"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="19.1报告编制和结果通知；19.2报告编制和结果通知；19.3通知状态枚举",
        note={"comment": "源自 e28；③序判frm先于to；audit留痕；终态：已批准；协同角色：授权签字人批准结果报告/结果通知单，实验室负责人签发合格证书（§5角色职责+§19.1/19.2流程表合并批准行）"},
    )

    # ---- E-BMJL 报名记录 费用状态 ----
    # t28 报名（费用状态创建）
    m.add_trans(
        tid="t28", entity="E-BMJL", dimension="费用状态",
        frm=None, to="待缴费", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["费用状态初始化为待缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e29；⓪frm=None创建转换；与 t12 同动作跨维度，note 互引"},
    )
    # t29 缴费
    m.add_trans(
        tid="t29", entity="E-BMJL", dimension="费用状态",
        frm="待缴费", to="已缴费", action="缴费", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录费用状态为待缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "待缴费")),
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
        ],
        expected_results=["费用状态变为已缴费"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e30；③序判frm先于to；§20.5.2.1多次付款不影响状态值，仅累计已收金额"},
    )
    # t30 缴费退款
    m.add_trans(
        tid="t30", entity="E-BMJL", dimension="费用状态",
        frm="已缴费", to="待缴费", action="缴费退款", role="财务人员",
        preconditions=[
            precond(text="报名记录费用状态为已缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "已缴费")),
            precond(text="退款金额不能大于当前缴费金额", ptype="constraint"),
        ],
        expected_results=["费用状态变为待缴费，退款金额累加，实际付款更新"],
        traits=["rollback", "data_constraint"], direction="backward", priority="P1",
        source_ref="20.10.2.3缴费单退款",
        note={"comment": "源自 e31；①'退款'→backward；rollback回退；data_constraint执行前置数据校验；§20.10.2.3退款后更新项目费用为实际付款金额"},
    )

    # ---- E-BMJL 报名记录 发票状态 ----
    # t31 报名（发票状态创建）
    m.add_trans(
        tid="t31", entity="E-BMJL", dimension="发票状态",
        frm=None, to="待开票", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["发票状态初始化为待开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e32；⓪frm=None创建转换；与 t12 同动作跨维度，note 互引"},
    )
    # t32 发票开具
    m.add_trans(
        tid="t32", entity="E-BMJL", dimension="发票状态",
        frm="待开票", to="已开票", action="发票开具", role="财务人员",
        preconditions=[
            precond(text="报名记录发票状态为待开票", ptype="state_ref",
                    ref=state_ref("E-BMJL", "发票状态", "待开票")),
            precond(text="费用状态为已缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "已缴费")),
        ],
        expected_results=["发票状态变为已开票"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e33；③序判frm先于to；§20.10.2.2支持多次分批上传，状态不变；跨主体门禁：费用状态.已缴费 落 state_ref"},
    )

    # ---- E-BMJL 报名记录 缴费通知状态 ----
    # t33 报名（缴费通知状态创建）
    m.add_trans(
        tid="t33", entity="E-BMJL", dimension="缴费通知状态",
        frm=None, to="未发送", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["缴费通知状态初始化为未发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "源自 e34；⓪frm=None创建转换；inferred：§19.3未列缴费通知单，由流程表'缴费通知单'列推导；与 t12 同动作跨维度"},
    )
    # t34 报名审核通过（缴费通知状态联动）
    m.add_trans(
        tid="t34", entity="E-BMJL", dimension="缴费通知状态",
        frm="未发送", to="已发送", action="报名审核通过", role="项目管理员",
        preconditions=[
            precond(text="报名记录缴费通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BMJL", "缴费通知状态", "未发送")),
        ],
        expected_results=["缴费通知状态变为已发送"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "源自 e35；③序判frm先于to；inferred：维度由流程表推导；与 t14 同动作跨维度，note 互引"},
    )

    # ---- E-BMJL 报名记录 报名记录样品状态 ----
    # t52 样品发放前创建转换（inferred：报名记录创建时样品状态初始化为待发样）
    m.add_trans(
        tid="t52", entity="E-BMJL", dimension="报名记录样品状态",
        frm=None, to="待发样", action="报名", role="能力验证参加者",
        preconditions=[],
        expected_results=["报名记录样品状态初始化为待发样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        note={"comment": "inferred创建转换：§19.3枚举'报名记录样品状态'初值'待发样'推导为报名时初始化；与 t12 同动作跨维度，note 互引"},
    )
    # t35 样品发放（报名记录样品状态：待发样→待收样）
    m.add_trans(
        tid="t35", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待发样", to="待收样", action="样品发放", role="项目管理员",
        preconditions=[
            precond(text="报名记录样品状态为待发样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待发样")),
            precond(text="样品已核查", ptype="event_ref"),
        ],
        expected_results=["报名记录样品状态变为待收样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3报名记录样品状态枚举",
        note={"comment": "源自 e36；③序判frm先于to；与 t09 同动作跨维度，note 互引"},
    )
    # t36 样品签收
    m.add_trans(
        tid="t36", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待收样", to="已收样", action="样品签收", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为待收样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待收样")),
        ],
        expected_results=["报名记录样品状态变为已收样"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3报名记录样品状态枚举",
        note={"comment": "源自 e37；③序判frm先于to"},
    )
    # t37 样品确认
    m.add_trans(
        tid="t37", entity="E-BMJL", dimension="报名记录样品状态",
        frm="已收样", to="已确认", action="样品确认", role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为已收样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "已收样")),
        ],
        expected_results=["报名记录样品状态变为已确认"],
        traits=[], direction="forward", priority="P0",
        source_ref="19.3报名记录样品状态枚举",
        note={"comment": "源自 e38；③序判frm先于to；终态：已确认"},
    )

    # ---- E-SYS 实验室信息 实验室状态 ----
    # t38 实验室新增/修改（创建转换：待审核）
    m.add_trans(
        tid="t38", entity="E-SYS", dimension="实验室状态",
        frm=None, to="待审核", action="实验室新增/修改", role="能力验证参加者",
        preconditions=[],
        expected_results=["实验室状态变为待审核"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.3.1实验室信息；20.4.1.2实验室审核",
        note={"comment": "源自 e39；⓪frm=None创建转换；机构新增/修改后需审核通过方可用于项目报名"},
    )
    # t39 实验室审核通过（分支：通过）
    m.add_trans(
        tid="t39", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="启用", action="实验室审核通过", role="系统管理员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=通过", ptype="constraint",
                    note={"comment": "分支值条件"}),
        ],
        expected_results=["实验室状态变为启用，生成数据快照记录"],
        traits=["audit", "branch"], direction="forward", priority="P0",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e40；③序判frm先于to；audit留痕；路径分歧：Step 2 value=通过 指向本条；通过时审核意见可为空"},
    )
    # t39b 实验室审核退回（分支：退回修改）
    m.add_trans(
        tid="t39b", entity="E-SYS", dimension="实验室状态",
        frm="待审核", to="退回修改", action="实验室审核退回", role="系统管理员",
        preconditions=[
            precond(text="实验室处于待审核状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "待审核")),
            precond(text="审核结果=退回修改", ptype="constraint",
                    note={"comment": "分支值条件"}),
            precond(text="退回修改必须填写审核意见", ptype="constraint"),
        ],
        expected_results=["实验室状态变为退回修改，必须填写审核意见"],
        traits=["audit", "rollback", "branch", "data_constraint"], direction="backward", priority="P1",
        source_ref="20.4.1.2实验室审核",
        note={"branch_dimension": "审核结果", "comment": "源自 e41；①'退回'→backward；audit留痕；rollback回退；data_constraint执行前置数据校验；路径分歧：Step 2 value=退回修改 指向本条"},
    )
    # t39c 实验室退回修改后重新提交（退回修改→待审核，inferred：机构修改后重新提交）
    m.add_trans(
        tid="t39c", entity="E-SYS", dimension="实验室状态",
        frm="退回修改", to="待审核", action="实验室修改", role="能力验证参加者",
        preconditions=[
            precond(text="实验室处于退回修改状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "退回修改")),
        ],
        expected_results=["实验室状态变为待审核，等待重新审核"],
        traits=[], direction="forward", priority="P1",
        source_ref="20.4.1.3实验室修改；20.4.1.2实验室审核",
        note={"comment": "inferred：退回修改后机构修改实验室信息重新提交；与 t42 同动作不同frm；序判③frm先于to；图完整性补全"},
    )
    # t40 实验室停用
    m.add_trans(
        tid="t40", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="停用", action="实验室停用", role="系统管理员",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变为停用"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e42；①'停用'→lateral"},
    )
    # t41 实验室启用
    m.add_trans(
        tid="t41", entity="E-SYS", dimension="实验室状态",
        frm="停用", to="启用", action="实验室启用", role="系统管理员",
        preconditions=[
            precond(text="实验室处于停用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "停用")),
        ],
        expected_results=["实验室状态变为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.1.1实验室列表与查询",
        note={"comment": "源自 e43；①'启用'→resume；从侧挂状态恢复"},
    )
    # t42 实验室修改（启用→待审核）
    m.add_trans(
        tid="t42", entity="E-SYS", dimension="实验室状态",
        frm="启用", to="待审核", action="实验室修改", role="能力验证参加者",
        preconditions=[
            precond(text="实验室处于启用状态", ptype="state_ref",
                    ref=state_ref("E-SYS", "实验室状态", "启用")),
        ],
        expected_results=["实验室状态变为待审核"],
        traits=[], direction="backward", priority="P1",
        source_ref="20.4.1.3实验室修改；20.3.1实验室信息",
        note={"comment": "源自 e44；序判④，语义backward（启用→待审核为回退）；启用状态修改后回到待审核"},
    )

    # ---- E-BZK 标准库 标准库状态 ----
    # t43 新增标准库（创建转换：启用）
    m.add_trans(
        tid="t43", entity="E-BZK", dimension="标准库状态",
        frm=None, to="启用", action="新增标准库", role="系统管理员",
        preconditions=[],
        expected_results=["标准库创建成功，状态为启用"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.4.2.2新增标准库",
        note={"comment": "源自 e45；⓪frm=None创建转换；默认启用"},
    )
    # t44 停用标准库
    m.add_trans(
        tid="t44", entity="E-BZK", dimension="标准库状态",
        frm="启用", to="停用", action="停用标准库", role="系统管理员",
        preconditions=[
            precond(text="标准库处于启用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "启用")),
        ],
        expected_results=["标准库状态变为停用，项目创建等环节不可被选择"],
        traits=[], direction="lateral", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e46；①'停用'→lateral；停用后项目创建等环节不可被选择（b08）"},
    )
    # t45 启用标准库
    m.add_trans(
        tid="t45", entity="E-BZK", dimension="标准库状态",
        frm="停用", to="启用", action="启用标准库", role="系统管理员",
        preconditions=[
            precond(text="标准库处于停用状态", ptype="state_ref",
                    ref=state_ref("E-BZK", "标准库状态", "停用")),
        ],
        expected_results=["标准库状态变为启用"],
        traits=[], direction="resume", priority="P1",
        source_ref="20.4.2.5停用/启用标准库",
        note={"comment": "源自 e47；①'启用'→resume；从侧挂状态恢复"},
    )

    # ---- E-PJ 评价 评价状态 ----
    # t46 评价组长完善（创建转换：待评价）
    m.add_trans(
        tid="t46", entity="E-PJ", dimension="评价状态",
        frm=None, to="待评价", action="评价组长完善", role="评价组长",
        preconditions=[
            precond(text="项目已创建", ptype="event_ref"),
        ],
        expected_results=["评价状态初始化为待评价，评价组长完善测试项目及评价细则"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.1测试项目、评价细则完善",
        note={"comment": "源自 e48；⓪frm=None创建转换；inferred：评价状态由§20.7推导"},
    )
    # t47 评价人员评价
    m.add_trans(
        tid="t47", entity="E-PJ", dimension="评价状态",
        frm="待评价", to="评价中", action="评价人员评价", role="评价人员",
        preconditions=[
            precond(text="评价处于待评价状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "待评价")),
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价组长已完善测试项目及评价细则", ptype="event_ref"),
        ],
        expected_results=["评价状态变为评价中，评价人员只能修改自己的评价结果"],
        traits=[], direction="forward", priority="P0",
        source_ref="20.7.1.2协同评价",
        note={"comment": "源自 e49；③序判frm先于to；跨主体门禁：报名记录.结果已提交 落 state_ref；§9落盘示例同型"},
    )
    # t48 评价结果确认
    m.add_trans(
        tid="t48", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="评价完成", action="评价结果确认", role="评价组长",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变为评价完成，当前结果提交为最终评价结果，项目评价状态关闭"],
        traits=["audit"], direction="forward", priority="P0",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e50；③序判frm先于to；audit留痕；终态：评价完成"},
    )
    # t49 评价退回修改
    m.add_trans(
        tid="t49", entity="E-PJ", dimension="评价状态",
        frm="评价中", to="待评价", action="评价退回修改", role="评价组长",
        preconditions=[
            precond(text="评价处于评价中状态", ptype="state_ref",
                    ref=state_ref("E-PJ", "评价状态", "评价中")),
        ],
        expected_results=["评价状态变为待评价，当前评价结果保存为历史，开启下一轮评价"],
        traits=["rollback"], direction="backward", priority="P1",
        source_ref="20.7.1.3评价确认",
        note={"comment": "源自 e51；①'退回修改'→backward；rollback回退；开启下一轮评价"},
    )

    # ===== Step 3.4 因果 =====

    # 因果1：报名记录创建 → 项目状态变化（同时发生）
    m.add_causal(
        frm="E-XM", to="E-BMJL",
        desc="项目发布后参加者可报名，报名记录创建同时项目进入报名中阶段",
        trigger="项目状态变为报名中触发参加者报名流程",
        trigger_source="desc",
        evidence_transitions=["t02", "t12"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：项目变直接致报名记录可被创建；Q2未表达；显式句式（项目发布后参加者可报名）"},
    )

    # 因果2：报名审核通过 → 缴费通知状态变为已发送
    m.add_causal(
        frm="E-BMJL", to="E-BMJL",
        desc="报名审核通过后系统自动发送缴费通知单，缴费通知状态变为已发送",
        trigger="报名审核通过后缴费通知自动发送",
        trigger_source="expected_results",
        evidence_transitions=["t14", "t34"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：报名审核通过直接致缴费通知状态变；Q2未表达；expected_results含对缴费通知状态影响"},
    )

    # 因果3：能力验证预通知 → 通知状态变为已发送（同时）
    m.add_causal(
        frm="E-BMJL", to="E-BMJL",
        desc="能力验证预通知动作同时改变报名记录状态（→结果待提交）和通知状态（→已发送）",
        trigger="能力验证预通知动作跨维度同步",
        trigger_source="action",
        evidence_transitions=["t16", "t21"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：同一动作同时改变两维度；Q2未表达；preconditions含跨维度state_ref"},
    )

    # 因果4：评价完成 → 编制结果报告
    m.add_causal(
        frm="E-PJ", to="E-BMJL",
        desc="评价结果确认完成后，策划人员编制结果报告，报名记录状态变为报告/证书审核中",
        trigger="评价完成后编制结果报告",
        trigger_source="desc",
        evidence_transitions=["t48", "t19"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：评价完成直接致结果报告编制启动；Q2未表达；显式句式"},
    )

    # 因果5：报告批准 → 发放结果报告和证书
    m.add_causal(
        frm="E-BMJL", to="E-XM",
        desc="结果通知单授权签字人批准及证书实验室负责人批准后，项目管理员发放结果报告和证书，项目状态变为已结束",
        trigger="报告/证书批准后发放",
        trigger_source="desc",
        evidence_transitions=["t27", "t20", "t06"],
        rollback_propagation=False, confidence="high",
        note={"comment": "Q1通过：批准后直接发放；Q2未表达；显式句式"},
    )

    # ===== Step 4 约束 =====

    # ---- invalid：无文档明确"不允许/不可以从X到Y"表述，无 invalid ----

    # ---- XC 跨实体约束 ----

    # x01 镜像：报名门禁 - 项目状态必须为报名中（镜像自 t12 的 state_ref）
    m.add_xc(
        xid="x01", source_entity="E-XM", source_transition="t02",
        source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名记录创建需项目处于报名中状态",
        desc="项目状态为报名中时参加者方可创建报名记录",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        target_transition="t12",
        xc_source="镜像",
    )

    # x02 镜像：报名审核通过门禁 - 实验室信息必须为启用（镜像自 t14 的 state_ref）
    m.add_xc(
        xid="x02", source_entity="E-SYS", source_transition="t39",
        source_state="启用",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="报名审核通过需实验室信息处于启用状态",
        desc="实验室信息处于启用状态时报名记录方可审核通过",
        source_ref="20.3.1实验室信息；20.4.1.2实验室审核",
        target_transition="t14",
        xc_source="镜像",
    )

    # x03 镜像：能力验证预通知门禁 - 报名记录必须为报名成功（镜像自 t16 的 state_ref）
    m.add_xc(
        xid="x03", source_entity="E-BMJL", source_transition="t14",
        source_state="报名成功",
        target_entity="E-BMJL", target_dimension="通知状态",
        target_condition="能力验证预通知需报名记录处于报名成功状态",
        desc="报名记录处于报名成功状态时项目管理员方可发送能力验证预通知",
        source_ref="19.1实施阶段；19.2实施阶段",
        target_transition="t21",
        xc_source="镜像",
    )

    # x04 镜像：评价人员评价门禁 - 报名记录必须为结果已提交（镜像自 t47 的 state_ref）
    m.add_xc(
        xid="x04", source_entity="E-BMJL", source_transition="t17",
        source_state="结果已提交",
        target_entity="E-PJ", target_dimension="评价状态",
        target_condition="评价人员评价需报名记录处于结果已提交状态",
        desc="报名记录处于结果已提交状态时评价人员方可启动评价",
        source_ref="20.7.1.2协同评价",
        target_transition="t47",
        xc_source="镜像",
    )

    # x05 镜像：发票开具门禁 - 费用状态必须为已缴费（镜像自 t32 的 state_ref）
    m.add_xc(
        xid="x05", source_entity="E-BMJL", source_transition="t29",
        source_state="已缴费",
        target_entity="E-BMJL", target_dimension="发票状态",
        target_condition="发票开具需费用状态为已缴费",
        desc="费用状态为已缴费时财务人员方可开具发票",
        source_ref="19.1实施阶段；19.2项目准备阶段",
        target_transition="t32",
        xc_source="镜像",
    )

    # x06 联动：项目结束联动报名记录发布（联动自 t06）
    m.add_xc(
        xid="x06", source_entity="E-XM", source_transition="t06",
        source_state="已结束",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="项目结束时报名记录应已发布",
        desc="项目状态变为已结束联动报名记录状态变为报告/证书已发布",
        source_ref="19.1报告编制和结果通知",
        target_transition="t20",
        xc_source="联动",
    )

    # x07 4.5判：实验室审核通过约束 - 实验室需审核通过方可用于项目报名
    m.add_xc(
        xid="x07", source_entity="E-SYS", source_transition="t39",
        source_state="启用",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_condition="实验室信息需审核通过方可用于项目报名",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名（b07承载）",
        source_ref="20.3.1实验室信息",
        target_transition=None,
        xc_source="4.5判",
    )

    # ---- BR 业务规则 ----

    # 通知公告相关
    m.add_br(
        bid="b01", category="display",
        desc="15天内发布的通知在内容前标注'new'标识，超过15天后此标识自动隐藏",
        entities_involved=["E-TZGG"], source_ref="20.2.1通知公告",
        signal_type="display",
        note={"comment": "signal_type命中'display'；category判信息展示；15天阈值规则"},
    )

    m.add_br(
        bid="b02", category="usability",
        desc="首页能力验证增加'待提交结果'统计内容，测量审核增加'待审核'统计内容",
        entities_involved=["E-DAI"], source_ref="20.2.3待办事项",
        signal_type="usability",
        note={"comment": "signal_type命中'增加'（应提供/应支持/可）；category判易用功能"},
    )

    # 实验室信息相关
    m.add_br(
        bid="b03", category="validation",
        desc="实验室查询状态选项包括：待审核、启用、停用、已退回",
        entities_involved=["E-SYS"], source_ref="20.4.1.1实验室列表与查询",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'field_constraint'（取值范围）；category判有效性校验；'已退回'与状态值'退回修改'为查询别名"},
    )

    m.add_br(
        bid="b04", category="validation",
        desc="实验室审核结果为通过时审核意见可以为空；审核结果为退回修改时必须填写审核意见",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"branch_dimension": "审核结果", "comment": "signal_type命中'必须'；category判有效性校验；分支承载：审核结果维度"},
    )

    m.add_br(
        bid="b05", category="validation",
        desc="实验室审核通过时为当前数据生成快照记录",
        entities_involved=["E-SYS"], source_ref="20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"comment": "signal_type命中'生成'（必须衍生）；category判有效性校验"},
    )

    m.add_br(
        bid="b06", category="authorization",
        desc="实验室信息修改权限：能力验证参加者可新增/修改自己的实验室信息，系统管理员审核/停用/启用",
        entities_involved=["E-SYS"], source_ref="20.3.1实验室信息；20.4.1.2实验室审核",
        signal_type="restrictive",
        note={"role": "能力验证参加者；系统管理员", "comment": "signal_type命中'可'（必须/仅当/禁止/不能/不可）；category判访问控制；authorization类角色放note.role"},
    )

    m.add_br(
        bid="b07", category="authorization",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-SYS", "E-BMJL"], source_ref="20.3.1实验室信息",
        signal_type="restrictive",
        constrained_entity="E-SYS",
        note={"comment": "signal_type命中'后方可'（必须/不得/仅当/禁止/不能/不可）；category判访问控制；constrained_entity为被门禁实体E-SYS"},
    )

    # 标准库相关
    m.add_br(
        bid="b08", category="validation",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"], source_ref="20.4.2.5停用/启用标准库",
        signal_type="restrictive",
        constrained_entity="E-BZK",
        note={"comment": "signal_type命中'不可'；category判有效性校验；constrained_entity为被门禁实体E-BZK"},
    )

    m.add_br(
        bid="b09", category="validation",
        desc="含有子项的测试项记录不允许删除",
        entities_involved=["E-CSX"], source_ref="20.4.2.10删除测试项；20.4.3.4删除测试项",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不允许'；category判有效性校验"},
    )

    # 信息发送记录
    m.add_br(
        bid="b10", category="authorization",
        desc="只有系统管理员和项目管理员可以查看信息发送记录",
        entities_involved=["E-XXJL"], source_ref="20.4.4.1信息发送记录",
        signal_type="restrictive",
        note={"role": "系统管理员；项目管理员", "comment": "signal_type命中'只有'（必须/不得/仅当/禁止/不能/不可）；category判访问控制；authorization类"},
    )

    # 项目管理相关
    m.add_br(
        bid="b11", category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'；category判有效性校验"},
    )

    m.add_br(
        bid="b12", category="usability",
        desc="未结束的项目可以进行消息发送",
        entities_involved=["E-XM"], source_ref="20.5.1.4优化消息发送功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'可以'（应提供/应支持/可等量化）；category判易用功能"},
    )

    # 已报名项目相关
    m.add_br(
        bid="b13", category="validation",
        desc="已报名项目多次付款不对付款金额进行校验限制",
        entities_involved=["E-BMJL"], source_ref="20.5.2.1已报名项目增加多次付款功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不对...进行校验限制'；category判有效性校验；§20.5.2.1多次付款"},
    )

    # 证书到期提醒（系统行为BR：notification/timing）
    m.add_br(
        bid="b14", category="notification",
        desc="系统在每天上午9点对系统中的证书信息进行查询，距到期时间等于30天时通过邮件方式对用户进行提醒，并抄送项目管理员；提醒标题：证书到期提醒；提醒内容：您证书编号为xxxx的证书将于2025-01-01到期，请知悉",
        entities_involved=["E-FP"], source_ref="20.5.2.3增加证书到期前30天提醒功能；20.6.2.3增加证书到期前30天提醒功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'每天上午9点'（X日内/X次以内类量化措辞）；category判通知触发；无状态落点，不入台账/operations"},
    )

    # 操作节点短信通知（系统行为BR：notification）
    m.add_br(
        bid="b15", category="notification",
        desc="管理人员对用户报名项目操作后使用短信方式对用户进行通知，包括：报名审核通过/退回修改、发样通知、测试结果审核通过/退回、结果通知单发布",
        entities_involved=["E-BMJL"], source_ref="20.5.3.2操作节点增加用户短信通知；20.6.3.2操作节点增加用户短信通知",
        signal_type="restrictive",
        note={"comment": "signal_type命中'后使用'（必须/不得/仅当/禁止/不能/不可及量化措辞）；category判通知触发；短信通知规则"},
    )

    # 评价相关
    m.add_br(
        bid="b16", category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-PJ"], source_ref="20.7.1.2协同评价",
        signal_type="restrictive",
        note={"role": "评价人员", "comment": "signal_type命中'只能'（必须/不得/仅当/禁止/不能/不可）；category判访问控制；authorization类"},
    )

    m.add_br(
        bid="b17", category="validation",
        desc="新建项目时第一个被选择的评价人员默认做为评价组长",
        entities_involved=["E-PJ"], source_ref="20.7.1项目列表",
        signal_type="restrictive",
        note={"comment": "signal_type命中'默认'（默认值）；category判有效性校验"},
    )

    m.add_br(
        bid="b18", category="validation",
        desc="评价组长在评价结果确认页面填写及格分，及格分录入后跟随其他结果一起记录到系统中",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'field_constraint'（必填）；category判有效性校验"},
    )

    m.add_br(
        bid="b19", category="validation",
        desc="统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'field_constraint'（取值范围）；category判有效性校验"},
    )

    m.add_br(
        bid="b20", category="validation",
        desc="评价确认退回修改后将当前评价结果保存为历史结果，并开启下一轮评价",
        entities_involved=["E-PJ"], source_ref="20.7.1.3评价确认",
        signal_type="restrictive",
        note={"branch_dimension": "评分方式", "comment": "signal_type命中'后'（必须/不得/仅当/禁止/不能/不可及量化措辞）；category判有效性校验；分支承载：评分方式维度（影响得分计算与退回后重评逻辑）"},
    )

    # 业务审核相关
    m.add_br(
        bid="b21", category="usability",
        desc="测量审核结果通知单审批流程合并为一个流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序",
        entities_involved=["E-BMJL"], source_ref="20.9.1.1测量审核结果通知单审核流程优化",
        signal_type="restrictive",
        note={"branch_dimension": "业务类型", "comment": "signal_type命中'设置为'（必须/不得/仅当/禁止/不能/不可及量化措辞）；category判易用功能；流程重构；分支承载：业务类型维度（测量审核特有）"},
    )

    m.add_br(
        bid="b22", category="notification",
        desc="用户通过表单或审核一个已存在的任务，生成一个新的审核任务时，系统发送短信通知相关负责人；短信内容：您有一个新的xxx审核任务，请及时处理",
        entities_involved=["E-BMJL"], source_ref="20.9.1.3增加任务提醒",
        signal_type="restrictive",
        note={"comment": "signal_type命中'生成'（必须/不得/仅当/禁止/不能/不可及量化措辞）；category判通知触发；无状态落点"},
    )

    m.add_br(
        bid="b23", category="validation",
        desc="批量审核时系统会根据任务节点的类型及内容判断当前节点是否可以被批量处理",
        entities_involved=["E-BMJL"], source_ref="20.9.1.4任务批量处理",
        signal_type="restrictive",
        note={"comment": "signal_type命中'判断'（必须/不得/仅当/禁止/不能/不可及量化措辞）；category判有效性校验"},
    )

    m.add_br(
        bid="b24", category="usability",
        desc="系统预设若干自定义流程（4个以内），用于用户选择并提交文档审核的自定义流程，并支持相应的签章",
        entities_involved=["E-BMJL"], source_ref="20.9.1.6增加自定义流程",
        signal_type="restrictive",
        note={"comment": "signal_type命中'4个以内'（X日内/X次以内类量化措辞）；category判易用功能"},
    )

    # 财务管理相关
    m.add_br(
        bid="b25", category="validation",
        desc="缴费单退款金额不能大于当前缴费金额，退款金额使用红色字体且大于0时显示",
        entities_involved=["E-JF"], source_ref="20.10.2.3缴费单退款",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'；category判有效性校验；含显示规则"},
    )

    m.add_br(
        bid="b26", category="computation",
        desc="退款后更新项目费用为实际付款金额，实际付款=付款金额-退款金额；多次退款金额做累加处理",
        entities_involved=["E-JF", "E-BMJL"], source_ref="20.10.2.3缴费单退款",
        signal_type="restrictive",
        constrained_entity="E-JF",
        note={"comment": "signal_type命中'累计'/'按X计算'（含'累计'措辞）；category判计算衍生；constrained_entity为被计算实体E-JF"},
    )

    m.add_br(
        bid="b27", category="validation",
        desc="发票上传支持多次分批上传，最后一次开票时间记录为开票时间",
        entities_involved=["E-FP"], source_ref="20.10.2.2修改发票上传功能",
        signal_type="restrictive",
        note={"comment": "signal_type命中'最后一次'（量化措辞）；category判有效性校验"},
    )

    # 缴费信息管理时间快速录入
    m.add_br(
        bid="b28", category="usability",
        desc="缴费信息查询时间参数支持本月、本季、本年单选快速录入，并支持自定义时间范围",
        entities_involved=["E-JF"], source_ref="20.10.1.1缴费信息查询与管理",
        signal_type="usability",
        note={"comment": "signal_type命中'支持'（应提供/应支持/可）；category判易用功能"},
    )

    # 其他
    m.add_br(
        bid="b29", category="usability",
        desc="对关键操作进行留痕处理，系统自动记录操作者身份、时间戳、操作细节及结果，生成不可篡改的审计日志",
        entities_involved=["E-XM", "E-BMJL", "E-SYS", "E-BZK", "E-PJ"], source_ref="20.11.1.2安全性相关内容优化",
        signal_type="usability",
        note={"comment": "signal_type命中'应'（应提供/应支持/可）；category判易用功能；多实体审计日志"},
    )

    m.add_br(
        bid="b30", category="display",
        desc="统一系统显示风格，对不符合当前风格的页面进行调整，消除现有风格差异",
        entities_involved=["E-XM"], source_ref="20.11.1.3系统UI风格优化",
        signal_type="display",
        note={"comment": "signal_type命中'display'（显示/展示）；category判信息展示"},
    )

    # 删除操作警示框
    m.add_br(
        bid="b31", category="usability",
        desc="删除操作时系统提示警示框'您确认删除记录吗？操作不可恢复！'，用户点击确认后才执行删除",
        entities_involved=["E-SYS", "E-BZK", "E-CSX", "E-ZYL"], source_ref="3.6.6完备提示信息",
        signal_type="usability",
        note={"comment": "signal_type命中'应'（应提供/应支持/可）；category判易用功能；通用删除确认"},
    )

    # 性能要求
    m.add_br(
        bid="b32", category="usability",
        desc="平台应支持至少300个同时在线用户数；并发100时每个页面响应时间不超过5秒；单次报名操作成功率应达到95%以上",
        entities_involved=["E-XM"], source_ref="3.4性能要求；21.3性能要求",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不超过'/'达到95%以上'（X日内/X次以内类量化措辞）；category判易用功能；性能指标"},
    )

    # 兼容性
    m.add_br(
        bid="b33", category="validation",
        desc="Web系统兼容win7、win10及以上；浏览器兼容Edge、Chrome、火狐等主流浏览器",
        entities_involved=["E-XM"], source_ref="3.5兼容性要求；21.5兼容性要求",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'field_constraint'（取值范围）；category判有效性校验；兼容性约束"},
    )

    # 项目批量处理门禁
    m.add_br(
        bid="b34", category="validation",
        desc="只有已上传对应文件且未提交审核的记录才可以被选定进行批量提交审核",
        entities_involved=["E-BMJL"], source_ref="20.5.1.3项目批量操作",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只有'（必须/不得/仅当/禁止/不能/不可）；category判有效性校验"},
    )

    # 数据备份与恢复
    m.add_br(
        bid="b35", category="usability",
        desc="系统应提供数据备份与恢复功能",
        entities_involved=["E-XM"], source_ref="3.7集成部署要求",
        signal_type="usability",
        note={"comment": "signal_type命中'应提供'（应提供/应支持/可）；category判易用功能"},
    )

    m.add_br(
        bid="b36", category="validation",
        desc="能力验证项目样品可能需要还样或无需还样，测量审核项目样品无须归还",
        entities_involved=["E-YP"], source_ref="19.1实施阶段；19.2实施阶段",
        signal_type="restrictive",
        note={"branch_dimension": "样品归还方式", "comment": "signal_type命中'无须'（必须/不得/仅当/禁止/不能/不可）；category判有效性校验；分支承载：样品归还方式维度"},
    )

    return m
