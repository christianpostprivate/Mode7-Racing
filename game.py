import numpy as np
import pygame as pg

try:
    from pytmx.util_pygame import load_pygame
except ModuleNotFoundError:
    print('Warning: Pytmx is not installed')

import traceback
from math import sin, cos, pi
from os import path

from particle import Particle


vec = pg.math.Vector2


def load_map(folder, name):
    """
    load a Tiled map in .tmx format and return a background image Surface, 
    map objects as a TiledObjectGroup and layer_data as a list of 2D arrays
    with tile indices
    """
    tiled_map = load_pygame(path.join(folder, f'{name}.tmx'))
    # create empty surface based on tile map dimensions
    bg_image = pg.Surface((tiled_map.width * tiled_map.tilewidth,
                          tiled_map.height * tiled_map.tileheight))
    # iterate through each tile layer and blit the corresponding tile
    layer_data = []
    for layer in tiled_map.layers:
        if hasattr(layer, 'data'):
            layer_data.append(layer.data)
            for x, y, image in layer.tiles():
                if image:
                    bg_image.blit(image, (x * tiled_map.tilewidth,
                                          y * tiled_map.tileheight))
    return bg_image, layer_data


class Game:
    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        self.display_screen = pg.display.set_mode((800, 600))
        self.display_rect = self.display_screen.get_rect()
        self.game_screen = pg.Surface((200, 150))
        self.game_screen_rect = self.game_screen.get_rect()
        self.background = pg.Surface(self.game_screen.get_size())
        self.background.fill(pg.Color('skyblue'))
        self.fps = 120
        self.all_sprites = pg.sprite.Group()
        self.running = True

        # specify the directories for asset loading
        base_dir = path.dirname(__file__)
        assets_folder = path.join(base_dir, 'assets')

        player_image_strip = pg.image.load(
                path.join(assets_folder, 'kart.png')).convert_alpha()
        self.player_images = [player_image_strip.subsurface((i * 30, 0, 30, 32))
                              for i in range(11)]

        self.cloud_image = pg.image.load(
                path.join(assets_folder, 'cloud.png')).convert_alpha()
        self.traffic_light_images = pg.image.load(
                path.join(assets_folder, 'lights.png')).convert_alpha()
        self.bush_image = pg.image.load(
                path.join(assets_folder, 'bush.png')).convert_alpha()  # TODO: unused

        self.player = Player(self)
        self.traffic_light = TrafficLight(self, (100, 60))

        try:
            self.map_img, _ = load_map(folder=assets_folder, name='track2')
            self.map = Mode7(self, self.map_img)
        except Exception:
            traceback.print_exc()
            self.map = Mode7(self)

        self.started = False


    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False


    def update(self, dt):
        self.game_screen.blit(self.background, (0, 0))
        self.map.update(dt)
        self.all_sprites.update(dt)

        if self.traffic_light.done:
            self.started = True


    def draw(self):
        for s in self.all_sprites:
            s.draw(self.game_screen)

# =============================================================================
#         #for debugging
#         start1 = vec(self.player.rect.center)
#         end1 = start1 + self.player.vel * 300
#         pg.draw.line(self.fake_screen, pg.Color('white'), start1, end1)
#
#         start2 = vec(self.player.rect.center)
#         v = vec()
#         v.from_polar((20, self.player.angle * 180 / pi))
#         end2 = start2 + v
#         pg.draw.line(self.fake_screen, pg.Color('red'), start2, end2)
#
#         print(end1.angle_to(end2))
#         for s in self.all_sprites:
#             pg.draw.rect(self.fake_screen, pg.Color('red'), s.rect, 1)
# =============================================================================

        transformed_screen = pg.transform.scale(self.game_screen,
                                                self.display_rect.size, self.display_screen)
        #self.display_screen.blit(transformed_screen, (0, 0))
        pg.display.update()


    def run(self):
        self.running = True
        while self.running:
            delta_time = self.clock.tick(self.fps) / 1000
            pg.display.set_caption(f'FPS: {round(self.clock.get_fps(), 2)}')
            self.events()
            self.update(delta_time)
            self.draw()

        pg.quit()



