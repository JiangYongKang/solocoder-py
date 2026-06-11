import pytest

from solocoder_py.undo_redo import (
    Command,
    CommandExecutionError,
    RedoStackEmptyError,
    UndoRedoStack,
    UndoStackEmptyError,
)


class TestBasicUndoRedo:
    def test_initial_state(self, stack):
        assert stack.can_undo is False
        assert stack.can_redo is False
        assert stack.undo_count == 0
        assert stack.redo_count == 0

    def test_execute_single_command(self, stack, counter, make_increment_command):
        cmd = make_increment_command(amount=5, name="inc5")
        result = stack.execute(cmd)

        assert result == 5
        assert counter["value"] == 5
        assert stack.can_undo is True
        assert stack.undo_count == 1
        assert stack.can_redo is False
        assert stack.redo_count == 0

    def test_execute_then_undo(self, stack, counter, make_increment_command):
        cmd = make_increment_command(amount=5, name="inc5")
        stack.execute(cmd)

        assert counter["value"] == 5
        assert stack.can_undo is True

        stack.undo()
        assert counter["value"] == 0
        assert stack.can_undo is False
        assert stack.can_redo is True
        assert stack.undo_count == 0
        assert stack.redo_count == 1

    def test_undo_then_redo(self, stack, counter, make_increment_command):
        cmd = make_increment_command(amount=10, name="inc10")
        stack.execute(cmd)

        assert counter["value"] == 10

        stack.undo()
        assert counter["value"] == 0
        assert stack.can_redo is True

        stack.redo()
        assert counter["value"] == 10
        assert stack.can_undo is True
        assert stack.can_redo is False
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_multiple_undo_and_redo(self, stack, counter, make_increment_command):
        cmd1 = make_increment_command(amount=1, name="inc1")
        cmd2 = make_increment_command(amount=2, name="inc2")
        cmd3 = make_increment_command(amount=3, name="inc3")

        stack.execute(cmd1)
        stack.execute(cmd2)
        stack.execute(cmd3)

        assert counter["value"] == 6
        assert stack.undo_count == 3

        stack.undo()
        assert counter["value"] == 3
        assert stack.undo_count == 2
        assert stack.redo_count == 1

        stack.undo()
        assert counter["value"] == 1
        assert stack.undo_count == 1
        assert stack.redo_count == 2

        stack.undo()
        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 3

        stack.redo()
        assert counter["value"] == 1
        assert stack.undo_count == 1
        assert stack.redo_count == 2

        stack.redo()
        assert counter["value"] == 3
        assert stack.undo_count == 2
        assert stack.redo_count == 1

        stack.redo()
        assert counter["value"] == 6
        assert stack.undo_count == 3
        assert stack.redo_count == 0

    def test_undo_stack_empty_raises(self, stack):
        with pytest.raises(UndoStackEmptyError, match="Cannot undo: undo stack is empty"):
            stack.undo()

    def test_redo_stack_empty_raises(self, stack):
        with pytest.raises(RedoStackEmptyError, match="Cannot redo: redo stack is empty"):
            stack.redo()

    def test_new_command_clears_redo_stack(self, stack, counter, make_increment_command):
        cmd1 = make_increment_command(amount=1, name="inc1")
        cmd2 = make_increment_command(amount=2, name="inc2")
        cmd3 = make_increment_command(amount=3, name="inc3")

        stack.execute(cmd1)
        stack.execute(cmd2)

        assert counter["value"] == 3
        assert stack.undo_count == 2
        assert stack.redo_count == 0

        stack.undo()
        assert counter["value"] == 1
        assert stack.undo_count == 1
        assert stack.redo_count == 1

        stack.execute(cmd3)
        assert counter["value"] == 4
        assert stack.undo_count == 2
        assert stack.redo_count == 0
        assert stack.can_redo is False

    def test_execute_invalid_command_type_raises(self, stack):
        with pytest.raises(TypeError, match="command must be an instance of Command"):
            stack.execute("not a command")


