import pytest

from solocoder_py.pathfinding import (
    AStarFinder,
    CellType,
    CoordinateOutOfBoundsError,
    GoalNotPassableError,
    GridMap,
    InvalidGridDimensionsError,
    NoPathFoundError,
    PathResult,
    Point,
    PathfindingError,
    StartNotPassableError,
    manhattan_distance,
    octile_distance,
    simplify_path,
    simplify_path_result,
)


@pytest.fixture
def open_grid():
    return GridMap(width=10, height=10)


@pytest.fixture
def grid_with_wall():
    grid = GridMap(width=10, height=10)
    for y in range(1, 9):
        grid.set_wall(Point(5, y))
    return grid


@pytest.fixture
def finder(open_grid):
    return AStarFinder(open_grid, allow_diagonal=True)


@pytest.fixture
def finder_no_diagonal(open_grid):
    return AStarFinder(open_grid, allow_diagonal=False)


class TestGridMap:
    def test_create_grid(self):
        grid = GridMap(width=5, height=3)
        assert grid.width == 5
        assert grid.height == 3

    def test_invalid_dimensions(self):
        with pytest.raises(InvalidGridDimensionsError):
            GridMap(width=0, height=5)
        with pytest.raises(InvalidGridDimensionsError):
            GridMap(width=5, height=0)
        with pytest.raises(InvalidGridDimensionsError):
            GridMap(width=-1, height=5)

    def test_default_cells_passable(self, open_grid):
        for y in range(open_grid.height):
            for x in range(open_grid.width):
                assert open_grid.is_passable(Point(x, y))

    def test_default_weight(self, open_grid):
        assert open_grid.get_weight(Point(0, 0)) == 1.0

    def test_set_wall(self, open_grid):
        p = Point(3, 3)
        open_grid.set_wall(p)
        assert not open_grid.is_passable(p)

    def test_set_passable(self, open_grid):
        p = Point(3, 3)
        open_grid.set_wall(p)
        open_grid.set_passable(p, True)
        assert open_grid.is_passable(p)

    def test_set_weight(self, open_grid):
        p = Point(2, 2)
        open_grid.set_weight(p, 5.0)
        assert open_grid.get_weight(p) == 5.0

    def test_set_weight_invalid(self, open_grid):
        with pytest.raises(ValueError):
            open_grid.set_weight(Point(0, 0), 0.0)
        with pytest.raises(ValueError):
            open_grid.set_weight(Point(0, 0), -1.0)

    def test_set_terrain(self, open_grid):
        p = Point(4, 4)
        open_grid.set_terrain(p, weight=3.0, passable=True)
        assert open_grid.is_passable(p)
        assert open_grid.get_weight(p) == 3.0

    def test_in_bounds(self, open_grid):
        assert open_grid.in_bounds(Point(0, 0))
        assert open_grid.in_bounds(Point(9, 9))
        assert not open_grid.in_bounds(Point(10, 0))
        assert not open_grid.in_bounds(Point(0, 10))
        assert not open_grid.in_bounds(Point(-1, 0))

    def test_get_cell_out_of_bounds(self, open_grid):
        with pytest.raises(CoordinateOutOfBoundsError):
            open_grid.get_cell(Point(10, 0))

    def test_is_passable_out_of_bounds(self, open_grid):
        assert not open_grid.is_passable(Point(10, 0))
        assert not open_grid.is_passable(Point(-1, 0))

    def test_get_neighbors_cardinal(self, open_grid):
        neighbors = open_grid.get_neighbors(Point(5, 5), allow_diagonal=False)
        assert len(neighbors) == 4
        points = {n[0] for n in neighbors}
        assert Point(5, 4) in points
        assert Point(5, 6) in points
        assert Point(4, 5) in points
        assert Point(6, 5) in points

    def test_get_neighbors_diagonal(self, open_grid):
        neighbors = open_grid.get_neighbors(Point(5, 5), allow_diagonal=True)
        assert len(neighbors) == 8

    def test_get_neighbors_corner(self, open_grid):
        neighbors = open_grid.get_neighbors(Point(0, 0), allow_diagonal=True)
        assert len(neighbors) == 3
        points = {n[0] for n in neighbors}
        assert Point(1, 0) in points
        assert Point(0, 1) in points
        assert Point(1, 1) in points

    def test_diagonal_cost(self, open_grid):
        neighbors = open_grid.get_neighbors(Point(5, 5), allow_diagonal=True)
        for point, cost in neighbors:
            if point.x != 5 and point.y != 5:
                assert abs(cost - 1.414) < 0.01
            else:
                assert cost == 1.0

    def test_weighted_neighbor_cost(self, open_grid):
        open_grid.set_weight(Point(6, 5), 3.0)
        neighbors = open_grid.get_neighbors(Point(5, 5), allow_diagonal=False)
        for point, cost in neighbors:
            if point == Point(6, 5):
                assert abs(cost - 3.0) < 0.01

    def test_diagonal_corner_cutting_blocked(self, open_grid):
        open_grid.set_wall(Point(1, 0))
        open_grid.set_wall(Point(0, 1))
        neighbors = open_grid.get_neighbors(Point(0, 0), allow_diagonal=True)
        points = {n[0] for n in neighbors}
        assert Point(1, 1) not in points

    def test_from_char_map(self):
        char_map = [
            "...",
            ".#.",
            "...",
        ]
        grid = GridMap.from_char_map(char_map)
        assert grid.width == 3
        assert grid.height == 3
        assert not grid.is_passable(Point(1, 1))
        assert grid.is_passable(Point(0, 0))

    def test_from_char_map_with_weights(self):
        char_map = [
            ".~.",
            "...",
        ]
        grid = GridMap.from_char_map(char_map, weight_map={"~": 5.0})
        assert grid.get_weight(Point(1, 0)) == 5.0

    def test_from_char_map_empty(self):
        with pytest.raises(InvalidGridDimensionsError):
            GridMap.from_char_map([])
        with pytest.raises(InvalidGridDimensionsError):
            GridMap.from_char_map([""])


