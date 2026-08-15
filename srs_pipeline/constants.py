"""全部枚举常量集中于此。prompt 修订（如新增 trait、direction）时只改本文件。"""
import re

OP_CATEGORIES = ("session", "ui", "file", "query", "crud", "config")
PRECOND_TYPES = ("state_ref", "event_ref", "constraint")
TRAITS = ("audit", "rollback", "branch", "time_sensitive", "data_constraint")
DIRECTIONS = ("forward", "backward", "lateral", "resume")
PRIORITIES = ("P0", "P1", "P2")
RELATION_TYPES = ("composition", "reference", "hierarchy", "self_reference")
CARDINALITIES = ("1:N", "1:1", "M:N")                      # 永不 N:1
OWNERSHIP_DIMS = ("business_ownership", "management_dimension", "configuration_source")
TRIGGER_SOURCES = ("cross_entity", "action", "expected_results",
                   "desc", "business_rule", "bidi_coupling")
BR_CATEGORIES = ("validation", "computation", "authorization",
                 "timing", "notification", "usability", "display")
BR_SIGNALS = ("restrictive", "usability", "display", "field_constraint")
BR_ENFORCEMENTS = ("mandatory", "conditional")
ENTITY_TYPES = ("core", "managed")
TAGS = ("approvable", "multi-state", "expirable", "collaborative", "configurable")
CONFIDENCE = ("high", "medium", "low")
RESERVED_ROLES = ("system", "系统")                        # 4.3：保留角色(英/中)，引用校验豁免

# 铁律8：trigger_source 优先级（索引小者优先级高，去重仅升级不降级）
TRIGGER_PRIORITY = {name: i for i, name in enumerate(TRIGGER_SOURCES)}

# Step 2 联动约束：composition↔business_ownership，reference↔configuration_source
OWNERSHIP_BY_RELATION = {"composition": "business_ownership",
                         "reference": "configuration_source"}

# 铁律14：局部标签形态（t01/t07a/tp01/p04/u01/o01/s01/x01/b01/i01 等），
# 编号移交前数据文件统一用此形态；编号移交（_assign_ids）按此改写交叉引用。
# 中文需求文本中"小写字母+数字"几乎必是标签，误伤可忽略。
LOCAL_LABEL = re.compile(r"\b[a-z]{1,3}\d{2,3}[a-z]?\b")

# Step 5 XC 四来源分类（add_xc 的 xc_source 枚举；desc 前缀由框架按此生成）
XC_SOURCES = ("镜像", "4.5判", "联动", "分支差异")

# 最终 desc 形态（前缀 + 注入标签 + 语义内容，单一真相源）。{label} 由 assemble
# 在 _assign_ids 改写后注入正式号：
#   镜像/分支差异 → target_transition（消费者/持有跨实体前置条件的转换，与 C04 同源）
#   联动          → source_transition（触发联动的生产者，与手工数据同源）
#   4.5判         → 无 label
XC_DESC_TPL = {
    "镜像":    "镜像 {label} {desc}",
    "4.5判":   "由 Step 4.5 约束-因果鉴别确认：{desc}",
    "联动":    "联动: {label}{desc}",
    "分支差异": "分支[{label}]{desc}",
}

# 旧数据（golden 冻结）desc 前缀 → (来源, 剥掉前缀后语义) 的向后兼容正则表。
# 命中即反推 xc_source 并剥掉前缀+残留"T-tXX"标签，供 assemble 统一重建。
XC_LEGACY_RE = (
    ("镜像",  re.compile(r"^镜像\s*(?:T-?)?[a-z]?\d+[a-z]?\s*")),
    ("4.5判", re.compile(r"^由\s*Step\s*4\.\d\s*约束-因果鉴别确认[：:]?\s*")),
    ("联动",  re.compile(r"^联动:?\s*(?:T-?)?[a-z]?\d+[a-z]?\s*")),
    ("分支差异", re.compile(r"^分支\[.*?\]\s*")),
)