class Mode7:
    def __init__(self, game, sprite=None, size=(1024, 1024)):
        self.game = game
        if sprite:
            self.image = sprite
            self.size = sprite.get_size()
        else:
            # if no sprite is provided, draw an image with horizontal and vertical lines
            self.image = pg.Surface(size)
            self.image.fill(pg.Color('black'))
            
            tilesize = 32
            for x in range(0, size[0], tilesize):
                pg.draw.line(self.image, pg.Color('darkturquoise'),
                             (x, 0), (x, size[1]), 4)
            for y in range(0, size[1], tilesize):
                pg.draw.line(self.image, pg.Color('blueviolet'),
                             (0, y), (size[0], y), 4)
        self.rect = self.image.get_rect()
        
        # settings for the near and far plane
        self.near = 0.005
        self.far = 0.01215
        # field of view
        self.fov_half = pi / 4
        self.draw = self._draw

    def set_np_drawing(self, enabled=True):
        self.draw = self._np_draw if enabled else self._draw
        
    
    def update(self, dt):
        # references to the "fake" screen (the one that gets rendered onto the screen)
        player = self.game.player
        
        # create the frustum corner points
        self.far_x1 = player.pos.x + cos(player.angle - self.fov_half) * self.far
        self.far_y1 = player.pos.y + sin(player.angle - self.fov_half) * self.far
        
        self.near_x1 = player.pos.x + cos(player.angle - self.fov_half) * self.near
        self.near_y1 = player.pos.y + sin(player.angle - self.fov_half) * self.near
        
        self.far_x2 = player.pos.x + cos(player.angle + self.fov_half) * self.far
        self.far_y2 = player.pos.y + sin(player.angle + self.fov_half) * self.far
        
        self.near_x2 = player.pos.x + cos(player.angle + self.fov_half) * self.near
        self.near_y2 = player.pos.y + sin(player.angle + self.fov_half) * self.near

        near_rect = (self.near_x1, self.near_y1, self.near_x2, self.near_y2)
        far_rect = (self.far_x1, self.far_y1, self.far_x2, self.far_y2)
        self.draw(self.image, self.game.game_screen, near_rect, far_rect)

        keys = pg.key.get_pressed()
        # control the rendering parameters
        # this is for debugging only!
        if keys[pg.K_LEFT]:
            self.near -= 0.05 * dt
        elif keys[pg.K_RIGHT]:
            self.near += 0.05 * dt
            self.near = min(self.near, 0.01)
        if keys[pg.K_UP]:
            self.far += 0.05 * dt
        elif keys[pg.K_DOWN]:
            self.far -= 0.05 * dt
            self.far = max(self.far, 0.01)
        if keys[pg.K_q]:
            self.fov_half -= 0.2 * dt
        elif keys[pg.K_e]:
            self.fov_half += 0.2 * dt

    @staticmethod
    def _draw(source, screen, near_rect, far_rect):
        HORIZON = 0.2
        width, height = source.get_rect().size
        screen_width, screen_height = screen.get_rect().size
        near_x1, near_y1, near_x2, near_y2 = near_rect
        far_x1, far_y1, far_x2, far_y2 = far_rect

        # loop over every pixel on the image, beginning furthest away towards the
        # camera point
        get_ = source.get_at
        set_ = screen.set_at
        for y in range(screen_height):
            _y = int(y + screen_height*HORIZON)
            if _y >= screen_height:
                break
            # take a sample point for depth linearly related to rows on the screen
            sample_depth = y/screen_height + 0.0000001  # this prevents div by 0 errors
            # not sure how this is handled in the c++ code

            # Use sample point in non-linear (1/x) way to enable perspective
            # and grab start and end points for lines across the screen
            start_x = (far_x1 - near_x1)/sample_depth + near_x1
            start_y = (far_y1 - near_y1)/sample_depth + near_y1
            end_x = (far_x2 - near_x2)/sample_depth + near_x2
            end_y = (far_y2 - near_y2)/sample_depth + near_y2
            fx = (end_x - start_x)/screen_width
            fy = (end_y - start_y)/screen_width

            # Linearly interpolate lines across the screen
            for x in range(screen_width):
                sample_x = x*fx + start_x
                sample_y = x*fy + start_y

                # Wrap sample coordinates to give "infinite" periodicity on maps
                sample_x = sample_x%1
                sample_y = sample_y%1

                # sample a color from the image
                # translate x and y to screen proportions first because they are fractions of 1
                col = get_((int(sample_x*width),
                            int(sample_y*height)))
                # set the pixel values of the fake screen image
                # get_at and set_at are super slow, gonna try pixel arrays instead
                set_((x, _y), col)

    @staticmethod
    def _np_draw(source, screen, near_rect, far_rect):
        HORIZON = 0.2
        width, height = source.get_rect().size
        screen_width, screen_height = screen.get_rect().size
        near_x1, near_y1, near_x2, near_y2 = near_rect
        far_x1, far_y1, far_x2, far_y2 = far_rect

        np_source = pg.surfarray.pixels3d(source)
        np_screen = pg.surfarray.pixels3d(screen)
        for y in range(screen_height):
            _y = int(y + screen_height*HORIZON)
            if _y >= screen_height:
                break
            # take a sample point for depth linearly related to rows on the screen
            sample_depth = y/screen_height + 0.0000001  # this prevents div by 0 errors
            # not sure how this is handled in the c++ code

            # Use sample point in non-linear (1/x) way to enable perspective
            # and grab start and end points for lines across the screen
            start_x = (far_x1 - near_x1)/sample_depth + near_x1
            start_y = (far_y1 - near_y1)/sample_depth + near_y1
            end_x = (far_x2 - near_x2)/sample_depth + near_x2
            end_y = (far_y2 - near_y2)/sample_depth + near_y2
            fx = (end_x - start_x)/screen_width
            fy = (end_y - start_y)/screen_width

            xs = np.arange(screen_width)
            sample_x = (xs*fx + start_x)%1
            sample_x = (sample_x*width).astype(int)
            sample_y = (xs*fy + start_y)%1
            sample_y = (sample_y*width).astype(int)
            np_screen[xs, _y] = np_source[sample_x, sample_y]


