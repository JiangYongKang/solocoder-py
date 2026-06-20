from __future__ import annotations

import pytest

from solocoder_py.telemetry.exceptions import CircularMappingError, TargetConflictError
from solocoder_py.telemetry.models import SchemaConfig
from solocoder_py.telemetry.schema import SchemaNormalizer


class TestBasicMapping:
    def test_simple_field_rename(self):
        config = SchemaConfig(field_mapping={"temp": "temperature", "humid": "humidity"})
        normalizer = SchemaNormalizer(config)

        result = normalizer.normalize({"temp": 25.5, "humid": 60})
        assert result == {"temperature": 25.5, "humidity": 60}

    def test_unmapped_fields_preserved_by_default(self):
        config = SchemaConfig(
            field_mapping={"temp": "temperature"},
            drop_unmapped=False,
        )
        normalizer = SchemaNormalizer(config)

        result = normalizer.normalize({"temp": 25.5, "extra": "value"})
        assert result == {"temperature": 25.5, "extra": "value"}

    def test_unmapped_fields_dropped_when_configured(self):
        config = SchemaConfig(
            field_mapping={"temp": "temperature"},
            drop_unmapped=True,
        )
        normalizer = SchemaNormalizer(config)

        result = normalizer.normalize({"temp": 25.5, "extra": "value"})
        assert result == {"temperature": 25.5}

    def test_identity_mapping(self):
        config = SchemaConfig(field_mapping={}, drop_unmapped=False)
        normalizer = SchemaNormalizer(config)

        data = {"temp": 25.5, "humid": 60}
        result = normalizer.normalize(data)
        assert result == {"temp": 25.5, "humid": 60}


class TestEmptyMapping:
    def test_empty_mapping_passthrough(self):
        config = SchemaConfig(field_mapping={}, drop_unmapped=False)
        normalizer = SchemaNormalizer(config)

        data = {"a": 1, "b": 2}
        result = normalizer.normalize(data)
        assert result == data

    def test_empty_mapping_drop_all(self):
        config = SchemaConfig(field_mapping={}, drop_unmapped=True)
        normalizer = SchemaNormalizer(config)

        data = {"a": 1, "b": 2}
        result = normalizer.normalize(data)
        assert result == {}


class TestNestedFieldMapping:
    def test_nested_field_rename(self):
        config = SchemaConfig(
            field_mapping={
                "device.temp": "device.temperature",
            }
        )
        normalizer = SchemaNormalizer(config)

        data = {"device": {"temp": 22.1}}
        result = normalizer.normalize(data)
        assert result == {"device": {"temperature": 22.1}}

    def test_deeply_nested_field_rename(self):
        config = SchemaConfig(
            field_mapping={
                "device.loc.lat": "device.location.latitude",
                "device.loc.lon": "device.location.longitude",
            }
        )
        normalizer = SchemaNormalizer(config)

        data = {"device": {"loc": {"lat": 34.05, "lon": -118.25}}}
        result = normalizer.normalize(data)
        assert result == {"device": {"location": {"latitude": 34.05, "longitude": -118.25}}}

    def test_mixed_flat_and_nested_mapping(self):
        config = SchemaConfig(
            field_mapping={
                "temp": "temperature",
                "device.temp": "device.temperature",
            }
        )
        normalizer = SchemaNormalizer(config)

        data = {
            "temp": 25.5,
            "device": {"temp": 22.1},
        }
        result = normalizer.normalize(data)
        assert result == {
            "temperature": 25.5,
            "device": {"temperature": 22.1},
        }

    def test_nested_with_unmapped_sibling(self):
        config = SchemaConfig(
            field_mapping={
                "device.temp": "device.temperature",
            },
            drop_unmapped=False,
        )
        normalizer = SchemaNormalizer(config)

        data = {"device": {"temp": 22.1, "id": "sensor-1"}}
        result = normalizer.normalize(data)
        assert result == {"device": {"temperature": 22.1, "id": "sensor-1"}}

    def test_nested_with_unmapped_sibling_dropped(self):
        config = SchemaConfig(
            field_mapping={
                "device.temp": "device.temperature",
            },
            drop_unmapped=True,
        )
        normalizer = SchemaNormalizer(config)

        data = {"device": {"temp": 22.1, "id": "sensor-1"}}
        result = normalizer.normalize(data)
        assert result == {"device": {"temperature": 22.1}}


class TestCircularReferenceDetection:
    def test_direct_cycle_raises(self):
        config = SchemaConfig(field_mapping={"a": "b", "b": "a"})
        with pytest.raises(CircularMappingError):
            SchemaNormalizer(config)

    def test_indirect_cycle_raises(self):
        config = SchemaConfig(field_mapping={"a": "b", "b": "c", "c": "a"})
        with pytest.raises(CircularMappingError):
            SchemaNormalizer(config)

    def test_no_cycle_allowed(self):
        config = SchemaConfig(field_mapping={"a": "b", "b": "c"})
        normalizer = SchemaNormalizer(config)
        assert normalizer is not None

    def test_self_mapping_raises(self):
        config = SchemaConfig(field_mapping={"a": "a"})
        with pytest.raises(CircularMappingError):
            SchemaNormalizer(config)


class TestTargetFieldConflict:
    def test_multiple_sources_same_target_raises(self):
        config = SchemaConfig(field_mapping={"temp": "temperature", "tmp": "temperature"})
        with pytest.raises(TargetConflictError):
            SchemaNormalizer(config)

    def test_distinct_targets_ok(self):
        config = SchemaConfig(field_mapping={"temp": "temperature", "humid": "humidity"})
        normalizer = SchemaNormalizer(config)
        assert normalizer is not None

    def test_nested_target_conflict(self):
        config = SchemaConfig(
            field_mapping={
                "a.x": "a.y",
                "a.z": "a.y",
            }
        )
        with pytest.raises(TargetConflictError):
            SchemaNormalizer(config)


class TestNormalizeBatch:
    def test_batch_normalization(self):
        config = SchemaConfig(field_mapping={"temp": "temperature"})
        normalizer = SchemaNormalizer(config)

        batch = [
            {"temp": 25.0, "id": 1},
            {"temp": 26.0, "id": 2},
        ]
        result = normalizer.normalize_batch(batch)
        assert len(result) == 2
        assert result[0] == {"temperature": 25.0, "id": 1}
        assert result[1] == {"temperature": 26.0, "id": 2}


class TestDeepCopy:
    def test_normalize_does_not_mutate_input(self):
        config = SchemaConfig(field_mapping={"temp": "temperature"}, drop_unmapped=False)
        normalizer = SchemaNormalizer(config)

        data = {"temp": 25.5, "nested": {"val": 1}}
        original = {"temp": 25.5, "nested": {"val": 1}}
        normalizer.normalize(data)
        assert data == original

    def test_normalize_nested_dict_not_mutated(self):
        config = SchemaConfig(field_mapping={}, drop_unmapped=False)
        normalizer = SchemaNormalizer(config)

        nested = {"a": 1}
        data = {"nested": nested}
        result = normalizer.normalize(data)
        result["nested"]["a"] = 999
        assert nested["a"] == 1
