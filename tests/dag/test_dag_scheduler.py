from __future__ import annotations

import pytest

from solocoder_py.dag import (
    CycleDetectedError,
    DAGScheduler,
    DAGError,
    DependencyNotFoundError,
    Task,
    TaskAlreadyRegisteredError,
    TaskExecutionContext,
    TaskNotFoundError,
    TaskNotReadyError,
    TaskStatus,
)
from tests.dag.conftest import (
    TaskTracker,
    build_diamond_scheduler,
    build_linear_scheduler,
    build_single_node_scheduler,
)


class TestTaskModel:
    def test_task_creation_basic(self) -> None:
        task = Task(task_id="t1")
        assert task.task_id == "t1"
        assert task.dependencies == []
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None

    def test_task_creation_with_deps_and_name(self) -> None:
        task = Task(task_id="t1", dependencies=["a", "b"], name="My Task")
        assert task.dependencies == ["a", "b"]
        assert task.name == "My Task"

    def test_task_empty_id_raises(self) -> None:
        with pytest.raises(DAGError, match="task_id cannot be empty"):
            Task(task_id="")

    def test_task_dependencies_deduplicated(self) -> None:
        task = Task(task_id="t1", dependencies=["a", "b", "a", "c", "b"])
        assert task.dependencies == ["a", "b", "c"]

    def test_task_mark_ready_from_pending(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        assert task.status == TaskStatus.READY

    def test_task_mark_ready_idempotent_if_already_ready(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        task.mark_ready()
        assert task.status == TaskStatus.READY

    def test_task_mark_running_from_ready(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_task_mark_running_from_pending_does_nothing(self) -> None:
        task = Task(task_id="t1")
        task.mark_running()
        assert task.status == TaskStatus.PENDING

    def test_task_mark_success_from_running(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        task.mark_running()
        task.mark_success(result="done")
        assert task.status == TaskStatus.SUCCESS
        assert task.result == "done"
        assert task.completed_at is not None

    def test_task_mark_success_from_pending_does_nothing(self) -> None:
        task = Task(task_id="t1")
        task.mark_success(result="done")
        assert task.status == TaskStatus.PENDING
        assert task.result is None

    def test_task_mark_failed_from_running(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        task.mark_running()
        err = RuntimeError("boom")
        task.mark_failed(err)
        assert task.status == TaskStatus.FAILED
        assert task.error is err
        assert task.completed_at is not None

    def test_task_mark_failed_from_pending_does_nothing(self) -> None:
        task = Task(task_id="t1")
        task.mark_failed(RuntimeError("boom"))
        assert task.status == TaskStatus.PENDING
        assert task.error is None

    def test_task_mark_blocked_from_pending(self) -> None:
        task = Task(task_id="t1")
        task.mark_blocked()
        assert task.status == TaskStatus.BLOCKED
        assert task.completed_at is not None

    def test_task_mark_blocked_from_ready(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        task.mark_blocked()
        assert task.status == TaskStatus.BLOCKED

    def test_task_mark_blocked_from_success_does_nothing(self) -> None:
        task = Task(task_id="t1")
        task.mark_ready()
        task.mark_running()
        task.mark_success()
        task.mark_blocked()
        assert task.status == TaskStatus.SUCCESS

    def test_task_is_terminal(self) -> None:
        task = Task(task_id="t1")
        assert not task.is_terminal()
        task.mark_ready()
        task.mark_running()
        assert not task.is_terminal()
        task.mark_success()
        assert task.is_terminal()

        task2 = Task(task_id="t2")
        task2.mark_blocked()
        assert task2.is_terminal()

        task3 = Task(task_id="t3")
        task3.mark_ready()
        task3.mark_running()
        task3.mark_failed(RuntimeError("x"))
        assert task3.is_terminal()


class TestTaskExecutionContext:
    def test_context_creation(self) -> None:
        ctx = TaskExecutionContext(task_id="t1")
        assert ctx.task_id == "t1"
        assert ctx.result is None
        assert ctx.error is None
        assert ctx.started_at is None
        assert ctx.completed_at is None


class TestDAGSchedulerRegistration:
    def test_register_single_task_no_deps(self, scheduler: DAGScheduler) -> None:
        task = scheduler.register_task(task_id="A")
        assert scheduler.task_count == 1
        assert scheduler.has_task("A")
        assert task.task_id == "A"
        assert task.status == TaskStatus.READY

    def test_register_task_with_valid_dependencies(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        task_b = scheduler.register_task(task_id="B", dependencies=["A"])
        assert task_b.status == TaskStatus.PENDING
        assert scheduler.get_dependencies("B") == ["A"]
        assert scheduler.get_dependents("A") == ["B"]

    def test_register_task_missing_dependency_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        with pytest.raises(DependencyNotFoundError, match="Dependency 'missing' not found"):
            scheduler.register_task(task_id="A", dependencies=["missing"])

    def test_register_duplicate_task_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        with pytest.raises(TaskAlreadyRegisteredError, match="Task already registered: A"):
            scheduler.register_task(task_id="A")

    def test_get_task_not_found_raises(self, scheduler: DAGScheduler) -> None:
        with pytest.raises(TaskNotFoundError, match="Task not found: missing"):
            scheduler.get_task("missing")

    def test_get_all_tasks(self, scheduler: DAGScheduler) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        tasks = scheduler.get_all_tasks()
        assert len(tasks) == 2
        ids = {t.task_id for t in tasks}
        assert ids == {"A", "B"}

    def test_add_dependency_valid(self, scheduler: DAGScheduler) -> None:
        scheduler.register_task(task_id="A")
        task_b = scheduler.register_task(task_id="B")
        assert task_b.status == TaskStatus.READY

        scheduler.add_dependency("B", "A")
        assert scheduler.get_dependencies("B") == ["A"]
        assert scheduler.get_dependents("A") == ["B"]
        assert task_b.status == TaskStatus.PENDING

    def test_add_dependency_duplicate_is_noop(self, scheduler: DAGScheduler) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.add_dependency("B", "A")
        assert scheduler.get_dependencies("B") == ["A"]

    def test_add_dependency_task_not_found_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        with pytest.raises(TaskNotFoundError):
            scheduler.add_dependency("missing", "A")

    def test_add_dependency_dep_not_found_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        with pytest.raises(DependencyNotFoundError):
            scheduler.add_dependency("A", "missing")

    def test_register_task_with_action(
        self, scheduler: DAGScheduler, tracker: TaskTracker
    ) -> None:
        scheduler.register_task(
            task_id="A", action=tracker.make_action("A", result=100)
        )
        task = scheduler.execute_task("A")
        assert task.status == TaskStatus.SUCCESS
        assert task.result == 100
        assert tracker.executed == ["A"]


class TestDAGSchedulerCycleDetection:
    def test_register_task_self_loop_raises_cycle_error(
        self, scheduler: DAGScheduler
    ) -> None:
        with pytest.raises(CycleDetectedError, match="create a cycle"):
            scheduler.register_task(task_id="A", dependencies=["A"])

    def test_add_dependency_self_loop_raises_cycle_error(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        with pytest.raises(CycleDetectedError, match="create a cycle"):
            scheduler.add_dependency("A", "A")

    def test_add_dependency_creates_simple_cycle_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B", "A"])
        with pytest.raises(CycleDetectedError, match="create a cycle"):
            scheduler.add_dependency("A", "C")

    def test_add_dependency_creates_three_node_cycle_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])
        with pytest.raises(CycleDetectedError, match="create a cycle"):
            scheduler.add_dependency("A", "C")

    def test_add_dependency_creates_multi_node_cycle_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])
        scheduler.register_task(task_id="D", dependencies=["C"])
        with pytest.raises(CycleDetectedError):
            scheduler.add_dependency("A", "D")

    def test_no_cycle_valid_diamond(self, scheduler: DAGScheduler) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["A"])
        scheduler.register_task(task_id="D", dependencies=["B", "C"])
        assert scheduler.task_count == 4

    def test_cycle_path_self_loop_register_matches_edges(
        self, scheduler: DAGScheduler
    ) -> None:
        with pytest.raises(CycleDetectedError) as exc_info:
            scheduler.register_task(task_id="X", dependencies=["X"])
        assert "X -> X" in str(exc_info.value)

    def test_cycle_path_self_loop_add_dep_matches_edges(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="X")
        with pytest.raises(CycleDetectedError) as exc_info:
            scheduler.add_dependency("X", "X")
        assert "X -> X" in str(exc_info.value)

    def test_cycle_path_three_node_chain_matches_actual_edges(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])

        with pytest.raises(CycleDetectedError) as exc_info:
            scheduler.add_dependency("A", "C")

        error_msg = str(exc_info.value)
        path_part = error_msg.split("cycle: ")[-1]
        nodes = [n.strip() for n in path_part.split("->")]

        assert len(nodes) >= 3
        assert set(nodes) == {"A", "B", "C"}

        adjacency = {
            "A": {"C"},
            "B": {"A"},
            "C": {"B"},
        }
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            assert to_node in adjacency.get(from_node, set()), (
                f"Reported path contains edge {from_node} -> {to_node}, "
                f"but no such edge exists in the graph"
            )

    def test_cycle_path_four_node_chain_matches_actual_edges(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])
        scheduler.register_task(task_id="D", dependencies=["C"])

        with pytest.raises(CycleDetectedError) as exc_info:
            scheduler.add_dependency("A", "D")

        error_msg = str(exc_info.value)
        path_part = error_msg.split("cycle: ")[-1]
        nodes = [n.strip() for n in path_part.split("->")]

        assert len(nodes) >= 4
        assert set(nodes) == {"A", "B", "C", "D"}

        adjacency = {
            "A": {"D"},
            "B": {"A"},
            "C": {"B"},
            "D": {"C"},
        }
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            assert to_node in adjacency.get(from_node, set()), (
                f"Reported path contains edge {from_node} -> {to_node}, "
                f"but no such edge exists in the graph"
            )

    def test_cycle_path_in_diamond_graph_matches_edges(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["A"])
        scheduler.register_task(task_id="D", dependencies=["B", "C"])

        with pytest.raises(CycleDetectedError) as exc_info:
            scheduler.add_dependency("A", "D")

        error_msg = str(exc_info.value)
        path_part = error_msg.split("cycle: ")[-1]
        nodes = [n.strip() for n in path_part.split("->")]

        assert len(nodes) >= 3
        for node in nodes:
            assert node in {"A", "B", "C", "D"}

        adjacency = {
            "A": ["D"],
            "B": ["A"],
            "C": ["A"],
            "D": ["B", "C"],
        }
        adjacency_set = {k: set(v) for k, v in adjacency.items()}
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            assert to_node in adjacency_set.get(from_node, set()), (
                f"Reported path contains edge {from_node} -> {to_node}, "
                f"but no such edge exists in the graph"
            )

    def test_cycle_path_with_unrelated_nodes_matches_edges(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="X")
        scheduler.register_task(task_id="Y", dependencies=["X"])
        scheduler.register_task(task_id="Z", dependencies=["Y"])
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])

        with pytest.raises(CycleDetectedError) as exc_info:
            scheduler.add_dependency("A", "C")

        error_msg = str(exc_info.value)
        path_part = error_msg.split("cycle: ")[-1]
        nodes = [n.strip() for n in path_part.split("->")]

        assert len(nodes) >= 3
        assert set(nodes) == {"A", "B", "C"}

        adjacency = {
            "A": ["C"],
            "B": ["A"],
            "C": ["B"],
            "X": [],
            "Y": ["X"],
            "Z": ["Y"],
        }
        adjacency_set = {k: set(v) for k, v in adjacency.items()}
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            assert to_node in adjacency_set.get(from_node, set()), (
                f"Reported path contains edge {from_node} -> {to_node}, "
                f"but no such edge exists in the graph"
            )


