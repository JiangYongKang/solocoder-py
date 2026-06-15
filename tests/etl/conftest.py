from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from solocoder_py.etl import (
    CheckpointStore,
    ETLPipeline,
    Extractor,
    IdentityTransformer,
    InMemoryExtractor,
    InMemoryLoader,
    Loader,
    Transformer,
)


@pytest.fixture
def checkpoint_dir(tmp_path) -> Path:
    d = tmp_path / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def checkpoint_store(checkpoint_dir) -> CheckpointStore:
    return CheckpointStore(checkpoint_dir=str(checkpoint_dir))


@pytest.fixture
def simple_source():
    return [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35},
        {"id": 4, "name": "Diana", "age": 28},
    ]


@pytest.fixture
def simple_extractor(simple_source) -> InMemoryExtractor:
    return InMemoryExtractor(simple_source)


@pytest.fixture
def identity_transformer() -> IdentityTransformer:
    return IdentityTransformer()


@pytest.fixture
def in_memory_loader() -> InMemoryLoader:
    return InMemoryLoader()


@pytest.fixture
def make_simple_pipeline(
    simple_extractor,
    identity_transformer,
    in_memory_loader,
    checkpoint_store,
):
    def _factory(
        job_id: str = "test_job",
        extractor: Extractor | None = None,
        transformer: Transformer | None = None,
        loader: Loader | None = None,
        enable_checkpoint: bool = True,
    ) -> ETLPipeline:
        return ETLPipeline(
            job_id=job_id,
            extractor=extractor or simple_extractor,
            transformer=transformer or identity_transformer,
            loader=loader or in_memory_loader,
            checkpoint_store=checkpoint_store if enable_checkpoint else None,
        )
    return _factory
