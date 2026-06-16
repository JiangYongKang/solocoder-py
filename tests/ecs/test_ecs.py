from __future__ import annotations

import pytest

from solocoder_py.ecs import (
    ArchetypeManager,
    CircularDependencyError,
    ComponentAlreadyExistsError,
    ComponentNotFoundError,
    EntityId,
    EntityNotFoundError,
    Health,
    Name,
    Position,
    SparseSet,
    System,
    SystemAlreadyExistsError,
    SystemNotFoundError,
    SystemScheduler,
    Tag,
    Velocity,
    World,
    component,
)


@component
class Score:
    value: int = 0


# ============================================================
# Entity and Component Tests - Normal Flows
# ============================================================


class TestEntityCreation:
    def test_create_entity(self):
        world = World()
        entity = world.create_entity()
        assert isinstance(entity, EntityId)
        assert world.is_entity_alive(entity)
        assert world.entity_count() == 1

    def test_create_multiple_entities(self):
        world = World()
        entities = [world.create_entity() for _ in range(10)]
        assert len(entities) == 10
        assert world.entity_count() == 10
        for entity in entities:
            assert world.is_entity_alive(entity)

    def test_entity_id_unique(self):
        world = World()
        entities = [world.create_entity() for _ in range(100)]
        ids = {e.id for e in entities}
        assert len(ids) == 100

    def test_destroy_entity(self):
        world = World()
        entity = world.create_entity()
        world.destroy_entity(entity)
        assert not world.is_entity_alive(entity)
        assert world.entity_count() == 0

    def test_destroy_entity_reuses_id(self):
        world = World()
        e1 = world.create_entity()
        world.destroy_entity(e1)
        e2 = world.create_entity()
        assert e2.id == e1.id

    def test_destroy_nonexistent_entity_raises(self):
        world = World()
        entity = EntityId(999)
        with pytest.raises(EntityNotFoundError):
            world.destroy_entity(entity)


class TestComponentAssociation:
    def test_add_component(self):
        world = World()
        entity = world.create_entity()
        pos = Position(x=1.0, y=2.0)
        world.add_component(entity, pos)
        assert world.has_component(entity, Position)
        retrieved = world.get_component(entity, Position)
        assert retrieved.x == 1.0
        assert retrieved.y == 2.0

    def test_add_multiple_components(self):
        world = World()
        entity = world.create_entity()
        world.add_component(entity, Position(x=1.0, y=2.0))
        world.add_component(entity, Velocity(x=0.5, y=0.5))
        world.add_component(entity, Health(current=100, max=100))

        assert world.has_component(entity, Position)
        assert world.has_component(entity, Velocity)
        assert world.has_component(entity, Health)

        components = world.get_entity_components(entity)
        assert len(components) == 3

    def test_add_duplicate_component_raises(self):
        world = World()
        entity = world.create_entity()
        world.add_component(entity, Position(x=1.0, y=2.0))
        with pytest.raises(ComponentAlreadyExistsError):
            world.add_component(entity, Position(x=3.0, y=4.0))

    def test_add_component_to_nonexistent_entity_raises(self):
        world = World()
        entity = EntityId(999)
        with pytest.raises(EntityNotFoundError):
            world.add_component(entity, Position())

    def test_remove_component(self):
        world = World()
        entity = world.create_entity()
        world.add_component(entity, Position(x=1.0, y=2.0))
        world.remove_component(entity, Position)
        assert not world.has_component(entity, Position)

    def test_remove_nonexistent_component_raises(self):
        world = World()
        entity = world.create_entity()
        with pytest.raises(ComponentNotFoundError):
            world.remove_component(entity, Position)

    def test_get_nonexistent_component_raises(self):
        world = World()
        entity = world.create_entity()
        with pytest.raises(ComponentNotFoundError):
            world.get_component(entity, Position)

    def test_destroy_entity_removes_components(self):
        world = World()
        entity = world.create_entity()
        world.add_component(entity, Position(x=1.0, y=2.0))
        world.add_component(entity, Velocity(x=0.5, y=0.5))
        world.destroy_entity(entity)

        assert not world.has_component(entity, Position)
        assert not world.has_component(entity, Velocity)


