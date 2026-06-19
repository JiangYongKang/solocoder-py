from __future__ import annotations

"""
独立几何验算脚本 - 不依赖引擎实现，纯手算射线交点
用于验证测试预期的几何真值
"""


def verify_concave_polygon():
    """
    凹多边形顶点: V0(0,0), V1(10,0), V2(10,10), V3(7,5), V4(3,5), V5(0,10)
    边: V0V1, V1V2, V2V3, V3V4, V4V5, V5V0
    """
    print("=" * 60)
    print("凹多边形几何验算")
    print("=" * 60)

    edges = [
        ((0, 0), (10, 0)),
        ((10, 0), (10, 10)),
        ((10, 10), (7, 5)),
        ((7, 5), (3, 5)),
        ((3, 5), (0, 10)),
        ((0, 10), (0, 0)),
    ]

    test_cases = [
        ((5, 8), "凹口区域", "OUTSIDE"),
        ((5, 3), "凹口下方", "INSIDE"),
        ((1, 8), "左上区域", "INSIDE"),
        ((9, 8), "右上区域", "INSIDE"),
    ]

    for (px, py), desc, expected in test_cases:
        count = 0
        print(f"\n点 ({px}, {py}) - {desc}, 预期: {expected}")
        print(f"射线 y={py} 向右:")

        for i, ((x1, y1), (x2, y2)) in enumerate(edges):
            v1_above = y1 > py
            v2_above = y2 > py
            v1_on = abs(y1 - py) < 1e-10
            v2_on = abs(y2 - py) < 1e-10

            if v1_on and v2_on:
                print(f"  边{i}: ({x1},{y1})→({x2},{y2}) - 水平共线，跳过")
                continue

            if v1_above == v2_above and not v1_on and not v2_on:
                print(f"  边{i}: ({x1},{y1})→({x2},{y2}) - 同侧，跳过")
                continue

            if v1_on:
                prev_y = edges[(i - 1) % 6][0][1]
                prev_above = prev_y > py
                if prev_above != v2_above:
                    t = (py - y1) / (y2 - y1) if abs(y2 - y1) > 1e-10 else 0
                    x_intersect = x1 + t * (x2 - x1)
                    if x_intersect > px:
                        count += 1
                        print(f"  边{i}: 过顶点，异侧，x={x_intersect:.2f} > {px}，计数+1 (count={count})")
                    else:
                        print(f"  边{i}: 过顶点，异侧，x={x_intersect:.2f} <= {px}，不计入")
                else:
                    print(f"  边{i}: 过顶点，同侧，不计入")
                continue

            if v2_on:
                print(f"  边{i}: 下端点在射线上，跳过")
                continue

            t = (py - y1) / (y2 - y1)
            x_intersect = x1 + t * (x2 - x1)
            if x_intersect > px:
                count += 1
                print(f"  边{i}: 相交 x={x_intersect:.2f} > {px}，计数+1 (count={count})")
            else:
                print(f"  边{i}: 相交 x={x_intersect:.2f} <= {px}，不计入")

        result = "INSIDE" if count % 2 == 1 else "OUTSIDE"
        status = "OK" if result == expected else "FAIL"
        print(f"  总计: count={count}, {result} {status} (预期 {expected})")