class TestDAGSchedulerTopologicalSort:
    def test_topological_sort_single_node(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        assert scheduler.topological_sort() == ["A"]

    def test_topological_sort_linear_chain(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])
        order = scheduler.topological_sort()
        assert order == ["A", "B", "C"]

    def test_topological_sort_diamond(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["A"])
        scheduler.register_task(task_id="D", dependencies=["B", "C"])
        order = scheduler.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_topological_sort_multiple_roots(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B")
        scheduler.register_task(task_id="C", dependencies=["A", "B"])
        order = scheduler.topological_sort()
        assert set(order[:2]) == {"A", "B"}
        assert order[2] == "C"

    def test_get_downstream(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_linear_scheduler(tracker, task_count=4)
        assert scheduler.get_downstream("task-0") == ["task-1", "task-2", "task-3"]
        assert scheduler.get_downstream("task-2") == ["task-3"]
        assert scheduler.get_downstream("task-3") == []

    def test_get_downstream_diamond(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_diamond_scheduler(tracker)
        downstream_a = set(scheduler.get_downstream("A"))
        assert downstream_a == {"B", "C", "D"}
        assert set(scheduler.get_downstream("B")) == {"D"}
        assert scheduler.get_downstream("D") == []


class TestDAGSchedulerNormalFlow:
    def test_single_node_success(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_single_node_scheduler(tracker)
        ready = scheduler.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "only"

        task = scheduler.execute_task("only")
        assert task.status == TaskStatus.SUCCESS
        assert task.result == 42
        assert tracker.executed == ["only"]
        assert scheduler.is_success()
        assert scheduler.is_complete()

    def test_linear_chain_success(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_linear_scheduler(tracker, task_count=4)
        executed = scheduler.run_all()

        assert len(executed) == 4
        assert tracker.executed == ["task-0", "task-1", "task-2", "task-3"]
        for i in range(4):
            task = scheduler.get_task(f"task-{i}")
            assert task.status == TaskStatus.SUCCESS
            assert task.result == i
        assert scheduler.is_success()

    def test_diamond_success(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_diamond_scheduler(tracker)
        executed = scheduler.run_all()

        assert len(executed) == 4
        assert "A" in tracker.executed
        assert "D" in tracker.executed
        assert tracker.executed.index("A") < tracker.executed.index("B")
        assert tracker.executed.index("A") < tracker.executed.index("C")
        assert tracker.executed.index("B") < tracker.executed.index("D")
        assert tracker.executed.index("C") < tracker.executed.index("D")
        assert scheduler.is_success()

    def test_task_ready_transition_on_dependency_complete(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(
            task_id="A", action=tracker.make_action("A", result=1)
        )
        scheduler.register_task(
            task_id="B",
            dependencies=["A"],
            action=tracker.make_action("B", result=2),
        )
        assert scheduler.get_task("B").status == TaskStatus.PENDING
        assert len(scheduler.get_ready_tasks()) == 1

        scheduler.execute_task("A")
        assert scheduler.get_task("B").status == TaskStatus.READY
        assert len(scheduler.get_ready_tasks()) == 1

    def test_complete_task_manually(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        task_a = scheduler.complete_task("A", result="done")
        assert task_a.status == TaskStatus.SUCCESS
        assert task_a.result == "done"
        assert scheduler.get_task("B").status == TaskStatus.READY

    def test_reset_scheduler(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_linear_scheduler(tracker, task_count=3)
        scheduler.run_all()
        assert scheduler.is_success()

        scheduler.reset()
        assert not scheduler.is_complete()
        assert scheduler.get_task("task-0").status == TaskStatus.READY
        assert scheduler.get_task("task-1").status == TaskStatus.PENDING
        assert scheduler.get_task("task-2").status == TaskStatus.PENDING
        assert scheduler.get_task("task-0").result is None


class TestDAGSchedulerFailurePropagation:
    def test_single_node_failure(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_single_node_scheduler(tracker, fail=True)
        task = scheduler.execute_task("only")
        assert task.status == TaskStatus.FAILED
        assert task.error is not None
        assert isinstance(task.error, RuntimeError)
        assert scheduler.is_complete()
        assert not scheduler.is_success()

    def test_linear_chain_middle_failure_blocks_downstream(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_linear_scheduler(tracker, task_count=4, fail_at=1)
        scheduler.run_all()

        assert scheduler.get_task("task-0").status == TaskStatus.SUCCESS
        assert scheduler.get_task("task-1").status == TaskStatus.FAILED
        assert scheduler.get_task("task-2").status == TaskStatus.BLOCKED
        assert scheduler.get_task("task-3").status == TaskStatus.BLOCKED
        assert tracker.executed == ["task-0", "task-1"]
        assert scheduler.is_complete()
        assert not scheduler.is_success()

    def test_diamond_b_failure_blocks_d(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_diamond_scheduler(tracker, fail_at="B")
        scheduler.run_all()

        assert scheduler.get_task("A").status == TaskStatus.SUCCESS
        assert scheduler.get_task("B").status == TaskStatus.FAILED
        assert scheduler.get_task("C").status == TaskStatus.SUCCESS
        assert scheduler.get_task("D").status == TaskStatus.BLOCKED
        assert "D" not in tracker.executed

    def test_fail_task_manually(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        scheduler.register_task(task_id="C", dependencies=["B"])

        task_a = scheduler.fail_task("A", error=RuntimeError("manual fail"))
        assert task_a.status == TaskStatus.FAILED
        assert scheduler.get_task("B").status == TaskStatus.BLOCKED
        assert scheduler.get_task("C").status == TaskStatus.BLOCKED

    def test_first_node_failure_blocks_all(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_linear_scheduler(tracker, task_count=5, fail_at=0)
        scheduler.run_all()

        assert scheduler.get_task("task-0").status == TaskStatus.FAILED
        for i in range(1, 5):
            assert scheduler.get_task(f"task-{i}").status == TaskStatus.BLOCKED
        assert tracker.executed == ["task-0"]


class TestDAGSchedulerEdgeCases:
    def test_execute_not_ready_task_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        with pytest.raises(TaskNotReadyError, match="not ready"):
            scheduler.execute_task("B")

    def test_execute_already_completed_task_raises(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler = build_single_node_scheduler(tracker)
        scheduler.execute_task("only")
        with pytest.raises(TaskNotReadyError):
            scheduler.execute_task("only")

    def test_empty_scheduler(self, scheduler: DAGScheduler) -> None:
        assert scheduler.task_count == 0
        assert scheduler.get_ready_tasks() == []
        assert scheduler.get_all_tasks() == []
        assert scheduler.topological_sort() == []
        assert scheduler.is_complete()
        assert scheduler.is_success()

    def test_complete_not_running_task_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        with pytest.raises(TaskNotReadyError, match="not running"):
            scheduler.complete_task("B")

    def test_fail_not_running_task_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        scheduler.register_task(task_id="B", dependencies=["A"])
        with pytest.raises(TaskNotReadyError, match="not running"):
            scheduler.fail_task("B")

    def test_get_dependents_not_found_raises(
        self, scheduler: DAGScheduler
    ) -> None:
        with pytest.raises(TaskNotFoundError):
            scheduler.get_dependents("missing")

    def test_task_without_action_defaults_success(
        self, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(task_id="A")
        task = scheduler.execute_task("A")
        assert task.status == TaskStatus.SUCCESS
        assert task.result is None

    def test_multiple_independent_tasks(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        for i in range(3):
            scheduler.register_task(
                task_id=f"t{i}",
                action=tracker.make_action(f"t{i}", result=i),
            )
        assert len(scheduler.get_ready_tasks()) == 3
        executed = scheduler.run_all()
        assert len(executed) == 3
        assert scheduler.is_success()
        assert set(tracker.executed) == {"t0", "t1", "t2"}

    def test_complex_multi_branch_dag(
        self, tracker: TaskTracker, scheduler: DAGScheduler
    ) -> None:
        scheduler.register_task(
            task_id="start", action=tracker.make_action("start", result=0)
        )
        scheduler.register_task(
            task_id="a1",
            dependencies=["start"],
            action=tracker.make_action("a1", result=1),
        )
        scheduler.register_task(
            task_id="a2",
            dependencies=["a1"],
            action=tracker.make_action("a2", result=2),
        )
        scheduler.register_task(
            task_id="b1",
            dependencies=["start"],
            action=tracker.make_action("b1", result=3),
        )
        scheduler.register_task(
            task_id="end",
            dependencies=["a2", "b1"],
            action=tracker.make_action("end", result=4),
        )

        scheduler.run_all()
        assert scheduler.is_success()
        assert tracker.executed.index("start") < tracker.executed.index("a1")
        assert tracker.executed.index("a1") < tracker.executed.index("a2")
        assert tracker.executed.index("start") < tracker.executed.index("b1")
        assert tracker.executed.index("a2") < tracker.executed.index("end")
        assert tracker.executed.index("b1") < tracker.executed.index("end")
