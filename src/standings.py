import pygame as pg

vec = pg.math.Vector2


class RaceStandings:
    # ranks karts: finished karts by finish order, the rest by progress along the path

    def __init__(self, path_points, finish_pos, max_laps):
        self.path_points = [vec(point) for point in path_points]
        # arc length at the start of each segment
        self.cumulative_lengths = [0.0]
        point_count = len(self.path_points)
        for i in range(point_count):
            segment_start = self.path_points[i]
            segment_end = self.path_points[(i + 1) % point_count]
            self.cumulative_lengths.append(self.cumulative_lengths[-1]
                                           + segment_start.distance_to(segment_end))
        self.path_length = self.cumulative_lengths[-1]
        self.finish_distance = self.distance_along_path(finish_pos)
        self.max_laps = max_laps

        self.karts = []
        self.auto_finish = {}    # False for the player (finishes via checkpoints)
        self.last_distance = {}
        self.laps = {}
        self.progress = {}       # laps * path_length + distance past the finish line
        self.finish_order = []


    def distance_along_path(self, pos):
        closest_distance = float("inf")
        best_distance = 0.0
        point_count = len(self.path_points)
        for i in range(point_count):
            segment_start = self.path_points[i]
            segment = self.path_points[(i + 1) % point_count] - segment_start
            if segment.length_squared() == 0:
                continue
            projection = (pos - segment_start).dot(segment) / segment.length_squared()
            projection = max(0.0, min(1.0, projection))
            normal_point = segment_start + segment * projection
            distance = pos.distance_to(normal_point)
            if distance < closest_distance:
                closest_distance = distance
                best_distance = self.cumulative_lengths[i] + segment.length() * projection
        return best_distance


    def distance_past_finish(self, pos):
        return (self.distance_along_path(pos) - self.finish_distance) % self.path_length


    def add_kart(self, kart, auto_finish=True):
        distance = self.distance_past_finish(kart.map_pos)
        self.karts.append(kart)
        self.auto_finish[kart] = auto_finish
        self.last_distance[kart] = distance
        # grid is behind the finish line -> start on lap -1
        self.laps[kart] = -1 if distance > self.path_length / 2 else 0
        self.progress[kart] = self.laps[kart] * self.path_length + distance


    def update(self):
        half_length = self.path_length / 2
        for kart in self.karts:
            distance = self.distance_past_finish(kart.map_pos)
            delta = distance - self.last_distance[kart]
            if delta < -half_length:
                self.laps[kart] += 1   # crossed the line forwards
            elif delta > half_length:
                self.laps[kart] -= 1   # crossed it backwards
            self.last_distance[kart] = distance
            self.progress[kart] = self.laps[kart] * self.path_length + distance

            if (self.auto_finish[kart]
                    and self.progress[kart] >= self.max_laps * self.path_length):
                self.mark_finished(kart)


    def mark_finished(self, kart):
        if kart not in self.finish_order:
            self.finish_order.append(kart)


    def replace_kart(self, old_kart, new_kart):
        # new kart takes over position, laps and finish place
        # used when the player crosses the finish line and turns into an AI kart
        self.karts[self.karts.index(old_kart)] = new_kart
        if old_kart in self.finish_order:
            self.finish_order[self.finish_order.index(old_kart)] = new_kart
        for table in (self.auto_finish, self.last_distance, self.laps, self.progress):
            table[new_kart] = table.pop(old_kart)


    def ranking(self):
        def sort_key(kart):
            if kart in self.finish_order:
                return (0, self.finish_order.index(kart))
            return (1, -self.progress[kart])
        return sorted(self.karts, key=sort_key)


    def position_of(self, kart):
        return self.ranking().index(kart) + 1