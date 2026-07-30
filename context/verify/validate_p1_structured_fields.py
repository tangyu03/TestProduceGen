#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v29 Engineering Optimization — Gap 2: P1 Structured-Field Validator
(Updated to match current P1_output.json schema — 2026-07-30)

Problem (from critic's review of v29):
    v29's design says "P1 LLM emits structured fields → engine reads them →
    keyword fallback only fires for backward compat." But the critic asked:
        "P1 LLM 对新字段的产出可靠性如何？"
    ("How reliable is the P1 LLM's emission of new fields?")

    Without measuring this, you can't claim the relocation is "root-cause":
      - If P1 emits structured fields correctly 99% of the time → relocation works.
      - If P1 emits them 60% of the time → 40% of cases fall back to keywords,
        which is the same fragile behavior v29 was supposed to eliminate.

Schema migration (2026-07):
    The original v29 field names evolved during P1 LLM prompt iteration:
      is_approve (bool)           → traits (list, includes "audit")
      valid_combinations (list)   → branch_dimensions[].branches + .values
      causal_pairs (list)         → evidence_transitions + trigger_source
      operations[].is_special     → operations[].category
      (new)                       → direction, priority, rollback_propagation,
                                    confidence, has_critical_ambiguity

What this validator does:
    Reads a P1 domain model JSON (the OUTPUT of P1 LLM, INPUT to P2).
    For each structured field in the current schema:
      - Reports total expected count
      - Reports actual populated count
      - Reports coverage percentage
      - Reports sample missing IDs for debugging
    Emits a JSON report + human-readable summary.

Coverage targets:
    - traits:                ≥85% of transitions
    - direction:             ≥95% of transitions
    - priority:              ≥90% of transitions
    - preconditions[].type:  ≥90% of all preconditions
    - trigger_source:        ≥90% of transition_relations
    - evidence_transitions:  ≥85% of transition_relations
    - rollback_propagation:  ≥90% of transition_relations
    - confidence:            ≥80% of transition_relations
    - operations[].category: ≥95% of operations
    - branch_dim branches:   ≥90% of branch_dimensions
    - branch_dim values:     ≥90% of branch_dimensions
    - has_critical_ambiguity: 100% (project-level, must exist)
    - action_keywords:        0% (optional project-level customisation)

Usage:
    python context/validate_p1_structured_fields.py <p1.json> [--strict]
    python context/validate_p1_structured_fields.py <p1.json> --report <out.json>

Exit codes:
    0 — all fields meet minimum coverage
    1 — at least one field below minimum coverage (or --strict and not 100%)
    2 — file/structure error
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Field specifications — each describes ONE structured field
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FieldSpec:
    """Spec for one structured field in the current P1 schema."""
    name: str                       # short name, e.g. "traits"
    location: str                   # JSON path, e.g. "state_and_flow.transitions[].traits"
    description: str                # what this field is for
    fallback_site: str              # the FALLBACK_SITES entry that fires if absent
    min_coverage: float             # minimum acceptable coverage (0.0-1.0)
    strict_target: float = 1.0      # strict-mode target (usually 1.0)


SPECS: list[FieldSpec] = [
    # ── Transition-level fields ──────────────────────────────────────────
    FieldSpec(
        name="traits",
        location="state_and_flow.transitions[].traits",
        description="Transition traits: audit / branch / rollback / time_sensitive. "
                    "Replaces the old is_approve boolean — 'audit' means is_approve=true.",
        fallback_site="s1.is_approve.keyword_fallback",
        min_coverage=0.85,
    ),
    FieldSpec(
        name="direction",
        location="state_and_flow.transitions[].direction",
        description="Transition direction: forward / backward. "
                    "Replaces implicit direction inference from action text.",
        fallback_site="s0.classify_edge_type.action_keywords",
        min_coverage=0.95,
    ),
    FieldSpec(
        name="priority",
        location="state_and_flow.transitions[].priority",
        description="Transition priority: P0 (critical) / P1 (normal). "
                    "Replaces implicit priority from keyword matching.",
        fallback_site="s1.is_approve.derived_fallback",
        min_coverage=0.90,
    ),
    FieldSpec(
        name="preconditions[].type",
        location="state_and_flow.transitions[].preconditions[].type",
        description="Marks each precondition's type: state_ref | event_ref | constraint.",
        fallback_site="s1.precondition_type.keyword_split",
        min_coverage=0.90,
    ),

    # ── Transition-relation fields ───────────────────────────────────────
    FieldSpec(
        name="trigger_source",
        location="domain_model.transition_relations[].trigger_source",
        description="Declares what triggers the cross-entity relation: "
                    "expected_results | action_text | guard_condition. "
                    "Replaces the old causal_pairs list.",
        fallback_site="s0.causal_pairs.index_pairing_fallback",
        min_coverage=0.90,
    ),
    FieldSpec(
        name="evidence_transitions",
        location="domain_model.transition_relations[].evidence_transitions",
        description="List of transition IDs that evidence this cross-entity relation. "
                    "Replaces the old causal_pairs index-based pairing.",
        fallback_site="p2.causal_pairs.index_pairing_fallback",
        min_coverage=0.85,
    ),
    FieldSpec(
        name="rollback_propagation",
        location="domain_model.transition_relations[].rollback_propagation",
        description="Whether rollback propagates across this relation (boolean). "
                    "Replaces implicit rollback chain inference.",
        fallback_site="s0.causal_pairs.index_pairing_fallback",
        min_coverage=0.90,
    ),
    FieldSpec(
        name="confidence",
        location="domain_model.transition_relations[].confidence",
        description="LLM confidence in this relation: high | medium | low. "
                    "New v29 field — flags uncertain edges for manual review.",
        fallback_site="s0.causal_pairs.index_pairing_fallback",
        min_coverage=0.80,
    ),

    # ── Entity-operation fields ─────────────────────────────────────────
    FieldSpec(
        name="operations[].category",
        location="domain_model.entities[].operations[].category",
        description="Operation category: crud | query | session | ui | file | config. "
                    "Replaces the old is_special boolean — 'crud' ops are the data-mutating ones.",
        fallback_site="s1.type5_special_ops.generic_fallback",
        min_coverage=0.95,
    ),
    FieldSpec(
        name="operations[].expected_results",
        location="domain_model.entities[].operations[].expected_results",
        description="Each operation must declare its expected results (non-empty list). "
                    "Critical for test-case generation in P2.",
        fallback_site="s3.guard6.regex_fallback",
        min_coverage=0.90,
    ),
    FieldSpec(
        name="operations[].source_ref",
        location="domain_model.entities[].operations[].source_ref",
        description="Source-document reference for each operation. "
                    "Enables downstream traceability.",
        fallback_site="s1.type5_special_ops.generic_fallback",
        min_coverage=0.80,
    ),

    # ── Branch-dimension fields ─────────────────────────────────────────
    FieldSpec(
        name="branch_dimensions[].values",
        location="_meta.branch_dimensions[].values",
        description="Explicit list of legal dimension values "
                    "(replaces the old valid_combinations dict).",
        fallback_site="p2.valid_combinations.action_text_fallback",
        min_coverage=0.90,
    ),
    FieldSpec(
        name="branch_dimensions[].branches",
        location="_meta.branch_dimensions[].branches",
        description="Branch detail objects with value, target_transition, desc. "
                    "Replaces the old valid_combinations per-transition declarations.",
        fallback_site="p2.valid_combinations.action_text_fallback",
        min_coverage=0.90,
    ),

    # ── _meta project-level fields ──────────────────────────────────────
    FieldSpec(
        name="has_critical_ambiguity",
        location="_meta.has_critical_ambiguity",
        description="Boolean flag: does the source document have critical ambiguity? "
                    "P2 uses this to decide strict vs. lenient mode.",
        fallback_site="p2.action_keywords.default",
        min_coverage=1.00,  # must exist — engine changes behaviour without it
    ),
    FieldSpec(
        name="action_keywords",
        location="_meta.action_keywords",
        description="Optional project-specific rollback/resubmit action keywords. "
                    "If absent, engine falls back to generic Chinese defaults.",
        fallback_site="p2.action_keywords.default",
        min_coverage=0.00,  # optional — 0 means default Chinese keywords used
        strict_target=1.00,
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Coverage measurement
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FieldCoverage:
    spec: FieldSpec
    total_expected: int = 0
    actual_populated: int = 0
    coverage: float = 0.0
    missing_examples: list[str] = field(default_factory=list)
    passes_min: bool = False
    passes_strict: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.spec.name,
            "location": self.spec.location,
            "description": self.spec.description,
            "fallback_site": self.spec.fallback_site,
            "total_expected": self.total_expected,
            "actual_populated": self.actual_populated,
            "coverage": round(self.coverage, 4),
            "min_required": self.spec.min_coverage,
            "strict_target": self.spec.strict_target,
            "passes_min": self.passes_min,
            "passes_strict": self.passes_strict,
            "missing_examples": self.missing_examples[:10],
        }


# ── Transition-level measurers ──────────────────────────────────────────────

def _measure_traits(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "traits")
    cov = FieldCoverage(spec=spec)
    transitions = (p1.get("state_and_flow") or {}).get("transitions") or []
    cov.total_expected = len(transitions)
    missing = []
    for t in transitions:
        traits = t.get("traits")
        if not isinstance(traits, list) or len(traits) == 0:
            missing.append(t.get("id", "?"))
    cov.actual_populated = cov.total_expected - len(missing)
    cov.coverage = (cov.actual_populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_direction(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "direction")
    cov = FieldCoverage(spec=spec)
    transitions = (p1.get("state_and_flow") or {}).get("transitions") or []
    cov.total_expected = len(transitions)
    missing = []
    for t in transitions:
        d = t.get("direction")
        if not isinstance(d, str) or not d.strip():
            missing.append(t.get("id", "?"))
    cov.actual_populated = cov.total_expected - len(missing)
    cov.coverage = (cov.actual_populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_priority(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "priority")
    cov = FieldCoverage(spec=spec)
    transitions = (p1.get("state_and_flow") or {}).get("transitions") or []
    cov.total_expected = len(transitions)
    missing = []
    for t in transitions:
        p = t.get("priority")
        if not isinstance(p, str) or not p.strip():
            missing.append(t.get("id", "?"))
    cov.actual_populated = cov.total_expected - len(missing)
    cov.coverage = (cov.actual_populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_preconditions_type(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "preconditions[].type")
    cov = FieldCoverage(spec=spec)
    transitions = (p1.get("state_and_flow") or {}).get("transitions") or []
    total = 0
    populated = 0
    missing = []
    for t in transitions:
        tid = t.get("id", "?")
        preconds = t.get("preconditions") or []
        for prec in preconds:
            total += 1
            if isinstance(prec, dict) and prec.get("type"):
                populated += 1
            else:
                missing.append(f"{tid}")
    cov.total_expected = total
    cov.actual_populated = populated
    cov.coverage = (populated / total) if total else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


# ── Transition-relation measurers ───────────────────────────────────────────

def _measure_trigger_source(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "trigger_source")
    cov = FieldCoverage(spec=spec)
    trs = (p1.get("domain_model") or {}).get("transition_relations") or []
    cov.total_expected = len(trs)
    populated = 0
    missing = []
    for r in trs:
        ts = r.get("trigger_source")
        if isinstance(ts, str) and ts.strip():
            populated += 1
        else:
            missing.append(f"{r.get('from','?')}->{r.get('to','?')}")
    cov.actual_populated = populated
    cov.coverage = (populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_evidence_transitions(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "evidence_transitions")
    cov = FieldCoverage(spec=spec)
    trs = (p1.get("domain_model") or {}).get("transition_relations") or []
    cov.total_expected = len(trs)
    populated = 0
    missing = []
    for r in trs:
        et = r.get("evidence_transitions")
        if isinstance(et, list) and len(et) > 0:
            populated += 1
        else:
            missing.append(f"{r.get('from','?')}->{r.get('to','?')}")
    cov.actual_populated = populated
    cov.coverage = (populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_rollback_propagation(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "rollback_propagation")
    cov = FieldCoverage(spec=spec)
    trs = (p1.get("domain_model") or {}).get("transition_relations") or []
    cov.total_expected = len(trs)
    populated = 0
    missing = []
    for r in trs:
        if "rollback_propagation" in r:
            populated += 1
        else:
            missing.append(f"{r.get('from','?')}->{r.get('to','?')}")
    cov.actual_populated = populated
    cov.coverage = (populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_confidence(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "confidence")
    cov = FieldCoverage(spec=spec)
    trs = (p1.get("domain_model") or {}).get("transition_relations") or []
    cov.total_expected = len(trs)
    populated = 0
    missing = []
    valid_levels = {"high", "medium", "low"}
    for r in trs:
        c = r.get("confidence")
        if isinstance(c, str) and c.strip().lower() in valid_levels:
            populated += 1
        else:
            missing.append(f"{r.get('from','?')}->{r.get('to','?')}")
    cov.actual_populated = populated
    cov.coverage = (populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


# ── Entity-operation measurers ──────────────────────────────────────────────

def _measure_operations_category(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "operations[].category")
    cov = FieldCoverage(spec=spec)
    entities = (p1.get("domain_model") or {}).get("entities") or []
    total = 0
    populated = 0
    missing = []
    valid_cats = {"crud", "query", "session", "ui", "file", "config"}
    for e in entities:
        eid = e.get("id", "?")
        ops = e.get("operations") or []
        for op in ops:
            total += 1
            if isinstance(op, dict):
                cat = op.get("category")
                if isinstance(cat, str) and cat.strip().lower() in valid_cats:
                    populated += 1
                else:
                    op_name = op.get("name", "?")
                    missing.append(f"{eid}.{op_name}")
            else:
                missing.append(f"{eid}.{op if isinstance(op, str) else '?'}")
    cov.total_expected = total
    cov.actual_populated = populated
    cov.coverage = (populated / total) if total else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_operations_expected_results(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "operations[].expected_results")
    cov = FieldCoverage(spec=spec)
    entities = (p1.get("domain_model") or {}).get("entities") or []
    total = 0
    populated = 0
    missing = []
    for e in entities:
        eid = e.get("id", "?")
        ops = e.get("operations") or []
        for op in ops:
            total += 1
            if isinstance(op, dict):
                er = op.get("expected_results")
                if isinstance(er, list) and len(er) > 0:
                    populated += 1
                else:
                    op_name = op.get("name", "?")
                    missing.append(f"{eid}.{op_name}")
            else:
                missing.append(f"{eid}.{op if isinstance(op, str) else '?'}")
    cov.total_expected = total
    cov.actual_populated = populated
    cov.coverage = (populated / total) if total else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_operations_source_ref(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "operations[].source_ref")
    cov = FieldCoverage(spec=spec)
    entities = (p1.get("domain_model") or {}).get("entities") or []
    total = 0
    populated = 0
    missing = []
    for e in entities:
        eid = e.get("id", "?")
        ops = e.get("operations") or []
        for op in ops:
            total += 1
            if isinstance(op, dict) and isinstance(op.get("source_ref"), str) and op["source_ref"].strip():
                populated += 1
            else:
                op_name = op.get("name", "?") if isinstance(op, dict) else str(op)
                missing.append(f"{eid}.{op_name}")
    cov.total_expected = total
    cov.actual_populated = populated
    cov.coverage = (populated / total) if total else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


# ── Branch-dimension measurers ──────────────────────────────────────────────

def _measure_branch_dim_values(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "branch_dimensions[].values")
    cov = FieldCoverage(spec=spec)
    bds = (p1.get("_meta") or {}).get("branch_dimensions") or []
    cov.total_expected = len(bds)
    populated = 0
    missing = []
    for bd in bds:
        vals = bd.get("values")
        if isinstance(vals, list) and len(vals) > 0:
            populated += 1
        else:
            missing.append(bd.get("dimension", "?"))
    cov.actual_populated = populated
    cov.coverage = (populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_branch_dim_branches(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "branch_dimensions[].branches")
    cov = FieldCoverage(spec=spec)
    bds = (p1.get("_meta") or {}).get("branch_dimensions") or []
    cov.total_expected = len(bds)
    populated = 0
    missing = []
    for bd in bds:
        branches = bd.get("branches")
        if isinstance(branches, list) and len(branches) > 0:
            populated += 1
        else:
            missing.append(bd.get("dimension", "?"))
    cov.actual_populated = populated
    cov.coverage = (populated / cov.total_expected) if cov.total_expected else 1.0
    cov.missing_examples = missing
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


# ── _meta project-level measurers ───────────────────────────────────────────

def _measure_has_critical_ambiguity(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "has_critical_ambiguity")
    cov = FieldCoverage(spec=spec)
    meta = p1.get("_meta") or {}
    cov.total_expected = 1
    if "has_critical_ambiguity" in meta and isinstance(meta["has_critical_ambiguity"], bool):
        cov.actual_populated = 1
    else:
        cov.actual_populated = 0
        cov.missing_examples = ["_meta.has_critical_ambiguity (missing or not boolean)"]
    cov.coverage = float(cov.actual_populated)
    cov.passes_min = cov.coverage >= spec.min_coverage
    cov.passes_strict = cov.coverage >= spec.strict_target
    return cov


def _measure_action_keywords(p1: dict) -> FieldCoverage:
    spec = next(s for s in SPECS if s.name == "action_keywords")
    cov = FieldCoverage(spec=spec)
    ak = (p1.get("_meta") or {}).get("action_keywords")
    cov.total_expected = 1
    if isinstance(ak, dict) and (ak.get("rollback") or ak.get("resubmit")):
        cov.actual_populated = 1
    else:
        cov.actual_populated = 0
    cov.coverage = float(cov.actual_populated)
    cov.passes_min = cov.coverage >= spec.min_coverage  # min is 0.0 → always passes
    cov.passes_strict = cov.coverage >= spec.strict_target
    if cov.actual_populated == 0:
        cov.missing_examples = ["_meta.action_keywords (absent or empty — engine uses generic Chinese defaults)"]
    return cov


_MEASURERS = [
    # Transition-level
    _measure_traits,
    _measure_direction,
    _measure_priority,
    _measure_preconditions_type,
    # Relation-level
    _measure_trigger_source,
    _measure_evidence_transitions,
    _measure_rollback_propagation,
    _measure_confidence,
    # Operation-level
    _measure_operations_category,
    _measure_operations_expected_results,
    _measure_operations_source_ref,
    # Branch-dimension-level
    _measure_branch_dim_values,
    _measure_branch_dim_branches,
    # _meta project-level
    _measure_has_critical_ambiguity,
    _measure_action_keywords,
]


# ─────────────────────────────────────────────────────────────────────────────
# Top-level entry
# ─────────────────────────────────────────────────────────────────────────────

def validate_p1(p1: dict, strict: bool = False) -> dict:
    """Run all coverage measurements on a P1 JSON dict.

    Returns:
        {
            "summary": {total_specs, pass_min, pass_strict, overall_coverage},
            "fields": [FieldCoverage.to_dict(), ...],
            "strict_mode": bool,
            "overall_pass": bool,
        }
    """
    coverages = [m(p1) for m in _MEASURERS]
    field_dicts = [c.to_dict() for c in coverages]

    pass_min = sum(1 for c in coverages if c.passes_min)
    pass_strict = sum(1 for c in coverages if c.passes_strict)
    overall_cov = sum(c.coverage for c in coverages) / len(coverages) if coverages else 0.0

    overall_pass = all(c.passes_strict if strict else c.passes_min for c in coverages)

    return {
        "summary": {
            "total_specs": len(coverages),
            "pass_min": pass_min,
            "pass_strict": pass_strict,
            "overall_coverage": round(overall_cov, 4),
            "strict_mode": strict,
        },
        "fields": field_dicts,
        "strict_mode": strict,
        "overall_pass": overall_pass,
    }


def print_human_report(report: dict) -> None:
    """Print a human-readable coverage report to stdout."""
    s = report["summary"]
    print("=" * 80)
    print(f"P1 Structured-Field Coverage Report  (strict_mode={s['strict_mode']})")
    print("=" * 80)
    print(f"Overall coverage: {s['overall_coverage']*100:.2f}%  "
          f"(pass_min: {s['pass_min']}/{s['total_specs']}, "
          f"pass_strict: {s['pass_strict']}/{s['total_specs']})")
    print(f"Overall pass: {report['overall_pass']}")
    print()
    print(f"{'Field':<30} {'Location':<52} {'Cov':>7} {'Min':>6} {'Pass':>6}")
    print("-" * 104)
    for f in report["fields"]:
        cov_pct = f"{f['coverage']*100:.1f}%"
        min_pct = f"{f['min_required']*100:.0f}%"
        pass_str = "✓" if (f['passes_strict'] if s['strict_mode'] else f['passes_min']) else "✗"
        print(f"{f['name']:<30} {f['location']:<52} {cov_pct:>7} {min_pct:>6} {pass_str:>6}")
        if f['missing_examples']:
            ex = ", ".join(f['missing_examples'][:5])
            more = f" (+{len(f['missing_examples'])-5} more)" if len(f['missing_examples']) > 5 else ""
            print(f"  ↳ missing: {ex}{more}")
            print(f"  ↳ fallback site: {f['fallback_site']}")
    print()
    if report['overall_pass']:
        print("✓ PASS — P1 meets minimum structured-field coverage.")
    else:
        print("✗ FAIL — P1 is missing structured fields. Engine will fall back")
        print("         to keyword/heuristic logic at the listed fallback sites.")
        print("         See tools/fallback_log.py FALLBACK_SITES for engine-side impact.")


def main() -> int:
    ap = argparse.ArgumentParser(description="v29 P1 structured-field validator (Gap 2)")
    ap.add_argument("p1_json", help="Path to P1 domain model JSON")
    ap.add_argument("--strict", action="store_true",
                    help="Require 100%% coverage on all fields (default: per-field min)")
    ap.add_argument("--report", help="Optional path to write JSON report")
    ap.add_argument("--quiet", action="store_true", help="Suppress human report")
    args = ap.parse_args()

    if not os.path.exists(args.p1_json):
        print(f"ERROR: file not found: {args.p1_json}", file=sys.stderr)
        return 2
    try:
        with open(args.p1_json, "r", encoding="utf-8") as f:
            p1 = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        return 2

    report = validate_p1(p1, strict=args.strict)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Report written to: {args.report}", file=sys.stderr)

    if not args.quiet:
        print_human_report(report)

    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