class TestComponentTypeQuery:
    def test_query_entities_with_component(self):
        world = World()
        e1 = world.create_entity()
        e2 = world.create_entity()
        e3 = world.create_entity()

        world.add_component(e1, Position())
        world.add_component(e2, Position())
        world.add_component(e3, Velocity())

        entities_with_pos = list(world.get_entities_with_component(Position))
        assert len(entities_with_pos) == 2
        assert e1 in entities_with_pos
        assert e2 in entities_with_pos
        assert e3 not in entities_with_pos

    def test_query_empty_component_type(self):
        world = World()
        entities = list(world.get_entities_with_component(Position))
        assert len(entities) == 0

    def test_query_by_multiple_components(self):
        world = World()
        e1 = world.create_entity()
        e2 = world.create_entity()
        e3 = world.create_entity()

        world.add_component(e1, Position())
        world.add_component(e1, Velocity())
        world.add_component(e2, Position())
        world.add_component(e3, Position())
        world.add_component(e3, Velocity())
        world.add_component(e3, Health())

        results = list(world.query_entities([Position, Velocity]))
        assert len(results) == 2
        entity_ids = [e.id for e, _ in results]
        assert e1.id in entity_ids
        assert e3.id in entity_ids
        assert e2.id not in entity_ids

        for entity, (pos, vel) in results:
            assert isinstance(pos, Position)
            assert isinstance(vel, Velocity)

    def test_query_no_matching_entities(self):
        world = World()
        e1 = world.create_entity()
        world.add_component(e1, Position())

        results = list(world.query_entities([Position, Health]))
        assert len(results) == 0

    def test_query_uses_sparse_set_intersection(self):
        world = World()
        e1 = world.create_entity()
        e2 = world.create_entity()
        e3 = world.create_entity()
        e4 = world.create_entity()

        world.add_component(e1, Position())
        world.add_component(e1, Velocity())
        world.add_component(e2, Position())
        world.add_component(e3, Position())
        world.add_component(e3, Velocity())
        world.add_component(e3, Health())
        world.add_component(e4, Velocity())
        world.add_component(e4, Health())

        results = list(world.query_entities([Position, Velocity]))
        assert len(results) == 2
        entity_ids = [e.id for e, _ in results]
        assert e1.id in entity_ids
        assert e3.id in entity_ids

    def test_query_entities_and_archetype_return_same_results(self):
        world = World()
        for i in range(10):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            if i % 2 == 0:
                world.add_component(e, Velocity(x=0.5, y=0.5))
            if i % 3 == 0:
                world.add_component(e, Health(current=100, max=100))

        sparse_results = list(world.query_entities([Position, Velocity]))
        archetype_results = list(world.query_entities_archetype([Position, Velocity]))

        assert len(sparse_results) == len(archetype_results)

        sparse_ids = sorted(e.id for e, _ in sparse_results)
        archetype_ids = sorted(e.id for e, _ in archetype_results)
        assert sparse_ids == archetype_ids

    def test_single_data_source_no_duplicate_storage(self):
        world = World()
        e = world.create_entity()
        pos = Position(x=1.0, y=2.0)
        world.add_component(e, pos)

        assert not hasattr(world, '_entity_components')
        archetype = world._archetypes.get_entity_archetype(e)
        assert archetype is not None
        stored_pos = archetype.get_component(e, Position)
        assert stored_pos is pos

    def test_sparse_set_only_stores_indices_not_data(self):
        world = World()
        e = world.create_entity()
        world.add_component(e, Position(x=1.0, y=2.0))

        ss = world._components[Position]
        assert not hasattr(ss, '_components')
        assert hasattr(ss, '_sparse')
        assert hasattr(ss, '_dense')
        assert len(ss._dense) == 1
        assert len(ss._sparse) > 0


# ============================================================
# SparseSet Tests
# ============================================================


