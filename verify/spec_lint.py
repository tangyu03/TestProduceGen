#!/usr/bin/env python3
"""spec_lint — case_spec.json 自身的一致性校验（评审者的评审者）。

定位：每次修改 case_spec 后强制先跑本脚本，再跑 validators。
case_spec 只承载模型无法表达的 4 类测试设计事实（guard_policies /
built_in_entities / dimension_constraints / time_control.allowed_mechanisms），
其自身缺陷（如 guard cond 含表达式导致永不命中）会让整个校验体系把错误当标准。

检查分组（E=error 阻断，W=warning 提示）：
  GP  守卫规则：id 唯一、expected 档位、cond 禁表达式、assertion_pattern 非空、clause
  BI  内置对象：readonly/no_form_page 实体格式
  DC  维度约束：invalid_combos 非空、键名可识别
  TC  超时控制：allowed_mechanisms 非空
  ID  全局：guard_id 全局唯一

状态机/动作目录/角色矩阵/覆盖矩阵的一致性已由模型承载（coverage_obligations.json），
不属于 case_spec 的 lint 范围——case_spec 不再重复这些段。

用法：
  python -m verify.spec_lint -s verify/case_spec.json
  python -m verify.spec_lint -s verify/case_spec.json --json lint_report.json
退出码：有 error → 1，否则 0。
"""
import argparse
import json
import sys
from pathlib import Path

EXPR_SYMBOLS = ("!=", ">=", "<=", "==", "∈", "∉")
KNOWN_COMBO_KEYS = {"current", "pre_pause", "other_dim", "note", "match_mode"}
EXPECTED_LEVELS = {"rejected", "confirm"}


class Reporter:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, cat, msg):
        self.errors.append({"cat": cat, "msg": msg})

    def warn(self, cat, msg):
        self.warnings.append({"cat": cat, "msg": msg})

    def summary(self):
        return {"errors": self.errors, "warnings": self.warnings,
                "error_count": len(self.errors), "warning_count": len(self.warnings)}


def lint_guard_policies(spec, rep):
    policies = spec.get("guard_policies") or []
    seen = set()
    for pol in policies:
        gid = pol.get("guard_id")
        if not gid:
            rep.err("GP", "guard_policy missing guard_id")
            continue
        if gid in seen:
            rep.err("GP", f"duplicate guard_id: {gid}")
        seen.add(gid)
        if pol.get("expected") not in EXPECTED_LEVELS:
            rep.err("GP", f"{gid}: expected must be one of {sorted(EXPECTED_LEVELS)}")
        cond = pol.get("when_given_matches", "") or ""
        if not cond:
            rep.err("GP", f"{gid}: empty when_given_matches")
        elif any(s in cond for s in EXPR_SYMBOLS):
            rep.err("GP", f"{gid}: cond contains expression symbols {cond!r}; "
                          f"case givens can never textually match it (silent miss)")
        if not (pol.get("assertion_pattern") or "").strip():
            rep.err("GP", f"{gid}: empty assertion_pattern")
        if not pol.get("clause"):
            rep.warn("GP", f"{gid}: missing clause")


def lint_built_in(spec, rep):
    bi = spec.get("built_in_entities") or {}
    for ent in bi.get("readonly") or []:
        if not (isinstance(ent, str) and ent.strip()):
            rep.err("BI", f"readonly entity invalid: {ent!r}")
    for ent in bi.get("no_form_page") or []:
        if not (isinstance(ent, str) and ent.strip()):
            rep.err("BI", f"no_form_page entity invalid: {ent!r}")


def lint_dimension_constraints(spec, rep):
    for c in spec.get("dimension_constraints") or []:
        name = c.get("name", "?")
        combos = c.get("invalid_combos")
        if not combos:
            rep.warn("DC", f"constraint '{name}': empty invalid_combos (inert)")
            continue
        for combo in combos:
            unknown = set(combo.keys()) - KNOWN_COMBO_KEYS
            if unknown:
                rep.warn("DC", f"constraint '{name}': unknown combo keys {sorted(unknown)}")


def lint_time_control(spec, rep):
    tc = spec.get("time_control") or {}
    if not tc.get("allowed_mechanisms"):
        rep.err("TC", "time_control.allowed_mechanisms empty")


def lint_global_ids(spec, rep):
    gids = set()
    for pol in spec.get("guard_policies") or []:
        gid = pol.get("guard_id")
        if gid:
            if gid in gids:
                rep.err("ID", f"guard_id duplicated: {gid}")
            gids.add(gid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", "-s", required=True)
    ap.add_argument("--json", "-j", default=None)
    args = ap.parse_args()
    spec_path = Path(args.spec)
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    rep = Reporter()
    lint_guard_policies(spec, rep)
    lint_built_in(spec, rep)
    lint_dimension_constraints(spec, rep)
    lint_time_control(spec, rep)
    lint_global_ids(spec, rep)

    report = rep.summary()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
    for e in report["errors"]:
        print(f"  [E:{e['cat']}] {e['msg']}")
    for w in report["warnings"]:
        print(f"  [W:{w['cat']}] {w['msg']}")
    print(f"spec_lint: {report['error_count']} errors, {report['warning_count']} warnings")
    sys.exit(1 if report["error_count"] else 0)


if __name__ == "__main__":
    main()
