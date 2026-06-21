import threading
import time

import pytest

from solocoder_py.memoize import (
    MemoizeError,
    NotAFunctionError,
    UnhashableArgumentError,
    memoize,
)


class TestCacheKeyGeneration:
    def test_same_positional_args_hit_same_cache(self):
        call_count = 0

        @memoize
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3
        assert call_count == 1

    def test_positional_and_keyword_args_hit_same_cache(self):
        call_count = 0

        @memoize
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert add(a=1, b=2) == 3
        assert call_count == 1

    def test_default_args_hit_same_cache(self):
        call_count = 0

        @memoize
        def add(a, b=2):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1) == 3
        assert add(1, 2) == 3
        assert add(1, b=2) == 3
        assert call_count == 1

    def test_different_args_independent_caches(self):
        call_count = 0

        @memoize
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert add(3, 4) == 7
        assert add(1, 2) == 3
        assert call_count == 2

    def test_different_functions_isolated_caches(self):
        call_count_a = 0
        call_count_b = 0

        @memoize
        def func_a(x):
            nonlocal call_count_a
            call_count_a += 1
            return x * 2

        @memoize
        def func_b(x):
            nonlocal call_count_b
            call_count_b += 1
            return x * 3

        assert func_a(5) == 10
        assert func_b(5) == 15
        assert call_count_a == 1
        assert call_count_b == 1


class TestUnhashableArguments:
    def test_list_argument_cached(self):
        call_count = 0

        @memoize
        def sum_list(items):
            nonlocal call_count
            call_count += 1
            return sum(items)

        assert sum_list([1, 2, 3]) == 6
        assert sum_list([1, 2, 3]) == 6
        assert call_count == 1

    def test_list_and_tuple_hit_same_cache(self):
        call_count = 0

        @memoize
        def sum_list(items):
            nonlocal call_count
            call_count += 1
            return sum(items)

        assert sum_list([1, 2, 3]) == 6
        assert sum_list((1, 2, 3)) == 6
        assert call_count == 1

    def test_dict_argument_cached(self):
        call_count = 0

        @memoize
        def get_value(d, key):
            nonlocal call_count
            call_count += 1
            return d.get(key)

        assert get_value({"a": 1, "b": 2}, "a") == 1
        assert get_value({"a": 1, "b": 2}, "a") == 1
        assert call_count == 1

    def test_dict_key_order_independent(self):
        call_count = 0

        @memoize
        def process(d):
            nonlocal call_count
            call_count += 1
            return sum(d.values())

        assert process({"a": 1, "b": 2}) == 3
        assert process({"b": 2, "a": 1}) == 3
        assert call_count == 1

    def test_nested_unhashable_args(self):
        call_count = 0

        @memoize
        def nested(data):
            nonlocal call_count
            call_count += 1
            return len(data["items"])

        data = {"items": [1, 2, 3], "meta": {"count": 3}}
        assert nested(data) == 3
        assert nested(data) == 3
        assert call_count == 1

    def test_set_argument_cached(self):
        call_count = 0

        @memoize
        def get_set_size(s):
            nonlocal call_count
            call_count += 1
            return len(s)

        assert get_set_size({1, 2, 3}) == 3
        assert get_set_size({3, 2, 1}) == 3
        assert call_count == 1

    def test_custom_unhashable_raises(self):
        class Unhashable:
            __hash__ = None

        @memoize
        def process(obj):
            return obj

        with pytest.raises(UnhashableArgumentError):
            process(Unhashable())


class TestTTLExpiration:
    def test_expired_entry_recomputed(self):
        call_count = 0

        @memoize(ttl=0.05)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(10) == 20
        assert compute(10) == 20
        assert call_count == 1

        time.sleep(0.1)
        assert compute(10) == 20
        assert call_count == 2

    def test_non_expired_entry_not_recomputed(self):
        call_count = 0

        @memoize(ttl=10)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(10) == 20
        assert compute(10) == 20
        assert call_count == 1

    def test_ttl_zero_never_expires(self):
        call_count = 0

        @memoize(ttl=0)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(10) == 20
        time.sleep(0.05)
        assert compute(10) == 20
        assert call_count == 1

    def test_default_ttl_zero_never_expires(self):
        call_count = 0

        @memoize
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(10) == 20
        time.sleep(0.05)
        assert compute(10) == 20
        assert call_count == 1

    def test_expired_entry_updates_created_at(self):
        call_count = 0

        @memoize(ttl=0.05)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(10)
        time.sleep(0.1)
        compute(10)
        assert call_count == 2

        compute(10)
        assert call_count == 2