class TestSparseSet:
    def test_insert_and_contains(self):
        ss = SparseSet(Position)
        entity = EntityId(0)
        ss.insert(entity)
        assert ss.contains(entity)
        assert len(ss) == 1

    def test_insert_idempotent(self):
        ss = SparseSet(Position)
        entity = EntityId(0)
        ss.insert(entity)
        ss.insert(entity)
        assert ss.contains(entity)
        assert len(ss) == 1

    def test_remove(self):
        ss = SparseSet(Position)
        entity = EntityId(0)
        ss.insert(entity)
        ss.remove(entity)
        assert not ss.contains(entity)
        assert len(ss) == 0

    def test_remove_nonexistent_no_error(self):
        ss = SparseSet(Position)
        entity = EntityId(999)
        ss.remove(entity)

    def test_iter_entities(self):
        ss = SparseSet(Position)
        for i in range(5):
            ss.insert(EntityId(i))

        entities = list(ss.iter_entities())
        assert len(entities) == 5
        ids = {e.id for e in entities}
        assert ids == {0, 1, 2, 3, 4}

    def test_sparse_gap_handling(self):
        ss = SparseSet(Position)
        ss.insert(EntityId(100))
        assert ss.contains(EntityId(100))
        assert len(ss) == 1
        assert not ss.contains(EntityId(99))

    def test_clear(self):
        ss = SparseSet(Position)
        for i in range(10):
            ss.insert(EntityId(i))
        ss.clear()
        assert len(ss) == 0
        for i in range(10):
            assert not ss.contains(EntityId(i))

    def test_remove_maintains_dense_order(self):
        ss = SparseSet(Position)
        for i in range(5):
            ss.insert(EntityId(i))

        ss.remove(EntityId(2))

        entities = list(ss.iter_entities())
        ids = [e.id for e in entities]
        assert len(ids) == 4
        assert set(ids) == {0, 1, 3, 4}
        assert len(ss) == 4

    def test_get_component_from_sparse_set(self):
        world = World()
        e = world.create_entity()
        pos = Position(x=1.0, y=2.0)
        world.add_component(e, pos)

        ss = world._components[Position]
        retrieved = ss.get(e)
        assert retrieved is not None
        assert retrieved.x == 1.0
        assert retrieved.y == 2.0

    def test_get_nonexistent_returns_none(self):
        archetype_manager = ArchetypeManager()
        ss = SparseSet(Position, archetype_manager)
        entity = EntityId(999)
        assert ss.get(entity) is None

    def test_getitem_operator(self):
        world = World()
        e = world.create_entity()
        pos = Position(x=3.0, y=4.0)
        world.add_component(e, pos)

        ss = world._components[Position]
        retrieved = ss[e]
        assert retrieved.x == 3.0
        assert retrieved.y == 4.0

    def test_getitem_nonexistent_raises(self):
        archetype_manager = ArchetypeManager()
        ss = SparseSet(Position, archetype_manager)
        entity = EntityId(999)
        with pytest.raises(KeyError):
            ss[entity]

    def test_iter_components(self):
        world = World()
        positions = [Position(x=float(i), y=float(i)) for i in range(3)]
        for i, pos in enumerate(positions):
            e = world.create_entity()
            world.add_component(e, pos)

        ss = world._components[Position]
        components = list(ss.iter_components())
        assert len(components) == 3
        x_values = sorted(c.x for c in components)
        assert x_values == [0.0, 1.0, 2.0]

    def test_iter_entities_and_components(self):
        world = World()
        for i in range(3):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))

        ss = world._components[Position]
        results = list(ss.iter())
        assert len(results) == 3
        for entity, pos in results:
            assert isinstance(entity, EntityId)
            assert isinstance(pos, Position)

    def test_contains_operator(self):
        ss = SparseSet(Position)
        entity = EntityId(0)
        ss.insert(entity)
        assert entity in ss
        assert EntityId(1) not in ss


# ============================================================
# Archetype Tests
# ============================================================


