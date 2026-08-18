"""网数中心能力验证服务平台升级维护项目 需求数据。"""
from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    # ── 标签分配表 ──
    # 实体: E-XM(验证项目) | E-BMJL(报名记录) | E-SYS(实验室) | E-BZK(标准库) | E-CSX(测试项) | E-ZLY(子领域) | E-ZS(证书) | E-XX(信息发送记录) | E-JFD(缴费记录) | E-LSPJ(历史项目)
    # 转换:
    #   E-XM.项目状态: t01(→待开始) | t02(待开始→报名中) | t03(报名中→进行中) | t04(进行中→报告审核中) | t05(报告审核中→已结束)
    #   E-XM.样品状态: t06(→待核查) | t07(待核查→已核查)
    #   E-BMJL.报名记录状态: t08(→报名待审核) | t09(报名待审核→报名退回) | t10(报名待审核→报名成功) | t11(报名待审核→已撤销) | t12(报名成功→结果待提交) | t13(结果待提交→结果已提交) | t14(结果已提交→结果退回修改) | t15(结果已提交→报告/证书审核中) | t16(报告/证书审核中→报告/证书已发布)
    #   E-BMJL.通知状态: t17(→未发送) | t18(未发送→待确认)
    #   E-BMJL.报名记录样品状态: t19(→待发样) | t20(待发样→待收样) | t21(待收样→已收样) | t22(已收样→已确认)
    #   E-BMJL.费用状态: t23(→待缴费) | t24(待缴费→已缴费)
    #   E-BMJL.发票状态: t25(→待开票) | t26(待开票→已开票)
    #   E-SYS.状态: t27(→待审核) | t28(待审核→启用) | t29(待审核→已退回) | t30(启用→停用) | t31(停用→启用) | t32(已退回→待审核)
    #   E-BZK.状态: t33(→启用) | t34(启用→停用) | t35(停用→启用)
    # XC: x01-x04, x07
    # BR: b01-b18
    # IT: (无)
    # 角色: r01(实验室负责人) | r02(技术主管) | r03(授权签字人) | r04(策划人员) | r05(项目管理员) | r06(样品制备人员) | r07(样品管理员) | r08(评价人员) | r09(统计人员) | r10(质量专员) | r11(财务管理人员) | r12(系统管理人员) | r13(能力验证参加者) | r14(监督员)
    # 分支维度: 项目类型@E-XM | 评分方式@E-XM
    m = DomainModel(
        source="网数中心能力验证服务平台升级维护项目-需求分析与设计1116_2089153243181768704.md",
        document_scope="网数中心能力验证服务平台升级维护项目需求分析与设计文档，覆盖系统功能架构、用户角色、业务流程（能力验证提供者/参加者、测量审核提供者/参加者）、项目状态分析、各功能模块（首页、基本信息、系统管理、能力验证、测量审核、项目评价、统计分析、业务审核、财务管理、其他）需求",
    )

    # === Step 0: 动词种子词表 ===
    m.set_prohibition_config(config={
        "action_verbs": [
            "新增", "修改", "删除", "查询", "重置", "审核", "退回", "通过", "批准",
            "提交", "保存", "上传", "下载", "导入", "导出", "发送", "发放", "发布",
            "停用", "启用", "归档", "确认", "撤销", "选入", "登录", "退出", "编辑",
            "查看", "分配", "评价", "统计", "分析", "申请", "报名", "缴费", "退款",
            "开票", "签发", "盖章", "签字", "进入", "执行", "整理", "打印", "抄送",
            "提醒", "完善", "调整", "领用", "核查", "发样", "还样", "选中", "选定",
        ],
        "prohibit_keywords": [
            "不能同时为空",
            "不允许删除",
            "不可以删除",
            "不可被选择",
            "不能为大于当前缴费金额",
            "未结束的项目可以进行消息发送",
            "只能新增一级测试项目",
            "不可以编辑",
            "只有系统管理员和项目管理员可以查看",
            "不能查看和修改其他评价人员的评价结果",
            "含有子项的记录不允许删除",
            "存在子项的数据不可以删除",
            "15天内发布的通知在内容前标注new标识",
            "超过15天后此标识自动隐藏",
            "评价人员只能对自己的评价结果进行修改",
        ],
    })

    # === Step 0.5: 角色与权限 ===
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

    m.add_permission(role="系统管理人员", operations=["系统登录", "用户管理", "角色管理", "内容管理", "查询实验室", "查询标准库", "查询子领域", "查询信息发送记录", "查询用户", "查询角色"])
    m.add_permission(role="项目管理员", operations=["系统登录", "查询项目", "查询报名信息", "查询信息发送记录", "查询实验室", "查询标准库", "查询子领域", "查询历史项目"])
    m.add_permission(role="能力验证参加者", operations=["系统登录", "查询项目", "查询报名信息", "下载文件", "上传附件"])
    m.add_permission(role="技术主管", operations=["系统登录", "查询项目", "查询报名信息"])
    m.add_permission(role="实验室负责人", operations=["系统登录", "查询项目", "查询报名信息"])
    m.add_permission(role="授权签字人", operations=["系统登录", "查询项目", "查询报名信息"])
    m.add_permission(role="策划人员", operations=["系统登录", "查询项目", "查询报名信息"])
    m.add_permission(role="评价人员", operations=["系统登录", "查询项目", "查询报名信息"])
    m.add_permission(role="样品管理员", operations=["系统登录", "查询项目", "查询样品"])
    m.add_permission(role="样品制备人员", operations=["系统登录", "查询项目", "查询样品"])
    m.add_permission(role="统计人员", operations=["系统登录", "查询项目"])
    m.add_permission(role="质量专员", operations=["系统登录", "查询项目", "查询报告"])
    m.add_permission(role="财务管理人员", operations=["系统登录", "查询项目", "查询缴费", "查询发票"])
    m.add_permission(role="监督员", operations=["系统登录", "查询项目"])

    # === Step 1: 实体 ===

    # --- E-XM: 验证项目 ---
    m.add_entity(
        id="E-XM",
        name="验证项目",
        desc="能力验证/测量审核项目，承载项目全生命周期信息，含项目状态和样品状态两个维度",
        type="core",
        tags=["multi-state", "approvable", "collaborative", "configurable"],
        attributes=[
            attr(name="项目编号", desc="文本；系统生成；唯一"),
            attr(name="项目名称", desc="文本；必填"),
            attr(name="产品类型", desc="下拉；必填；来源于系统产品类型字典"),
            attr(name="项目类型", desc="单选；必填；能力验证/测量审核", is_config=True),
            attr(name="所属年度", desc="时间；必填"),
            attr(name="项目费用", desc="数值；必填；退款后更新为实际付款金额"),
            attr(name="技术主管", desc="下拉；项目新增时若备选人唯一则默认填充"),
            attr(name="实验室负责人", desc="下拉；项目新增时若备选人唯一则默认填充"),
            attr(name="授权签字人", desc="下拉；项目新增时若备选人唯一则默认填充"),
            attr(name="监督员", desc="下拉；选填；项目新增表单新增字段；导出项目通知书时填充"),
            attr(name="评价人员", desc="下拉；多选；首个被选评价人员默认为评价组长"),
            attr(name="评分方式", desc="单选；必填；分值/权重", is_config=True),
            attr(name="及格分", desc="数值；评价确认页面填写；其余字段不可编辑"),
            attr(name="财务备注", desc="文本；选填；项目列表新增字段；管理人员可修改"),
            attr(name="子领域", desc="下拉；必填；关联E-ZLY"),
            attr(name="依据标准", desc="文本；选填"),
        ],
        state_dimensions=[
            {
                "dimension_name": "项目状态",
                "states": ["待开始", "报名中", "进行中", "报告审核中", "已结束"],
                "initial": "待开始",
                "terminal": ["已结束"],
                "note": {"comment": "原文19.3项目状态分析：待开始、报名中、进行中、报告审核中、已结束"},
            },
            {
                "dimension_name": "样品状态",
                "states": ["待核查", "已核查"],
                "initial": "待核查",
                "terminal": ["已核查"],
                "note": {"comment": "原文19.3验证项目状态子状态类型：样品状态"},
            },
        ],
        operations=[
            op(name="项目列表查询", category="query",
               expected_results=["分页展示符合条件的项目列表"],
               source_ref="20.5.1",
               note=N(role="项目管理员", comment="通用查询操作")),
            op(name="新增项目", category="crud",
               expected_results=["新增一条项目记录，项目状态为待开始"],
               source_ref="20.5.1.5；20.5.1.6",
               note=N(role="项目管理员", comment="对应转换 t01；新增表单含监督员字段；技术主管/实验室负责人/授权签字人备选唯一时默认填充")),
            op(name="修改项目", category="crud",
               expected_results=["修改项目信息并保存"],
               source_ref="20.5.1",
               note=N(role="项目管理员", comment="crud操作")),
            op(name="删除项目", category="crud",
               expected_results=["删除项目记录"],
               source_ref="20.2.3",
               note=N(role="项目管理员", comment="管理侧待办事项含能力验证项目删除")),
            op(name="项目详情查看", category="query",
               expected_results=["展示项目详情页"],
               source_ref="20.5.2.1",
               note=N(role="项目管理员", comment="通用查询操作")),
            op(name="文件整理", category="crud",
               expected_results=["归档任务已开启，请稍后查看；完成后显示查看归档按钮"],
               source_ref="20.5.1.1",
               note=N(role="项目管理员", comment="仅已结束项目可执行；归档子流程入口")),
            op(name="代码导入", category="file",
               expected_results=["导入报名机构三方代码"],
               source_ref="20.5.1.2",
               note=N(role="项目管理员", comment="文件上传操作")),
            op(name="批量处理", category="crud",
               expected_results=["跳转报名信息批量处理页面；批量上传结果通知单/证书；批量提交审核"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="批量操作入口")),
            op(name="消息发送", category="crud",
               expected_results=["按选择方式发送消息；接收人1和接收人2不能同时为空"],
               source_ref="20.5.1.4",
               note=N(role="项目管理员", comment="仅未结束项目可执行；详情页入口")),
            op(name="导出项目通知书", category="file",
               expected_results=["导出项目通知书；含监督员字段填充"],
               source_ref="20.5.1.5",
               note=N(role="项目管理员", comment="文件导出")),
            op(name="另存常用测试项", category="crud",
               expected_results=["将当前测试项组合保存为常用项"],
               source_ref="20.5.1.7",
               note=N(role="项目管理员", comment="项目新增表单内常用项管理")),
            op(name="归档文件上传", category="file",
               expected_results=["上传归档文件；项目阶段为其它"],
               source_ref="20.5.1.1",
               note=N(role="项目管理员", comment="归档页面文件上传")),
            op(name="归档文件打包下载", category="file",
               expected_results=["下载zip格式归档文件，含清单文件及按项目阶段命名的目录"],
               source_ref="20.5.1.1",
               note=N(role="项目管理员", comment="归档文件打包下载")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.5.1",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-BMJL: 报名记录 ---
    m.add_entity(
        id="E-BMJL",
        name="报名记录",
        desc="参加者报名能力验证/测量审核项目的记录，承载报名全流程多维度状态（报名记录状态、通知状态、报名记录样品状态、费用状态、发票状态）",
        type="core",
        tags=["multi-state", "approvable", "collaborative"],
        attributes=[
            attr(name="报名编号", desc="文本；系统生成；唯一"),
            attr(name="项目编号", desc="文本；关联E-XM；必填"),
            attr(name="实验室", desc="下拉；关联E-SYS；必填"),
            attr(name="统一社会信用代码", desc="文本；来自实验室"),
            attr(name="报名时间", desc="时间；系统记录"),
            attr(name="机构代码", desc="文本；项目管理员导入"),
            attr(name="评价得分", desc="数值；评价完成后填入"),
            attr(name="评价结果", desc="文本；评价完成后填入"),
            attr(name="退款金额", desc="数值；多次退款累加；红色字体且大于0时显示"),
            attr(name="实际付款", desc="数值；付款金额-退款金额"),
            attr(name="管理备注", desc="文本；选填；记录退款原因等"),
            attr(name="行政区划", desc="文本；来自实验室"),
        ],
        state_dimensions=[
            {
                "dimension_name": "报名记录状态",
                "states": ["报名待审核", "报名退回", "报名成功", "结果待提交", "结果已提交", "结果退回修改", "报告/证书审核中", "报告/证书已发布", "已撤销"],
                "initial": "报名待审核",
                "terminal": ["报告/证书已发布", "已撤销"],
                "note": {"comment": "原文19.3报名记录状态子状态类型：报名记录状态"},
            },
            {
                "dimension_name": "通知状态",
                "states": ["未发送", "待确认", "待审核", "退回", "已审核", "已批准"],
                "initial": "未发送",
                "terminal": ["已批准"],
                "note": {"comment": "原文19.3报名记录状态子状态类型：通知状态；§19.1/19.2表中称预通知状态"},
            },
            {
                "dimension_name": "报名记录样品状态",
                "states": ["待发样", "待收样", "已收样", "已确认"],
                "initial": "待发样",
                "terminal": ["已确认"],
                "note": {"comment": "原文19.3报名记录状态子状态类型：报名记录样品状态"},
            },
            {
                "dimension_name": "费用状态",
                "states": ["待缴费", "已缴费"],
                "initial": "待缴费",
                "terminal": ["已缴费"],
                "note": {"comment": "原文19.3报名记录状态子状态类型：费用状态"},
            },
            {
                "dimension_name": "发票状态",
                "states": ["待开票", "已开票"],
                "initial": "待开票",
                "terminal": ["已开票"],
                "note": {"comment": "原文19.3报名记录状态子状态类型：发票状态"},
            },
        ],
        operations=[
            op(name="报名", category="crud",
               expected_results=["新增一条报名记录，状态为报名待审核"],
               source_ref="19.4；20.5",
               note=N(role="能力验证参加者", comment="对应转换 t08")),
            op(name="报名审核", category="crud",
               expected_results=["通过：报名信息审核通过；退回修改：报名信息审核未通过"],
               source_ref="20.5.3.2",
               note=N(role="项目管理员", comment="对应转换 t09/t10；操作后短信通知用户")),
            op(name="撤销报名", category="crud",
               expected_results=["报名记录状态变为已撤销"],
               source_ref="19.3",
               note=N(role="能力验证参加者", comment="对应转换 t11")),
            op(name="上传付款单", category="crud",
               expected_results=["新增一条缴费记录；费用状态变为已缴费；支持多次付款不对金额校验"],
               source_ref="20.5.2.1",
               note=N(role="能力验证参加者", comment="对应转换 t24；可多次付款")),
            op(name="上传测试结果", category="crud",
               expected_results=["报名记录状态变为结果已提交"],
               source_ref="19.4；20.5",
               note=N(role="能力验证参加者", comment="对应转换 t13")),
            op(name="结果审核", category="crud",
               expected_results=["通过：测试报告审核通过；退回：测试报告审核未通过"],
               source_ref="20.5.3.2",
               note=N(role="技术主管", comment="对应转换 t14/t15；操作后短信通知用户")),
            op(name="发放结果通知单", category="crud",
               expected_results=["报名记录状态变为报告/证书已发布；短信通知用户结果通知单已发布"],
               source_ref="19.1；20.5.3.2",
               note=N(role="项目管理员", comment="对应转换 t16")),
            op(name="发放证书", category="crud",
               expected_results=["证书发放给参加者；报名记录状态为报告/证书已发布"],
               source_ref="19.1",
               note=N(role="项目管理员", comment="对应转换 t16")),
            op(name="发样通知", category="crud",
               expected_results=["样品已发出；短信通知用户样品已发出"],
               source_ref="20.5.3.2",
               note=N(role="项目管理员", comment="对应报名记录样品状态推进")),
            op(name="报名信息列表查询", category="query",
               expected_results=["分页展示符合条件的数据"],
               source_ref="20.5.3",
               note=N(role="项目管理员", comment="通用查询操作")),
            op(name="报名详情查看", category="query",
               expected_results=["展示报名详情页"],
               source_ref="20.5.2.1",
               note=N(role="能力验证参加者", comment="通用查询操作")),
            op(name="预通知文件下载", category="file",
               expected_results=["下载预通知文件"],
               source_ref="20.5.2.2；20.5.3.1",
               note=N(role="能力验证参加者", comment="文件下载Tab下")),
            op(name="结果通知单上传", category="file",
               expected_results=["上传结果通知单文件"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="批量处理页面操作")),
            op(name="证书上传", category="file",
               expected_results=["上传证书文件"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="批量处理页面操作")),
            op(name="提交审核", category="crud",
               expected_results=["对选择记录进行任务提交操作；如未选择记录则提示用户"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="批量处理页面操作；仅已上传文件且未提交审核的记录可选")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.5.3",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-SYS: 实验室 ---
    m.add_entity(
        id="E-SYS",
        name="实验室",
        desc="机构实验室信息，新增/修改后需经管理用户审核通过方可用于项目报名",
        type="managed",
        tags=["approvable"],
        attributes=[
            attr(name="实验室编号", desc="文本；模糊查询"),
            attr(name="实验室名称", desc="文本；必填；模糊查询"),
            attr(name="统一社会信用代码", desc="文本；必填"),
            attr(name="法人名称", desc="文本"),
            attr(name="企业类型", desc="下拉"),
            attr(name="企业规模", desc="下拉"),
            attr(name="CNAS", desc="布尔；已获CNAS认可"),
            attr(name="CNAS证书号", desc="文本"),
            attr(name="CMA", desc="布尔；已获CMA认可"),
            attr(name="CMA证书编号", desc="文本"),
            attr(name="联系人", desc="文本"),
            attr(name="联系电话", desc="文本"),
            attr(name="邮箱", desc="文本"),
            attr(name="座机号码", desc="文本"),
            attr(name="行政区域", desc="下拉"),
            attr(name="详细地址", desc="文本"),
            attr(name="默认实验室", desc="布尔"),
            attr(name="证明文件", desc="文件；上传营业执照或其他证书材料"),
        ],
        state_dimensions=[
            {
                "dimension_name": "状态",
                "states": ["待审核", "启用", "停用", "已退回"],
                "initial": "待审核",
                "terminal": [],
                "note": {"comment": "原文20.3.1状态字段：待审核、启用、停用、退回修改；20.4.1.2审核退回修改时状态变更为'已退回'"},
            },
        ],
        operations=[
            op(name="实验室列表查询", category="query",
               expected_results=["分页展示符合条件的实验室列表"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员", comment="通用查询操作")),
            op(name="新增实验室", category="crud",
               expected_results=["新增实验室记录，状态为待审核"],
               source_ref="20.3.1；20.4.1",
               note=N(role="能力验证参加者", comment="机构新增；对应转换 t27")),
            op(name="修改实验室", category="crud",
               expected_results=["修改实验室信息；状态变为待审核"],
               source_ref="20.4.1.3",
               note=N(role="能力验证参加者", comment="机构修改后需重新审核")),
            op(name="删除实验室", category="crud",
               expected_results=["删除实验室记录"],
               source_ref="20.3.1",
               note=N(role="能力验证参加者", comment="机构操作")),
            op(name="实验室审核", category="crud",
               expected_results=["通过：状态变为启用，生成数据快照；退回修改：状态变为已退回，需填审核意见"],
               source_ref="20.4.1.2",
               note=N(role="系统管理人员", comment="对应转换 t28/t29")),
            op(name="停用实验室", category="crud",
               expected_results=["状态由启用变为停用"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员", comment="对应转换 t30")),
            op(name="启用实验室", category="crud",
               expected_results=["状态由停用变为启用"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员", comment="对应转换 t31")),
            op(name="证明文件下载", category="file",
               expected_results=["下载实验室证明文件"],
               source_ref="20.4.1.1",
               note=N(role="系统管理人员", comment="证明文件为链接，点击可下载")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.4.1.1",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-BZK: 标准库 ---
    m.add_entity(
        id="E-BZK",
        name="标准库",
        desc="标准库基础数据及其下属测试项和参数的全生命周期管理；为系统中各类实验和项目提供准确的数据基础",
        type="managed",
        tags=["configurable"],
        attributes=[
            attr(name="标准库编号", desc="文本；必填；模糊查询"),
            attr(name="标准库名称", desc="文本；必填；模糊查询"),
            attr(name="状态", desc="单选；必填；启用/停用"),
            attr(name="描述", desc="文本；选填"),
            attr(name="创建时间", desc="时间；系统记录"),
        ],
        state_dimensions=[
            {
                "dimension_name": "状态",
                "states": ["启用", "停用"],
                "initial": "启用",
                "terminal": [],
                "note": {"comment": "原文20.4.2.1标准库状态：启用/停用；20.4.2.5停用的标准库在项目创建等环节不可被选择"},
            },
        ],
        operations=[
            op(name="标准库列表查询", category="query",
               expected_results=["分页展示符合条件的数据"],
               source_ref="20.4.2.1",
               note=N(role="系统管理人员", comment="通用查询操作")),
            op(name="新增标准库", category="crud",
               expected_results=["新增一条标准库记录，状态为启用"],
               source_ref="20.4.2.2",
               note=N(role="系统管理人员", comment="对应转换 t33")),
            op(name="修改标准库", category="crud",
               expected_results=["修改标准库信息并保存"],
               source_ref="20.4.2.3",
               note=N(role="系统管理人员", comment="crud操作")),
            op(name="删除标准库", category="crud",
               expected_results=["删除标准库记录；二次确认"],
               source_ref="20.4.2.4",
               note=N(role="系统管理人员", comment="crud操作")),
            op(name="停用标准库", category="crud",
               expected_results=["状态由启用变为停用；二次确认"],
               source_ref="20.4.2.5",
               note=N(role="系统管理人员", comment="对应转换 t34")),
            op(name="启用标准库", category="crud",
               expected_results=["状态由停用变为启用；二次确认"],
               source_ref="20.4.2.5",
               note=N(role="系统管理人员", comment="对应转换 t35")),
            op(name="管理测试项", category="ui",
               expected_results=["跳转或新开标签页进入该标准库的测试项管理界面"],
               source_ref="20.4.2.6",
               note=N(role="系统管理人员", comment="UI导航操作")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.4.2.1",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-CSX: 测试项 ---
    m.add_entity(
        id="E-CSX",
        name="测试项",
        desc="标准库下的测试项，可层级嵌套；测试项由编号和名称组成，测试项下可以有子测试项",
        type="managed",
        tags=[],
        attributes=[
            attr(name="标号", desc="文本；必填"),
            attr(name="名称", desc="文本；必填"),
            attr(name="父测试项", desc="关联E-CSX；选填；用于层级嵌套"),
            attr(name="所属标准库", desc="关联E-BZK；必填"),
        ],
        operations=[
            op(name="测试项列表查询", category="query",
               expected_results=["以嵌套表格或树形表格展示该标准库下所有测试项"],
               source_ref="20.4.2.7",
               note=N(role="系统管理人员", comment="通用查询操作")),
            op(name="新增测试项", category="crud",
               expected_results=["新增一条测试项记录；刷新列表"],
               source_ref="20.4.2.8",
               note=N(role="系统管理人员", comment="crud操作")),
            op(name="修改测试项", category="crud",
               expected_results=["修改测试项信息；刷新列表"],
               source_ref="20.4.2.9",
               note=N(role="系统管理人员", comment="crud操作")),
            op(name="删除测试项", category="crud",
               expected_results=["删除测试项；含有子项的记录不允许删除"],
               source_ref="20.4.2.10",
               note=N(role="系统管理人员", comment="crud操作")),
        ],
    )

    # --- E-ZLY: 子领域 ---
    m.add_entity(
        id="E-ZLY",
        name="子领域",
        desc="子领域基础数据，其测试项由原表单方式变更为从标准库选择方式",
        type="managed",
        tags=[],
        attributes=[
            attr(name="子领域名称", desc="文本；必填"),
            attr(name="子领域编码", desc="文本；必填；唯一"),
        ],
        operations=[
            op(name="子领域列表查询", category="query",
               expected_results=["分页展示符合条件的子领域列表"],
               source_ref="20.4.3.2",
               note=N(role="系统管理人员", comment="通用查询操作")),
            op(name="进入子领域测试项管理", category="ui",
               expected_results=["跳转或新开标签页进入该子领域的测试项管理界面"],
               source_ref="20.4.3.1",
               note=N(role="系统管理人员", comment="UI导航操作")),
            op(name="子领域新增测试项", category="crud",
               expected_results=["选择标准库及测试项后保存；新标准库出现在列表中"],
               source_ref="20.4.3.3",
               note=N(role="系统管理人员", comment="crud操作；选择数据来源于标准库")),
            op(name="子领域删除测试项", category="crud",
               expected_results=["删除测试项；存在子项的数据不可以删除"],
               source_ref="20.4.3.4",
               note=N(role="系统管理人员", comment="crud操作")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.4.3.2",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-ZS: 证书 ---
    m.add_entity(
        id="E-ZS",
        name="证书",
        desc="能力验证合格证书，由项目管理员编制、技术主管审核、实验室负责人批准；含证书到期提醒",
        type="managed",
        tags=["expirable"],
        attributes=[
            attr(name="证书编号", desc="文本；系统生成；唯一"),
            attr(name="关联报名记录", desc="关联E-BMJL；必填"),
            attr(name="关联项目", desc="关联E-XM；必填"),
            attr(name="到期时间", desc="时间；用于到期前30天邮件提醒"),
            attr(name="证书文件", desc="文件；PDF格式"),
        ],
        operations=[
            op(name="证书列表查询", category="query",
               expected_results=["分页展示符合条件的证书列表"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="通用查询操作")),
            op(name="证书上传", category="file",
               expected_results=["上传证书文件"],
               source_ref="20.5.1.3",
               note=N(role="项目管理员", comment="文件上传操作；批量处理页面")),
            op(name="证书下载", category="file",
               expected_results=["下载证书文件"],
               source_ref="20.5.2.1",
               note=N(role="能力验证参加者", comment="文件下载")),
        ],
    )

    # --- E-XX: 信息发送记录 ---
    m.add_entity(
        id="E-XX",
        name="信息发送记录",
        desc="系统中的信息发送历史记录，仅系统管理员和项目管理员可以查看",
        type="managed",
        tags=[],
        attributes=[
            attr(name="接收号码", desc="文本；模糊匹配"),
            attr(name="发送方式", desc="下拉；短信/邮件/站内信"),
            attr(name="发送时间", desc="时间；范围匹配"),
            attr(name="发送人", desc="文本"),
            attr(name="消息标题", desc="文本"),
            attr(name="消息内容", desc="文本"),
            attr(name="发送结果", desc="文本"),
        ],
        operations=[
            op(name="信息发送记录列表查询", category="query",
               expected_results=["分页展示符合条件的数据"],
               source_ref="20.4.4.1",
               note=N(role=["系统管理人员", "项目管理员"], comment="仅系统管理员和项目管理员可查看")),
            op(name="消息详情查看", category="query",
               expected_results=["查看消息详细内容"],
               source_ref="20.4.4.1",
               note=N(role=["系统管理人员", "项目管理员"], comment="通用查询操作")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.4.4.1",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-JFD: 缴费记录 ---
    m.add_entity(
        id="E-JFD",
        name="缴费记录",
        desc="项目报名的缴费记录，支持多次分批上传；含退款功能；退款后更新项目费用为实际付款金额",
        type="managed",
        tags=[],
        attributes=[
            attr(name="关联报名记录", desc="关联E-BMJL；必填"),
            attr(name="支付方式", desc="下拉；必填"),
            attr(name="支付账户名称", desc="文本；必填"),
            attr(name="汇款金额", desc="数值；必填；默认为项目费用金额"),
            attr(name="付款底单", desc="文件；必填"),
            attr(name="付款项目", desc="文本；只读；内容为当前报名编号"),
            attr(name="备注", desc="文本；选填"),
            attr(name="缴费时间", desc="时间；系统记录"),
            attr(name="到款日期", desc="时间"),
            attr(name="开票时间", desc="时间；最后一次开票时间"),
            attr(name="退款金额", desc="数值；多次退款累加；红色字体且大于0时显示"),
            attr(name="实际付款", desc="数值；付款金额-退款金额"),
            attr(name="管理备注", desc="文本；选填；记录退款原因等"),
        ],
        operations=[
            op(name="缴费记录列表查询", category="query",
               expected_results=["分页展示符合条件的数据；含退款金额、实际付款、管理备注列"],
               source_ref="20.10.2.3",
               note=N(role="财务管理人员", comment="通用查询操作")),
            op(name="上传付款单", category="crud",
               expected_results=["新增一条缴费记录；支持多次分批上传"],
               source_ref="20.5.2.1；20.10.2.2",
               note=N(role="能力验证参加者", comment="crud操作")),
            op(name="发票上传", category="file",
               expected_results=["上传发票文件；支持多次分批上传；表单提交后生效"],
               source_ref="20.10.2.2",
               note=N(role="财务管理人员", comment="文件上传操作")),
            op(name="修改财务备注", category="crud",
               expected_results=["修改项目财务备注内容"],
               source_ref="20.10.2.1",
               note=N(role="财务管理人员", comment="crud操作")),
            op(name="缴费单退款", category="crud",
               expected_results=["新增退款记录；退款金额累加；更新项目费用为实际付款金额"],
               source_ref="20.10.2.3",
               note=N(role="财务管理人员", comment="退款金额不能大于当前缴费金额")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.10.2.3",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # --- E-LSPJ: 历史项目 ---
    m.add_entity(
        id="E-LSPJ",
        name="历史项目",
        desc="往年项目数据，已分析整理并导入到系统中为数据分析提供关键数据",
        type="managed",
        tags=[],
        attributes=[
            attr(name="项目编号", desc="文本"),
            attr(name="项目名称", desc="文本；模糊匹配"),
            attr(name="子领域", desc="文本；模糊匹配"),
            attr(name="项目类型", desc="下拉；能力验证/测量审核"),
            attr(name="项目管理员", desc="文本"),
            attr(name="所属年度", desc="文本；精确匹配"),
            attr(name="统一社会信息代码", desc="文本"),
            attr(name="实验室名称", desc="文本"),
            attr(name="企业类型", desc="文本"),
            attr(name="企业规模", desc="文本"),
            attr(name="法人名称", desc="文本"),
            attr(name="联系人", desc="文本"),
            attr(name="联系电话", desc="文本"),
            attr(name="报告时间", desc="时间"),
            attr(name="证书时间", desc="时间"),
            attr(name="证书编号", desc="文本"),
            attr(name="评价结果", desc="文本"),
            attr(name="项目费用", desc="数值"),
        ],
        operations=[
            op(name="历史项目列表查询", category="query",
               expected_results=["分页展示符合条件的历史项目列表"],
               source_ref="20.11.1.1",
               note=N(role="项目管理员", comment="通用查询操作")),
            op(name="重置查询", category="ui",
               expected_results=["清空查询条件并展示所有数据"],
               source_ref="20.11.1.1",
               note=N(role="system", comment="通用UI操作；框架行为")),
        ],
    )

    # === Step 2: 结构关系 ===

    # E-XM → E-BMJL：项目拥有报名记录（B 有独立创建流程，B 是 core 流程实体，A 为其业务归属容器）
    m.add_structural(
        frm="E-XM", to="E-BMJL",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="能力验证/测量审核项目拥有多条报名记录；报名记录的归属字段继承自项目；项目为报名记录的业务归属容器",
        confidence="high",
        note={"comment": "四元分类判(c)：B有独立创建流程、B为core、A为业务归属容器；项目编号继承、生命周期挂靠项目侧管理"},
    )

    # E-BZK → E-CSX：标准库拥有测试项（B 无独立于标准库的创建流程，A 创建时 B 自动入）
    m.add_structural(
        frm="E-BZK", to="E-CSX",
        relation_type="composition", cardinality="1:N",
        ownership_dimension="business_ownership",
        desc="标准库下管理测试项及子测试项；测试项生命周期挂靠标准库",
        confidence="high",
        note={"comment": "四元分类判(b)：B无独立创建流程(测试项只能在标准库下新增)、共享操作主体；20.4.2.6管理测试项入口"},
    )

    # E-ZLY → E-CSX：子领域引用标准库的测试项（A 为 B 提供配置/分类，B 独立创建）
    m.add_structural(
        frm="E-ZLY", to="E-CSX",
        relation_type="reference", cardinality="M:N",
        ownership_dimension="configuration_source",
        desc="子领域通过选择标准库的测试项来配置自身的测试项；20.4.3.3新增测试项时选择标准库及测试项",
        confidence="high",
        note={"comment": "四元分类判(a)：A为B提供配置/分类，B独立创建(标准库的测试项)；子领域选择来源标准库"},
    )

    # E-BMJL → E-ZS：报名记录关联证书（B 可能在报告/证书已发布后产生，可能永不创建）
    m.add_structural(
        frm="E-BMJL", to="E-ZS",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联其证书；证书在报告/证书已发布阶段产生，未通过评价则永不创建",
        confidence="high",
        note={"comment": "四元分类判(d)：B有前置条件(报告/证书已发布)、可能永不创建(评价未通过)、不满足(c)；非级联删除"},
    )

    # E-BMJL → E-JFD：报名记录关联缴费记录（B 有独立创建流程，B 是 managed）
    m.add_structural(
        frm="E-BMJL", to="E-JFD",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="报名记录关联其缴费记录；支持多次分批上传；缴费记录独立创建",
        confidence="high",
        note={"comment": "四元分类判(d)：B有独立创建流程(上传付款单)、B为managed不满足(c)、可能永不创建(免费项目)"},
    )

    # E-SYS → E-BMJL：实验室关联报名记录（A 为 B 的实验室信息来源）
    m.add_structural(
        frm="E-SYS", to="E-BMJL",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="实验室作为报名记录中实验室信息的来源；报名记录引用实验室基础信息",
        confidence="high",
        note={"comment": "四元分类判(a)：A为B提供配置/信息来源；实验室生命周期独立于报名记录"},
    )

    # E-XM → E-XX：项目关联信息发送记录（A 为 B 的业务上下文）
    m.add_structural(
        frm="E-XM", to="E-XX",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="项目作为信息发送记录的业务上下文；信息发送记录独立维护",
        confidence="high",
        note={"comment": "四元分类判(d)：B有独立创建流程、A为业务上下文非业务归属容器；信息发送记录系统级独立维护"},
    )

    # === Step 3: 分支维度 ===

    # 分支维度1：项目类型@E-XM（能力验证 vs 测量审核）
    m.add_branch_dimension(
        dimension="项目类型",
        entity="E-XM",
        values=["能力验证", "测量审核"],
        impact_scope="影响项目全流程：能力验证含完整报名审核/样品发收/结果提交/报告编制流程；测量审核流程相对简化，受理用户报名后直接进入实施阶段",
        evidence="三型判定：①配置型（对应 is_config 属性'项目类型'，创建时定、互斥、影响后续流程分支）；原文3.2平台集成能力验证和测量审核两类业务；20.5/20.6分别为能力验证和测量审核设置独立项目管理模块",
        branches=[
            {"value": "能力验证", "target_transition": "t02", "desc": "能力验证流程：项目发布后进入报名中，含完整样品发收循环"},
            {"value": "测量审核", "target_transition": "t02", "desc": "测量审核流程：受理用户报名后进入实施，样品管理较简化"},
        ],
    )

    # 分支维度2：评分方式@E-XM（分值 vs 权重）
    m.add_branch_dimension(
        dimension="评分方式",
        entity="E-XM",
        values=["分值", "权重"],
        impact_scope="影响评价阶段的计算方式：分值方式直接打分；权重方式按权重计算加权得分",
        evidence="三型判定：①配置型（对应 is_config 属性'评分方式'，创建时定、互斥、影响后续评价计算）；原文20.7调整评价功能，支持分值和权重两种评价方式",
        branches=[
            {"value": "分值", "target_transition": "t04", "desc": "评价时直接录入分值；及格分阈值判定"},
            {"value": "权重", "target_transition": "t04", "desc": "评价时录入权重；按权重加权计算最终得分"},
        ],
    )

    # === Step 4: 转换与因果 ===

    # --- E-XM.项目状态 转换 ---
    m.add_trans(
        tid="t01", entity="E-XM", dimension="项目状态",
        frm=None, to="待开始",
        action="新增项目",
        role="项目管理员",
        preconditions=[],
        expected_results=["新增一条项目记录，项目状态为待开始"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="20.5.1.5；20.5.1.6",
        note={"comment": "direction判⓪ frm=None创建转换；20.5.1.5新增监督员字段；20.5.1.6技术主管/实验室负责人/授权签字人备选唯一时默认填充"},
    )
    m.add_trans(
        tid="t02", entity="E-XM", dimension="项目状态",
        frm="待开始", to="报名中",
        action="能力验证计划发布",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于待开始状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "待开始")),
            precond(text="设计方案已编制", ptype="event_ref"),
        ],
        expected_results=["若项目类型=能力验证，则项目状态变为报名中，开放参加者报名"],
        traits=["branch"],
        direction="forward",
        priority="P0",
        source_ref="19.1实施阶段；19.3",
        note={"branch_dimension": "项目类型",
              "comment": "direction判③frm待开始先于to报名中；分支穿透：项目类型影响后续流程"},
    )
    m.add_trans(
        tid="t03", entity="E-XM", dimension="项目状态",
        frm="报名中", to="进行中",
        action="启动实施",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
            precond(text="报名截止且样品核查完成", ptype="event_ref"),
        ],
        expected_results=["项目状态变为进行中；参加者开始测试与结果提交"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1实施阶段",
        note={"comment": "direction判③frm报名中先于to进行中"},
    )
    m.add_trans(
        tid="t04", entity="E-XM", dimension="项目状态",
        frm="进行中", to="报告审核中",
        action="完成评审",
        role="策划人员",
        preconditions=[
            precond(text="项目处于进行中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "进行中")),
            precond(text="评价结果已确认", ptype="event_ref"),
        ],
        expected_results=["若评分方式=分值，则按分值生成评价结果；若评分方式=权重，则按权重加权计算生成评价结果"],
        traits=["branch"],
        direction="forward",
        priority="P0",
        source_ref="19.1报告编制和结果通知；20.7",
        note={"branch_dimension": "评分方式",
              "comment": "direction判③frm进行中先于to报告审核中；分支穿透：评分方式影响评价计算"},
    )
    m.add_trans(
        tid="t05", entity="E-XM", dimension="项目状态",
        frm="报告审核中", to="已结束",
        action="项目归档",
        role="项目管理员",
        preconditions=[
            precond(text="项目处于报告审核中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报告审核中")),
            precond(text="结果通知单和证书已发放", ptype="event_ref"),
        ],
        expected_results=["项目状态变为已结束；策划人员进行项目总结，记录归档；可执行文件整理"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1项目验收总结；19.1结束",
        note={"comment": "direction判③frm报告审核中先于to已结束；终态；20.5.1.1文件整理仅已结束项目可执行"},
    )

    # --- E-XM.样品状态 转换 ---
    m.add_trans(
        tid="t06", entity="E-XM", dimension="样品状态",
        frm=None, to="待核查",
        action="样品接收",
        role="样品管理员",
        preconditions=[],
        expected_results=["样品状态初始化为待核查"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="19.1实施阶段；19.3",
        note={"comment": "direction判⓪ frm=None创建转换；隐式初态：项目进入实施阶段后样品接收登记"},
    )
    m.add_trans(
        tid="t07", entity="E-XM", dimension="样品状态",
        frm="待核查", to="已核查",
        action="样品核查",
        role="样品管理员",
        preconditions=[
            precond(text="样品处于待核查状态", ptype="state_ref",
                    ref=state_ref("E-XM", "样品状态", "待核查")),
        ],
        expected_results=["样品状态变为已核查；生成核查记录表；可进行样品发放"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1实施阶段样品核查；19.3",
        note={"comment": "direction判③frm待核查先于to已核查；终态"},
    )

    # --- E-BMJL.报名记录状态 转换 ---
    m.add_trans(
        tid="t08", entity="E-BMJL", dimension="报名记录状态",
        frm=None, to="报名待审核",
        action="报名",
        role="能力验证参加者",
        preconditions=[
            precond(text="项目处于报名中状态", ptype="state_ref",
                    ref=state_ref("E-XM", "项目状态", "报名中")),
        ],
        expected_results=["新增一条报名记录，状态为报名待审核；附件包含报名表"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1实施阶段报名；19.4",
        note={"comment": "direction判⓪ frm=None创建转换；持有跨实体前置条件：E-XM项目状态=报名中"},
    )
    m.add_trans(
        tid="t09", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名退回",
        action="报名审核退回",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变为报名退回；短信通知用户'报名信息审核未通过'"],
        traits=["rollback"],
        direction="backward",
        priority="P1",
        source_ref="19.1报名审核；20.5.3.2",
        note={"comment": "direction判①显式措辞'退回修改'为回退至先前状态；20.5.3.2退回修改短信通知"},
    )
    m.add_trans(
        tid="t10", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="报名成功",
        action="报名审核通过",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变为报名成功；缴费通知单已发送；费用状态变为待缴费；短信通知用户'报名信息审核通过'"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1报名审核；20.5.3.2",
        note={"comment": "direction判③frm报名待审核先于to报名成功；联动费用状态初始化为待缴费"},
    )
    m.add_trans(
        tid="t11", entity="E-BMJL", dimension="报名记录状态",
        frm="报名待审核", to="已撤销",
        action="撤销报名",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于报名待审核状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名待审核")),
        ],
        expected_results=["报名记录状态变为已撤销"],
        traits=["rollback"],
        direction="backward",
        priority="P1",
        source_ref="19.3",
        note={"comment": "direction判①显式措辞'撤销'为回退至主线外；终态"},
    )
    m.add_trans(
        tid="t12", entity="E-BMJL", dimension="报名记录状态",
        frm="报名成功", to="结果待提交",
        action="能力验证预通知",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报名成功状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报名成功")),
            precond(text="样品已核查并发送预通知", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为结果待提交；通知状态变为待确认；预通知文件可下载"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1能力验证预通知；19.3",
        note={"comment": "direction判③frm报名成功先于to结果待提交；联动通知状态推进"},
    )
    m.add_trans(
        tid="t13", entity="E-BMJL", dimension="报名记录状态",
        frm="结果待提交", to="结果已提交",
        action="上传测试结果",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录处于结果待提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果待提交")),
        ],
        expected_results=["报名记录状态变为结果已提交；附件包含测试结果、报名表盖章版"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1参加者测试与结果提交；19.4",
        note={"comment": "direction判③frm结果待提交先于to结果已提交"},
    )
    m.add_trans(
        tid="t14", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="结果退回修改",
        action="结果审核退回",
        role="技术主管",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
        ],
        expected_results=["报名记录状态变为结果退回修改；短信通知用户'测试报告审核未通过'"],
        traits=["rollback"],
        direction="backward",
        priority="P1",
        source_ref="19.1结果报告回收；20.5.3.2",
        note={"comment": "direction判①显式措辞'退回'为回退至先前状态；20.5.3.2测试结果审核退回短信通知"},
    )
    m.add_trans(
        tid="t15", entity="E-BMJL", dimension="报名记录状态",
        frm="结果已提交", to="报告/证书审核中",
        action="编制结果报告",
        role="策划人员",
        preconditions=[
            precond(text="报名记录处于结果已提交状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "结果已提交")),
            precond(text="评价已完成且统计完成", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书审核中；附件包含报告、结果通知"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1报告编制和结果通知",
        note={"comment": "direction判③frm结果已提交先于to报告/证书审核中"},
    )
    m.add_trans(
        tid="t16", entity="E-BMJL", dimension="报名记录状态",
        frm="报告/证书审核中", to="报告/证书已发布",
        action="发放结果报告和证书",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录处于报告/证书审核中状态", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录状态", "报告/证书审核中")),
            precond(text="技术主管审核通过", ptype="event_ref"),
            precond(text="授权签字人/实验室负责人批准", ptype="event_ref"),
        ],
        expected_results=["报名记录状态变为报告/证书已发布；短信通知用户'结果通知单已发布'；证书发放给参加者"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1发放结果报告和证书；20.5.3.2",
        note={"comment": "direction判③frm报告/证书审核中先于to报告/证书已发布；终态；20.5.3.2结果通知单发布短信通知"},
    )

    # --- E-BMJL.通知状态 转换 ---
    m.add_trans(
        tid="t17", entity="E-BMJL", dimension="通知状态",
        frm=None, to="未发送",
        action="创建报名记录",
        role="system",
        preconditions=[],
        expected_results=["通知状态初始化为未发送"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="19.1；19.3",
        note={"comment": "direction判⓪ frm=None创建转换；隐式初态：报名记录创建时同步初始化通知状态"},
    )
    m.add_trans(
        tid="t18", entity="E-BMJL", dimension="通知状态",
        frm="未发送", to="待确认",
        action="发送预通知",
        role="项目管理员",
        preconditions=[
            precond(text="通知状态为未发送", ptype="state_ref",
                    ref=state_ref("E-BMJL", "通知状态", "未发送")),
        ],
        expected_results=["通知状态变为待确认；预通知文件可下载"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1能力验证预通知；19.3",
        note={"comment": "direction判③frm未发送先于to待确认；§19.1表中'已发送/待确认'合并表达，§19.3枚举为'待确认'"},
    )

    # --- E-BMJL.报名记录样品状态 转换 ---
    m.add_trans(
        tid="t19", entity="E-BMJL", dimension="报名记录样品状态",
        frm=None, to="待发样",
        action="创建报名记录",
        role="system",
        preconditions=[],
        expected_results=["报名记录样品状态初始化为待发样"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="19.1；19.3",
        note={"comment": "direction判⓪ frm=None创建转换；隐式初态：报名记录创建时同步初始化样品状态"},
    )
    m.add_trans(
        tid="t20", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待发样", to="待收样",
        action="样品发放",
        role="项目管理员",
        preconditions=[
            precond(text="报名记录样品状态为待发样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待发样")),
        ],
        expected_results=["报名记录样品状态变为待收样；短信通知用户'样品已发出'"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1样品发放；20.5.3.2",
        note={"comment": "direction判③frm待发样先于to待收样；20.5.3.2发样通知短信"},
    )
    m.add_trans(
        tid="t21", entity="E-BMJL", dimension="报名记录样品状态",
        frm="待收样", to="已收样",
        action="样品签收",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为待收样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "待收样")),
        ],
        expected_results=["报名记录样品状态变为已收样"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1；19.3",
        note={"comment": "direction判③frm待收样先于to已收样"},
    )
    m.add_trans(
        tid="t22", entity="E-BMJL", dimension="报名记录样品状态",
        frm="已收样", to="已确认",
        action="样品确认",
        role="能力验证参加者",
        preconditions=[
            precond(text="报名记录样品状态为已收样", ptype="state_ref",
                    ref=state_ref("E-BMJL", "报名记录样品状态", "已收样")),
        ],
        expected_results=["报名记录样品状态变为已确认；可进行测试与结果提交"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1；19.3",
        note={"comment": "direction判③frm已收样先于to已确认；终态"},
    )

    # --- E-BMJL.费用状态 转换 ---
    m.add_trans(
        tid="t23", entity="E-BMJL", dimension="费用状态",
        frm=None, to="待缴费",
        action="报名审核通过",
        role="system",
        preconditions=[
            precond(text="报名审核通过", ptype="event_ref"),
        ],
        expected_results=["费用状态初始化为待缴费；缴费通知单已发送"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1报名审核；19.3",
        note={"comment": "direction判⓪ frm=None创建转换；隐式初态：报名成功时同步初始化费用状态为待缴费；precondition为event_ref捕获报名审核通过事件"},
    )
    m.add_trans(
        tid="t24", entity="E-BMJL", dimension="费用状态",
        frm="待缴费", to="已缴费",
        action="上传付款单",
        role="能力验证参加者",
        preconditions=[
            precond(text="费用状态为待缴费", ptype="state_ref",
                    ref=state_ref("E-BMJL", "费用状态", "待缴费")),
        ],
        expected_results=["费用状态变为已缴费；支持多次付款不对金额校验限制"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1缴费；20.5.2.1",
        note={"comment": "direction判③frm待缴费先于to已缴费；终态；20.5.2.1多次付款不对金额校验"},
    )

    # --- E-BMJL.发票状态 转换 ---
    m.add_trans(
        tid="t25", entity="E-BMJL", dimension="发票状态",
        frm=None, to="待开票",
        action="创建报名记录",
        role="system",
        preconditions=[],
        expected_results=["发票状态初始化为待开票"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="19.1；19.3",
        note={"comment": "direction判⓪ frm=None创建转换；隐式初态：报名记录创建时同步初始化发票状态"},
    )
    m.add_trans(
        tid="t26", entity="E-BMJL", dimension="发票状态",
        frm="待开票", to="已开票",
        action="发票开具",
        role="财务管理人员",
        preconditions=[
            precond(text="发票状态为待开票", ptype="state_ref",
                    ref=state_ref("E-BMJL", "发票状态", "待开票")),
        ],
        expected_results=["发票状态变为已开票；附件包含发票；支持多次分批上传"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="19.1发票开具；20.10.2.2",
        note={"comment": "direction判③frm待开票先于to已开票；终态；20.10.2.2支持多次分批上传"},
    )

    # --- E-SYS.状态 转换 ---
    m.add_trans(
        tid="t27", entity="E-SYS", dimension="状态",
        frm=None, to="待审核",
        action="新增实验室",
        role="能力验证参加者",
        preconditions=[],
        expected_results=["新增实验室记录，状态为待审核"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="20.3.1；20.4.1",
        note={"comment": "direction判⓪ frm=None创建转换；机构新增/修改实验室后需管理用户审核通过方可用于项目报名"},
    )
    m.add_trans(
        tid="t28", entity="E-SYS", dimension="状态",
        frm="待审核", to="启用",
        action="实验室审核通过",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SYS", "状态", "待审核")),
        ],
        expected_results=["实验室状态变为启用；为当前数据生成快照记录；可用于项目报名"],
        traits=["audit"],
        direction="forward",
        priority="P0",
        source_ref="20.4.1.2",
        note={"comment": "direction判③frm待审核先于to启用；20.4.1.2审核通过生成快照记录"},
    )
    m.add_trans(
        tid="t29", entity="E-SYS", dimension="状态",
        frm="待审核", to="已退回",
        action="实验室审核退回",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为待审核", ptype="state_ref",
                    ref=state_ref("E-SYS", "状态", "待审核")),
            precond(text="审核结果为退回修改时必须填写审核意见", ptype="constraint",
                    note={"comment": "原文20.4.1.2退回修改必须填写审核意见"}),
        ],
        expected_results=["实验室状态变为已退回"],
        traits=["audit", "rollback"],
        direction="backward",
        priority="P1",
        source_ref="20.4.1.2",
        note={"comment": "direction判①显式措辞'退回修改'为回退至先前状态；20.4.1.2退回修改时状态变更为'已退回'"},
    )
    m.add_trans(
        tid="t30", entity="E-SYS", dimension="状态",
        frm="启用", to="停用",
        action="停用实验室",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为启用", ptype="state_ref",
                    ref=state_ref("E-SYS", "状态", "启用")),
        ],
        expected_results=["实验室状态变为停用；不可用于项目报名"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction判⑤无状态迁移语义但frm!=to，按forward+inferred处置；原文未明确方向语义"},
    )
    m.add_trans(
        tid="t31", entity="E-SYS", dimension="状态",
        frm="停用", to="启用",
        action="启用实验室",
        role="系统管理人员",
        preconditions=[
            precond(text="实验室状态为停用", ptype="state_ref",
                    ref=state_ref("E-SYS", "状态", "停用")),
        ],
        expected_results=["实验室状态变为启用；可用于项目报名"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="20.4.1.1",
        note={"comment": "direction判⑤无状态迁移语义但frm!=to，按forward+inferred处置；原文未明确方向语义"},
    )
    m.add_trans(
        tid="t32", entity="E-SYS", dimension="状态",
        frm="已退回", to="待审核",
        action="重新提交实验室",
        role="能力验证参加者",
        preconditions=[
            precond(text="实验室状态为已退回", ptype="state_ref",
                    ref=state_ref("E-SYS", "状态", "已退回")),
        ],
        expected_results=["实验室状态变为待审核"],
        traits=[],
        direction="resume",
        priority="P1",
        source_ref="20.4.1.3",
        note={"comment": "direction判①显式措辞'修改后重新提交'为自挂起恢复；20.4.1.3修改实验室后状态变为待审核"},
    )

    # --- E-BZK.状态 转换 ---
    m.add_trans(
        tid="t33", entity="E-BZK", dimension="状态",
        frm=None, to="启用",
        action="新增标准库",
        role="系统管理人员",
        preconditions=[],
        expected_results=["新增一条标准库记录，状态为启用"],
        traits=[],
        direction="forward",
        priority="P0",
        source_ref="20.4.2.2",
        note={"comment": "direction判⓪ frm=None创建转换；20.4.2.2新增标准库默认状态启用"},
    )
    m.add_trans(
        tid="t34", entity="E-BZK", dimension="状态",
        frm="启用", to="停用",
        action="停用标准库",
        role="系统管理人员",
        preconditions=[
            precond(text="标准库状态为启用", ptype="state_ref",
                    ref=state_ref("E-BZK", "状态", "启用")),
        ],
        expected_results=["标准库状态变为停用；项目创建等环节不可被选择"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction判⑤无状态迁移语义但frm!=to，按forward+inferred处置；20.4.2.5停用后不可被选择"},
    )
    m.add_trans(
        tid="t35", entity="E-BZK", dimension="状态",
        frm="停用", to="启用",
        action="启用标准库",
        role="系统管理人员",
        preconditions=[
            precond(text="标准库状态为停用", ptype="state_ref",
                    ref=state_ref("E-BZK", "状态", "停用")),
        ],
        expected_results=["标准库状态变为启用；可被选择"],
        traits=[],
        direction="forward",
        priority="P1",
        source_ref="20.4.2.5",
        note={"comment": "direction判⑤无状态迁移语义但frm!=to，按forward+inferred处置"},
    )

    # --- 4.3 自检 ---
    # ① Step 3 的 target_transition 局部 tid 均有对应 add_trans：t02/t04 已定义 ✓
    # ② crud 操作 comment 已回填对应转换标签或注明"无对应转换"
    # （E-SYS 删除、E-BZK 删除/修改、E-CSX 增改删 等纯crud无对应状态转换，已注明crud操作）

    # --- 4.4 因果 ---
    # 鉴别4.5：以下关系均为约束（门禁/前置条件），不是因果
    # - 项目状态=报名中 → 报名记录可创建：约束（precondition state_ref，走镜像XC）
    # - 项目状态=报告审核中 → 报告/证书可发布：约束（precondition state_ref，走镜像XC）
    # - 实验室状态=启用 → 可用于项目报名：约束（走BR）
    # - 标准库状态=启用 → 可被选择：约束（走BR）
    # 不存在显式跨实体因果（无"B完成后A自动变"的描述），故不写入 add_causal

    # === Step 5: 约束补充 ===

    # --- invalid_transitions：本文档无明确禁止的状态转换对，不生成IT ---

    # --- XC 跨实体约束 ---

    # 镜像XC：t08 持有 E-XM.项目状态=报名中 前置条件
    m.add_xc(
        xid="x01",
        source_entity="E-XM", source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="项目状态",
        target_transition="t08",
        target_condition="报名待审核",
        xc_source="镜像",
        desc="precondition'项目处于报名中状态'作为报名记录创建前置条件",
        source_ref="19.1实施阶段报名；19.3",
    )

    # 镜像XC：t16 持有 E-XM.项目状态=报告审核中 前置条件（隐式：报告发放依赖项目进入报告审核中）
    m.add_xc(
        xid="x02",
        source_entity="E-XM", source_transition="t04", source_state="报告审核中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t16",
        target_condition="报告/证书已发布",
        xc_source="镜像",
        desc="precondition'项目处于报告审核中状态'作为报告/证书发放前置条件",
        source_ref="19.1报告编制和结果通知",
    )

    # 镜像XC：t12 持有 E-XM.样品状态=已核查 前置条件（隐式：预通知需样品核查完成）
    m.add_xc(
        xid="x03",
        source_entity="E-XM", source_transition="t07", source_state="已核查",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t12",
        target_condition="结果待提交",
        xc_source="镜像",
        desc="precondition'样品已核查'作为预通知发送前置条件",
        source_ref="19.1能力验证预通知；19.1样品核查",
    )

    # 联动XC：t02 (E-XM 待开始→报名中) 联动 E-BMJL 创建报名记录（初始化报名记录状态为报名待审核）
    m.add_xc(
        xid="x04",
        source_entity="E-XM", source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t08",
        target_condition="报名待审核",
        xc_source="联动",
        desc="项目进入报名中后联动开启报名记录创建，新报名记录初始化为报名待审核",
        source_ref="19.1实施阶段",
    )

    # 注：t10→t23（报名审核通过→费用状态初始化）为同实体跨维度关系，由 t23 的 event_ref 前置条件承载，不作为跨实体 XC
    # 注：t05→文件整理可执行性为同实体操作可用性约束，由 BR b09 承载，不作为跨实体 XC

    # 分支差异XC：项目类型分支差异导致能力验证/测量审核流程不同
    m.add_xc(
        xid="x07",
        source_entity="E-XM", source_transition="t02", source_state="报名中",
        target_entity="E-BMJL", target_dimension="报名记录状态",
        target_transition="t08",
        target_condition="报名待审核",
        xc_source="分支差异",
        desc="若项目类型=能力验证，则报名记录需经完整审核流程；若项目类型=测量审核，则流程相对简化，受理用户报名后直接进入实施",
        source_ref="19.1；19.2",
    )

    # 注：评分方式分支差异（同实体 E-XM→E-XM）由 BR b17/b18 承载，不作为跨实体 XC

    # --- BR 业务规则 ---

    # BR1：实验室新增/修改后需审核通过
    m.add_br(
        bid="b01",
        category="authorization",
        desc="机构新增/修改实验室信息后需经管理用户审核通过后方可用于项目报名",
        entities_involved=["E-SYS"],
        source_ref="20.3.1",
        signal_type="restrictive",
        note={"comment": "signal_type命中'需经…方可'；授权类规则"},
    )

    # BR2：实验室审核退回修改必须填写审核意见
    m.add_br(
        bid="b02",
        category="validation",
        desc="实验室审核结果为退回修改时必须填写审核意见；审核结果为通过时审核意见可以为空",
        entities_involved=["E-SYS"],
        source_ref="20.4.1.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'必须'"},
    )

    # BR3：实验室审核通过生成数据快照
    m.add_br(
        bid="b03",
        category="computation",
        desc="审核结果为通过时为当前数据生成该数据的快照记录",
        entities_involved=["E-SYS"],
        source_ref="20.4.1.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'生成'约束性规则"},
    )

    # BR4：标准库新增字段必填
    m.add_br(
        bid="b04",
        category="validation",
        desc="标准库新增/修改时标准库编号、标准库名称、状态为必填字段；描述为选填",
        entities_involved=["E-BZK"],
        source_ref="20.4.2.2；20.4.2.3",
        signal_type="field_constraint",
        note={"comment": "signal_type命中'必填'字段约束"},
    )

    # BR5：标准库删除二次确认
    m.add_br(
        bid="b05",
        category="usability",
        desc="删除标准库时弹出二次确认框'确认删除标准库『XXX』？'；点击确定执行删除，点击取消关闭弹窗",
        entities_involved=["E-BZK"],
        source_ref="20.4.2.4",
        signal_type="usability",
        note={"comment": "signal_type命中'确认'易用性规则；3.6完备提示信息：删除操作时系统提示警示框'您确认删除记录吗？操作不可恢复！'"},
    )

    # BR6：停用的标准库不可被选择
    m.add_br(
        bid="b06",
        category="restrictive",
        desc="停用的标准库在项目创建等环节不可被选择",
        entities_involved=["E-BZK", "E-XM"],
        constrained_entity="E-BZK",
        source_ref="20.4.2.5",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不可'；constrained_entity判①操作对象为标准库"},
    )

    # BR7：测试项含有子项不允许删除
    m.add_br(
        bid="b07",
        category="validation",
        desc="含有子项的测试项记录不允许删除；存在子项的数据不可以删除",
        entities_involved=["E-CSX", "E-ZLY"],
        constrained_entity="E-CSX",
        source_ref="20.4.2.10；20.4.3.4",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不允许/不可以'；constrained_entity判①操作对象为测试项"},
    )

    # BR8：信息发送记录仅系统管理员和项目管理员可查看
    m.add_br(
        bid="b08",
        category="authorization",
        desc="信息发送记录仅系统管理员和项目管理员可以查看",
        entities_involved=["E-XX"],
        source_ref="20.4.4.1",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只有…可以'；授权类规则"},
    )

    # BR9：文件整理仅已结束项目可执行
    m.add_br(
        bid="b09",
        category="restrictive",
        desc="文件整理仅对已结束的项目记录提供操作入口",
        entities_involved=["E-XM"],
        source_ref="20.5.1.1；20.6.1.1",
        signal_type="restrictive",
        note={"comment": "signal_type命中'仅'；约束性规则"},
    )

    # BR10：批量提交审核仅已上传文件且未提交审核的记录可选
    m.add_br(
        bid="b10",
        category="validation",
        desc="只有已上传对应文件且未提交审核的记录才可以被选定进行批量提交审核",
        entities_involved=["E-BMJL"],
        source_ref="20.5.1.3",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只有…才'；分支维度承载", "branch_dimension": "项目类型"},
    )

    # BR11：消息发送接收人不能同时为空
    m.add_br(
        bid="b11",
        category="validation",
        desc="消息发送时接收人1和接收人2不能同时为空",
        entities_involved=["E-XM"],
        source_ref="20.5.1.4",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不能'"},
    )

    # BR12：未结束项目可消息发送
    m.add_br(
        bid="b12",
        category="restrictive",
        desc="未结束的项目可以进行消息发送；已结束项目不提供消息发送入口",
        entities_involved=["E-XM"],
        source_ref="20.5.1.4；20.6.1.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'未结束…可以'隐含已结束不可；分支维度承载", "branch_dimension": "项目类型"},
    )

    # BR13：技术主管/实验室负责人/授权签字人备选人唯一时默认填充
    m.add_br(
        bid="b13",
        category="usability",
        desc="项目新增表单中技术主管、实验室负责人、授权签字人字段，如果其备选人有且仅有一个时默认填充为备选值",
        entities_involved=["E-XM"],
        source_ref="20.5.1.6；20.6.1.4",
        signal_type="usability",
        note={"comment": "signal_type命中'如果…时默认'易用性规则"},
    )

    # BR14：多次付款不对金额校验限制
    m.add_br(
        bid="b14",
        category="validation",
        desc="已报名项目支持多次付款操作；不对付款金额进行校验限制",
        entities_involved=["E-BMJL"],
        source_ref="20.5.2.1；20.6.2.1",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不对…限制'"},
    )

    # BR15：证书到期前30天邮件提醒
    m.add_br(
        bid="b15",
        category="notification",
        desc="系统每天上午9点对系统中的证书信息进行查询；如证书距到期时间等于30天则通过邮件方式对用户进行提醒，并抄送项目管理员；提醒标题：证书到期提醒；提醒内容：您证书编号为xxxx的证书将于2025-01-01到期，请知悉",
        entities_involved=["E-ZS"],
        source_ref="20.5.2.3；20.6.2.3",
        signal_type="restrictive",
        note={"comment": "signal_type命中'每天…则'；通知类规则"},
    )

    # BR16：操作节点短信通知用户
    m.add_br(
        bid="b16",
        category="notification",
        desc="管理用户对报名信息操作后，对需要告知用户的节点增加短信提醒功能：报名审核通过/退回修改、发样通知、测试结果审核通过/退回、结果通知单发布",
        entities_involved=["E-BMJL"],
        source_ref="20.5.3.2；20.6.3.2",
        signal_type="usability",
        note={"comment": "signal_type命中'增加'易用性规则；分支维度承载", "branch_dimension": "项目类型"},
    )

    # BR17：评价人员只能修改自己的评价结果
    m.add_br(
        bid="b17",
        category="authorization",
        desc="评价人员只能对自己的评价结果进行修改，不能查看和修改其他评价人员的评价结果",
        entities_involved=["E-BMJL"],
        source_ref="20.7.1.2",
        signal_type="restrictive",
        note={"comment": "signal_type命中'只能…不能'；授权类规则；分支维度承载", "branch_dimension": "评分方式"},
    )

    # BR18：评价确认后项目评价状态关闭
    m.add_br(
        bid="b18",
        category="validation",
        desc="评价组长点击确认后将当前结果正式提交为项目的最终评价结果，项目评价状态关闭；除及格分外其他字段都不可以编辑",
        entities_involved=["E-XM"],
        source_ref="20.7.1.3",
        signal_type="restrictive",
        note={"comment": "signal_type命中'不可以编辑'；分支维度承载", "branch_dimension": "评分方式"},
    )

    return m
