"""Shared types and helpers for Gate-S checks."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    check_id: str
    result: str = "pass"                # pass | fail | skipped
    severity: str = "blocker"           # blocker | warning
    fail_count: int = 0
    evidence: list = field(default_factory=list)
    suspected_stage: str = ""
    suspected_files: list = field(default_factory=list)
    note: str = ""

    def fail(self, item: Any):
        self.result = "fail"
        self.fail_count += 1
        self.evidence.append(item)

    def skip(self, note: str):
        self.result = "skipped"
        self.note = note

    def to_dict(self) -> dict:
        # When the check passes (fail_count=0), auto-generate a human-readable
        # pass_reason if note is empty — so verdict.json readers can understand
        # WHY the check passed without digging into the code.
        note = self.note
        if self.result == "pass" and self.fail_count == 0 and not note:
            note = self._default_pass_reason()
        return {
            "check_id": self.check_id,
            "result": self.result,
            "severity": self.severity,
            "fail_count": self.fail_count,
            "evidence": self.evidence[:50],          # verdict 体积上限
            "evidence_truncated": max(0, len(self.evidence) - 50),
            "suspected_stage": self.suspected_stage,
            "suspected_files": self.suspected_files,
            "note": note,
        }

    def _default_pass_reason(self) -> str:
        """Auto-generate a pass reason based on check_id.

        Each check has a distinct semantic — this method produces a short
        human-readable explanation of what was verified, so that verdict.json
        readers don't see an empty note and wonder if the check actually ran.
        """
        reasons = {
            "V01": "依赖图健康检查通过：无悬空引用、无依赖环、依赖相位单调（所有 proc 的 phase ≥ 其依赖的 phase）",
            "V02": "守卫极性检查通过：所有命中禁止规则的 proc 都断言了拒绝/提示，无成功迁移误断言",
            "V03": "动作归属检查通过：跨实体级联均使用 indirect_via，未直接操作从动实体",
            "V04": "内置对象保护检查通过：readonly/no_form_page 实体未被误建 type3/9 义务",
            "V05": "维度组合检查通过：实例化前 dimension_constraints 可达性剪枝无冲突",
            "V06": "时间控制检查通过：超时事件均声明了 mechanism",
            "V07": "角色权限检查通过：when.actor 均在 role_permissions.matrix 内",
            "V08": "相位一致性检查通过：终态=最大相位、forward 迁移相位递增、状态未坍缩",
            "V09": "去重检查通过：无重复 (givens,when,thens) 合并、单例实体未复制",
            "V10": "覆盖矩阵检查通过：coverage_matrix 所有 probe 均在 procedure 文本中命中",
        }
        return reasons.get(self.check_id, "检查通过，无违规项")


def normalize_text(s: Any) -> str:
    """折叠空白，用于稳定比较与哈希。"""
    return re.sub(r"\s+", "", str(s or ""))


def text_hash(obj: Any) -> str:
    import json
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def get_procedures(output: dict) -> list:
    return output.get("procedures", []) or []


def entity_alias(entity: str, known: set) -> str:
    """虚拟实体名归一：项目B/项目A/项目H → 项目（剥掉尾部单个大写字母）。"""
    if entity in known:
        return entity
    if entity and entity[-1].isupper() and entity[:-1] in known:
        return entity[:-1]
    return entity
