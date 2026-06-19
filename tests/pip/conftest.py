from solocoder_py.pip import Point, Polygon, RayCastingEngine


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
        (3, 5),
        (7, 5),
        (10, 0),
        (10, 10),
        (0, 10),
    ])


def build_butterfly_polygon():
    return Polygon.from_tuples([
        (0, 0),
        (10, 10),
        (0, 10),
        (10, 0),
    ])


def build_engine():
    return RayCastingEngine()