class TestCommandExecutionError:
    def test_execute_failure_raises(self, stack):
        def failing_execute():
            raise ValueError("execute failed")

        def undo():
            pass

        cmd = Command(name="failing-cmd", execute=failing_execute, undo=undo)

        with pytest.raises(CommandExecutionError, match="Failed to execute command"):
            stack.execute(cmd)

        assert stack.can_undo is False
        assert stack.undo_count == 0

    def test_undo_failure_preserves_stack(self, stack, counter):
        fail_after = {"count": 0}

        def execute():
            counter["value"] += 1

        def failing_undo():
            fail_after["count"] += 1
            if fail_after["count"] >= 1:
                raise ValueError("undo failed")

        cmd = Command(name="failing-undo", execute=execute, undo=failing_undo)

        stack.execute(cmd)
        assert counter["value"] == 1
        assert stack.undo_count == 1

        with pytest.raises(Exception):
            stack.undo()

        assert counter["value"] == 1
        assert stack.undo_count == 1
        assert stack.redo_count == 0


class TestTransactionGroup:
    def test_begin_and_commit_transaction(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1", "Test transaction")

        assert stack.state.has_active_transaction is True
        assert stack.state.active_transaction.name == "tx1"
        assert stack.state.active_transaction.description == "Test transaction"

        cmd1 = make_increment_command(amount=1, name="inc1")
        cmd2 = make_increment_command(amount=2, name="inc2")

        stack.execute(cmd1)
        stack.execute(cmd2)

        assert counter["value"] == 3
        assert stack.undo_count == 0
        assert stack.state.active_transaction.size == 2

        stack.commit_transaction()

        assert stack.state.has_active_transaction is False
        assert stack.undo_count == 1
        assert counter["value"] == 3

    def test_transaction_undo(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")

        cmd1 = make_increment_command(amount=1, name="inc1")
        cmd2 = make_increment_command(amount=2, name="inc2")
        cmd3 = make_increment_command(amount=3, name="inc3")

        stack.execute(cmd1)
        stack.execute(cmd2)
        stack.execute(cmd3)

        stack.commit_transaction()

        assert counter["value"] == 6
        assert stack.undo_count == 1

        stack.undo()
        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 1

    def test_transaction_redo(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")

        cmd1 = make_increment_command(amount=1, name="inc1")
        cmd2 = make_increment_command(amount=2, name="inc2")

        stack.execute(cmd1)
        stack.execute(cmd2)
        stack.commit_transaction()

        assert counter["value"] == 3

        stack.undo()
        assert counter["value"] == 0
        assert stack.can_redo is True

        stack.redo()
        assert counter["value"] == 3
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_transaction_rollback(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")

        cmd1 = make_increment_command(amount=5, name="inc5")
        cmd2 = make_increment_command(amount=10, name="inc10")

        stack.execute(cmd1)
        stack.execute(cmd2)

        assert counter["value"] == 15
        assert stack.state.has_active_transaction is True

        stack.rollback_transaction()

        assert counter["value"] == 0
        assert stack.state.has_active_transaction is False
        assert stack.undo_count == 0
        assert stack.redo_count == 0

    def test_transaction_single_command(self, stack, counter, make_increment_command):
        stack.begin_transaction("single-cmd-tx")

        cmd = make_increment_command(amount=42, name="inc42")
        stack.execute(cmd)

        stack.commit_transaction()

        assert counter["value"] == 42
        assert stack.undo_count == 1

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 1

        stack.redo()
        assert counter["value"] == 42
        assert stack.undo_count == 1

    def test_begin_transaction_when_active_raises(self, stack):
        stack.begin_transaction("tx1")

        with pytest.raises(
            Exception, match="Cannot begin transaction: a transaction is already active"
        ):
            stack.begin_transaction("tx2")

    def test_commit_without_transaction_raises(self, stack):
        with pytest.raises(
            Exception, match="Cannot commit transaction: no active transaction"
        ):
            stack.commit_transaction()

    def test_rollback_without_transaction_raises(self, stack):
        with pytest.raises(
            Exception, match="Cannot rollback transaction: no active transaction"
        ):
            stack.rollback_transaction()

    def test_empty_transaction_not_added_to_stack(self, stack):
        stack.begin_transaction("empty-tx")
        stack.commit_transaction()

        assert stack.undo_count == 0
        assert stack.can_undo is False

    def test_new_command_after_transaction_clears_redo(
        self, stack, counter, make_increment_command, make_decrement_command
    ):
        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=1, name="inc1"))
        stack.execute(make_increment_command(amount=2, name="inc2"))
        stack.commit_transaction()

        assert counter["value"] == 3
        assert stack.undo_count == 1

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 1

        new_cmd = make_decrement_command(amount=5, name="dec5")
        stack.execute(new_cmd)

        assert counter["value"] == -5
        assert stack.undo_count == 1
        assert stack.redo_count == 0
        assert stack.can_redo is False

    def test_multiple_transactions(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=1, name="inc1"))
        stack.commit_transaction()

        stack.begin_transaction("tx2")
        stack.execute(make_increment_command(amount=2, name="inc2"))
        stack.execute(make_increment_command(amount=3, name="inc3"))
        stack.commit_transaction()

        assert counter["value"] == 6
        assert stack.undo_count == 2

        stack.undo()
        assert counter["value"] == 1
        assert stack.undo_count == 1
        assert stack.redo_count == 1

        stack.undo()
        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 2

        stack.redo()
        assert counter["value"] == 1
        assert stack.undo_count == 1
        assert stack.redo_count == 1

    def test_mixed_commands_and_transactions(self, stack, counter, make_increment_command):
        cmd1 = make_increment_command(amount=10, name="inc10")
        stack.execute(cmd1)

        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=1, name="inc1"))
        stack.execute(make_increment_command(amount=2, name="inc2"))
        stack.commit_transaction()

        cmd2 = make_increment_command(amount=20, name="inc20")
        stack.execute(cmd2)

        assert counter["value"] == 33
        assert stack.undo_count == 3

        stack.undo()
        assert counter["value"] == 13

        stack.undo()
        assert counter["value"] == 10

        stack.undo()
        assert counter["value"] == 0

        assert stack.redo_count == 3

        stack.redo()
        assert counter["value"] == 10

        stack.redo()
        assert counter["value"] == 13

        stack.redo()
        assert counter["value"] == 33


