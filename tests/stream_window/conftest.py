import pytest

from solocoder_py.stream_window import (
    AggregationType,
    Event,
    SlidingWindowAggregator,
    TumblingWindowAggregator,
    WatermarkGenerator,
)


@pytest.fixture
def tumbling_count_agg():
    return TumblingWindowAggregator(
        window_size_seconds=10.0,
        agg_type=AggregationType.COUNT,
    )


@pytest.fixture
def tumbling_sum_agg():
    return TumblingWindowAggregator(
        window_size_seconds=10.0,
        agg_type=AggregationType.SUM,
    )


@pytest.fixture
def tumbling_avg_agg():
    return TumblingWindowAggregator(
        window_size_seconds=10.0,
        agg_type=AggregationType.AVG,
    )


@pytest.fixture
def tumbling_with_lateness():
    return TumblingWindowAggregator(
        window_size_seconds=10.0,
        agg_type=AggregationType.COUNT,
        allowed_lateness_seconds=5.0,
        watermark_delay_seconds=2.0,
    )


@pytest.fixture
def sliding_count_agg():
    return SlidingWindowAggregator(
        window_size_seconds=10.0,
        slide_seconds=5.0,
        agg_type=AggregationType.COUNT,
    )


@pytest.fixture
def sliding_sum_agg():
    return SlidingWindowAggregator(
        window_size_seconds=10.0,
        slide_seconds=5.0,
        agg_type=AggregationType.SUM,
    )


@pytest.fixture
def sliding_with_lateness():
    return SlidingWindowAggregator(
        window_size_seconds=10.0,
        slide_seconds=5.0,
        agg_type=AggregationType.COUNT,
        allowed_lateness_seconds=5.0,
        watermark_delay_seconds=2.0,
    )


@pytest.fixture
def watermark_gen():
    return WatermarkGenerator(delay_seconds=2.0)
