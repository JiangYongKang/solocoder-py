import pytest

from solocoder_py.tracing import Tracer


@pytest.fixture
def tracer():
    tracer = Tracer(sampling_rate=1.0)
    yield tracer
    tracer.clear()
    Tracer.reset_instance()


@pytest.fixture
def tracer_half_sampling():
    tracer = Tracer(sampling_rate=0.5)
    yield tracer
    tracer.clear()
    Tracer.reset_instance()


@pytest.fixture
def tracer_no_sampling():
    tracer = Tracer(sampling_rate=0.0)
    yield tracer
    tracer.clear()
    Tracer.reset_instance()


@pytest.fixture
def tracer_full_sampling():
    tracer = Tracer(sampling_rate=1.0)
    yield tracer
    tracer.clear()
    Tracer.reset_instance()
