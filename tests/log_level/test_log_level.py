import pytest

from solocoder_py.log_level import LogLevel, LogLevelManager


class TestExplicitLevelSetAndGet:
    def test_set_and_get_effective_level(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        assert mgr.get_effective_level("app") == LogLevel.DEBUG

    def test_set_info_on_logger(self):
        mgr = LogLevelManager()
        mgr.set_level("app.service", "INFO")
        assert mgr.get_effective_level("app.service") == LogLevel.INFO

    def test_set_warning_on_logger(self):
        mgr = LogLevelManager()
        mgr.set_level("app.service.db", "WARNING")
        assert mgr.get_effective_level("app.service.db") == LogLevel.WARNING

    def test_set_error_on_logger(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        assert mgr.get_effective_level("app") == LogLevel.ERROR

    def test_set_critical_on_logger(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "CRITICAL")
        assert mgr.get_effective_level("app") == LogLevel.CRITICAL

    def test_set_level_case_insensitive(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "debug")
        assert mgr.get_effective_level("app") == LogLevel.DEBUG
        mgr.set_level("app", "Info")
        assert mgr.get_effective_level("app") == LogLevel.INFO

    def test_overwrite_existing_level(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        mgr.set_level("app", "ERROR")
        assert mgr.get_effective_level("app") == LogLevel.ERROR


class TestIsEnabledWithExplicitLevel:
    def test_debug_logger_debug_enabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        assert mgr.is_enabled("app", "DEBUG") is True

    def test_debug_logger_info_enabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        assert mgr.is_enabled("app", "INFO") is True

    def test_info_logger_debug_disabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "INFO")
        assert mgr.is_enabled("app", "DEBUG") is False

    def test_info_logger_info_enabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "INFO")
        assert mgr.is_enabled("app", "INFO") is True

    def test_warning_logger_info_disabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        assert mgr.is_enabled("app", "INFO") is False

    def test_error_logger_warning_disabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        assert mgr.is_enabled("app", "WARNING") is False

    def test_critical_logger_error_disabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "CRITICAL")
        assert mgr.is_enabled("app", "ERROR") is False

    def test_critical_logger_critical_enabled(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "CRITICAL")
        assert mgr.is_enabled("app", "CRITICAL") is True