class TestArchetypeGrouping:
    def test_single_archetype(self):
        world = World()
        for _ in range(10):
            e = world.create_entity()
            world.add_component(e, Position())
            world.add_component(e, Velocity())

        assert world.count_archetypes() == 1

    def test_multiple_archetypes(self):
        world = World()

        for _ in range(3):
            e = world.create_entity()
            world.add_component(e, Position())

        for _ in range(5):
            e = world.create_entity()
            world.add_component(e, Position())
            world.add_component(e, Velocity())

        for _ in range(2):
            e = world.create_entity()
            world.add_component(e, Health())

        assert world.count_archetypes() == 3

    def test_remove_component_changes_archetype(self):
        world = World()
        e = world.create_entity()
        world.add_component(e, Position())
        world.add_component(e, Velocity())

        initial_archetype = world.get_entity_archetype(e)
        assert initial_archetype is not None
        assert Position in initial_archetype
        assert Velocity in initial_archetype

        world.remove_component(e, Velocity)

        new_archetype = world.get_entity_archetype(e)
        assert new_archetype is not None
        assert Position in new_archetype
        assert Velocity not in new_archetype

        assert world.count_archetypes() == 1

    def test_add_component_changes_archetype(self):
        world = World()
        e = world.create_entity()
        world.add_component(e, Position())

        initial_archetype = world.get_entity_archetype(e)
        assert len(initial_archetype) == 1

        world.add_component(e, Velocity())

        new_archetype = world.get_entity_archetype(e)
        assert len(new_archetype) == 2

    def test_query_by_archetype(self):
        world = World()

        for _ in range(5):
            e = world.create_entity()
            world.add_component(e, Position(x=1.0, y=2.0))
            world.add_component(e, Velocity(x=0.5, y=0.5))

        for _ in range(3):
            e = world.create_entity()
            world.add_component(e, Position(x=3.0, y=4.0))
            world.add_component(e, Velocity(x=1.0, y=1.0))
            world.add_component(e, Health(current=100, max=100))

        results = list(world.query_entities_archetype([Position, Velocity]))
        assert len(results) == 8

        for entity, (pos, vel) in results:
            assert isinstance(pos, Position)
            assert isinstance(vel, Velocity)

    def test_query_by_archetype_no_match(self):
        world = World()
        e = world.create_entity()
        world.add_component(e, Position())

        results = list(world.query_entities_archetype([Position, Health]))
        assert len(results) == 0

    def test_single_archetype_entity_traversal(self):
        world = World()
        n = 100
        for i in range(n):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            world.add_component(e, Velocity(x=0.1, y=0.1))

        results = list(world.query_entities_archetype([Position, Velocity]))
        assert len(results) == n

        positions = [pos.x for _, (pos, _) in results]
        positions.sort()
        for i in range(n):
            assert positions[i] == float(i)

    def test_archetype_entity_removal(self):
        world = World()
        e1 = world.create_entity()
        e2 = world.create_entity()

        world.add_component(e1, Position())
        world.add_component(e2, Position())

        assert world.count_archetypes() == 1

        world.destroy_entity(e1)

        results = list(world.query_entities_archetype([Position]))
        assert len(results) == 1
        assert results[0][0].id == e2.id


# ============================================================
# System Scheduler Tests - Normal Flows
# ============================================================


