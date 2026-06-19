from solocoder_py.pip import Point, Polygon, PolygonWithHoles, RayCastingEngine


def build_square_polygon():
    return Polygon.from_tuples([
        (0, 0),
        (10, 0),
        (10, 10),
        (0, 10),
    ])


def build_triangle_polygon():
    return Polygon.from_tuples([
        (0, 0),
        (10, 0),
        (5, 10),
    ])


def build_concave_polygon():
    return Polygon.from_tuples([
        (0, 0),
        (10, 0),
        (10, 10),
        (7, 5),
        (3, 5),
        (0, 10),
    ])


def build_butterfly_polygon():
    return Polygon.from_tuples([
        (0, 0),
        (10, 10),
        (0, 10),
        (10, 0),
    ])


def build_holed_polygon():
    return PolygonWithHoles.from_tuples(
        outer_ring=[
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ],
        inner_rings=[
            [
                (3, 3),
                (7, 3),
                (7, 7),
                (3, 7),
            ],
        ],
    )


def build_engine():
    return RayCastingEngine()
