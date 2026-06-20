import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from solocoder_py.telemetry.clock import ManualClock
from solocoder_py.telemetry.models import (
    BufferConfig,
    SchemaConfig,
    WindowConfig,
    LateDataStrategy,
)
from solocoder_py.telemetry.buffer import BatchBuffer
from solocoder_py.telemetry.schema import SchemaNormalizer
from solocoder_py.telemetry.window import OrderWindow
from solocoder_py.telemetry.pipeline import TelemetryPipeline

import pytest


@pytest.fixture
def manual_clock():
    return ManualClock(start_time=1000.0)


@pytest.fixture
def buffer_config_default():
    return BufferConfig(batch_size=5, timeout_seconds=10.0)


@pytest.fixture
def schema_config_default():
    return SchemaConfig(
        field_mapping={
            "temp": "temperature",
            "humid": "humidity",
        },
        drop_unmapped=False,
    )


@pytest.fixture
def window_config_default():
    return WindowConfig(
        tolerance_seconds=30.0,
        timestamp_field="timestamp",
        late_data_strategy=LateDataStrategy.LOG,
    )


@pytest.fixture
def collected_flushes():
    return []