class TestSystemTopologicalOrder:
    def test_systems_sorted_by_dependency(self):
        scheduler = SystemScheduler()

        execution_order: list[str] = []

        def make_system(name: str, reads=None, writes=None):
            def update_fn(world, sys):
                execution_order.append(name)

            return System(name, read_components=reads, write_components=writes, update=update_fn)

        s1 = make_system("velocity_writer", writes=[Velocity])
        s2 = make_system("position_updater", reads=[Velocity], writes=[Position])
        s3 = make_system("renderer", reads=[Position])

        scheduler.add_system(s3)
        scheduler.add_system(s1)
        scheduler.add_system(s2)

        order = scheduler.get_order()
        assert order.index("velocity_writer") < order.index("position_updater")
        assert order.index("position_updater") < order.index("renderer")

    def test_systems_execute_in_order(self):
        scheduler = SystemScheduler()
        world = World()

        execution_order: list[str] = []

        def make_system(name, reads=None, writes=None):
            def update_fn(w, s):
                execution_order.append(name)
            return System(name, read_components=reads, write_components=writes, update=update_fn)

        scheduler.add_system(make_system("s1", writes=[Position]))
        scheduler.add_system(make_system("s2", reads=[Position], writes=[Velocity]))
        scheduler.add_system(make_system("s3", reads=[Velocity]))

        scheduler.update(world)

        assert execution_order == ["s1", "s2", "s3"]

    def test_system_with_no_dependencies(self):
        scheduler = SystemScheduler()
        world = World()

        executed = []

        def update_fn(w, s):
            executed.append(True)

        sys = System("standalone", update=update_fn)
        scheduler.add_system(sys)

        scheduler.update(world)
        assert len(executed) == 1
        assert scheduler.get_order() == ["standalone"]

    def test_multiple_systems_no_dependencies(self):
        scheduler = SystemScheduler()
        world = World()

        execution_order: list[str] = []

        def make_system(name):
            def update_fn(w, s):
                execution_order.append(name)
            return System(name, update=update_fn)

        for name in ["a", "b", "c"]:
            scheduler.add_system(make_system(name))

        scheduler.update(world)
        assert len(execution_order) == 3
        assert set(execution_order) == {"a", "b", "c"}

    def test_read_write_conflict_ordering(self):
        scheduler = SystemScheduler()

        def make_system(name, reads=None, writes=None):
            return System(name, read_components=reads, write_components=writes)

        s_read = make_system("reader", reads=[Position])
        s_write = make_system("writer", writes=[Position])

        scheduler.add_system(s_read)
        scheduler.add_system(s_write)

        order = scheduler.get_order()
        assert order.index("writer") < order.index("reader")

    def test_pure_writer_before_pure_reader(self):
        scheduler = SystemScheduler()

        s_write = System("writer", write_components=[Position])
        s_read = System("reader", read_components=[Position])

        scheduler.add_system(s_write)
        scheduler.add_system(s_read)

        order = scheduler.get_order()
        assert order.index("writer") < order.index("reader")

    def test_writer_with_read_before_pure_reader(self):
        scheduler = SystemScheduler()

        s_writer = System("writer", read_components=[Velocity], write_components=[Position])
        s_reader = System("reader", read_components=[Position])

        scheduler.add_system(s_writer)
        scheduler.add_system(s_reader)

        order = scheduler.get_order()
        assert order.index("writer") < order.index("reader")

    def test_write_write_conflict_ordering(self):
        scheduler = SystemScheduler()

        def make_system(name, writes):
            return System(name, write_components=writes)

        s1 = make_system("writer1", [Position])
        s2 = make_system("writer2", [Position])

        scheduler.add_system(s1)
        scheduler.add_system(s2)

        order = scheduler.get_order()
        assert "writer1" in order
        assert "writer2" in order

    def test_system_queries_entities(self):
        world = World()
        scheduler = SystemScheduler()

        for i in range(5):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            world.add_component(e, Velocity(x=0.1, y=0.1))

        processed: list[int] = []

        def movement_update(w, s):
            for entity, (pos, vel) in s.query(w):
                pos.x += vel.x
                pos.y += vel.y
                processed.append(entity.id)

        movement = System(
            "movement",
            read_components=[Velocity],
            write_components=[Position],
            update=movement_update,
        )
        scheduler.add_system(movement)
        scheduler.update(world)

        assert len(processed) == 5
        for entity in world.iter_entities():
            pos = world.get_component(entity, Position)
            assert pos.x >= 0.1
            assert pos.y >= 0.1

    def test_system_query_by_archetype(self):
        world = World()
        scheduler = SystemScheduler()

        for i in range(3):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            world.add_component(e, Health(current=100, max=100))

        results: list[tuple[float, int]] = []

        def update_fn(w, s):
            for entity, (health, pos) in s.query_by_archetype(w):
                results.append((pos.x, health.current))

        sys = System(
            "query_test",
            read_components=[Position, Health],
            update=update_fn,
        )
        scheduler.add_system(sys)
        scheduler.update(world)

        assert len(results) == 3


# ============================================================
# System Scheduler Tests - Edge Cases
# ============================================================


