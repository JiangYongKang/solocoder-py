from __future__ import annotations

import pytest
from typing import List

from solocoder_py.proxy import (
    HttpForwardProxy,
    ManualClock,
    MockUpstreamServer,
    ProxyConfig,
    UpstreamServer,
)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(0.0)


@pytest.fixture
def proxy_config() -> ProxyConfig:
    return ProxyConfig(
        connect_timeout=5.0,
        read_timeout=30.0,
        max_failures=2,
        failure_timeout=10.0,
        auto_failback=True,
        failback_interval=5.0,
        max_idle_time=30.0,
        max_reuse_count=5,
        max_pool_size=3,
    )


@pytest.fixture
def primary_upstream() -> UpstreamServer:
    return UpstreamServer(
        name="primary",
        host="127.0.0.1",
        port=8080,
        is_primary=True,
    )


@pytest.fixture
def backup_upstream() -> UpstreamServer:
    return UpstreamServer(
        name="backup",
        host="127.0.0.1",
        port=8081,
        is_primary=False,
    )


@pytest.fixture
def mock_primary_server() -> MockUpstreamServer:
    server = MockUpstreamServer("primary", "127.0.0.1", 8080)
    server.add_route(
        path_pattern="/api/test",
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=b'{"status": "ok", "server": "primary"}',
    )
    return server


@pytest.fixture
def mock_backup_server() -> MockUpstreamServer:
    server = MockUpstreamServer("backup", "127.0.0.1", 8081)
    server.add_route(
        path_pattern="/api/test",
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=b'{"status": "ok", "server": "backup"}',
    )
    return server


@pytest.fixture
def proxy_with_servers(
    primary_upstream: UpstreamServer,
    backup_upstream: UpstreamServer,
    mock_primary_server: MockUpstreamServer,
    mock_backup_server: MockUpstreamServer,
    proxy_config: ProxyConfig,
    clock: ManualClock,
) -> HttpForwardProxy:
    proxy = HttpForwardProxy(
        upstreams=[primary_upstream, backup_upstream],
        config=proxy_config,
        clock=clock,
    )
    proxy.register_mock_server(mock_primary_server)
    proxy.register_mock_server(mock_backup_server)
    return proxy


@pytest.fixture
def single_upstream_proxy(
    primary_upstream: UpstreamServer,
    mock_primary_server: MockUpstreamServer,
    proxy_config: ProxyConfig,
    clock: ManualClock,
) -> HttpForwardProxy:
    proxy = HttpForwardProxy(
        upstreams=[primary_upstream],
        config=proxy_config,
        clock=clock,
    )
    proxy.register_mock_server(mock_primary_server)
    return proxy
