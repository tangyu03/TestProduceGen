#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1-6: 结构化分析流水线 - 构建完整 JSON 输出
源文档: 网数中心能力验证服务平台升级维护项目-歧义修正.docx
"""
import json
from datetime import datetime, timezone, timedelta

# ============================================================
# 辅助：note 默认
# ============================================================
def note(inferred=False, comment="", conflict="", branch_dimension=""):
    return {
        "inferred": inferred,
        "comment": comment,
        "conflict": conflict,
        "branch_dimension": branch_dimension
    }

# ============================================================
# _meta
# ============================================================
meta = {
    "version": "18.1",
    "generated_at": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "source": "网数中心能力验证服务平台升级维护项目-歧义修正.docx",
    "document_scope": "网数中心能力验证服务平台升级维护项目需求分析与设计说明书，覆盖项目背景/目标/要求、用户角色、系统流程(能力验证/测量审核 提供者与参加者)、系统功能需求(首页/基本信息/系统管理/能力验证/测量审核/项目评价/统计分析/业务审核/财务管理/其他)、非功能性需求",
    "has_critical_ambiguity": False,
    "consistency_check": "passed",
    "branch_dimensions": []  # 填充于 Step 3
}

# ============================================================
# Step 1: 实体识别与内部结构建模
# ============================================================

entities = []

# ---------- E-PROJ 能力验证项目 ----------
entities.append({
    "id": "E-PROJ",
    "name": "能力验证项目",
    "desc": "能力验证或测量审核项目的主体业务对象，承载项目立项、方案设计、实施、评价统计、报告编制与归档等全生命周期。项目类型分为能力验证与测量审核两种(分支维度)。项目下挂样品、报名记录、评价、归档等子对象。",
    "type": "core",
    "tags": ["approvable", "multi-state", "configurable", "collaborative"],
    "attributes": [
        {"name": "项目编号", "desc": "项目唯一标识，文本输入框", "is_config": False},
        {"name": "项目名称", "desc": "项目名称，文本输入框，模糊匹配查询字段", "is_config": False},
        {"name": "产品类型", "desc": "下拉框，精确匹配；选项为系统内所有的产品信息", "is_config": False},
        {"name": "项目类型", "desc": "下拉框，精确匹配；选项包括：能力验证、测量审核。创建时确定，影响后续流程与消息发送规则(分支维度)", "is_config": True},
        {"name": "所属年度", "desc": "项目所属年度", "is_config": False},
        {"name": "子领域", "desc": "项目所属子领域，关联子领域管理", "is_config": False},
        {"name": "项目费用", "desc": "项目费用金额，数值，作为报名缴费汇款金额默认值", "is_config": False},
        {"name": "依据标准", "desc": "项目依据标准信息，来源于标准库", "is_config": False},
        {"name": "技术主管", "desc": "项目人员信息，下拉框；备选人有且仅有一个时默认填充为备选值", "is_config": False},
        {"name": "实验室负责人", "desc": "项目人员信息，下拉框；备选人有且仅有一个时默认填充为备选值", "is_config": False},
        {"name": "授权签字人", "desc": "项目人员信息，下拉框；备选人有且仅有一个时默认填充为备选值", "is_config": False},
        {"name": "监督员", "desc": "项目人员信息区域最后一行新增字段，下拉框，可以为空；导出项目通知书时填充到对应位置", "is_config": False},
        {"name": "评价人员", "desc": "新建项目时项目管理员选择评价人员；第一个被选择的评价人员默认作为评价组长", "is_config": False},
        {"name": "项目管理员", "desc": "项目管理员", "is_config": False},
        {"name": "财务备注", "desc": "项目列表新增字段，管理人员可以修改备注内容", "is_config": False},
        {"name": "项目状态", "desc": "项目状态字段，枚举：待开始、报名中、进行中、报告审核中、已结束", "is_config": False}
    ],
    "state_dimensions": [
        {
            "dimension_name": "项目状态",
            "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
            "initial": "待开始",
            "terminal": ["已结束"],
            "note": note(False, "来源于项目状态分析章节明确枚举", "", "")
        },
        {
            "dimension_name": "样品状态",
            "states": ["待核查", "已核查"],
            "initial": "待核查",
            "terminal": ["已核查"],
            "note": note(False, "验证项目状态-样品状态枚举", "", "")
        }
    ],
    "operations": ["新增", "修改", "删除", "查看", "文件整理", "代码导入", "批量处理", "消息发送", "导出"]
})

# ---------- E-REG 报名记录 ----------
entities.append({
    "id": "E-REG",
    "name": "报名记录",
    "desc": "参加者报名某项目的业务记录对象，承载报名审核、样品收发、结果提交、报告发布、缴费与发票等独立状态维度。是连接项目与参加者业务行为的核心载体，具有多条独立演进的状态维度。",
    "type": "core",
    "tags": ["approvable", "multi-state", "expirable", "collaborative"],
    "attributes": [
        {"name": "报名编号", "desc": "报名记录唯一标识，文本，模糊匹配查询字段；上传付款单/发票时只读展示", "is_config": False},
        {"name": "项目编号", "desc": "关联项目编号，只读", "is_config": False},
        {"name": "项目名称", "desc": "关联项目名称，只读", "is_config": False},
        {"name": "实验室", "desc": "报名实验室，关联实验室信息；机构代码导入后含机构代码字段", "is_config": False},
        {"name": "统一社会信用代码", "desc": "实验室统一社会信用代码", "is_config": False},
        {"name": "报名时间", "desc": "报名时间", "is_config": False},
        {"name": "行政区划", "desc": "实验室所在行政区划", "is_config": False},
        {"name": "机构代码", "desc": "报名机构的三方代码，由项目管理员通过代码导入功能批量导入", "is_config": False},
        {"name": "实施状态", "desc": "报名实施状态(报名记录状态字段)", "is_config": False},
        {"name": "付款状态", "desc": "费用状态字段，枚举：待缴费、已缴费", "is_config": False},
        {"name": "评价得分", "desc": "项目评价完成后回填", "is_config": False},
        {"name": "评价结果", "desc": "项目评价完成后回填", "is_config": False},
        {"name": "证书编号", "desc": "合格证书编号，评价合格后生成", "is_config": False},
        {"name": "结果通知单", "desc": "结果通知单文件，由项目管理员上传后批量提交审核", "is_config": False},
        {"name": "证书", "desc": "能力验证合格证书文件，由项目管理员上传后批量提交审核", "is_config": False}
    ],
    "state_dimensions": [
        {
            "dimension_name": "报名记录状态",
            "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告审核中", "报告已发布", "已撤销"],
            "initial": "报名待审核",
            "terminal": ["报告已发布", "已撤销"],
            "note": note(False, "来源于项目状态分析章节 报名记录状态-报名记录状态枚举", "", "")
        },
        {
            "dimension_name": "报名记录样品状态",
            "states": ["待发样", "待收样", "已收样", "已确认"],
            "initial": "待发样",
            "terminal": ["已确认"],
            "note": note(False, "来源于项目状态分析章节 报名记录状态-报名记录样品状态枚举", "", "")
        },
        {
            "dimension_name": "费用状态",
            "states": ["待缴费", "已缴费"],
            "initial": "待缴费",
            "terminal": ["已缴费"],
            "note": note(False, "来源于项目状态分析章节 报名记录状态-费用状态枚举", "", "")
        },
        {
            "dimension_name": "发票状态",
            "states": ["待开票", "已开票"],
            "initial": "待开票",
            "terminal": ["已开票"],
            "note": note(False, "来源于项目状态分析章节 报名记录状态-发票状态枚举", "", "")
        },
        {
            "dimension_name": "通知状态",
            "states": ["未发送", "待确认", "待审核", "退回", "已审核", "已批准"],
            "initial": "未发送",
            "terminal": ["已批准"],
            "note": note(False, "来源于项目状态分析章节 报名记录状态-通知状态枚举", "", "")
        }
    ],
    "operations": ["报名", "审核", "退回", "发样", "收样", "结果提交", "结果审核", "上传付款单", "上传发票", "撤销", "批量提交审核", "查看详情"]
})

# ---------- E-LAB 实验室 ----------
entities.append({
    "id": "E-LAB",
    "name": "实验室",
    "desc": "能力验证参加者(机构)维护的实验室信息对象，机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名。本次升级新增状态字段及审核流程。",
    "type": "core",
    "tags": ["approvable", "multi-state", "configurable"],
    "attributes": [
        {"name": "实验室编号", "desc": "文本输入框，模糊查询", "is_config": False},
        {"name": "实验室名称", "desc": "实验室名称，文本输入框，模糊查询", "is_config": False},
        {"name": "统一社会信用代码", "desc": "统一社会信用代码", "is_config": False},
        {"name": "法人名称", "desc": "法人名称", "is_config": False},
        {"name": "企业类型", "desc": "企业类型", "is_config": False},
        {"name": "企业规模", "desc": "企业规模", "is_config": False},
        {"name": "CNAS", "desc": "已获CNAS认可及CNAS证书号", "is_config": False},
        {"name": "CMA", "desc": "已获CMA认可及CMA证书编号", "is_config": False},
        {"name": "邮箱", "desc": "邮箱", "is_config": False},
        {"name": "座机号码", "desc": "座机号码", "is_config": False},
        {"name": "地址", "desc": "行政区域+详细地址", "is_config": False},
        {"name": "联系人", "desc": "联系人", "is_config": False},
        {"name": "联系电话", "desc": "联系电话", "is_config": False},
        {"name": "默认实验室", "desc": "标识是否为机构默认实验室", "is_config": False},
        {"name": "证明文件", "desc": "请上传营业执照或其他证书材料，链接形式可下载", "is_config": False},
        {"name": "状态", "desc": "状态字段，枚举：待审核、启用、停用、退回修改", "is_config": False}
    ],
    "state_dimensions": [
        {
            "dimension_name": "审核状态",
            "states": ["待审核", "启用", "停用", "退回修改"],
            "initial": "待审核",
            "terminal": [],
            "note": note(False, "来源于基本信息-实验室信息章节明确状态字段", "", "")
        }
    ],
    "operations": ["新增", "修改", "删除", "审核", "停用", "启用", "查询"]
})

# ---------- E-STD 标准库 ----------
entities.append({
    "id": "E-STD",
    "name": "标准库",
    "desc": "系统基础数据对象，代表一个完整的可被引用的标准集合(如GB/T 12345-2020电子产品安全标准)。通过分层级方式维护其下测试项与子测试项，为系统中各类实验和项目提供数据基础。停用的标准库在项目创建等环节不可被选择。",
    "type": "managed",
    "tags": ["configurable", "multi-state"],
    "attributes": [
        {"name": "标准库编号", "desc": "文本输入框，必填，模糊查询", "is_config": False},
        {"name": "标准库名称", "desc": "文本输入框，必填，模糊查询", "is_config": False},
        {"name": "状态", "desc": "单选框，包含启用、停用两个状态，必填；精确匹配查询", "is_config": False},
        {"name": "描述", "desc": "文本输入框，选填", "is_config": False},
        {"name": "创建时间", "desc": "记录创建时间", "is_config": False}
    ],
    "state_dimensions": [
        {
            "dimension_name": "启用状态",
            "states": ["启用", "停用"],
            "initial": "启用",
            "terminal": [],
            "note": note(False, "来源于标准库管理-新增标准库章节", "", "")
        }
    ],
    "operations": ["新增", "修改", "删除", "启用", "停用", "管理测试项", "查询"]
})

# ---------- E-TESTITEM 测试项(标准库测试项) ----------
entities.append({
    "id": "E-TESTITEM",
    "name": "测试项",
    "desc": "标准库下的测试项对象，由编号和名称组成，测试项下可以有子测试项(自引用层级结构)。本次升级子领域下测试项改为从标准库选择方式引入。",
    "type": "managed",
    "tags": ["configurable"],
    "attributes": [
        {"name": "标号", "desc": "文本输入框，必填", "is_config": False},
        {"name": "名称", "desc": "文本输入框，必填", "is_config": False}
    ],
    "state_dimensions": [],
    "operations": ["新增", "新增子项", "修改", "删除"]
})

# ---------- E-CATE 子领域 ----------
entities.append({
    "id": "E-CATE",
    "name": "子领域",
    "desc": "项目分类管理的基础数据对象。本次升级将子领域下测试项的管理方式由表单方式变更为选择方式，选择数据来源于标准库。子领域支持常用测试项组合的另存与复用。",
    "type": "managed",
    "tags": ["configurable"],
    "attributes": [
        {"name": "子领域名称", "desc": "子领域名称", "is_config": False},
        {"name": "常用测试项组合", "desc": "保存的常用测试项组合，含名称字段(必填)，可在新建项目时复用", "is_config": False}
    ],
    "state_dimensions": [],
    "operations": ["新增", "修改", "删除", "管理测试项", "另存常用", "删除常用"]
})

# ---------- E-EVAL 评价 ----------
entities.append({
    "id": "E-EVAL",
    "name": "项目评价",
    "desc": "针对项目内报名参加者的协同评价业务对象。本次升级支持分值和权重两种评价方式(分支维度)、协同评价(多评价人员独立打分，组长汇总确认)，并可导出评价结果。新建项目时第一个被选择的评价人员默认作为评价组长。评价组长可在评价结果确认页面查看各评价人员评价结果并对最终结果进行确认。评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果。评价支持退回修改开启下一轮循环评价。",
    "type": "core",
    "tags": ["approvable", "multi-state", "collaborative", "configurable"],
    "attributes": [
        {"name": "项目编号", "desc": "关联项目编号", "is_config": False},
        {"name": "项目名称", "desc": "关联项目名称", "is_config": False},
        {"name": "子领域", "desc": "项目子领域，仅展示", "is_config": False},
        {"name": "评分方式", "desc": "评分方式，分值或权重两种(分支维度)，仅展示", "is_config": True},
        {"name": "依据标准", "desc": "依据标准信息，仅展示", "is_config": False},
        {"name": "及格分", "desc": "及格分，评价组长录入后跟随其他结果一起记录到系统中", "is_config": False},
        {"name": "评价人员", "desc": "评价人员列表，多人均可独立打分", "is_config": False},
        {"name": "评价组长", "desc": "第一个被选择的评价人员默认作为评价组长", "is_config": False},
        {"name": "评价结果", "desc": "评价人员的评价信息，含检测项目/分值/评价细则/分值或权重/客户列", "is_config": False},
        {"name": "历史结果", "desc": "保存的历史评价结果，可下载", "is_config": False},
        {"name": "成绩区间统计", "desc": "动态统计报名实验室得分的区间分布；统计规则由低值/高值组成，判断规则为大于等于低值小于高值", "is_config": False}
    ],
    "state_dimensions": [
        {
            "dimension_name": "评价状态",
            "states": ["待完善", "评价中", "评价确认中", "已确认"],
            "initial": "待完善",
            "terminal": ["已确认"],
            "note": note(True, "文档未直接命名评价状态枚举，但描述了评价组长完善、评价人员评价、评价组长确认/退回修改开启下一轮评价的流程。推断为四态并支持退回循环。", "", "")
        }
    ],
    "operations": ["完善测试项目和评价细则", "评价", "结果确认", "退回修改", "保存历史", "调整细则", "调整统计规则", "导出评价结果"]
})

# ---------- E-CERT 证书 ----------
entities.append({
    "id": "E-CERT",
    "name": "能力验证合格证书",
    "desc": "对通过能力验证的参加者发放的合格证书对象。证书具有到期时间，到期前30天系统通过邮件提醒用户并抄送项目管理员。证书需经项目管理员编制、技术主管审核、实验室负责人批准后发放。",
    "type": "core",
    "tags": ["approvable", "expirable"],
    "attributes": [
        {"name": "证书编号", "desc": "证书唯一编号", "is_config": False},
        {"name": "证书到期时间", "desc": "证书到期时间，距到期30天触发邮件提醒", "is_config": False},
        {"name": "关联报名记录", "desc": "关联报名记录", "is_config": False},
        {"name": "关联项目", "desc": "关联项目", "is_config": False},
        {"name": "证书文件", "desc": "证书文件，由项目管理员上传后批量提交审核", "is_config": False}
    ],
    "state_dimensions": [],
    "operations": ["编制", "审核", "批准", "发放", "到期提醒"]
})

# ---------- E-PAY 缴费记录 ----------
entities.append({
    "id": "E-PAY",
    "name": "缴费记录",
    "desc": "参加者就某报名项目进行缴费的记录对象。本次升级支持多次付款(不对付款金额进行校验限制)与分批退款，退款后更新项目费用为实际付款金额。支持多次分批上传发票。",
    "type": "core",
    "tags": ["multi-state"],
    "attributes": [
        {"name": "支付方式", "desc": "下拉选择框，必填", "is_config": False},
        {"name": "支付账户名称", "desc": "文本输入框，必填", "is_config": False},
        {"name": "汇款金额", "desc": "文本输入框，必填，默认为项目费用金额", "is_config": False},
        {"name": "付款底单", "desc": "文件选择框，必填", "is_config": False},
        {"name": "付款项目", "desc": "文本输入框，只读，内容为当前报名编号", "is_config": False},
        {"name": "备注", "desc": "文本输入框，选填", "is_config": False},
        {"name": "开票时间", "desc": "时间选择框，最后一次开票时间", "is_config": False},
        {"name": "电子发票", "desc": "文件选择组件，支持多次分批上传；发票列表点击x可移除文件(表单提交后生效)", "is_config": False},
        {"name": "退款金额", "desc": "文本输入框，必填，不能大于当前缴费金额；多次退款金额做累加处理，使用红色字体且大于0时显示", "is_config": False},
        {"name": "实际付款", "desc": "付款金额-退款金额=实际付款；退款后更新项目费用为实际付款金额", "is_config": False},
        {"name": "管理备注", "desc": "用于记录退款原因等内容", "is_config": False}
    ],
    "state_dimensions": [],
    "operations": ["上传付款单", "多次付款", "发票上传", "分批上传发票", "退款", "修改备注"]
})

# ---------- E-MSG 信息发送记录 ----------
entities.append({
    "id": "E-MSG",
    "name": "信息发送记录",
    "desc": "系统发送记录模块用于记录系统中的信息发送历史，记录内容包含发送方式、接收人、发送时间、发送人、发送结果。只有系统管理员和项目管理员可以查看。",
    "type": "managed",
    "tags": [],
    "attributes": [
        {"name": "接收号码", "desc": "接收号码，模糊匹配查询", "is_config": False},
        {"name": "发送方式", "desc": "下拉列表，精确匹配；选项有：短信、邮件、站内信", "is_config": False},
        {"name": "发送时间", "desc": "时间范围选择框，精确匹配", "is_config": False},
        {"name": "发送人", "desc": "发送操作人", "is_config": False},
        {"name": "消息标题", "desc": "消息标题", "is_config": False},
        {"name": "消息内容", "desc": "消息内容，可查看详情", "is_config": False},
        {"name": "发送结果", "desc": "发送结果", "is_config": False}
    ],
    "state_dimensions": [],
    "operations": ["查询", "查看详情"]
})

# ---------- E-TASK 审核任务 ----------
entities.append({
    "id": "E-TASK",
    "name": "审核任务",
    "desc": "业务审核流程中的任务对象，承载结果通知单审核、报告审核、证书审核等多类型审批。本次升级对测量审核结果通知单审核流程重构为单一流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序。支持批量处理、任务提醒(短信)、流程信息展示与导出。",
    "type": "core",
    "tags": ["approvable", "multi-state", "collaborative"],
    "attributes": [
        {"name": "任务类型", "desc": "审核任务类型，如结果通知单审核、报告审核、证书审核等", "is_config": False},
        {"name": "创建时间", "desc": "任务创建时间，查询参数", "is_config": False},
        {"name": "流程处理人", "desc": "审批顺序为提交申请时签字人的选择顺序", "is_config": False},
        {"name": "签章位置", "desc": "系统内增加电子签章位置信息，签章操作时自动代入减少手动调整", "is_config": False},
        {"name": "审核结果", "desc": "下拉选择框，选项有：同意、退回", "is_config": False},
        {"name": "审核意见", "desc": "文本输入框，选填", "is_config": False}
    ],
    "state_dimensions": [
        {
            "dimension_name": "审核任务状态",
            "states": ["待审核", "已通过", "已退回"],
            "initial": "待审核",
            "terminal": ["已通过", "已退回"],
            "note": note(True, "文档描述批量审核表单含同意/退回选项，推断审核任务存在待审核/已通过/已退回三态", "", "")
        }
    ],
    "operations": ["创建任务", "审核", "批量审核", "导出", "任务提醒"]
})

# ---------- E-ARC 项目归档 ----------
entities.append({
    "id": "E-ARC",
    "name": "项目归档",
    "desc": "已结束项目文件的分类整理对象，包括归档、结构化分析和数字化存储。主子表展示，主表为项目阶段，子表为各实验室文件。支持上传文件、打包下载(zip格式含清单文件及按项目阶段命名的目录)。",
    "type": "managed",
    "tags": ["configurable"],
    "attributes": [
        {"name": "项目阶段", "desc": "归档文件所属项目阶段(能力验证：能力验证计划报名表/参加者提交的资料/结果通知单/能力验证合格证书复印件等;其它)", "is_config": False},
        {"name": "文件名称", "desc": "文本输入框，必填", "is_config": False},
        {"name": "份数", "desc": "文本输入框", "is_config": False},
        {"name": "页数", "desc": "文本输入框", "is_config": False},
        {"name": "备注", "desc": "文本输入框", "is_config": False},
        {"name": "实验室", "desc": "子表字段，文件所属实验室", "is_config": False}
    ],
    "state_dimensions": [],
    "operations": ["开启整理任务", "查看归档", "上传文件", "打包下载", "编辑", "下载"]
})

# ============================================================
# Step 2: 结构关系建模
# ============================================================
structural_relations = [
    {
        "from": "E-PROJ", "to": "E-REG",
        "relation_type": "composition",
        "cardinality": "1:N",
        "ownership_dimension": "business_ownership",
        "desc": "一个能力验证项目拥有多条报名记录，报名记录的业务成果(报名/结果/证书)归属于项目",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "项目-报名为主从业务关系", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-EVAL",
        "relation_type": "composition",
        "cardinality": "1:1",
        "ownership_dimension": "business_ownership",
        "desc": "一个项目拥有一个项目评价对象，评价业务成果归属于项目",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "评价针对项目内所有报名参加者进行", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-ARC",
        "relation_type": "reference",
        "cardinality": "1:1",
        "ownership_dimension": "configuration_source",
        "desc": "一个已结束项目关联一个归档对象；归档需用户主动点击『文件整理』按钮触发，仅已结束项目才有归档，非每条项目都有",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "(c)事件触发归属: 归档有独立整理流程(整理任务->整理中->已归档), 创建前置条件为项目状态=已结束, 并非每条项目都有归档(仅已结束项目)", "", "")
    },
    {
        "from": "E-REG", "to": "E-PAY",
        "relation_type": "composition",
        "cardinality": "1:N",
        "ownership_dimension": "business_ownership",
        "desc": "一条报名记录拥有多条缴费记录(支持多次付款与分批退款)，缴费业务成果归属于报名记录",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "已报名项目支持多次付款功能", "", "")
    },
    {
        "from": "E-REG", "to": "E-CERT",
        "relation_type": "reference",
        "cardinality": "1:1",
        "ownership_dimension": "configuration_source",
        "desc": "一条报名记录(通过者)关联一个合格证书；证书为条件性生成，仅对通过能力验证的参加者发放，非每条报名记录都有证书",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "(c)事件触发归属: 证书有独立多步骤创建流程(编制->审核->批准->发放), 创建前置条件含项目状态=报告审核中+结果通知单已批准, 并非每条报名都有证书(仅通过者)", "", "")
    },
    {
        "from": "E-REG", "to": "E-TASK",
        "relation_type": "reference",
        "cardinality": "1:N",
        "ownership_dimension": "configuration_source",
        "desc": "报名记录在结果通知单/证书审核环节引用审核任务，报名记录为审核任务提供业务上下文(并非生命周期容器)",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "审核任务由多种业务对象触发，非报名记录独占", "", "")
    },
    {
        "from": "E-LAB", "to": "E-REG",
        "relation_type": "reference",
        "cardinality": "1:N",
        "ownership_dimension": "configuration_source",
        "desc": "实验室为报名记录提供主体信息来源(实验室信息作为报名主体)，但报名记录生命周期归属于项目而非实验室",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(True, "实验室管理入口在系统管理菜单下，但实验室信息是报名记录的主体来源而非生命周期容器，按配置来源/引用处理", "", "")
    },
    {
        "from": "E-STD", "to": "E-TESTITEM",
        "relation_type": "composition",
        "cardinality": "1:N",
        "ownership_dimension": "business_ownership",
        "desc": "一个标准库拥有其下多个测试项(含子测试项)，测试项作为标准库的结构组成",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "标准库-测试项为整体-部分关系", "", "")
    },
    {
        "from": "E-TESTITEM", "to": "E-TESTITEM",
        "relation_type": "self_reference",
        "cardinality": "1:N",
        "ownership_dimension": "business_ownership",
        "desc": "测试项下可有子测试项，自引用层级结构；含有子项的记录不允许删除",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "测试项嵌套层级", "", "")
    },
    {
        "from": "E-CATE", "to": "E-TESTITEM",
        "relation_type": "reference",
        "cardinality": "1:N",
        "ownership_dimension": "configuration_source",
        "desc": "子领域通过从标准库选择方式引入测试项(本次升级由表单方式变更为选择方式)，子领域为测试项在项目中的引用提供配置入口，不拥有测试项生命周期",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "子领域-测试项为引用关系，测试项生命周期归属标准库", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-CATE",
        "relation_type": "reference",
        "cardinality": "N:1",
        "ownership_dimension": "configuration_source",
        "desc": "项目引用子领域作为分类配置；子领域为项目提供分类参数",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "项目-子领域为引用关系", "", "cardinality 翻转为父侧视角应为 1:N 多个项目引用同一子领域，但本条以项目为主动方引用子领域")
    },
    {
        "from": "E-PROJ", "to": "E-STD",
        "relation_type": "reference",
        "cardinality": "N:1",
        "ownership_dimension": "configuration_source",
        "desc": "项目依据标准引用标准库；标准库为项目提供标准数据来源",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "项目-标准库为引用关系", "", "同上 cardinality 备注")
    },
    {
        "from": "E-EVAL", "to": "E-REG",
        "relation_type": "reference",
        "cardinality": "1:N",
        "ownership_dimension": "configuration_source",
        "desc": "项目评价对象以报名参加者为评价目标，评价结果回填至报名记录；评价对象不拥有报名记录生命周期",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "评价目标是报名参加者，评价结果回填报名记录", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-MSG",
        "relation_type": "reference",
        "cardinality": "1:N",
        "ownership_dimension": "configuration_source",
        "desc": "项目通过详情页消息发送功能生成信息发送记录；项目为消息发送提供业务上下文，不拥有信息发送记录生命周期",
        "confidence": "high",
        "conflict_flags": "",
        "note": note(False, "消息发送入口在项目详情页", "", "")
    }
]

# 修正：E-PROJ->E-CATE 与 E-PROJ->E-STD 的 cardinality 应为父侧视角
# 父侧为子领域/标准库(被多个项目引用) - 但 from=PROJ 是主动引用方
# 按铁律方向 from=父/拥有方 - 这两条应翻转为 E-CATE->E-PROJ, E-STD->E-PROJ
# 但实际语义是项目引用(配置来源)子领域，业务成果归属项目自身
# 处理：调整为 reference 且 from 为被引用方(标准库/子领域) to 为项目，体现"标准库/子领域被项目引用"
# 但这违反"from=父方"铁律。重新审视：reference 关系中 from 仍应为拥有方/主动方
# 项目拥有自己的子领域配置项 -> from=PROJ to=CATE 是合理的(项目方拥有引用记录)
# cardinality 1:N 是父侧视角，一个项目对应一个子领域配置 → 实际为 N:1 (多项目一子领域)
# 但铁律禁止 N:1。此处语义为：子领域被多个项目引用 -> 翻转为 E-CATE -> E-PROJ (1:N) reference
structural_relations = [r for r in structural_relations if not (
    (r["from"] == "E-PROJ" and r["to"] == "E-CATE") or
    (r["from"] == "E-PROJ" and r["to"] == "E-STD")
)]
structural_relations.append({
    "from": "E-CATE", "to": "E-PROJ",
    "relation_type": "reference",
    "cardinality": "1:N",
    "ownership_dimension": "configuration_source",
    "desc": "一个子领域可被多个项目引用作为分类配置；子领域为项目提供分类参数",
    "confidence": "high",
    "conflict_flags": "",
    "note": note(False, "翻转为父侧视角(子领域被引用)", "", "")
})
structural_relations.append({
    "from": "E-STD", "to": "E-PROJ",
    "relation_type": "reference",
    "cardinality": "1:N",
    "ownership_dimension": "configuration_source",
    "desc": "一个标准库可被多个项目引用作为依据标准；标准库为项目提供标准数据来源",
    "confidence": "high",
    "conflict_flags": "",
    "note": note(False, "翻转为父侧视角(标准库被引用)", "", "")
})

# ============================================================
# Step 3: 分支维度映射
# ============================================================
branch_dimensions = [
    {
        "dimension": "项目类型",
        "entity": "E-PROJ",
        "values": ["能力验证", "测量审核"],
        "impact_scope": "提供者流程结构、消息发送接收人1必填性、评价与统计阶段是否分离、文件整理主表数据组成、批量处理流程",
        "evidence": "P0106-P0122 能力验证提供者流程 vs 测量审核提供者流程；P0421/P0544 接收人1在能力验证为选填(数据来源于所有实验室/报名实验室)，在测量审核为必填(只包含当前报名实验室)",
        "branches": [
            {"value": "能力验证", "target_transition": "T-001", "desc": "提供者流程含立项/方案设计/实施/评价和统计(分离)/报告编制与结果通知/项目验收总结/结束"},
            {"value": "测量审核", "target_transition": "T-001", "desc": "提供者流程含受理报名/方案设计/实施(评价人员评价并对评价结果进行统计分析合并)/结果通知与证书/归档/结束"}
        ],
        "coverage": {"transitions": ["T-001", "T-014", "T-030"], "cross_entity": ["XC-03", "XC-04"], "business_rules": ["BR-VAL-07", "BR-USA-09"]}
    },
    {
        "dimension": "评分方式",
        "entity": "E-EVAL",
        "values": ["分值", "权重"],
        "impact_scope": "评价表单中『分值/权重』列含义、评价细则录入字段、评价结果计算逻辑",
        "evidence": "P0633 调整评价功能，支持分值和权重两种评价方式；P0642/P0675 评价表单含『分值/权重』字段",
        "branches": [
            {"value": "分值", "target_transition": "T-091", "desc": "评价人员按分值打分，及格分按分值判定"},
            {"value": "权重", "target_transition": "T-091", "desc": "评价人员按权重打分，及格分按权重计算"}
        ],
        "coverage": {"transitions": ["T-091", "T-093"], "cross_entity": [], "business_rules": ["BR-VAL-12"]}
    },
    {
        "dimension": "评价人员角色",
        "entity": "E-EVAL",
        "values": ["评价组长", "评价成员"],
        "impact_scope": "评价结果可见性、最终结果确认权限、测试项目与评价细则完善权限、调整细则与统计规则配置权限",
        "evidence": "P0669-P0705 协同评价与评价确认章节；评价组长可查看各评价人员评价结果并对最终结果进行确认，评价人员只能对自己的评价结果进行修改",
        "branches": [
            {"value": "评价组长", "target_transition": "T-090", "desc": "可完善测试项目与评价细则、查看所有评价人员评价结果、确认最终结果、退回修改开启下一轮、保存历史、调整细则、配置统计规则"},
            {"value": "评价成员", "target_transition": "T-091", "desc": "仅能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果"}
        ],
        "coverage": {"transitions": ["T-090", "T-091", "T-093", "T-094"], "cross_entity": [], "business_rules": ["BR-AUT-03"]}
    },
    {
        "dimension": "消息发送接收人范围",
        "entity": "E-MSG",
        "values": ["所有实验室", "报名实验室"],
        "impact_scope": "消息发送页面接收人1数据列表内容",
        "evidence": "P0421 当项目状态为待开始/报名中时右侧实验室列表为所有实验室，其他状态为报名实验室(运行时选择型)",
        "branches": [
            {"value": "所有实验室", "target_transition": "T-110", "desc": "项目状态为待开始/报名中时，接收人1数据来源于所有实验室"},
            {"value": "报名实验室", "target_transition": "T-110", "desc": "项目状态为进行中/报告审核中/已结束时，接收人1数据来源于报名实验室"}
        ],
        "coverage": {"transitions": ["T-110"], "cross_entity": [], "business_rules": []}
    }
]
meta["branch_dimensions"] = branch_dimensions

# ============================================================
# Step 4: 状态转换提取与因果关系构建
# ============================================================
transitions = []

# ---------- E-PROJ 项目状态 ----------
transitions.append({
    "id": "T-001", "entity": "E-PROJ", "dimension": "项目状态",
    "from": "待开始", "to": "报名中",
    "action": "立项批准并发布邀请函/通知",
    "role": "R-LAB-DIR",
    "preconditions": ["项目已立项", "技术主管已审核邀请函/通知(测量审核无此环节)"],
    "expected_results": ["项目状态变为报名中", "参加者可接收能力验证通知并报名"],
    "traits": ["audit", "branch"],
    "priority": "P0",
    "source_ref": "P0106-P0113 能力验证提供者流程; P0117-P0122 测量审核提供者流程",
    "note": note(True, "项目类型分支：能力验证需立项+邀请函审核;测量审核需受理报名+组建项目组+任务通知书", "", "项目类型"),
    "sub_steps": []
})
transitions.append({
    "id": "T-002", "entity": "E-PROJ", "dimension": "项目状态",
    "from": "报名中", "to": "进行中",
    "action": "发布能力验证实施计划并发放样品与作业指导书",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名结束", "样品已核查(E-PROJ.样品状态=已核查)"],
    "expected_results": ["项目状态变为进行中", "参加者开始测试", "报名记录样品状态推进至待收样/已收样"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0110 实施阶段",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-003", "entity": "E-PROJ", "dimension": "项目状态",
    "from": "进行中", "to": "报告审核中",
    "action": "结果报告回收与评价完成，提交报告审核",
    "role": "R-PLANNER",
    "preconditions": ["参加者结果报告已回收", "评价已完成(E-EVAL.评价状态=已确认)", "策划人员编制结果报告和结果通知单"],
    "expected_results": ["项目状态变为报告审核中", "技术主管审核结果报告", "授权签字人批准结果报告和结果通知单"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0112 报告编制和结果通知",
    "note": note(False, "", "", ""),
    "sub_steps": [
        {"step": 1, "action": "策划人员编制结果报告和结果通知单", "role": "R-PLANNER", "expected_result": "结果报告与结果通知单编制完成"},
        {"step": 2, "action": "技术主管审核", "role": "R-TECH", "expected_result": "审核通过或退回"},
        {"step": 3, "action": "授权签字人批准结果报告和结果通知单", "role": "R-SIGN", "expected_result": "批准完成"},
        {"step": 4, "action": "项目管理员编制证书项目", "role": "R-PROJ-ADMIN", "expected_result": "证书项目编制完成"},
        {"step": 5, "action": "技术主管审核证书", "role": "R-TECH", "expected_result": "审核通过或退回"},
        {"step": 6, "action": "实验室负责人批准证书", "role": "R-LAB-DIR", "expected_result": "批准完成"}
    ]
})
transitions.append({
    "id": "T-004", "entity": "E-PROJ", "dimension": "项目状态",
    "from": "报告审核中", "to": "已结束",
    "action": "项目管理员发放结果通知单和证书，策划人员进行项目总结并记录归档",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["结果报告已批准", "结果通知单已批准", "证书已批准"],
    "expected_results": ["项目状态变为已结束", "结果通知单和证书已发放", "归档任务可开启", "报名记录状态推进至报告已发布"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0112-P0113 报告编制与项目验收总结",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-PROJ 样品状态 ----------
transitions.append({
    "id": "T-005", "entity": "E-PROJ", "dimension": "样品状态",
    "from": "待核查", "to": "已核查",
    "action": "样品制备人员执行样品配置、核查和一致性测试",
    "role": "R-SAMPLE-MAKER",
    "preconditions": ["样品制备方案已编制", "样品已制备完成"],
    "expected_results": ["样品状态变为已核查", "样品可用于发放"],
    "traits": [],
    "priority": "P1",
    "source_ref": "P0081-P0082 样品制备人员职责; P0109 方案设计阶段",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-REG 报名记录状态 ----------
# 注：T-020 (报告已发布→已撤销) 已移除：违反"终态→终态转换"铁律
# "已撤销"作为孤立终态保留在枚举中，标注无合理非终态入边
# 若业务确需撤销操作，应从"报名成功"或"结果待提交"等中间态发起
transitions.append({
    "id": "T-010", "entity": "E-REG", "dimension": "报名记录状态",
    "from": None, "to": "报名待审核",
    "action": "参加者提交报名",
    "role": "R-PARTICIPANT",
    "preconditions": ["项目状态为报名中", "实验室已审核通过(E-LAB.审核状态=启用)"],
    "expected_results": ["报名记录创建", "报名记录状态为报名待审核", "费用状态为待缴费", "发票状态为待开票", "通知状态为未发送"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0140 报名参加能力验证",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-011", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "报名待审核", "to": "报名成功",
    "action": "项目管理员审核报名通过",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名记录状态为报名待审核"],
    "expected_results": ["报名记录状态变为报名成功", "短信通知参加者『报名信息审核通过』", "报名记录样品状态可推进至待发样"],
    "traits": ["audit", "rollback"],
    "priority": "P0",
    "source_ref": "P0497 报名审核通过短信通知",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-012", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "报名待审核", "to": "报名退回",
    "action": "项目管理员审核报名退回",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名记录状态为报名待审核"],
    "expected_results": ["报名记录状态变为报名退回", "短信通知参加者『报名信息审核未通过』"],
    "traits": ["audit", "rollback"],
    "priority": "P1",
    "source_ref": "P0498 报名审核退回修改短信通知",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-013", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "报名退回", "to": "报名待审核",
    "action": "参加者修改后重新提交报名",
    "role": "R-PARTICIPANT",
    "preconditions": ["报名记录状态为报名退回"],
    "expected_results": ["报名记录状态变为报名待审核"],
    "traits": ["rollback"],
    "priority": "P1",
    "source_ref": "P0131 报名记录状态含报名退回-报名待审核流转",
    "note": note(True, "依据状态枚举与报名退回可重新提交的业务常识推断", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-014", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "报名成功", "to": "结果待提交",
    "action": "项目管理员发放样品与作业指导书，参加者接收样品",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名记录状态为报名成功", "报名记录样品状态推进(待发样->待收样->已收样)"],
    "expected_results": ["报名记录状态变为结果待提交", "报名记录样品状态推进", "短信通知参加者『样品已发出』"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0110 实施阶段; P0499 发样通知短信",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-015", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "结果待提交", "to": "结果已提交",
    "action": "参加者提交结果报告",
    "role": "R-PARTICIPANT",
    "preconditions": ["报名记录状态为结果待提交", "参加者已完成测试"],
    "expected_results": ["报名记录状态变为结果已提交"],
    "traits": [],
    "priority": "P0",
    "source_ref": "P0146 提交结果报告",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-016", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "结果已提交", "to": "结果退回修改",
    "action": "项目管理员测试结果审核退回",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名记录状态为结果已提交"],
    "expected_results": ["报名记录状态变为结果退回修改", "短信通知参加者『测试报告审核未通过』"],
    "traits": ["audit", "rollback"],
    "priority": "P1",
    "source_ref": "P0502 测试结果审核退回短信",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-017", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "结果退回修改", "to": "结果已提交",
    "action": "参加者修改后重新提交结果报告",
    "role": "R-PARTICIPANT",
    "preconditions": ["报名记录状态为结果退回修改"],
    "expected_results": ["报名记录状态变为结果已提交"],
    "traits": ["rollback"],
    "priority": "P1",
    "source_ref": "P0131 报名记录状态含结果退回修改-结果已提交流转",
    "note": note(True, "依据状态枚举与退回可重新提交的业务常识推断", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-018", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "结果已提交", "to": "报告审核中",
    "action": "项目管理员测试结果审核通过并批量提交审核",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名记录状态为结果已提交", "结果通知单/证书已上传"],
    "expected_results": ["报名记录状态变为报告审核中", "短信通知参加者『测试报告审核通过』"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0501 测试结果审核通过短信; P0392-P0410 项目批量操作提交审核",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-019", "entity": "E-REG", "dimension": "报名记录状态",
    "from": "报告审核中", "to": "报告已发布",
    "action": "授权签字人/实验室负责人批准并发放结果通知单和证书",
    "role": "R-LAB-DIR",
    "preconditions": ["报名记录状态为报告审核中", "结果通知单已批准", "证书已批准"],
    "expected_results": ["报名记录状态变为报告已发布", "短信通知参加者『结果通知单已发布』", "证书生成并关联报名记录"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0503 结果通知单发布短信; P0112 发放结果通知单和证书",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
# T-020 已移除：原 from=报告已发布(终态) to=已撤销(终态) 违反终态→终态铁律
# "已撤销"保留为孤立终态，若业务需撤销应从非终态发起

# ---------- E-REG 报名记录样品状态 ----------
transitions.append({
    "id": "T-030", "entity": "E-REG", "dimension": "报名记录样品状态",
    "from": "待发样", "to": "待收样",
    "action": "项目管理员发出样品",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["报名记录状态为报名成功", "项目样品状态为已核查"],
    "expected_results": ["报名记录样品状态变为待收样", "短信通知参加者『样品已发出』"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0110 样品发放; P0499 发样通知短信",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-031", "entity": "E-REG", "dimension": "报名记录样品状态",
    "from": "待收样", "to": "已收样",
    "action": "参加者接收样品",
    "role": "R-PARTICIPANT",
    "preconditions": ["报名记录样品状态为待收样"],
    "expected_results": ["报名记录样品状态变为已收样"],
    "traits": [],
    "priority": "P0",
    "source_ref": "P0145 接收样品",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-032", "entity": "E-REG", "dimension": "报名记录样品状态",
    "from": "已收样", "to": "已确认",
    "action": "参加者确认收样",
    "role": "R-PARTICIPANT",
    "preconditions": ["报名记录样品状态为已收样"],
    "expected_results": ["报名记录样品状态变为已确认"],
    "traits": [],
    "priority": "P0",
    "source_ref": "P0131 报名记录样品状态含已确认终态",
    "note": note(True, "文档未明确确认动作主体与时机，依据状态枚举推断为参加者确认", "", ""),
    "sub_steps": []
})

# ---------- E-REG 费用状态 ----------
transitions.append({
    "id": "T-040", "entity": "E-REG", "dimension": "费用状态",
    "from": "待缴费", "to": "已缴费",
    "action": "参加者上传付款单(支持多次付款)",
    "role": "R-PARTICIPANT",
    "preconditions": ["费用状态为待缴费", "报名记录状态为报名成功或之后"],
    "expected_results": ["费用状态变为已缴费", "缴费记录创建(支持多次)", "发票状态可推进至待开票"],
    "traits": ["data_constraint"],
    "priority": "P0",
    "source_ref": "P0456-P0469 已报名项目多次付款功能; P0141-P0142 进行缴费上传缴费证明",
    "note": note(False, "不对付款金额进行校验限制，可多次付款", "", ""),
    "sub_steps": []
})

# ---------- E-REG 发票状态 ----------
transitions.append({
    "id": "T-050", "entity": "E-REG", "dimension": "发票状态",
    "from": "待开票", "to": "已开票",
    "action": "财务管理人员分批上传发票",
    "role": "R-FIN",
    "preconditions": ["发票状态为待开票", "费用状态为已缴费"],
    "expected_results": ["发票状态变为已开票", "参加者可下载发票"],
    "traits": ["data_constraint"],
    "priority": "P0",
    "source_ref": "P0985-P0995 修改发票上传功能支持多次分批上传; P0143 接收发票",
    "note": note(False, "支持多次分批上传发票", "", ""),
    "sub_steps": []
})

# ---------- E-REG 通知状态 ----------
transitions.append({
    "id": "T-060", "entity": "E-REG", "dimension": "通知状态",
    "from": "未发送", "to": "待确认",
    "action": "系统发送能力验证通知",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["通知状态为未发送", "项目状态为报名中"],
    "expected_results": ["通知状态变为待确认", "参加者接收能力验证通知"],
    "traits": [],
    "priority": "P0",
    "source_ref": "P0139 接收能力验证通知; P0131 通知状态枚举",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-061", "entity": "E-REG", "dimension": "通知状态",
    "from": "待确认", "to": "待审核",
    "action": "参加者接收能力验证计划并确认",
    "role": "R-PARTICIPANT",
    "preconditions": ["通知状态为待确认"],
    "expected_results": ["通知状态变为待审核"],
    "traits": [],
    "priority": "P0",
    "source_ref": "P0144 接收能力验证计划并确认",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-062", "entity": "E-REG", "dimension": "通知状态",
    "from": "待审核", "to": "已审核",
    "action": "项目管理员/技术主管审核",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["通知状态为待审核"],
    "expected_results": ["通知状态变为已审核"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0131 通知状态枚举",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-063", "entity": "E-REG", "dimension": "通知状态",
    "from": "已审核", "to": "已批准",
    "action": "授权签字人/实验室负责人批准",
    "role": "R-LAB-DIR",
    "preconditions": ["通知状态为已审核"],
    "expected_results": ["通知状态变为已批准"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0131 通知状态枚举",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-064", "entity": "E-REG", "dimension": "通知状态",
    "from": "待审核", "to": "退回",
    "action": "审核退回",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["通知状态为待审核"],
    "expected_results": ["通知状态变为退回"],
    "traits": ["audit", "rollback"],
    "priority": "P1",
    "source_ref": "P0131 通知状态枚举",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-LAB 审核状态 ----------
transitions.append({
    "id": "T-070", "entity": "E-LAB", "dimension": "审核状态",
    "from": None, "to": "待审核",
    "action": "机构新增/修改实验室信息",
    "role": "R-PARTICIPANT",
    "preconditions": ["机构用户已登录"],
    "expected_results": ["实验室状态为待审核", "需管理用户审核通过后方可用于项目报名"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0185 实验室信息新增状态字段",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-071", "entity": "E-LAB", "dimension": "审核状态",
    "from": "待审核", "to": "启用",
    "action": "管理用户审核通过",
    "role": "R-SYS-ADMIN",
    "preconditions": ["实验室状态为待审核"],
    "expected_results": ["实验室状态变为启用", "为当前数据生成快照记录", "实验室可用于项目报名"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0210 实验室审核通过",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-072", "entity": "E-LAB", "dimension": "审核状态",
    "from": "待审核", "to": "退回修改",
    "action": "管理用户审核退回修改(必须填写审核意见)",
    "role": "R-SYS-ADMIN",
    "preconditions": ["实验室状态为待审核", "审核意见必填"],
    "expected_results": ["实验室状态变为退回修改"],
    "traits": ["audit", "rollback"],
    "priority": "P1",
    "source_ref": "P0211 实验室审核退回修改",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-073", "entity": "E-LAB", "dimension": "审核状态",
    "from": "退回修改", "to": "待审核",
    "action": "机构修改后重新提交",
    "role": "R-PARTICIPANT",
    "preconditions": ["实验室状态为退回修改"],
    "expected_results": ["实验室状态变为待审核"],
    "traits": ["rollback"],
    "priority": "P1",
    "source_ref": "P0185 实验室信息状态字段含退回修改-待审核流转",
    "note": note(True, "依据状态枚举与退回可重新提交的业务常识推断", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-074", "entity": "E-LAB", "dimension": "审核状态",
    "from": "启用", "to": "停用",
    "action": "管理用户停用实验室",
    "role": "R-SYS-ADMIN",
    "preconditions": ["实验室状态为启用"],
    "expected_results": ["实验室状态变为停用"],
    "traits": [],
    "priority": "P2",
    "source_ref": "P0196 实验室列表操作列含停用按钮",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-075", "entity": "E-LAB", "dimension": "审核状态",
    "from": "停用", "to": "启用",
    "action": "管理用户启用实验室",
    "role": "R-SYS-ADMIN",
    "preconditions": ["实验室状态为停用"],
    "expected_results": ["实验室状态变为启用"],
    "traits": [],
    "priority": "P2",
    "source_ref": "P0196 实验室列表操作列含启用按钮",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-STD 启用状态 ----------
transitions.append({
    "id": "T-080", "entity": "E-STD", "dimension": "启用状态",
    "from": "启用", "to": "停用",
    "action": "管理用户停用标准库",
    "role": "R-SYS-ADMIN",
    "preconditions": ["标准库状态为启用"],
    "expected_results": ["标准库状态变为停用", "停用的标准库在项目创建等环节不可被选择"],
    "traits": [],
    "priority": "P2",
    "source_ref": "P0269 停用/启用标准库",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-081", "entity": "E-STD", "dimension": "启用状态",
    "from": "停用", "to": "启用",
    "action": "管理用户启用标准库",
    "role": "R-SYS-ADMIN",
    "preconditions": ["标准库状态为停用"],
    "expected_results": ["标准库状态变为启用"],
    "traits": [],
    "priority": "P2",
    "source_ref": "P0269 停用/启用标准库",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-EVAL 评价状态 ----------
transitions.append({
    "id": "T-090", "entity": "E-EVAL", "dimension": "评价状态",
    "from": None, "to": "待完善",
    "action": "评价组长点击编辑进入完善页面，编辑完善评价项目及评价细则",
    "role": "R-EVAL-LEAD",
    "preconditions": ["项目已进入评价阶段", "评价组长已确定(第一个被选择的评价人员)"],
    "expected_results": ["评价状态为待完善", "评价组长可编辑测试项目和评价细则", "支持另存常用与常用项复用"],
    "traits": ["branch"],
    "priority": "P0",
    "source_ref": "P0634-P0659 测试项目评价细则完善",
    "note": note(False, "评价人员角色分支：仅评价组长可完善", "", "评价人员角色"),
    "sub_steps": []
})
transitions.append({
    "id": "T-091", "entity": "E-EVAL", "dimension": "评价状态",
    "from": "待完善", "to": "评价中",
    "action": "评价组长确定完善内容，评价人员对报名项目进行评价",
    "role": "R-EVAL",
    "preconditions": ["评价状态为待完善", "评价组长已保存完善后的测试项目数据"],
    "expected_results": ["评价状态变为评价中", "评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果"],
    "traits": ["branch"],
    "priority": "P0",
    "source_ref": "P0668-P0680 协同评价",
    "note": note(False, "评分方式分支影响分值/权重列含义", "", "评分方式"),
    "sub_steps": []
})
transitions.append({
    "id": "T-092", "entity": "E-EVAL", "dimension": "评价状态",
    "from": "评价中", "to": "评价确认中",
    "action": "评价人员提交评价结果",
    "role": "R-EVAL",
    "preconditions": ["评价状态为评价中", "评价人员已录入评价分数"],
    "expected_results": ["评价状态变为评价确认中", "评价组长可在结果确认页面查看各评价人员的评价结果"],
    "traits": [],
    "priority": "P0",
    "source_ref": "P0669 评价人员确定提交结果; P0682 评价确认",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-093", "entity": "E-EVAL", "dimension": "评价状态",
    "from": "评价确认中", "to": "已确认",
    "action": "评价组长点击确认将当前结果正式提交为项目的最终评价结果",
    "role": "R-EVAL-LEAD",
    "preconditions": ["评价状态为评价确认中", "评价组长已填写及格分和客户得分"],
    "expected_results": ["评价状态变为已确认", "项目评价状态关闭", "评价结果回填至报名记录"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0693 确认按钮",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-094", "entity": "E-EVAL", "dimension": "评价状态",
    "from": "评价确认中", "to": "评价中",
    "action": "评价组长点击退回修改，将当前评价结果保存为历史结果并开启下一轮评价",
    "role": "R-EVAL-LEAD",
    "preconditions": ["评价状态为评价确认中"],
    "expected_results": ["当前评价结果保存为历史结果", "开启下一轮评价", "评价状态变为评价中"],
    "traits": ["rollback"],
    "priority": "P1",
    "source_ref": "P0696 退回修改",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-TASK 审核任务状态 ----------
transitions.append({
    "id": "T-100", "entity": "E-TASK", "dimension": "审核任务状态",
    "from": None, "to": "待审核",
    "action": "用户通过表单或审核已存在任务生成新的审核任务",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["存在已存在的任务或表单提交", "签字人选择顺序已确定"],
    "expected_results": ["审核任务创建", "审核任务状态为待审核", "系统发送短信通知相关负责人『您有一个新的xxx审核任务，请及时处理』"],
    "traits": ["audit", "time_sensitive"],
    "priority": "P0",
    "source_ref": "P0925-P0934 测量审核结果通知单审核流程优化与任务提醒",
    "note": note(False, "测量审核结果通知单审批流程合并为单一流程", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-101", "entity": "E-TASK", "dimension": "审核任务状态",
    "from": "待审核", "to": "已通过",
    "action": "流程处理人按签字顺序审核同意",
    "role": "R-TECH",
    "preconditions": ["审核任务状态为待审核", "前序处理人已审核同意"],
    "expected_results": ["审核任务状态变为已通过", "签章位置信息自动代入"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0926-P0929 预置签章位置信息; P0939-P0943 批量审核含同意选项",
    "note": note(False, "", "", ""),
    "sub_steps": []
})
transitions.append({
    "id": "T-102", "entity": "E-TASK", "dimension": "审核任务状态",
    "from": "待审核", "to": "已退回",
    "action": "流程处理人审核退回",
    "role": "R-TECH",
    "preconditions": ["审核任务状态为待审核"],
    "expected_results": ["审核任务状态变为已退回"],
    "traits": ["audit", "rollback"],
    "priority": "P1",
    "source_ref": "P0939-P0943 批量审核含退回选项",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-MSG 信息发送记录(无状态机但有创建转换) ----------
transitions.append({
    "id": "T-110", "entity": "E-MSG", "dimension": "",
    "from": None, "to": "已发送",
    "action": "项目管理员在项目详情页发送消息(短信/邮件/站内信)",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["项目未结束", "接收人1和接收人2不能同时为空", "发送方式已选择", "内容已填写"],
    "expected_results": ["信息发送记录创建", "消息按选择方式发送", "记录发送方式/接收人/发送时间/发送人/发送结果"],
    "traits": ["branch"],
    "priority": "P1",
    "source_ref": "P0416-P0428 优化消息发送功能(能力验证); P0538-P0551 优化消息发送功能(测量审核)",
    "note": note(False, "消息发送接收人范围分支：项目状态决定接收人1数据来源(所有实验室/报名实验室)", "", "消息发送接收人范围"),
    "sub_steps": []
})

# ---------- E-ARC 归档(无状态机但有创建转换) ----------
transitions.append({
    "id": "T-120", "entity": "E-ARC", "dimension": "",
    "from": None, "to": "整理中",
    "action": "项目管理员对已结束项目点击文件整理按钮开启整理任务",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["项目状态为已结束"],
    "expected_results": ["系统开启整理任务", "提示用户『归档任务已开启，请稍后查看』"],
    "traits": ["branch"],
    "priority": "P1",
    "source_ref": "P0354-P0380 文件整理(能力验证); P0508-P0534 文件整理(测量审核)",
    "note": note(False, "项目类型分支：能力验证主表含能力验证计划报名表/参加者提交的资料/结果通知单/能力验证合格证书复印件;测量审核主表含参加者提交的资料", "", "项目类型"),
    "sub_steps": []
})
transitions.append({
    "id": "T-121", "entity": "E-ARC", "dimension": "",
    "from": "整理中", "to": "已归档",
    "action": "系统完成归档、结构化分析和数字化存储",
    "role": "system",
    "preconditions": ["归档任务已开启"],
    "expected_results": ["整理完成", "操作列显示查看归档按钮", "用户可进入归档数据查看页面查看并补充归档信息"],
    "traits": [],
    "priority": "P1",
    "source_ref": "P0357-P0359 文件整理完成后展示查看归档",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ---------- E-CERT 证书(到期提醒触发性转换) ----------
transitions.append({
    "id": "T-130", "entity": "E-CERT", "dimension": "",
    "from": None, "to": "已发放",
    "action": "项目管理员编制证书项目，技术主管审核，实验室负责人批准并发放",
    "role": "R-PROJ-ADMIN",
    "preconditions": ["项目状态为报告审核中", "结果通知单已批准"],
    "expected_results": ["证书生成", "证书关联报名记录", "证书到期时间设定"],
    "traits": ["audit"],
    "priority": "P0",
    "source_ref": "P0112 报告编制和结果通知(证书编制审核批准)",
    "note": note(False, "", "", ""),
    "sub_steps": [
        {"step": 1, "action": "项目管理员编制证书项目", "role": "R-PROJ-ADMIN", "expected_result": "证书项目编制完成"},
        {"step": 2, "action": "技术主管审核证书", "role": "R-TECH", "expected_result": "审核通过或退回"},
        {"step": 3, "action": "实验室负责人批准证书", "role": "R-LAB-DIR", "expected_result": "批准完成"}
    ]
})
transitions.append({
    "id": "T-131", "entity": "E-CERT", "dimension": "",
    "from": "已发放", "to": "已发放",
    "action": "系统每天上午9点查询证书信息，距到期时间等于30天的证书触发邮件提醒并抄送项目管理员",
    "role": "system",
    "preconditions": ["证书距到期时间等于30天"],
    "expected_results": ["邮件通知用户『证书编号为xxxx的证书将于2025-01-01到期，请知悉』", "邮件抄送项目管理员"],
    "traits": ["time_sensitive"],
    "priority": "P1",
    "source_ref": "P0477-P0483 证书到期前30天提醒功能; P0602-P0608 测量审核同款功能",
    "note": note(False, "", "", ""),
    "sub_steps": []
})

# ============================================================
# Step 4.3 角色汇总
# ============================================================
roles = [
    {"id": "R-LAB-DIR", "name": "实验室负责人", "readonly": False},
    {"id": "R-TECH", "name": "技术主管", "readonly": False},
    {"id": "R-SIGN", "name": "授权签字人", "readonly": False},
    {"id": "R-PLANNER", "name": "策划人员", "readonly": False},
    {"id": "R-PROJ-ADMIN", "name": "项目管理员", "readonly": False},
    {"id": "R-SAMPLE-MAKER", "name": "样品制备人员", "readonly": False},
    {"id": "R-SAMPLE-MGR", "name": "样品管理员", "readonly": True},
    {"id": "R-EVAL", "name": "评价人员", "readonly": False},
    {"id": "R-EVAL-LEAD", "name": "评价组长", "readonly": False},
    {"id": "R-STAT", "name": "统计人员", "readonly": True},
    {"id": "R-QUALITY", "name": "质量专员", "readonly": True},
    {"id": "R-FIN", "name": "财务管理人员", "readonly": False},
    {"id": "R-SYS-ADMIN", "name": "系统管理人员", "readonly": False},
    {"id": "R-PARTICIPANT", "name": "能力验证参加者", "readonly": False},
    {"id": "R-SUPERVISOR", "name": "监督员", "readonly": True}
]

# ============================================================
# Step 4.5 因果关系构建 -> transition_relations
# ============================================================
transition_relations = [
    {
        "from": "E-EVAL", "to": "E-PROJ",
        "desc": "评价状态推进至已确认驱动项目状态从进行中推进至报告审核中(评价完成是结果报告回收与提交审核的前置因果)",
        "trigger": "评价确认(E-EVAL.评价状态=已确认)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-003"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-003.preconditions含E-EVAL.评价状态=已确认", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-REG",
        "desc": "项目状态推进至报名中驱动参加者可创建报名记录(项目状态变更直接导致报名记录可被创建)",
        "trigger": "项目进入报名中(E-PROJ.项目状态=报名中)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-001", "T-010"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-001.expected_results含参加者可报名;T-010.preconditions含项目状态为报名中", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-REG",
        "desc": "项目状态推进至进行中驱动报名记录状态从报名成功推进至结果待提交(实施阶段开始驱动样品发放)",
        "trigger": "项目进入进行中(E-PROJ.项目状态=进行中)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-002", "T-014"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-002.expected_results含报名记录样品状态推进;T-014.preconditions含报名记录状态为报名成功", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-REG",
        "desc": "项目状态推进至报告审核中并最终已结束驱动报名记录状态从报告审核中推进至报告已发布",
        "trigger": "项目进入已结束(E-PROJ.项目状态=已结束)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-004", "T-019"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-004.expected_results含报名记录状态推进至报告已发布;T-019为对应报名记录状态推进", "", "")
    },
    {
        "from": "E-PROJ", "to": "E-ARC",
        "desc": "项目状态推进至已结束驱动归档任务可被开启(项目作为归档对象的生命周期容器，项目结束是归档任务创建的前置因果)",
        "trigger": "项目结束(E-PROJ.项目状态=已结束)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-004", "T-120"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-004.expected_results含归档任务可开启;T-120.preconditions含项目状态为已结束", "", "")
    },
    {
        "from": "E-REG", "to": "E-PAY",
        "desc": "报名记录创建驱动缴费记录可被创建(支持多次付款，缴费记录生命周期归属于报名记录)",
        "trigger": "报名记录创建(E-REG.报名记录状态=报名成功)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-011", "T-040"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-011.expected_results含报名记录状态变为报名成功;T-040.preconditions含报名记录状态为报名成功或之后", "", "")
    },
    {
        "from": "E-REG", "to": "E-CERT",
        "desc": "报名记录状态推进至报告已发布驱动证书生成并关联(报名记录作为证书的生命周期容器，报告发布是证书生成的前置因果)",
        "trigger": "报告发布(E-REG.报名记录状态=报告已发布)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-019", "T-130"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-019.expected_results含证书生成并关联报名记录;T-130.preconditions含项目状态为报告审核中", "", "")
    },
    {
        "from": "E-REG", "to": "E-TASK",
        "desc": "报名记录结果通知单/证书上传并批量提交审核驱动审核任务创建(批量提交审核为审核任务创建因果源)",
        "trigger": "批量提交审核(E-REG.报名记录状态=报告审核中)",
        "trigger_source": "action",
        "evidence_transitions": ["T-018", "T-100"],
        "rollback_propagation": True,
        "confidence": "high",
        "note": note(False, "T-018.action含批量提交审核;T-100为审核任务创建;若审核退回则报名记录需退回修改", "", "")
    },
    {
        "from": "E-REG", "to": "E-EVAL",
        "desc": "报名记录状态推进至结果已提交驱动项目评价对象进入评价阶段(评价目标为报名参加者)",
        "trigger": "结果已提交(E-REG.报名记录状态=结果已提交)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-015", "T-090"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(True, "T-015.expected_results含结果已提交;T-090.preconditions含项目已进入评价阶段。文档未显式表述结果提交驱动评价开始，但业务上评价需基于参加者结果", "", "")
    },
    {
        "from": "E-LAB", "to": "E-REG",
        "desc": "实验室审核通过(启用状态)驱动其可作为报名主体创建报名记录(实验室状态作为报名前置门禁，仅启用状态可用于报名)",
        "trigger": "实验室启用(E-LAB.审核状态=启用)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-071", "T-010"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(True, "T-071.expected_results含实验室可用于项目报名;T-010.preconditions含实验室已审核通过(E-LAB.审核状态=启用)。实验室状态变更为门禁条件，非自动因果驱动报名记录变更", "", "")
    },
    {
        "from": "E-CERT", "to": "E-MSG",
        "desc": "证书距到期30天触发邮件提醒并抄送项目管理员(时间触发因果驱动信息发送)",
        "trigger": "证书距到期30天(E-CERT.证书到期时间-当前日期=30天)",
        "trigger_source": "business_rule",
        "evidence_transitions": ["T-131"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "BR-TIME-02 证书到期前30天邮件提醒;T-131为对应转换", "", "")
    },
    {
        "from": "E-TASK", "to": "E-MSG",
        "desc": "审核任务创建驱动短信通知相关负责人(任务提醒短信)",
        "trigger": "审核任务创建(E-TASK.审核任务状态=待审核)",
        "trigger_source": "expected_results",
        "evidence_transitions": ["T-100", "T-110"],
        "rollback_propagation": False,
        "confidence": "high",
        "note": note(False, "T-100.expected_results含系统发送短信通知相关负责人", "", "")
    }
]

# ============================================================
# Step 5: 约束条件与因果关系补充
# ============================================================

# 5.1 无效转换
invalid_transitions = [
    {"id": "IT-01", "entity": "E-TESTITEM", "from": "含子项", "to": "已删除", "reason": "含有子项的记录不允许删除(P0304)"},
    {"id": "IT-02", "entity": "E-STD", "from": "停用", "to": "项目创建可选", "reason": "停用的标准库在项目创建等环节不可被选择(P0269)"},
    {"id": "IT-03", "entity": "E-LAB", "from": "非启用状态", "to": "用于项目报名", "reason": "机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名(P0185)"},
    {"id": "IT-04", "entity": "E-PROJ", "from": "已结束", "to": "消息发送", "reason": "未结束的项目可以进行消息发送(P0418)"},
    {"id": "IT-05", "entity": "E-REG", "from": "报告已发布", "to": "结果待提交", "reason": "报名记录状态不可逆向回退至结果待提交"},
    {"id": "IT-06", "entity": "E-PAY", "from": "退款金额大于缴费金额", "to": "退款成功", "reason": "退款金额不能大于当前缴费金额(P1005)"},
    {"id": "IT-07", "entity": "E-LAB", "from": "待审核", "to": "退回修改", "reason": "审核退回修改必须填写审核意见(P0211)"}
]

# 5.2 跨实体约束 XC
cross_entity = [
    {
        "id": "XC-01", "source_entity": "E-PROJ", "source_transition": "T-010",
        "source_state": "项目状态=报名中", "target_entity": "E-REG",
        "target_dimension": "报名记录状态", "target_condition": "可创建(报名待审核)",
        "desc": "镜像T-010 precondition '项目状态为报名中'：参加者仅当项目处于报名中时可提交报名"
    },
    {
        "id": "XC-02", "source_entity": "E-LAB", "source_transition": "T-010",
        "source_state": "审核状态=启用", "target_entity": "E-REG",
        "target_dimension": "报名记录状态", "target_condition": "可创建(报名待审核)",
        "desc": "镜像T-010 precondition '实验室已审核通过(E-LAB.审核状态=启用)'：仅启用状态实验室可用于项目报名"
    },
    {
        "id": "XC-03", "source_entity": "E-PROJ", "source_transition": "T-110",
        "source_state": "项目状态=待开始/报名中", "target_entity": "E-MSG",
        "target_dimension": "", "target_condition": "接收人1数据来源=所有实验室",
        "desc": "分支[项目类型=能力验证][项目状态=待开始/报名中]: 消息发送接收人1数据列表为所有实验室(P0421)"
    },
    {
        "id": "XC-04", "source_entity": "E-PROJ", "source_transition": "T-110",
        "source_state": "项目状态=进行中/报告审核中/已结束", "target_entity": "E-MSG",
        "target_dimension": "", "target_condition": "接收人1数据来源=报名实验室",
        "desc": "分支[项目类型=能力验证][项目状态=其他]: 消息发送接收人1数据列表为报名实验室(P0421)"
    },
    {
        "id": "XC-05", "source_entity": "E-PROJ", "source_transition": "T-002",
        "source_state": "样品状态=已核查", "target_entity": "E-REG",
        "target_dimension": "报名记录样品状态", "target_condition": "可推进至待收样",
        "desc": "镜像T-002 precondition '样品已核查(E-PROJ.样品状态=已核查)'：项目样品核查完成是报名记录样品状态推进的门禁"
    },
    {
        "id": "XC-06", "source_entity": "E-EVAL", "source_transition": "T-003",
        "source_state": "评价状态=已确认", "target_entity": "E-PROJ",
        "target_dimension": "项目状态", "target_condition": "可推进至报告审核中",
        "desc": "镜像T-003 precondition '评价已完成(E-EVAL.评价状态=已确认)'：评价完成是项目进入报告审核中的门禁"
    },
    {
        "id": "XC-07", "source_entity": "E-REG", "source_transition": "T-050",
        "source_state": "费用状态=已缴费", "target_entity": "E-REG",
        "target_dimension": "发票状态", "target_condition": "可推进至已开票",
        "desc": "镜像T-050 precondition '费用状态为已缴费'：缴费完成是发票开票的门禁"
    },
    {
        "id": "XC-08", "source_entity": "E-PROJ", "source_transition": "T-120",
        "source_state": "项目状态=已结束", "target_entity": "E-ARC",
        "target_dimension": "", "target_condition": "整理任务可开启",
        "desc": "镜像T-120 precondition '项目状态为已结束'：仅已结束项目可开启文件整理任务"
    },
    {
        "id": "XC-09", "source_entity": "E-REG", "source_transition": "T-130",
        "source_state": "报名记录状态=报告已发布", "target_entity": "E-CERT",
        "target_dimension": "", "target_condition": "证书已发放",
        "desc": "镜像T-130 precondition 间接含 '结果通知单已批准'：证书编制需在结果通知单批准后"
    },
    {
        "id": "XC-10", "source_entity": "E-REG", "source_transition": "T-018",
        "source_state": "报名记录状态=报告审核中", "target_entity": "E-TASK",
        "target_dimension": "审核任务状态", "target_condition": "可创建(待审核)",
        "desc": "联动: T-018 执行后 E-REG.报名记录状态 由 结果已提交 变为 报告审核中，批量提交审核驱动 E-TASK 创建"
    },
    {
        "id": "XC-11", "source_entity": "E-REG", "source_transition": "T-011",
        "source_state": "报名记录状态=报名成功", "target_entity": "E-REG",
        "target_dimension": "报名记录样品状态", "target_condition": "可推进至待发样",
        "desc": "联动: T-011 执行后 E-REG.报名记录状态 由 报名待审核 变为 报名成功，报名记录样品状态可推进至待发样"
    },
    {
        "id": "XC-12", "source_entity": "E-LAB", "source_transition": "T-071",
        "source_state": "审核状态=启用", "target_entity": "E-REG",
        "target_dimension": "报名记录状态", "target_condition": "可创建(报名待审核)",
        "desc": "由 Step 4.6 约束-因果鉴别确认：实验室状态变更为门禁条件，非自动因果驱动报名记录变更，已在 transition_relations 中以低优先级 trigger_source=expected_results 表达，此处补充 XC 条目"
    }
]

# 5.3 业务规则 BR
business_rules = [
    # validation 类
    {"id": "BR-VAL-01", "category": "validation", "desc": "标准库编号：文本输入框，必填;标准库名称：文本输入框，必填;状态：单选框，包含启用/停用两个状态，必填", "entities_involved": ["E-STD"], "severity": "mandatory", "source_ref": "P0242-P0246 新增标准库", "signal_type": "field_constraint", "note": note(False, "", "", "")},
    {"id": "BR-VAL-02", "category": "validation", "desc": "测试项标号：文本输入框，必填;名称：文本输入框，必填", "entities_involved": ["E-TESTITEM"], "severity": "mandatory", "source_ref": "P0286-P0287 新增测试项", "signal_type": "field_constraint", "note": note(False, "", "", "")},
    {"id": "BR-VAL-03", "category": "validation", "desc": "含有子项的测试项记录不允许删除;数据删除前会做前置判断，存在子项的数据不可以删除", "entities_involved": ["E-TESTITEM"], "severity": "mandatory", "source_ref": "P0304 删除测试项", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-VAL-04", "category": "validation", "desc": "实验室审核退回修改时必须填写审核意见;审核结果为通过时审核意见可以为空", "entities_involved": ["E-LAB"], "severity": "mandatory", "source_ref": "P0211-P0212 实验室审核", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-VAL-05", "category": "validation", "desc": "退款金额：文本输入框，必填，不能为大于当前缴费金额;多次退款金额做累加处理，退款金额使用红色字体且大于0时显示;实际付款=付款金额-退款金额", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P1005-P1006 缴费单退款", "signal_type": "field_constraint", "note": note(False, "", "", "")},
    {"id": "BR-VAL-06", "category": "validation", "desc": "消息发送时接收人1和接收人2不能同时为空;内容：文本输入框，必填;发送方式：选择框，必填", "entities_involved": ["E-MSG"], "severity": "mandatory", "source_ref": "P0420-P0425 优化消息发送功能", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-VAL-07", "category": "validation", "desc": "分支[项目类型=测量审核]: 消息发送接收人1为必填，数据来源于右侧实验室列表，只包含当前报名实验室;分支[项目类型=能力验证]: 接收人1为选填，项目状态为待开始/报名中时为所有实验室，其他状态为报名实验室", "entities_involved": ["E-MSG"], "severity": "conditional", "source_ref": "P0421/P0544", "signal_type": "restrictive", "note": note(False, "", "", "项目类型")},
    {"id": "BR-VAL-08", "category": "validation", "desc": "缴费时间查询参数含三个单选按钮(本月/本季/本年)和时间选择组件;发票类型：下拉列表，精确匹配，选项包括电子专票、电子普票", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P0964-P0971 缴费信息查询", "signal_type": "field_constraint", "note": note(False, "", "", "")},
    {"id": "BR-VAL-09", "category": "validation", "desc": "统计规则由一个低值、一个高值组成，判断规则为大于等于低值，小于高值", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0700 调整统计规则", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-VAL-10", "category": "validation", "desc": "项目批量操作选择列：只有已上传对应文件且未提交审核的记录才可以被选定;如没有选择记录，将提示用户选择记录信息", "entities_involved": ["E-REG"], "severity": "mandatory", "source_ref": "P0401-P0403 项目批量操作", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-VAL-11", "category": "validation", "desc": "上传文件表单：文件名称文本输入框必填;文件为文件选择框;份数/页数/备注为文本输入框", "entities_involved": ["E-ARC"], "severity": "mandatory", "source_ref": "P0363-P0367 上传文件", "signal_type": "field_constraint", "note": note(False, "", "", "")},
    {"id": "BR-VAL-12", "category": "validation", "desc": "分支[评分方式=分值/权重]: 评价项目新增表单『分值/权重』文本框必填;『说明/评分细则』文本框选填;显示顺序文本框必填", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0642-P0645 评价项目新增", "signal_type": "field_constraint", "note": note(False, "", "", "评分方式")},
    {"id": "BR-VAL-13", "category": "validation", "desc": "缴费单付款单上传：支付方式下拉选择框必填;支付账户名称文本输入框必填;汇款金额文本输入框必填，默认为项目费用金额;付款底单文件选择框必填;付款项目文本输入框只读，内容为当前报名编号", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P0461-P0466 付款录入表单", "signal_type": "field_constraint", "note": note(False, "", "", "")},
    {"id": "BR-VAL-14", "category": "validation", "desc": "标准库编号/标准库名称/实验室编号/实验室名称等模糊查询字段为文本输入框;状态下拉列表精确匹配", "entities_involved": ["E-STD", "E-LAB"], "severity": "mandatory", "source_ref": "P0197-P0202/P0232-P0237", "signal_type": "field_constraint", "note": note(False, "", "", "")},

    # authorization 类
    {"id": "BR-AUT-01", "category": "authorization", "desc": "信息发送记录只有系统管理员和项目管理员可以查看", "entities_involved": ["E-MSG"], "severity": "mandatory", "source_ref": "P0338 信息发送记录", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-AUT-02", "category": "authorization", "desc": "评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0669 协同评价", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-AUT-03", "category": "authorization", "desc": "分支[评价人员角色=评价组长]: 评价组长可在评价结果确认页面查看各评价人员的评价结果并对最终结果进行确认，可完善测试项目与评价细则、退回修改开启下一轮、保存历史、调整细则、配置统计规则;分支[评价人员角色=评价成员]: 仅能对自己的评价结果进行修改", "entities_involved": ["E-EVAL"], "severity": "conditional", "source_ref": "P0633-P0705 项目评价", "signal_type": "restrictive", "note": note(False, "", "", "评价人员角色")},
    {"id": "BR-AUT-04", "category": "authorization", "desc": "能力验证项目中固定角色在注册时系统赋予，在各项目中角色保持一致;非固定角色在项目建立时根据项目需要赋予;固定角色含实验室负责人/技术主管/项目管理员/样品管理员/系统管理人员/财务管理人员/质量专员/能力验证参加者;非固定角色含授权签字人/评价人员/监督员/样品制备人员/统计人员", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0102-P0104 角色分类", "signal_type": "restrictive", "note": note(False, "", "", "")},

    # timing 类
    {"id": "BR-TIME-01", "category": "timing", "desc": "通知公告15天内发布的通知在内容前标注new标识，超过15天后此标识自动隐藏", "entities_involved": ["E-MSG"], "severity": "mandatory", "source_ref": "P0164 通知公告", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-TIME-02", "category": "timing", "desc": "系统在每天上午9点对系统中的证书信息进行查询，如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送给项目管理员;提醒标题：证书到期提醒;提醒内容：您证书编号为xxxx的证书将于2025-01-01到期，请知悉", "entities_involved": ["E-CERT"], "severity": "mandatory", "source_ref": "P0477-P0483 证书到期前30天提醒", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-TIME-03", "category": "timing", "desc": "平台升级改造项目按照中心年度计划要求需要在2025年11月15日前完成相应的设计、开发、测试、部署、试运行等相关工作", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P1103 时间要求", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-TIME-04", "category": "timing", "desc": "性能要求：平台应支持至少300个同时在线用户数;并发100时每个页面响应时间不超过5秒;单次报名操作成功率应达到95%以上", "entities_involved": ["E-PROJ", "E-REG"], "severity": "mandatory", "source_ref": "P1079 性能要求", "signal_type": "restrictive", "note": note(False, "", "", "")},

    # notification 类
    {"id": "BR-NOT-01", "category": "notification", "desc": "操作节点增加用户短信通知：报名审核通过/退回修改、发样通知、测试结果审核通过/退回、结果通知单发布，使用短信方式通知参加者", "entities_involved": ["E-REG"], "severity": "mandatory", "source_ref": "P0493-P0503 操作节点短信通知", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-NOT-02", "category": "notification", "desc": "增加任务创建提醒：用户通过表单或审核已存在任务生成新审核任务时，系统发送短信通知相关负责人『您有一个新的xxx审核任务，请及时处理』", "entities_involved": ["E-TASK"], "severity": "mandatory", "source_ref": "P0930-P0934 增加任务提醒", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-NOT-03", "category": "notification", "desc": "证书到期前30天通过邮件方式提醒用户并抄送项目管理员", "entities_involved": ["E-CERT"], "severity": "mandatory", "source_ref": "P0477-P0483/P0602-P0608", "signal_type": "restrictive", "note": note(False, "", "", "")},

    # usability 类
    {"id": "BR-USA-01", "category": "usability", "desc": "对现有显示模块进行调整，优化待办事项显示效果并调整相关文字说明", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0174 待办事项", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-02", "category": "usability", "desc": "完善用户侧首页能力验证和测量审核统计部分内容：能力验证增加待提交结果统计内容;测量审核增加待审核统计内容", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0181 完善用户侧首页统计", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-03", "category": "usability", "desc": "项目新增表单新增监督员字段(下拉框可以为空)，导出项目通知书时填充到对应位置", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0430-P0435 项目新增表单增加监督员", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-04", "category": "usability", "desc": "项目新增表单中技术主管/实验室负责人/授权签字人字段，如备选人有且仅有一个时默认填充为备选值", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0436-P0440 默认填充", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-05", "category": "usability", "desc": "项目新建页面增加子领域常用测试项管理能力：另存常用(名称必填)、常用下拉列表复用、删除常用", "entities_involved": ["E-CATE", "E-PROJ"], "severity": "mandatory", "source_ref": "P0441-P0451 常用子领域测试项", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-06", "category": "usability", "desc": "已报名项目详情页文件下载Tab下增加预通知文件下载功能", "entities_involved": ["E-REG"], "severity": "mandatory", "source_ref": "P0470-P0475 预通知文件下载", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-07", "category": "usability", "desc": "已报名项目增加多次付款功能(不对付款金额进行校验限制)", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P0456-P0469 多次付款", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-08", "category": "usability", "desc": "项目列表增加财务备注字段，管理人员可修改备注内容", "entities_involved": ["E-PROJ", "E-PAY"], "severity": "mandatory", "source_ref": "P0976-P0984 财务备注", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-09", "category": "usability", "desc": "分支[项目类型=能力验证]: 文件整理主表含能力验证计划报名表/参加者提交的资料/结果通知单/能力验证合格证书复印件(含子表);分支[项目类型=测量审核]: 文件整理主表含参加者提交的资料(含子表)", "entities_involved": ["E-ARC"], "severity": "conditional", "source_ref": "P0376/P0530 文件整理主表", "signal_type": "usability", "note": note(False, "", "", "项目类型")},
    {"id": "BR-USA-10", "category": "usability", "desc": "测量审核结果通知单审批流程重构为单一流程，并设置流程处理人审批顺序为提交申请时签字人的选择顺序", "entities_involved": ["E-TASK"], "severity": "mandatory", "source_ref": "P0925 测量审核结果通知单审核流程优化", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-11", "category": "usability", "desc": "系统内增加电子签章位置信息，当进行签章操作时自动代入此位置信息减少手动调整操作", "entities_involved": ["E-TASK"], "severity": "mandatory", "source_ref": "P0928 预置签章位置信息", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-12", "category": "usability", "desc": "优化审核流程详情的显示效果，在页面上完整展示审核流程，并用不同的颜色对各个状态的节点进行标记", "entities_involved": ["E-TASK"], "severity": "mandatory", "source_ref": "P0951-P0952 优化流程信息展示效果", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-13", "category": "usability", "desc": "客户统计列表查询参数时间参数增加年度/季度/月度单选按钮快速录入;实验室名称列增加跳转功能可跳转至报名信息统计页面", "entities_involved": ["E-LAB"], "severity": "mandatory", "source_ref": "P0859-P0867 客户统计优化", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-14", "category": "usability", "desc": "项目总览关键指标(客户数量/项目总数/进行中的项目/未付款的客户数/业务类型分布/当年产品类型分布/当年客户类型分布/本月付款情况统计)增加数据下钻能力，点击跳转至对应统计报表", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0716-P0781 项目总览数据下钻", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-15", "category": "usability", "desc": "数据看板提供实时监控/趋势分析/区域洞察/产品类型细分四部分数据统计报表，使用图表直观展示", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0782-P0789 数据看板", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-16", "category": "usability", "desc": "强化系统安全性，对关键操作实施留痕机制，系统将自动记录操作者的身份、时间戳、操作细节及结果，生成不可篡改的审计日志", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P1029-P1030 安全性相关内容优化", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-17", "category": "usability", "desc": "优化系统显示效果，对不符合当前风格的页面进行调整，以实现更加完整和统一的视觉体验", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P1031 系统UI风格优化", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-18", "category": "usability", "desc": "对往年项目数据进行分析整理并导入到系统中为数据分析提供关键数据(历史项目模块)", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P1017-P1027 历史数据列表", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-19", "category": "usability", "desc": "完善并收集整理高频咨询问题及典型误操作场景的解决方案，为用户提供自助查询服务", "entities_involved": ["E-MSG"], "severity": "mandatory", "source_ref": "P0166-P0172 常见问题", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-20", "category": "usability", "desc": "财务管理系统修改发票上传功能支持多次分批上传;发票列表点击文件地址后的x可以移除文件(表单提交后生效)", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P0985-P0995 发票上传", "signal_type": "usability", "note": note(False, "", "", "")},
    {"id": "BR-USA-21", "category": "usability", "desc": "评价组长可点击调整细则按钮打开评价细节完善页面，配置完成后回到本页面将会刷新本页面数据", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0695 调整细则", "signal_type": "usability", "note": note(False, "", "", "")},

    # display 类
    {"id": "BR-DIS-01", "category": "display", "desc": "退款金额使用红色字体且大于0时显示", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P1001 退款金额显示", "signal_type": "display", "note": note(False, "", "", "")},
    {"id": "BR-DIS-02", "category": "display", "desc": "评价细则被标记为调整状态的评价细则将显示不同的背景颜色", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0677 评价细则调整状态显示", "signal_type": "display", "note": note(False, "", "", "")},
    {"id": "BR-DIS-03", "category": "display", "desc": "区域洞察统计报表中使用不同的颜色来标识客户数量的多少，用户将鼠标移动到不同区域时系统以信息提示框的方式显示当前区域的客户数量", "entities_involved": ["E-PROJ"], "severity": "mandatory", "source_ref": "P0788 区域洞察", "signal_type": "display", "note": note(False, "", "", "")},
    {"id": "BR-DIS-04", "category": "display", "desc": "实验室列表证明文件为链接，点击可下载相关文件;操作列为功能列下有修改/审核(待审核状态显示)/停用(启用状态显示)/启用(停用状态显示)按钮", "entities_involved": ["E-LAB"], "severity": "mandatory", "source_ref": "P0196 实验室列表", "signal_type": "display", "note": note(False, "", "", "")},
    {"id": "BR-DIS-05", "category": "display", "desc": "标准库列表操作列为功能列下有管理测试项/修改/启用/停用/删除按钮", "entities_involved": ["E-STD"], "severity": "mandatory", "source_ref": "P0231 标准库列表", "signal_type": "display", "note": note(False, "", "", "")},
    {"id": "BR-DIS-06", "category": "display", "desc": "评价页面客户列显示的是客户的实验室编码信息，有多少个客户就显示多少列;评价确认页面每组由评价人员的评价结果/参考值(各专家评分的均值)/得分组成", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0676/P0691 评价页面客户列", "signal_type": "display", "note": note(False, "", "", "")},

    # computation 类
    {"id": "BR-COM-01", "category": "computation", "desc": "实际付款=付款金额-退款金额;退款后更新项目费用为实际付款金额;多次退款金额做累加处理", "entities_involved": ["E-PAY"], "severity": "mandatory", "source_ref": "P0997-P1006 缴费单退款", "signal_type": "restrictive", "note": note(False, "", "", "")},
    {"id": "BR-COM-02", "category": "computation", "desc": "评价确认页面参考值为各专家评分的均值;得分需要评价组长填写补充", "entities_involved": ["E-EVAL"], "severity": "mandatory", "source_ref": "P0691 评价结果参考值", "signal_type": "restrictive", "note": note(False, "", "", "")}
]

# 5.4 因果补充(基于 XC/BR 数据) - 已在 transition_relations 中体现，此处无需新增

# ============================================================
# Step 6: 一致性检查与最终组装
# ============================================================
# 内部校验：所有 transition relation 的 evidence_transitions 引用的 T-XXX 必须存在
all_t_ids = {t["id"] for t in transitions}
for tr in transition_relations:
    for et in tr["evidence_transitions"]:
        assert et in all_t_ids, f"evidence_transitions {et} 不存在于 transitions"

# 校验：所有 entity 引用存在
all_e_ids = {e["id"] for e in entities}
for sr in structural_relations:
    assert sr["from"] in all_e_ids and sr["to"] in all_e_ids, f"structural_relations 引用不存在实体: {sr}"
for tr in transition_relations:
    assert tr["from"] in all_e_ids and tr["to"] in all_e_ids, f"transition_relations 引用不存在实体: {tr}"
for t in transitions:
    assert t["entity"] in all_e_ids, f"transition {t['id']} entity 不存在: {t['entity']}"

# 校验：cardinality 不出现 N:1
for sr in structural_relations:
    assert sr["cardinality"] != "N:1", f"structural_relations {sr['from']}->{sr['to']} cardinality 为 N:1，违反铁律"

# 校验：role 引用存在(除 system)
all_r_ids = {r["id"] for r in roles}
for t in transitions:
    if t["role"] != "system":
        assert t["role"] in all_r_ids, f"transition {t['id']} role 不存在: {t['role']}"

# 校验：transition_relations 的 trigger_source 合法
valid_ts = {"cross_entity", "action", "expected_results", "desc", "business_rule", "bidi_coupling"}
for tr in transition_relations:
    assert tr["trigger_source"] in valid_ts, f"trigger_source 非法: {tr['trigger_source']}"

# 新增校验12: composition 创建同步性校验 (语义校验, 替代关键词扫描)
# 对每条 composition + business_ownership 关系 A→B, 验证 B 是否满足"生命周期同步归属"判定信号:
#   ① B 是否有 from==null 的创建转换, 且该转换无独立业务前置条件(preconditions 仅引用 A 本身或为空)?
#   ② B 创建转换的 preconditions 是否引用了 A 之外实体的状态? 若引用 → 进一步判定:
#      - 若引用的是"门禁条件"(如"实验室已启用""项目状态=报名中") → 仍属 (b) 类, B 创建归属 A
#      - 若引用的是"事件触发"(如"项目状态=报告审核中""结果通知单已批准", 且 B 创建与 A 创建时间间隔大) → 实为 (c) 类, 应降级为 reference
#   ③ 是否存在"A 没有 B"的可能? 若存在 → 实为 0..1:1, 应降级为 reference
_e_by_id = {e["id"]: e for e in entities}
_t_by_entity = {}
for t in transitions:
    _t_by_entity.setdefault(t["entity"], []).append(t)

# 门禁条件 vs 事件触发 判定:
# 门禁条件: B 创建转换的 preconditions 引用 A 当前状态(如 A.状态=报名中) 或外部实体的启用状态(如 E-LAB.状态=启用)
#   → B 仍可在 A 创建后立即创建(只要门禁满足), 属 (b) 类
# 事件触发: B 创建转换的 preconditions 引用 A 的后期状态(如 A.项目状态=报告审核中/已结束) 或其他实体的事件结果
#   → B 创建与 A 创建时间间隔大, 属 (c) 类
def is_event_triggered(A, B, B_creation, entities_list):
    """判定 B 创建是否为事件触发(而非随 A 创建自动产生)"""
    pres = B_creation.get("preconditions", [])
    A_entity = _e_by_id.get(A)
    if not A_entity:
        return False
    # A 的所有状态
    A_states_all = set()
    A_initial = None
    for sd in A_entity.get("state_dimensions", []):
        A_states_all.update(sd.get("states", []))
        if sd.get("initial"):
            A_initial = sd["initial"]
    # 检查 preconditions 是否引用 A 的非 initial 状态(后期状态)
    for pre in pres:
        if A in pre:
            # 提取 A 的状态引用
            for state in A_states_all:
                if state in pre and state != A_initial:
                    # 引用 A 的后期状态 → 事件触发
                    return True
    return False

for sr in structural_relations:
    if (sr["relation_type"] == "composition" 
        and sr.get("ownership_dimension") == "business_ownership"):
        A = sr["from"]
        B = sr["to"]
        # 找 B 的创建转换 (from==null)
        B_creation = None
        for t in _t_by_entity.get(B, []):
            if t.get("from") is None:
                B_creation = t
                break
        if B_creation:
            # 判定: B 创建是否为事件触发(引用 A 的后期状态)
            if is_event_triggered(A, B, B_creation, entities):
                raise AssertionError(
                    f"composition 创建同步性校验失败: {A}->{B} B创建转换{B_creation['id']} "
                    f"preconditions 引用 A 的后期状态, 实为事件触发, 应降级为 reference")

# 新增校验13: 终态语义校验 (铁律10)
for t in transitions:
    e = _e_by_id.get(t["entity"])
    if e and t.get("dimension"):
        for sd in e.get("state_dimensions", []):
            if sd["dimension_name"] == t["dimension"]:
                terminal = sd.get("terminal", [])
                # from 不得为终态
                if t.get("from") in terminal:
                    raise AssertionError(
                        f"终态语义校验失败: {t['id']} from={t['from']}(终态), 终态不应有出边")
                # 终态→终态转换异常
                if t.get("from") in terminal and t.get("to") in terminal:
                    raise AssertionError(
                        f"终态→终态转换异常: {t['id']} from={t['from']}(终态) to={t['to']}(终态)")
                break

# 校验：bidi_coupling 时 structural 中确有反向 A->B
for tr in transition_relations:
    if tr["trigger_source"] == "bidi_coupling":
        # 检查是否存在 structural tr.to -> tr.from (父->子)
        found = any(sr["from"] == tr["to"] and sr["to"] == tr["from"] for sr in structural_relations)
        assert found, f"bidi_coupling {tr['from']}->{tr['to']} 在 structural 中未找到反向 {tr['to']}->{tr['from']}"

# JSON 字符安全验证：扫描残留 Unicode 箭头/弯引号
def safety_check(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            safety_check(v)
    elif isinstance(obj, list):
        for x in obj:
            safety_check(x)
    elif isinstance(obj, str):
        for bad in ["\u2192", "\u2190", "\u2191", "\u2193", "\u201c", "\u201d", "\u2018", "\u2019"]:
            if bad in obj:
                raise AssertionError(f"字符串含禁止字符: {repr(bad)} in {obj[:80]}")

safety_check({
    "entities": entities,
    "structural_relations": structural_relations,
    "transition_relations": transition_relations,
    "transitions": transitions,
    "cross_entity": cross_entity,
    "business_rules": business_rules,
    "invalid_transitions": invalid_transitions,
    "meta": meta
})

# 组装最终 JSON
final = {
    "_meta": meta,
    "domain_model": {
        "entities": entities,
        "roles": roles,
        "structural_relations": structural_relations,
        "transition_relations": transition_relations
    },
    "state_and_flow": {
        "transitions": transitions
    },
    "constraints": {
        "invalid_transitions": invalid_transitions,
        "cross_entity": cross_entity,
        "business_rules": business_rules
    }
}

# 写入文件
out_path = "/home/z/my-project/download/structured_analysis.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

print(f"OK - 写入 {out_path}")
print(f"实体数: {len(entities)}")
print(f"角色数: {len(roles)}")
print(f"结构关系数: {len(structural_relations)}")
print(f"因果关系数: {len(transition_relations)}")
print(f"转换数: {len(transitions)}")
print(f"无效转换数: {len(invalid_transitions)}")
print(f"跨实体约束数: {len(cross_entity)}")
print(f"业务规则数: {len(business_rules)}")
print(f"分支维度数: {len(branch_dimensions)}")
