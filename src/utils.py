def point_in_polygon(point, polygon):
    # polygon: list of vec2 / (x, y) tuples
    inside = False
    count = len(polygon)
    for i in range(count):
        start = polygon[i]
        end = polygon[(i + 1) % count]
        # does a horizontal ray from point cross edge start->end?
        if (start[1] > point[1]) != (end[1] > point[1]):
            cross_x = start[0] + (point[1] - start[1]) * (end[0] - start[0]) / (end[1] - start[1])
            if point[0] < cross_x:
                inside = not inside
    return inside