from __future__ import annotations

import pytest

from solocoder_py.abac import (
    ABACEngine,
    ABACError,
    AttributeCategory,
    AttributeCondition,
    ComparisonOperator,
    ConditionExpression,
    ConflictResolutionStrategy,
    Decision,
    InvalidConditionError,
    InvalidPolicyError,
    LogicalOperator,
    Policy,
    PolicyEffect,
    PolicyNotFoundError,
    RequestContext,
    UnknownAttributeError,
)


# =============================
# Model Validation Tests
# =============================


class TestAttributeConditionValidation:
    def test_empty_attribute_path_rejected(self):
        with pytest.raises(InvalidConditionError, match="attribute_path must not be empty"):
            AttributeCondition(attribute_path="", operator=ComparisonOperator.EQ, expected_value="x")

    def test_invalid_operator_rejected(self):
        with pytest.raises(InvalidConditionError, match="Invalid operator"):
            AttributeCondition(attribute_path="subject.role", operator="BAD", expected_value="admin")

    def test_valid_condition_created(self):
        cond = AttributeCondition(
            attribute_path="subject.role",
            operator=ComparisonOperator.EQ,
            expected_value="admin",
        )
        assert cond.attribute_path == "subject.role"
        assert cond.operator == ComparisonOperator.EQ
        assert cond.expected_value == "admin"


class TestConditionExpressionValidation:
    def test_invalid_logical_operator_rejected(self):
        with pytest.raises(InvalidConditionError, match="Invalid logical operator"):
            ConditionExpression(logical_operator="BAD", operands=[])

    def test_not_operator_requires_exactly_one_operand(self):
        with pytest.raises(InvalidConditionError, match="NOT operator requires exactly one operand"):
            ConditionExpression(logical_operator=LogicalOperator.NOT, operands=[])
        with pytest.raises(InvalidConditionError, match="NOT operator requires exactly one operand"):
            ConditionExpression(
                logical_operator=LogicalOperator.NOT,
                operands=[
                    AttributeCondition("subject.role", ComparisonOperator.EQ, "a"),
                    AttributeCondition("subject.role", ComparisonOperator.EQ, "b"),
                ],
            )

    def test_and_or_requires_at_least_one_operand(self):
        with pytest.raises(InvalidConditionError, match="AND operator requires at least one operand"):
            ConditionExpression(logical_operator=LogicalOperator.AND, operands=[])
        with pytest.raises(InvalidConditionError, match="OR operator requires at least one operand"):
            ConditionExpression(logical_operator=LogicalOperator.OR, operands=[])

    def test_invalid_operand_type_rejected(self):
        with pytest.raises(InvalidConditionError, match="Invalid operand type"):
            ConditionExpression(logical_operator=LogicalOperator.AND, operands=["not a condition"])

    def test_valid_expression_created(self):
        expr = ConditionExpression(
            logical_operator=LogicalOperator.AND,
            operands=[
                AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                AttributeCondition("resource.type", ComparisonOperator.EQ, "document"),
            ],
        )
        assert expr.logical_operator == LogicalOperator.AND
        assert len(expr.operands) == 2


