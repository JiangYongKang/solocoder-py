from __future__ import annotations

import pytest

from solocoder_py.pipeline import PipelineExecutor, StageConfig


def double(x: int) -> int:
    return x * 2


def to_str(x: int) -> str:
    return f"str_{x}"


def wrap_dict(x: str) -> dict:
    return {"value": x}


def fail_always(x) -> None:
    raise ValueError("always fails")


@pytest.fixture
def double_stage() -> StageConfig:
    return StageConfig(name="double", handler=double)


@pytest.fixture
def to_str_stage() -> StageConfig:
    return StageConfig(name="to_str", handler=to_str)


@pytest.fixture
def wrap_dict_stage() -> StageConfig:
    return StageConfig(name="wrap_dict", handler=wrap_dict)


@pytest.fixture
def fail_stage() -> StageConfig:
    return StageConfig(name="fail", handler=fail_always)


@pytest.fixture
def simple_pipeline(double_stage: StageConfig) -> PipelineExecutor:
    return PipelineExecutor(stages=[double_stage])


@pytest.fixture
def three_stage_pipeline(
    double_stage: StageConfig,
    to_str_stage: StageConfig,
    wrap_dict_stage: StageConfig,
) -> PipelineExecutor:
    return PipelineExecutor(stages=[double_stage, to_str_stage, wrap_dict_stage])
