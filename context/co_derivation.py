#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CO dependent-transition derivation rule — shared by P2 (generator) and
validate_p2.py (gate). Single source of truth for mapping an XC's
target_condition / target_from / target_to onto a dependent transition id.

Historical defect this prevents: P2 used a direction-blind reverse lookup —
the first TO whose (entity, dimension, to) matched the condition. When several
transitions reach the same state it silently picked the WRONG one, e.g.
E-PROJ→已选入 has four inbound transitions (T-002 待选入, T-007 待归档,
T-011 评审中, T-012 待评审); the cancel-rollback XC-012 must pick T-012 but
got T-002.

Root-cause reframe: the information isn't lost — P1 already carries from→to
(either in target_condition free text "X到Y", or in the mirror/联动 sibling
XC of the same rule). P2 was throwing it away. Resolution order:
  1. structured fields  target_from / target_to   (P1 v20+)
  2. parse target_condition free text             (到 / → / 变为 / 变更为 / 状态=)
  3. lossy (only `to` known) → inherit `from` from a sibling XC sharing
     (source_transition, target_entity, target_to) that carries full from→to
     (mirror XCs are the complete form of the same rule)
  4. match (entity, dimension, from, to) against P1 original transitions —
     abstract-aware: split transitions match on their base id, downstream
     (S0) resolves variants via transition_splits.

Escalation rule: NEVER first-pick. If the candidate set is not exactly one,
resolve_dependent_transition returns None and the caller records a judgment
and lets the XC fall through to RO-BR (fails closed, never silently wrong).
"""

import re

_SEP_RE = re.compile(r"^(.+?)(?:到|→|变为|变更为)(.+)$")
_STATE_EQ_RE = re.compile(r"^状态\s*=\s*(.+)$")


def parse_target_condition(target_cond):
    """Split target_condition into (from_state, to_state).

    Returns (from_state | None, to_state | None). from_state is None when the
    condition carries only the target state (lossy free text, e.g. "已选入" or
    "状态=未打分"). to_state is None only for empty input.
    """
    if not target_cond:
        return None, None
    target_cond = str(target_cond).strip()
    m = _STATE_EQ_RE.match(target_cond)
    if m:
        return None, m.group(1).strip()
    m = _SEP_RE.match(target_cond)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, target_cond


def is_aggregate_target(to_state):
    """True for non-single-state targets that must never enter single-state
    reverse lookup (aggregate / computed / none targets)."""
    if to_state is None or str(to_state).strip() in ("", "None"):
        return True
    s = str(to_state)
    if re.match(r"^按.+变更", s):          # 按阶段和评级变更 / 按累计评价结果变更 / 按评级变更
        return True
    if "不变" in s and ("（" in s or "(" in s):  # 不变（开题）
        return True
    return False


def find_transitions_by_from_to(p1_transitions_by_id, entity_id, dimension,
                                from_state, to_state):
    """Match P1 original transitions by (entity, dimension, from, to).

    Returns a list of abstract transition ids. from_state=None matches any
    `from` — used for the from-less unambiguous case (single inbound
    transition to the state). Split transitions match on their base id
    (variants share from/to).
    """
    out = []
    for tid, t in p1_transitions_by_id.items():
        if t.get("entity") != entity_id:
            continue
        if dimension and t.get("dimension") != dimension:
            continue
        if t.get("to") != to_state:
            continue
        if from_state is not None and t.get("from") != from_state:
            continue
        out.append(tid)
    return out


def _inherit_from_mirror(p1_xc, xc, to_state):
    """Inherit the missing `from` from a sibling XC carrying full from→to and
    sharing (source_transition, target_entity, target_to).

    The mirror XC (desc "镜像 T-xxx") is the complete form of the same rule as
    the 联动 XC — they are mirror/联动 pairs in the source and always share
    target_to. Returns the unique inherited from-state, or None when 0/≥2
    distinct froms (ambiguous → caller escalates).
    """
    uniq_froms = set()
    for other in p1_xc:
        if other.get("id") == xc.get("id"):
            continue
        if other.get("source_transition") != xc.get("source_transition"):
            continue
        if other.get("target_entity") != xc.get("target_entity"):
            continue
        ofrom = other.get("target_from")
        oto = other.get("target_to")
        if ofrom is None or oto is None:
            ofrom, oto = parse_target_condition(other.get("target_condition", ""))
        if oto != to_state or ofrom is None:
            continue
        uniq_froms.add(ofrom)
    if len(uniq_froms) == 1:
        return next(iter(uniq_froms))
    return None


def extract_target_states(xc, p1_xc, p1_transitions_by_id):
    """Resolve an XC's dependent-transition endpoints (target_from, target_to).

    Order: structured fields → parse → mirror-inherit → single-candidate from
    backfill. from_state may remain None (e.g. the sole inbound transition is a
    creation with from=None); the caller (resolve_dependent_transition) treats
    None as "no from filter" and relies on the candidate-set uniqueness.
    Returns (None, None) for aggregate targets and for to-states no transition
    reaches (non-state conditions like "不可纳入评审计划").
    """
    from_state = xc.get("target_from")
    to_state = xc.get("target_to")
    # Fill missing endpoint(s) from the free text. When either field is absent,
    # parse the FULL condition — a parsed from is meaningful (e.g. mirror XC-004
    # "待评审到已选入" and XC-009 "待评审到评审中" where E-PLAN 评审中 has TWO
    # inbound transitions; discarding the parsed from would turn them ambiguous).
    if from_state is None or to_state is None:
        p_from, p_to = parse_target_condition(xc.get("target_condition", ""))
        if from_state is None:
            from_state = p_from
        if to_state is None:
            to_state = p_to
    if is_aggregate_target(to_state):
        return None, None
    # target must be a reachable single state of the target entity/dimension —
    # otherwise it is a non-state condition, not a transition endpoint.
    reachable = [t for t in p1_transitions_by_id.values()
                 if t.get("entity") == xc.get("target_entity")
                 and t.get("dimension") == xc.get("target_dimension")
                 and t.get("to") == to_state]
    if not reachable:
        return None, None
    if from_state is None:
        from_state = _inherit_from_mirror(p1_xc, xc, to_state)
    if from_state is None and len(reachable) == 1:
        from_state = reachable[0].get("from")
    return from_state, to_state


def resolve_dependent_transition(p1_xc, p1_transitions_by_id, xc):
    """Resolve the dependent transition id for an XC (auto/constraint lanes).

    Returns (dependent_tid | None, info). info carries {from_state, to_state,
    via, candidates} for auditability. Never first-picks: returns None when
    the candidate set is not exactly one.
    """
    from_state, to_state = extract_target_states(xc, p1_xc, p1_transitions_by_id)
    if to_state is None:
        return None, {"from_state": from_state, "to_state": to_state,
                      "via": "none", "candidates": []}
    candidates = find_transitions_by_from_to(
        p1_transitions_by_id, xc.get("target_entity"), xc.get("target_dimension"),
        from_state, to_state)
    if len(candidates) == 1:
        return candidates[0], {"from_state": from_state, "to_state": to_state,
                               "via": "resolved", "candidates": candidates}
    return None, {"from_state": from_state, "to_state": to_state,
                  "via": "ambiguous" if candidates else "missing",
                  "candidates": candidates}
