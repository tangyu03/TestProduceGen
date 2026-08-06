"""全部枚举常量集中于此。prompt 修订（如新增 trait、direction）时只改本文件。"""

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
