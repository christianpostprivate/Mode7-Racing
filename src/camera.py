import pygame as pg
from math import cos, sin

vec = pg.math.Vector2


class CameraMode:
    locked = False  # True = target sprite stays at its fixed screen position

    def enter(self, camera):
        pass

    def update(self, camera, dt):
        pass


class FollowMode(CameraMode):
    # behind the target, optionally rotated and closer/farther
    def __init__(self, angle_offset=0.0, distance_factor=1.0):
        self.angle_offset = angle_offset
        self.distance_factor = distance_factor
        self.locked = angle_offset == 0.0 and distance_factor == 1.0

    def update(self, camera, dt):
        camera.angle = camera.target.angle + self.angle_offset
        camera.look_at_target(self.distance_factor)


class OrbitMode(CameraMode):
    def __init__(self, speed=0.5, distance_factor=1.0):
        self.speed = speed  # rad/s
        self.distance_factor = distance_factor

    def enter(self, camera):
        camera.angle = camera.target.angle  # start from behind, no jump

    def update(self, camera, dt):
        camera.angle += self.speed * dt
        camera.look_at_target(self.distance_factor)


class FixedMode(CameraMode):
    # static camera, e.g. at the finish line
    def __init__(self, pos, angle):
        self.pos = vec(pos)
        self.angle = angle

    def update(self, camera, dt):
        camera.pos = self.pos.copy()
        camera.angle = self.angle


class Camera:
    # view position and direction for Mode7 and billboards
    def __init__(self, game, target=None):
        self.game = game
        self.pos = vec()
        self.angle = 0.0
        self.target = target  # object with pos and angle
        self.mode = FollowMode()


    def set_mode(self, mode, target=None):
        if target is not None:
            self.target = target
        self.mode = mode
        self.mode.enter(self)


    @property
    def forward(self):
        return vec(cos(self.angle), sin(self.angle))


    def is_locked_on(self, sprite):
        return self.mode.locked and sprite is self.target


    def look_at_target(self, distance_factor=1.0):
        # place the camera so the target is in the kart screen spot
        distance = self.game.map.kart_ground_distance() * distance_factor
        self.pos = self.target.pos - vec(distance, 0).rotate_rad(self.angle)


    def update(self, dt):
        if self.target is None and not isinstance(self.mode, FixedMode):
            return
        self.mode.update(self, dt)