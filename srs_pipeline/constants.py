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

# Step 5 XC desc 四来源前缀约定（分类由 desc 前缀承载，INV-8 只认此集）
XC_DESC_PREFIXES = ("镜像", "由 Step 4.5", "联动", "分支[")
