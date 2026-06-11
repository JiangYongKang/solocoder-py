import pytest

from solocoder_py.undo_redo import UndoRedoStack


@pytest.fixture
def stack():
    return UndoRedoStack()


@pytest.fixture
def counter():
    return {"value": 0}


@pytest.fixture
def make_increment_command(counter):
    def _make_increment_command(amount=1, name="increment"):
        from solocoder_py.undo_redo import Command

        def execute():
            counter["value"] += amount
            return counter["value"]

        def undo():
            counter["value"] -= amount
            return counter["value"]

        return Command(name=name, execute=execute, undo=undo)

    return _make_increment_command


@pytest.fixture
def make_decrement_command(counter):
    def _make_decrement_command(amount=1, name="decrement"):
        from solocoder_py.undo_redo import Command

        def execute():
            counter["value"] -= amount
            return counter["value"]

        def undo():
            counter["value"] += amount
            return counter["value"]

        return Command(name=name, execute=execute, undo=undo)

    return _make_decrement_command
