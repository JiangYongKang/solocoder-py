from __future__ import annotations

import pytest

from solocoder_py.config_merge import (
    ArrayMergeStrategy,
    CircularReferenceError,
    ConfigLayer,
    ConfigLayerType,
    ConfigMergeManager,
    ConfigTypeConflictError,
    InvalidConfigLayerError,
    UnknownArrayMergeStrategyError,
)
from .conftest import make_manager


class TestConfigLayerTypeEnum:
    def test_layer_type_values(self):
        assert ConfigLayerType.DEFAULT == "default"
        assert ConfigLayerType.ENVIRONMENT == "environment"
        assert ConfigLayerType.OVERRIDE == "override"


class TestArrayMergeStrategyEnum:
    def test_strategy_values(self):
        assert ArrayMergeStrategy.REPLACE == "replace"
        assert ArrayMergeStrategy.APPEND == "append"


class TestConfigLayerModel:
    def test_layer_creation(self):
        layer = ConfigLayer(
            layer_type=ConfigLayerType.DEFAULT,
            data={"key": "value"},
        )
        assert layer.layer_type == ConfigLayerType.DEFAULT
        assert layer.data == {"key": "value"}

    def test_layer_creation_empty_data(self):
        layer = ConfigLayer(layer_type=ConfigLayerType.DEFAULT)
        assert layer.data == {}

    def test_layer_invalid_data_type(self):
        with pytest.raises(TypeError, match="data must be a dict"):
            ConfigLayer(layer_type=ConfigLayerType.DEFAULT, data="not a dict")

    def test_layer_get(self):
        layer = ConfigLayer(
            layer_type=ConfigLayerType.DEFAULT,
            data={"a": 1, "b": 2},
        )
        assert layer.get("a") == 1
        assert layer.get("c") is None
        assert layer.get("c", "default") == "default"

    def test_layer_set(self):
        layer = ConfigLayer(layer_type=ConfigLayerType.DEFAULT, data={"a": 1})
        layer.set("b", 2)
        assert layer.data == {"a": 1, "b": 2}
        layer.set("a", 10)
        assert layer.data == {"a": 10, "b": 2}

    def test_layer_has_key(self):
        layer = ConfigLayer(
            layer_type=ConfigLayerType.DEFAULT,
            data={"a": 1, "b": 2},
        )
        assert layer.has_key("a") is True
        assert layer.has_key("c") is False

    def test_layer_keys_sorted(self):
        layer = ConfigLayer(
            layer_type=ConfigLayerType.DEFAULT,
            data={"c": 3, "a": 1, "b": 2},
        )
        assert layer.keys() == ("a", "b", "c")

    def test_layer_clear(self):
        layer = ConfigLayer(
            layer_type=ConfigLayerType.DEFAULT,
            data={"a": 1, "b": 2},
        )
        layer.clear()
        assert layer.data == {}

    def test_layer_update(self):
        layer = ConfigLayer(
            layer_type=ConfigLayerType.DEFAULT,
            data={"a": 1, "b": 2},
        )
        layer.update({"b": 20, "c": 3})
        assert layer.data == {"a": 1, "b": 20, "c": 3}

    def test_layer_update_invalid_type(self):
        layer = ConfigLayer(layer_type=ConfigLayerType.DEFAULT)
        with pytest.raises(TypeError, match="data must be a dict"):
            layer.update("not a dict")