# ENUMS correspond to kart image index
LEFT = [5, 4, 3, 2, 1, 0]
RIGHT = [5, 6, 7, 8, 9, 10]


class Player(pg.sprite.Sprite):
    def __init__(self, game):
        super().__init__(game.all_sprites)
        self.game = game
        self.pos = vec(999.904, 1000.38)
        self.angle = -1.54
        self.acc = vec()
        self.vel = vec()
        self.speed = 0.2

        self.image = game.player_images[LEFT[0]]
        self.rect = self.image.get_rect()
        self.rect.topleft = (84, 84)

        self.time_passed = 0 # seconds from the start of the game
        self.steer_time = 0 # seconds the player is pressing a direction
        self.lastdir = 'LEFT'
        self.moving = 1 # 1 forward, -1 backwards
        self.dust_timer = 0


    def update(self, dt):
        self.time_passed += dt

        keys = pg.key.get_pressed()

        if not self.game.started:
            if keys[pg.K_w]:
                self.dust_timer += dt
                if self.dust_timer >= 0.3:
                    # create two particles (left and right)
                    Particle(self.game, self.rect.bottomright,
                             images=[self.game.cloud_image],
                             colors=[pg.Color('white')],
                             vel=vec(1, 0),
                             random_angle=20,
                             vanish_speed=20,
                             end_size=1.4)
                    Particle(self.game, self.rect.bottomleft,
                             images=[self.game.cloud_image],
                             colors=[pg.Color('white')],
                             vel=vec(-1, 0),
                             random_angle=20,
                             vanish_speed=20,
                             end_size=1.4)
                    self.dust_timer = 0

        else:
            if self.moving == 1:
                turn_force = 20 # how much the angle changes when turning
            else:
                turn_force = 50
            steer_anim_speed = 10 # turning animation speed

            current_speed = self.vel.length()

            # steer
            # cap the image index at 4 (len of animation minus 2)
            index = min(4, int(self.steer_time * steer_anim_speed))

            if keys[pg.K_a]:
                # turning left
                if self.lastdir == 'RIGHT':
                    self.steer_time = 0
                # increase the steering time
                self.steer_time += dt
                self.angle -= turn_force * dt * current_speed * self.moving
                # add 1 to the index to get the first turning sprite and set the image
                if self.moving == 1:
                    self.image = self.game.player_images[LEFT[index + 1]]
                else:
                    self.image = self.game.player_images[RIGHT[index + 1]]
                self.lastdir = 'LEFT'
            elif keys[pg.K_d]:
                # turning right
                if self.lastdir == 'LEFT':
                    self.steer_time = 0
                self.steer_time += dt
                self.angle += turn_force * dt * current_speed * self.moving
                if self.moving == 1:
                    self.image = self.game.player_images[RIGHT[index + 1]]
                else:
                    self.image = self.game.player_images[LEFT[index + 1]]
                self.lastdir = 'RIGHT'
            else:
                if self.lastdir == 'LEFT' and self.moving == 1:
                    self.image = self.game.player_images[LEFT[index]]
                elif self.lastdir == 'LEFT' and self.moving == -1:
                    self.image = self.game.player_images[RIGHT[index]]
                elif self.lastdir == 'RIGHT' and self.moving == 1:
                    self.image = self.game.player_images[RIGHT[index]]
                elif self.lastdir == 'RIGHT' and self.moving == -1:
                    self.image = self.game.player_images[LEFT[index]]

                self.steer_time -= dt

            # limit the steer time between 0 and the maximum image index
            self.steer_time = max(min(self.steer_time, steer_anim_speed * dt), 0)

            # move forward or backwards
            if keys[pg.K_w]:
                self.moving = 1
                self.acc.x = self.speed
                self.acc.y = self.speed
            elif keys[pg.K_s]:
                self.moving = -1
                self.acc.x = self.speed * -0.4
                self.acc.y = self.speed * -0.4

            self.vel.x += self.acc.x * cos(self.angle) * dt
            self.vel.y += self.acc.y * sin(self.angle) * dt
            self.pos += self.vel * dt

            self.acc *= 0
            self.vel *= 0.9


            # move image up and down
            if int(self.time_passed * 5) % 2 == 0 and current_speed >= 0.01:
                self.rect.top = 85
            else:
                self.rect.top = 84


            # create dust clouds
            self.dust_timer += dt
            if self.dust_timer >= 0.2:
                if self.lastdir == 'RIGHT':
                    v = vec(3, 0) * self.moving
                elif self.lastdir == 'LEFT':
                    v = vec(-3, 0) * self.moving
                if self.steer_time >= 0.3 and current_speed > 0.04:
                    if self.moving == 1:
                        p = Particle(self.game, self.rect.midbottom,
                                     images=[self.game.cloud_image],
                                     colors=[pg.Color('white')],
                                     vel=v, random_angle=30,
                                     vanish_speed=20,
                                     end_size=1.4)
                        p.add_force(vec(0, 1), 10)
                    else:
                        p = Particle(self.game, self.rect.midbottom,
                                     images=[self.game.cloud_image],
                                     colors=[pg.Color('white')],
                                     vel=v, random_angle=30,
                                     vanish_speed=20,
                                     end_size=0.9)
                        p.add_force(vec(0, -2), 10)

                self.dust_timer = 0


    def draw(self, screen):
        screen.blit(self.image, self.rect)