class TestTransactionUndoFailure:
    def test_transaction_undo_first_command_failure_preserves_state(self, stack, counter):
        fail_at = {"cmd3": False}

        def make_cmd(name, amount):
            def execute():
                counter["value"] += amount

            def undo():
                if name == "cmd3" and fail_at["cmd3"]:
                    raise ValueError("cmd3 undo failed")
                counter["value"] -= amount

            return Command(name=name, execute=execute, undo=undo)

        stack.begin_transaction("tx1")
        stack.execute(make_cmd("cmd1", 1))
        stack.execute(make_cmd("cmd2", 2))
        stack.execute(make_cmd("cmd3", 4))
        stack.commit_transaction()

        assert counter["value"] == 7
        assert stack.undo_count == 1

        fail_at["cmd3"] = True

        with pytest.raises(Exception):
            stack.undo()

        assert counter["value"] == 7
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_transaction_undo_middle_command_failure_preserves_state(self, stack, counter):
        fail_at = {"cmd2": False}

        def make_cmd(name, amount):
            def execute():
                counter["value"] += amount

            def undo():
                if name == "cmd2" and fail_at["cmd2"]:
                    raise ValueError("cmd2 undo failed")
                counter["value"] -= amount

            return Command(name=name, execute=execute, undo=undo)

        stack.begin_transaction("tx1")
        stack.execute(make_cmd("cmd1", 10))
        stack.execute(make_cmd("cmd2", 20))
        stack.execute(make_cmd("cmd3", 30))
        stack.commit_transaction()

        assert counter["value"] == 60
        assert stack.undo_count == 1

        fail_at["cmd2"] = True

        with pytest.raises(Exception):
            stack.undo()

        assert counter["value"] == 60
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_transaction_undo_last_command_failure_preserves_state(self, stack, counter):
        fail_at = {"cmd1": False}

        def make_cmd(name, amount):
            def execute():
                counter["value"] += amount

            def undo():
                if name == "cmd1" and fail_at["cmd1"]:
                    raise ValueError("cmd1 undo failed")
                counter["value"] -= amount

            return Command(name=name, execute=execute, undo=undo)

        stack.begin_transaction("tx1")
        stack.execute(make_cmd("cmd1", 5))
        stack.execute(make_cmd("cmd2", 15))
        stack.execute(make_cmd("cmd3", 25))
        stack.commit_transaction()

        assert counter["value"] == 45
        assert stack.undo_count == 1

        fail_at["cmd1"] = True

        with pytest.raises(Exception):
            stack.undo()

        assert counter["value"] == 45
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_transaction_redo_middle_command_failure_preserves_state(self, stack, counter):
        fail_at = {"cmd2": False}

        def make_cmd(name, amount):
            def execute():
                if name == "cmd2" and fail_at["cmd2"]:
                    raise ValueError("cmd2 execute failed")
                counter["value"] += amount

            def undo():
                counter["value"] -= amount

            return Command(name=name, execute=execute, undo=undo)

        stack.begin_transaction("tx1")
        stack.execute(make_cmd("cmd1", 1))
        stack.execute(make_cmd("cmd2", 2))
        stack.execute(make_cmd("cmd3", 3))
        stack.commit_transaction()

        assert counter["value"] == 6

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 1

        fail_at["cmd2"] = True

        with pytest.raises(Exception):
            stack.redo()

        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 1

    def test_transaction_rollback_middle_failure_preserves_state(self, stack, counter):
        fail_at = {"cmd2": False}

        def make_cmd(name, amount):
            def execute():
                counter["value"] += amount

            def undo():
                if name == "cmd2" and fail_at["cmd2"]:
                    raise ValueError("cmd2 undo failed")
                counter["value"] -= amount

            return Command(name=name, execute=execute, undo=undo)

        stack.begin_transaction("tx1")
        stack.execute(make_cmd("cmd1", 100))
        stack.execute(make_cmd("cmd2", 200))
        stack.execute(make_cmd("cmd3", 300))

        assert counter["value"] == 600
        assert stack.state.has_active_transaction is True
        assert stack.undo_count == 0
        assert stack.redo_count == 0

        fail_at["cmd2"] = True

        with pytest.raises(Exception):
            stack.rollback_transaction()

        assert counter["value"] == 600
        assert stack.state.has_active_transaction is True
        assert stack.undo_count == 0
        assert stack.redo_count == 0


