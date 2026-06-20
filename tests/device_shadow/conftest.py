import pytest

from solocoder_py.device_shadow import DeviceShadow


@pytest.fixture
def shadow():
    return DeviceShadow(device_id="test-device-001")


@pytest.fixture
def shadow_v0():
    return DeviceShadow(device_id="test-device-001", initial_version=0)


@pytest.fixture
def shadow_with_desired(shadow):
    shadow.set_desired({"temperature": 25, "humidity": 60}, expected_version=1)
    return shadow


@pytest.fixture
def shadow_with_both(shadow):
    shadow.set_desired({"temperature": 25, "humidity": 60}, expected_version=1)
    shadow.set_reported({"temperature": 22, "humidity": 60}, expected_version=2)
    return shadow
