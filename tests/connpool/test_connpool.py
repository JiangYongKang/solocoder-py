import pytest
import threading
import time

from solocoder_py.connpool import (
    ConnectionPool,
    ConnectionState,
    ConnPoolError,
    HealthCheckFailedError,
    ManualClock,
    MockTCPConnection,
    PoolClosedError,
    PoolConfig,
    PoolExhaustedError,
    PoolStats,
    PoolWaitStrategy,
    ConnectionNotFoundError,
    ConnectionClosedError,
    RealClock,
)
from .conftest import make_pool, make_config, make_clock


class TestMockTCPConnection:
    def test_connection_creation(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        assert conn.host == "localhost"
        assert conn.port == 6379
        assert conn.conn_id is not None
        assert conn.state == ConnectionState.IDLE
        assert conn.is_closed is False
        assert conn.is_healthy is True

    def test_connection_close(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        assert conn.is_closed is False
        conn.close()
        assert conn.is_closed is True
        assert conn.is_healthy is False
        assert conn.state == ConnectionState.CLOSED

    def test_connection_close_idempotent(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        conn.close()
        conn.close()
        assert conn.is_closed is True

    def test_connection_health_toggle(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        assert conn.health_check() is True
        conn.set_unhealthy()
        assert conn.health_check() is False
        assert conn.is_healthy is False
        conn.set_healthy()
        assert conn.health_check() is True
        assert conn.is_healthy is True

    def test_closed_connection_unhealthy(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        conn.close()
        assert conn.health_check() is False

    def test_send_recv_healthy(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        conn.connect()
        conn.send(b"test")
        resp = conn.recv()
        assert resp == b"mock-response"

    def test_send_unhealthy_raises(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        conn.set_unhealthy()
        with pytest.raises(HealthCheckFailedError):
            conn.send(b"test")

    def test_send_closed_raises(self):
        conn = MockTCPConnection(host="localhost", port=6379)
        conn.close()
        with pytest.raises(ConnectionClosedError):
            conn.send(b"test")


class TestPoolConfig:
    def test_default_config(self):
        config = PoolConfig()
        assert config.max_size == 10
        assert config.wait_strategy == PoolWaitStrategy.BLOCK
        assert config.wait_timeout == 5.0
        assert config.idle_timeout == 60.0
        assert config.eviction_interval == 30.0
        assert config.max_lifetime == 300.0
        assert config.health_check_on_borrow is True

    def test_pool_stats_initial(self):
        stats = PoolStats()
        assert stats.total_connections == 0
        assert stats.idle_connections == 0
        assert stats.borrowed_connections == 0
        assert stats.active_connections == 0


class TestConnectionPoolBasic:
    def test_pool_creation(self):
        pool, clock = make_pool()
        assert pool.host == "localhost"
        assert pool.port == 6379
        assert pool.is_closed is False
        assert pool.size() == 0
        assert pool.idle_size() == 0
        assert pool.borrowed_size() == 0

    def test_borrow_first_creates_new(self):
        pool, clock = make_pool()
        conn = pool.borrow()
        assert conn is not None
        assert conn.state == ConnectionState.BORROWED
        assert pool.size() == 1
        assert pool.borrowed_size() == 1
        assert pool.idle_size() == 0
        assert pool.stats.borrow_count == 1
        assert pool.stats.total_connections == 1

    def test_return_and_reborrow_same_connection(self):
        pool, clock = make_pool()
        conn1 = pool.borrow()
        conn_id = conn1.conn_id
        pool.return_conn(conn1)

        assert pool.idle_size() == 1
        assert pool.borrowed_size() == 0

        conn2 = pool.borrow()
        assert conn2.conn_id == conn_id
        assert pool.idle_size() == 0
        assert pool.borrowed_size() == 1
        assert pool.stats.return_count == 1
        assert pool.stats.borrow_count == 2

    def test_borrow_multiple_up_to_max(self):
        config = make_config(max_size=3)
        pool, clock = make_pool(config=config)

        conns = []
        for i in range(3):
            conn = pool.borrow()
            conns.append(conn)

        assert pool.size() == 3
        assert pool.borrowed_size() == 3
        assert pool.idle_size() == 0
        assert pool.stats.total_connections == 3

    def test_borrow_exceeds_max_fail_strategy(self):
        config = make_config(max_size=2, wait_strategy=PoolWaitStrategy.FAIL)
        pool, clock = make_pool(config=config)

        conn1 = pool.borrow()
        conn2 = pool.borrow()

        with pytest.raises(PoolExhaustedError):
            pool.borrow()

        assert pool.size() == 2

    def test_max_size_zero_borrow_fail(self):
        config = make_config(max_size=0, wait_strategy=PoolWaitStrategy.FAIL)
        pool, clock = make_pool(config=config)

        assert pool.size() == 0
        assert pool.config.max_size == 0

        with pytest.raises(PoolExhaustedError):
            pool.borrow()

        assert pool.size() == 0
        assert pool.stats.total_connections == 0
        pool.close()

    def test_max_size_zero_block_timeout(self):
        config = make_config(max_size=0, wait_strategy=PoolWaitStrategy.BLOCK, wait_timeout=0.1)
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        assert pool.size() == 0

        start = time.monotonic()
        with pytest.raises(PoolExhaustedError):
            pool.borrow()
        elapsed = time.monotonic() - start

        assert elapsed >= 0.09
        assert pool.size() == 0
        pool.close()

    def test_max_size_negative_rejected(self):
        config = make_config(max_size=-1)
        with pytest.raises(ValueError, match="max_size cannot be negative"):
            make_pool(config=config)

    def test_return_all_and_close(self):
        config = make_config(max_size=5)
        pool, clock = make_pool(config=config)

        conns = [pool.borrow() for _ in range(3)]
        for conn in conns:
            pool.return_conn(conn)

        assert pool.idle_size() == 3
        assert pool.borrowed_size() == 0

        pool.close()
        assert pool.is_closed is True
        assert pool.size() == 0
        assert pool.idle_size() == 0
        assert pool.borrowed_size() == 0
        assert pool.stats.closed_connections == 3

    def test_close_pool_with_borrowed_connections(self):
        pool, clock = make_pool()
        conn = pool.borrow()

        pool.close()
        assert pool.is_closed is True
        assert pool.size() == 0
        assert conn.is_closed is True

    def test_close_idempotent(self):
        pool, clock = make_pool()
        pool.close()
        pool.close()
        assert pool.is_closed is True

    def test_borrow_from_closed_pool(self):
        pool, clock = make_pool()
        pool.close()
        with pytest.raises(PoolClosedError):
            pool.borrow()

    def test_return_unknown_connection_raises(self):
        pool, clock = make_pool()
        other_conn = MockTCPConnection(host="other", port=1234)
        with pytest.raises(ConnectionNotFoundError):
            pool.return_conn(other_conn)

    def test_context_manager(self):
        config = make_config()
        clock = make_clock()
        with ConnectionPool("localhost", 6379, config, clock) as pool:
            assert pool.is_closed is False
            conn = pool.borrow()
            pool.return_conn(conn)
        assert pool.is_closed is True


class TestPoolExhaustedBlocking:
    def test_block_wait_and_return(self):
        config = PoolConfig(
            max_size=1, wait_strategy=PoolWaitStrategy.BLOCK, wait_timeout=2.0,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        conn1 = pool.borrow()
        result = {}
        errors = []

        def borrower():
            try:
                conn = pool.borrow(timeout=1.0)
                result["conn"] = conn
                pool.return_conn(conn)
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=borrower)
        t.start()

        time.sleep(0.1)
        pool.return_conn(conn1)
        t.join(timeout=2.0)

        assert not errors, f"Errors: {errors}"
        assert "conn" in result
        assert pool.borrowed_size() == 0
        pool.close()

    def test_block_timeout(self):
        config = PoolConfig(
            max_size=1, wait_strategy=PoolWaitStrategy.BLOCK, wait_timeout=0.2,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        conn1 = pool.borrow()

        start = time.monotonic()
        with pytest.raises(PoolExhaustedError):
            pool.borrow(timeout=0.1)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.09

        pool.return_conn(conn1)
        pool.close()

    def test_multiple_waiters_woken(self):
        config = PoolConfig(
            max_size=1, wait_strategy=PoolWaitStrategy.BLOCK, wait_timeout=2.0,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        conn = pool.borrow()
        order = []
        errors = []

        def make_borrower(name):
            def borrower():
                try:
                    c = pool.borrow(timeout=2.0)
                    order.append(name)
                    time.sleep(0.02)
                    pool.return_conn(c)
                except Exception as e:
                    errors.append((name, e))

            return borrower

        t1 = threading.Thread(target=make_borrower("A"))
        t2 = threading.Thread(target=make_borrower("B"))

        t1.start()
        time.sleep(0.05)
        t2.start()
        time.sleep(0.05)

        pool.return_conn(conn)

        t1.join(timeout=3.0)
        t2.join(timeout=3.0)

        assert not errors, f"Errors: {errors}"
        assert len(order) == 2
        pool.close()


class TestIdleEviction:
    def test_evict_idle_connections(self):
        config = make_config(
            max_size=5,
            idle_timeout=10.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn1 = pool.borrow()
        conn2 = pool.borrow()
        pool.return_conn(conn1)
        pool.return_conn(conn2)

        assert pool.idle_size() == 2

        clock.advance(5.0)
        pool.evict_now()
        assert pool.idle_size() == 2

        clock.advance(6.0)
        pool.evict_now()
        assert pool.idle_size() == 0
        assert pool.size() == 0
        assert pool.stats.evicted_count == 2

    def test_borrowed_connections_not_evicted(self):
        config = make_config(
            max_size=5,
            idle_timeout=10.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn1 = pool.borrow()
        conn2 = pool.borrow()
        pool.return_conn(conn1)

        assert pool.idle_size() == 1
        assert pool.borrowed_size() == 1

        clock.advance(15.0)
        pool.evict_now()

        assert pool.idle_size() == 0
        assert pool.borrowed_size() == 1
        assert pool.size() == 1
        assert pool.stats.evicted_count == 1
        assert conn2.is_closed is False

    def test_evict_after_return_reborrow(self):
        config = make_config(
            max_size=3,
            idle_timeout=10.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        pool.return_conn(conn)

        clock.advance(5.0)
        conn2 = pool.borrow()
        assert conn2.conn_id == conn.conn_id
        pool.return_conn(conn2)

        clock.advance(6.0)
        pool.evict_now()

        assert pool.idle_size() == 1
        assert pool.stats.evicted_count == 0

        clock.advance(5.0)
        pool.evict_now()
        assert pool.idle_size() == 0
        assert pool.stats.evicted_count == 1

    def test_eviction_zero_after_eviction(self):
        config = make_config(
            max_size=5,
            idle_timeout=5.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conns = []
        for _ in range(3):
            conn = pool.borrow()
            conns.append(conn)

        for conn in conns:
            pool.return_conn(conn)

        assert pool.idle_size() == 3

        clock.advance(10.0)
        pool.evict_now()

        assert pool.idle_size() == 0
        assert pool.size() == 0


class TestMaxLifetime:
    def test_return_expired_connection_discarded(self):
        config = make_config(
            max_size=5,
            max_lifetime=60.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        pool.return_conn(conn)

        assert pool.idle_size() == 1

        clock.advance(50.0)
        conn2 = pool.borrow()
        assert conn2.conn_id == conn.conn_id
        pool.return_conn(conn2)

        clock.advance(15.0)
        conn3 = pool.borrow()
        assert conn3.conn_id == conn.conn_id

        clock.advance(5.0)
        pool.return_conn(conn3)

        assert pool.idle_size() == 0
        assert pool.size() == 0
        assert conn3.is_closed is True
        assert pool.stats.closed_connections == 1

    def test_borrowed_connection_not_affected_by_lifetime(self):
        config = make_config(
            max_size=5,
            max_lifetime=30.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn = pool.borrow()

        clock.advance(60.0)
        assert conn.is_closed is False
        assert pool.borrowed_size() == 1

        pool.return_conn(conn)
        assert conn.is_closed is True
        assert pool.idle_size() == 0

    def test_max_lifetime_zero_disables(self):
        config = make_config(
            max_size=5,
            max_lifetime=0.0,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        clock.advance(1000.0)
        pool.return_conn(conn)

        assert pool.idle_size() == 1
        assert conn.is_closed is False


class TestHealthCheck:
    def test_borrow_unhealthy_connection_discarded(self):
        config = make_config(
            max_size=5,
            health_check_on_borrow=True,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn1 = pool.borrow()
        conn1.set_unhealthy()
        pool.return_conn(conn1)

        assert pool.idle_size() == 1

        conn2 = pool.borrow()
        assert conn2.conn_id != conn1.conn_id
        assert conn1.is_closed is True
        assert pool.idle_size() == 0
        assert pool.stats.health_check_failed_count == 1
        assert pool.stats.total_connections == 2

    def test_all_idle_unhealthy_creates_new(self):
        config = make_config(
            max_size=3,
            health_check_on_borrow=True,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conns = []
        for _ in range(2):
            conn = pool.borrow()
            conn.set_unhealthy()
            conns.append(conn)

        for conn in conns:
            pool.return_conn(conn)

        assert pool.idle_size() == 2

        conn = pool.borrow()
        assert all(c.conn_id != conn.conn_id for c in conns)
        assert all(c.is_closed for c in conns)
        assert pool.stats.health_check_failed_count == 2

    def test_health_check_disabled(self):
        config = make_config(
            max_size=5,
            health_check_on_borrow=False,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn1 = pool.borrow()
        conn1.set_unhealthy()
        pool.return_conn(conn1)

        conn2 = pool.borrow()
        assert conn2.conn_id == conn1.conn_id
        assert pool.stats.health_check_failed_count == 0

    def test_health_check_exception_safe(self):
        config = make_config(
            max_size=3,
            health_check_on_borrow=True,
            eviction_interval=0,
        )
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        pool.return_conn(conn)

        original_health_check = conn.health_check

        def broken_health_check():
            raise RuntimeError("boom")

        conn.health_check = broken_health_check

        conn2 = pool.borrow()
        assert conn2.conn_id != conn.conn_id
        assert conn.is_closed is True
        assert pool.stats.health_check_failed_count == 1

    def test_health_check_timeout(self):
        config = PoolConfig(
            max_size=5,
            health_check_on_borrow=True,
            health_check_timeout=0.1,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        conn1 = pool.borrow()
        conn1.set_health_check_delay(1.0)
        pool.return_conn(conn1)

        assert pool.idle_size() == 1

        start = time.monotonic()
        conn2 = pool.borrow()
        elapsed = time.monotonic() - start

        assert elapsed >= 0.09
        assert elapsed < 0.5
        assert conn2.conn_id != conn1.conn_id
        assert conn1.is_closed is True
        assert pool.stats.health_check_failed_count == 1

        pool.return_conn(conn2)
        pool.close()

    def test_health_check_timeout_parameter_used(self):
        config = PoolConfig(
            max_size=3,
            health_check_on_borrow=True,
            health_check_timeout=0.2,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        conn = pool.borrow()
        conn.set_health_check_delay(0.05)
        pool.return_conn(conn)

        conn2 = pool.borrow()
        assert conn2.conn_id == conn.conn_id
        assert pool.stats.health_check_failed_count == 0

        pool.return_conn(conn2)
        pool.close()


class TestReturnEdgeCases:
    def test_return_closed_connection(self):
        config = make_config(max_size=5, eviction_interval=0)
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        conn.close()
        pool.return_conn(conn)

        assert pool.idle_size() == 0
        assert pool.size() == 0
        assert conn.is_closed is True

    def test_return_already_returned_connection(self):
        config = make_config(max_size=5, eviction_interval=0)
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        pool.return_conn(conn)
        pool.return_conn(conn)

        assert pool.idle_size() == 1
        assert pool.stats.return_count == 1

    def test_return_to_closed_pool(self):
        config = make_config(max_size=5, eviction_interval=0)
        pool, clock = make_pool(config=config)

        conn = pool.borrow()
        pool.close()
        assert pool.is_closed is True

        pool.return_conn(conn)
        assert conn.is_closed is True
        assert pool.size() == 0


class TestConcurrentAccess:
    def test_concurrent_borrow_and_return(self):
        config = PoolConfig(
            max_size=5,
            wait_strategy=PoolWaitStrategy.BLOCK,
            wait_timeout=5.0,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        errors = []
        iterations = 20
        num_threads = 5

        def worker():
            for _ in range(iterations):
                try:
                    conn = pool.borrow()
                    time.sleep(0.001)
                    pool.return_conn(conn)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Errors: {errors[:5]}"
        assert pool.idle_size() <= config.max_size
        assert pool.size() <= config.max_size
        pool.close()

    def test_concurrent_close(self):
        config = PoolConfig(
            max_size=5,
            wait_strategy=PoolWaitStrategy.BLOCK,
            wait_timeout=1.0,
            eviction_interval=0,
        )
        pool = ConnectionPool(
            host="localhost", port=6379, config=config, clock=RealClock()
        )

        conns = [pool.borrow() for _ in range(3)]

        errors = []

        def closer():
            try:
                pool.close()
            except Exception as e:
                errors.append(e)

        def borrower():
            try:
                pool.borrow(timeout=0.5)
            except (PoolClosedError, PoolExhaustedError):
                pass
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=closer)
        t2 = threading.Thread(target=borrower)
        t3 = threading.Thread(target=borrower)

        t1.start()
        time.sleep(0.01)
        t2.start()
        t3.start()

        t1.join(timeout=2.0)
        t2.join(timeout=2.0)
        t3.join(timeout=2.0)

        assert not errors, f"Errors: {errors}"
        assert pool.is_closed is True


class TestEvictionThread:
    def test_eviction_thread_runs(self):
        config = make_config(
            max_size=5,
            idle_timeout=0.1,
            eviction_interval=0.05,
        )
        pool = ConnectionPool(
            host="localhost",
            port=6379,
            config=config,
            clock=RealClock(),
        )

        try:
            conn = pool.borrow()
            pool.return_conn(conn)

            assert pool.idle_size() == 1

            time.sleep(0.3)

            assert pool.idle_size() == 0
        finally:
            pool.close()