class TestSystemEdgeCases:
    def test_system_with_no_matching_entities(self):
        world = World()
        scheduler = SystemScheduler()

        processed = []

        def update_fn(w, s):
            for _ in s.query(w):
                processed.append(True)

        sys = System(
            "test",
            read_components=[Position, Velocity],
            update=update_fn,
        )
        scheduler.add_system(sys)
        scheduler.update(world)

        assert len(processed) == 0

    def test_system_runs_with_empty_world(self):
        world = World()
        scheduler = SystemScheduler()

        ran = False

        def update_fn(w, s):
            nonlocal ran
            ran = True

        sys = System("test", update=update_fn)
        scheduler.add_system(sys)
        scheduler.update(world)

        assert ran is True

    def test_remove_system(self):
        scheduler = SystemScheduler()
        sys = System("test")
        scheduler.add_system(sys)
        assert scheduler.has_system("test")
        scheduler.remove_system("test")
        assert not scheduler.has_system("test")

    def test_remove_nonexistent_system_raises(self):
        scheduler = SystemScheduler()
        with pytest.raises(SystemNotFoundError):
            scheduler.remove_system("nonexistent")

    def test_add_duplicate_system_raises(self):
        scheduler = SystemScheduler()
        sys1 = System("test")
        sys2 = System("test")
        scheduler.add_system(sys1)
        with pytest.raises(SystemAlreadyExistsError):
            scheduler.add_system(sys2)

    def test_get_nonexistent_system_raises(self):
        scheduler = SystemScheduler()
        with pytest.raises(SystemNotFoundError):
            scheduler.get_system("nonexistent")

    def test_empty_scheduler(self):
        scheduler = SystemScheduler()
        assert scheduler.list_systems() == []
        assert scheduler.get_order() == []
        world = World()
        scheduler.update(world)

    def test_clear_scheduler(self):
        scheduler = SystemScheduler()
        scheduler.add_system(System("s1"))
        scheduler.add_system(System("s2"))
        scheduler.clear()
        assert scheduler.list_systems() == []


# ============================================================
# System Scheduler Tests - Error Cases
# ============================================================


class TestSystemErrorCases:
    def test_circular_dependency_detection(self):
        scheduler = SystemScheduler()

        def make_system(name, reads=None, writes=None):
            return System(name, read_components=reads, write_components=writes)

        s1 = make_system("s1", reads=[Velocity], writes=[Position])
        s2 = make_system("s2", reads=[Position], writes=[Velocity])

        scheduler.add_system(s1)
        scheduler.add_system(s2)

        with pytest.raises(CircularDependencyError) as exc_info:
            scheduler.sort()

        cycle = exc_info.value.cycle
        assert "s1" in cycle
        assert "s2" in cycle

    def test_complex_circular_dependency(self):
        scheduler = SystemScheduler()

        def make_system(name, reads=None, writes=None):
            return System(name, read_components=reads, write_components=writes)

        s1 = make_system("s1", writes=[Position])
        s2 = make_system("s2", reads=[Position], writes=[Velocity])
        s3 = make_system("s3", reads=[Velocity], writes=[Health])
        s4 = make_system("s4", reads=[Health], writes=[Position])

        scheduler.add_system(s1)
        scheduler.add_system(s2)
        scheduler.add_system(s3)
        scheduler.add_system(s4)

        with pytest.raises(CircularDependencyError):
            scheduler.sort()

    def test_circular_detection_on_update(self):
        scheduler = SystemScheduler()
        world = World()

        def make_system(name, reads=None, writes=None):
            return System(name, read_components=reads, write_components=writes)

        scheduler.add_system(make_system("a", writes=[Position]))
        scheduler.add_system(make_system("b", reads=[Position], writes=[Velocity]))
        scheduler.add_system(make_system("c", reads=[Velocity], writes=[Position]))

        with pytest.raises(CircularDependencyError):
            scheduler.update(world)


# ============================================================
# Full Integration Tests
# ============================================================