class TestInheritancePropagation:
    def test_child_inherits_from_parent(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        assert mgr.get_effective_level("app.service") == LogLevel.WARNING

    def test_grandchild_inherits_from_grandparent(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        assert mgr.get_effective_level("app.service.db") == LogLevel.ERROR

    def test_child_with_explicit_level_does_not_inherit(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        mgr.set_level("app.service", "DEBUG")
        assert mgr.get_effective_level("app.service") == LogLevel.DEBUG

    def test_grandchild_inherits_from_parent_not_grandparent(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        mgr.set_level("app.service", "DEBUG")
        assert mgr.get_effective_level("app.service.db") == LogLevel.DEBUG

    def test_grandchild_with_explicit_level(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        mgr.set_level("app.service", "DEBUG")
        mgr.set_level("app.service.db", "INFO")
        assert mgr.get_effective_level("app.service.db") == LogLevel.INFO

    def test_default_info_when_no_level_set(self):
        mgr = LogLevelManager()
        assert mgr.get_effective_level("app") == LogLevel.INFO
        assert mgr.get_effective_level("app.service") == LogLevel.INFO
        assert mgr.get_effective_level("app.service.db") == LogLevel.INFO


class TestHotSwitching:
    def test_change_parent_level_child_inherits_immediately(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        assert mgr.is_enabled("app.service", "INFO") is False
        mgr.set_level("app", "DEBUG")
        assert mgr.is_enabled("app.service", "INFO") is True

    def test_change_parent_level_explicit_child_unaffected(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        mgr.set_level("app.service", "INFO")
        mgr.set_level("app", "DEBUG")
        assert mgr.get_effective_level("app.service") == LogLevel.INFO

    def test_change_own_level_immediate_effect(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        assert mgr.is_enabled("app", "INFO") is False
        mgr.set_level("app", "DEBUG")
        assert mgr.is_enabled("app", "INFO") is True

    def test_hot_switch_deep_hierarchy(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        assert mgr.is_enabled("app.service.db", "WARNING") is False
        mgr.set_level("app", "DEBUG")
        assert mgr.is_enabled("app.service.db", "WARNING") is True

    def test_hot_switch_mid_hierarchy(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        mgr.set_level("app.service", "WARNING")
        assert mgr.is_enabled("app.service.db", "INFO") is False
        mgr.set_level("app.service", "DEBUG")
        assert mgr.is_enabled("app.service.db", "INFO") is True

    def test_is_enabled_after_hot_switch(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "INFO")
        assert mgr.is_enabled("app.service", "DEBUG") is False
        assert mgr.is_enabled("app.service", "INFO") is True
        mgr.set_level("app", "WARNING")
        assert mgr.is_enabled("app.service", "INFO") is False
        assert mgr.is_enabled("app.service", "WARNING") is True


class TestRootLoggerLevel:
    def test_root_logger_empty_string(self):
        mgr = LogLevelManager()
        mgr.set_level("", "DEBUG")
        assert mgr.get_effective_level("") == LogLevel.DEBUG

    def test_root_logger_affects_all_children(self):
        mgr = LogLevelManager()
        mgr.set_level("", "DEBUG")
        assert mgr.get_effective_level("app") == LogLevel.DEBUG
        assert mgr.get_effective_level("app.service") == LogLevel.DEBUG

    def test_root_logger_overridden_by_closer_parent(self):
        mgr = LogLevelManager()
        mgr.set_level("", "DEBUG")
        mgr.set_level("app", "ERROR")
        assert mgr.get_effective_level("app.service") == LogLevel.ERROR

    def test_root_logger_default_is_info(self):
        mgr = LogLevelManager()
        assert mgr.get_effective_level("") == LogLevel.INFO

    def test_no_root_no_parent_defaults_to_info(self):
        mgr = LogLevelManager()
        assert mgr.get_effective_level("nonexistent") == LogLevel.INFO


class TestDeepInheritanceChain:
    def test_four_level_chain(self):
        mgr = LogLevelManager()
        mgr.set_level("a", "ERROR")
        assert mgr.get_effective_level("a.b") == LogLevel.ERROR
        assert mgr.get_effective_level("a.b.c") == LogLevel.ERROR
        assert mgr.get_effective_level("a.b.c.d") == LogLevel.ERROR

    def test_mid_override_in_deep_chain(self):
        mgr = LogLevelManager()
        mgr.set_level("a", "ERROR")
        mgr.set_level("a.b.c", "DEBUG")
        assert mgr.get_effective_level("a.b") == LogLevel.ERROR
        assert mgr.get_effective_level("a.b.c") == LogLevel.DEBUG
        assert mgr.get_effective_level("a.b.c.d") == LogLevel.DEBUG

    def test_deep_chain_with_multiple_overrides(self):
        mgr = LogLevelManager()
        mgr.set_level("a", "CRITICAL")
        mgr.set_level("a.b", "WARNING")
        mgr.set_level("a.b.c.d", "DEBUG")
        assert mgr.get_effective_level("a") == LogLevel.CRITICAL
        assert mgr.get_effective_level("a.b") == LogLevel.WARNING
        assert mgr.get_effective_level("a.b.c") == LogLevel.WARNING
        assert mgr.get_effective_level("a.b.c.d") == LogLevel.DEBUG


class TestAllLevelComparisons:
    def test_debug_level_all_comparisons(self):
        mgr = LogLevelManager()
        mgr.set_level("x", "DEBUG")
        assert mgr.is_enabled("x", "DEBUG") is True
        assert mgr.is_enabled("x", "INFO") is True
        assert mgr.is_enabled("x", "WARNING") is True
        assert mgr.is_enabled("x", "ERROR") is True
        assert mgr.is_enabled("x", "CRITICAL") is True

    def test_info_level_all_comparisons(self):
        mgr = LogLevelManager()
        mgr.set_level("x", "INFO")
        assert mgr.is_enabled("x", "DEBUG") is False
        assert mgr.is_enabled("x", "INFO") is True
        assert mgr.is_enabled("x", "WARNING") is True
        assert mgr.is_enabled("x", "ERROR") is True
        assert mgr.is_enabled("x", "CRITICAL") is True

    def test_warning_level_all_comparisons(self):
        mgr = LogLevelManager()
        mgr.set_level("x", "WARNING")
        assert mgr.is_enabled("x", "DEBUG") is False
        assert mgr.is_enabled("x", "INFO") is False
        assert mgr.is_enabled("x", "WARNING") is True
        assert mgr.is_enabled("x", "ERROR") is True
        assert mgr.is_enabled("x", "CRITICAL") is True

    def test_error_level_all_comparisons(self):
        mgr = LogLevelManager()
        mgr.set_level("x", "ERROR")
        assert mgr.is_enabled("x", "DEBUG") is False
        assert mgr.is_enabled("x", "INFO") is False
        assert mgr.is_enabled("x", "WARNING") is False
        assert mgr.is_enabled("x", "ERROR") is True
        assert mgr.is_enabled("x", "CRITICAL") is True

    def test_critical_level_all_comparisons(self):
        mgr = LogLevelManager()
        mgr.set_level("x", "CRITICAL")
        assert mgr.is_enabled("x", "DEBUG") is False
        assert mgr.is_enabled("x", "INFO") is False
        assert mgr.is_enabled("x", "WARNING") is False
        assert mgr.is_enabled("x", "ERROR") is False
        assert mgr.is_enabled("x", "CRITICAL") is True

    def test_level_numeric_ordering(self):
        assert LogLevel.DEBUG < LogLevel.INFO
        assert LogLevel.INFO < LogLevel.WARNING
        assert LogLevel.WARNING < LogLevel.ERROR
        assert LogLevel.ERROR < LogLevel.CRITICAL


class TestInvalidLevelName:
    def test_set_invalid_level_raises(self):
        mgr = LogLevelManager()
        with pytest.raises(ValueError, match="Invalid log level"):
            mgr.set_level("app", "VERBOSE")

    def test_set_invalid_level_case_raises(self):
        mgr = LogLevelManager()
        with pytest.raises(ValueError, match="Invalid log level"):
            mgr.set_level("app", "notalevel")

    def test_is_enabled_invalid_level_raises(self):
        mgr = LogLevelManager()
        with pytest.raises(ValueError, match="Invalid log level"):
            mgr.is_enabled("app", "TRACE")

    def test_set_empty_string_level_raises(self):
        mgr = LogLevelManager()
        with pytest.raises(ValueError, match="Invalid log level"):
            mgr.set_level("app", "")


class TestQueryNonexistentLogger:
    def test_nonexistent_logger_returns_default_info(self):
        mgr = LogLevelManager()
        assert mgr.get_effective_level("nonexistent") == LogLevel.INFO

    def test_nonexistent_deep_logger_returns_default(self):
        mgr = LogLevelManager()
        assert mgr.get_effective_level("x.y.z.w") == LogLevel.INFO

    def test_is_enabled_nonexistent_logger_default_info(self):
        mgr = LogLevelManager()
        assert mgr.is_enabled("nonexistent", "INFO") is True
        assert mgr.is_enabled("nonexistent", "DEBUG") is False

    def test_nonexistent_logger_with_root_set(self):
        mgr = LogLevelManager()
        mgr.set_level("", "DEBUG")
        assert mgr.get_effective_level("nonexistent") == LogLevel.DEBUG


class TestMultipleLoggerInheritanceIsolation:
    def test_sibling_loggers_independent(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        mgr.set_level("app.service_a", "DEBUG")
        assert mgr.get_effective_level("app.service_a") == LogLevel.DEBUG
        assert mgr.get_effective_level("app.service_b") == LogLevel.WARNING

    def test_changing_one_sibling_does_not_affect_other(self):
        mgr = LogLevelManager()
        mgr.set_level("app.service_a", "DEBUG")
        mgr.set_level("app.service_b", "ERROR")
        mgr.set_level("app.service_a", "INFO")
        assert mgr.get_effective_level("app.service_a") == LogLevel.INFO
        assert mgr.get_effective_level("app.service_b") == LogLevel.ERROR

    def test_different_branches_independent(self):
        mgr = LogLevelManager()
        mgr.set_level("app.db", "DEBUG")
        mgr.set_level("app.web", "ERROR")
        assert mgr.get_effective_level("app.db.conn") == LogLevel.DEBUG
        assert mgr.get_effective_level("app.web.handler") == LogLevel.ERROR
        assert mgr.get_effective_level("app.cache") == LogLevel.INFO

    def test_multiple_overrides_no_interference(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        mgr.set_level("app.db", "DEBUG")
        mgr.set_level("app.web", "WARNING")
        assert mgr.get_effective_level("app") == LogLevel.ERROR
        assert mgr.get_effective_level("app.db") == LogLevel.DEBUG
        assert mgr.get_effective_level("app.web") == LogLevel.WARNING
        assert mgr.get_effective_level("app.cache") == LogLevel.ERROR
        assert mgr.get_effective_level("app.db.conn") == LogLevel.DEBUG
        assert mgr.get_effective_level("app.web.handler") == LogLevel.WARNING

    def test_hot_switch_one_branch_does_not_affect_other(self):
        mgr = LogLevelManager()
        mgr.set_level("app.db", "DEBUG")
        mgr.set_level("app.web", "ERROR")
        mgr.set_level("app.db", "CRITICAL")
        assert mgr.get_effective_level("app.db") == LogLevel.CRITICAL
        assert mgr.get_effective_level("app.web") == LogLevel.ERROR
        assert mgr.get_effective_level("app.db.conn") == LogLevel.CRITICAL
        assert mgr.get_effective_level("app.web.handler") == LogLevel.ERROR


class TestClearLevel:
    def test_clear_explicit_level(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        assert mgr.clear_level("app") is True
        assert mgr.get_effective_level("app") == LogLevel.INFO

    def test_clear_nonexistent_level(self):
        mgr = LogLevelManager()
        assert mgr.clear_level("app") is False

    def test_clear_level_causes_reinherit(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "ERROR")
        mgr.set_level("app.service", "DEBUG")
        mgr.clear_level("app.service")
        assert mgr.get_effective_level("app.service") == LogLevel.ERROR

    def test_clear_level_causes_default(self):
        mgr = LogLevelManager()
        mgr.set_level("app.service", "DEBUG")
        mgr.clear_level("app.service")
        assert mgr.get_effective_level("app.service") == LogLevel.INFO

    def test_clear_child_does_not_affect_parent(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "WARNING")
        mgr.set_level("app.service", "DEBUG")
        mgr.clear_level("app.service")
        assert mgr.get_effective_level("app") == LogLevel.WARNING


class TestHasExplicitLevel:
    def test_has_explicit_level_true(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        assert mgr.has_explicit_level("app") is True

    def test_has_explicit_level_false(self):
        mgr = LogLevelManager()
        assert mgr.has_explicit_level("app") is False

    def test_has_explicit_after_clear(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        mgr.clear_level("app")
        assert mgr.has_explicit_level("app") is False


class TestClearAll:
    def test_clear_all_resets_to_default(self):
        mgr = LogLevelManager()
        mgr.set_level("app", "DEBUG")
        mgr.set_level("app.service", "ERROR")
        mgr.clear_all()
        assert mgr.get_effective_level("app") == LogLevel.INFO
        assert mgr.get_effective_level("app.service") == LogLevel.INFO

    def test_clear_all_no_explicit_levels(self):
        mgr = LogLevelManager()
        mgr.clear_all()
        assert mgr.get_effective_level("app") == LogLevel.INFO


class TestLogLevelEnum:
    def test_level_values(self):
        assert LogLevel.DEBUG == 10
        assert LogLevel.INFO == 20
        assert LogLevel.WARNING == 30
        assert LogLevel.ERROR == 40
        assert LogLevel.CRITICAL == 50

    def test_level_from_name(self):
        assert LogLevel["DEBUG"] == LogLevel.DEBUG
        assert LogLevel["INFO"] == LogLevel.INFO