class TestPolicyValidation:
    def test_empty_policy_id_rejected(self):
        with pytest.raises(InvalidPolicyError, match="policy_id must not be empty"):
            Policy(policy_id="", name="test", effect=PolicyEffect.PERMIT)

    def test_empty_name_rejected(self):
        with pytest.raises(InvalidPolicyError, match="name must not be empty"):
            Policy(policy_id="p1", name="", effect=PolicyEffect.PERMIT)

    def test_invalid_effect_rejected(self):
        with pytest.raises(InvalidPolicyError, match="Invalid effect"):
            Policy(policy_id="p1", name="test", effect="BAD")

    def test_deny_policy_not_marked_explicit_deny_by_default(self):
        p = Policy(policy_id="p1", name="deny all", effect=PolicyEffect.DENY)
        assert p.is_explicit_deny is False

    def test_deny_policy_can_be_marked_explicit(self):
        p = Policy(
            policy_id="p1",
            name="explicit deny all",
            effect=PolicyEffect.DENY,
            is_explicit_deny=True,
        )
        assert p.is_explicit_deny is True

    def test_permit_policy_not_marked_explicit_deny(self):
        p = Policy(policy_id="p1", name="permit all", effect=PolicyEffect.PERMIT)
        assert p.is_explicit_deny is False

    def test_permit_policy_cannot_be_marked_explicit_deny(self):
        with pytest.raises(
            InvalidPolicyError,
            match="is_explicit_deny=True can only be used with effect=PolicyEffect.DENY",
        ):
            Policy(
                policy_id="p1",
                name="permit",
                effect=PolicyEffect.PERMIT,
                is_explicit_deny=True,
            )

    def test_deny_policy_can_be_marked_explicit_deny(self):
        p = Policy(
            policy_id="p1",
            name="explicit deny",
            effect=PolicyEffect.DENY,
            is_explicit_deny=True,
        )
        assert p.effect == PolicyEffect.DENY
        assert p.is_explicit_deny is True

    def test_deny_policy_default_not_explicit(self):
        p = Policy(
            policy_id="p1",
            name="normal deny",
            effect=PolicyEffect.DENY,
        )
        assert p.effect == PolicyEffect.DENY
        assert p.is_explicit_deny is False

    def test_is_explicit_deny_must_be_bool(self):
        with pytest.raises(InvalidPolicyError, match="is_explicit_deny must be a boolean"):
            Policy(
                policy_id="p1",
                name="x",
                effect=PolicyEffect.DENY,
                is_explicit_deny="yes",
            )

    def test_valid_policy_created(self):
        p = Policy(
            policy_id="p1",
            name="Admin Access",
            effect=PolicyEffect.PERMIT,
            priority=10,
            description="Allow admins full access",
        )
        assert p.policy_id == "p1"
        assert p.name == "Admin Access"
        assert p.effect == PolicyEffect.PERMIT
        assert p.priority == 10
        assert p.description == "Allow admins full access"


class TestRequestContext:
    def test_get_attribute_nested_path(self):
        ctx = RequestContext(
            subject={"profile": {"role": "admin"}},
            resource={},
            environment={},
        )
        assert ctx.get_attribute(AttributeCategory.SUBJECT, "profile.role") == "admin"

    def test_get_missing_attribute_raises(self):
        ctx = RequestContext()
        with pytest.raises(UnknownAttributeError, match="subject.role"):
            ctx.get_attribute(AttributeCategory.SUBJECT, "role")

    def test_get_missing_nested_attribute_raises(self):
        ctx = RequestContext(subject={"profile": {}})
        with pytest.raises(UnknownAttributeError, match="subject.profile.role"):
            ctx.get_attribute(AttributeCategory.SUBJECT, "profile.role")

    def test_empty_context(self):
        ctx = RequestContext()
        assert ctx.subject == {}
        assert ctx.resource == {}
        assert ctx.environment == {}


# =============================
# Policy CRUD Tests
# =============================


class TestPolicyCRUD:
    def test_add_and_get_policy(self, engine):
        p = Policy(policy_id="p1", name="Test", effect=PolicyEffect.PERMIT)
        engine.add_policy(p)
        assert engine.get_policy("p1") is p
        assert engine.list_policies() == [p]

    def test_add_overwrites_existing(self, engine):
        p1 = Policy(policy_id="p1", name="A", effect=PolicyEffect.PERMIT)
        p2 = Policy(policy_id="p1", name="B", effect=PolicyEffect.DENY)
        engine.add_policy(p1)
        engine.add_policy(p2)
        assert engine.get_policy("p1").name == "B"
        assert len(engine.list_policies()) == 1

    def test_update_existing_policy(self, engine):
        p1 = Policy(policy_id="p1", name="A", effect=PolicyEffect.PERMIT, priority=0)
        p2 = Policy(policy_id="p1", name="A Updated", effect=PolicyEffect.DENY, priority=100)
        engine.add_policy(p1)
        engine.update_policy(p2)
        assert engine.get_policy("p1").name == "A Updated"
        assert engine.get_policy("p1").priority == 100

    def test_update_nonexistent_raises(self, engine):
        p = Policy(policy_id="missing", name="X", effect=PolicyEffect.PERMIT)
        with pytest.raises(PolicyNotFoundError, match="Policy 'missing' not found"):
            engine.update_policy(p)

    def test_delete_policy(self, engine):
        p = Policy(policy_id="p1", name="Test", effect=PolicyEffect.PERMIT)
        engine.add_policy(p)
        engine.delete_policy("p1")
        assert engine.get_policy("p1") is None
        assert engine.list_policies() == []

    def test_delete_nonexistent_raises(self, engine):
        with pytest.raises(PolicyNotFoundError, match="Policy 'missing' not found"):
            engine.delete_policy("missing")


# =============================
# Comparison Operator Tests
# =============================


