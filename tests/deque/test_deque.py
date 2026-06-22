import pytest

from solocoder_py.deque import Deque, DequeEmptyError, DequeIndexError


class TestAddOperations:
    def test_add_front_single_element(self, deque: Deque):
        deque.add_front(1)
        assert deque.size() == 1
        assert deque.peek_front() == 1
        assert deque.peek_rear() == 1

    def test_add_rear_single_element(self, deque: Deque):
        deque.add_rear(1)
        assert deque.size() == 1
        assert deque.peek_front() == 1
        assert deque.peek_rear() == 1

    def test_add_front_multiple_elements(self, deque: Deque):
        deque.add_front(1)
        deque.add_front(2)
        deque.add_front(3)
        assert deque.size() == 3
        assert deque.peek_front() == 3
        assert deque.peek_rear() == 1

    def test_add_rear_multiple_elements(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        assert deque.size() == 3
        assert deque.peek_front() == 1
        assert deque.peek_rear() == 3

    def test_add_front_and_rear_mixed(self, deque: Deque):
        deque.add_front(2)
        deque.add_rear(3)
        deque.add_front(1)
        deque.add_rear(4)
        assert deque.size() == 4
        assert deque.peek_front() == 1
        assert deque.peek_rear() == 4

    def test_add_different_types(self, deque: Deque):
        deque.add_front(1)
        deque.add_rear("hello")
        deque.add_front(3.14)
        deque.add_rear([1, 2, 3])
        assert deque.size() == 4
        assert deque.peek_front() == 3.14
        assert deque.peek_rear() == [1, 2, 3]


class TestRemoveOperations:
    def test_remove_front_single_element(self, deque: Deque):
        deque.add_front(1)
        result = deque.remove_front()
        assert result == 1
        assert deque.is_empty() is True

    def test_remove_rear_single_element(self, deque: Deque):
        deque.add_rear(1)
        result = deque.remove_rear()
        assert result == 1
        assert deque.is_empty() is True

    def test_remove_front_order(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        assert deque.remove_front() == 1
        assert deque.remove_front() == 2
        assert deque.remove_front() == 3
        assert deque.is_empty() is True

    def test_remove_rear_order(self, deque: Deque):
        deque.add_front(1)
        deque.add_front(2)
        deque.add_front(3)
        assert deque.remove_rear() == 1
        assert deque.remove_rear() == 2
        assert deque.remove_rear() == 3
        assert deque.is_empty() is True

    def test_mixed_add_and_remove(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        assert deque.remove_front() == 1
        deque.add_rear(4)
        assert deque.remove_rear() == 4
        assert deque.remove_front() == 2
        assert deque.remove_rear() == 3
        assert deque.is_empty() is True

    def test_alternate_removal(self, deque: Deque):
        for i in range(1, 7):
            deque.add_rear(i)
        assert deque.remove_front() == 1
        assert deque.remove_rear() == 6
        assert deque.remove_front() == 2
        assert deque.remove_rear() == 5
        assert deque.remove_front() == 3
        assert deque.remove_rear() == 4
        assert deque.is_empty() is True


class TestIndexAccess:
    def test_getitem_valid_index(self, deque: Deque):
        deque.add_rear(10)
        deque.add_rear(20)
        deque.add_rear(30)
        assert deque[0] == 10
        assert deque[1] == 20
        assert deque[2] == 30

    def test_getitem_after_add_front(self, deque: Deque):
        deque.add_rear(20)
        deque.add_front(10)
        deque.add_rear(30)
        assert deque[0] == 10
        assert deque[1] == 20
        assert deque[2] == 30

    def test_setitem_valid_index(self, deque: Deque):
        deque.add_rear(10)
        deque.add_rear(20)
        deque.add_rear(30)
        deque[1] = 200
        assert deque[1] == 200
        assert deque[0] == 10
        assert deque[2] == 30

    def test_getitem_negative_index_raises(self, deque: Deque):
        deque.add_rear(10)
        with pytest.raises(DequeIndexError):
            deque[-1]

    def test_getitem_index_equal_to_size_raises(self, deque: Deque):
        deque.add_rear(10)
        deque.add_rear(20)
        with pytest.raises(DequeIndexError):
            deque[2]

    def test_getitem_index_greater_than_size_raises(self, deque: Deque):
        deque.add_rear(10)
        with pytest.raises(DequeIndexError):
            deque[5]

    def test_setitem_negative_index_raises(self, deque: Deque):
        deque.add_rear(10)
        with pytest.raises(DequeIndexError):
            deque[-1] = 100

    def test_setitem_index_equal_to_size_raises(self, deque: Deque):
        deque.add_rear(10)
        with pytest.raises(DequeIndexError):
            deque[1] = 100

    def test_getitem_empty_deque_raises(self, deque: Deque):
        with pytest.raises(DequeIndexError):
            deque[0]

    def test_setitem_empty_deque_raises(self, deque: Deque):
        with pytest.raises(DequeIndexError):
            deque[0] = 100

    def test_getitem_non_integer_raises_type_error(self, deque: Deque):
        deque.add_rear(10)
        with pytest.raises(TypeError):
            deque["0"]

    def test_setitem_non_integer_raises_type_error(self, deque: Deque):
        deque.add_rear(10)
        with pytest.raises(TypeError):
            deque["0"] = 100


class TestIterator:
    def test_iterate_empty_deque(self, deque: Deque):
        result = list(deque)
        assert result == []

    def test_iterate_single_element(self, deque: Deque):
        deque.add_rear(42)
        result = list(deque)
        assert result == [42]

    def test_iterate_multiple_elements(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        deque.add_rear(4)
        deque.add_rear(5)
        result = list(deque)
        assert result == [1, 2, 3, 4, 5]

    def test_iterate_after_add_front(self, deque: Deque):
        deque.add_front(3)
        deque.add_front(2)
        deque.add_front(1)
        result = list(deque)
        assert result == [1, 2, 3]

    def test_iterate_after_mixed_operations(self, deque: Deque):
        deque.add_rear(2)
        deque.add_front(1)
        deque.add_rear(3)
        deque.remove_front()
        deque.add_front(0)
        result = list(deque)
        assert result == [0, 2, 3]

    def test_for_loop_iteration(self, deque: Deque):
        deque.add_rear("a")
        deque.add_rear("b")
        deque.add_rear("c")
        collected = []
        for item in deque:
            collected.append(item)
        assert collected == ["a", "b", "c"]

    def test_iterator_independence(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        iter1 = iter(deque)
        iter2 = iter(deque)
        assert next(iter1) == 1
        assert next(iter1) == 2
        assert next(iter2) == 1
        assert next(iter1) == 3
        assert next(iter2) == 2
        assert next(iter2) == 3


class TestQueryOperations:
    def test_is_empty_new_deque(self, deque: Deque):
        assert deque.is_empty() is True
        assert deque.size() == 0

    def test_is_empty_after_add(self, deque: Deque):
        deque.add_front(1)
        assert deque.is_empty() is False
        assert deque.size() == 1

    def test_is_empty_after_remove(self, deque: Deque):
        deque.add_front(1)
        deque.remove_front()
        assert deque.is_empty() is True
        assert deque.size() == 0

    def test_size_after_multiple_operations(self, deque: Deque):
        deque.add_front(1)
        deque.add_rear(2)
        deque.add_front(3)
        assert deque.size() == 3
        deque.remove_front()
        assert deque.size() == 2
        deque.remove_rear()
        assert deque.size() == 1
        deque.remove_front()
        assert deque.size() == 0

    def test_len_dunder(self, deque: Deque):
        assert len(deque) == 0
        deque.add_rear(1)
        assert len(deque) == 1
        deque.add_rear(2)
        assert len(deque) == 2

    def test_contains(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        assert 2 in deque
        assert 4 not in deque
        assert "hello" not in deque


class TestPeekOperations:
    def test_peek_front_does_not_remove(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        assert deque.peek_front() == 1
        assert deque.peek_front() == 1
        assert deque.size() == 2

    def test_peek_rear_does_not_remove(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        assert deque.peek_rear() == 2
        assert deque.peek_rear() == 2
        assert deque.size() == 2

    def test_peek_front_empty_deque_raises(self, deque: Deque):
        with pytest.raises(DequeEmptyError):
            deque.peek_front()

    def test_peek_rear_empty_deque_raises(self, deque: Deque):
        with pytest.raises(DequeEmptyError):
            deque.peek_rear()


class TestEmptyDequeExceptions:
    def test_remove_front_empty_raises(self, deque: Deque):
        with pytest.raises(DequeEmptyError, match="Cannot remove from an empty deque"):
            deque.remove_front()

    def test_remove_rear_empty_raises(self, deque: Deque):
        with pytest.raises(DequeEmptyError, match="Cannot remove from an empty deque"):
            deque.remove_rear()

    def test_remove_front_after_all_removed_raises(self, deque: Deque):
        deque.add_front(1)
        deque.remove_front()
        with pytest.raises(DequeEmptyError):
            deque.remove_front()

    def test_remove_rear_after_all_removed_raises(self, deque: Deque):
        deque.add_rear(1)
        deque.remove_rear()
        with pytest.raises(DequeEmptyError):
            deque.remove_rear()

    def test_exception_hierarchy(self, deque: Deque):
        try:
            deque.remove_front()
        except DequeEmptyError as e:
            assert isinstance(e, DequeEmptyError)
        try:
            deque[0]
        except DequeIndexError as e:
            assert isinstance(e, DequeIndexError)
            assert isinstance(e, IndexError)


class TestSingleElementOperations:
    def test_single_element_add_front_remove_front(self, deque: Deque):
        deque.add_front("only")
        assert deque.size() == 1
        assert deque.peek_front() == "only"
        assert deque.peek_rear() == "only"
        assert deque.remove_front() == "only"
        assert deque.is_empty() is True

    def test_single_element_add_front_remove_rear(self, deque: Deque):
        deque.add_front("only")
        assert deque.remove_rear() == "only"
        assert deque.is_empty() is True

    def test_single_element_add_rear_remove_front(self, deque: Deque):
        deque.add_rear("only")
        assert deque.remove_front() == "only"
        assert deque.is_empty() is True

    def test_single_element_add_rear_remove_rear(self, deque: Deque):
        deque.add_rear("only")
        assert deque.remove_rear() == "only"
        assert deque.is_empty() is True

    def test_single_element_index_access(self, deque: Deque):
        deque.add_rear(42)
        assert deque[0] == 42
        deque[0] = 100
        assert deque[0] == 100
        assert deque.remove_front() == 100

    def test_single_element_iterator(self, deque: Deque):
        deque.add_rear("test")
        items = list(deque)
        assert items == ["test"]


class TestLargeNumberOfElements:
    def test_large_add_rear_remove_front_order(self, deque: Deque):
        n = 1000
        for i in range(n):
            deque.add_rear(i)
        assert deque.size() == n
        for i in range(n):
            assert deque.remove_front() == i
        assert deque.is_empty() is True

    def test_large_add_front_remove_rear_order(self, deque: Deque):
        n = 1000
        for i in range(n):
            deque.add_front(i)
        assert deque.size() == n
        for i in range(n):
            assert deque.remove_rear() == i
        assert deque.is_empty() is True

    def test_large_add_rear_remove_rear_order(self, deque: Deque):
        n = 1000
        for i in range(n):
            deque.add_rear(i)
        assert deque.size() == n
        for i in range(n - 1, -1, -1):
            assert deque.remove_rear() == i
        assert deque.is_empty() is True

    def test_large_add_front_remove_front_order(self, deque: Deque):
        n = 1000
        for i in range(n):
            deque.add_front(i)
        assert deque.size() == n
        for i in range(n - 1, -1, -1):
            assert deque.remove_front() == i
        assert deque.is_empty() is True

    def test_large_mixed_operations(self, deque: Deque):
        n = 500
        for i in range(n):
            deque.add_rear(i)
        for i in range(n):
            deque.add_front(i + n)
        assert deque.size() == 2 * n
        for i in range(2 * n - 1, n - 1, -1):
            assert deque.remove_front() == i
        for i in range(n - 1, -1, -1):
            assert deque.remove_rear() == i
        assert deque.is_empty() is True

    def test_large_index_access(self, deque: Deque):
        n = 1000
        for i in range(n):
            deque.add_rear(i * 10)
        for i in range(n):
            assert deque[i] == i * 10
        for i in range(n):
            deque[i] = i * 20
        for i in range(n):
            assert deque[i] == i * 20

    def test_large_iterator(self, deque: Deque):
        n = 1000
        expected = list(range(n))
        for i in expected:
            deque.add_rear(i)
        result = list(deque)
        assert result == expected


class TestClearOperation:
    def test_clear_empty_deque(self, deque: Deque):
        deque.clear()
        assert deque.is_empty() is True
        assert deque.size() == 0

    def test_clear_non_empty_deque(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        deque.clear()
        assert deque.is_empty() is True
        assert deque.size() == 0

    def test_clear_then_add(self, deque: Deque):
        deque.add_rear(1)
        deque.clear()
        deque.add_rear(2)
        assert deque.size() == 1
        assert deque.peek_front() == 2


class TestStringRepresentation:
    def test_repr_empty(self, deque: Deque):
        assert repr(deque) == "Deque([])"

    def test_repr_with_elements(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        deque.add_rear(3)
        assert repr(deque) == "Deque([1, 2, 3])"

    def test_str_empty(self, deque: Deque):
        assert str(deque) == "[]"

    def test_str_with_elements(self, deque: Deque):
        deque.add_rear(1)
        deque.add_rear(2)
        assert str(deque) == "[1, 2]"


class TestPalindromeUseCase:
    def test_palindrome_check_even_length(self, deque: Deque):
        word = "abba"
        for char in word:
            deque.add_rear(char)
        while deque.size() > 1:
            assert deque.remove_front() == deque.remove_rear()
        assert deque.size() <= 1

    def test_palindrome_check_odd_length(self, deque: Deque):
        word = "racecar"
        for char in word:
            deque.add_rear(char)
        while deque.size() > 1:
            assert deque.remove_front() == deque.remove_rear()
        assert deque.size() == 1

    def test_non_palindrome_check(self, deque: Deque):
        word = "hello"
        for char in word:
            deque.add_rear(char)
        is_palindrome = True
        while deque.size() > 1:
            if deque.remove_front() != deque.remove_rear():
                is_palindrome = False
                break
        assert is_palindrome is False
