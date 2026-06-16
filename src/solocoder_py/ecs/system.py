from __future__ import annotations

from collections import deque
from typing import Any, Callable, Iterable

from .component import validate_component_type
from .entity import EntityId
from .exceptions import (
    CircularDependencyError,
    SystemAlreadyExistsError,
    SystemNotFoundError,
)
from .world import World


class System:
    def __init__(
        self,
        name: str,
        read_components: Iterable[type] | None = None,
        write_components: Iterable[type] | None = None,
        update: Callable[[World, "System"], None] | None = None,
    ) -> None:
        self._name = name
        self._read_components: frozenset[type] = frozenset(read_components or [])
        self._write_components: frozenset[type] = frozenset(write_components or [])
        self._update = update

        all_components = self._read_components | self._write_components
        self._query_order: list[type] = sorted(
            all_components, key=lambda t: t.__name__
        )

        for ct in self._read_components:
            validate_component_type(ct)
        for ct in self._write_components:
            validate_component_type(ct)

    @property
    def name(self) -> str:
        return self._name

    @property
    def read_components(self) -> frozenset[type]:
        return self._read_components

    @property
    def write_components(self) -> frozenset[type]:
        return self._write_components

    def update(self, world: World) -> None:
        if self._update is not None:
            self._update(world, self)

    def query(
        self, world: World, component_order: Iterable[type] | None = None
    ) -> Iterable[tuple[EntityId, tuple[Any, ...]]]:
        if component_order is None:
            component_order = self._query_order
        return world.query_entities(component_order)

    def query_by_archetype(
        self, world: World, component_order: Iterable[type] | None = None
    ) -> Iterable[tuple[EntityId, tuple[Any, ...]]]:
        if component_order is None:
            component_order = self._query_order
        return world.query_entities_archetype(component_order)


class SystemScheduler:
    def __init__(self) -> None:
        self._systems: dict[str, System] = {}
        self._order: list[str] = []
        self._needs_sort: bool = True

    def add_system(self, system: System) -> None:
        if system.name in self._systems:
            raise SystemAlreadyExistsError(system.name)
        self._systems[system.name] = system
        self._needs_sort = True

    def remove_system(self, name: str) -> None:
        if name not in self._systems:
            raise SystemNotFoundError(name)
        del self._systems[name]
        if name in self._order:
            self._order.remove(name)
        self._needs_sort = True

    def get_system(self, name: str) -> System:
        if name not in self._systems:
            raise SystemNotFoundError(name)
        return self._systems[name]

    def has_system(self, name: str) -> bool:
        return name in self._systems

    def list_systems(self) -> list[str]:
        return list(self._systems.keys())

    def _build_dependency_graph(self) -> tuple[dict[str, set[str]], dict[str, int]]:
        adjacency: dict[str, set[str]] = {name: set() for name in self._systems}
        in_degree: dict[str, int] = {name: 0 for name in self._systems}

        systems_list = list(self._systems.values())
        n = len(systems_list)

        def add_edge(from_sys, to_sys):
            if to_sys.name not in adjacency[from_sys.name]:
                adjacency[from_sys.name].add(to_sys.name)
                in_degree[to_sys.name] += 1

        for i in range(n):
            for j in range(i + 1, n):
                sys_a = systems_list[i]
                sys_b = systems_list[j]

                a_reads = sys_a.read_components
                a_writes = sys_a.write_components
                b_reads = sys_b.read_components
                b_writes = sys_b.write_components

                raw_ab = bool(a_writes & b_reads)
                raw_ba = bool(b_writes & a_reads)
                war_ab = bool(a_reads & b_writes)
                war_ba = bool(b_reads & a_writes)
                waw_ab = bool(a_writes & b_writes)

                if raw_ab and raw_ba:
                    add_edge(sys_a, sys_b)
                    add_edge(sys_b, sys_a)

                elif raw_ab:
                    add_edge(sys_a, sys_b)

                elif raw_ba:
                    add_edge(sys_b, sys_a)

                elif war_ab and war_ba:
                    if sys_a.name < sys_b.name:
                        add_edge(sys_a, sys_b)
                    else:
                        add_edge(sys_b, sys_a)

                elif war_ab:
                    add_edge(sys_a, sys_b)

                elif war_ba:
                    add_edge(sys_b, sys_a)

                elif waw_ab:
                    if sys_a.name < sys_b.name:
                        add_edge(sys_a, sys_b)
                    else:
                        add_edge(sys_b, sys_a)

        return adjacency, in_degree

    def _detect_cycle(
        self, adjacency: dict[str, set[str]]
    ) -> tuple[bool, list[str] | None]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {name: WHITE for name in adjacency}
        parent: dict[str, str | None] = {name: None for name in adjacency}

        def dfs(node: str, path: list[str]) -> tuple[bool, list[str] | None]:
            color[node] = GRAY
            path.append(node)

            for neighbor in adjacency[node]:
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:] + [neighbor]
                elif color[neighbor] == WHITE:
                    parent[neighbor] = node
                    found, cycle = dfs(neighbor, path)
                    if found:
                        return True, cycle

            path.pop()
            color[node] = BLACK
            return False, None

        for node in adjacency:
            if color[node] == WHITE:
                found, cycle = dfs(node, [])
                if found:
                    return True, cycle

        return False, None

    def sort(self) -> None:
        if not self._needs_sort and self._order:
            return

        if not self._systems:
            self._order = []
            self._needs_sort = False
            return

        adjacency, in_degree = self._build_dependency_graph()

        has_cycle, cycle = self._detect_cycle(adjacency)
        if has_cycle and cycle:
            raise CircularDependencyError(cycle)

        queue: deque[str] = deque()
        for name, deg in in_degree.items():
            if deg == 0:
                queue.append(name)

        result: list[str] = []
        temp_in_degree = dict(in_degree)

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in sorted(adjacency[node]):
                temp_in_degree[neighbor] -= 1
                if temp_in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._systems):
            remaining = [name for name in self._systems if name not in result]
            raise CircularDependencyError(remaining)

        self._order = result
        self._needs_sort = False

    def update(self, world: World) -> None:
        self.sort()
        for name in self._order:
            self._systems[name].update(world)

    def get_order(self) -> list[str]:
        self.sort()
        return list(self._order)

    def clear(self) -> None:
        self._systems.clear()
        self._order.clear()
        self._needs_sort = True