class TestHeuristics:
    def test_manhattan_distance(self):
        assert manhattan_distance(Point(0, 0), Point(3, 4)) == 7.0

    def test_manhattan_same_point(self):
        assert manhattan_distance(Point(2, 3), Point(2, 3)) == 0.0

    def test_octile_distance_cardinal(self):
        dist = octile_distance(Point(0, 0), Point(3, 0))
        assert abs(dist - 3.0) < 0.01

    def test_octile_distance_diagonal(self):
        dist = octile_distance(Point(0, 0), Point(3, 3))
        expected = 3 * 1.414
        assert abs(dist - expected) < 0.01

    def test_octile_distance_mixed(self):
        dist = octile_distance(Point(0, 0), Point(3, 5))
        expected = 5 + (1.414 - 1) * 3
        assert abs(dist - expected) < 0.01


class TestAStarNormalFlow:
    def test_straight_line_path(self, finder, open_grid):
        result = finder.find_path(Point(0, 0), Point(5, 0))
        assert result.found
        assert result.path[0] == Point(0, 0)
        assert result.path[-1] == Point(5, 0)

    def test_open_map_path_cost(self, finder, open_grid):
        result = finder.find_path(Point(0, 0), Point(3, 0))
        assert result.found
        assert abs(result.cost - 3.0) < 0.01

    def test_diagonal_path_cost(self, finder, open_grid):
        result = finder.find_path(Point(0, 0), Point(3, 3))
        assert result.found
        expected_cost = 3 * 1.414
        assert abs(result.cost - expected_cost) < 0.05

    def test_path_around_wall(self, grid_with_wall):
        finder = AStarFinder(grid_with_wall, allow_diagonal=False)
        result = finder.find_path(Point(0, 5), Point(9, 5))
        assert result.found
        assert result.path[0] == Point(0, 5)
        assert result.path[-1] == Point(9, 5)
        for pt in result.path:
            assert grid_with_wall.is_passable(pt)

    def test_diagonal_bypass_obstacle(self):
        grid = GridMap(width=5, height=5)
        grid.set_wall(Point(2, 1))
        grid.set_wall(Point(2, 2))
        grid.set_wall(Point(2, 3))
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 2), Point(4, 2))
        assert result.found
        assert result.path[0] == Point(0, 2)
        assert result.path[-1] == Point(4, 2)

    def test_no_diagonal_bypass_obstacle(self):
        grid = GridMap(width=5, height=5)
        grid.set_wall(Point(2, 1))
        grid.set_wall(Point(2, 2))
        grid.set_wall(Point(2, 3))
        finder = AStarFinder(grid, allow_diagonal=False)
        result = finder.find_path(Point(0, 2), Point(4, 2))
        assert result.found

    def test_custom_heuristic(self, open_grid):
        finder = AStarFinder(open_grid, heuristic=manhattan_distance)
        result = finder.find_path(Point(0, 0), Point(3, 3))
        assert result.found

    def test_cardinal_only_movement(self, finder_no_diagonal, open_grid):
        result = finder_no_diagonal.find_path(Point(0, 0), Point(3, 3))
        assert result.found
        for i in range(len(result.path) - 1):
            curr = result.path[i]
            nxt = result.path[i + 1]
            dx = abs(nxt.x - curr.x)
            dy = abs(nxt.y - curr.y)
            assert dx <= 1 and dy <= 1