class TestSetAndGetLayerData:
    def test_set_default_layer(self):
        manager = make_manager()
        data = {"key": "default_value"}
        manager.set_layer_data(ConfigLayerType.DEFAULT, data)
        result = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert result == data

    def test_set_environment_layer(self):
        manager = make_manager()
        data = {"key": "env_value"}
        manager.set_layer_data(ConfigLayerType.ENVIRONMENT, data)
        result = manager.get_layer_data(ConfigLayerType.ENVIRONMENT)
        assert result == data

    def test_set_override_layer(self):
        manager = make_manager()
        data = {"key": "override_value"}
        manager.set_layer_data(ConfigLayerType.OVERRIDE, data)
        result = manager.get_layer_data(ConfigLayerType.OVERRIDE)
        assert result == data

    def test_set_layer_data_is_deep_copied(self):
        manager = make_manager()
        original = {"nested": {"inner": [1, 2]}}
        manager.set_layer_data(ConfigLayerType.DEFAULT, original)
        original["nested"]["inner"].append(999)
        original["extra"] = "injected"

        stored = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert stored["nested"]["inner"] == [1, 2]
        assert "extra" not in stored

    def test_get_layer_data_returns_deep_copy(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"nested": {"inner": [1, 2]}}
        )

        value = manager.get_layer_data(ConfigLayerType.DEFAULT)
        value["nested"]["inner"].append(999)
        value["extra"] = "injected"

        stored = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert stored["nested"]["inner"] == [1, 2]
        assert "extra" not in stored

    def test_set_layer_data_invalid_type(self):
        manager = make_manager()
        with pytest.raises(TypeError, match="data must be a dict"):
            manager.set_layer_data(ConfigLayerType.DEFAULT, "not a dict")

    def test_update_layer(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1, "b": 2}
        )
        manager.update_layer(ConfigLayerType.DEFAULT, {"b": 20, "c": 3})
        result = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert result == {"a": 1, "b": 20, "c": 3}

    def test_clear_layer(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1, "b": 2}
        )
        manager.clear_layer(ConfigLayerType.DEFAULT)
        result = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert result == {}

    def test_clear_all_layers(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})
        manager.set_layer_data(ConfigLayerType.ENVIRONMENT, {"b": 2})
        manager.set_layer_data(ConfigLayerType.OVERRIDE, {"c": 3})
        manager.clear_all()
        assert manager.get_layer_data(ConfigLayerType.DEFAULT) == {}
        assert manager.get_layer_data(ConfigLayerType.ENVIRONMENT) == {}
        assert manager.get_layer_data(ConfigLayerType.OVERRIDE) == {}


class TestDefaultArrayStrategy:
    def test_default_strategy_is_replace(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"items": [1, 2, 3]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"items": [4, 5]}
        )
        merged = manager.merge()
        assert merged["items"] == [4, 5]

    def test_set_default_array_strategy(self):
        manager = make_manager()
        manager.set_default_array_strategy(ArrayMergeStrategy.APPEND)
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"items": [1, 2, 3]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"items": [4, 5]}
        )
        merged = manager.merge()
        assert merged["items"] == [1, 2, 3, 4, 5]

    def test_set_invalid_default_strategy(self):
        manager = make_manager()
        with pytest.raises(UnknownArrayMergeStrategyError):
            manager.set_default_array_strategy("invalid")


class TestTwoLayerMerge:
    def test_default_only(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1, "b": {"c": 2}}
        )
        merged = manager.merge()
        assert merged == {"a": 1, "b": {"c": 2}}

    def test_default_and_environment(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1, "b": 2}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"b": 20, "c": 3}
        )
        merged = manager.merge()
        assert merged == {"a": 1, "b": 20, "c": 3}

    def test_environment_overrides_default(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"app": {"debug": False, "name": "App"}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"app": {"debug": True}}
        )
        merged = manager.merge()
        assert merged["app"]["debug"] is True
        assert merged["app"]["name"] == "App"

    def test_default_env_and_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1, "b": 2, "c": 3}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"b": 20, "c": 30}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"c": 300}
        )
        merged = manager.merge()
        assert merged == {"a": 1, "b": 20, "c": 300}


class TestDeepNestedMerge:
    def test_deep_nested_merge(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT,
            {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {
                        "username": "admin",
                        "password": "default",
                    },
                    "options": {
                        "ssl": False,
                        "timeout": 30,
                    },
                },
            },
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT,
            {
                "database": {
                    "credentials": {
                        "password": "env_secret",
                    },
                    "options": {
                        "ssl": True,
                    },
                },
            },
        )
        merged = manager.merge()
        assert merged["database"]["host"] == "localhost"
        assert merged["database"]["port"] == 5432
        assert merged["database"]["credentials"]["username"] == "admin"
        assert merged["database"]["credentials"]["password"] == "env_secret"
        assert merged["database"]["options"]["ssl"] is True
        assert merged["database"]["options"]["timeout"] == 30

    def test_triple_layer_nested_merge(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT,
            {
                "a": {"b": {"c": {"d": "default"}}},
            },
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT,
            {
                "a": {"b": {"c": {"d": "env", "e": "env"}}},
            },
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE,
            {
                "a": {"b": {"c": {"d": "override"}}},
            },
        )
        merged = manager.merge()
        assert merged["a"]["b"]["c"]["d"] == "override"
        assert merged["a"]["b"]["c"]["e"] == "env"


