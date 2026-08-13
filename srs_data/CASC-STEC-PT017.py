"""CASC-STEC-PT017 能力验证软件需求规格说明 需求数据。"""

from srs_pipeline import DomainModel, N, attr, op, precond, state_ref


def build() -> DomainModel:
    m = DomainModel(
        source="CASC-STEC-PT017能力验证软件需求规格说明.md",
        document_scope="载体管理系统 V1.00 的功能、易用性、安全需求；覆盖导入管理、载体登记、归档、移交、留存、回收、外送、文件导出、文件扫描、系统管理、监督管理、角色管理、日志管理等模块（4.x 章节）",
    )

    # ============================================================
    # Step 0: 项目操作词汇
    # ============================================================
    m.set_prohibition_config({
        "action_verbs": [
            "登录", "注销", "退出", "锁定", "解锁",
            "发起", "提交", "申请", "暂存", "重置", "取消", "关闭",
            "审批", "通过", "拒绝",
            "执行", "导入", "登记", "归档", "移交", "留存", "回收", "外送",
            "导出", "扫描",
            "查看", "查询", "下载", "确认", "打印",
            "新增", "编辑", "删除", "修改",
            "授权", "重置密码",
            "提醒", "限制", "终止", "完成",
            "统计", "审计",
        ],
        # prohibit_keywords 只收录"显式禁止类"领域短语。触发条件/默认值/取值范围
        # （如 "连续输错3次密码"、"无操作30分钟"、"份数1~99"）不是禁止词——它们是
        # 操作的触发条件或校验上限，当作禁止词会让 guard-polarity 把"自动锁定"这类
        # 正常操作误判为负向用例（曾致 PROC-013 自相矛盾：操作被拒绝 + 自动锁定）。
        # 此类短语已从列表移除；通用否定词（不可/不能/禁止/不得/不允许等）由
        # context/generate_obligation_model.py 的默认兜底提供。
        "prohibit_keywords": [
            "不能删除修改根部门",
            "对已归档载体无法进行移交留存回收外送",
            "内置3个角色不可更改删除",
        ],
    })

    # ============================================================
    # Step 0.5: 角色与权限
    # ============================================================
    # 8 种角色（4.2）
    m.add_role("r01", "系统管理员")
    m.add_role("r02", "普通用户")
    m.add_role("r03", "一级审批员")
    m.add_role("r04", "二级审批员")
    m.add_role("r05", "载体管理员")
    m.add_role("r06", "监督员")
    m.add_role("r07", "角色管理员")
    m.add_role("r08", "日志管理员")

    # 权限：仅声明 session/ui/file/query/config/crud 类无状态操作；转换型操作由 transitions 承载
    m.add_permission("系统管理员", [
        "新增用户", "编辑用户", "查看用户详情", "锁定用户", "解锁用户",
        "重置用户密码", "删除用户", "查询用户",
        "查看角色", "查询角色", "查看角色下用户",
        "新增部门", "编辑部门", "删除部门",
    ])
    m.add_permission("普通用户", [
        "查询导入任务", "查询登记任务", "查询归档任务", "查询移交任务",
        "查询留存任务", "查询回收任务", "查询外送任务",
        "查询导出任务", "查询扫描任务",
        "下载导入文件", "下载登记任务", "下载归档任务", "下载移交任务",
        "下载留存任务", "下载回收任务", "下载外送任务",
        "下载导出任务", "下载扫描任务",
    ])
    m.add_permission("一级审批员", [
        "查询待审批任务",
    ])
    m.add_permission("二级审批员", [
        "查询待审批任务",
    ])
    m.add_permission("载体管理员", [
        "查询待执行任务", "查看任务详情", "上传执行结果", "下载附件",
    ])
    m.add_permission("监督员", [
        "查询任务统计", "查询审批统计", "查询载体管理统计",
    ])
    m.add_permission("角色管理员", [
        "查询用户角色", "查询日志", "查询登录日志", "查询操作日志",
    ])
    m.add_permission("日志管理员", [
        "查询日志", "查询登录日志", "查询操作日志",
        "导入日志文件", "导出日志Excel",
    ])

    # ============================================================
    # Step 1: 实体
    # ============================================================

    # ---------- E-IMP 导入任务 ----------
    m.add_entity(
        id="E-IMP",
        name="导入任务",
        desc="对系统内任务数据、文件数据进行导入（外部导入至系统）的权限控制与流程管理；支持外部文件（格式不限）导入至系统指定模块；任务完成后系统归档导入记录",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成，规则为:任务类型+申请时间+流水序号"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；20个字符"),
            attr(name="源数据单位", desc="字符；必填项"),
            attr(name="源文件存储介质", desc="字符；必填项；可选:光盘、U盘、其它；选择其它时文本框必须输入内容"),
            attr(name="任务级别", desc="字符；必填项；只可选:A级、B级、C级", is_config=True),
            attr(name="联系电话", desc="数字；可选项"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.5.1 未命名此状态；4.4 通用功能含暂存"}},
        ],
        operations=[
            op(name="新增导入申请", category="crud",
               expected_results=["进入导入申请页面，可录入申请内容"],
               source_ref="4.5.1（1）",
               note=N(comment="crud 回填：对应转换 t65")),
            op(name="编辑导入申请", category="crud",
               expected_results=["可对已存在的导入申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存导入申请", category="crud",
               expected_results=["保存为草稿状态，不进入审批流程"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询导入任务", category="query",
               expected_results=["申请监控页面看到本人提交的导入任务列表及当前状态"],
               source_ref="4.5.4"),
            op(name="下载导入文件", category="file",
               expected_results=["能够将导入任务批量下载保存"],
               source_ref="4.5.4"),
            op(name="查看导入任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）",
               note=N(comment="通用功能：详情")),
            op(name="删除导入申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
            op(name="确认导入完成", category="crud",
               expected_results=["此任务结束"],
               source_ref="4.5.3",
               note=N(comment="crud 操作；对应执行后申请人确认动作；对应转换 t06")),
        ],
    )

    # ---------- E-REG 载体登记任务 ----------
    m.add_entity(
        id="E-REG",
        name="载体登记任务",
        desc="用户持有外来载体在系统中提交登记申请，只有通过审批后才允许将载体登记并纳入系统载体台账统一管理",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成，规则为:任务类型+申请时间+流水序号"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="载体信息", desc="必填项；添加载体后可看到载体快照"),
            attr(name="文件或资料名称", desc="字符；必填项；30个字符"),
            attr(name="载体类别", desc="必填项；下拉选项:光盘、纸质", is_config=True),
            attr(name="载体来源", desc="字符；必填项"),
            attr(name="原载体编号", desc="字符；必填项；20个字符"),
            attr(name="级别", desc="字符；必填项；只可选:A级、B级、C级", is_config=True),
            attr(name="纸张页数", desc="字符；载体类别为纸质时必填项；数值范围1-9999"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.6.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增登记申请", category="crud",
               expected_results=["进入载体登记申请页面，可录入申请内容"],
               source_ref="4.6.1",
               note=N(comment="crud 回填：对应转换 t66")),
            op(name="编辑登记申请", category="crud",
               expected_results=["可对已存在的登记申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存登记申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询登记任务", category="query",
               expected_results=["申请监控页面看到本人提交的载体登记任务列表及当前状态"],
               source_ref="4.6.4"),
            op(name="下载登记任务", category="file",
               expected_results=["能够将载体登记任务批量下载保存"],
               source_ref="4.6.4"),
            op(name="查看登记任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="删除登记申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-ARC 载体归档任务 ----------
    m.add_entity(
        id="E-ARC",
        name="载体归档任务",
        desc="对已登记的载体进行归档处理，实现载体的有序存放管理；完成载体归档审批后用户将待归档载体交给载体管理员，载体管理员接收载体后线上确认该份载体归档完成",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="载体信息", desc="字符；必填项；从申请人名下载体中选择，载体信息自动带入；包括载体编号、载体名称、文件名、载体级别、载体类型、人员部门等"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.7.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增归档申请", category="crud",
               expected_results=["进入归档申请页面，可录入申请内容"],
               source_ref="4.7.1",
               note=N(comment="crud 回填：对应转换 t67")),
            op(name="编辑归档申请", category="crud",
               expected_results=["可对已存在的归档申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存归档申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询归档任务", category="query",
               expected_results=["申请监控页面看到本人提交的载体归档任务列表及当前状态"],
               source_ref="4.7.4"),
            op(name="下载归档任务", category="file",
               expected_results=["能够将载体归档任务批量下载保存"],
               source_ref="4.7.4"),
            op(name="查看归档任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="删除归档申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-TRF 载体移交任务 ----------
    m.add_entity(
        id="E-TRF",
        name="载体移交任务",
        desc="载体可在不同用户之间进行移交管理；当前用户可将所持有的载体转交到其它用户处；系统自动记录移交历史并变更台账中的载体归属人",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="载体信息", desc="字符；必填项；从申请人名下载体中选择，载体信息自动带入；包括载体编号、载体名称、文件名、载体级别、载体类型、人员部门等"),
            attr(name="接收人", desc="字符；必填项；从系统用户中进行选择"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.8.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增移交申请", category="crud",
               expected_results=["进入载体移交申请页面，可录入申请内容"],
               source_ref="4.8.1",
               note=N(comment="crud 回填：对应转换 t68")),
            op(name="编辑移交申请", category="crud",
               expected_results=["可对已存在的移交申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存移交申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询移交任务", category="query",
               expected_results=["申请监控页面看到本人提交的载体移交任务列表及当前状态"],
               source_ref="4.8.4"),
            op(name="下载移交任务", category="file",
               expected_results=["能够将载体移交任务批量下载保存"],
               source_ref="4.8.4"),
            op(name="查看移交任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="删除移交申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-RET 载体留存任务 ----------
    m.add_entity(
        id="E-RET",
        name="载体留存任务",
        desc="如果用户对持有载体的使用需求可能超过规定的留存时限，系统可实现留存载体的延期管理功能；留存最长可增加48小时持有时间",
        type="core",
        tags=["multi-state", "approvable", "expirable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="载体信息", desc="字符；必填项；从申请人名下载体中选择，载体信息自动带入"),
            attr(name="留存原因", desc="字符；必填项"),
            attr(name="留存时间", desc="字符；必填项；单位为小时；只能填入1~48之间的整数"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.9.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增留存申请", category="crud",
               expected_results=["进入载体留存申请页面，可录入申请内容"],
               source_ref="4.9.1",
               note=N(comment="crud 回填：对应转换 t69")),
            op(name="编辑留存申请", category="crud",
               expected_results=["可对已存在的留存申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存留存申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询留存任务", category="query",
               expected_results=["申请监控页面看到本人提交的载体留存任务列表及当前状态"],
               source_ref="4.9.4"),
            op(name="下载留存任务", category="file",
               expected_results=["能够将载体留存任务批量下载保存"],
               source_ref="4.9.4"),
            op(name="查看留存任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="删除留存申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-RCY 载体回收任务 ----------
    m.add_entity(
        id="E-RCY",
        name="载体回收任务",
        desc="对无需留存的载体进行回收管理；用户发起回收申请，审批通过后将载体移交给载体管理员，载体管理员完成回收之后在线上提交回收完成，载体状态变为已回收",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="载体信息", desc="字符；必填项；从申请人名下载体中选择，载体信息自动带入"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.10.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增回收申请", category="crud",
               expected_results=["进入回收申请页面，可录入申请内容"],
               source_ref="4.10.1",
               note=N(comment="crud 回填：对应转换 t70")),
            op(name="编辑回收申请", category="crud",
               expected_results=["可对已存在的回收申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存回收申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询回收任务", category="query",
               expected_results=["申请监控页面看到本人提交的载体回收任务列表及当前状态"],
               source_ref="4.10.4"),
            op(name="下载回收任务", category="file",
               expected_results=["能够将载体回收任务批量下载保存"],
               source_ref="4.10.4"),
            op(name="查看回收任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="删除回收申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-OUT 载体外送任务 ----------
    m.add_entity(
        id="E-OUT",
        name="载体外送任务",
        desc="对需外送的载体进行管理，记录外送信息；载体外送申请审批通过后需打印外送交接单，载体管理员在接收到外送交接单回执后在系统中确认外送完成",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="外送单位", desc="字符；必填项；30个字符"),
            attr(name="载体信息", desc="字符；必填项；从申请人名下载体中选择，载体信息自动带入"),
            attr(name="文件内容", desc="字符；必填项"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.11.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增外送申请", category="crud",
               expected_results=["进入外送申请页面，可录入申请内容"],
               source_ref="4.11.1",
               note=N(comment="crud 回填：对应转换 t71")),
            op(name="编辑外送申请", category="crud",
               expected_results=["可对已存在的外送申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存外送申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询外送任务", category="query",
               expected_results=["申请监控页面看到本人提交的载体外送任务列表及当前状态"],
               source_ref="4.11.4"),
            op(name="下载外送任务", category="file",
               expected_results=["能够将载体外送任务批量下载保存"],
               source_ref="4.11.4"),
            op(name="查看外送任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="下载外送回执单", category="file",
               expected_results=["审批通过后回执单可以在回执单菜单进行查看和下载"],
               source_ref="4.11.2",
               note=N(comment="外送特有操作")),
            op(name="删除外送申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-EXP 文件导出任务 ----------
    m.add_entity(
        id="E-EXP",
        name="文件导出任务",
        desc="文件导出模块实现用户导出任务的提交、审核、执行、查询、归档等全流程管理；任务完成后系统归档任务信息、导出记录及光盘信息，支持光盘编号管理",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="导出方式", desc="字符；必填项；从光盘、U盘、邮件中选择；选择邮件方式需添加邮箱地址", is_config=True),
            attr(name="密码保护", desc="字符；必填项；从是、否中选择；选择是系统对导出文件加密，收件箱收到加密密码"),
            attr(name="文件列表", desc="字符；必填项；从本地磁盘选择上传文件并确定文件级别；文件名必须标明文件级别；导出文件不大于2GB"),
            attr(name="份数", desc="字符；必填项；输入1~99数字"),
            attr(name="联系电话", desc="数字；可选项"),
            attr(name="备注", desc="字符；可选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.12.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增导出申请", category="crud",
               expected_results=["进入导出申请页面，可录入申请内容"],
               source_ref="4.12.1",
               note=N(comment="crud 回填：对应转换 t72")),
            op(name="编辑导出申请", category="crud",
               expected_results=["可对已存在的导出申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存导出申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="上传导出文件", category="file",
               expected_results=["从本地磁盘中选择需要上传的文件，确定文件级别；文件名称、级别、大小由系统自动从文件中获取"],
               source_ref="4.12.1（2）；4.12.1（3）"),
            op(name="查询导出任务", category="query",
               expected_results=["申请监控页面看到本人提交的文件导出任务列表及当前状态"],
               source_ref="4.12.4"),
            op(name="下载导出任务", category="file",
               expected_results=["能够将文件导出任务批量下载保存"],
               source_ref="4.12.4"),
            op(name="查看导出任务详情", category="query",
               expected_results=["提供记录的详细信息；审批人可查看到上传的文件快照"],
               source_ref="4.4（4）；4.12.1（4）"),
            op(name="删除导出申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-SCN 文件扫描任务 ----------
    m.add_entity(
        id="E-SCN",
        name="文件扫描任务",
        desc="扫描管理模块实现扫描任务的提交、扫描文件的处理与存储管理；用户发起扫描任务，系统根据任务级别匹配审批流程；审批通过后执行人操作扫描设备完成扫描，由载体管理员在线上确认扫描任务完成，同时归档任务信息和扫描记录",
        type="core",
        tags=["multi-state", "approvable"],
        attributes=[
            attr(name="申请人", desc="字符；必填项；根据登录用户自动获取申请人姓名"),
            attr(name="申请部门", desc="字符；必填项；根据登录用户自动获取申请人部门"),
            attr(name="流水号", desc="字符；必填项；系统自动生成"),
            attr(name="申请时间", desc="字符；必填项；系统自动生成"),
            attr(name="申请事由", desc="字符；必填项；30个字符"),
            attr(name="文件级别", desc="字符；必填项；只可选:A级、B级、C级", is_config=True),
            attr(name="文件页数", desc="字符；必填项；只能填入1~100之间的数字"),
            attr(name="联系电话", desc="数字；可选项"),
            attr(name="扫描内容", desc="字符；必选项"),
        ],
        state_dimensions=[
            {"dimension_name": "任务状态",
             "states": [
                 "草稿",
                 "待审批", "审批通过", "审批拒绝", "待执行", "已完成",
             ],
             "initial": "草稿", "terminal": ["审批拒绝", "已完成"],
             "inferred": ["草稿", "待审批", "待执行", "已完成"],
             "note": {"comment": "隐式初态：暂存后初始化，原文 4.13.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增扫描申请", category="crud",
               expected_results=["进入扫描申请页面，可录入申请内容"],
               source_ref="4.13.1",
               note=N(comment="crud 回填：对应转换 t73")),
            op(name="编辑扫描申请", category="crud",
               expected_results=["可对已存在的扫描申请记录进行修改"],
               source_ref="4.4（2）",
               note=N(comment="无对应转换（编辑为草稿阶段属性修改，不改任务状态）")),
            op(name="暂存扫描申请", category="crud",
               expected_results=["保存为草稿状态"],
               source_ref="4.4",
               note=N(comment="通用功能：暂存；无对应转换（暂存保存草稿，不改变任务状态）")),
            op(name="查询扫描任务", category="query",
               expected_results=["申请监控页面看到本人提交的文件扫描任务列表及当前状态"],
               source_ref="4.13.4"),
            op(name="下载扫描任务", category="file",
               expected_results=["能够将文件扫描任务批量下载保存"],
               source_ref="4.13.4"),
            op(name="查看扫描任务详情", category="query",
               expected_results=["提供记录的详细信息"],
               source_ref="4.4（4）"),
            op(name="删除扫描申请", category="crud",
               expected_results=["业务允许情况下删除选中记录，列表数据实时刷新"],
               source_ref="4.4（5）",
               note=N(comment="无对应转换（删除记录为生命周期终止，不建模状态转换）")),
        ],
    )

    # ---------- E-CAR 载体 ----------
    m.add_entity(
        id="E-CAR",
        name="载体",
        desc="载体台账中的核心实体；通过载体登记任务纳入台账，可在不同用户间流转（归档/移交/留存/回收/外送）；持有时间默认72小时，到期前12小时系统提醒",
        type="core",
        tags=["multi-state", "expirable"],
        attributes=[
            attr(name="载体编号", desc="系统自动生成；唯一"),
            attr(name="载体名称", desc="字符；自动从登记申请带入"),
            attr(name="文件名", desc="字符；自动从登记申请带入"),
            attr(name="载体级别", desc="字符；A级、B级、C级"),
            attr(name="载体类型", desc="字符；光盘、纸质等"),
            attr(name="人员部门", desc="字符；自动带入"),
            attr(name="持有时间", desc="数字；单位为小时；初始默认72小时；留存后可增加1~48小时"),
            attr(name="载体到期提醒时间", desc="持有时间到期前12小时系统自动提醒"),
        ],
        state_dimensions=[
            {"dimension_name": "载体状态",
             "states": [
                 "已登记",
                 "已归档", "已回收", "已外送",
             ],
             "initial": "已登记", "terminal": ["已归档", "已回收", "已外送"],
             "inferred": ["已登记"],
             "note": {"comment": "登记执行完成后初始状态，原文 4.6.3 描述'载体已经登记入个人台账'；移交/留存为属性级操作（归属人变更/持有时间延长，4.8.3/4.9.3），不改载体状态；已外送为终态（4.11.3 确认载体已外送，全文无归还回路）"}},
        ],
        operations=[
            op(name="查询载体台账", category="query",
               expected_results=["申请人能够看到本人名下的载体列表"],
               source_ref="4.6.3；4.7.3",
               note=N(comment="通用操作：查询载体")),
        ],
    )

    # ---------- E-USER 用户 ----------
    m.add_entity(
        id="E-USER",
        name="用户",
        desc="系统用户；用户管理只对系统管理员开放，实现用户的新增、锁定、解锁、删除、查询；用户信息包括用户账号、用户姓名、手机号码等",
        type="managed",
        attributes=[
            attr(name="用户账号", desc="字符；必填项；可以由汉字、小写字母、数字、下划线(_)组成；不可重复；不可修改"),
            attr(name="用户姓名", desc="字符；必填项"),
            attr(name="登录密码", desc="数字；必填项；由数字、大小写字母和特殊符号组成；长度大于等于8个字符小于等于18个字符"),
            attr(name="确认密码", desc="数字；必填项；与登录密码一致"),
            attr(name="手机号码", desc="数字；必填项，唯一；第一位数字1，第二位数字:3、4、5、6、7、8、9，一共11位数字"),
            attr(name="邮箱", desc="字符；必须包含@和.；不能包含中文、其它特殊符号"),
            attr(name="生日", desc="日期；yyyy-mm-dd"),
        ],
        state_dimensions=[
            {"dimension_name": "用户状态",
             "states": [
                 "正常",
                 "锁定",
             ],
             "initial": "正常", "terminal": [],
             "inferred": ["正常"],
             "note": {"comment": "隐式初态：用户新增后默认正常，原文 4.14.1 未命名此状态"}},
        ],
        operations=[
            op(name="新增用户", category="crud",
               expected_results=["实现用户新增的功能"],
               source_ref="4.14.1（1）",
               note=N(comment="crud 回填：对应转换 t75")),
            op(name="编辑用户", category="crud",
               expected_results=["实现用户信息的修改，用户账号不能进行修改"],
               source_ref="4.14.1（2）",
               note=N(comment="无对应转换（修改用户信息不改用户状态；账号不可修改）")),
            op(name="查看用户详情", category="query",
               expected_results=["查看用户的详细信息"],
               source_ref="4.14.1（3）"),
            op(name="重置用户密码", category="crud",
               expected_results=["重置后的密码为:Abcd123456！"],
               source_ref="4.14.1（6）",
               note=N(comment="无对应转换（重置密码为属性操作，不改用户状态）")),
            op(name="删除用户", category="crud",
               expected_results=["将用户从系统中删除，具有流程信息的用户不能进行删除"],
               source_ref="4.14.1（7）",
               note=N(comment="无对应转换（删除为生命周期终止，不建模状态转换）")),
            op(name="查询用户", category="query",
               expected_results=["根据用户账号查询符合条件的用户"],
               source_ref="4.14.1（8）"),
            op(name="登录", category="session",
               expected_results=["登录成功后进入的功能操作页面右上角显示登录人员的名称；根据角色进入相应页面"],
               source_ref="4.3.1（1）；4.3.1（5）；4.3.1（6）"),
            op(name="注销", category="session",
               expected_results=["退出登录状态，关闭所有操作界面，返回到用户登录界面"],
               source_ref="4.3.2（1）"),
        ],
    )

    # ---------- E-DEPT 部门/机构 ----------
    m.add_entity(
        id="E-DEPT",
        name="部门",
        desc="机构管理应实现系统角色对部门信息的新增、编辑、删除；不能删除修改根部门",
        type="managed",
        attributes=[
            attr(name="部门名称", desc="字符；必填项；名称唯一"),
            attr(name="排序", desc="数字；默认为0"),
            attr(name="备注", desc="字符"),
        ],
        state_dimensions=[],
        operations=[
            op(name="新增部门", category="crud",
               expected_results=["点击添加下级机构按钮可增加下级机构信息"],
               source_ref="4.14.3（1）",
               note=N(comment="无对应转换（部门为组织分类配置实体，无状态维度）")),
            op(name="编辑部门", category="crud",
               expected_results=["实现对已存在部门信息的编辑，被客户使用的部门不能进行必填项信息的修改"],
               source_ref="4.14.3（2）",
               note=N(comment="无对应转换（部门为组织分类配置实体，无状态维度）")),
            op(name="删除部门", category="crud",
               expected_results=["实现对已存在部门信息的删除，被客户使用和实验单使用的部门不能进行删除"],
               source_ref="4.14.3（3）",
               note=N(comment="无对应转换（部门为组织分类配置实体，无状态维度）")),
        ],
    )
    m.add_br(
        bid="b47",
        category="validation",
        desc="不能删除修改根部门",
        entities_involved=["E-DEPT"],
        source_ref="4.14.3",
        signal_type="restrictive",
    )

    # ---------- E-ROLE 角色 ----------
    m.add_entity(
        id="E-ROLE",
        name="角色",
        desc="系统提供8种角色：系统管理员、普通用户、一级审批员、二级审批员、载体管理员、监督员、角色管理员和日志管理员；内置3个角色不可更改删除",
        type="managed",
        attributes=[
            attr(name="角色名称", desc="字符；必填项，只能单选；取值范围:1系统管理员2普通用户3一级审批员4二级审批员5载体管理员6监督员7角色管理员8日志管理员"),
            attr(name="角色编码", desc="字符"),
            attr(name="创建时间", desc="日期"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询角色", category="query",
               expected_results=["通过角色名称字段进行查询"],
               source_ref="4.14.2（1）"),
            op(name="查看角色下用户", category="query",
               expected_results=["查看该角色下对应的用户信息"],
               source_ref="4.14.2（2）"),
        ],
    )

    # ---------- E-LOG 日志 ----------
    m.add_entity(
        id="E-LOG",
        name="日志",
        desc="系统的日志管理只对日志管理员和角色管理员开放，包括登录日志和操作日志；登录日志至少记录用户登录日志；操作日志至少记录用户信息的新增、编辑、删除",
        type="managed",
        attributes=[
            attr(name="日志内容", desc="字符"),
            attr(name="操作人账号", desc="字符"),
            attr(name="操作人名称", desc="字符"),
            attr(name="IP", desc="数字"),
            attr(name="日志类型", desc="枚举；登录日志/操作日志"),
            attr(name="创建时间", desc="日期；yyyy-mm-dd hh:mm:ss"),
        ],
        state_dimensions=[],
        operations=[
            op(name="查询登录日志", category="query",
               expected_results=["可以根据操作人账号、操作人名称、创建时间查询登录日志信息"],
               source_ref="4.17.1（1）"),
            op(name="查询操作日志", category="query",
               expected_results=["可以根据操作人账号、操作人名称、创建时间查询操作日志信息"],
               source_ref="4.17.1（1）"),
            op(name="导入日志文件", category="file",
               expected_results=["系统进入日志导入页面，可选择需要导入的日志文件，完成日志导入操作"],
               source_ref="4.17.1（2）"),
            op(name="导出日志Excel", category="file",
               expected_results=["根据起始时间，完成导出成Excel文件操作；可选择导出后删除导出项"],
               source_ref="4.17.2（1）"),
        ],
    )

    # ============================================================
    # Step 2: 结构关系
    # ============================================================
    # 用户与部门：reference（部门为用户组织分类配置，非拥有）
    m.add_structural(
        frm="E-DEPT", to="E-USER",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="部门为用户组织分类配置；用户新增时必填申请部门，根据登录用户自动获取",
        confidence="high",
        note={"comment": "(d) 用户有独立创建流程（系统管理员新增），生命周期独立；部门仅提供组织分类，删除部门不级联用户（文档 4.14.3：被使用部门禁止删除为阻断非级联）；management_dimension 复核为 configuration_source"},
    )
    # 用户与角色：reference（用户被授予角色，角色可独立存在）
    m.add_structural(
        frm="E-ROLE", to="E-USER",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="角色配置源；系统预置8种角色，用户被授予某角色；角色管理员可对用户授权/修改/删除角色",
        confidence="high",
        note={"comment": "(a) 角色提供配置分类，用户独立创建；management_dimension 复核为 configuration_source"},
    )
    # 载体与用户（持有人）：reference（载体归属用户，但载体由登记任务创建）
    m.add_structural(
        frm="E-USER", to="E-CAR",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="用户持有载体；载体登记成功后记入申请人台账，持有时间默认72小时；移交后归属人变更",
        confidence="high",
        note={"comment": "(d) 载体有独立创建流程（登记任务执行后产生），可跨用户流转；relation_type=reference 配 configuration_source（联动约束；载体创建语义由 XC x10 联动承载）"},
    )
    # 登记任务与载体：reference（登记执行产出载体，载体产生后独立流转）
    m.add_structural(
        frm="E-REG", to="E-CAR",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="登记任务执行完成后产出载体；载体经登记入个人台账，产生后独立流转（归档/移交/回收/外送）",
        confidence="high",
        note={"comment": "(d) 载体由登记任务驱动产生（创建联动经 XC x10），产生后独立于登记任务流转；登记任务为来源非归属容器，删除登记任务不级联载体；management_dimension 复核为 configuration_source"},
    )
    # 归档/移交/留存/回收/外送任务与载体：reference（任务操作既有载体）
    m.add_structural(
        frm="E-CAR", to="E-ARC",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="载体可被多次发起归档任务（实际仅一次成功）；归档任务以载体为操作对象",
        confidence="high",
        note={"comment": "(d) 归档任务有独立创建流程且可能永不创建；载体为业务归属容器但 relation_type=reference 因载体可独立存在"},
    )
    m.add_structural(
        frm="E-CAR", to="E-TRF",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="载体可被多次发起移交任务；移交任务以载体为操作对象",
        confidence="high",
        note={"comment": "(d) 同上"},
    )
    m.add_structural(
        frm="E-CAR", to="E-RET",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="载体可被多次发起留存任务；留存任务以载体为操作对象",
        confidence="high",
        note={"comment": "(d) 同上"},
    )
    m.add_structural(
        frm="E-CAR", to="E-RCY",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="载体可被发起回收任务；回收任务以载体为操作对象",
        confidence="high",
        note={"comment": "(d) 同上"},
    )
    m.add_structural(
        frm="E-CAR", to="E-OUT",
        relation_type="reference", cardinality="1:N",
        ownership_dimension="configuration_source",
        desc="载体可被发起外送任务；外送任务以载体为操作对象",
        confidence="high",
        note={"comment": "(d) 同上"},
    )
    # 各任务与用户（申请人）：reference（任务由用户发起）
    for frm_eid, task_name in [
        ("E-USER", "E-IMP"), ("E-USER", "E-REG"), ("E-USER", "E-ARC"),
        ("E-USER", "E-TRF"), ("E-USER", "E-RET"), ("E-USER", "E-RCY"),
        ("E-USER", "E-OUT"), ("E-USER", "E-EXP"), ("E-USER", "E-SCN"),
    ]:
        m.add_structural(
            frm=frm_eid, to=task_name,
            relation_type="reference", cardinality="1:N",
            ownership_dimension="configuration_source",
            desc=f"用户发起{task_name.replace('E-','')}任务；任务记录申请人字段",
            confidence="high",
            note={"comment": "(d) 任务有独立创建流程；用户为发起人；relation_type=reference 配 configuration_source（联动约束）"},
        )

    # ============================================================
    # Step 3: 分支维度
    # ============================================================
    # 任务级别是核心分支维度，适用于全部 9 类任务实体
    # 此处为代表实体 E-IMP 添加，分支覆盖由 Step 5 多条 BR 兑现
    m.add_branch_dimension(
        dimension="任务级别",
        entity="E-IMP",
        values=["A级", "B级", "C级"],
        impact_scope="审批流程：A级无需审批直接进入待执行；B级需一级审批；C级需二级审批",
        evidence="4.5.2 任务级别为A级无需审批；B级需经过一级审批；C级需经过二级审批；4.6.2/4.7.2/4.8.2/4.9.2/4.10.2/4.11.2/4.12.2/4.13.2 同此规则",
        branches=[
            {"value": "A级", "target_transition": "任务提交转换（A级直入待执行）",
             "desc": "A级无需审批，提交后直接进入待执行状态"},
            {"value": "B级", "target_transition": "一级审批通过转换",
             "desc": "B级需经过一级审批员审批通过后进入待执行"},
            {"value": "C级", "target_transition": "二级审批通过转换",
             "desc": "C级需经过二级审批员审批通过后进入待执行"},
        ],
    )

    # ----- Step 1 回写：发现 transitions 中使用动词"进入"（如"进入导入执行"），回写 action_verbs -----
    # 来源 Step 4.1 自检
    m.add_action_verbs(["进入"])

    # ============================================================
    # Step 4.1: 转换
    # ============================================================
    # 结构概览：
    #   E-IMP   t01-t06   E-REG   t07-t12   E-ARC   t13-t18
    #   E-TRF   t19-t24   E-RET   t25-t30   E-RCY   t31-t36
    #   E-OUT   t37-t42   E-EXP   t43-t48   E-SCN   t49-t54
    #   E-CAR   t55-t60   E-USER  t61-t64   E-DEPT  t65-t67
    #   E-ROLE  t68-t70   E-LOG   (无转换型状态)

    # ----- E-IMP 导入任务转换 -----
    m.add_trans(
        tid="t01",
        entity="E-IMP", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交导入申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None,
                    note={"comment": "必填项校验为数据约束，无对应状态维度"}),
        ],
        expected_results=["导入申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.5.1；4.4（3）",
        note={"comment": "direction: 草稿在 states 列表先于待审批，判 forward；仅 B/C 级任务走此路径，A 级走 t04"},
    )
    m.add_trans(
        tid="t02",
        entity="E-IMP", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="导入任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-IMP", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None,
                    note={"comment": "A级无需审批；分支约束由 branch_dimension 承载"}),
        ],
        expected_results=["审批通过后导入申请人可进行文件的导入；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.5.2",
        note={"branch_dimension": "任务级别",
              "comment": "B级一级审批员通过；C级需二级审批员（t02b）"},
    )
    # C 级二级审批（与 t02 同 frm/to 但分支不同，按业务实质合并为 t02 + 二级审批约束）
    # 此处简化：t02 表达 B 级一级审批通过；C 级需先一级再二级，作为分支差异在 expected_results 体现
    m.add_trans(
        tid="t03",
        entity="E-IMP", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="导入任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-IMP", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["导入任务终止；导入申请人需重新提交导入任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.5.2",
        note={"branch_dimension": "任务级别",
              "comment": "direction: 终态侧挂，判 lateral；B/C 级适用"},
    )
    m.add_trans(
        tid="t04",
        entity="E-IMP", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交导入申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None,
                    note={"comment": "分支约束：A级无需审批"}),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.5.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t05",
        entity="E-IMP", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入导入执行",
        role="载体管理员",
        preconditions=[
            precond(text="导入任务审批通过", ptype="state_ref",
                    ref=state_ref("E-IMP", "任务状态", "审批通过")),
        ],
        expected_results=["导入任务进入执行环节；载体管理员实施文件导入"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.5.3",
    )
    m.add_trans(
        tid="t06",
        entity="E-IMP", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认导入完成",
        role="普通用户",
        preconditions=[
            precond(text="载体管理员已完成文件导入", ptype="event_ref"),
        ],
        expected_results=["申请人下载导入文件后进行确认，此任务结束；如未确认48小时后系统自动结束并删除导入文件"],
        traits=["time_sensitive"],
        direction="forward", priority="P0",
        source_ref="4.5.3",
        note={"comment": "48小时超时由 BR 承载"},
    )

    # ----- E-REG 载体登记任务转换 -----
    m.add_trans(
        tid="t07",
        entity="E-REG", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交登记申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["登记申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.6.1；4.4（3）",
        note={"comment": "仅 B/C 级走此路径，A 级走 t10"},
    )
    m.add_trans(
        tid="t08",
        entity="E-REG", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="登记任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-REG", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后登记申请人可看到载体已经登记入个人台账；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.6.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t09",
        entity="E-REG", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="登记任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-REG", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["登记任务终止；登记申请人需重新提交登记任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.6.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t10",
        entity="E-REG", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交登记申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.6.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t11",
        entity="E-REG", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入登记执行",
        role="载体管理员",
        preconditions=[
            precond(text="登记任务审批通过", ptype="state_ref",
                    ref=state_ref("E-REG", "任务状态", "审批通过")),
        ],
        expected_results=["登记任务进入执行环节；载体管理员实施载体登记"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.6.3",
    )
    m.add_trans(
        tid="t12",
        entity="E-REG", dimension="任务状态",
        frm="待执行", to="已完成",
        action="完成登记执行",
        role="载体管理员",
        preconditions=[
            precond(text="载体管理员已实施载体登记", ptype="event_ref"),
        ],
        expected_results=["登记完成后，申请人能够看到本人名下的载体；载体记入申请人台账，持有时间默认72小时"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.6.3；4.6.5",
    )

    # ----- E-ARC 载体归档任务转换 -----
    m.add_trans(
        tid="t13",
        entity="E-ARC", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交归档申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="载体处于已登记状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记")),
        ],
        expected_results=["归档申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.7.1",
    )
    m.add_trans(
        tid="t14",
        entity="E-ARC", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="归档任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-ARC", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后归档申请人需将载体交到载体管理员处；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.7.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t15",
        entity="E-ARC", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="归档任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-ARC", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["归档任务终止；归档申请人需重新提交归档任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.7.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t16",
        entity="E-ARC", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交归档申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.7.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t17",
        entity="E-ARC", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入归档执行",
        role="载体管理员",
        preconditions=[
            precond(text="归档任务审批通过", ptype="state_ref",
                    ref=state_ref("E-ARC", "任务状态", "审批通过")),
        ],
        expected_results=["归档任务进入执行环节；载体管理员接收载体并确认归档完成"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.7.3",
    )
    m.add_trans(
        tid="t18",
        entity="E-ARC", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认归档完成",
        role="载体管理员",
        preconditions=[
            precond(text="载体管理员已接收待归档载体", ptype="event_ref"),
        ],
        expected_results=["申请人能够看到本人名下的载体状态为已归档；对已归档载体，无法进行移交、留存、回收、外送操作"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.7.3",
    )

    # ----- E-TRF 载体移交任务转换 -----
    m.add_trans(
        tid="t19",
        entity="E-TRF", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交移交申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="载体处于可移交状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记"),
                    note={"comment": "载体处于已登记状态即可发起移交；移交为归属人变更（4.8.3），不改载体状态"}),
        ],
        expected_results=["移交申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.8.1",
    )
    m.add_trans(
        tid="t20",
        entity="E-TRF", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="移交任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-TRF", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后移交申请人需和接收人完成交接；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.8.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t21",
        entity="E-TRF", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="移交任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-TRF", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["移交任务终止；移交申请人需重新提交移交任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.8.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t22",
        entity="E-TRF", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交移交申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.8.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t23",
        entity="E-TRF", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入移交执行",
        role="普通用户",
        preconditions=[
            precond(text="移交任务审批通过", ptype="state_ref",
                    ref=state_ref("E-TRF", "任务状态", "审批通过")),
        ],
        expected_results=["移交任务进入执行环节；接收人在线确认载体移交"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.8.3",
    )
    m.add_trans(
        tid="t24",
        entity="E-TRF", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认移交完成",
        role="普通用户",
        preconditions=[
            precond(text="接收人在线确认载体移交", ptype="event_ref"),
        ],
        expected_results=["移交成功后，申请人台账中看不到此载体；接收人台账中自动增加此载体；系统自动记录移交历史并变更台账中的载体归属人"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.8.3",
    )

    # ----- E-RET 载体留存任务转换 -----
    m.add_trans(
        tid="t25",
        entity="E-RET", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交留存申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="留存时间在1~48小时之间", ptype="constraint", ref=None),
            precond(text="载体处于可留存状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记"),
                    note={"comment": "载体处于已登记状态即可发起留存；留存为持有时间延长（4.9.3），不改载体状态"}),
        ],
        expected_results=["留存申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.9.1",
    )
    m.add_trans(
        tid="t26",
        entity="E-RET", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="留存任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-RET", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后载体持有时间自动增加；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.9.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t27",
        entity="E-RET", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="留存任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-RET", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["留存任务终止；留存申请人需重新提交留存任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.9.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t28",
        entity="E-RET", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交留存申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="留存时间在1~48小时之间", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.9.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t29",
        entity="E-RET", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入留存执行",
        role="system",
        preconditions=[
            precond(text="留存任务审批通过", ptype="state_ref",
                    ref=state_ref("E-RET", "任务状态", "审批通过")),
        ],
        expected_results=["将当前用户所持有的载体持有时间自动增加"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.9.3",
    )
    m.add_trans(
        tid="t30",
        entity="E-RET", dimension="任务状态",
        frm="待执行", to="已完成",
        action="完成留存执行",
        role="system",
        preconditions=[
            precond(text="载体持有时间已增加", ptype="event_ref"),
        ],
        expected_results=["载体持有时间到期前12小时系统自动向持有人发送载体到期提醒；持有人可选择将载体进行归档、移交、回收、留存或者外送；到期不处理系统自动将此载体持有人用户进行功能限制"],
        traits=["time_sensitive"],
        direction="forward", priority="P0",
        source_ref="4.9.3",
    )

    # ----- E-RCY 载体回收任务转换 -----
    m.add_trans(
        tid="t31",
        entity="E-RCY", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交回收申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="载体处于可回收状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记"),
                    note={"comment": "载体处于已登记状态即可发起回收（已外送载体已在系统外，不参与回收）"}),
        ],
        expected_results=["回收申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.10.1",
    )
    m.add_trans(
        tid="t32",
        entity="E-RCY", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="回收任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-RCY", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后回收申请人将载体移交给载体管理员进行回收；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.10.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t33",
        entity="E-RCY", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="回收任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-RCY", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["回收任务终止；回收申请人需重新提交回收任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.10.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t34",
        entity="E-RCY", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交回收申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.10.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t35",
        entity="E-RCY", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入回收执行",
        role="载体管理员",
        preconditions=[
            precond(text="回收任务审批通过", ptype="state_ref",
                    ref=state_ref("E-RCY", "任务状态", "审批通过")),
        ],
        expected_results=["将当前用户所申请回收的载体转交到载体管理员处；载体管理员在线确认载体回收"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.10.3",
    )
    m.add_trans(
        tid="t36",
        entity="E-RCY", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认回收完成",
        role="载体管理员",
        preconditions=[
            precond(text="载体管理员已接收待回收载体", ptype="event_ref"),
        ],
        expected_results=["载体状态变为已回收；回收任务完成"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.10；4.10.3",
    )

    # ----- E-OUT 载体外送任务转换 -----
    m.add_trans(
        tid="t37",
        entity="E-OUT", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交外送申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="载体处于可外送状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记"),
                    note={"comment": "载体处于已登记状态即可发起外送；外送完成后载体状态变为已外送（终态，4.11.3）"}),
        ],
        expected_results=["外送申请提交至审批流程；任务状态变为待审批"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.11.1",
    )
    m.add_trans(
        tid="t38",
        entity="E-OUT", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="外送任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-OUT", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后外送申请人需打印载体外送交接单并将回执交给载体管理员；回执单可在回执单菜单查看和下载；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.11.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t39",
        entity="E-OUT", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="外送任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-OUT", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["外送任务终止；外送申请人需重新提交载体外送任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.11.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t40",
        entity="E-OUT", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交外送申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.11.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t41",
        entity="E-OUT", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入外送执行",
        role="载体管理员",
        preconditions=[
            precond(text="外送任务审批通过", ptype="state_ref",
                    ref=state_ref("E-OUT", "任务状态", "审批通过")),
            precond(text="载体管理员已接收外送交接单回执", ptype="event_ref"),
        ],
        expected_results=["载体管理员在线确认载体已外送；任务进入执行环节"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.11.3",
    )
    m.add_trans(
        tid="t42",
        entity="E-OUT", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认外送完成",
        role="载体管理员",
        preconditions=[
            precond(text="载体管理员在线确认外送完成", ptype="event_ref"),
        ],
        expected_results=["载体状态变为已外送；外送任务完成"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.11.3",
    )

    # ----- E-EXP 文件导出任务转换 -----
    m.add_trans(
        tid="t43",
        entity="E-EXP", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交导出申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="导出文件不大于2GB", ptype="constraint", ref=None),
            precond(text="份数在1~99之间", ptype="constraint", ref=None),
        ],
        expected_results=["导出申请提交至审批流程；任务状态变为待审批"],
        traits=["data_constraint"],
        direction="forward", priority="P0",
        source_ref="4.12.1",
    )
    m.add_trans(
        tid="t44",
        entity="E-EXP", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="导出任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-EXP", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后导出申请人可进行载体的导出；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.12.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t45",
        entity="E-EXP", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="导出任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-EXP", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["导出任务终止；导出申请人需重新提交导出任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.12.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t46",
        entity="E-EXP", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交导出申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="导出文件不大于2GB", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch", "data_constraint"],
        direction="forward", priority="P0",
        source_ref="4.12.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t47",
        entity="E-EXP", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入导出执行",
        role="载体管理员",
        preconditions=[
            precond(text="导出任务审批通过", ptype="state_ref",
                    ref=state_ref("E-EXP", "任务状态", "审批通过")),
        ],
        expected_results=["载体管理员在线确认载体已导出；任务进入执行环节"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.12.3",
    )
    m.add_trans(
        tid="t48",
        entity="E-EXP", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认导出完成",
        role="载体管理员",
        preconditions=[
            precond(text="载体管理员在线确认导出任务完成", ptype="event_ref"),
        ],
        expected_results=["任务完成后系统归档任务信息、导出记录及光盘信息；支持光盘编号管理"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.12；4.12.3",
    )

    # ----- E-SCN 文件扫描任务转换 -----
    m.add_trans(
        tid="t49",
        entity="E-SCN", dimension="任务状态",
        frm="草稿", to="待审批",
        action="提交扫描申请",
        role="普通用户",
        preconditions=[
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="文件页数在1~100之间", ptype="constraint", ref=None),
        ],
        expected_results=["扫描申请提交至审批流程；任务状态变为待审批"],
        traits=["data_constraint"],
        direction="forward", priority="P0",
        source_ref="4.13.1",
    )
    m.add_trans(
        tid="t50",
        entity="E-SCN", dimension="任务状态",
        frm="待审批", to="审批通过",
        action="审批通过",
        role="一级审批员",
        preconditions=[
            precond(text="扫描任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-SCN", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["审批通过后扫描申请人可进行文件的扫描；任务状态变为审批通过"],
        traits=["branch"],
        direction="forward", priority="P0",
        source_ref="4.13.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t51",
        entity="E-SCN", dimension="任务状态",
        frm="待审批", to="审批拒绝",
        action="审批拒绝",
        role="一级审批员",
        preconditions=[
            precond(text="扫描任务处于待审批状态", ptype="state_ref",
                    ref=state_ref("E-SCN", "任务状态", "待审批")),
            precond(text="任务级别为B级或C级", ptype="constraint", ref=None),
        ],
        expected_results=["扫描任务终止；扫描申请人需重新提交扫描任务"],
        traits=["branch"],
        direction="lateral", priority="P1",
        source_ref="4.13.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t52",
        entity="E-SCN", dimension="任务状态",
        frm="草稿", to="待执行",
        action="提交扫描申请（A级直入）",
        role="普通用户",
        preconditions=[
            precond(text="任务级别为A级", ptype="constraint", ref=None),
            precond(text="申请人已填写必填项", ptype="constraint", ref=None),
            precond(text="文件页数在1~100之间", ptype="constraint", ref=None),
        ],
        expected_results=["A级任务无需审批，提交后直接进入待执行状态"],
        traits=["branch", "data_constraint"],
        direction="forward", priority="P0",
        source_ref="4.13.2",
        note={"branch_dimension": "任务级别"},
    )
    m.add_trans(
        tid="t53",
        entity="E-SCN", dimension="任务状态",
        frm="审批通过", to="待执行",
        action="进入扫描执行",
        role="载体管理员",
        preconditions=[
            precond(text="扫描任务审批通过", ptype="state_ref",
                    ref=state_ref("E-SCN", "任务状态", "审批通过")),
        ],
        expected_results=["执行人操作扫描设备完成扫描；任务进入执行环节"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.13.3",
    )
    m.add_trans(
        tid="t54",
        entity="E-SCN", dimension="任务状态",
        frm="待执行", to="已完成",
        action="确认扫描完成",
        role="载体管理员",
        preconditions=[
            precond(text="载体管理员在线确认文件扫描完成", ptype="event_ref"),
        ],
        expected_results=["同时归档任务信息和扫描记录"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.13.3",
    )

    # ----- E-CAR 载体状态转换 -----
    m.add_trans(
        tid="t55",
        entity="E-CAR", dimension="载体状态",
        frm="已登记", to="已归档",
        action="载体归档",
        role="载体管理员",
        preconditions=[
            precond(text="载体处于已登记状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记")),
            precond(text="载体归档任务已完成", ptype="event_ref"),
        ],
        expected_results=["载体状态变为已归档；对已归档载体，无法进行移交、留存、回收、外送操作"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.7.3",
        note={"comment": "由 E-ARC 执行完成驱动；frm 已登记在 states 列表先于已归档，判 forward"},
    )
    m.add_trans(
        tid="t58",
        entity="E-CAR", dimension="载体状态",
        frm="已登记", to="已回收",
        action="载体回收",
        role="载体管理员",
        preconditions=[
            precond(text="载体处于可回收状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记")),
            precond(text="载体回收任务已完成", ptype="event_ref"),
        ],
        expected_results=["载体状态变为已回收"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.10.3",
        note={"comment": "由 E-RCY 执行完成驱动；已回收为终态"},
    )
    m.add_trans(
        tid="t59",
        entity="E-CAR", dimension="载体状态",
        frm="已登记", to="已外送",
        action="载体外送",
        role="载体管理员",
        preconditions=[
            precond(text="载体处于可外送状态", ptype="state_ref",
                    ref=state_ref("E-CAR", "载体状态", "已登记")),
            precond(text="载体外送任务已完成", ptype="event_ref"),
        ],
        expected_results=["载体状态变为已外送"],
        traits=[],
        direction="forward", priority="P0",
        source_ref="4.11.3",
        note={"comment": "由 E-OUT 执行完成驱动"},
    )
    m.add_trans(
        tid="t60",
        entity="E-CAR", dimension="载体状态",
        frm="已登记", to="已登记",
        action="载体到期提醒",
        role="system",
        preconditions=[
            precond(text="载体持有时间到期前12小时", ptype="constraint", ref=None,
                    note={"comment": "时间约束由 BR 承载"}),
        ],
        expected_results=["系统自动向持有人发送载体到期提醒；持有人可选择将载体进行归档、移交、回收、留存或者外送；到期不处理系统自动将此载体持有人用户进行功能限制"],
        traits=["time_sensitive"],
        direction="lateral", priority="P1",
        source_ref="4.6.5；4.9.3",
        note={"comment": "direction: frm=to 侧挂状态，判 lateral；状态本身不变，仅触发提醒"},
    )

    # ----- E-USER 用户状态转换 -----
    m.add_trans(
        tid="t61",
        entity="E-USER", dimension="用户状态",
        frm="正常", to="锁定",
        action="锁定用户",
        role="系统管理员",
        preconditions=[
            precond(text="用户处于正常状态", ptype="state_ref",
                    ref=state_ref("E-USER", "用户状态", "正常")),
        ],
        expected_results=["锁定后不得登录系统，状态变更为锁定"],
        traits=[],
        direction="lateral", priority="P1",
        source_ref="4.14.1（4）",
        note={"comment": "direction: 锁定为侧挂状态，判 lateral"},
    )
    m.add_trans(
        tid="t62",
        entity="E-USER", dimension="用户状态",
        frm="锁定", to="正常",
        action="解锁用户",
        role="系统管理员",
        preconditions=[
            precond(text="用户处于锁定状态", ptype="state_ref",
                    ref=state_ref("E-USER", "用户状态", "锁定")),
        ],
        expected_results=["解锁后可以登录系统"],
        traits=[],
        direction="resume", priority="P1",
        source_ref="4.14.1（5）",
        note={"comment": "direction: 从侧挂状态恢复，判 resume"},
    )
    m.add_trans(
        tid="t63",
        entity="E-USER", dimension="用户状态",
        frm="正常", to="锁定",
        action="连续输错密码锁定",
        role="system",
        preconditions=[
            precond(text="用户连续输错3次密码", ptype="constraint", ref=None),
        ],
        expected_results=["系统自动将此用户锁定"],
        traits=["time_sensitive"],
        direction="lateral", priority="P1",
        source_ref="4.3.1（2）",
        note={"comment": "direction: 锁定为侧挂状态，判 lateral"},
    )
    m.add_trans(
        tid="t64",
        entity="E-USER", dimension="用户状态",
        frm="正常", to="正常",
        action="功能限制",
        role="system",
        preconditions=[
            precond(text="持有人载体到期不进行处理", ptype="constraint", ref=None),
        ],
        expected_results=["系统自动将此载体持有人用户进行功能限制，不能发起登记、导入、导出、扫描流程"],
        traits=[],
        direction="lateral", priority="P1",
        source_ref="4.6.5；4.9.3",
        note={"comment": "direction: frm=to 同态，仅触发功能限制；用户状态本身不变但行为受限，记 lateral"},
    )

    # ----- E-DEPT 部门转换（新增/编辑/删除为 crud 不入转换；此处仅保留必要的状态型）
    # E-DEPT 无显式状态枚举，无转换型操作
    # ----- E-ROLE 角色授权/修改/删除（crud，不入转换）
    # ----- E-LOG 无状态枚举

    # ============================================================
    # Step 4.3 自检（前向引用回填）
    # ============================================================
    # Step 3 中 target_transition 使用语义描述，此处回填为精确 tid
    # 因 branch_dimension 仅声明在 E-IMP 上，且各任务实体均共用相同分支语义，
    # 以 E-IMP 的 t01/t02/t04 作为代表：
    #   - "任务提交转换（A级直入）" → t04
    #   - "一级审批通过转换" → t02
    #   - "二级审批通过转换" → t02（C 级二级审批在同 frm/to 上，作为分支差异由 BR 兑现）
    # 引用目标与实际输出一致，无需标 inferred。
    # （语义回填已在 Step 3 branches.desc 中体现，此处不再重复声明）

    # ============================================================
    # Step 4.4: 因果关系
    # ============================================================
    # 来源：expected_results 含对 E2 状态影响 / preconditions 含 state_ref 指向 E1 / 显式句式

    # 因果1：登记任务执行完成 → 载体状态变为已登记
    m.add_causal(
        frm="E-REG", to="E-CAR",
        desc="载体登记任务执行完成后，载体记入申请人台账，载体状态变为已登记",
        trigger="登记完成后，申请人能够看到本人名下的载体；载体记入申请人台账",
        trigger_source="expected_results",
        evidence_transitions=["t12"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "Q1 直接致变；Q2/Y 侧无 precondition 表达此因果；4.5 鉴别通过"},
    )
    # 因果2：归档任务执行完成 → 载体状态变为已归档
    m.add_causal(
        frm="E-ARC", to="E-CAR",
        desc="载体归档任务执行完成后，载体状态变为已归档",
        trigger="申请人能够看到本人名下的载体状态为已归档",
        trigger_source="expected_results",
        evidence_transitions=["t18", "t55"],
        rollback_propagation=True,
        confidence="high",
        note={"comment": "Q1 直接致变；归档含不可逆约束但归档任务本身可拒绝（rollback）"},
    )
    # 因果3：移交任务执行完成 → 载体归属人变更（属性级，状态不变）
    m.add_causal(
        frm="E-TRF", to="E-CAR",
        desc="载体移交任务执行完成后，载体归属人变更（接收人台账自动增加该载体）；载体状态不变（4.8.3 移交为归属人变更，非状态变化）",
        trigger="移交成功后，申请人台账中看不到此载体；接收人台账中自动增加此载体",
        trigger_source="expected_results",
        evidence_transitions=["t24"],
        rollback_propagation=False,
        confidence="high",
    )
    # 因果4：留存任务执行完成 → 载体持有时间增加（属性级，状态不变）
    m.add_causal(
        frm="E-RET", to="E-CAR",
        desc="载体留存任务执行完成后，载体持有时间自动增加；载体状态不变（4.9.3 留存为持有时间延长，非状态变化）",
        trigger="将当前用户所持有的载体持有时间自动增加",
        trigger_source="expected_results",
        evidence_transitions=["t30"],
        rollback_propagation=False,
        confidence="high",
    )
    # 因果5：回收任务执行完成 → 载体状态变为已回收
    m.add_causal(
        frm="E-RCY", to="E-CAR",
        desc="载体回收任务执行完成后，载体状态变为已回收",
        trigger="载体状态变为已回收",
        trigger_source="expected_results",
        evidence_transitions=["t36", "t58"],
        rollback_propagation=False,
        confidence="high",
    )
    # 因果6：外送任务执行完成 → 载体状态变为已外送
    m.add_causal(
        frm="E-OUT", to="E-CAR",
        desc="载体外送任务执行完成后，载体状态变为已外送",
        trigger="载体管理员在线确认载体已外送",
        trigger_source="expected_results",
        evidence_transitions=["t42", "t59"],
        rollback_propagation=False,
        confidence="high",
    )
    # 因果7：载体到期不处理 → 用户功能限制
    m.add_causal(
        frm="E-CAR", to="E-USER",
        desc="载体到期持有人不进行处理，系统自动将此载体持有人用户进行功能限制",
        trigger="如果持有人到期不进行处理，系统会自动将此载体持有人用户进行功能限制，不能发起登记、导入、导出、扫描流程",
        trigger_source="desc",
        evidence_transitions=["t60", "t64"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "Q1 直接致变；4.5 鉴别通过"},
    )
    # 因果8：用户连续输错密码 → 用户锁定
    m.add_causal(
        frm="E-USER", to="E-USER",
        desc="用户连续输错3次密码，系统自动将此用户锁定",
        trigger="用户连续输错3次密码，系统自动将此用户锁定",
        trigger_source="desc",
        evidence_transitions=["t63"],
        rollback_propagation=False,
        confidence="high",
        note={"comment": "同实体因果；自驱动"},
    )

    # ============================================================
    # Step 3.5: 创建转换（C02：每实体初始状态必须有 from=None 创建转换）
    # 申请/载体/用户在创建时初始化各自初始状态。
    # 创建转换不带跨实体 state_ref 前置——C04 会给 from=None 生成
    # target_condition=状态=None 的坏镜像，故用空前置 + note 说明触发。
    # ============================================================
    m.add_trans(
        tid="t65",
        entity="E-IMP", dimension="任务状态",
        frm=None, to="草稿",
        action="新建导入申请",
        role="普通用户",
        preconditions=[],
        expected_results=["导入任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.5.1（1）",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t66",
        entity="E-REG", dimension="任务状态",
        frm=None, to="草稿",
        action="新建登记申请",
        role="普通用户",
        preconditions=[],
        expected_results=["登记任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.6.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t67",
        entity="E-ARC", dimension="任务状态",
        frm=None, to="草稿",
        action="新建归档申请",
        role="普通用户",
        preconditions=[],
        expected_results=["归档任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.7.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t68",
        entity="E-TRF", dimension="任务状态",
        frm=None, to="草稿",
        action="新建移交申请",
        role="普通用户",
        preconditions=[],
        expected_results=["移交任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.8.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t69",
        entity="E-RET", dimension="任务状态",
        frm=None, to="草稿",
        action="新建留存申请",
        role="普通用户",
        preconditions=[],
        expected_results=["留存任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.9.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t70",
        entity="E-RCY", dimension="任务状态",
        frm=None, to="草稿",
        action="新建回收申请",
        role="普通用户",
        preconditions=[],
        expected_results=["回收任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.10.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t71",
        entity="E-OUT", dimension="任务状态",
        frm=None, to="草稿",
        action="新建外送申请",
        role="普通用户",
        preconditions=[],
        expected_results=["外送任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.11.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t72",
        entity="E-EXP", dimension="任务状态",
        frm=None, to="草稿",
        action="新建导出申请",
        role="普通用户",
        preconditions=[],
        expected_results=["导出任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.12.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    m.add_trans(
        tid="t73",
        entity="E-SCN", dimension="任务状态",
        frm=None, to="草稿",
        action="新建扫描申请",
        role="普通用户",
        preconditions=[],
        expected_results=["扫描任务创建，状态初始化为草稿"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.13.1",
        note={"comment": "申请创建即初始化草稿；4.4 通用功能含新增"},
    )
    # 载体：登记执行完成后由"不存在"变为已登记（XC x10 联动）；无前置避免 C04 坏镜像
    m.add_trans(
        tid="t74",
        entity="E-CAR", dimension="载体状态",
        frm=None, to="已登记",
        action="载体创建",
        role="system",
        preconditions=[],
        expected_results=["载体由登记执行完成产生，状态初始化为已登记"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.6.3",
        note={"comment": "载体由 E-REG 登记执行产生（XC x10 联动），产生后独立流转；E-REG→E-CAR 为 reference（登记任务是来源，非归属容器）"},
    )
    # 用户：仅系统管理员可新增，归属部门为组织分类配置（E-DEPT→E-USER reference）
    m.add_trans(
        tid="t75",
        entity="E-USER", dimension="用户状态",
        frm=None, to="正常",
        action="新建用户",
        role="系统管理员",
        preconditions=[],
        expected_results=["用户创建，状态初始化为正常"],
        traits=[], direction="forward", priority="P0",
        source_ref="4.14.1（1）",
        note={"comment": "仅系统管理员可新增用户；必填申请部门（E-DEPT→E-USER reference 提供组织分类）"},
    )

    # ============================================================
    # Step 5: 约束补充
    # ============================================================
    # ---------- XC 跨实体约束 ----------

    # 镜像 XC：归档任务 preconditions 中含载体状态约束，镜像至 XC
    m.add_xc(
        xid="x01",
        source_entity="E-ARC", source_transition="t13", source_state="待审批",
        target_entity="E-CAR", target_dimension="载体状态",
        target_condition="状态=已登记",
        desc="镜像T-t13 precondition'载体处于已登记状态'",
        source_ref="4.7.1；4.7.3",
    )
    # 4.5 判约束：归档后无法移交/留存/回收/外送（已归档载体操作门禁）
    m.add_xc(
        xid="x02",
        source_entity="E-ARC", source_transition="t18", source_state="已完成",
        target_entity="E-TRF", target_dimension="任务状态",
        target_condition="载体已归档时禁止发起移交任务",
        desc="由 Step 4.5 约束-因果鉴别确认：已归档载体无法发起移交任务（载体状态为已归档时禁止移交）",
        source_ref="4.7.3",
    )
    m.add_xc(
        xid="x03",
        source_entity="E-ARC", source_transition="t18", source_state="已完成",
        target_entity="E-RET", target_dimension="任务状态",
        target_condition="载体已归档时禁止发起留存任务",
        desc="由 Step 4.5 约束-因果鉴别确认：已归档载体无法发起留存任务",
        source_ref="4.7.3",
    )
    m.add_xc(
        xid="x04",
        source_entity="E-ARC", source_transition="t18", source_state="已完成",
        target_entity="E-RCY", target_dimension="任务状态",
        target_condition="载体已归档时禁止发起回收任务",
        desc="由 Step 4.5 约束-因果鉴别确认：已归档载体无法发起回收任务",
        source_ref="4.7.3",
    )
    m.add_xc(
        xid="x05",
        source_entity="E-ARC", source_transition="t18", source_state="已完成",
        target_entity="E-OUT", target_dimension="任务状态",
        target_condition="载体已归档时禁止发起外送任务",
        desc="由 Step 4.5 约束-因果鉴别确认：已归档载体无法发起外送任务",
        source_ref="4.7.3",
    )
    # 4.5 判约束：载体到期不处理 → 用户功能限制（不能发起登记/导入/导出/扫描）
    m.add_xc(
        xid="x06",
        source_entity="E-CAR", source_transition="t60", source_state="已登记",
        target_entity="E-REG", target_dimension="任务状态",
        target_condition="载体到期持有人不处理时禁止发起登记任务",
        desc="由 Step 4.5 约束-因果鉴别确认：载体到期持有人不处理，用户不能发起登记任务",
        source_ref="4.6.5；4.9.3",
    )
    m.add_xc(
        xid="x07",
        source_entity="E-CAR", source_transition="t60", source_state="已登记",
        target_entity="E-IMP", target_dimension="任务状态",
        target_condition="载体到期持有人不处理时禁止发起导入任务",
        desc="由 Step 4.5 约束-因果鉴别确认：载体到期持有人不处理，用户不能发起导入任务",
        source_ref="4.6.5；4.9.3",
    )
    m.add_xc(
        xid="x08",
        source_entity="E-CAR", source_transition="t60", source_state="已登记",
        target_entity="E-EXP", target_dimension="任务状态",
        target_condition="载体到期持有人不处理时禁止发起导出任务",
        desc="由 Step 4.5 约束-因果鉴别确认：载体到期持有人不处理，用户不能发起导出任务",
        source_ref="4.6.5；4.9.3",
    )
    m.add_xc(
        xid="x09",
        source_entity="E-CAR", source_transition="t60", source_state="已登记",
        target_entity="E-SCN", target_dimension="任务状态",
        target_condition="载体到期持有人不处理时禁止发起扫描任务",
        desc="由 Step 4.5 约束-因果鉴别确认：载体到期持有人不处理，用户不能发起扫描任务",
        source_ref="4.6.5；4.9.3",
    )
    # 联动 XC：登记执行后载体状态由"不存在"变为"已登记"
    m.add_xc(
        xid="x10",
        source_entity="E-REG", source_transition="t12", source_state="已完成",
        target_entity="E-CAR", target_dimension="载体状态",
        target_condition="由未创建变为已登记",
        desc="联动:T-t12执行后E-CAR.载体状态由未创建变为已登记",
        source_ref="4.6.3",
    )
    # 联动 XC：移交/留存 为属性级操作（归属人变更/持有时间延长），不改载体状态，
    # 效果经因果边 E-TRF→E-CAR / E-RET→E-CAR 表达（4.8.3 / 4.9.3），无 XC 联动。

    # ---------- IT 无效转换 ----------
    m.add_invalid(
        iid="i03",
        entity="E-CAR",
        frm="已归档", to="已回收",
        reason="对已归档载体，无法进行回收操作",
        source_ref="4.7.3",
    )
    m.add_invalid(
        iid="i04",
        entity="E-CAR",
        frm="已归档", to="已外送",
        reason="对已归档载体，无法进行外送操作",
        source_ref="4.7.3",
    )
    m.add_invalid(
        iid="i05",
        entity="E-CAR",
        frm="已回收", to="已归档",
        reason="已回收为终态，不可再归档",
        source_ref="4.10.3",
    )
    m.add_invalid(
        iid="i06",
        entity="E-USER",
        frm="锁定", to="正常",
        reason="锁定用户不可直接登录恢复正常，须由系统管理员执行解锁操作",
        source_ref="4.3.1（3）；4.14.1（5）",
    )

    # ---------- BR 业务规则 ----------
    # 登录与会话相关
    m.add_br(
        bid="b01",
        category="timing",
        desc="用户连续输错3次密码，系统自动将此用户锁定",
        entities_involved=["E-USER"],
        source_ref="4.3.1（2）",
        signal_type="restrictive",
    )
    m.add_br(
        bid="b02",
        category="authorization",
        desc="状态为'锁定'或'不存在'的用户不允许登录系统并给出对应提示信息",
        entities_involved=["E-USER"],
        source_ref="4.3.1（3）",
        signal_type="restrictive",
    )
    m.add_br(
        bid="b03",
        category="validation",
        desc="用户密码输入错误，经系统认证后应返回'用户名或密码错误'提示",
        entities_involved=["E-USER"],
        source_ref="4.3.1（4）",
        signal_type="display",
    )
    m.add_br(
        bid="b04",
        category="timing",
        desc="用户登录后无操作30分钟，系统自动退出登录",
        entities_involved=["E-USER"],
        source_ref="4.3.1（7）",
        signal_type="restrictive",
    )
    m.add_br(
        bid="b05",
        category="usability",
        desc="用户登录成功后，应在进入的功能操作页面右上角显示登录人员的名称；根据登录人员被指定的角色进入相应的页面，主菜单/功能操作、子菜单依据角色的不同而显示不同",
        entities_involved=["E-USER", "E-ROLE"],
        source_ref="4.3.1（5）；4.3.1（6）",
        signal_type="display",
    )
    m.add_br(
        bid="b06",
        category="usability",
        desc="退出系统时应给出确认信息，只有确定后才可以退出，否则不能退出系统，保持当前操作页面和用户状态",
        entities_involved=["E-USER"],
        source_ref="4.3.2（2）",
        signal_type="restrictive",
    )
    # 通用功能
    m.add_br(
        bid="b07",
        category="usability",
        desc="新增、编辑页面中的必填项应给出*标识，对未输入的必填项给出提示；有约束的必填项，输入不符合约束时应给出提示",
        entities_involved=["E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.19（6）；4.19（7）",
        signal_type="field_constraint",
    )
    m.add_br(
        bid="b08",
        category="usability",
        desc="查询功能中的组合查询支持一个（含）以上字段'与'的模糊查询",
        entities_involved=["E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.19（5）；4.4（6）",
        signal_type="usability",
    )
    m.add_br(
        bid="b09",
        category="usability",
        desc="对操作支持可逆性处理，有取消或者关闭操作",
        entities_involved=["E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.19（4）；4.4（8）；4.4（9）",
        signal_type="usability",
    )
    # 任务级别分支约束（4.5.2/4.6.2/…/4.13.2 同文重复，是一个规则适用于全部 9 类任务实体）
    # 曾拆成 9 条相同文本 BR（每实体一条），被 _backfill_branch_coverage 全部挂进 E-IMP 分支维度
    # → EO-ATC-001 配置用例 Then 重复 9 次（PROC-013/014/015）。合并为一条，source_ref 并列全条款。
    m.add_br(
        bid="b10",
        category="authorization",
        desc="任务级别为A级无需审批，提交后直接进入待执行；B级需经过一级审批；C级需经过二级审批",
        entities_involved=["E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.5.2；4.6.2；4.7.2；4.8.2；4.9.2；4.10.2；4.11.2；4.12.2；4.13.2",
        signal_type="restrictive",
        note={"branch_dimension": "任务级别"},
    )
    # 导入超时
    m.add_br(
        bid="b19",
        category="timing",
        desc="导入任务执行完成后如未进行确认，系统会在48小时后结束此任务，导入文件自动从系统中删除",
        entities_involved=["E-IMP"],
        source_ref="4.5.3",
        signal_type="restrictive",
    )
    # 载体持有时间
    m.add_br(
        bid="b20",
        category="timing",
        desc="载体登记成功之后，载体记入申请人台账中，持有时间默认为72小时；在到期前12小时，系统会自动向持有人发送载体到期提醒",
        entities_involved=["E-CAR", "E-REG"],
        source_ref="4.6.5",
        signal_type="field_constraint",
        note={"comment": "含默认值72小时，按优先级 field_constraint > restrictive"},
    )
    m.add_br(
        bid="b21",
        category="authorization",
        desc="如果持有人到期不进行处理，系统会自动将此载体持有人用户进行功能限制，不能发起登记、导入、导出、扫描流程",
        entities_involved=["E-CAR", "E-USER", "E-REG", "E-IMP", "E-EXP", "E-SCN"],
        source_ref="4.6.5",
        signal_type="restrictive",
    )
    # 留存时间约束
    m.add_br(
        bid="b22",
        category="validation",
        desc="留存时间只能填入1~48之间的整数；留存最长可增加48小时持有时间",
        entities_involved=["E-RET", "E-CAR"],
        source_ref="4.9.1；4.9",
        signal_type="field_constraint",
    )
    # 导出文件约束
    m.add_br(
        bid="b23",
        category="validation",
        desc="导出文件不大于2GB；份数输入1~99数字；上传文件名中必须标明文件级别，例如:导出文件(A级)；级别可以使用中英文圆括号和中括号标记",
        entities_involved=["E-EXP"],
        source_ref="4.12.1（5）；4.12.1（2）",
        signal_type="field_constraint",
    )
    # 扫描文件约束
    m.add_br(
        bid="b24",
        category="validation",
        desc="文件页数只能填入1~100之间的数字",
        entities_involved=["E-SCN"],
        source_ref="4.13.1（2）",
        signal_type="field_constraint",
    )
    # 登记纸张页数约束
    m.add_br(
        bid="b25",
        category="validation",
        desc="载体类别为纸质时，纸张页数必填；数值范围1-9999",
        entities_involved=["E-REG"],
        source_ref="4.6.1（1）；4.6.1（2）",
        signal_type="field_constraint",
    )
    # 用户账号约束
    m.add_br(
        bid="b26",
        category="validation",
        desc="用户账号可以由汉字、小写字母、数字、下划线(_)组成；不可重复；不可修改",
        entities_involved=["E-USER"],
        source_ref="4.14.1 表4.14.1-1（1）；4.14.1（2）",
        signal_type="field_constraint",
    )
    m.add_br(
        bid="b27",
        category="validation",
        desc="登录密码由数字、大小写字母和特殊符号组成；长度大于等于8个字符小于等于18个字符；密码设置时长度在8到18位，要包含大小写字母、数字和特殊字符",
        entities_involved=["E-USER"],
        source_ref="4.14.1 表4.14.1-1（3）；4.18（3）",
        signal_type="field_constraint",
    )
    m.add_br(
        bid="b28",
        category="validation",
        desc="手机号码第一位数字1，第二位数字:3、4、5、6、7、8、9，一共11位数字；唯一",
        entities_involved=["E-USER"],
        source_ref="4.14.1 表4.14.1-1（5）",
        signal_type="field_constraint",
    )
    m.add_br(
        bid="b29",
        category="validation",
        desc="邮箱必须包含@和.；不能包含中文、其它特殊符号",
        entities_involved=["E-USER"],
        source_ref="4.14.1 表4.14.1-1（6）",
        signal_type="field_constraint",
    )
    # 密码修改约束
    m.add_br(
        bid="b30",
        category="validation",
        desc="修改密码需要输入原密码，如果输入的原密码不对，则给出相应提示；新密码与原密码应不同，否则系统给出提示；新密码需要确认，输入两次且相同，否则系统给出提示",
        entities_involved=["E-USER"],
        source_ref="4.18（4）；4.18（5）；4.18（6）",
        signal_type="restrictive",
    )
    m.add_br(
        bid="b31",
        category="validation",
        desc="密码不以明文显示",
        entities_involved=["E-USER"],
        source_ref="4.18（2）",
        signal_type="display",
    )
    # 用户删除约束
    m.add_br(
        bid="b32",
        category="authorization",
        desc="具有流程信息的用户不能进行删除",
        entities_involved=["E-USER"],
        source_ref="4.14.1（7）",
        signal_type="restrictive",
    )
    # 部门约束
    m.add_br(
        bid="b33",
        category="authorization",
        desc="不能删除修改根部门；被客户使用的部门不能进行必填项信息的修改；被客户使用和实验单使用的部门不能进行删除",
        entities_involved=["E-DEPT"],
        source_ref="4.14.3；4.14.3（2）；4.14.3（3）",
        signal_type="restrictive",
    )
    m.add_br(
        bid="b34",
        category="validation",
        desc="部门名称必填项；名称唯一",
        entities_involved=["E-DEPT"],
        source_ref="4.14.3 表4.14.3-1（1）",
        signal_type="field_constraint",
    )
    # 日志可见性
    m.add_br(
        bid="b35",
        category="authorization",
        desc="系统的日志管理只对日志管理员和角色管理员开放；系统日志记录只能由日志管理员和角色管理员查看",
        entities_involved=["E-LOG", "E-ROLE"],
        source_ref="4.17；4.18（7）",
        signal_type="restrictive",
    )
    m.add_br(
        bid="b36",
        category="validation",
        desc="登录日志至少记录用户登录日志；操作日志至少记录用户信息的新增、编辑、删除；系统日志可以记录事件的时间、操作人和日志类型等",
        entities_involved=["E-LOG"],
        source_ref="4.17.1；4.18（8）",
        signal_type="restrictive",
        note={"comment": "含'至少'最低数量约束，按优先级 restrictive > usability"},
    )
    # 日志导出
    m.add_br(
        bid="b37",
        category="usability",
        desc="日志导出根据起始时间完成导出成Excel文件操作；可选择导出后删除导出项",
        entities_involved=["E-LOG"],
        source_ref="4.17.2（1）",
        signal_type="usability",
    )
    # 角色管理
    m.add_br(
        bid="b38",
        category="authorization",
        desc="角色管理员可授权普通用户、一级审批员、二级审批员、载体管理员和监督员；删除角色后用户角色默认为普通用户",
        entities_involved=["E-ROLE", "E-USER"],
        source_ref="4.16.1；4.16.2；4.16.3",
        signal_type="field_constraint",
        note={"comment": "含默认值'普通用户'，按优先级 field_constraint > restrictive"},
    )
    # 内置角色不可改
    m.add_br(
        bid="b39",
        category="authorization",
        desc="本样品内置3个角色（系统管理员、监督员、日志管理员），不可对其进行更改、删除；系统管理员角色绑定系统管理员用户(sysadmin_a)、监督员(secadmin_a)和日志管理员(secauditor_a)，不可更改、删除和禁用，也不授予其他用户",
        entities_involved=["E-ROLE", "E-USER"],
        source_ref="5；5",
        signal_type="restrictive",
    )
    # 安全性提示信息约束
    m.add_br(
        bid="b40",
        category="display",
        desc="提示信息不能含有系统运行、技术架构等信息",
        entities_involved=["E-USER"],
        source_ref="4.18（9）",
        signal_type="restrictive",
    )
    # 易用性
    m.add_br(
        bid="b41",
        category="usability",
        desc="对用户账号或者密码错误的输入有提示；用户不存在时，登录系统时可被证实",
        entities_involved=["E-USER"],
        source_ref="4.19（1）；4.19（3）",
        signal_type="display",
    )
    m.add_br(
        bid="b42",
        category="usability",
        desc="日期类数据输入，应提供日历选择功能",
        entities_involved=["E-USER", "E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.19（2）",
        signal_type="usability",
    )
    # 基于角色访问控制
    m.add_br(
        bid="b43",
        category="authorization",
        desc="实现基于角色的访问控制",
        entities_involved=["E-ROLE", "E-USER"],
        source_ref="4.18（1）",
        signal_type="restrictive",
    )
    # 留存到期提醒
    m.add_br(
        bid="b44",
        category="notification",
        desc="在载体里留存时间到期前12小时，系统会自动向持有人发送载体到期提醒，持有人可选择将载体进行归档、移交、回收、留存或者外送",
        entities_involved=["E-CAR", "E-RET"],
        source_ref="4.9.3",
        signal_type="usability",
        note={"comment": "含'可选择'，匹配 usability；无 restrictive/display/field_constraint 强信号"},
    )
    # 流水号生成
    m.add_br(
        bid="b45",
        category="computation",
        desc="流水号系统自动生成，规则为:任务类型+申请时间+流水序号",
        entities_involved=["E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.5.1 表4.5-1（3）；4.6.1；4.7.1；4.8.1；4.9.1；4.10.1；4.11.1；4.12.1；4.13.1",
        signal_type="field_constraint",
    )
    # 申请人/部门自动获取
    m.add_br(
        bid="b46",
        category="computation",
        desc="申请人、申请部门根据登录用户自动获取",
        entities_involved=["E-IMP", "E-REG", "E-ARC", "E-TRF", "E-RET", "E-RCY", "E-OUT", "E-EXP", "E-SCN"],
        source_ref="4.5.1 表4.5-1（1）（2）；4.6.1；4.7.1；4.8.1；4.9.1；4.10.1；4.11.1；4.12.1；4.13.1",
        signal_type="field_constraint",
    )

    return m