class TestAStarBoundaryConditions:
    def test_start_equals_goal(self, finder):
        result = finder.find_path(Point(5, 5), Point(5, 5))
        assert result.found
        assert result.path == [Point(5, 5)]
        assert result.cost == 0.0

    def test_single_row_map(self):
        grid = GridMap(width=5, height=1)
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 0), Point(4, 0))
        assert result.found
        assert result.path[0] == Point(0, 0)
        assert result.path[-1] == Point(4, 0)

    def test_single_column_map(self):
        grid = GridMap(width=1, height=5)
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 0), Point(0, 4))
        assert result.found
        assert result.path[0] == Point(0, 0)
        assert result.path[-1] == Point(0, 4)

    def test_narrow_corridor(self):
        grid = GridMap(width=3, height=10)
        for y in range(10):
            grid.set_wall(Point(0, y))
            grid.set_wall(Point(2, y))
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(1, 0), Point(1, 9))
        assert result.found

    def test_corridor_with_border_walls(self):
        grid = GridMap(width=5, height=7)
        for x in range(5):
            grid.set_wall(Point(x, 0))
            grid.set_wall(Point(x, 6))
        for y in range(7):
            grid.set_wall(Point(0, y))
            grid.set_wall(Point(4, y))
        grid.set_passable(Point(1, 0), True)
        grid.set_passable(Point(1, 6), True)
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(1, 0), Point(1, 6))
        assert result.found


class TestAStarExceptionBranches:
    def test_start_not_passable(self, open_grid):
        open_grid.set_wall(Point(0, 0))
        finder = AStarFinder(open_grid)
        with pytest.raises(StartNotPassableError):
            finder.find_path(Point(0, 0), Point(5, 5))

    def test_goal_not_passable(self, open_grid):
        open_grid.set_wall(Point(5, 5))
        finder = AStarFinder(open_grid)
        with pytest.raises(GoalNotPassableError):
            finder.find_path(Point(0, 0), Point(5, 5))

    def test_start_out_of_bounds(self, open_grid):
        finder = AStarFinder(open_grid)
        with pytest.raises(CoordinateOutOfBoundsError):
            finder.find_path(Point(-1, 0), Point(5, 5))

    def test_goal_out_of_bounds(self, open_grid):
        finder = AStarFinder(open_grid)
        with pytest.raises(CoordinateOutOfBoundsError):
            finder.find_path(Point(0, 0), Point(100, 0))

    def test_unreachable_path(self):
        grid = GridMap(width=5, height=5)
        for y in range(5):
            grid.set_wall(Point(2, y))
        finder = AStarFinder(grid, allow_diagonal=False)
        result = finder.find_path(Point(0, 2), Point(4, 2))
        assert not result.found
        assert result.failure_reason is not None
        assert "not reachable" in result.failure_reason or "No path" in result.failure_reason

    def test_surrounded_goal(self):
        grid = GridMap(width=5, height=5)
        grid.set_wall(Point(3, 2))
        grid.set_wall(Point(3, 4))
        grid.set_wall(Point(2, 3))
        grid.set_wall(Point(4, 3))
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 0), Point(3, 3))
        assert not result.found
        assert result.failure_reason is not None

    def test_high_cost_detour_vs_short_path(self):
        grid = GridMap(width=10, height=3)
        for x in range(1, 9):
            grid.set_terrain(Point(x, 1), weight=10.0)
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 1), Point(9, 1))
        assert result.found
        went_around = any(pt.y != 1 for pt in result.path[1:-1])
        assert went_around

    def test_high_cost_straight_through_cheaper(self):
        grid = GridMap(width=5, height=5)
        grid.set_terrain(Point(2, 0), weight=1.5)
        grid.set_terrain(Point(3, 0), weight=1.5)
        finder = AStarFinder(grid, allow_diagonal=False)
        result = finder.find_path(Point(0, 0), Point(4, 0))
        assert result.found
        straight_cost = 1.0 + 1.0 + 1.5 + 1.5 + 1.0
        assert result.cost <= straight_cost + 0.01