class TestArrayMergeStrategies:
    def test_array_replace_default_env(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"features": ["auth", "logging"]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"features": ["metrics"]}
        )
        merged = manager.merge(array_strategy=ArrayMergeStrategy.REPLACE)
        assert merged["features"] == ["metrics"]

    def test_array_replace_env_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"items": [1, 2, 3]}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"items": [4, 5]}
        )
        merged = manager.merge(array_strategy=ArrayMergeStrategy.REPLACE)
        assert merged["items"] == [4, 5]

    def test_array_append_default_env(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"features": ["auth", "logging"]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"features": ["metrics"]}
        )
        merged = manager.merge(array_strategy=ArrayMergeStrategy.APPEND)
        assert merged["features"] == ["auth", "logging", "metrics"]

    def test_array_append_three_layers(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"nums": [1]})
        manager.set_layer_data(ConfigLayerType.ENVIRONMENT, {"nums": [2, 3]})
        manager.set_layer_data(ConfigLayerType.OVERRIDE, {"nums": [4]})
        merged = manager.merge(array_strategy=ArrayMergeStrategy.APPEND)
        assert merged["nums"] == [1, 2, 3, 4]

    def test_array_append_with_nested_arrays(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT,
            {"data": [[1, 2], [3, 4]]},
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT,
            {"data": [[5, 6]]},
        )
        merged = manager.merge(array_strategy=ArrayMergeStrategy.APPEND)
        assert merged["data"] == [[1, 2], [3, 4], [5, 6]]

    def test_array_deep_copy_in_replace(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"items": [{"a": 1}]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"items": [{"b": 2}]}
        )
        merged = manager.merge(array_strategy=ArrayMergeStrategy.REPLACE)
        merged["items"][0]["b"] = 999

        env_data = manager.get_layer_data(ConfigLayerType.ENVIRONMENT)
        assert env_data["items"][0]["b"] == 2

    def test_array_deep_copy_in_append(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"items": [{"a": 1}]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"items": [{"b": 2}]}
        )
        merged = manager.merge(array_strategy=ArrayMergeStrategy.APPEND)
        merged["items"][0]["a"] = 999
        merged["items"][1]["b"] = 888

        default_data = manager.get_layer_data(ConfigLayerType.DEFAULT)
        env_data = manager.get_layer_data(ConfigLayerType.ENVIRONMENT)
        assert default_data["items"][0]["a"] == 1
        assert env_data["items"][0]["b"] == 2

    def test_unknown_array_strategy_in_merge(self):
        manager = make_manager()
        with pytest.raises(UnknownArrayMergeStrategyError):
            manager.merge(array_strategy="invalid")


class TestBoundaryConditions:
    def test_empty_all_layers(self):
        manager = make_manager()
        merged = manager.merge()
        assert merged == {}

    def test_empty_default_layer(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"a": 1}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"b": 2}
        )
        merged = manager.merge()
        assert merged == {"a": 1, "b": 2}

    def test_empty_environment_layer(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"b": 2}
        )
        merged = manager.merge()
        assert merged == {"a": 1, "b": 2}

    def test_empty_override_layer(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"b": 2}
        )
        merged = manager.merge()
        assert merged == {"a": 1, "b": 2}

    def test_all_default_no_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT,
            {
                "app": {"name": "MyApp", "debug": False},
                "server": {"host": "localhost", "port": 8080},
                "features": ["auth"],
            },
        )
        merged = manager.merge()
        assert merged["app"]["name"] == "MyApp"
        assert merged["app"]["debug"] is False
        assert merged["server"]["host"] == "localhost"
        assert merged["server"]["port"] == 8080
        assert merged["features"] == ["auth"]

    def test_three_layers_same_key(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"value": "default"})
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"value": "environment"}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"value": "override"}
        )
        merged = manager.merge()
        assert merged["value"] == "override"

    def test_three_layers_same_nested_key(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"app": {"name": "DefaultApp"}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"app": {"name": "EnvApp"}}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"app": {"name": "OverrideApp"}}
        )
        merged = manager.merge()
        assert merged["app"]["name"] == "OverrideApp"

    def test_none_values_handled(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": None, "b": 1}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"b": None, "c": 3}
        )
        merged = manager.merge()
        assert merged["a"] is None
        assert merged["b"] is None
        assert merged["c"] == 3

    def test_mixed_types_primitives(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT,
            {
                "str_key": "string",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
                "none_key": None,
            },
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT,
            {
                "int_key": 100,
                "bool_key": False,
            },
        )
        merged = manager.merge()
        assert merged["str_key"] == "string"
        assert merged["int_key"] == 100
        assert merged["float_key"] == 3.14
        assert merged["bool_key"] is False
        assert merged["none_key"] is None

    def test_high_layer_adds_new_nested_fields(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"app": {"name": "App"}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"app": {"version": "1.0"}}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"app": {"debug": True}}
        )
        merged = manager.merge()
        assert merged["app"]["name"] == "App"
        assert merged["app"]["version"] == "1.0"
        assert merged["app"]["debug"] is True