class TestLRUEviction:
    def test_evicts_lru_when_capacity_exceeded(self):
        call_count = 0

        @memoize(capacity=3)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(1)
        compute(2)
        compute(3)
        assert call_count == 3

        compute(4)
        assert call_count == 4

        compute(1)
        assert call_count == 5

        compute(2)
        compute(3)
        compute(4)
        assert call_count == 8

    def test_hit_updates_lru_order(self):
        call_count = 0

        @memoize(capacity=3)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(1)
        compute(2)
        compute(3)

        compute(1)

        compute(4)

        compute(1)
        compute(3)
        compute(4)
        assert call_count == 4

        compute(2)
        assert call_count == 5

    def test_capacity_one_eviction(self):
        call_count = 0

        @memoize(capacity=1)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(1)
        assert call_count == 1

        compute(2)
        assert call_count == 2

        compute(1)
        assert call_count == 3

        compute(2)
        assert call_count == 4

    def test_capacity_zero_no_eviction(self):
        call_count = 0

        @memoize(capacity=0)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        for i in range(100):
            compute(i)
        assert call_count == 100

        for i in range(100):
            compute(i)
        assert call_count == 100

    def test_large_capacity_no_eviction(self):
        call_count = 0

        @memoize(capacity=1000)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        for i in range(10):
            compute(i)
        assert call_count == 10

        for i in range(10):
            compute(i)
        assert call_count == 10


class TestHitRateStatistics:
    def test_initial_hit_rate_zero(self):
        @memoize
        def compute(x):
            return x * 2

        assert compute.hit_rate() == 0.0

    def test_first_call_miss(self):
        @memoize
        def compute(x):
            return x * 2

        compute(1)
        assert compute.hit_rate() == 0.0

    def test_second_call_hit(self):
        @memoize
        def compute(x):
            return x * 2

        compute(1)
        compute(1)
        assert compute.hit_rate() == 0.5

    def test_hit_rate_calculation(self):
        @memoize
        def compute(x):
            return x * 2

        for i in range(5):
            compute(i)
        for i in range(3):
            compute(i)

        assert compute.hit_rate() == 3 / 8

    def test_reset_stats(self):
        @memoize
        def compute(x):
            return x * 2

        for i in range(5):
            compute(i)
        for i in range(3):
            compute(i)

        assert compute.hit_rate() > 0
        compute.reset_stats()
        assert compute.hit_rate() == 0.0

        info = compute.cache_info()
        assert info["total_accesses"] == 0
        assert info["hits"] == 0

    def test_cache_info(self):
        @memoize(capacity=10, ttl=5)
        def compute(x):
            return x * 2

        compute(1)
        compute(2)
        compute(1)

        info = compute.cache_info()
        assert info["size"] == 2
        assert info["capacity"] == 10
        assert info["ttl"] == 5
        assert info["total_accesses"] == 3
        assert info["hits"] == 1
        assert info["hit_rate"] == 1 / 3

    def test_cache_clear(self):
        call_count = 0

        @memoize
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(1)
        compute(1)
        assert call_count == 1

        compute.cache_clear()
        compute(1)
        assert call_count == 2


class TestReturnNone:
    def test_none_return_value_cached(self):
        call_count = 0

        @memoize
        def get_none(x):
            nonlocal call_count
            call_count += 1
            return None

        assert get_none(1) is None
        assert get_none(1) is None
        assert call_count == 1

    def test_none_returns_counted_as_hit(self):
        @memoize
        def get_none(x):
            return None

        get_none(1)
        get_none(1)
        assert get_none.hit_rate() == 0.5