class TestPathSimplifier:
    def test_straight_line_simplification(self):
        path = [Point(0, 0), Point(1, 0), Point(2, 0), Point(3, 0)]
        simplified = simplify_path(path)
        assert simplified == [Point(0, 0), Point(3, 0)]

    def test_l_shaped_path(self):
        path = [Point(0, 0), Point(1, 0), Point(2, 0), Point(2, 1), Point(2, 2)]
        simplified = simplify_path(path)
        assert simplified == [Point(0, 0), Point(2, 0), Point(2, 2)]

    def test_diagonal_line_simplification(self):
        path = [Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3)]
        simplified = simplify_path(path)
        assert simplified == [Point(0, 0), Point(3, 3)]

    def test_short_path_no_simplification(self):
        path = [Point(0, 0), Point(1, 0)]
        simplified = simplify_path(path)
        assert simplified == path

    def test_single_point(self):
        path = [Point(0, 0)]
        simplified = simplify_path(path)
        assert simplified == path

    def test_zigzag_path(self):
        path = [
            Point(0, 0),
            Point(1, 0),
            Point(1, 1),
            Point(2, 1),
            Point(2, 2),
        ]
        simplified = simplify_path(path)
        assert len(simplified) <= len(path)
        assert simplified[0] == Point(0, 0)
        assert simplified[-1] == Point(2, 2)

    def test_simplify_path_result(self, finder, open_grid):
        result = finder.find_path(Point(0, 0), Point(5, 0))
        simplified_result = simplify_path_result(result)
        assert simplified_result.simplified_path is not None
        assert len(simplified_result.simplified_path) <= len(result.path)

    def test_simplify_failed_path(self):
        result = PathResult(path=[], cost=float("inf"), failure_reason="blocked")
        simplified = simplify_path_result(result)
        assert not simplified.found
        assert simplified.simplified_path is None

    def test_collinear_with_different_directions(self):
        path = [Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 2), Point(4, 2)]
        simplified = simplify_path(path)
        assert Point(1, 1) not in simplified
        assert Point(2, 2) in simplified


class TestPathResult:
    def test_found_property_true(self):
        result = PathResult(path=[Point(0, 0), Point(1, 0)], cost=1.0)
        assert result.found

    def test_found_property_false_no_path(self):
        result = PathResult(path=[], cost=float("inf"), failure_reason="blocked")
        assert not result.found

    def test_length_property(self):
        result = PathResult(path=[Point(0, 0), Point(1, 0), Point(2, 0)], cost=2.0)
        assert result.length == 3


class TestPoint:
    def test_point_addition(self):
        p = Point(1, 2) + Point(3, 4)
        assert p == Point(4, 6)

    def test_point_iteration(self):
        x, y = Point(3, 5)
        assert x == 3
        assert y == 5

    def test_point_frozen(self):
        p = Point(1, 2)
        with pytest.raises(AttributeError):
            p.x = 5


class TestIntegration:
    def test_full_workflow(self):
        grid = GridMap(width=10, height=10)
        for y in range(3, 7):
            grid.set_wall(Point(5, y))
        grid.set_terrain(Point(3, 3), weight=5.0)
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 0), Point(9, 9))
        assert result.found
        assert result.path[0] == Point(0, 0)
        assert result.path[-1] == Point(9, 9)
        simplified_result = simplify_path_result(result)
        assert simplified_result.simplified_path is not None
        assert len(simplified_result.simplified_path) <= len(result.path)

    def test_char_map_workflow(self):
        char_map = [
            "..........",
            "..........",
            "...####...",
            "..........",
            "..........",
            "...####...",
            "..........",
            "..........",
            "..........",
            "..........",
        ]
        grid = GridMap.from_char_map(char_map)
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 0), Point(9, 9))
        assert result.found

    def test_weighted_terrain_workflow(self):
        char_map = [
            ".....",
            ".~~~.",
            ".~~~.",
            ".~~~.",
            ".....",
        ]
        grid = GridMap.from_char_map(char_map, weight_map={"~": 5.0})
        finder = AStarFinder(grid, allow_diagonal=True)
        result = finder.find_path(Point(0, 2), Point(4, 2))
        assert result.found
        around_cost = 2 * 1.0 + 3 * 1.0 + 2 * 1.0
        through_cost = 2 * 1.0 + 3 * 5.0 + 2 * 1.0
        assert result.cost < through_cost