class TestTempOverride:
    def test_temp_override_simple_key(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})
        manager.set_layer_data(ConfigLayerType.OVERRIDE, {"a": 100})

        merged_normal = manager.merge()
        assert merged_normal["a"] == 100

        merged_with_override = manager.merge(temp_override={"a": 999})
        assert merged_with_override["a"] == 999

        merged_after = manager.merge()
        assert merged_after["a"] == 100

    def test_temp_override_nested_key(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"app": {"debug": False}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"app": {"debug": True}}
        )

        merged = manager.merge(
            temp_override={"app": {"debug": False, "extra": "temp"}}
        )
        assert merged["app"]["debug"] is False
        assert merged["app"]["extra"] == "temp"

    def test_temp_override_does_not_modify_layers(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": 1, "nested": {"b": 2}}
        )

        manager.merge(
            temp_override={
                "a": 999,
                "nested": {"b": 888, "c": 777},
            }
        )

        default_data = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert default_data["a"] == 1
        assert default_data["nested"]["b"] == 2
        assert "c" not in default_data["nested"]

    def test_temp_override_with_append_array_strategy(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"items": [1, 2]}
        )

        merged = manager.merge(
            array_strategy=ArrayMergeStrategy.APPEND,
            temp_override={"items": [3]},
        )
        assert merged["items"] == [1, 2, 3]

    def test_temp_override_invalid_type(self):
        manager = make_manager()
        with pytest.raises(TypeError, match="temp_override must be a dict"):
            manager.merge(temp_override="not a dict")

    def test_temp_override_empty_dict(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})
        merged = manager.merge(temp_override={})
        assert merged == {"a": 1}


class TestGetMethod:
    def test_get_top_level_key(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1, "b": 2})
        assert manager.get("a") == 1
        assert manager.get("b") == 2

    def test_get_missing_key_returns_default(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})
        assert manager.get("missing") is None
        assert manager.get("missing", "default_value") == "default_value"

    def test_get_with_temp_override(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})
        assert manager.get("a", temp_override={"a": 999}) == 999

    def test_get_with_array_strategy(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"items": [1]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"items": [2]}
        )
        assert manager.get(
            "items", array_strategy=ArrayMergeStrategy.REPLACE
        ) == [2]
        assert manager.get(
            "items", array_strategy=ArrayMergeStrategy.APPEND
        ) == [1, 2]

    def test_get_returns_deep_copy(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"nested": {"inner": [1, 2]}}
        )
        value = manager.get("nested")
        value["inner"].append(999)
        value["extra"] = "injected"

        stored = manager.get("nested")
        assert stored == {"inner": [1, 2]}


class TestGetNestedMethod:
    def test_get_nested_simple(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": {"b": {"c": "value"}}}
        )
        assert manager.get_nested(["a", "b", "c"]) == "value"

    def test_get_nested_missing_key(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": {"b": 1}})
        assert manager.get_nested(["a", "c"]) is None
        assert manager.get_nested(["x", "y"], "default") == "default"

    def test_get_nested_with_temp_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": {"b": 1}}
        )
        result = manager.get_nested(
            ["a", "b"], temp_override={"a": {"b": 999}}
        )
        assert result == 999

    def test_get_nested_empty_keys(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})
        result = manager.get_nested([])
        assert result == {"a": 1}


