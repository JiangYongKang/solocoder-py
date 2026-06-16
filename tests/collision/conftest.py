from solocoder_py.collision import (
    AABB,
    Collider,
    CollisionEngine,
)


def build_engine_with_colliders(cell_size: float = 100.0):
    engine = CollisionEngine(cell_size=cell_size)

    c1 = Collider(
        id="c1",
        aabb=AABB(min_x=10, min_y=10, max_x=40, max_y=40),
        data={"type": "player"},
    )
    c2 = Collider(
        id="c2",
        aabb=AABB(min_x=30, min_y=30, max_x=70, max_y=70),
        data={"type": "enemy"},
    )
    c3 = Collider(
        id="c3",
        aabb=AABB(min_x=200, min_y=200, max_x=250, max_y=250),
        data={"type": "wall"},
    )
    c4 = Collider(
        id="c4",
        aabb=AABB(min_x=50, min_y=50, max_x=90, max_y=90),
        data={"type": "enemy"},
    )
    c5 = Collider(
        id="c5",
        aabb=AABB(min_x=150, min_y=150, max_x=180, max_y=180),
        data={"type": "item"},
    )

    engine.add_collider(c1)
    engine.add_collider(c2)
    engine.add_collider(c3)
    engine.add_collider(c4)
    engine.add_collider(c5)

    return engine, c1, c2, c3, c4, c5
