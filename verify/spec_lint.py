#!/usr/bin/env python3
"""spec_lint — case_spec.json 自身的一致性校验（评审者的评审者）。

定位：每次修改 case_spec 后强制先跑本脚本，再跑 validators。
case_spec 是门禁的真实依据，其自身缺陷（如 forward 迁移相位倒退、
guard cond 含表达式导致永不命中）会让整个校验体系把错误当标准。

检查分组（E=error 阻断，W=warning 提示）：
  SM  状态机：相位-迁移一致性、终态可达、backward/lateral 须含章节依据 note
  GP  守卫规则：id 唯一、expected 档位、cond 禁表达式、action 可解析到动作目录
  BI  内置对象：字段格式、实体可见性、readonly 不得出现在动作目录
  AR  动作目录与角色矩阵：迁移 actor 合法、矩阵动作可映射到目录
  DC  维度约束：invalid_combos 非空、键名可识别
  TC  超时控制：机制清单非空、time_control_required 迁移的 trigger 含时间词
  CM  覆盖矩阵：clause 格式、boundary 须配模板、oracle 引用函数必须存在
  ID  全局：transition/guard id 全局唯一

用法：
  python -m verify.spec_lint -s verify/case_spec.json
  python -m verify.spec_lint -s verify/case_spec.json --json lint_report.json
退出码：有 error → 1，否则 0。
"""
import argparse
import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verify.checks.v08_phase_consistency import _derive_phases, _direction_of  # noqa: E402

EXPR_SYMBOLS = ("!=", ">=", "<=", "==", "∈", "∉")
TIME_WORDS = ("超时", "时限", "过期", "截止", "自动转换")
CLAUSE_RE = re.compile(r"^\d+(\.\d+)*")
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


def lint_state_machines(spec, rep):
    machines = spec.get("state_machines") or {}
    if not machines:
        rep.err("SM", "state_machines missing")
        return
    for name, m in machines.items():
        states = m.get("states") or []
        if len(states) != len(set(states)):
            rep.err("SM", f"{name}: duplicate states {states}")
        state_set = set(states)
        transitions = m.get("transitions") or []
        if not transitions:
            rep.warn("SM", f"{name}: no transitions")
            continue

        # 引用状态合法性
        for t in transitions:
            f, to = t.get("from"), t.get("to")
            if isinstance(f, str) and f != "(初始)" and f not in state_set:
                rep.err("SM", f"{name}.{t.get('id')}: from '{f}' not in states")
            if isinstance(to, str) and not to.startswith("$") and to not in state_set:
                rep.err("SM", f"{name}.{t.get('id')}: to '{to}' not in states")
            if not t.get("clause"):
                rep.warn("SM", f"{name}.{t.get('id')}: missing clause")

        # direction 与相位一致性
        derived, anomaly_fw = _derive_phases(m)
        for t in transitions:
            d = _direction_of(t)
            if d in {"backward", "lateral", "self"}:
                note = t.get("note") or ""
                if not note:
                    rep.err("SM", f"{name}.{t.get('id')}: {d} transition missing note")
                elif not (CLAUSE_RE.search(note) or "SRS" in note):
                    rep.warn("SM", f"{name}.{t.get('id')}: note lacks clause reference")
                continue
            if t.get("id") in set(anomaly_fw):
                if t.get("note") or t.get("time_control_required"):
                    continue    # 已有 note 或标记为超时迁移 → 设计意图已说明，不报警
                rep.warn("SM", f"{name}.{t.get('id')}: forward edge not increasing under "
                   f"derived phases (cyclic machine); consider adding note")
                continue
            f, to = t.get("from"), t.get("to")
            if f in derived and to in derived and derived[to] <= derived[f]:
                rep.err("SM", f"{name}.{t.get('id')}: forward transition "
                              f"{f}({derived[f]}) -> {to}({derived[to]}) violates phase order")

        # 终态可达性 & 终态无 forward 出边
        initials = {t.get("to") for t in transitions if t.get("from") == "(初始)"}
        fwd_adj = {}
        for t in transitions:
            if _direction_of(t) in {"forward", "lateral"} and isinstance(t.get("from"), str):
                fwd_adj.setdefault(t["from"], []).append(t.get("to"))
        reachable = set(initials)
        frontier = list(initials)
        while frontier:
            cur = frontier.pop()
            for nxt in fwd_adj.get(cur, []):
                if nxt and nxt not in reachable:
                    reachable.add(nxt)
                    frontier.append(nxt)
        for st in m.get("terminal_states") or []:
            if st not in state_set:
                rep.err("SM", f"{name}: terminal state '{st}' not in states")
            elif st not in reachable:
                rep.err("SM", f"{name}: terminal state '{st}' unreachable via forward edges")
            if st in fwd_adj:
                rep.warn("SM", f"{name}: terminal state '{st}' has outgoing forward edges")

        # phase_mapping 声明
        pm = m.get("phase_mapping") or {}
        if not pm.get("auto_derived"):
            rep.err("SM", f"{name}: phase_mapping must declare auto_derived=true "
                          f"(hand-written phase numbers are forbidden)")