class TestConfigTypeConflictErrors:
    def test_dict_vs_list_conflict(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"value": {"key": "dict"}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"value": [1, 2, 3]}
        )
        with pytest.raises(ConfigTypeConflictError, match="Type conflict"):
            manager.merge()

    def test_list_vs_dict_conflict(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"value": [1, 2, 3]}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"value": {"key": "dict"}}
        )
        with pytest.raises(ConfigTypeConflictError, match="Type conflict"):
            manager.merge()

    def test_nested_dict_vs_list_conflict(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": {"b": {"c": "dict"}}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"a": {"b": [1, 2]}}
        )
        with pytest.raises(
            ConfigTypeConflictError, match="Type conflict at 'a.b'"
        ):
            manager.merge()

    def test_three_layer_type_conflict_env_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": {"b": {"inner": 1}}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"a": {"b": {"inner": 2}}}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"a": {"b": [1, 2]}}
        )
        with pytest.raises(ConfigTypeConflictError):
            manager.merge()

    def test_primitive_to_list_is_valid_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": {"b": 1}}
        )
        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT, {"a": {"b": 2}}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"a": {"b": [1, 2]}}
        )
        merged = manager.merge()
        assert merged["a"]["b"] == [1, 2]

    def test_list_to_primitive_is_valid_override(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"a": {"b": [1, 2]}}
        )
        manager.set_layer_data(
            ConfigLayerType.OVERRIDE, {"a": {"b": "primitive"}}
        )
        merged = manager.merge()
        assert merged["a"]["b"] == "primitive"

    def test_temp_override_type_conflict(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"value": {"key": "dict"}}
        )
        with pytest.raises(ConfigTypeConflictError):
            manager.merge(temp_override={"value": [1, 2]})


class TestCircularReferenceErrors:
    def test_simple_circular_dict(self):
        manager = make_manager()
        circular = {"a": 1}
        circular["self"] = circular

        with pytest.raises(
            CircularReferenceError, match="Circular reference detected"
        ):
            manager.set_layer_data(ConfigLayerType.DEFAULT, circular)
            manager.merge()

    def test_circular_dict_at_merge(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})

        circular = {"b": 2}
        circular["self"] = circular
        with pytest.raises(CircularReferenceError):
            manager.set_layer_data(ConfigLayerType.ENVIRONMENT, circular)
            manager.merge()

    def test_circular_in_list(self):
        manager = make_manager()
        inner = [1, 2]
        circular = {"items": inner}
        inner.append(circular)

        with pytest.raises(CircularReferenceError):
            manager.set_layer_data(ConfigLayerType.DEFAULT, circular)
            manager.merge()

    def test_circular_in_temp_override(self):
        manager = make_manager()
        manager.set_layer_data(ConfigLayerType.DEFAULT, {"a": 1})

        circular = {"b": 2}
        circular["self"] = circular

        with pytest.raises(CircularReferenceError):
            manager.merge(temp_override=circular)

    def test_nested_circular_reference(self):
        manager = make_manager()
        level3 = {"value": "deep"}
        level2 = {"next": level3}
        level1 = {"next": level2}
        level3["back"] = level1

        with pytest.raises(CircularReferenceError):
            manager.set_layer_data(ConfigLayerType.DEFAULT, level1)
            manager.merge()


class TestInvalidConfigLayerError:
    def test_invalid_layer_type_in_get_layer(self):
        manager = make_manager()
        with pytest.raises(InvalidConfigLayerError):
            manager._get_layer("invalid_layer")

    def test_invalid_layer_type_set_layer_data(self):
        manager = make_manager()
        with pytest.raises(InvalidConfigLayerError):
            manager.set_layer_data("invalid", {})

    def test_invalid_layer_type_get_layer_data(self):
        manager = make_manager()
        with pytest.raises(InvalidConfigLayerError):
            manager.get_layer_data("invalid")


