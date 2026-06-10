from __future__ import annotations

import random

import pytest

from solocoder_py.load_balancer import (
    CircuitState,
    ConnectionLeakError,
    InstanceAlreadyRegisteredError,
    InstanceConfig,
    InstanceHealth,
    InstanceNotFoundError,
    InvalidConfigError,
    LeastConnectionsStrategy,
    Lease,
    LoadBalancer,
    LoadBalancerConfig,
    ManualClock,
    NoAvailableInstanceError,
    RoundRobinStrategy,
    SelectionStrategy,
    WeightedRandomStrategy,
)

from .conftest import make_config, make_lb


class TestLoadBalancerConfig:
    def test_default_config_is_valid(self):
        cfg = LoadBalancerConfig()
        assert cfg.default_strategy == SelectionStrategy.ROUND_ROBIN
        assert cfg.failure_threshold == 3
        assert cfg.recovery_timeout_seconds == 30.0
        assert cfg.half_open_max_probes == 1

    def test_invalid_failure_threshold_raises(self):
        with pytest.raises(InvalidConfigError):
            LoadBalancerConfig(failure_threshold=0)
        with pytest.raises(InvalidConfigError):
            LoadBalancerConfig(failure_threshold=-1)

    def test_invalid_recovery_timeout_raises(self):
        with pytest.raises(InvalidConfigError):
            LoadBalancerConfig(recovery_timeout_seconds=0)
        with pytest.raises(InvalidConfigError):
            LoadBalancerConfig(recovery_timeout_seconds=-1)

    def test_invalid_half_open_max_probes_raises(self):
        with pytest.raises(InvalidConfigError):
            LoadBalancerConfig(half_open_max_probes=0)
        with pytest.raises(InvalidConfigError):
            LoadBalancerConfig(half_open_max_probes=-1)


class TestInstanceConfig:
    def test_valid_instance_config(self):
        cfg = InstanceConfig(instance_id="s1", address="10.0.0.1", weight=3)
        assert cfg.instance_id == "s1"
        assert cfg.address == "10.0.0.1"
        assert cfg.weight == 3

    def test_empty_instance_id_raises(self):
        with pytest.raises(InvalidConfigError):
            InstanceConfig(instance_id="", weight=1)

    def test_negative_weight_raises(self):
        with pytest.raises(InvalidConfigError):
            InstanceConfig(instance_id="s1", weight=-1)

    def test_zero_weight_is_valid(self):
        cfg = InstanceConfig(instance_id="s1", weight=0)
        assert cfg.weight == 0


class TestManualClock:
    def test_initial_time(self):
        clock = ManualClock(start_time=100.0)
        assert clock.now() == 100.0

    def test_advance(self):
        clock = ManualClock()
        clock.advance(5.0)
        assert clock.now() == 5.0
        clock.advance(3.0)
        assert clock.now() == 8.0

    def test_advance_negative_raises(self):
        clock = ManualClock()
        with pytest.raises(ValueError):
            clock.advance(-1)

    def test_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0


