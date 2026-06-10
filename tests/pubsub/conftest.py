import pytest

from solocoder_py.pubsub import (
    BackpressureStrategy,
    PubSubBroker,
)


@pytest.fixture
def broker() -> PubSubBroker:
    return PubSubBroker(
        default_subscriber_buffer_size=100,
        default_backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
    )


@pytest.fixture
def broker_with_topic(broker: PubSubBroker) -> PubSubBroker:
    broker.create_topic("test-topic")
    return broker
