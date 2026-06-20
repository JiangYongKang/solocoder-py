import pytest

from solocoder_py.device_shadow import (
    DeviceShadow,
    DeviceShadowError,
    FieldDiff,
    InvalidStateError,
    InvalidVersionError,
    NonSerializableValueError,
    ShadowDiff,
    VersionMismatchError,
)


class TestSetDesiredAndReported:
    def test_set_desired_basic(self, shadow):
        new_version = shadow.set_desired({"temperature": 25}, expected_version=1)
        assert new_version == 2
        assert shadow.desired == {"temperature": 25}
        assert shadow.version == 2

    def test_set_reported_basic(self, shadow):
        new_version = shadow.set_reported({"temperature": 22}, expected_version=1)
        assert new_version == 2
        assert shadow.reported == {"temperature": 22}
        assert shadow.version == 2

    def test_set_desired_then_reported(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        shadow.set_reported({"temperature": 22}, expected_version=2)
        assert shadow.desired == {"temperature": 25}
        assert shadow.reported == {"temperature": 22}
        assert shadow.version == 3

    def test_set_desired_returns_copy(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        desired = shadow.desired
        desired["temperature"] = 999
        assert shadow.desired["temperature"] == 25

    def test_set_reported_returns_copy(self, shadow):
        shadow.set_reported({"temperature": 22}, expected_version=1)
        reported = shadow.reported
        reported["temperature"] = 999
        assert shadow.reported["temperature"] == 22

    def test_overwrite_desired(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        shadow.set_desired({"temperature": 30, "humidity": 70}, expected_version=2)
        assert shadow.desired == {"temperature": 30, "humidity": 70}

    def test_overwrite_reported(self, shadow):
        shadow.set_reported({"temperature": 22}, expected_version=1)
        shadow.set_reported({"temperature": 20, "pressure": 1013}, expected_version=2)
        assert shadow.reported == {"temperature": 20, "pressure": 1013}


class TestMerge:
    def test_merge_same_field_reported_wins(self, shadow_with_both):
        merged = shadow_with_both.merge()
        assert merged["temperature"] == 22
        assert merged["humidity"] == 60

    def test_merge_desired_only_field_included(self, shadow):
        shadow.set_desired({"temperature": 25, "fan": "on"}, expected_version=1)
        shadow.set_reported({"temperature": 22}, expected_version=2)
        merged = shadow.merge()
        assert merged["temperature"] == 22
        assert merged["fan"] == "on"

    def test_merge_reported_only_field_included(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        shadow.set_reported({"temperature": 22, "pressure": 1013}, expected_version=2)
        merged = shadow.merge()
        assert merged["temperature"] == 22
        assert merged["pressure"] == 1013

    def test_merge_both_empty(self, shadow):
        merged = shadow.merge()
        assert merged == {}

    def test_merge_only_desired(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        merged = shadow.merge()
        assert merged == {"temperature": 25}

    def test_merge_only_reported(self, shadow):
        shadow.set_reported({"temperature": 22}, expected_version=1)
        merged = shadow.merge()
        assert merged == {"temperature": 22}

    def test_merge_deep_nested(self, shadow):
        shadow.set_desired(
            {"config": {"network": {"ip": "192.168.1.1", "port": 8080}}},
            expected_version=1,
        )
        shadow.set_reported(
            {"config": {"network": {"ip": "10.0.0.1", "subnet": "255.255.255.0"}}},
            expected_version=2,
        )
        merged = shadow.merge()
        assert merged["config"]["network"]["ip"] == "10.0.0.1"
        assert merged["config"]["network"]["port"] == 8080
        assert merged["config"]["network"]["subnet"] == "255.255.255.0"

    def test_merge_returns_independent_copy(self, shadow_with_both):
        merged = shadow_with_both.merge()
        merged["temperature"] = 999
        assert shadow_with_both.merge()["temperature"] == 22


class TestDiff:
    def test_diff_identical_states(self, shadow):
        shadow.set_desired({"temperature": 25, "humidity": 60}, expected_version=1)
        shadow.set_reported({"temperature": 25, "humidity": 60}, expected_version=2)
        diff = shadow.diff()
        assert not diff.has_differences
        assert diff.desired_only == []
        assert diff.reported_only == []
        assert diff.value_diff == []

    def test_diff_value_mismatch(self, shadow_with_both):
        diff = shadow_with_both.diff()
        assert diff.has_differences
        assert len(diff.value_diff) == 1
        assert diff.value_diff[0].path == "temperature"
        assert diff.value_diff[0].desired_value == 25
        assert diff.value_diff[0].reported_value == 22

    def test_diff_desired_only_field(self, shadow):
        shadow.set_desired({"temperature": 25, "fan": "on"}, expected_version=1)
        shadow.set_reported({"temperature": 22}, expected_version=2)
        diff = shadow.diff()
        assert len(diff.desired_only) == 1
        assert diff.desired_only[0].path == "fan"
        assert diff.desired_only[0].desired_value == "on"

    def test_diff_reported_only_field(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        shadow.set_reported({"temperature": 22, "pressure": 1013}, expected_version=2)
        diff = shadow.diff()
        assert len(diff.reported_only) == 1
        assert diff.reported_only[0].path == "pressure"
        assert diff.reported_only[0].reported_value == 1013

    def test_diff_both_empty(self, shadow):
        diff = shadow.diff()
        assert not diff.has_differences

    def test_diff_deep_nested(self, shadow):
        shadow.set_desired(
            {"config": {"network": {"ip": "192.168.1.1", "port": 8080}}},
            expected_version=1,
        )
        shadow.set_reported(
            {"config": {"network": {"ip": "10.0.0.1", "subnet": "255.255.255.0"}}},
            expected_version=2,
        )
        diff = shadow.diff()
        ip_diff = [d for d in diff.value_diff if d.path == "config.network.ip"]
        assert len(ip_diff) == 1
        assert ip_diff[0].desired_value == "192.168.1.1"
        assert ip_diff[0].reported_value == "10.0.0.1"

        port_diff = [d for d in diff.desired_only if d.path == "config.network.port"]
        assert len(port_diff) == 1
        assert port_diff[0].desired_value == 8080

        subnet_diff = [d for d in diff.reported_only if d.path == "config.network.subnet"]
        assert len(subnet_diff) == 1
        assert subnet_diff[0].reported_value == "255.255.255.0"

    def test_diff_only_desired_no_reported(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        diff = shadow.diff()
        assert len(diff.desired_only) == 1
        assert diff.desired_only[0].path == "temperature"
        assert diff.desired_only[0].desired_value == 25

    def test_diff_only_reported_no_desired(self, shadow):
        shadow.set_reported({"temperature": 22}, expected_version=1)
        diff = shadow.diff()
        assert len(diff.reported_only) == 1
        assert diff.reported_only[0].path == "temperature"
        assert diff.reported_only[0].reported_value == 22

    def test_diff_multiple_value_mismatches(self, shadow):
        shadow.set_desired({"a": 1, "b": 2, "c": 3}, expected_version=1)
        shadow.set_reported({"a": 10, "b": 20, "c": 3}, expected_version=2)
        diff = shadow.diff()
        assert len(diff.value_diff) == 2
        paths = {d.path for d in diff.value_diff}
        assert paths == {"a", "b"}


class TestVersionSync:
    def test_initial_version_is_1(self, shadow):
        assert shadow.version == 1

    def test_initial_version_0(self, shadow_v0):
        assert shadow_v0.version == 0

    def test_version_increments_on_desired_update(self, shadow):
        v = shadow.set_desired({"temperature": 25}, expected_version=1)
        assert v == 2
        assert shadow.version == 2

    def test_version_increments_on_reported_update(self, shadow):
        v = shadow.set_reported({"temperature": 22}, expected_version=1)
        assert v == 2
        assert shadow.version == 2

    def test_version_monotonically_increases(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        shadow.set_reported({"temperature": 22}, expected_version=2)
        shadow.set_desired({"temperature": 30}, expected_version=3)
        assert shadow.version == 4

    def test_version_mismatch_rejection(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        with pytest.raises(VersionMismatchError) as exc_info:
            shadow.set_desired({"temperature": 30}, expected_version=1)
        assert exc_info.value.expected == 1
        assert exc_info.value.actual == 2
        assert shadow.desired == {"temperature": 25}

    def test_same_version_consecutive_update_rejected(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        with pytest.raises(VersionMismatchError):
            shadow.set_desired({"temperature": 30}, expected_version=1)
        assert shadow.desired == {"temperature": 25}

    def test_version_mismatch_on_reported(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        with pytest.raises(VersionMismatchError):
            shadow.set_reported({"temperature": 22}, expected_version=1)

    def test_stale_version_rejected(self, shadow):
        shadow.set_desired({"temperature": 25}, expected_version=1)
        shadow.set_reported({"temperature": 22}, expected_version=2)
        with pytest.raises(VersionMismatchError):
            shadow.set_desired({"temperature": 30}, expected_version=1)
        with pytest.raises(VersionMismatchError):
            shadow.set_desired({"temperature": 30}, expected_version=2)
        shadow.set_desired({"temperature": 30}, expected_version=3)
        assert shadow.desired == {"temperature": 30}

    def test_negative_version_rejected(self, shadow):
        with pytest.raises(InvalidVersionError):
            shadow.set_desired({"temperature": 25}, expected_version=-1)

    def test_negative_version_on_reported(self, shadow):
        with pytest.raises(InvalidVersionError):
            shadow.set_reported({"temperature": 22}, expected_version=-1)

    def test_negative_initial_version_rejected(self):
        with pytest.raises(InvalidVersionError):
            DeviceShadow(device_id="bad", initial_version=-1)


class TestBoundaryConditions:
    def test_initial_version_1_default(self):
        s = DeviceShadow(device_id="x")
        assert s.version == 1

    def test_initial_version_0(self):
        s = DeviceShadow(device_id="x", initial_version=0)
        assert s.version == 0
        s.set_desired({"a": 1}, expected_version=0)
        assert s.version == 1

    def test_both_empty_merge(self, shadow):
        assert shadow.merge() == {}

    def test_both_empty_diff(self, shadow):
        diff = shadow.diff()
        assert not diff.has_differences

    def test_identical_states_diff_empty(self, shadow):
        shadow.set_desired({"a": 1, "b": "hello"}, expected_version=1)
        shadow.set_reported({"a": 1, "b": "hello"}, expected_version=2)
        diff = shadow.diff()
        assert not diff.has_differences

    def test_deep_nested_diff(self, shadow):
        shadow.set_desired(
            {"level1": {"level2": {"level3": {"value": "desired"}}}},
            expected_version=1,
        )
        shadow.set_reported(
            {"level1": {"level2": {"level3": {"value": "reported"}}}},
            expected_version=2,
        )
        diff = shadow.diff()
        assert len(diff.value_diff) == 1
        assert diff.value_diff[0].path == "level1.level2.level3.value"
        assert diff.value_diff[0].desired_value == "desired"
        assert diff.value_diff[0].reported_value == "reported"

    def test_merge_only_desired(self, shadow):
        shadow.set_desired({"a": 1, "b": 2}, expected_version=1)
        merged = shadow.merge()
        assert merged == {"a": 1, "b": 2}

    def test_merge_only_reported(self, shadow):
        shadow.set_reported({"x": 10, "y": 20}, expected_version=1)
        merged = shadow.merge()
        assert merged == {"x": 10, "y": 20}

    def test_deep_merge_nested_dicts(self, shadow):
        shadow.set_desired(
            {"a": {"b": {"c": 1, "d": 2}}},
            expected_version=1,
        )
        shadow.set_reported(
            {"a": {"b": {"c": 99, "e": 3}}},
            expected_version=2,
        )
        merged = shadow.merge()
        assert merged == {"a": {"b": {"c": 99, "d": 2, "e": 3}}}

    def test_diff_type_mismatch_dict_vs_scalar(self, shadow):
        shadow.set_desired({"a": {"b": 1}}, expected_version=1)
        shadow.set_reported({"a": "scalar"}, expected_version=2)
        diff = shadow.diff()
        assert any(d.path == "a" for d in diff.value_diff)

    def test_diff_type_mismatch_scalar_vs_dict(self, shadow):
        shadow.set_desired({"a": "scalar"}, expected_version=1)
        shadow.set_reported({"a": {"b": 1}}, expected_version=2)
        diff = shadow.diff()
        assert any(d.path == "a" for d in diff.value_diff)

    def test_shadow_device_id(self, shadow):
        assert shadow.device_id == "test-device-001"

    def test_to_dict(self, shadow_with_both):
        result = shadow_with_both.to_dict()
        assert result["device_id"] == "test-device-001"
        assert result["desired"] == {"temperature": 25, "humidity": 60}
        assert result["reported"] == {"temperature": 22, "humidity": 60}
        assert result["version"] == 3

    def test_repr(self, shadow):
        r = repr(shadow)
        assert "test-device-001" in r
        assert "version=1" in r


class TestExceptionBranches:
    def test_version_mismatch_on_set_desired(self, shadow):
        with pytest.raises(VersionMismatchError) as exc_info:
            shadow.set_desired({"a": 1}, expected_version=999)
        assert exc_info.value.expected == 999
        assert exc_info.value.actual == 1

    def test_version_mismatch_on_set_reported(self, shadow):
        with pytest.raises(VersionMismatchError) as exc_info:
            shadow.set_reported({"a": 1}, expected_version=999)
        assert exc_info.value.expected == 999
        assert exc_info.value.actual == 1

    def test_negative_version_on_set_desired(self, shadow):
        with pytest.raises(InvalidVersionError):
            shadow.set_desired({"a": 1}, expected_version=-5)

    def test_negative_version_on_set_reported(self, shadow):
        with pytest.raises(InvalidVersionError):
            shadow.set_reported({"a": 1}, expected_version=-3)

    def test_non_serializable_object_in_state(self, shadow):
        with pytest.raises(NonSerializableValueError):
            shadow.set_desired({"a": {1, 2, 3}}, expected_version=1)

    def test_non_serializable_nested_object(self, shadow):
        with pytest.raises(NonSerializableValueError):
            shadow.set_desired({"a": {"b": object()}}, expected_version=1)

    def test_non_serializable_in_list(self, shadow):
        with pytest.raises(NonSerializableValueError):
            shadow.set_desired({"a": [1, 2, object()]}, expected_version=1)

    def test_none_state_rejected(self, shadow):
        with pytest.raises(InvalidStateError):
            shadow.set_desired(None, expected_version=1)

    def test_none_reported_rejected(self, shadow):
        with pytest.raises(InvalidStateError):
            shadow.set_reported(None, expected_version=1)

    def test_non_dict_state_rejected(self, shadow):
        with pytest.raises(InvalidStateError):
            shadow.set_desired("not a dict", expected_version=1)

    def test_non_dict_reported_rejected(self, shadow):
        with pytest.raises(InvalidStateError):
            shadow.set_reported([1, 2, 3], expected_version=1)

    def test_list_state_rejected(self, shadow):
        with pytest.raises(InvalidStateError):
            shadow.set_reported([1, 2], expected_version=1)

    def test_integer_state_rejected(self, shadow):
        with pytest.raises(InvalidStateError):
            shadow.set_desired(42, expected_version=1)

    def test_empty_dict_state_accepted(self, shadow):
        new_version = shadow.set_desired({}, expected_version=1)
        assert new_version == 2
        assert shadow.desired == {}

    def test_exception_hierarchy(self):
        assert issubclass(VersionMismatchError, DeviceShadowError)
        assert issubclass(InvalidVersionError, DeviceShadowError)
        assert issubclass(NonSerializableValueError, DeviceShadowError)
        assert issubclass(InvalidStateError, DeviceShadowError)

    def test_version_mismatch_preserves_state(self, shadow):
        shadow.set_desired({"a": 1}, expected_version=1)
        with pytest.raises(VersionMismatchError):
            shadow.set_desired({"a": 999}, expected_version=1)
        assert shadow.desired == {"a": 1}

    def test_state_with_various_json_types(self, shadow):
        state = {
            "string": "hello",
            "int": 42,
            "float": 3.14,
            "bool_true": True,
            "bool_false": False,
            "null": None,
            "list": [1, "two", None],
            "nested": {"deep": {"value": 99}},
        }
        new_version = shadow.set_desired(state, expected_version=1)
        assert new_version == 2
        assert shadow.desired == state
