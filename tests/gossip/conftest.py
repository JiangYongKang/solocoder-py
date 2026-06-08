from __future__ import annotations

import random

import pytest

from solocoder_py.gossip import (
    GossipConfig,
    GossipNode,
    ManualClock,
)


def make_config(
    *,
    heartbeat_interval: float = 1.0,
    suspect_timeout: float = 5.0,
    dead_timeout: float = 10.0,
    cleanup_timeout: float = 60.0,
    fanout: int = 3,
) -> GossipConfig:
    return GossipConfig(
        heartbeat_interval=heartbeat_interval,
        suspect_timeout=suspect_timeout,
        dead_timeout=dead_timeout,
        cleanup_timeout=cleanup_timeout,
        fanout=fanout,
    )


def make_node(
    node_id: str,
    clock: ManualClock,
    *,
    config: GossipConfig | None = None,
    seed: int = 42,
) -> GossipNode:
    cfg = config or make_config()
    rng = random.Random(seed)
    return GossipNode(node_id=node_id, config=cfg, clock=clock, rng=rng)


def connect_nodes(*nodes: GossipNode) -> None:
    for i, node in enumerate(nodes):
        for other in nodes[i + 1:]:
            node.connect(other)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def config() -> GossipConfig:
    return make_config()