def lint_guard_policies(spec, rep):
    policies = spec.get("guard_policies") or []
    catalog_verbs = set()
    for v in (spec.get("action_catalog") or {}).values():
        if isinstance(v, list):
            catalog_verbs.update(x for x in v if isinstance(x, str))
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
        act = (pol.get("action") or "").strip()
        if act and catalog_verbs:
            if not any(act in v or v in act for v in catalog_verbs):
                rep.warn("GP", f"{gid}: action '{act}' not resolvable to action_catalog")
        if not pol.get("clause"):
            rep.warn("GP", f"{gid}: missing clause")


def lint_built_in(spec, rep):
    bi = spec.get("built_in_entities") or {}
    catalog = spec.get("action_catalog") or {}
    for ent in bi.get("readonly") or []:
        if ent in catalog:
            rep.warn("BI", f"readonly entity '{ent}' appears in action_catalog; "
                           f"its verbs must not produce type-3/9 obligations")
    known_entities = set((spec.get("state_machines") or {}).keys()) | set(catalog.keys())
    for f in bi.get("system_maintained_fields") or []:
        if "." not in f:
            rep.err("BI", f"system_maintained_field '{f}' must be '实体.字段' format")
            continue
        ent = f.split(".", 1)[0]
        if ent not in known_entities and ent not in (bi.get("readonly") or []):
            rep.warn("BI", f"system_maintained_field '{f}': entity '{ent}' unseen in spec")


def lint_actions_roles(spec, rep):
    machines = spec.get("state_machines") or {}
    rp = spec.get("role_permissions") or {}
    matrix = rp.get("matrix") or {}
    catalog = spec.get("action_catalog") or {}
    catalog_verbs = set()
    for v in catalog.values():
        if isinstance(v, list):
            catalog_verbs.update(x for x in v if isinstance(x, str))
    roles = set(matrix.keys())
    for name, m in machines.items():
        for t in m.get("transitions") or []:
            actor = (t.get("actor") or "").strip()
            if actor and actor != "系统" and actor not in roles:
                rep.err("AR", f"{name}.{t.get('id')}: actor '{actor}' not in role matrix")
    for role, acts in matrix.items():
        for a in acts or []:
            if catalog_verbs and not any(a in v or v in a for v in catalog_verbs):
                rep.warn("AR", f"matrix action '{a}' ({role}) not resolvable to action_catalog")


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
    if not tc.get("events_requiring"):
        rep.warn("TC", "time_control.events_requiring empty")
    for name, m in (spec.get("state_machines") or {}).items():
        for t in m.get("transitions") or []:
            if t.get("time_control_required"):
                trig = t.get("trigger") or ""
                if not any(w in trig for w in TIME_WORDS):
                    rep.warn("TC", f"{name}.{t.get('id')}: time_control_required=true but "
                                   f"trigger '{trig}' lacks time keyword")


def lint_coverage_matrix(spec, rep, spec_path):
    matrix = spec.get("coverage_matrix") or []
    if not matrix:
        rep.err("CM", "coverage_matrix missing or empty")
        return
    oracles_mod = None
    try:
        oracles_mod = importlib.import_module("verify.oracles")
    except Exception:
        rep.warn("CM", "verify.oracles not importable; oracle existence check skipped")
    seen_clauses = set()
    for entry in matrix:
        clause = entry.get("clause", "")
        topic = entry.get("topic", "?")
        if not CLAUSE_RE.match(str(clause)):
            rep.warn("CM", f"'{clause}' ({topic}): clause format unusual")
        if clause in seen_clauses:
            rep.warn("CM", f"duplicate clause entry: {clause}")
        seen_clauses.add(clause)
        if not (entry.get("must_include") or entry.get("branches")):
            rep.warn("CM", f"{clause} ({topic}): no probes (must_include/branches empty)")
        if entry.get("boundary") and not entry.get("boundary_probe_template"):
            rep.warn("CM", f"{clause} ({topic}): boundary without probe template "
                           f"(will be skipped by V10, needs Gate-E coverage)")
        oracle = entry.get("oracle") or ""
        if oracle and oracles_mod:
            for ref in str(oracle).split("|"):
                func = ref.split("#")[-1].strip()
                if func and not hasattr(oracles_mod, func):
                    rep.err("CM", f"{clause} ({topic}): oracle function '{func}' "
                                  f"not implemented in verify/oracles.py")


def lint_global_ids(spec, rep):
    tids, gids = set(), set()
    for m in (spec.get("state_machines") or {}).values():
        for t in m.get("transitions") or []:
            tid = t.get("id")
            if tid:
                if tid in tids:
                    rep.err("ID", f"transition id duplicated across machines: {tid}")
                tids.add(tid)
    for pol in spec.get("guard_policies") or []:
        gid = pol.get("guard_id")
        if gid:
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
    lint_state_machines(spec, rep)
    lint_guard_policies(spec, rep)
    lint_built_in(spec, rep)
    lint_actions_roles(spec, rep)
    lint_dimension_constraints(spec, rep)
    lint_time_control(spec, rep)
    lint_coverage_matrix(spec, rep, spec_path)
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
