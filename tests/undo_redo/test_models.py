from solocoder_py.undo_redo import Command, UndoRedoStack


class TestCommandModel:
    def test_command_creation(self):
        def execute():
            pass

        def undo():
            pass

        cmd = Command(name="test-cmd", execute=execute, undo=undo)
        assert cmd.name == "test-cmd"
        assert cmd.execute == execute
        assert cmd.undo == undo
        assert cmd.description == ""

    def test_command_with_description(self):
        def execute():
            pass

        def undo():
            pass

        cmd = Command(
            name="test-cmd",
            execute=execute,
            undo=undo,
            description="A test command",
        )
        assert cmd.description == "A test command"

    def test_command_empty_name_rejected(self):
        import pytest

        def execute():
            pass

        def undo():
            pass

        with pytest.raises(ValueError, match="Command name cannot be empty"):
            Command(name="", execute=execute, undo=undo)

    def test_command_non_callable_execute_rejected(self):
        import pytest

        def undo():
            pass

        with pytest.raises(ValueError, match="execute must be callable"):
            Command(name="test", execute="not_callable", undo=undo)

    def test_command_non_callable_undo_rejected(self):
        import pytest

        def execute():
            pass

        with pytest.raises(ValueError, match="undo must be callable"):
            Command(name="test", execute=execute, undo="not_callable")


class TestTransactionGroupModel:
    def test_transaction_group_creation(self):
        from solocoder_py.undo_redo import TransactionGroup

        group = TransactionGroup(name="test-group")
        assert group.name == "test-group"
        assert group.commands == []
        assert group.description == ""
        assert group.size == 0
        assert group.is_empty is True

    def test_transaction_group_with_description(self):
        from solocoder_py.undo_redo import TransactionGroup

        group = TransactionGroup(
            name="test-group", description="A test transaction"
        )
        assert group.description == "A test transaction"

    def test_transaction_group_empty_name_rejected(self):
        import pytest
        from solocoder_py.undo_redo import TransactionGroup

        with pytest.raises(
            ValueError, match="TransactionGroup name cannot be empty"
        ):
            TransactionGroup(name="")

    def test_transaction_group_add_command(self):
        from solocoder_py.undo_redo import Command, TransactionGroup

        def execute():
            pass

        def undo():
            pass

        group = TransactionGroup(name="test-group")
        cmd = Command(name="cmd1", execute=execute, undo=undo)

        group.add_command(cmd)
        assert group.size == 1
        assert group.is_empty is False
        assert group.commands[0] == cmd

    def test_transaction_group_add_multiple_commands(self):
        from solocoder_py.undo_redo import Command, TransactionGroup

        def execute():
            pass

        def undo():
            pass

        group = TransactionGroup(name="test-group")
        cmd1 = Command(name="cmd1", execute=execute, undo=undo)
        cmd2 = Command(name="cmd2", execute=execute, undo=undo)

        group.add_command(cmd1)
        group.add_command(cmd2)
        assert group.size == 2
        assert group.commands == [cmd1, cmd2]


class TestUndoRedoState:
    def test_initial_state(self):
        from solocoder_py.undo_redo import UndoRedoState

        state = UndoRedoState()
        assert state.can_undo is False
        assert state.can_redo is False
        assert state.undo_count == 0
        assert state.redo_count == 0
        assert state.has_active_transaction is False
        assert state.undo_stack == []
        assert state.redo_stack == []
        assert state.active_transaction is None

    def test_state_with_commands(self):
        from solocoder_py.undo_redo import Command, UndoRedoState

        def execute():
            pass

        def undo():
            pass

        state = UndoRedoState()
        cmd1 = Command(name="cmd1", execute=execute, undo=undo)
        cmd2 = Command(name="cmd2", execute=execute, undo=undo)

        state.undo_stack.append(cmd1)
        state.undo_stack.append(cmd2)

        assert state.can_undo is True
        assert state.undo_count == 2

        state.redo_stack.append(cmd1)
        assert state.can_redo is True
        assert state.redo_count == 1

    def test_state_with_active_transaction(self):
        from solocoder_py.undo_redo import TransactionGroup, UndoRedoState

        state = UndoRedoState()
        state.active_transaction = TransactionGroup(name="tx1")

        assert state.has_active_transaction is True