class TestComparisonOperators:
    def test_eq(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Role is admin",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        assert result.decision == Decision.PERMIT

    def test_neq(self, engine, user_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Role is not guest",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.NEQ, "guest"
                ),
            )
        )
        result = engine.evaluate(user_context)
        assert result.decision == Decision.PERMIT

    def test_gt_and_lt(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Age between 18 and 65",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition("subject.age", ComparisonOperator.GT, 18),
                        AttributeCondition("subject.age", ComparisonOperator.LT, 65),
                    ],
                ),
            )
        )
        ctx_ok = RequestContext(subject={"age": 30})
        assert engine.evaluate(ctx_ok).decision == Decision.PERMIT
        ctx_young = RequestContext(subject={"age": 10})
        assert engine.evaluate(ctx_young).decision == Decision.NOT_APPLICABLE
        ctx_old = RequestContext(subject={"age": 70})
        assert engine.evaluate(ctx_old).decision == Decision.NOT_APPLICABLE

    def test_gte_and_lte(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Age gte 18 lte 65",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition("subject.age", ComparisonOperator.GTE, 18),
                        AttributeCondition("subject.age", ComparisonOperator.LTE, 65),
                    ],
                ),
            )
        )
        assert engine.evaluate(RequestContext(subject={"age": 18})).decision == Decision.PERMIT
        assert engine.evaluate(RequestContext(subject={"age": 65})).decision == Decision.PERMIT
        assert engine.evaluate(RequestContext(subject={"age": 17})).decision == Decision.NOT_APPLICABLE

    def test_contains_in_string(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Email contains example.com",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.email", ComparisonOperator.CONTAINS, "@example.com"
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"email": "user@example.com"})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"email": "user@test.com"})
        ).decision == Decision.NOT_APPLICABLE

    def test_contains_in_list(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Has vip tag",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.tags", ComparisonOperator.CONTAINS, "vip"
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"tags": ["vip", "new"]})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"tags": ["new"]})
        ).decision == Decision.NOT_APPLICABLE

    def test_contains_in_dict_values(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Has admin role in dict",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.roles", ComparisonOperator.CONTAINS, "admin"
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"roles": {"r1": "admin", "r2": "user"}})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"roles": {"r1": "user"}})
        ).decision == Decision.NOT_APPLICABLE

    def test_in_operator(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Role in allowed list",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.IN, ["admin", "manager"]
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"role": "admin"})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"role": "manager"})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"role": "user"})
        ).decision == Decision.NOT_APPLICABLE

    def test_regex_match(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Valid phone number",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.phone", ComparisonOperator.REGEX, r"^1[3-9]\d{9}$"
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"phone": "13812345678"})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"phone": "12345"})
        ).decision == Decision.NOT_APPLICABLE

    def test_starts_with(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Name starts with Admin",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.name", ComparisonOperator.STARTS_WITH, "Admin"
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"name": "Administrator"})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(subject={"name": "User"})
        ).decision == Decision.NOT_APPLICABLE

    def test_ends_with(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="File ends with .pdf",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "resource.filename", ComparisonOperator.ENDS_WITH, ".pdf"
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(resource={"filename": "report.pdf"})
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(resource={"filename": "report.docx"})
        ).decision == Decision.NOT_APPLICABLE


# =============================
# Logical Combination Tests
# =============================