class TestFullIntegration:
    def test_movement_system_integration(self):
        world = World()
        scheduler = SystemScheduler()

        for i in range(10):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            world.add_component(e, Velocity(x=1.0, y=2.0))

        def movement_update(w, s):
            for entity, (pos, vel) in s.query_by_archetype(w):
                pos.x += vel.x
                pos.y += vel.y

        movement = System(
            "movement",
            read_components=[Velocity],
            write_components=[Position],
            update=movement_update,
        )
        scheduler.add_system(movement)

        initial_positions = {}
        for entity in world.get_entities_with_component(Position):
            pos = world.get_component(entity, Position)
            initial_positions[entity.id] = (pos.x, pos.y)

        scheduler.update(world)

        for entity in world.get_entities_with_component(Position):
            pos = world.get_component(entity, Position)
            init_x, init_y = initial_positions[entity.id]
            assert pos.x == init_x + 1.0
            assert pos.y == init_y + 2.0

    def test_health_system_integration(self):
        world = World()
        scheduler = SystemScheduler()

        for i in range(5):
            e = world.create_entity()
            world.add_component(e, Health(current=100, max=100))
            if i < 3:
                world.add_component(e, Tag(value="damaged"))

        def damage_update(w, s):
            for entity, (health, tag) in s.query_by_archetype(w):
                if tag.value == "damaged":
                    health.current -= 10

        damage = System(
            "damage",
            read_components=[Tag],
            write_components=[Health],
            update=damage_update,
        )
        scheduler.add_system(damage)
        scheduler.update(world)

        damaged_count = 0
        for entity in world.get_entities_with_component(Health):
            health = world.get_component(entity, Health)
            if world.has_component(entity, Tag):
                assert health.current == 90
                damaged_count += 1
            else:
                assert health.current == 100

        assert damaged_count == 3

    def test_multiple_systems_pipeline(self):
        world = World()
        scheduler = SystemScheduler()

        for i in range(5):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            world.add_component(e, Velocity(x=1.0, y=1.0))
            world.add_component(e, Score(value=0))

        execution_log: list[str] = []

        def movement_update(w, s):
            execution_log.append("movement")
            for entity, (pos, vel) in s.query_by_archetype(w):
                pos.x += vel.x
                pos.y += vel.y

        def scoring_update(w, s):
            execution_log.append("scoring")
            for entity, (pos, score) in s.query_by_archetype(w):
                score.value = int(pos.x + pos.y)

        movement = System(
            "movement",
            read_components=[Velocity],
            write_components=[Position],
            update=movement_update,
        )
        scoring = System(
            "scoring",
            read_components=[Position],
            write_components=[Score],
            update=scoring_update,
        )

        scheduler.add_system(scoring)
        scheduler.add_system(movement)

        scheduler.update(world)

        assert execution_log == ["movement", "scoring"]

        for entity in world.get_entities_with_component(Score):
            score = world.get_component(entity, Score)
            pos = world.get_component(entity, Position)
            assert score.value == int(pos.x + pos.y)

    def test_archetype_regrouping_after_removal(self):
        world = World()
        scheduler = SystemScheduler()

        entities = []
        for i in range(5):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))
            world.add_component(e, Velocity(x=1.0, y=1.0))
            if i < 2:
                world.add_component(e, Health(current=100, max=100))
            entities.append(e)

        archetype_count = world.count_archetypes()
        assert archetype_count == 2

        with_health = list(world.query_entities_archetype([Position, Velocity, Health]))
        assert len(with_health) == 2

        world.remove_component(entities[0], Health)

        assert world.count_archetypes() == 2

        results = list(world.query_entities_archetype([Position, Velocity]))
        assert len(results) == 5

        results_with_health = list(world.query_entities_archetype([Position, Velocity, Health]))
        assert len(results_with_health) == 1
        assert results_with_health[0][0].id == entities[1].id

    def test_component_decorator(self):
        @component
        class MyComponent:
            value: int

        from solocoder_py.ecs import is_component_type
        assert is_component_type(MyComponent)

        world = World()
        e = world.create_entity()
        world.add_component(e, MyComponent(value=42))
        comp = world.get_component(e, MyComponent)
        assert comp.value == 42

    def test_world_clear(self):
        world = World()
        for i in range(10):
            e = world.create_entity()
            world.add_component(e, Position(x=float(i), y=float(i)))

        assert world.entity_count() == 10
        world.clear()
        assert world.entity_count() == 0
        assert world.count_archetypes() == 0
