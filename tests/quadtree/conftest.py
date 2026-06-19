from solocoder_py.quadtree import Point, Quadtree, Rectangle


def build_quadtree_with_points(max_capacity: int = 4, max_depth: int = 10):
    boundary = Rectangle(x=0, y=0, width=200, height=200)
    qt = Quadtree(boundary, max_capacity=max_capacity, max_depth=max_depth)

    p1 = Point(x=25, y=25, data="sw1")
    p2 = Point(x=75, y=25, data="se1")
    p3 = Point(x=25, y=75, data="nw1")
    p4 = Point(x=75, y=75, data="ne1")
    p5 = Point(x=30, y=30, data="sw2")

    qt.insert(p1)
    qt.insert(p2)
    qt.insert(p3)
    qt.insert(p4)

    return qt, p1, p2, p3, p4, p5
