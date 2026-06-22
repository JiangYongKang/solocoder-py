import pytest

from solocoder_py.stack import Stack, StackEmptyError, StackError


class TestPushPopOrder:
    def test_push_single_pop_single(self, stack: Stack):
        stack.push(42)
        assert stack.pop() == 42

    def test_push_multiple_pop_lifo_order(self, stack: Stack):
        stack.push("first")
        stack.push("second")
        stack.push("third")

        assert stack.pop() == "third"
        assert stack.pop() == "second"
        assert stack.pop() == "first"

    def test_push_various_types(self, stack: Stack):
        stack.push(1)
        stack.push("hello")
        stack.push(3.14)
        stack.push([1, 2, 3])
        stack.push({"key": "value"})

        assert stack.pop() == {"key": "value"}
        assert stack.pop() == [1, 2, 3]
        assert stack.pop() == 3.14
        assert stack.pop() == "hello"
        assert stack.pop() == 1

    def test_push_none_value(self, stack: Stack):
        stack.push(None)
        assert stack.size() == 1
        assert stack.peek() is None
        assert stack.pop() is None


class TestPeekOperation:
    def test_peek_returns_top_without_removing(self, stack: Stack):
        stack.push("a")
        stack.push("b")

        assert stack.peek() == "b"
        assert stack.size() == 2
        assert stack.peek() == "b"

    def test_peek_after_push_pop(self, stack: Stack):
        stack.push(1)
        stack.push(2)
        stack.pop()

        assert stack.peek() == 1


class TestIsEmpty:
    def test_new_stack_is_empty(self, stack: Stack):
        assert stack.is_empty() is True

    def test_stack_not_empty_after_push(self, stack: Stack):
        stack.push("item")
        assert stack.is_empty() is False

    def test_stack_empty_after_pop_all(self, stack: Stack):
        stack.push(1)
        stack.push(2)
        stack.pop()
        stack.pop()
        assert stack.is_empty() is True


class TestSize:
    def test_new_stack_size_zero(self, stack: Stack):
        assert stack.size() == 0

    def test_size_increments_with_push(self, stack: Stack):
        stack.push(1)
        assert stack.size() == 1
        stack.push(2)
        assert stack.size() == 2
        stack.push(3)
        assert stack.size() == 3

    def test_size_decrements_with_pop(self, stack: Stack):
        stack.push(1)
        stack.push(2)
        stack.push(3)
        stack.pop()
        assert stack.size() == 2
        stack.pop()
        assert stack.size() == 1
        stack.pop()
        assert stack.size() == 0


class TestEmptyStackExceptions:
    def test_pop_empty_stack_raises(self, stack: Stack):
        with pytest.raises(StackEmptyError) as exc_info:
            stack.pop()
        assert "empty stack" in str(exc_info.value).lower()

    def test_peek_empty_stack_raises(self, stack: Stack):
        with pytest.raises(StackEmptyError) as exc_info:
            stack.peek()
        assert "empty stack" in str(exc_info.value).lower()

    def test_stack_empty_error_is_stack_error(self, stack: Stack):
        with pytest.raises(StackError):
            stack.pop()
        with pytest.raises(StackError):
            stack.peek()


class TestLargeScaleOperations:
    def test_push_large_number_then_pop_all(self, stack: Stack):
        n = 1000
        for i in range(n):
            stack.push(i)

        assert stack.size() == n

        for i in range(n - 1, -1, -1):
            assert stack.pop() == i

        assert stack.is_empty() is True
        assert stack.size() == 0

    def test_push_large_strings(self, stack: Stack):
        long_str = "x" * 10000
        stack.push(long_str)
        assert stack.pop() == long_str


class TestAlternatingPushPop:
    def test_alternating_push_pop_single(self, stack: Stack):
        stack.push(1)
        assert stack.pop() == 1
        stack.push(2)
        assert stack.pop() == 2
        assert stack.is_empty() is True

    def test_alternating_push_pop_mixed(self, stack: Stack):
        stack.push(1)
        stack.push(2)
        assert stack.pop() == 2
        stack.push(3)
        assert stack.pop() == 3
        assert stack.pop() == 1
        assert stack.is_empty() is True

    def test_alternating_push_pop_sequence(self, stack: Stack):
        result = []
        stack.push(1)
        stack.push(2)
        result.append(stack.pop())
        stack.push(3)
        result.append(stack.pop())
        stack.push(4)
        stack.push(5)
        result.append(stack.pop())
        result.append(stack.pop())
        result.append(stack.pop())

        assert result == [2, 3, 5, 4, 1]
        assert stack.is_empty() is True
        assert stack.size() == 0

    def test_push_peek_pop_alternating(self, stack: Stack):
        stack.push("a")
        assert stack.peek() == "a"
        stack.push("b")
        assert stack.peek() == "b"
        assert stack.pop() == "b"
        assert stack.peek() == "a"
        stack.push("c")
        assert stack.peek() == "c"