class TestVariableArguments:
    def test_var_args_cached(self):
        call_count = 0

        @memoize
        def sum_all(*args):
            nonlocal call_count
            call_count += 1
            return sum(args)

        assert sum_all(1, 2, 3) == 6
        assert sum_all(1, 2, 3) == 6
        assert call_count == 1

    def test_var_kwargs_cached(self):
        call_count = 0

        @memoize
        def concat(**kwargs):
            nonlocal call_count
            call_count += 1
            return ", ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

        assert concat(a=1, b=2) == "a=1, b=2"
        assert concat(b=2, a=1) == "a=1, b=2"
        assert call_count == 1

    def test_mixed_var_args_kwargs(self):
        call_count = 0

        @memoize
        def mixed(a, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (a, args, tuple(sorted(kwargs.items())))

        result1 = mixed(1, 2, 3, x=4, y=5)
        result2 = mixed(1, 2, 3, y=5, x=4)
        assert result1 == result2
        assert call_count == 1


class TestEdgeCases:
    def test_kwargs_order_independent(self):
        call_count = 0

        @memoize
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(a=1, b=2) == 3
        assert add(b=2, a=1) == 3
        assert call_count == 1

    def test_args_with_different_types(self):
        call_count = 0

        @memoize
        def identity(x):
            nonlocal call_count
            call_count += 1
            return x

        assert identity(1) == 1
        assert identity(1.0) == 1.0
        assert call_count == 1

    def test_boolean_args(self):
        call_count = 0

        @memoize
        def negate(b):
            nonlocal call_count
            call_count += 1
            return not b

        assert negate(True) is False
        assert negate(True) is False
        assert negate(False) is True
        assert call_count == 2

    def test_empty_args(self):
        call_count = 0

        @memoize
        def get_constant():
            nonlocal call_count
            call_count += 1
            return 42

        assert get_constant() == 42
        assert get_constant() == 42
        assert call_count == 1


class TestExceptionBranches:
    def test_decorate_non_function_raises(self):
        with pytest.raises(NotAFunctionError):
            memoize(42)

        with pytest.raises(NotAFunctionError):
            memoize("not a function")

        with pytest.raises(NotAFunctionError):
            @memoize
            class NotAFunction:
                pass

    def test_negative_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl must be non-negative"):
            memoize(ttl=-1)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity must be non-negative"):
            memoize(capacity=-1)

    def test_memoize_error_base_class(self):
        assert issubclass(UnhashableArgumentError, MemoizeError)
        assert issubclass(NotAFunctionError, MemoizeError)


class TestTTLAndLRUInteraction:
    def test_expired_entry_evicted_before_lru(self):
        call_count = 0

        @memoize(capacity=2, ttl=0.05)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(1)
        compute(2)

        time.sleep(0.1)

        compute(3)

        info = compute.cache_info()
        assert info["size"] <= 2

        compute(1)
        assert call_count == 4

    def test_both_ttl_and_lru_triggered(self):
        call_count = 0

        @memoize(capacity=2, ttl=0.05)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(1)
        compute(2)
        compute(1)

        time.sleep(0.1)

        compute(3)
        compute(2)

        assert call_count >= 4

    def test_expired_entry_replaced_with_new_value(self):
        call_count = 0

        @memoize(capacity=2, ttl=0.05)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * call_count

        result1 = compute(1)
        assert result1 == 1

        time.sleep(0.1)

        result2 = compute(1)
        assert result2 == 2
        assert result1 != result2


class TestMethodDecoration:
    def test_instance_method_decoration(self):
        call_count = 0

        class Counter:
            @memoize
            def add(self, a, b):
                nonlocal call_count
                call_count += 1
                return a + b

        c = Counter()
        assert c.add(1, 2) == 3
        assert c.add(1, 2) == 3
        assert call_count == 1

    def test_different_instances_isolated(self):
        call_count = 0

        class Counter:
            def __init__(self, multiplier):
                self.multiplier = multiplier

            @memoize
            def multiply(self, x):
                nonlocal call_count
                call_count += 1
                return x * self.multiplier

        c1 = Counter(2)
        c2 = Counter(3)

        assert c1.multiply(5) == 10
        assert c2.multiply(5) == 15
        assert call_count == 2

        c1.multiply(5)
        c2.multiply(5)
        assert call_count == 2

    def test_method_hit_rate(self):
        class Calculator:
            @memoize
            def square(self, x):
                return x * x

        calc = Calculator()
        calc.square(2)
        calc.square(2)
        calc.square(3)

        assert calc.square.hit_rate() == 1 / 3
        calc.square.reset_stats()
        assert calc.square.hit_rate() == 0.0


class TestConcurrentAccess:
    def test_concurrent_reads_and_writes(self):
        @memoize(capacity=100)
        def compute(x):
            return x * 2

        errors = []

        def reader():
            try:
                for i in range(50):
                    compute(i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_hit_rate_consistency(self):
        @memoize(capacity=100)
        def compute(x):
            return x * 2

        for i in range(10):
            compute(i)

        def access():
            for i in range(10):
                compute(i)

        threads = [threading.Thread(target=access) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        info = compute.cache_info()
        assert info["total_accesses"] == 10 + 5 * 10
        assert info["hits"] == 5 * 10
        assert info["hit_rate"] == (5 * 10) / (10 + 5 * 10)