class TestLogicalCombinations:
    def test_and_all_true(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Admin and IT dept",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                        AttributeCondition("subject.department", ComparisonOperator.EQ, "IT"),
                    ],
                ),
            )
        )
        assert engine.evaluate(admin_context).decision == Decision.PERMIT

    def test_and_one_false(self, engine, user_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Admin and IT dept",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                        AttributeCondition("subject.department", ComparisonOperator.EQ, "IT"),
                    ],
                ),
            )
        )
        assert engine.evaluate(user_context).decision == Decision.NOT_APPLICABLE

    def test_or_one_true(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Admin or manager",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.OR,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "manager"),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"role": "manager"})
        ).decision == Decision.PERMIT

    def test_or_all_false(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Admin or manager",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.OR,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "manager"),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"role": "guest"})
        ).decision == Decision.NOT_APPLICABLE

    def test_not_true(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Not guest",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.NOT,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "guest"),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"role": "user"})
        ).decision == Decision.PERMIT

    def test_not_false(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Not guest",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.NOT,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "guest"),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"role": "guest"})
        ).decision == Decision.NOT_APPLICABLE

    def test_complex_nested_conditions(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Complex nested: (admin OR owner) AND NOT outside_hours",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        ConditionExpression(
                            LogicalOperator.OR,
                            operands=[
                                AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                                AttributeCondition("resource.owner", ComparisonOperator.EQ, "u2"),
                            ],
                        ),
                        ConditionExpression(
                            LogicalOperator.NOT,
                            operands=[
                                AttributeCondition("environment.time", ComparisonOperator.EQ, "22:00"),
                            ],
                        ),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(
                subject={"role": "admin", "user_id": "u1"},
                resource={"owner": "u2"},
                environment={"time": "09:00"},
            )
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(
                subject={"role": "user", "user_id": "u2"},
                resource={"owner": "u2"},
                environment={"time": "09:00"},
            )
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(
                subject={"role": "admin", "user_id": "u1"},
                resource={"owner": "u2"},
                environment={"time": "22:00"},
            )
        ).decision == Decision.NOT_APPLICABLE

    def test_triple_nested_not_not_not(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Triple negation (NOT NOT NOT X == NOT X)",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.NOT,
                    operands=[
                        ConditionExpression(
                            LogicalOperator.NOT,
                            operands=[
                                ConditionExpression(
                                    LogicalOperator.NOT,
                                    operands=[
                                        AttributeCondition(
                                            "subject.role",
                                            ComparisonOperator.EQ,
                                            "guest",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(subject={"role": "guest"})
        ).decision == Decision.NOT_APPLICABLE
        assert engine.evaluate(
            RequestContext(subject={"role": "admin"})
        ).decision == Decision.PERMIT

    def test_and_with_many_operands(self, engine):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="All conditions must match",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                        AttributeCondition("subject.department", ComparisonOperator.EQ, "IT"),
                        AttributeCondition("subject.age", ComparisonOperator.GT, 21),
                        AttributeCondition("resource.type", ComparisonOperator.EQ, "document"),
                    ],
                ),
            )
        )
        assert engine.evaluate(
            RequestContext(
                subject={"role": "admin", "department": "IT", "age": 30},
                resource={"type": "document"},
            )
        ).decision == Decision.PERMIT
        assert engine.evaluate(
            RequestContext(
                subject={"role": "admin", "department": "IT", "age": 18},
                resource={"type": "document"},
            )
        ).decision == Decision.NOT_APPLICABLE


# =============================
# Explicit Deny Priority Tests
# =============================


class TestExplicitDenyOverride:
    def test_explicit_deny_overrides_permit(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="permit1",
                name="Permit admins",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="deny1",
                name="Deny high sensitivity",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "resource.sensitivity", ComparisonOperator.EQ, "high"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "EXPLICIT_DENY_OVERRIDE"
        assert "Explicit deny override" in result.reason
        assert len(result.matched_policies) == 2

    def test_multiple_explicit_denies_pick_highest_priority(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="permit1",
                name="Permit all",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=None,
            )
        )
        engine.add_policy(
            Policy(
                policy_id="deny_low",
                name="Deny low priority",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="deny_high",
                name="Deny high priority",
                effect=PolicyEffect.DENY,
                priority=50,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "resource.type", ComparisonOperator.EQ, "document"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "EXPLICIT_DENY_OVERRIDE"
        assert "Deny high priority" in result.reason

    def test_explicit_deny_with_permit_overrides_strategy(self, permit_overrides_engine, admin_context):
        permit_overrides_engine.add_policy(
            Policy(
                policy_id="permit1",
                name="Permit admins",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        permit_overrides_engine.add_policy(
            Policy(
                policy_id="deny1",
                name="Deny high sensitivity",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "resource.sensitivity", ComparisonOperator.EQ, "high"
                ),
            )
        )
        result = permit_overrides_engine.evaluate(admin_context)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "EXPLICIT_DENY_OVERRIDE"

    def test_no_explicit_deny_uses_conflict_strategy(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="permit1",
                name="Permit role user",
                effect=PolicyEffect.PERMIT,
                priority=10,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="permit2",
                name="Permit all",
                effect=PolicyEffect.PERMIT,
                priority=5,
                condition=None,
            )
        )
        result = engine.evaluate(admin_context)
        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "ONLY_PERMIT"

    def test_normal_deny_does_not_bypass_conflict_strategy_permit_overrides(
        self, permit_overrides_engine
    ):
        permit_overrides_engine.add_policy(
            Policy(
                policy_id="permit1",
                name="Permit by role",
                effect=PolicyEffect.PERMIT,
                priority=1,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        permit_overrides_engine.add_policy(
            Policy(
                policy_id="deny_normal",
                name="Normal deny by dept",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin", "department": "IT"})
        result = permit_overrides_engine.evaluate(ctx)
        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "PERMIT_OVERRIDES"

    def test_normal_deny_vs_explicit_deny_difference(self):
        engine_normal = ABACEngine(
            conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES
        )
        engine_normal.add_policy(
            Policy(
                policy_id="p1",
                name="Permit",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine_normal.add_policy(
            Policy(
                policy_id="p2",
                name="Normal Deny",
                effect=PolicyEffect.DENY,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )

        engine_explicit = ABACEngine(
            conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES
        )
        engine_explicit.add_policy(
            Policy(
                policy_id="p1",
                name="Permit",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine_explicit.add_policy(
            Policy(
                policy_id="p2",
                name="Explicit Deny",
                effect=PolicyEffect.DENY,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )

        ctx = RequestContext(subject={"role": "admin"})
        assert engine_normal.evaluate(ctx).decision == Decision.PERMIT
        assert engine_explicit.evaluate(ctx).decision == Decision.DENY

    def test_normal_deny_uses_highest_priority(self, highest_priority_engine):
        highest_priority_engine.add_policy(
            Policy(
                policy_id="permit_low",
                name="Low priority permit",
                effect=PolicyEffect.PERMIT,
                priority=1,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        highest_priority_engine.add_policy(
            Policy(
                policy_id="deny_high_normal",
                name="High priority normal deny",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin"})
        result = highest_priority_engine.evaluate(ctx)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "HIGHEST_PRIORITY"
        assert "High priority normal deny" in result.reason

    def test_permit_with_explicit_deny_flag_does_not_trigger_override_via_evaluate(self):
        engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES)

        permit_policy = Policy(
            policy_id="permit_role",
            name="Permit by role",
            effect=PolicyEffect.PERMIT,
            priority=1,
            condition=AttributeCondition(
                "subject.role", ComparisonOperator.EQ, "admin"
            ),
        )
        object.__setattr__(permit_policy, "is_explicit_deny", True)
        engine.add_policy(permit_policy)

        engine.add_policy(
            Policy(
                policy_id="deny_dept",
                name="Normal deny by dept",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )

        ctx = RequestContext(subject={"role": "admin", "department": "IT"})
        result = engine.evaluate(ctx)

        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "PERMIT_OVERRIDES"
        assert "Permit by role" in [h.policy_name for h in result.matched_policies]
        permit_hit = next(
            h for h in result.matched_policies if h.policy_id == "permit_role"
        )
        assert permit_hit.is_explicit_deny is True
        assert permit_hit.effect == PolicyEffect.PERMIT

    def test_real_explicit_deny_triggers_override_via_full_evaluate(self):
        engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES)

        engine.add_policy(
            Policy(
                policy_id="permit_high",
                name="High priority permit",
                effect=PolicyEffect.PERMIT,
                priority=999,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="deny_explicit",
                name="Low priority explicit deny",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )

        ctx = RequestContext(subject={"role": "admin", "department": "IT"})
        result = engine.evaluate(ctx)

        assert result.decision == Decision.DENY
        assert result.resolved_by == "EXPLICIT_DENY_OVERRIDE"
        assert len(result.matched_policies) == 2
        explicit_hit = next(
            h for h in result.matched_policies if h.policy_id == "deny_explicit"
        )
        assert explicit_hit.is_explicit_deny is True
        assert explicit_hit.effect == PolicyEffect.DENY


# =============================
# Conflict Resolution Tests
# =============================


class TestConflictResolution:
    def test_deny_overrides_default(self, engine):
        engine.add_policy(
            Policy(
                policy_id="permit_role",
                name="Permit by role",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="deny_sensitivity",
                name="Deny by sensitivity",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "resource.sensitivity", ComparisonOperator.EQ, "high"
                ),
            )
        )
        ctx = RequestContext(
            subject={"role": "admin"},
            resource={"sensitivity": "high"},
        )
        result = engine.evaluate(ctx)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "DENY_OVERRIDES"

    def test_permit_overrides_strategy(self, permit_overrides_engine):
        permit_overrides_engine.add_policy(
            Policy(
                policy_id="deny1",
                name="Deny by dept",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )
        permit_overrides_engine.add_policy(
            Policy(
                policy_id="permit1",
                name="Permit by role",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin", "department": "IT"})
        result = permit_overrides_engine.evaluate(ctx)
        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "PERMIT_OVERRIDES"

    def test_highest_priority_strategy_deny_wins(self, highest_priority_engine):
        highest_priority_engine.add_policy(
            Policy(
                policy_id="deny_high",
                name="Deny high priority",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        highest_priority_engine.add_policy(
            Policy(
                policy_id="permit_low",
                name="Permit low priority",
                effect=PolicyEffect.PERMIT,
                priority=1,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin"})
        result = highest_priority_engine.evaluate(ctx)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "HIGHEST_PRIORITY"
        assert "Deny high priority" in result.reason

    def test_highest_priority_strategy_permit_wins(self, highest_priority_engine):
        highest_priority_engine.add_policy(
            Policy(
                policy_id="deny_low",
                name="Deny low priority",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        highest_priority_engine.add_policy(
            Policy(
                policy_id="permit_high",
                name="Permit high priority",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin"})
        result = highest_priority_engine.evaluate(ctx)
        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "HIGHEST_PRIORITY"

    def test_first_applicable_strategy_deny_first(self):
        engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.FIRST_APPLICABLE)
        engine.add_policy(
            Policy(
                policy_id="p_deny",
                name="First deny",
                effect=PolicyEffect.DENY,
                priority=1,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="p_permit",
                name="Second permit",
                effect=PolicyEffect.PERMIT,
                priority=100,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin"})
        result = engine.evaluate(ctx)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "FIRST_APPLICABLE"
        assert "First deny" in result.reason
        assert "p_deny" in result.reason

    def test_first_applicable_strategy_permit_first(self):
        engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.FIRST_APPLICABLE)
        engine.add_policy(
            Policy(
                policy_id="p_permit",
                name="First permit",
                effect=PolicyEffect.PERMIT,
                priority=1,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="p_deny",
                name="Second deny",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin"})
        result = engine.evaluate(ctx)
        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "FIRST_APPLICABLE"
        assert "First permit" in result.reason
        assert "p_permit" in result.reason

    def test_first_applicable_stable_order_regardless_of_priority(self):
        engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.FIRST_APPLICABLE)
        engine.add_policy(
            Policy(
                policy_id="first",
                name="Low priority first",
                effect=PolicyEffect.PERMIT,
                priority=0,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="second",
                name="High priority second",
                effect=PolicyEffect.DENY,
                priority=9999,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        ctx = RequestContext(subject={"role": "admin"})
        result = engine.evaluate(ctx)
        assert result.decision == Decision.PERMIT
        assert result.resolved_by == "FIRST_APPLICABLE"
        assert "Low priority first" in result.reason


# =============================
# No Match / Empty Tests
# =============================


class TestNoMatchAndEmpty:
    def test_no_policies_returns_not_applicable(self, engine, admin_context):
        result = engine.evaluate(admin_context)
        assert result.decision == Decision.NOT_APPLICABLE
        assert result.matched_policies == []
        assert "No matching policies" in result.reason

    def test_no_matching_policies(self, engine, user_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Permit admins only",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        result = engine.evaluate(user_context)
        assert result.decision == Decision.NOT_APPLICABLE
        assert len(result.matched_policies) == 0

    def test_policy_without_condition_matches_everything(self, engine, empty_context):
        engine.add_policy(
            Policy(
                policy_id="catch_all",
                name="Catch all permit",
                effect=PolicyEffect.PERMIT,
                condition=None,
            )
        )
        result = engine.evaluate(empty_context)
        assert result.decision == Decision.PERMIT
        assert len(result.matched_policies) == 1

    def test_empty_context_with_policy_needing_attributes(self, engine, empty_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Need role",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        with pytest.raises(UnknownAttributeError):
            engine.evaluate(empty_context)


# =============================
# Error / Exception Tests
# =============================


class TestErrorBranches:
    def test_unknown_attribute_reference_raises(self, engine, empty_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Check missing attr",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.missing_field", ComparisonOperator.EQ, "value"
                ),
            )
        )
        with pytest.raises(UnknownAttributeError, match="subject.missing_field"):
            engine.evaluate(empty_context)

    def test_invalid_attribute_path_format_no_dot(self, engine):
        with pytest.raises(InvalidConditionError, match="Invalid attribute_path format"):
            ABACEngine._parse_attribute_path("invalid_format")

    def test_invalid_attribute_category(self, engine):
        with pytest.raises(InvalidConditionError, match="Invalid attribute category"):
            ABACEngine._parse_attribute_path("bad_category.role")

    def test_valid_attribute_path_parsing(self):
        cat, path = ABACEngine._parse_attribute_path("subject.profile.role")
        assert cat == AttributeCategory.SUBJECT
        assert path == "profile.role"
        cat, path = ABACEngine._parse_attribute_path("resource.type")
        assert cat == AttributeCategory.RESOURCE
        assert path == "type"
        cat, path = ABACEngine._parse_attribute_path("environment.ip")
        assert cat == AttributeCategory.ENVIRONMENT
        assert path == "ip"

    def test_contains_with_unsupported_type_returns_false(self):
        assert ABACEngine._compare(42, "x", ComparisonOperator.CONTAINS) is False

    def test_in_with_unsupported_type_returns_false(self):
        assert ABACEngine._compare("x", "not a list", ComparisonOperator.IN) is False

    def test_starts_with_non_string_returns_false(self):
        assert ABACEngine._compare(123, "1", ComparisonOperator.STARTS_WITH) is False

    def test_ends_with_non_string_returns_false(self):
        assert ABACEngine._compare(123, "3", ComparisonOperator.ENDS_WITH) is False

    def test_exception_hierarchy(self):
        assert issubclass(InvalidPolicyError, ABACError)
        assert issubclass(InvalidConditionError, ABACError)
        assert issubclass(UnknownAttributeError, ABACError)
        assert issubclass(PolicyNotFoundError, ABACError)

    def test_unknown_attribute_error_stores_path(self):
        err = UnknownAttributeError("subject.role")
        assert err.attribute_path == "subject.role"

    def test_policy_not_found_error_stores_id(self):
        err = PolicyNotFoundError("p1")
        assert err.policy_id == "p1"


# =============================
# Audit / Matched Policies Tests
# =============================


class TestAuditInformation:
    def test_matched_policies_recorded(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Permit admins",
                effect=PolicyEffect.PERMIT,
                priority=10,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        assert len(result.matched_policies) == 1
        hit = result.matched_policies[0]
        assert hit.policy_id == "p1"
        assert hit.policy_name == "Permit admins"
        assert hit.effect == PolicyEffect.PERMIT
        assert hit.priority == 10
        assert hit.is_explicit_deny is False
        assert hit.matched_at > 0
        assert hit.order == 0

    def test_multiple_matched_policies_recorded(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="p1",
                name="Permit admins",
                effect=PolicyEffect.PERMIT,
                priority=10,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="p2",
                name="Permit IT",
                effect=PolicyEffect.PERMIT,
                priority=5,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="p3",
                name="Permit docs",
                effect=PolicyEffect.PERMIT,
                priority=1,
                condition=AttributeCondition(
                    "resource.type", ComparisonOperator.EQ, "document"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        assert len(result.matched_policies) == 3
        ids = {h.policy_id for h in result.matched_policies}
        assert ids == {"p1", "p2", "p3"}
        orders = sorted(h.order for h in result.matched_policies)
        assert orders == [0, 1, 2]

    def test_normal_deny_policy_hit_recorded(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="d1",
                name="Normal deny high sensitivity",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "resource.sensitivity", ComparisonOperator.EQ, "high"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        hit = result.matched_policies[0]
        assert hit.is_explicit_deny is False
        assert hit.effect == PolicyEffect.DENY

    def test_explicit_deny_policy_hit_recorded(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="d1",
                name="Explicit deny high sensitivity",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=True,
                condition=AttributeCondition(
                    "resource.sensitivity", ComparisonOperator.EQ, "high"
                ),
            )
        )
        result = engine.evaluate(admin_context)
        hit = result.matched_policies[0]
        assert hit.is_explicit_deny is True
        assert hit.effect == PolicyEffect.DENY

    def test_multi_policy_conflict_audit_contains_all_hits(self, engine):
        engine.add_policy(
            Policy(
                policy_id="perm1",
                name="Permit by role",
                effect=PolicyEffect.PERMIT,
                priority=10,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="deny1",
                name="Normal deny by dept",
                effect=PolicyEffect.DENY,
                priority=20,
                is_explicit_deny=False,
                condition=AttributeCondition(
                    "subject.department", ComparisonOperator.EQ, "IT"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="perm2",
                name="Permit by ip",
                effect=PolicyEffect.PERMIT,
                priority=5,
                condition=AttributeCondition(
                    "environment.ip", ComparisonOperator.EQ, "192.168.1.1"
                ),
            )
        )
        ctx = RequestContext(
            subject={"role": "admin", "department": "IT"},
            environment={"ip": "192.168.1.1"},
        )
        result = engine.evaluate(ctx)
        assert len(result.matched_policies) == 3
        hit_ids = [h.policy_id for h in result.matched_policies]
        assert hit_ids == ["perm1", "deny1", "perm2"]
        for i, h in enumerate(result.matched_policies):
            assert h.order == i
        assert result.decision == Decision.DENY
        assert result.resolved_by == "DENY_OVERRIDES"

    def test_audit_order_preserved_across_evaluations(self, engine, admin_context):
        engine.add_policy(
            Policy(
                policy_id="a",
                name="Policy A",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "subject.role", ComparisonOperator.EQ, "admin"
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="b",
                name="Policy B",
                effect=PolicyEffect.PERMIT,
                condition=AttributeCondition(
                    "resource.type", ComparisonOperator.EQ, "document"
                ),
            )
        )
        r1 = engine.evaluate(admin_context)
        r2 = engine.evaluate(admin_context)
        assert [h.order for h in r1.matched_policies] == [0, 1]
        assert [h.order for h in r2.matched_policies] == [0, 1]
        assert [h.policy_id for h in r1.matched_policies] == ["a", "b"]
        assert [h.policy_id for h in r2.matched_policies] == ["a", "b"]


# =============================
# Integration Scenario Tests
# =============================


class TestIntegrationScenarios:
    def test_document_access_control_scenario(self):
        engine = ABACEngine()

        engine.add_policy(
            Policy(
                policy_id="deny_outside_hours",
                name="Deny access outside business hours",
                effect=PolicyEffect.DENY,
                priority=100,
                is_explicit_deny=True,
                condition=ConditionExpression(
                    LogicalOperator.NOT,
                    operands=[
                        AttributeCondition(
                            "environment.hour",
                            ComparisonOperator.IN,
                            list(range(9, 18)),
                        ),
                    ],
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="permit_owner",
                name="Permit document owner",
                effect=PolicyEffect.PERMIT,
                priority=10,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition(
                            "resource.type", ComparisonOperator.EQ, "document"
                        ),
                        AttributeCondition(
                            "subject.user_id", ComparisonOperator.EQ, "u1"
                        ),
                        AttributeCondition(
                            "resource.owner", ComparisonOperator.EQ, "u1"
                        ),
                    ],
                ),
            )
        )
        engine.add_policy(
            Policy(
                policy_id="permit_admin_view",
                name="Permit admin to view any document",
                effect=PolicyEffect.PERMIT,
                priority=20,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition(
                            "subject.role", ComparisonOperator.EQ, "admin"
                        ),
                        AttributeCondition(
                            "resource.type", ComparisonOperator.EQ, "document"
                        ),
                    ],
                ),
            )
        )

        owner_business_hours = RequestContext(
            subject={"user_id": "u1", "role": "user"},
            resource={"type": "document", "owner": "u1"},
            environment={"hour": 10},
        )
        result = engine.evaluate(owner_business_hours)
        assert result.decision == Decision.PERMIT

        admin_outside_hours = RequestContext(
            subject={"user_id": "u99", "role": "admin"},
            resource={"type": "document", "owner": "u1"},
            environment={"hour": 20},
        )
        result = engine.evaluate(admin_outside_hours)
        assert result.decision == Decision.DENY
        assert result.resolved_by == "EXPLICIT_DENY_OVERRIDE"

        stranger_business_hours = RequestContext(
            subject={"user_id": "u50", "role": "user"},
            resource={"type": "document", "owner": "u1"},
            environment={"hour": 10},
        )
        result = engine.evaluate(stranger_business_hours)
        assert result.decision == Decision.NOT_APPLICABLE

    def test_cross_category_conditions(self):
        engine = ABACEngine()
        engine.add_policy(
            Policy(
                policy_id="cross",
                name="Cross category check",
                effect=PolicyEffect.PERMIT,
                condition=ConditionExpression(
                    LogicalOperator.AND,
                    operands=[
                        AttributeCondition(
                            "subject.role", ComparisonOperator.EQ, "manager"
                        ),
                        AttributeCondition(
                            "resource.classification",
                            ComparisonOperator.LTE,
                            "internal",
                        ),
                        AttributeCondition(
                            "environment.network",
                            ComparisonOperator.EQ,
                            "corporate",
                        ),
                    ],
                ),
            )
        )
        ctx = RequestContext(
            subject={"role": "manager"},
            resource={"classification": "internal"},
            environment={"network": "corporate"},
        )
        assert engine.evaluate(ctx).decision == Decision.PERMIT
