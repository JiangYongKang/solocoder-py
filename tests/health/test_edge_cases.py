from __future__ import annotations

import pytest

from solocoder_py.health import (
    CircularDependencyError,
    ComponentConfig,
    HealthCheckAggregator,
    HealthStatus,
)

from .conftest import make_component_config


class TestNoDependencyComponent:
    def test_standalone_component_check(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="standalone")
        )
        health = aggregator.check_component("standalone")
        assert health.component_id == "standalone"
        assert health.dependencies == []
        assert health.is_ready()
        assert health.is_alive()
        assert health.readiness.cascaded_from is None

    def test_multiple_independent_components(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        aggregator.register_component(
            make_component_config(component_id="comp2")
        )
        aggregator.register_component(
            make_component_config(component_id="comp3")
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY
        assert len(result.components) == 3
        for cid in ["comp1", "comp2", "comp3"]:
            assert result.components[cid].dependencies == []
            assert result.components[cid].readiness.cascaded_from is None

    def test_independent_component_unhealthy_no_cascade(self, aggregator: HealthCheckAggregator):
        def bad_check():
            return False, "Failed"

        aggregator.register_component(
            make_component_config(component_id="bad", readiness_check=bad_check)
        )
        aggregator.register_component(
            make_component_config(component_id="good")
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["bad"].is_ready()
        assert result.components["good"].is_ready()
        assert result.components["good"].readiness.cascaded_from is None


class TestCircularDependencyDetection:
    def test_direct_self_dependency_detected(self, aggregator: HealthCheckAggregator):
        with pytest.raises(CircularDependencyError, match="cannot depend on itself"):
            aggregator.register_component(
                make_component_config(
                    component_id="comp1",
                    dependencies=["comp1"],
                )
            )
        assert aggregator.is_registered("comp1") is False

    def test_acyclic_graph_passes_detection(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        aggregator.register_component(
            make_component_config(component_id="comp2", dependencies=["comp1"])
        )
        aggregator.register_component(
            make_component_config(component_id="comp3", dependencies=["comp2"])
        )
        aggregator._detect_circular_dependencies()
        assert True

    def test_circular_detection_prevents_registration(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        aggregator.register_component(
            make_component_config(component_id="comp2", dependencies=["comp1"])
        )
        original_count = len(aggregator.get_all_component_ids())
        try:
            aggregator._components["comp1"].dependencies = ["comp2"]
            aggregator._detect_circular_dependencies()
        except CircularDependencyError:
            pass
        assert len(aggregator.get_all_component_ids()) == original_count

    def test_manual_cycle_detection(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="a")
        )
        aggregator.register_component(
            make_component_config(component_id="b", dependencies=["a"])
        )
        aggregator._components["a"].dependencies = ["b"]
        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            aggregator._detect_circular_dependencies()

    def test_complex_graph_no_false_positive(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="db")
        )
        aggregator.register_component(
            make_component_config(component_id="cache", dependencies=["db"])
        )
        aggregator.register_component(
            make_component_config(component_id="api", dependencies=["db", "cache"])
        )
        aggregator.register_component(
            make_component_config(component_id="gateway", dependencies=["api"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY


class TestEmptyAggregator:
    def test_empty_aggregator_check_all(self, aggregator: HealthCheckAggregator):
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY
        assert result.components == {}
        assert result.degraded_components == []
        data = result.to_dict()
        assert data["overall_status"] == "healthy"
        assert data["components"] == {}
        assert data["degraded_components"] == []

    def test_empty_aggregator_get_component_ids(self, aggregator: HealthCheckAggregator):
        assert aggregator.get_all_component_ids() == []

    def test_empty_aggregator_is_registered(self, aggregator: HealthCheckAggregator):
        assert aggregator.is_registered("anything") is False

    def test_empty_aggregator_get_config(self, aggregator: HealthCheckAggregator):
        assert aggregator.get_component_config("nonexistent") is None

    def test_add_and_remove_all_components(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="comp1")
        )
        aggregator.register_component(
            make_component_config(component_id="comp2", dependencies=["comp1"])
        )
        assert len(aggregator.get_all_component_ids()) == 2
        aggregator.unregister_component("comp2")
        aggregator.unregister_component("comp1")
        assert len(aggregator.get_all_component_ids()) == 0
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY


class TestSingleProbeType:
    def test_only_readiness_probe(self, aggregator: HealthCheckAggregator):
        cfg = ComponentConfig(
            component_id="readiness_only",
            readiness_check=lambda: (True, None),
        )
        aggregator.register_component(cfg)
        health = aggregator.check_component("readiness_only")
        assert health.is_ready()
        assert health.is_alive()

    def test_only_liveness_probe(self, aggregator: HealthCheckAggregator):
        cfg = ComponentConfig(
            component_id="liveness_only",
            liveness_check=lambda: (True, None),
        )
        aggregator.register_component(cfg)
        health = aggregator.check_component("liveness_only")
        assert health.is_ready()
        assert health.is_alive()

    def test_only_liveness_probe_unhealthy(self, aggregator: HealthCheckAggregator):
        cfg = ComponentConfig(
            component_id="liveness_only",
            is_core=True,
            liveness_check=lambda: (False, "Dead"),
        )
        aggregator.register_component(cfg)
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.UNAVAILABLE
        assert not result.components["liveness_only"].is_alive()

    def test_only_readiness_probe_unhealthy(self, aggregator: HealthCheckAggregator):
        cfg = ComponentConfig(
            component_id="readiness_only",
            readiness_check=lambda: (False, "Not ready"),
        )
        aggregator.register_component(cfg)
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["readiness_only"].is_ready()
        assert result.components["readiness_only"].is_alive()


class TestDependencyEdgeCases:
    def test_multiple_dependencies_one_unhealthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="dep1")
        )
        aggregator.register_component(
            make_component_config(
                component_id="dep2",
                readiness_check=lambda: (False, "Failed"),
            )
        )
        aggregator.register_component(
            make_component_config(
                component_id="main",
                dependencies=["dep1", "dep2"],
            )
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert result.components["dep1"].is_ready()
        assert not result.components["dep2"].is_ready()
        assert not result.components["main"].is_ready()
        assert result.components["main"].readiness.cascaded_from == "dep2"

    def test_deep_dependency_chain_healthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="l1")
        )
        aggregator.register_component(
            make_component_config(component_id="l2", dependencies=["l1"])
        )
        aggregator.register_component(
            make_component_config(component_id="l3", dependencies=["l2"])
        )
        aggregator.register_component(
            make_component_config(component_id="l4", dependencies=["l3"])
        )
        aggregator.register_component(
            make_component_config(component_id="l5", dependencies=["l4"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY
        for i in range(1, 6):
            assert result.components[f"l{i}"].is_ready()
            assert result.components[f"l{i}"].readiness.cascaded_from is None

    def test_diamond_dependency_graph(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(component_id="base")
        )
        aggregator.register_component(
            make_component_config(component_id="left", dependencies=["base"])
        )
        aggregator.register_component(
            make_component_config(component_id="right", dependencies=["base"])
        )
        aggregator.register_component(
            make_component_config(component_id="top", dependencies=["left", "right"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.HEALTHY

    def test_diamond_dependency_with_base_unhealthy(self, aggregator: HealthCheckAggregator):
        aggregator.register_component(
            make_component_config(
                component_id="base",
                readiness_check=lambda: (False, "Failed"),
            )
        )
        aggregator.register_component(
            make_component_config(component_id="left", dependencies=["base"])
        )
        aggregator.register_component(
            make_component_config(component_id="right", dependencies=["base"])
        )
        aggregator.register_component(
            make_component_config(component_id="top", dependencies=["left", "right"])
        )
        result = aggregator.check_all()
        assert result.overall_status == HealthStatus.DEGRADED
        assert not result.components["base"].is_ready()
        assert not result.components["left"].is_ready()
        assert not result.components["right"].is_ready()
        assert not result.components["top"].is_ready()
        assert result.components["left"].readiness.cascaded_from == "base"
        assert result.components["right"].readiness.cascaded_from == "base"
        assert result.components["top"].readiness.cascaded_from == "left"


class TestComponentConfigValidation:
    def test_component_config_post_init_validation(self):
        from solocoder_py.health import InvalidComponentConfigError

        with pytest.raises(InvalidComponentConfigError, match="component_id must not be empty"):
            ComponentConfig(
                component_id="",
                readiness_check=lambda: (True, None),
            )

        with pytest.raises(InvalidComponentConfigError, match="At least one"):
            ComponentConfig(component_id="comp1")

    def test_valid_config_passes_validation(self):
        cfg = ComponentConfig(
            component_id="valid",
            readiness_check=lambda: (True, None),
        )
        assert cfg.component_id == "valid"
