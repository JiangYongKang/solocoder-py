from __future__ import annotations

import pytest

from solocoder_py.health import (
    ComponentAlreadyRegisteredError,
    ComponentConfig,
    ComponentNotFoundError,
    HealthCheckAggregator,
    HealthStatus,
    InvalidComponentConfigError,
)

from .conftest import make_component_config


class TestCheckFunctionExceptionHandling:
    def test_readiness_check_raises_exception(self, aggregator: HealthCheckAggregator):
        def bad_check():
            raise RuntimeError("Something went wrong")

        aggregator.register_component(
            make_component_config(
                component_id="flaky",
                readiness_check=bad_check,
            )
        )
        result = aggregator.check_component("flaky")
        assert not result.is_ready()
        assert result.is_alive()
        assert "RuntimeError" in result.readiness.error
        assert "Something went wrong" in result.readiness.error

    def test_liveness_check_raises_exception(self, aggregator: HealthCheckAggregator):
        def bad_check():
            raise ValueError("Invalid state")

        aggregator.register_component(
            make_component_config(
                component_id="flaky",
                is_core=True,
                liveness_check=bad_check,
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.UNAVAILABLE
        assert not result.components["flaky"].is_alive()
        assert "ValueError" in result.components["flaky"].liveness.error
        assert "Invalid state" in result.components["flaky"].liveness.error

    def test_exception_in_dependency_propagates_cascade(self, aggregator: HealthCheckAggregator):
        def bad_check():
            raise ConnectionError("Database down")

        aggregator.register_component(
            make_component_config(
                component_id="db",
                readiness_check=bad_check,
            )
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["db"].is_ready()
        assert not result.components["api"].is_ready()
        assert "ConnectionError" in result.components["db"].readiness.error
        assert result.components["api"].readiness.cascaded_from == "db"
        assert result.components["api"].readiness.root_cause == "db"

    def test_multiple_exceptions_handled_independently(self, aggregator: HealthCheckAggregator):
        def check1():
            raise TypeError("Type error")

        def check2():
            raise AttributeError("Attr error")

        aggregator.register_component(
            make_component_config(component_id="comp1", readiness_check=check1)
        )
        aggregator.register_component(
            make_component_config(component_id="comp2", readiness_check=check2)
        )
        aggregator.register_component(
            make_component_config(component_id="comp3")
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["comp1"].is_ready()
        assert not result.components["comp2"].is_ready()
        assert result.components["comp3"].is_ready()
        assert "TypeError" in result.components["comp1"].readiness.error
        assert "AttributeError" in result.components["comp2"].readiness.error

    def test_non_tuple_return_value(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            ComponentConfig(
                component_id="comp1",
                readiness_check=lambda: False,
                liveness_check=lambda: True,
            )
        )
        result = aggregator.check_component("comp1")
        assert not result.is_ready()
        assert result.is_alive()
        assert result.readiness.error is None

    def test_non_string_error_converted(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            ComponentConfig(
                component_id="comp1",
                readiness_check=lambda: (False, 404),
                liveness_check=lambda: (True, None),
            )
        )
        result = aggregator.check_component("comp1")
        assert not result.is_ready()
        assert result.readiness.error == "404"


class TestUnregisteredComponentAccess:
    def test_check_unregistered_component_raises(self, aggregator: HealthCheckAggregator):
        with pytest.raises(ComponentNotFoundError, match="not registered"):
            aggregator.check_component("nonexistent")

    def test_unregister_unregistered_component_raises(self, aggregator: HealthCheckAggregator):
        with pytest.raises(ComponentNotFoundError, match="not registered"):
            aggregator.unregister_component("nonexistent")

    def test_register_with_unregistered_dependency_raises(self, aggregator: HealthCheckAggregator):
        with pytest.raises(ComponentNotFoundError, match="not registered"):
            aggregator.register_component(
                make_component_config(
                    component_id="comp1",
                    dependencies=["nonexistent"],
                )
            )
        assert aggregator.is_registered("comp1") is False

    def test_dependency_must_exist_before_dependent(self, aggregator: HealthCheckAggregator):
        with pytest.raises(ComponentNotFoundError):
            aggregator.register_component(
                make_component_config(
                    component_id="api",
                    dependencies=["db"],
                )
            )
        aggregator.register_component(
            make_component_config(component_id="db")
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        assert aggregator.is_registered("api") is True


class TestDuplicateRegistration:
    def test_register_same_component_twice_raises(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        with pytest.raises(ComponentAlreadyRegisteredError, match="already registered"):
            aggregator.register_component(
                make_component_config(component_id="comp1")
            )

    def test_duplicate_registration_preserves_original(self, aggregator: HealthCheckAggregator):
        original_check = lambda: (True, "original")
        new_check = lambda: (False, "new")

        aggregator.register_component(
            make_component_config(
                component_id="comp1",
                readiness_check=original_check,
            )
        )
        try:
            aggregator.register_component(
                make_component_config(
                    component_id="comp1",
                    readiness_check=new_check,
                )
            )
        except ComponentAlreadyRegisteredError:
            pass
        cfg = aggregator.get_component_config("comp1")
        assert cfg is not None
        result = aggregator.check_component("comp1")
        assert result.is_ready()

    def test_unregister_then_reregister_allowed(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        aggregator.unregister_component("comp1")
        aggregator.register_component(
            make_component_config(
                component_id="comp1",
                readiness_check=lambda: (False, "Changed"),
            )
        )
        result = aggregator.check_component("comp1")
        assert not result.is_ready()
        assert "Changed" in result.readiness.error


class TestUnregisterWithDependents:
    def test_unregister_component_with_dependents_raises(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="db")
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        with pytest.raises(InvalidComponentConfigError, match="is a dependency of"):
            aggregator.unregister_component("db")
        assert aggregator.is_registered("db") is True

    def test_unregister_dependents_first_then_dependency(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="db")
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        aggregator.register_component(
            make_component_config(component_id="gateway", dependencies=["api"])
        )
        aggregator.unregister_component("gateway")
        aggregator.unregister_component("api")
        aggregator.unregister_component("db")
        assert len(aggregator.get_all_component_ids()) == 0


class TestInvalidConfig:
    def test_empty_component_id_raises(self):
        with pytest.raises(InvalidComponentConfigError, match="component_id must not be empty"):
            ComponentConfig(
                component_id="",
                readiness_check=lambda: (True, None),
            )

    def test_no_probes_raises(self):
        with pytest.raises(InvalidComponentConfigError, match="At least one"):
            ComponentConfig(component_id="comp1")

    def test_whitespace_component_id_raises(self):
        with pytest.raises(InvalidComponentConfigError):
            ComponentConfig(
                component_id="   ",
                readiness_check=lambda: (True, None),
            )


class TestMixedHealthScenarios:
    def test_core_alive_failure_overrides_degraded(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="core",
                is_core=True,
                liveness_check=lambda: (False, "Dead"),
            )
        )
        aggregator.register_component(
            make_component_config(
                component_id="noncore",
                readiness_check=lambda: (False, "Not ready"),
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.UNAVAILABLE

    def test_all_core_alive_some_noncore_unhealthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="core1", is_core=True)
        )
        aggregator.register_component(
            make_component_config(component_id="core2", is_core=True)
        )
        aggregator.register_component(
            make_component_config(
                component_id="noncore1",
                readiness_check=lambda: (False, "Failed"),
            )
        )
        aggregator.register_component(
            make_component_config(component_id="noncore2")
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        degraded_ids = [dc.component_id for dc in result.degraded_components]
        assert "noncore1" in degraded_ids
        assert "core1" not in degraded_ids
        assert "core2" not in degraded_ids
        assert "noncore2" not in degraded_ids

    def test_check_all_visits_each_component_once(self, aggregator: HealthCheckAggregator):
        call_count = {"db": 0, "api": 0}

        def db_check():
            call_count["db"] += 1
            return (True, None)

        def api_check():
            call_count["api"] += 1
            return (True, None)

        aggregator.register_component(
            make_component_config(
                component_id="db",
                readiness_check=db_check,
            )
        )
        aggregator.register_component(
            make_component_config(
                component_id="api",
                dependencies=["db"],
                readiness_check=api_check,
            )
        )
        aggregator.check_all()
        assert call_count["db"] == 1
        assert call_count["api"] == 1

    def test_check_component_visits_dependencies(self, aggregator: HealthCheckAggregator):
        call_count = {"l1": 0, "l2": 0, "l3": 0}

        def make_check(name):
            def check():
                call_count[name] += 1
                return (True, None)
            return check

        aggregator.register_component(
            make_component_config(
                component_id="l1",
                readiness_check=make_check("l1"),
            )
        )
        aggregator.register_component(
            make_component_config(
                component_id="l2",
                dependencies=["l1"],
                readiness_check=make_check("l2"),
            )
        )
        aggregator.register_component(
            make_component_config(
                component_id="l3",
                dependencies=["l2"],
                readiness_check=make_check("l3"),
            )
        )
        aggregator.check_component("l3")
        assert call_count["l1"] == 1
        assert call_count["l2"] == 1
        assert call_count["l3"] == 1


class TestProbeResultImmutability:
    def test_component_health_not_affecting_internal_state(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        health1 = aggregator.check_component("comp1")
        health1.readiness.healthy = False
        health1.readiness.error = "Modified"
        health2 = aggregator.check_component("comp1")
        assert health2.is_ready()
        assert health2.readiness.error is None
