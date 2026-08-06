#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entity → operator-role derivation — shared by the Type9 field-validation
generator (nodes/s1_generation.py) and the V07 role-consistency gate
(verify/checks/v07_role_permission.py).

Single source of truth for "which roles operate entity X's create/edit form".
Both consumers MUST go through here so they cannot drift — the same
architectural rule co_derivation.py establishes for dependent transitions
("shared by P2 (generator) and validate_p2.py (gate)").

Historical defect this prevents:
  Type9 procs are generated with a generic scaffold action
  "提交含违规值的表单" that is not a domain operation, so V07's old
  action-substring permission check flagged every Type9 proc. The generator
  "fixed" its own side with a blanket 系统管理员 fallback for managed
  entities — producing the wrong actor for 专家(→评审管理员)、分数限值(→评审管理员)、
  附件(→机构管理员)。Generator and validator each held half the truth and
  drifted.

Why entity-level, not action-level:
  A Type9 case asserts "actor submits an invalid <entity> form and field
  validation rejects it". The form is the entity's create/edit operation, so
  the invariant is ENTITY-level: actor ∈ operators(entity). The action string
  is scaffold, not a model claim, so action-substring matching is meaningless
  for Type9.

Derivation (model structured fields only — no SRS prose keyword matching):
  1. _context.permissions: role's operation containing the entity name AND a
     form-mutating verb (新增/编辑/删除/添加/上传/设置/提交/保存) → operator.
  2. transition_obligations: every (entity, role) claim → operator
     (authoritative for core state-machine entities — E-PROJ/E-PLAN/E-SCORE/
     E-USER/E-ORG carry TOs; managed entities do not).
  3. structural_relations: composition + business_ownership parent
     inheritance (E-ATT → E-PROJ: attachments are attributes of the project
     form, so their operators are the project form's operators).

form_operator_roles() = ordered picks for the generator (create-permission
role first — the role that owns the form; e.g. 机构管理员 for 项目 via 新增项目,
not 评审管理员 via 回避项目设置). entity_operator_set() = full membership
sets for the V07 gate. Both derive from the same three model sections, so the
gate verifies exactly what the generator was told to produce.
"""

_FORM_VERBS = ("新增", "编辑", "删除", "添加", "上传", "设置", "提交", "保存")
_CREATE_VERBS = ("新增", "添加")
_SYSTEM_ROLES = {"系统", "system", "System"}


def _names_by_id(model):
    return {ed.get("id"): ed.get("name") for ed in
            (model.get("_context") or {}).get("entity_details", []) if ed.get("id")}


def _entity_name(model, key):
    """Resolve an entity key (ID like 'E-PROJ' or Chinese name like '项目') to
    the canonical Chinese name. The generator passes IDs (constraint_steps is
    keyed by E-XXX); the V07 gate reads post-translation output where main.py
    has replaced every E-XXX with its Chinese name. Both keys must resolve."""
    names = _names_by_id(model)
    if key in names:
        return names[key]
    return key


def _ownership_parent(model, entity_id):
    """composition + business_ownership parent (from) of entity_id, or None."""
    for rel in (model.get("_context") or {}).get("structural_relations") or []:
        if (rel.get("relation_type") == "composition"
                and rel.get("ownership_dimension") == "business_ownership"
                and rel.get("to") == entity_id):
            return rel.get("from")
    return None


def form_operator_roles(model, entity_id) -> list:
    """Ordered roles authorized to operate entity_id's create/edit form.

    Priority: (1) create-permission roles (op = 新增/添加 + entity name),
    (2) other form-op roles (permissions list order — deterministic),
    (3) TO roles for the entity (non-system, stable), (4) composition
    business_ownership parent, recursively. Empty list → the caller's 系统管理员
    fallback is a genuine last resort (not the managed-entity default).
    """
    name = _entity_name(model, entity_id)
    create_roles: list = []
    form_roles: list = []
    if name:
        for perm in (model.get("_context") or {}).get("permissions", []) or []:
            role = perm.get("role")
            if not role or role in _SYSTEM_ROLES:
                continue
            for op in perm.get("operations", []) or []:
                if not op or name not in op or not any(v in op for v in _FORM_VERBS):
                    continue
                if any(c in op for c in _CREATE_VERBS):
                    if role not in create_roles:
                        create_roles.append(role)
                elif role not in form_roles:
                    form_roles.append(role)
                break
    if create_roles:
        return create_roles
    if form_roles:
        return form_roles
    to_roles: list = []
    for to in model.get("transition_obligations", []) or []:
        if to.get("entity") == entity_id:
            r = to.get("role")
            if r and r not in _SYSTEM_ROLES and r not in to_roles:
                to_roles.append(r)
    if to_roles:
        return to_roles
    parent = _ownership_parent(model, entity_id)
    if parent:
        return form_operator_roles(model, parent)
    return []


def entity_operator_set(model) -> dict:
    """entity_id → set of roles authorized to operate the entity's form.

    Precisely: an entity's form operators are its OWN create/edit roles
    (L1 permission ops); TO roles (L2) are a fallback ONLY for entities with
    no L1 form ops (core entities like E-SCORE whose form lives in TOs);
    parent inheritance happens ONLY for entities with neither L1 nor L2
    (dependent entities like E-ATT). This is deliberately NOT a blind union —
    E-ORG→E-PROJ is composition business_ownership (机构拥有项目), but the
    机构's operator 系统管理员 must not bleed into 项目's form operators; E-ATT
    inherits only E-PROJ's OWN form operators (机构管理员/评审管理员), so a wrong
    actor like 附件/系统管理员 fails the gate. The generator's
    form_operator_roles() follows the same order (create → form → TO → parent),
    so every actor it produces is guaranteed to be in this set."""
    names = _names_by_id(model)
    sets = {eid: set() for eid in names}
    # L1: form-op roles per entity
    for eid, name in names.items():
        if not name:
            continue
        for perm in (model.get("_context") or {}).get("permissions", []) or []:
            role = perm.get("role")
            if not role:
                continue
            for op in perm.get("operations", []) or []:
                if op and name in op and any(v in op for v in _FORM_VERBS):
                    sets[eid].add(role)
    # L2: TO roles — only where L1 is empty
    to_roles: dict = {}
    for to in model.get("transition_obligations", []) or []:
        eid = to.get("entity")
        if eid and to.get("role"):
            to_roles.setdefault(eid, []).append(to.get("role"))
    for eid in sets:
        if not sets[eid]:
            sets[eid].update(to_roles.get(eid, ()))
    # L3: parent inheritance — only where L1 and L2 are both empty
    parent = {eid: _ownership_parent(model, eid) for eid in names}

    def inherit(eid, stack):
        if eid in stack or sets[eid]:
            return  # has its own form operators — don't broaden with ancestors
        par = parent.get(eid)
        if par:
            inherit(par, stack | {eid})
            sets[eid] |= sets.get(par, set())

    for eid in list(sets):
        inherit(eid, frozenset())
    # Alias each set under its Chinese name too — the V07 gate reads
    # post-translation output where main.py replaced E-XXX with 项目.
    for eid, name in names.items():
        sets[name] = sets[eid]
    return sets
