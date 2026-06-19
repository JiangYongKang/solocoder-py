from __future__ import annotations

import pytest

from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
    HealthStatus,
)

from .conftest import make_component_config, unhealthy_check


class TestAllComponentsHealthy:
    def test_single_component_healthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY
        assert "comp1" in result.components
        assert result.components["comp1"].is_ready()
        assert result.components["comp1"].is_alive()
        assert len(result.degraded_components) == 0

    def test_multiple_components_all_healthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="db", is_core=True)
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        aggregator.register_component(
            make_component_config(component_id="cache", dependencies=["db"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY
        assert len(result.degraded_components) == 0
        for cid in ["db", "api", "cache"]:
            assert result.components[cid].is_ready()
            assert result.components[cid].is_alive()

    def test_to_dict_serialization(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1", is_core=True)
        )
        result = aggregator.check_all()
        data = result.to_dict()
        assert data["overall_status"] == "healthy"
        assert "comp1" in data["components"]
        assert data["components"]["comp1"]["is_core"] is True
        assert data["components"]["comp1"]["readiness"]["healthy"] is True
        assert data["components"]["comp1"]["liveness"]["healthy"] is True
        assert data["degraded_components"] == []


class TestSingleComponentReadinessUnhealthy:
    def test_single_component_readiness_unhealthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="comp1",
                readiness_check=unhealthy_check,
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert len(result.degraded_components) == 1
        assert result.degraded_components[0].component_id == "comp1"
        assert "Check failed" in result.degraded_components[0].reason
        assert result.components["comp1"].is_alive()

    def test_cascaded_degradation(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="db",
                readiness_check=unhealthy_check,
            )
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        degraded_ids = [dc.component_id for dc in result.degraded_components]
        assert "db" in degraded_ids
        assert "api" in degraded_ids
        assert result.components["api"].readiness.cascaded_from == "db"
        assert result.components["api"].readiness.root_cause == "db"
        assert "Cascaded from unhealthy dependency: db" in [
            dc.reason for dc in result.degraded_components if dc.component_id == "api"
        ][0]


class TestThreeLevelDependencyChain:
    def test_three_level_cascaded_propagation(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="level1",
                readiness_check=unhealthy_check,
            )
        )
        aggregator.register_component(
            make_component_config(component_id="level2", dependencies=["level1"])
        )
        aggregator.register_component(
            make_component_config(component_id="level3", dependencies=["level2"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["level1"].is_ready()
        assert not result.components["level2"].is_ready()
        assert not result.components["level3"].is_ready()
        assert result.components["level1"].readiness.cascaded_from is None
        assert result.components["level1"].readiness.root_cause is None
        assert result.components["level2"].readiness.cascaded_from == "level1"
        assert result.components["level2"].readiness.root_cause == "level1"
        assert result.components["level3"].readiness.cascaded_from == "level2"
        assert result.components["level3"].readiness.root_cause == "level1"
        api_reason = [
            dc.reason for dc in result.degraded_components if dc.component_id == "level3"
        ][0]
        assert "level1" in api_reason

    def test_middle_component_unhealthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="level1")
        )
        aggregator.register_component(
            make_component_config(
                component_id="level2",
                dependencies=["level1"],
                readiness_check=unhealthy_check,
            )
        )
        aggregator.register_component(
            make_component_config(component_id="level3", dependencies=["level2"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert result.components["level1"].is_ready()
        assert not result.components["level2"].is_ready()
        assert not result.components["level3"].is_ready()
        assert result.components["level2"].readiness.cascaded_from is None
        assert result.components["level2"].readiness.root_cause is None
        assert result.components["level3"].readiness.cascaded_from == "level2"
        assert result.components["level3"].readiness.root_cause == "level2"


class TestLivenessProbeIndependent:
    def test_liveness_not_affected_by_dependency_readiness(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="db",
                readiness_check=unhealthy_check,
            )
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db"])
        )
        result = aggregator.check_all()
        assert not result.components["api"].is_ready()
        assert result.components["api"].is_alive()
        assert result.components["db"].is_alive()

    def test_liveness_failure_only_marks_unavailable(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="core",
                is_core=True,
                liveness_check=lambda: (False, "Process crashed"),
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.UNAVAILABLE
        assert not result.components["core"].is_alive()

    def test_non_core_liveness_failure_marks_degraded(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="non_core",
                is_core=False,
                liveness_check=lambda: (False, "Not responding"),
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["non_core"].is_alive()


class TestCoreComponentUnavailable:
    def test_core_component_liveness_failure(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="non_core1")
        )
        aggregator.register_component(
            make_component_config(
                component_id="core_db",
                is_core=True,
                liveness_check=lambda: (False, "Dead"),
            )
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["core_db"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.UNAVAILABLE

    def test_multiple_core_components_one_failed(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="core1", is_core=True)
        )
        aggregator.register_component(
            make_component_config(
                component_id="core2",
                is_core=True,
                liveness_check=lambda: (False, "Failed"),
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.UNAVAILABLE


class TestComponentQueries:
    def test_check_single_component(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        health = aggregator.check_component("comp1")
        assert health.component_id == "comp1"
        assert health.is_ready()
        assert health.is_alive()

    def test_is_registered(self, aggregator: HealthCheckAggregator):
        assert aggregator.is_registered("comp1") is False
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        assert aggregator.is_registered("comp1") is True

    def test_get_component_config(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="dep1")
        )
        aggregator.register_component(
            make_component_config(
                component_id="comp1",
                is_core=True,
                dependencies=["dep1"],
            )
        )
        cfg = aggregator.get_component_config("comp1")
        assert cfg is not None
        assert cfg.component_id == "comp1"
        assert cfg.is_core is True
        assert cfg.dependencies == ["dep1"]

    def test_get_component_config_returns_none_for_unregistered(self, aggregator: HealthCheckAggregator):
        assert aggregator.get_component_config("nonexistent") is None

    def test_get_all_component_ids(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        aggregator.register_component(
            make_component_config(component_id="comp2", dependencies=["comp1"])
        )
        ids = aggregator.get_all_component_ids()
        assert set(ids) == {"comp1", "comp2"}

    def test_unregister_component(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        assert aggregator.is_registered("comp1") is True
        aggregator.unregister_component("comp1")
        assert aggregator.is_registered("comp1") is False


class TestCheckResultDetails:
    def test_probe_result_contains_error_message(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="comp1",
                readiness_check=lambda: (False, "Custom error message"),
            )
        )
        result = aggregator.check_component("comp1")
        assert result.readiness.error == "Custom error message"
        assert result.readiness.healthy is False

    def test_probe_result_no_error_when_healthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1"))
        result = aggregator.check_component("comp1")
        assert result.readiness.error is None
        assert result.readiness.healthy is True

    def test_boolean_return_from_check(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            ComponentConfig(
                component_id="comp1",
                readiness_check=lambda: False,
                liveness_check=lambda: True,
            )
        )
        result = aggregator.check_component("comp1")
        assert result.readiness.healthy is False
        assert result.liveness.healthy is True