class TestLoadBalancerRegistration:
    def test_register_instance(self, lb: LoadBalancer):
        lb.register_instance("s1", address="10.0.0.1", weight=2)
        assert lb.is_registered("s1") is True
        inst = lb.get_instance("s1")
        assert inst is not None
        assert inst.instance_id == "s1"
        assert inst.address == "10.0.0.1"
        assert inst.weight == 2
        assert inst.health == InstanceHealth.HEALTHY
        assert inst.circuit_state == CircuitState.CLOSED

    def test_register_instance_defaults(self, lb: LoadBalancer):
        lb.register_instance("s1")
        inst = lb.get_instance("s1")
        assert inst.address == ""
        assert inst.weight == 1

    def test_register_duplicate_raises(self, lb: LoadBalancer):
        lb.register_instance("s1")
        with pytest.raises(InstanceAlreadyRegisteredError):
            lb.register_instance("s1")

    def test_register_from_config(self, lb: LoadBalancer):
        cfg = InstanceConfig(instance_id="s1", address="10.0.0.2", weight=5)
        lb.register_instance_from_config(cfg)
        inst = lb.get_instance("s1")
        assert inst.address == "10.0.0.2"
        assert inst.weight == 5

    def test_unregister_instance(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.unregister_instance("s1")
        assert lb.is_registered("s1") is False
        assert lb.get_instance("s1") is None

    def test_unregister_nonexistent_raises(self, lb: LoadBalancer):
        with pytest.raises(InstanceNotFoundError):
            lb.unregister_instance("nope")

    def test_get_nonexistent_returns_none(self, lb: LoadBalancer):
        assert lb.get_instance("nope") is None

    def test_get_all_instances(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        all_inst = lb.get_all_instances()
        assert set(all_inst.keys()) == {"s1", "s2"}

    def test_get_instance_returns_clone(self, lb: LoadBalancer):
        lb.register_instance("s1")
        inst = lb.get_instance("s1")
        inst.health = InstanceHealth.UNHEALTHY
        stored = lb.get_instance("s1")
        assert stored.health == InstanceHealth.HEALTHY


class TestHealthManagement:
    def test_mark_unhealthy(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.mark_unhealthy("s1")
        assert lb.get_instance("s1").health == InstanceHealth.UNHEALTHY

    def test_mark_healthy(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.mark_unhealthy("s1")
        lb.mark_healthy("s1")
        assert lb.get_instance("s1").health == InstanceHealth.HEALTHY

    def test_mark_nonexistent_raises(self, lb: LoadBalancer):
        with pytest.raises(InstanceNotFoundError):
            lb.mark_healthy("nope")
        with pytest.raises(InstanceNotFoundError):
            lb.mark_unhealthy("nope")

    def test_unhealthy_instance_not_selected(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        lb.mark_unhealthy("s1")
        for _ in range(10):
            with lb.acquire() as lease:
                assert lease.instance_id == "s2"

    def test_unhealthy_instance_recovers(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        lb.mark_unhealthy("s1")
        lb.mark_healthy("s1")
        selected = set()
        for _ in range(20):
            with lb.acquire() as lease:
                selected.add(lease.instance_id)
        assert "s1" in selected
        assert "s2" in selected


class TestRoundRobinStrategy:
    def test_round_robin_distributes_evenly(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        lb.register_instance("s3")
        order = []
        for _ in range(6):
            with lb.acquire() as lease:
                order.append(lease.instance_id)
        assert order == ["s1", "s2", "s3", "s1", "s2", "s3"]

    def test_round_robin_wraps_around(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        for _ in range(100):
            with lb.acquire() as lease:
                pass
        with lb.acquire() as lease:
            assert lease.instance_id == "s1"

    def test_round_robin_single_instance(self, lb: LoadBalancer):
        lb.register_instance("solo")
        for _ in range(5):
            with lb.acquire() as lease:
                assert lease.instance_id == "solo"

    def test_round_robin_strategy_class(self):
        strategy = RoundRobinStrategy()
        from solocoder_py.load_balancer.models import Instance
        instances = [
            Instance(instance_id="a"),
            Instance(instance_id="b"),
        ]
        assert strategy.select(instances).instance_id == "a"
        assert strategy.select(instances).instance_id == "b"
        assert strategy.select(instances).instance_id == "a"
        strategy.reset()
        assert strategy.select(instances).instance_id == "a"

    def test_round_robin_empty_returns_none(self):
        strategy = RoundRobinStrategy()
        assert strategy.select([]) is None


class TestWeightedRandomStrategy:
    def test_weighted_random_proportional(self, clock: ManualClock):
        lb = make_lb(clock=clock)
        lb.register_instance("high", weight=5)
        lb.register_instance("low", weight=1)
        lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)
        counts = {"high": 0, "low": 0}
        for _ in range(6000):
            with lb.acquire() as lease:
                counts[lease.instance_id] += 1
        assert counts["high"] > counts["low"] * 3
        assert counts["high"] < counts["low"] * 8

    def test_weighted_random_zero_weight_excluded(self, lb: LoadBalancer):
        lb.register_instance("zero", weight=0)
        lb.register_instance("normal", weight=1)
        lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)
        for _ in range(100):
            with lb.acquire() as lease:
                assert lease.instance_id == "normal"

    def test_weighted_random_all_zero_weight_no_instance(self, lb: LoadBalancer):
        lb.register_instance("a", weight=0)
        lb.register_instance("b", weight=0)
        lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()

    def test_weighted_random_equal_weights(self, clock: ManualClock):
        lb = make_lb(clock=clock)
        lb.register_instance("a", weight=1)
        lb.register_instance("b", weight=1)
        lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)
        counts = {"a": 0, "b": 0}
        for _ in range(2000):
            with lb.acquire() as lease:
                counts[lease.instance_id] += 1
        assert 800 < counts["a"] < 1200

    def test_weighted_random_strategy_class_deterministic(self):
        rng = random.Random(42)
        strategy = WeightedRandomStrategy(rng=rng)
        from solocoder_py.load_balancer.models import Instance
        instances = [
            Instance(instance_id="a", weight=1),
            Instance(instance_id="b", weight=3),
        ]
        ids = [strategy.select(instances).instance_id for _ in range(100)]
        assert "a" in ids
        assert "b" in ids
        assert ids.count("b") > ids.count("a")

    def test_weighted_random_empty_returns_none(self):
        strategy = WeightedRandomStrategy()
        assert strategy.select([]) is None


class TestLeastConnectionsStrategy:
    def test_least_connections_picks_min(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        lb.set_strategy(SelectionStrategy.LEAST_CONNECTIONS)

        lease1 = lb.acquire()
        lease2 = lb.acquire()

        assert lease1.instance_id != lease2.instance_id

        busy_id = lease1.instance_id
        idle_id = lease2.instance_id
        lease2.release()

        for _ in range(10):
            l = lb.acquire()
            assert l.instance_id == idle_id
            l.release()

        lease1.release()

    def test_least_connections_tie_random(self, clock: ManualClock):
        lb = make_lb(clock=clock)
        lb.register_instance("s1")
        lb.register_instance("s2")
        lb.set_strategy(SelectionStrategy.LEAST_CONNECTIONS)
        counts = {"s1": 0, "s2": 0}
        for _ in range(1000):
            with lb.acquire() as lease:
                counts[lease.instance_id] += 1
        assert 400 < counts["s1"] < 600

    def test_least_connections_strategy_class(self):
        strategy = LeastConnectionsStrategy(rng=random.Random(42))
        from solocoder_py.load_balancer.models import Instance
        inst_a = Instance(instance_id="a")
        inst_b = Instance(instance_id="b")
        inst_b.active_connections = 5
        assert strategy.select([inst_a, inst_b]).instance_id == "a"

    def test_least_connections_empty_returns_none(self):
        strategy = LeastConnectionsStrategy()
        assert strategy.select([]) is None


class TestDynamicStrategySwitching:
    def test_set_strategy(self, lb: LoadBalancer):
        assert lb.current_strategy == SelectionStrategy.ROUND_ROBIN
        lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)
        assert lb.current_strategy == SelectionStrategy.WEIGHTED_RANDOM

    def test_per_request_strategy_override(self, lb: LoadBalancer):
        lb.register_instance("a", weight=100)
        lb.register_instance("b", weight=1)
        lb.set_strategy(SelectionStrategy.ROUND_ROBIN)

        with lb.acquire() as lease:
            assert lease.instance_id == "a"

        with lb.acquire(strategy=SelectionStrategy.WEIGHTED_RANDOM) as lease:
            pass

        with lb.acquire() as lease:
            assert lease.instance_id == "b"


class TestCircuitBreaker:
    def test_failure_triggers_circuit_open(self, clock: ManualClock):
        config = make_config(failure_threshold=2)
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("s1")
        lb.register_instance("s2")

        for i in range(2):
            lease = lb.acquire()
            while lease.instance_id != "s1":
                lease.release(success=True)
                lease = lb.acquire()
            lease.release(success=False)

        assert lb.get_instance("s1").circuit_state == CircuitState.OPEN
        assert lb.get_instance("s1").consecutive_failures == 2

    def test_open_instance_not_selected(self, clock: ManualClock):
        config = make_config(failure_threshold=1)
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("bad")
        lb.register_instance("good")

        lease = lb.acquire()
        while lease.instance_id != "bad":
            lease.release(success=True)
            lease = lb.acquire()
        lease.release(success=False)

        for _ in range(10):
            with lb.acquire() as l:
                assert l.instance_id == "good"

    def test_recovery_timeout_transitions_to_half_open(self, clock: ManualClock):
        config = make_config(
            failure_threshold=1,
            recovery_timeout_seconds=10.0,
        )
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("s1")

        lease = lb.acquire()
        lease.release(success=False)
        assert lb.get_instance("s1").circuit_state == CircuitState.OPEN

        clock.advance(9.9)
        assert lb.get_available_instances() == {}

        clock.advance(0.2)
        available = lb.get_available_instances()
        assert "s1" in available or lb.get_instance("s1").circuit_state == CircuitState.HALF_OPEN

    def test_half_open_probe_success_closes_circuit(self, clock: ManualClock):
        config = make_config(
            failure_threshold=1,
            recovery_timeout_seconds=5.0,
        )
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("s1")

        lease = lb.acquire()
        lease.release(success=False)
        assert lb.get_instance("s1").circuit_state == CircuitState.OPEN

        clock.advance(5.0)
        with lb.acquire() as probe:
            assert probe.instance_id == "s1"

        assert lb.get_instance("s1").circuit_state == CircuitState.CLOSED
        assert lb.get_instance("s1").consecutive_failures == 0

    def test_half_open_probe_failure_reopens_circuit(self, clock: ManualClock):
        config = make_config(
            failure_threshold=1,
            recovery_timeout_seconds=5.0,
        )
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("s1")

        lease = lb.acquire()
        lease.release(success=False)
        assert lb.get_instance("s1").circuit_state == CircuitState.OPEN

        clock.advance(5.0)
        probe = lb.acquire()
        assert probe.instance_id == "s1"
        probe.release(success=False)

        assert lb.get_instance("s1").circuit_state == CircuitState.OPEN

    def test_half_open_max_probes_respected(self, clock: ManualClock):
        config = make_config(
            failure_threshold=1,
            recovery_timeout_seconds=5.0,
            half_open_max_probes=2,
        )
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("probe-target")

        lease = lb.acquire()
        lease.release(success=False)

        clock.advance(5.0)

        probe1 = lb.acquire()
        probe2 = lb.acquire()
        assert probe1.instance_id == "probe-target"
        assert probe2.instance_id == "probe-target"
        assert lb.get_instance("probe-target").half_open_probe_count == 2

    def test_success_resets_consecutive_failures(self, lb: LoadBalancer):
        lb.register_instance("s1")
        for _ in range(2):
            lease = lb.acquire()
            while lease.instance_id != "s1":
                lease.release(success=True)
                lease = lb.acquire()
            lease.release(success=False)
        lb2 = lb
        lease = lb2.acquire()
        while lease.instance_id != "s1":
            lease.release(success=True)
            lease = lb2.acquire()
        lease.release(success=True)
        assert lb.get_instance("s1").consecutive_failures == 0


class TestConnectionLifecycle:
    def test_acquire_increments_connection_count(self, lb: LoadBalancer):
        lb.register_instance("s1")
        assert lb.get_instance("s1").active_connections == 0
        lease = lb.acquire()
        assert lb.get_instance("s1").active_connections == 1
        lease.release()
        assert lb.get_instance("s1").active_connections == 0

    def test_context_manager_success(self, lb: LoadBalancer):
        lb.register_instance("s1")
        with lb.acquire() as lease:
            assert lease.instance_id == "s1"
        assert lb.get_instance("s1").active_connections == 0
        assert lb.get_instance("s1").consecutive_failures == 0

    def test_context_manager_failure(self, lb: LoadBalancer):
        lb.register_instance("s1")
        with pytest.raises(RuntimeError):
            with lb.acquire() as lease:
                assert lease.instance_id == "s1"
                raise RuntimeError("fail")
        assert lb.get_instance("s1").active_connections == 0
        assert lb.get_instance("s1").consecutive_failures == 1

    def test_release_unallocated_connection_raises(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lease = lb.acquire()
        lease.release()
        with pytest.raises(ConnectionLeakError):
            lease.release()

    def test_release_wrong_instance_raises(self, clock: ManualClock):
        lb = make_lb(clock=clock)
        lb.register_instance("s1")
        lb.register_instance("s2")
        lease1 = lb.acquire()
        lease2 = lb.acquire()
        assert lease1.instance_id != lease2.instance_id
        with pytest.raises(InstanceNotFoundError):
            fake_lease = Lease(lb, "s99", 999)
            fake_lease.release()

    def test_lease_instance_id_property(self, lb: LoadBalancer):
        lb.register_instance("s1")
        with lb.acquire() as lease:
            assert lease.instance_id == "s1"
            assert isinstance(lease.request_id, int)

    def test_double_release_raises_connection_leak_error(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lease = lb.acquire()
        lease.release()
        assert lb.get_instance("s1").active_connections == 0
        with pytest.raises(ConnectionLeakError):
            lease.release()

    def test_explicit_release_inside_with_block_no_double_error(self, lb: LoadBalancer):
        lb.register_instance("s1")
        with lb.acquire() as lease:
            lease.release(success=True)
        assert lb.get_instance("s1").active_connections == 0

    def test_active_connections_reflected_in_least_connections(self, lb: LoadBalancer):
        lb.register_instance("a")
        lb.register_instance("b")
        lb.set_strategy(SelectionStrategy.LEAST_CONNECTIONS)

        hold_a = lb.acquire()
        if hold_a.instance_id == "b":
            hold_a.release()
            hold_a = lb.acquire()
            hold_b = lb.acquire()
            hold_b.release()
        else:
            pass

        assert lb.get_instance(hold_a.instance_id).active_connections >= 1

        for _ in range(5):
            l = lb.acquire()
            assert l.instance_id != hold_a.instance_id
            l.release()

        hold_a.release()


class TestNoAvailableInstance:
    def test_no_instances_registered_raises(self, lb: LoadBalancer):
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()

    def test_all_unhealthy_raises(self, lb: LoadBalancer):
        lb.register_instance("s1")
        lb.register_instance("s2")
        lb.mark_unhealthy("s1")
        lb.mark_unhealthy("s2")
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()

    def test_all_circuit_open_raises(self, clock: ManualClock):
        config = make_config(failure_threshold=1)
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("s1")
        lease = lb.acquire()
        lease.release(success=False)
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()

    def test_all_zero_weight_raises(self, lb: LoadBalancer):
        lb.register_instance("s1", weight=0)
        lb.register_instance("s2", weight=0)
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()


class TestSingleInstanceEdgeCase:
    def test_single_instance_all_traffic(self, lb: LoadBalancer):
        lb.register_instance("only")
        for _ in range(10):
            with lb.acquire() as lease:
                assert lease.instance_id == "only"

    def test_single_instance_failure_no_available(self, clock: ManualClock):
        config = make_config(failure_threshold=1)
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("only")
        lease = lb.acquire()
        lease.release(success=False)
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()

    def test_single_instance_weight_zero(self, lb: LoadBalancer):
        lb.register_instance("only", weight=0)
        with pytest.raises(NoAvailableInstanceError):
            lb.acquire()


class TestZeroWeightEdgeCase:
    def test_mixed_zero_and_positive_weight(self, lb: LoadBalancer):
        lb.register_instance("zero", weight=0)
        lb.register_instance("one", weight=1)
        lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)
        for _ in range(10):
            with lb.acquire() as lease:
                assert lease.instance_id == "one"

    def test_zero_weight_instance_ignored_in_round_robin(self, lb: LoadBalancer):
        lb.register_instance("zero", weight=0)
        lb.register_instance("active", weight=1)
        for _ in range(10):
            with lb.acquire() as lease:
                assert lease.instance_id == "active"


class TestInstanceAvailabilityChecks:
    def test_is_available_healthy_closed_positive_weight(self):
        from solocoder_py.load_balancer.models import Instance
        inst = Instance(instance_id="s1", weight=1)
        assert inst.is_available() is True

    def test_is_available_unhealthy(self):
        from solocoder_py.load_balancer.models import Instance
        inst = Instance(instance_id="s1", weight=1)
        inst.health = InstanceHealth.UNHEALTHY
        assert inst.is_available() is False

    def test_is_available_circuit_open(self):
        from solocoder_py.load_balancer.models import Instance
        inst = Instance(instance_id="s1", weight=1)
        inst.circuit_state = CircuitState.OPEN
        assert inst.is_available() is False

    def test_is_available_zero_weight(self):
        from solocoder_py.load_balancer.models import Instance
        inst = Instance(instance_id="s1", weight=0)
        assert inst.is_available() is False


class TestFullScenario:
    def test_normal_flow_round_robin_with_health_and_circuit(self, clock: ManualClock):
        config = make_config(
            failure_threshold=2,
            recovery_timeout_seconds=60.0,
        )
        lb = make_lb(config=config, clock=clock)
        lb.register_instance("s1", weight=1)
        lb.register_instance("s2", weight=1)
        lb.register_instance("s3", weight=1)

        results = []
        for i in range(3):
            with lb.acquire() as lease:
                results.append(lease.instance_id)
        assert results == ["s1", "s2", "s3"]

        for _ in range(2):
            lease = lb.acquire()
            while lease.instance_id != "s1":
                lease.release(success=True)
                lease = lb.acquire()
            lease.release(success=False)
        assert lb.get_instance("s1").circuit_state == CircuitState.OPEN

        after = []
        for _ in range(4):
            with lb.acquire() as lease:
                after.append(lease.instance_id)
        assert all(id in ("s2", "s3") for id in after)

        lb.mark_unhealthy("s2")
        with lb.acquire() as lease:
            assert lease.instance_id == "s3"

        lb.mark_healthy("s2")
        selected = set()
        for _ in range(10):
            with lb.acquire() as lease:
                selected.add(lease.instance_id)
        assert "s2" in selected
        assert "s3" in selected
        assert "s1" not in selected

        clock.advance(60.0)
        with lb.acquire() as lease:
            assert lease.instance_id == "s1"
        assert lb.get_instance("s1").circuit_state == CircuitState.CLOSED

    def test_least_connections_balances_load(self, lb: LoadBalancer):
        lb.register_instance("fast")
        lb.register_instance("slow")
        lb.set_strategy(SelectionStrategy.LEAST_CONNECTIONS)

        slow_lease = lb.acquire()
        if slow_lease.instance_id == "fast":
            slow_lease.release()
            slow_lease = lb.acquire()

        fast_count = 0
        slow_count = 0
        for _ in range(10):
            l = lb.acquire()
            if l.instance_id == "fast":
                fast_count += 1
            else:
                slow_count += 1
            l.release()

        assert fast_count >= 5
        slow_lease.release()
