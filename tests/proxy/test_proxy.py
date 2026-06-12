from __future__ import annotations

import pytest

from solocoder_py.proxy import (
    AllUpstreamsFailedError,
    FilterMode,
    HeaderFilter,
    HeaderFilterConfig,
    HttpForwardProxy,
    LambdaRequestRewriter,
    LambdaResponseRewriter,
    ManualClock,
    MockUpstreamServer,
    ProxyConfig,
    Request,
    RequestBodyRewriter,
    RequestHeaderRewriter,
    Response,
    ResponseBodyRewriter,
    ResponseHeaderRewriter,
    RewriterChain,
    RewriterError,
    StatusCodeRewriter,
    UpstreamError,
    UpstreamServer,
    UrlRewriter,
)


class TestNormalFlows:
    def test_request_forward_and_response_echo(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={"Accept": "application/json"},
        )
        response = proxy_with_servers.forward(request)

        assert response.status_code == 200
        assert b'"status": "ok"' in response.body
        assert response.headers["X-Upstream-Server"] == "primary"
        assert proxy_with_servers.stats.total_requests == 1
        assert proxy_with_servers.stats.forwarded_requests == 1

    def test_rewriters_execute_in_order(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        chain = proxy_with_servers.rewriter_chain

        chain.register_request_rewriter(
            RequestHeaderRewriter(add_headers={"X-Proxy-Id": "test-123"})
        )
        chain.register_request_rewriter(
            UrlRewriter().add_rule(r"/api/test", "/api/v1/test")
        )

        captured_headers: dict = {}

        def capture_headers(req: Request) -> Request:
            captured_headers["X-Proxy-Id"] = req.headers.get("X-Proxy-Id", "")
            captured_headers["url"] = req.url
            return req

        chain.register_request_rewriter(LambdaRequestRewriter(capture_headers))

        chain.register_response_rewriter(
            ResponseHeaderRewriter(add_headers={"X-Proxied": "true"})
        )
        chain.register_response_rewriter(
            StatusCodeRewriter(mappings={200: 201})
        )

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )
        response = proxy_with_servers.forward(request)

        assert captured_headers["X-Proxy-Id"] == "test-123"
        assert "/api/v1/test" in captured_headers["url"]
        assert response.status_code == 201
        assert response.headers["X-Proxied"] == "true"

    def test_whitelist_header_filter(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
    ) -> None:
        captured_request_headers: dict = {}

        def capture_and_echo(request: Request) -> Response:
            captured_request_headers.update(dict(request.headers))
            return Response(
                status_code=200,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": "2",
                    "X-Upstream-Server": "primary",
                    "X-Internal": "secret",
                },
                body=b"OK",
            )

        mock_primary_server.add_route(
            path_pattern="/filtered",
            handler=capture_and_echo,
        )

        request_filter = HeaderFilter(
            HeaderFilterConfig(
                mode=FilterMode.WHITELIST,
                headers=["accept", "content-type"],
                case_insensitive=True,
            )
        )
        response_filter = HeaderFilter(
            HeaderFilterConfig(
                mode=FilterMode.WHITELIST,
                headers=["content-type", "content-length"],
                case_insensitive=True,
            )
        )
        proxy_with_servers.set_request_header_filter(request_filter)
        proxy_with_servers.set_response_header_filter(response_filter)

        request = Request(
            method="GET",
            url="http://example.com/filtered",
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "X-Secret": "should-be-removed",
                "Authorization": "Bearer token",
            },
        )
        response = proxy_with_servers.forward(request)

        captured_lower = {k.lower(): v for k, v in captured_request_headers.items()}
        assert "accept" in captured_lower
        assert "content-type" in captured_lower
        assert "x-secret" not in captured_lower
        assert "authorization" not in captured_lower

        response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert "content-type" in response_headers_lower
        assert "content-length" in response_headers_lower
        assert "x-upstream-server" not in response_headers_lower
        assert "x-internal" not in response_headers_lower

    def test_blacklist_header_filter(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
    ) -> None:
        captured_request_headers: dict = {}

        def capture_and_echo(request: Request) -> Response:
            captured_request_headers.update(dict(request.headers))
            return Response(
                status_code=200,
                headers={"Content-Type": "text/plain"},
                body=b"OK",
            )

        mock_primary_server.add_route(
            path_pattern="/filtered",
            handler=capture_and_echo,
        )

        request_filter = HeaderFilter(
            HeaderFilterConfig(
                mode=FilterMode.BLACKLIST,
                headers=["x-secret", "authorization"],
                case_insensitive=True,
            )
        )
        proxy_with_servers.set_request_header_filter(request_filter)

        request = Request(
            method="GET",
            url="http://example.com/filtered",
            headers={
                "Accept": "application/json",
                "X-Secret": "should-be-removed",
                "Authorization": "Bearer token",
                "X-Other": "keep",
            },
        )
        response = proxy_with_servers.forward(request)

        captured_lower = {k.lower(): v for k, v in captured_request_headers.items()}
        assert "accept" in captured_lower
        assert "x-other" in captured_lower
        assert "x-secret" not in captured_lower
        assert "authorization" not in captured_lower
        assert captured_lower.get("x-other") == "keep"

    def test_upstream_failover(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
        clock: ManualClock,
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        response1 = proxy_with_servers.forward(request)
        assert response1.headers["X-Upstream-Server"] == "primary"
        assert proxy_with_servers.stats.failover_count == 0

        mock_primary_server.set_unavailable()

        response2 = proxy_with_servers.forward(request)
        assert response2.headers["X-Upstream-Server"] == "backup"
        assert proxy_with_servers.stats.failover_count >= 1

        assert proxy_with_servers.upstream_manager.current_upstream.name == "backup"

    def test_connection_reuse(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        for i in range(3):
            response = proxy_with_servers.forward(request)
            assert response.status_code == 200

        stats = proxy_with_servers.stats
        assert stats.total_requests == 3
        assert stats.reused_connections >= 2

        pool = proxy_with_servers.connection_pool
        assert pool.get_total_connections() >= 1


class TestEdgeCases:
    def test_no_rewriters_passthrough(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        assert proxy_with_servers.rewriter_chain.request_rewriter_count == 0
        assert proxy_with_servers.rewriter_chain.response_rewriter_count == 0

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={"X-Custom": "value"},
            body=b"original-body",
        )
        request_copy = request.copy()

        response = proxy_with_servers.forward(request)

        assert request.method == request_copy.method
        assert request.url == request_copy.url
        assert request.headers == request_copy.headers
        assert request.body == request_copy.body
        assert response.status_code == 200

    def test_empty_request_body(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
            body=b"",
        )
        response = proxy_with_servers.forward(request)
        assert response.status_code == 200

    def test_empty_response_body(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
    ) -> None:
        mock_primary_server.add_route(
            path_pattern="/empty",
            status_code=204,
            body=b"",
        )

        request = Request(
            method="GET",
            url="http://example.com/empty",
            headers={},
        )
        response = proxy_with_servers.forward(request)

        assert response.status_code == 204
        assert response.body == b""

    def test_single_upstream_failure(
        self,
        single_upstream_proxy: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
        proxy_config: ProxyConfig,
    ) -> None:
        mock_primary_server.set_unavailable()

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        with pytest.raises(UpstreamError):
            single_upstream_proxy.forward(request)

        assert single_upstream_proxy.stats.failed_requests >= 1

    def test_connection_max_reuse_creates_new(
        self,
        proxy_with_servers: HttpForwardProxy,
        proxy_config: ProxyConfig,
        clock: ManualClock,
    ) -> None:
        max_reuse = proxy_config.max_reuse_count
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        for i in range(max_reuse + 2):
            response = proxy_with_servers.forward(request)
            assert response.status_code == 200
            clock.advance(0.1)

        conn_counter = proxy_with_servers.connection_pool.connection_counter
        assert conn_counter >= 2

    def test_no_matching_rewrite_rule(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        chain = proxy_with_servers.rewriter_chain
        chain.register_request_rewriter(
            UrlRewriter().add_rule(r"/api/v2/", "/api/v1/")
        )

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )
        original_url = request.url

        response = proxy_with_servers.forward(request)

        assert request.url == original_url
        assert response.status_code == 200


class TestExceptionBranches:
    def test_all_upstreams_failed(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
        mock_backup_server: MockUpstreamServer,
    ) -> None:
        mock_primary_server.set_unavailable()
        mock_backup_server.set_unavailable()

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        with pytest.raises(AllUpstreamsFailedError):
            proxy_with_servers.forward(request)

        stats = proxy_with_servers.stats
        assert stats.failed_requests >= 1

    def test_rewriter_exception_handling(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        def failing_rewriter(req: Request) -> Request:
            raise RuntimeError("Rewrite failed")

        proxy_with_servers.rewriter_chain.register_request_rewriter(
            LambdaRequestRewriter(failing_rewriter)
        )

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        with pytest.raises(RewriterError, match="Rewrite failed"):
            proxy_with_servers.forward(request)

        assert proxy_with_servers.stats.failed_requests == 1

    def test_rewriter_exception_in_response(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        def failing_response_rewriter(resp: Response, req: Request) -> Response:
            raise RuntimeError("Response rewrite failed")

        proxy_with_servers.rewriter_chain.register_response_rewriter(
            LambdaResponseRewriter(failing_response_rewriter)
        )

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        with pytest.raises(RewriterError, match="Response rewrite failed"):
            proxy_with_servers.forward(request)

    def test_connection_break_retry(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
    ) -> None:
        fail_count = 0

        def flaky_handler(request: Request) -> Response:
            nonlocal fail_count
            if fail_count == 0:
                fail_count += 1
                raise UpstreamError("Connection reset")
            return Response(
                status_code=200,
                headers={"Content-Type": "text/plain"},
                body=b"Success after retry",
            )

        mock_primary_server.add_route(
            path_pattern="/flaky",
            handler=flaky_handler,
        )

        request = Request(
            method="GET",
            url="http://example.com/flaky",
            headers={},
        )

        response = proxy_with_servers.forward(request)
        assert response.status_code == 200
        assert response.body == b"Success after retry"

    def test_large_request_body_streaming(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
    ) -> None:
        large_body = b"x" * 1024 * 1024

        def echo_handler(request: Request) -> Response:
            return Response(
                status_code=200,
                headers={"Content-Type": "application/octet-stream"},
                body=request.body,
            )

        mock_primary_server.add_route(
            path_pattern="/large",
            handler=echo_handler,
        )

        request = Request(
            method="POST",
            url="http://example.com/large",
            headers={"Content-Type": "application/octet-stream"},
            body=large_body,
            stream=True,
        )

        response = proxy_with_servers.forward(request)
        assert response.status_code == 200
        assert response.body == large_body
        assert len(response.body) == 1024 * 1024


class TestRewriterChain:
    def test_request_body_rewrite(self) -> None:
        chain = RewriterChain()
        chain.register_request_rewriter(
            RequestBodyRewriter(
                transformer=lambda b: b.replace(b"old", b"new")
            )
        )

        request = Request(
            method="POST",
            url="http://example.com",
            body=b"This is old content",
        )
        modified = chain.rewrite_request(request)

        assert modified.body == b"This is new content"

    def test_response_body_rewrite(self) -> None:
        chain = RewriterChain()
        chain.register_response_rewriter(
            ResponseBodyRewriter(
                transformer=lambda b, req: b.upper() if req.method == "GET" else b
            )
        )

        request = Request(method="GET", url="http://example.com")
        response = Response(status_code=200, body=b"hello world")
        modified = chain.rewrite_response(response, request)

        assert modified.body == b"HELLO WORLD"

    def test_multiple_rewriters_chained(self) -> None:
        chain = RewriterChain()
        chain.register_request_rewriter(
            UrlRewriter().add_rule(r"/api/", "/api/v1/")
        )
        chain.register_request_rewriter(
            RequestHeaderRewriter(add_headers={"X-Version": "1"})
        )
        chain.register_request_rewriter(
            RequestBodyRewriter(transformer=lambda b: b + b" [modified]")
        )

        request = Request(
            method="POST",
            url="http://example.com/api/test",
            headers={},
            body=b"original",
        )
        modified = chain.rewrite_request(request)

        assert "/api/v1/" in modified.url
        assert modified.headers["X-Version"] == "1"
        assert modified.body == b"original [modified]"

    def test_url_rewrite_ignores_query_params_match(self) -> None:
        rewriter = UrlRewriter().add_rule(r"/api", "/api/v1")

        request = Request(
            method="GET",
            url="http://example.com/products?filter=api&sort=name",
            headers={},
        )
        modified = rewriter.rewrite(request)

        assert modified.url == request.url
        assert "/products?" in modified.url
        assert "filter=api" in modified.url
        assert "sort=name" in modified.url
        assert "/api/v1" not in modified.url


class TestHeaderFilter:
    def test_case_insensitive_matching(self) -> None:
        config = HeaderFilterConfig(
            mode=FilterMode.BLACKLIST,
            headers=["authorization", "x-secret"],
            case_insensitive=True,
        )
        hf = HeaderFilter(config)

        request = Request(
            method="GET",
            url="http://example.com",
            headers={
                "Authorization": "Bearer token",
                "X-SECRET": "value",
                "Accept": "application/json",
            },
        )
        filtered = hf.filter_request_headers(request)

        assert "Authorization" not in filtered.headers
        assert "X-SECRET" not in filtered.headers
        assert "Accept" in filtered.headers

    def test_case_sensitive_matching(self) -> None:
        config = HeaderFilterConfig(
            mode=FilterMode.WHITELIST,
            headers=["Authorization"],
            case_insensitive=False,
        )
        hf = HeaderFilter(config)

        request = Request(
            method="GET",
            url="http://example.com",
            headers={
                "Authorization": "Bearer token",
                "authorization": "lowercase",
                "Accept": "application/json",
            },
        )
        filtered = hf.filter_request_headers(request)

        assert "Authorization" in filtered.headers
        assert "authorization" not in filtered.headers
        assert "Accept" not in filtered.headers

    def test_empty_filter_list_blacklist(self) -> None:
        config = HeaderFilterConfig(
            mode=FilterMode.BLACKLIST,
            headers=[],
        )
        hf = HeaderFilter(config)

        request = Request(
            method="GET",
            url="http://example.com",
            headers={"A": "1", "B": "2", "C": "3"},
        )
        filtered = hf.filter_request_headers(request)

        assert len(filtered.headers) == 3

    def test_empty_filter_list_whitelist(self) -> None:
        config = HeaderFilterConfig(
            mode=FilterMode.WHITELIST,
            headers=[],
        )
        hf = HeaderFilter(config)

        request = Request(
            method="GET",
            url="http://example.com",
            headers={"A": "1", "B": "2", "C": "3"},
        )
        filtered = hf.filter_request_headers(request)

        assert len(filtered.headers) == 0


class TestFailoverRecovery:
    def test_primary_recovery_failback(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
        clock: ManualClock,
        proxy_config: ProxyConfig,
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        mock_primary_server.set_unavailable()
        response = proxy_with_servers.forward(request)
        assert response.headers["X-Upstream-Server"] == "backup"

        mock_primary_server.set_available()
        clock.advance(proxy_config.failure_timeout + 1)
        clock.advance(proxy_config.failback_interval + 1)

        response = proxy_with_servers.forward(request)
        assert response.headers["X-Upstream-Server"] == "primary"

    def test_no_auto_failback(
        self,
        primary_upstream: UpstreamServer,
        backup_upstream: UpstreamServer,
        mock_primary_server: MockUpstreamServer,
        mock_backup_server: MockUpstreamServer,
        clock: ManualClock,
    ) -> None:
        config = ProxyConfig(
            max_failures=1,
            failure_timeout=10.0,
            auto_failback=False,
            max_reuse_count=5,
            max_pool_size=3,
        )
        proxy = HttpForwardProxy(
            upstreams=[primary_upstream, backup_upstream],
            config=config,
            clock=clock,
        )
        proxy.register_mock_server(mock_primary_server)
        proxy.register_mock_server(mock_backup_server)

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        mock_primary_server.set_unavailable()
        response = proxy.forward(request)
        assert response.headers["X-Upstream-Server"] == "backup"

        mock_primary_server.set_available()
        clock.advance(100.0)

        for _ in range(5):
            response = proxy.forward(request)
            assert response.headers["X-Upstream-Server"] == "backup"


class TestConnectionPool:
    def test_connection_expiry(
        self,
        proxy_with_servers: HttpForwardProxy,
        clock: ManualClock,
        proxy_config: ProxyConfig,
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        proxy_with_servers.forward(request)
        initial_connections = proxy_with_servers.connection_pool.get_total_connections()
        assert initial_connections >= 1

        clock.advance(proxy_config.max_idle_time + 1)

        proxy_with_servers.forward(request)
        new_connections = proxy_with_servers.connection_pool.get_total_connections()
        assert new_connections >= 1

    def test_multiple_upstream_pools(
        self,
        proxy_with_servers: HttpForwardProxy,
        mock_primary_server: MockUpstreamServer,
        mock_backup_server: MockUpstreamServer,
    ) -> None:
        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        proxy_with_servers.forward(request)
        primary_pool_size = proxy_with_servers.connection_pool.get_pool_size(
            mock_primary_server.address
        )
        assert primary_pool_size >= 1

        mock_primary_server.set_unavailable()
        proxy_with_servers.forward(request)

        backup_pool_size = proxy_with_servers.connection_pool.get_pool_size(
            mock_backup_server.address
        )
        assert backup_pool_size >= 1


class TestConfigValidation:
    def test_invalid_config_negative_timeout(self) -> None:
        with pytest.raises(Exception, match="connect_timeout must be positive"):
            ProxyConfig(connect_timeout=-1)

    def test_invalid_config_zero_max_failures(self) -> None:
        with pytest.raises(Exception, match="max_failures must be positive"):
            ProxyConfig(max_failures=0)

    def test_invalid_config_zero_pool_size(self) -> None:
        with pytest.raises(Exception, match="max_pool_size must be positive"):
            ProxyConfig(max_pool_size=0)


class TestProxyLifecycle:
    def test_context_manager(self) -> None:
        upstream = UpstreamServer(name="test", host="127.0.0.1", port=9999)
        mock_server = MockUpstreamServer("test", "127.0.0.1", 9999)

        with HttpForwardProxy(upstreams=[upstream]) as proxy:
            proxy.register_mock_server(mock_server)
            assert proxy.connection_pool.get_total_connections() == 0

        assert proxy.connection_pool.get_total_connections() == 0

    def test_closed_proxy_rejects_requests(
        self, proxy_with_servers: HttpForwardProxy
    ) -> None:
        proxy_with_servers.close()

        request = Request(
            method="GET",
            url="http://example.com/api/test",
            headers={},
        )

        with pytest.raises(Exception, match="Proxy is closed"):
            proxy_with_servers.forward(request)
