import pygame as pg
import traceback
from random import uniform, choice, randint

vec = pg.math.Vector2
vec3 = pg.math.Vector3
Color = pg.Color

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def lerp_colors(color, start, end, dist):
    color.r, color.g, color.b = list(
        map(lambda x: int((x[0] * (1 - dist)) + (x[1] * dist)),
            zip(start[:3], end[:3])))


class Particle(pg.sprite.Sprite):
    def __init__(self,
                 game,
                 pos,
                 images=None,
                 colors=[],
                 vel=vec(),
                 random_angle=0,
                 vanish_speed=4,
                 start_size=1,
                 end_size=1,
                 lifespan=4):
        super().__init__()
        self.game = game
        self.game.all_sprites.add(self)

        if images:
            # if initialized with a list of images, choose one at random
            self.original_image = choice(images).copy()
            if start_size != 1:
                s = self.original_image.get_size()
                self.original_image = pg.transform.scale(
                    self.original_image,
                    (s[0] * start_size, s[1] * start_size))
            self.image = self.original_image.copy()
            self.rect = self.image.get_rect()
            self.size = list(self.rect.size)
            self.end_size = end_size
            self.size_factor = 1 + (end_size - start_size) / lifespan
        else:
            # if not initialized with images, draw a circle
            self.image = pg.Surface((20, 20))
            self.image.set_colorkey((0, 0, 0))
            self.rect = self.image.get_rect()
            pg.draw.ellipse(self.image, (255, 255, 255), self.rect)
        self.colors = colors
        self.color = self.colors[0]
        self.alpha = 255
        if len(self.colors) > 1:
            self.prev_color = self.colors[0]
            self.target_color = self.colors[1]
            self.target_index = 1
        self.lerp_dist = 0
        self.lerp_speed = 0.07
        self.vanish_speed = vanish_speed

        self.pos = vec(pos)
        self.rect.center = self.pos
        # set random velocity vector
        #self.vel = vec(uniform(-0.6, 0.6), uniform(-3, -2))
        self.vel = vel.rotate(randint(-random_angle, random_angle))

        self.forces = [self.vel]  # additional forces to impact the vel

    def add_force(self, force, random_angle=0):
        self.forces.append(force.rotate(randint(-random_angle, random_angle)))

    def update(self, dt):
        # add velocity to position
        #self.pos += self.vel
        for f in self.forces:
            self.pos += f
        # update rect
        self.rect = self.image.get_rect()
        self.rect.center = self.pos
        # reduce alpha gradually
        self.alpha -= self.vanish_speed
        if self.alpha < 0:
            self.kill()
        else:
            self.color.a = int(self.alpha)

        self.size[0] = int(self.size[0] * self.size_factor)
        self.size[1] = int(self.size[1] * self.size_factor)

    def draw(self, screen):
        self.blend_colors()
        self.image = self.original_image.copy()
        self.image = pg.transform.scale(self.image, self.size)
        self.image.fill(self.color, None, pg.BLEND_RGBA_MULT)

        screen.blit(self.image, self.rect)

    def blend_colors(self):
        if len(self.colors) > 1:
            if self.lerp_dist < 1:
                # linear interpolation between previous and target color
                lerp_colors(self.color, self.prev_color, self.target_color,
                            self.lerp_dist)
                self.lerp_dist += self.lerp_speed
            else:
                # if lerp distance reached 1, set the next target color
                self.target_index += 1
                if self.target_index < len(self.colors):
                    self.prev_color = self.target_color
                    self.target_color = self.colors[self.target_index]
                    self.lerp_dist = 0