def verify_butterfly_polygon():
    """
    蝴蝶形顶点: V0(0,0), V1(10,10), V2(0,10), V3(10,0)
    边: V0V1, V1V2, V2V3, V3V0
    """
    print("\n" + "=" * 60)
    print("蝴蝶形多边形几何验算")
    print("=" * 60)

    edges = [
        ((0, 0), (10, 10)),
        ((10, 10), (0, 10)),
        ((0, 10), (10, 0)),
        ((10, 0), (0, 0)),
    ]

    test_cases = [
        ((5, 8), "上翼", "INSIDE"),
        ((5, 2), "下翼", "INSIDE"),
        ((2, 5), "左中", "OUTSIDE"),
        ((8, 5), "右中", "OUTSIDE"),
    ]

    for (px, py), desc, expected in test_cases:
        count = 0
        print(f"\n点 ({px}, {py}) - {desc}, 预期: {expected}")
        print(f"射线 y={py} 向右:")

        for i, ((x1, y1), (x2, y2)) in enumerate(edges):
            v1_above = y1 > py
            v2_above = y2 > py
            v1_on = abs(y1 - py) < 1e-10
            v2_on = abs(y2 - py) < 1e-10

            if v1_on and v2_on:
                print(f"  边{i}: ({x1},{y1})→({x2},{y2}) - 水平共线，跳过")
                continue

            if v1_above == v2_above and not v1_on and not v2_on:
                print(f"  边{i}: ({x1},{y1})→({x2},{y2}) - 同侧，跳过")
                continue

            if v1_on:
                prev_y = edges[(i - 1) % 4][0][1]
                prev_above = prev_y > py
                if prev_above != v2_above:
                    t = (py - y1) / (y2 - y1) if abs(y2 - y1) > 1e-10 else 0
                    x_intersect = x1 + t * (x2 - x1)
                    if x_intersect > px:
                        count += 1
                        print(f"  边{i}: 过顶点，异侧，x={x_intersect:.2f} > {px}，计数+1 (count={count})")
                    else:
                        print(f"  边{i}: 过顶点，异侧，x={x_intersect:.2f} <= {px}，不计入")
                else:
                    print(f"  边{i}: 过顶点，同侧，不计入")
                continue

            if v2_on:
                print(f"  边{i}: 下端点在射线上，跳过")
                continue

            t = (py - y1) / (y2 - y1)
            x_intersect = x1 + t * (x2 - x1)
            if x_intersect > px:
                count += 1
                print(f"  边{i}: 相交 x={x_intersect:.2f} > {px}，计数+1 (count={count})")
            else:
                print(f"  边{i}: 相交 x={x_intersect:.2f} <= {px}，不计入")

        result = "INSIDE" if count % 2 == 1 else "OUTSIDE"
        status = "OK" if result == expected else "FAIL"
        print(f"  总计: count={count}, {result} {status} (预期 {expected})")


def verify_holed_polygon():
    """
    带孔多边形: 外环(0,0)-(10,0)-(10,10)-(0,10)，内环(3,3)-(7,3)-(7,7)-(3,7)
    """
    print("\n" + "=" * 60)
    print("带孔多边形几何验算")
    print("=" * 60)

    outer_edges = [
        ((0, 0), (10, 0)),
        ((10, 0), (10, 10)),
        ((10, 10), (0, 10)),
        ((0, 10), (0, 0)),
    ]

    inner_edges = [
        ((3, 3), (7, 3)),
        ((7, 3), (7, 7)),
        ((7, 7), (3, 7)),
        ((3, 7), (3, 3)),
    ]

    def ray_cast(edges, px, py):
        count = 0
        n = len(edges)
        for i, ((x1, y1), (x2, y2)) in enumerate(edges):
            v1_above = y1 > py
            v2_above = y2 > py
            v1_on = abs(y1 - py) < 1e-10
            v2_on = abs(y2 - py) < 1e-10

            if v1_on and v2_on:
                continue
            if v1_above == v2_above and not v1_on and not v2_on:
                continue
            if v1_on:
                prev_y = edges[(i - 1) % n][0][1]
                prev_above = prev_y > py
                if prev_above != v2_above:
                    t = (py - y1) / (y2 - y1) if abs(y2 - y1) > 1e-10 else 0
                    x_intersect = x1 + t * (x2 - x1)
                    if x_intersect > px:
                        count += 1
                continue
            if v2_on:
                continue

            t = (py - y1) / (y2 - y1)
            x_intersect = x1 + t * (x2 - x1)
            if x_intersect > px:
                count += 1
        return count % 2 == 1

    test_cases = [
        ((5, 9), "外环内、内环外", "INSIDE"),
        ((5, 5), "内环内", "OUTSIDE"),
        ((15, 5), "外环外", "OUTSIDE"),
        ((1, 5), "外环内、内环左", "INSIDE"),
    ]

    for (px, py), desc, expected in test_cases:
        outer_inside = ray_cast(outer_edges, px, py)
        inner_inside = ray_cast(inner_edges, px, py)
        result = "INSIDE" if (outer_inside and not inner_inside) else "OUTSIDE"
        status = "OK" if result == expected else "FAIL"
        print(f"点 ({px}, {py}) - {desc}")
        print(f"  外环判定: {'INSIDE' if outer_inside else 'OUTSIDE'}")
        print(f"  内环判定: {'INSIDE' if inner_inside else 'OUTSIDE'}")
        print(f"  联合判定: {result} {status} (预期 {expected})")


if __name__ == "__main__":
    verify_concave_polygon()
    verify_butterfly_polygon()
    verify_holed_polygon()
    print("\n" + "=" * 60)
    print("验算完成！所有测试点均已独立手算验证")
    print("=" * 60)
