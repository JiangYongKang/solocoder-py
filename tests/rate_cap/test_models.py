from __future__ import annotations

import pytest

from solocoder_py.rate_cap import (
    InvalidWindowConfigError,
    RateCapConfig,
    SubjectQuotas,
    WindowConfig,
)


class TestWindowConfigValidation:
    def test_empty_name_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError, match="window name cannot be empty"
        ):
            WindowConfig(
                name="", window_seconds=60, max_operations=100
            )

    def test_negative_window_seconds_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="window_seconds must be positive",
        ):
            WindowConfig(
                name="w", window_seconds=-1, max_operations=100
            )

    def test_zero_window_seconds_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="window_seconds must be positive",
        ):
            WindowConfig(
                name="w", window_seconds=0, max_operations=100
            )

    def test_negative_max_operations_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="max_operations must be positive",
        ):
            WindowConfig(
                name="w", window_seconds=60, max_operations=-1
            )

    def test_zero_max_operations_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="max_operations must be positive",
        ):
            WindowConfig(
                name="w", window_seconds=60, max_operations=0
            )

    def test_negative_granularity_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="slide_granularity_seconds cannot be negative",
        ):
            WindowConfig(
                name="w",
                window_seconds=60,
                max_operations=100,
                slide_granularity_seconds=-1,
            )

    def test_granularity_exceeds_window_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="slide_granularity_seconds.*cannot exceed window_seconds",
        ):
            WindowConfig(
                name="w",
                window_seconds=60,
                max_operations=100,
                slide_granularity_seconds=61,
            )

    def test_valid_zero_granularity(self):
        wc = WindowConfig(
            name="w",
            window_seconds=60,
            max_operations=100,
            slide_granularity_seconds=0,
        )
        assert wc.slide_granularity_seconds == 0

    def test_valid_granularity_equals_window(self):
        wc = WindowConfig(
            name="w",
            window_seconds=60,
            max_operations=100,
            slide_granularity_seconds=60,
        )
        assert wc.slide_granularity_seconds == 60


class TestRateCapConfigValidation:
    def test_empty_windows_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="At least one window must be configured",
        ):
            RateCapConfig(windows=[])

    def test_duplicate_window_names_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError, match="Duplicate window name"
        ):
            RateCapConfig(
                windows=[
                    WindowConfig("a", 60, 100),
                    WindowConfig("a", 120, 200),
                ]
            )

    def test_subject_quotas_subject_id_mismatch(self):
        with pytest.raises(
            InvalidWindowConfigError, match="SubjectQuotas.subject_id mismatch"
        ):
            RateCapConfig(
                windows=[WindowConfig("1min", 60, 100)],
                subject_quotas={
                    "key-001": SubjectQuotas(
                        subject_id="key-002",
                        per_window_quotas={"1min": 50},
                    )
                },
            )

    def test_subject_references_unknown_window(self):
        with pytest.raises(
            InvalidWindowConfigError, match="references unknown window"
        ):
            RateCapConfig(
                windows=[WindowConfig("1min", 60, 100)],
                subject_quotas={
                    "u1": SubjectQuotas(
                        subject_id="u1",
                        per_window_quotas={"unknown_window": 50},
                    )
                },
            )

    def test_subject_non_positive_quota_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError, match="quota must be positive"
        ):
            RateCapConfig(
                windows=[WindowConfig("1min", 60, 100)],
                subject_quotas={
                    "u1": SubjectQuotas(
                        subject_id="u1",
                        per_window_quotas={"1min": 0},
                    )
                },
            )

    def test_default_quotas_references_unknown_window(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="default_subject_quotas references unknown window",
        ):
            RateCapConfig(
                windows=[WindowConfig("1min", 60, 100)],
                default_subject_quotas={"unknown": 50},
            )

    def test_default_quotas_non_positive_rejected(self):
        with pytest.raises(
            InvalidWindowConfigError,
            match="default_subject_quotas.*quota must be positive",
        ):
            RateCapConfig(
                windows=[WindowConfig("1min", 60, 100)],
                default_subject_quotas={"1min": -1},
            )

    def test_valid_config(self):
        config = RateCapConfig(
            windows=[
                WindowConfig("1min", 60, 100),
                WindowConfig("1hour", 3600, 1000),
            ],
            subject_quotas={
                "u1": SubjectQuotas(
                    subject_id="u1",
                    per_window_quotas={"1min": 50, "1hour": 500},
                )
            },
            default_subject_quotas={"1min": 80, "1hour": 800},
        )
        assert len(config.windows) == 2
        assert config.get_subject_limit("u1", "1min") == 50
        assert config.get_subject_limit("u1", "1hour") == 500
        assert config.get_subject_limit("unknown", "1min") == 80
        assert config.get_subject_limit("unknown", "1hour") == 800
        assert config.get_global_limit("1min") == 100
        assert config.get_global_limit("1hour") == 1000

    def test_get_window(self):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 100)]
        )
        assert config.get_window("1min") is not None
        assert config.get_window("unknown") is None

    def test_get_subject_limit_falls_back_to_window(self):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 100)]
        )
        assert config.get_subject_limit("any", "1min") == 100

    def test_get_subject_limit_unknown_window(self):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 100)]
        )
        assert config.get_subject_limit("any", "unknown") is None

    def test_get_global_limit_unknown_window(self):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 100)]
        )
        assert config.get_global_limit("unknown") is None