class TestSameTransactionContinuousBoundary:
    def test_same_transaction_consecutive_undo_raises(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=10, name="inc10"))
        stack.execute(make_increment_command(amount=20, name="inc20"))
        stack.commit_transaction()

        assert counter["value"] == 30
        assert stack.undo_count == 1

        stack.undo()
        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 1

        with pytest.raises(UndoStackEmptyError):
            stack.undo()

        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 1

    def test_same_transaction_consecutive_redo_raises(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=5, name="inc5"))
        stack.execute(make_increment_command(amount=15, name="inc15"))
        stack.commit_transaction()

        assert counter["value"] == 20

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 1

        stack.redo()
        assert counter["value"] == 20
        assert stack.undo_count == 1
        assert stack.redo_count == 0

        with pytest.raises(RedoStackEmptyError):
            stack.redo()

        assert counter["value"] == 20
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_same_transaction_undo_redo_undo_redo_cycle(self, stack, counter, make_increment_command):
        stack.begin_transaction("cycle-tx")
        stack.execute(make_increment_command(amount=7, name="inc7"))
        stack.execute(make_increment_command(amount=3, name="inc3"))
        stack.commit_transaction()

        assert counter["value"] == 10
        assert stack.undo_count == 1
        assert stack.redo_count == 0

        stack.undo()
        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 1

        stack.redo()
        assert counter["value"] == 10
        assert stack.undo_count == 1
        assert stack.redo_count == 0

        stack.undo()
        assert counter["value"] == 0
        assert stack.undo_count == 0
        assert stack.redo_count == 1

        stack.redo()
        assert counter["value"] == 10
        assert stack.undo_count == 1
        assert stack.redo_count == 0

    def test_same_transaction_then_new_command_clears_redo(self, stack, counter, make_increment_command):
        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=1, name="inc1"))
        stack.execute(make_increment_command(amount=2, name="inc2"))
        stack.commit_transaction()

        assert counter["value"] == 3

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 1
        assert stack.can_redo is True

        new_cmd = make_increment_command(amount=100, name="inc100")
        stack.execute(new_cmd)

        assert counter["value"] == 100
        assert stack.undo_count == 1
        assert stack.redo_count == 0
        assert stack.can_redo is False

        with pytest.raises(RedoStackEmptyError):
            stack.redo()

        assert counter["value"] == 100

    def test_single_command_transaction_consecutive_undo_redo(self, stack, counter, make_increment_command):
        stack.begin_transaction("single-tx")
        stack.execute(make_increment_command(amount=42, name="inc42"))
        stack.commit_transaction()

        assert counter["value"] == 42
        assert stack.undo_count == 1

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 1

        with pytest.raises(UndoStackEmptyError):
            stack.undo()

        stack.redo()
        assert counter["value"] == 42
        assert stack.undo_count == 1
        assert stack.redo_count == 0

        with pytest.raises(RedoStackEmptyError):
            stack.redo()

        assert counter["value"] == 42

    def test_same_transaction_after_multiple_others(self, stack, counter, make_increment_command):
        cmd_a = make_increment_command(amount=10, name="incA")
        stack.execute(cmd_a)

        stack.begin_transaction("tx-target")
        stack.execute(make_increment_command(amount=1, name="inc1"))
        stack.execute(make_increment_command(amount=2, name="inc2"))
        stack.commit_transaction()

        cmd_b = make_increment_command(amount=20, name="incB")
        stack.execute(cmd_b)

        assert counter["value"] == 33
        assert stack.undo_count == 3

        stack.undo()
        assert counter["value"] == 13

        stack.undo()
        assert counter["value"] == 10

        stack.undo()
        assert counter["value"] == 0
        assert stack.redo_count == 3

        stack.redo()
        assert counter["value"] == 10

        stack.redo()
        assert counter["value"] == 13

        stack.redo()
        assert counter["value"] == 33


class TestClear:
    def test_clear_all_state(self, stack, counter, make_increment_command):
        cmd1 = make_increment_command(amount=1, name="inc1")
        cmd2 = make_increment_command(amount=2, name="inc2")

        stack.execute(cmd1)
        stack.execute(cmd2)

        stack.undo()

        assert stack.undo_count == 1
        assert stack.redo_count == 1

        stack.clear()

        assert stack.can_undo is False
        assert stack.can_redo is False
        assert stack.undo_count == 0
        assert stack.redo_count == 0
        assert stack.state.has_active_transaction is False

    def test_clear_with_active_transaction(self, stack, make_increment_command):
        stack.begin_transaction("tx1")
        stack.execute(make_increment_command(amount=1, name="inc1"))

        assert stack.state.has_active_transaction is True

        stack.clear()

        assert stack.state.has_active_transaction is False
        assert stack.undo_count == 0
