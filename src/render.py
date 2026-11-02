from numba import njit
import pygame as pg
import math
from math import sin, cos, pi

vec = pg.Vector2


class Mode7:
    KART_SCREEN_BOTTOM = 116  # bottom of the locked kart sprite (84 + 32)

    def __init__(self, game, sprite=None, size=(1024, 1024)):
        self.game = game
        if sprite:
            self.image = sprite
            self.size = sprite.get_size()
        else:
            self.image = pg.Surface(size)
            self.image.fill(pg.Color("black"))
            
            tilesize = 32
            for x in range(0, size[0], tilesize):
                pg.draw.line(self.image, pg.Color("darkturquoise"),
                             (x, 0), (x, size[1]), 4)
            for y in range(0, size[1], tilesize):
                pg.draw.line(self.image, pg.Color("blueviolet"),
                             (0, y), (size[0], y), 4)
        self.rect = self.image.get_rect()
        
        # Convert source image to numpy array once
        self.image_array = pg.surfarray.array3d(self.image)

        # tile drawn outside the map (top left map tile by default)
        course = self.game.course
        fill_w = course.tiled_map.tilewidth if course else 32
        fill_h = course.tiled_map.tileheight if course else 32
        fill_tile = self.image.subsurface((0, 0, fill_w, fill_h))
        self.fill_array = pg.surfarray.array3d(fill_tile)
        
        self.near = 16.0
        self.far = 40.0
        self.fov_half = pi / 4


    def kart_ground_distance(self):
        # world distance from camera to the ground point under the kart sprite
        screen_h = self.game.game_screen_rect.h
        horizon_offset = int(screen_h * self.game.config["Visuals.horizon"])
        row = self.KART_SCREEN_BOTTOM - horizon_offset
        depth = row / screen_h
        return (self.near + (self.far - self.near) / depth) * cos(self.fov_half)

        
    def draw(self, screen):
        screen_rect = screen.get_rect()
        player = self.game.player

        player = self.game.player  # used for the debug tile highlight
        camera = self.game.camera

        far_x1 = camera.pos.x + cos(camera.angle - self.fov_half) * self.far
        far_y1 = camera.pos.y + sin(camera.angle - self.fov_half) * self.far
        near_x1 = camera.pos.x + cos(camera.angle - self.fov_half) * self.near
        near_y1 = camera.pos.y + sin(camera.angle - self.fov_half) * self.near

        far_x2 = camera.pos.x + cos(camera.angle + self.fov_half) * self.far
        far_y2 = camera.pos.y + sin(camera.angle + self.fov_half) * self.far
        near_x2 = camera.pos.x + cos(camera.angle + self.fov_half) * self.near
        near_y2 = camera.pos.y + sin(camera.angle + self.fov_half) * self.near
        
        # Render using compiled function
        screen_array = pg.surfarray.pixels3d(screen)

        # tile size and player tile for debug highlight
        course = self.game.course
        tile_w = course.tiled_map.tilewidth if course else 32
        tile_h = course.tiled_map.tileheight if course else 32
        player_tile_x = int(player.pos.x) // tile_w
        player_tile_y = int(player.pos.y) // tile_h
        
        render_mode7(
            screen_array,
            self.image_array,
            self.fill_array,
            screen_rect.w, screen_rect.h,
            self.rect.w, self.rect.h,
            far_x1, far_y1, near_x1, near_y1,
            far_x2, far_y2, near_x2, near_y2,
            self.game.config["Visuals.horizon"],
            tile_w, tile_h,
            player_tile_x, player_tile_y, 
            self.game.show_debug
        )
        
        del screen_array  # Release the lock on the surface


    def update(self, dt):
        if not self.game.show_debug:
            return
        
        # Debug controls
        keys = pg.key.get_pressed()
        if keys[pg.K_LEFT]:
            self.near -= 160 * dt
        elif keys[pg.K_RIGHT]:
            self.near += 160 * dt
            self.near = min(self.near, 32)
        if keys[pg.K_UP]:
            self.far += 160 * dt
        elif keys[pg.K_DOWN]:
            self.far -= 160 * dt
            self.far = max(self.far, 32)
        if keys[pg.K_q]:
            self.fov_half -= 0.2 * dt
        elif keys[pg.K_e]:
            self.fov_half += 0.2 * dt

        self.game.debug_values['near'] = f'{self.near:.3f}'
        self.game.debug_values['far'] = f'{self.far:.5f}'


@njit(cache=True, fastmath=True)
def render_mode7(screen_array, image_array, fill_array,
                 screen_w, screen_h,
                 image_w, image_h,
                 far_x1, far_y1, near_x1, near_y1,
                 far_x2, far_y2, near_x2, near_y2,
                 horizon,
                 tile_w, tile_h,
                 player_tile_x, player_tile_y,
                 highlight):
    horizon_offset = int(screen_h * horizon)
    fill_w = fill_array.shape[0]
    fill_h = fill_array.shape[1]

    for y in range(screen_h):
        y_screen = y + horizon_offset
        if y_screen >= screen_h:
            continue

        sample_depth = y / screen_h + 0.0000001  # avoid division by zero

        # perspective
        start_x = (far_x1 - near_x1) / sample_depth + near_x1
        start_y = (far_y1 - near_y1) / sample_depth + near_y1
        end_x = (far_x2 - near_x2) / sample_depth + near_x2
        end_y = (far_y2 - near_y2) / sample_depth + near_y2

        dx = (end_x - start_x) / screen_w
        dy = (end_y - start_y) / screen_w

        sample_x = start_x
        sample_y = start_y

        for x in range(screen_w):
            tex_x = int(math.floor(sample_x))
            tex_y = int(math.floor(sample_y))

            if tex_x < 0 or tex_x >= image_w or tex_y < 0 or tex_y >= image_h:
                # outside the map -> repeat fill tile
                fx = tex_x % fill_w
                fy = tex_y % fill_h
                screen_array[x, y_screen, 0] = fill_array[fx, fy, 0]
                screen_array[x, y_screen, 1] = fill_array[fx, fy, 1]
                screen_array[x, y_screen, 2] = fill_array[fx, fy, 2]
            elif highlight and tex_x // tile_w == player_tile_x and tex_y // tile_h == player_tile_y:
                screen_array[x, y_screen, 0] = (int(image_array[tex_x, tex_y, 0]) + 255) // 2
                screen_array[x, y_screen, 1] = int(image_array[tex_x, tex_y, 1]) // 2
                screen_array[x, y_screen, 2] = int(image_array[tex_x, tex_y, 2]) // 2
            else:
                screen_array[x, y_screen, 0] = image_array[tex_x, tex_y, 0]
                screen_array[x, y_screen, 1] = image_array[tex_x, tex_y, 1]
                screen_array[x, y_screen, 2] = image_array[tex_x, tex_y, 2]

            sample_x += dx
            sample_y += dy
            