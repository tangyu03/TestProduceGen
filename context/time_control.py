#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which obligations require a ``time_control`` declaration.

Single source of truth for the "does this obligation need time_control" rule —
shared by the S1 generator (nodes/s1_generation.py) and the V06 gate
(verify/checks/v06_time_control.py) so they cannot drift. Same architectural
rule co_derivation.py and entity_operators.py establish: one shared derivation,
consumed by both the producer and the gate.

Rule (from the coverage model, not case_spec keywords):
  - transition_obligations whose risk_traits contain "time_sensitive"
  - constraint_obligations that are timing BRs
    (type == business_rule and (category == timing or desc mentions 超时/时限))

Any procedure that references one of these ids (source_ids) must declare
``time_control.mechanism`` in the allowed set (or ``status == "planned"``).
The S1 generator fills time_control from the action's time semantics via
``_derive_time_mechanism``; a dedup merge that unions source_ids must preserve
that declaration even when the surviving sibling itself wasn't time-sensitive.
"""
__all__ = ["needs_time_control_ids"]


def needs_time_control_ids(model: dict) -> set:
    """Return the ids of obligations that require a time_control declaration."""
    needs: set = set()
    for to in model.get("transition_obligations", []) or []:
        if "time_sensitive" in (to.get("risk_traits") or []):
            if to.get("id"):
                needs.add(to["id"])
    for br in model.get("constraint_obligations", []) or []:
        desc = br.get("description") or ""
        if (br.get("type") == "business_rule"
                and (br.get("category") == "timing"
                     or "超时" in desc or "时限" in desc)):
            if br.get("id"):
                needs.add(br["id"])
    return needs