class TestMergeResultDeepCopyIsolation:
    def test_modify_merged_dict_does_not_affect_layers(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"nested": {"inner": [1, 2]}}
        )
        merged = manager.merge()
        merged["nested"]["inner"].append(999)
        merged["nested"]["extra"] = "injected"
        merged["new_key"] = "new_value"

        default_data = manager.get_layer_data(ConfigLayerType.DEFAULT)
        assert default_data["nested"]["inner"] == [1, 2]
        assert "extra" not in default_data["nested"]
        assert "new_key" not in default_data

    def test_consecutive_merges_are_isolated(self):
        manager = make_manager()
        manager.set_layer_data(
            ConfigLayerType.DEFAULT, {"data": {"list": [1]}}
        )

        merged1 = manager.merge()
        merged1["data"]["list"].append(2)

        merged2 = manager.merge()
        assert merged2["data"]["list"] == [1]


class TestComplexRealWorldScenario:
    def test_full_application_config(self):
        manager = make_manager()

        manager.set_layer_data(
            ConfigLayerType.DEFAULT,
            {
                "app": {
                    "name": "EcommercePlatform",
                    "version": "1.0.0",
                    "debug": False,
                    "features": ["auth", "cart", "checkout"],
                },
                "database": {
                    "type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "pool": {
                        "min_connections": 5,
                        "max_connections": 20,
                        "timeout": 30,
                    },
                    "credentials": {
                        "username": "default_user",
                        "password": "default_pass",
                    },
                },
                "server": {
                    "host": "127.0.0.1",
                    "port": 8000,
                    "workers": 4,
                    "cors": {
                        "enabled": False,
                        "origins": [],
                    },
                },
                "logging": {
                    "level": "WARNING",
                    "format": "json",
                    "handlers": ["file"],
                },
                "cache": {
                    "enabled": False,
                    "ttl": 300,
                },
            },
        )

        manager.set_layer_data(
            ConfigLayerType.ENVIRONMENT,
            {
                "app": {
                    "debug": True,
                    "features": ["auth", "cart", "checkout", "metrics"],
                },
                "database": {
                    "host": "prod-db.internal",
                    "pool": {
                        "max_connections": 100,
                    },
                    "credentials": {
                        "username": "env_user",
                        "password": "env_pass",
                    },
                },
                "server": {
                    "host": "0.0.0.0",
                    "workers": 8,
                    "cors": {
                        "enabled": True,
                        "origins": ["https://example.com"],
                    },
                },
                "logging": {
                    "level": "INFO",
                    "handlers": ["file", "console"],
                },
                "cache": {
                    "enabled": True,
                    "redis": {
                        "host": "redis.internal",
                        "port": 6379,
                    },
                },
            },
        )

        manager.set_layer_data(
            ConfigLayerType.OVERRIDE,
            {
                "server": {
                    "port": 9000,
                },
                "logging": {
                    "level": "DEBUG",
                },
                "database": {
                    "credentials": {
                        "password": "override_super_secret",
                    },
                },
            },
        )

        merged = manager.merge(array_strategy=ArrayMergeStrategy.APPEND)

        assert merged["app"]["name"] == "EcommercePlatform"
        assert merged["app"]["version"] == "1.0.0"
        assert merged["app"]["debug"] is True
        assert merged["app"]["features"] == [
            "auth",
            "cart",
            "checkout",
            "auth",
            "cart",
            "checkout",
            "metrics",
        ]

        assert merged["database"]["type"] == "postgresql"
        assert merged["database"]["host"] == "prod-db.internal"
        assert merged["database"]["port"] == 5432
        assert merged["database"]["pool"]["min_connections"] == 5
        assert merged["database"]["pool"]["max_connections"] == 100
        assert merged["database"]["pool"]["timeout"] == 30
        assert merged["database"]["credentials"]["username"] == "env_user"
        assert (
            merged["database"]["credentials"]["password"]
            == "override_super_secret"
        )

        assert merged["server"]["host"] == "0.0.0.0"
        assert merged["server"]["port"] == 9000
        assert merged["server"]["workers"] == 8
        assert merged["server"]["cors"]["enabled"] is True
        assert merged["server"]["cors"]["origins"] == ["https://example.com"]

        assert merged["logging"]["level"] == "DEBUG"
        assert merged["logging"]["format"] == "json"
        assert merged["logging"]["handlers"] == [
            "file",
            "file",
            "console",
        ]

        assert merged["cache"]["enabled"] is True
        assert merged["cache"]["ttl"] == 300
        assert merged["cache"]["redis"]["host"] == "redis.internal"
        assert merged["cache"]["redis"]["port"] == 6379