class TrafficLight(pg.sprite.Sprite):
    def __init__(self, game, pos):
        super().__init__(game.all_sprites)
        self.game = game
        self.images = [game.traffic_light_images.subsurface((i * 24, 0, 24, 32)) for i in range(5)]
        self.image = self.images[0]
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.done = False
        self.timer = 0
        self.img_index = 0


    def update(self, dt):
        self.timer += dt
        if self.timer >= 1:
            self.timer = 0
            self.img_index += 1
            if self.img_index == 4:
                self.done = True
            try:
                self.image = self.images[self.img_index]
            except:
                self.kill()


    def draw(self, screen):
        screen.blit(self.image, self.rect)



class Bush(pg.sprite.Sprite):
    # TODO: work in progress
    def __init__(self, game, map_pos):
        super().__init__(game.all_sprites)
        self.game = game
        self.image = game.bush_image
        self.rect = self.image.get_rect()
        # position on the map
        self.map_pos = map_pos


    def update(self, dt):
        # calculate screen position and size based on relative position
        # on game map to the player
        dist_vec = self.map_pos - self.game.player.pos
        distance = dist_vec.length()


if __name__ == '__main__':
    try:
        g = Game()
        g.map.set_np_drawing()
        g.run()
    except Exception:
        traceback.print_exc()
        pg.quit()
