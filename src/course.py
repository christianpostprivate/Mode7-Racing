import pygame as pg
import numpy as np
from os import path

try:
    from pytmx import TiledTileLayer
    from pytmx.util_pygame import load_pygame
except ModuleNotFoundError:
    print("Warning: Pytmx is not installed")

vec = pg.math.Vector2


class Course:
    """
    Interface between a Tiled .tmx course and the game.
    Expected layers:
        ground   - tile layer, visual only
        road     - tile layer, full speed where a tile is set
        killzone - tile layer (optional), resets player to last road pos
        objects  - object layer (optional), object named "start" with
                   optional custom property "angle" (radians)
    """

    def __init__(self, folder, name, road_layer="road",
                 killzone_layer="killzone", offroad_speed=0.3):
        self.name = name
        self.offroad_speed = offroad_speed
        self.tiled_map = load_pygame(path.join(folder, f"{name}.tmx"))
        self.pixel_width = self.tiled_map.width * self.tiled_map.tilewidth
        self.pixel_height = self.tiled_map.height * self.tiled_map.tileheight

        self.image = self._render_tiles()
        self.speed_grid = self._build_grid(road_layer, 1.0, offroad_speed,
                                           np.float32)
        self.killzone_grid = self._build_grid(killzone_layer, True, False,
                                              bool)
        self.start_positions = self._load_start_positions()
        self.path_points = self._load_path()

        self.game_object_data = {layer.name: list(layer) for layer in self.tiled_map.objectgroups}

    # --- loading ---

    def _render_tiles(self):
        image = pg.Surface((self.pixel_width, self.pixel_height))
        for layer in self.tiled_map.visible_layers:
            if isinstance(layer, TiledTileLayer) and not layer.name == "killzone":
                for x, y, tile_image in layer.tiles():
                    if tile_image:
                        image.blit(tile_image, (x * self.tiled_map.tilewidth,
                                                y * self.tiled_map.tileheight))
        return image


    def _build_grid(self, layer_name, tile_value, empty_value, dtype):
        grid = np.full((self.tiled_map.width, self.tiled_map.height),
                       empty_value, dtype=dtype)
        try:
            layer = self.tiled_map.get_layer_by_name(layer_name)
        except ValueError:
            print(f"Warning: course '{self.name}' has no layer '{layer_name}'")
            return grid
        for x, y, gid in layer.iter_data():
            if gid:
                grid[x, y] = tile_value
        return grid


    def _load_start_positions(self):
        # position number -> rect center in normalized map coords (0..1)
        start_positions = {}
        try:
            layer = self.tiled_map.get_layer_by_name("start_positions")
        except ValueError:
            print(f"Warning: course '{self.name}' has no layer 'start_positions'")
            return start_positions
        for obj in layer:
            number = obj.properties.get("position")
            if number is None:
                continue
            start_positions[number] = vec(obj.x + obj.width / 2, obj.y + obj.height / 2)
        return start_positions


    def _load_path(self, layer_name="path"):
        # returns the polygon points of the first object in the path layer
        try:
            layer = self.tiled_map.get_layer_by_name(layer_name)
        except ValueError:
            print(f"Warning: course '{self.name}' has no layer '{layer_name}'")
            return []
        for obj in layer:
            if hasattr(obj, "points"):
                return [vec(point) for point in obj.points]
        return []
    

    def get_start_position(self, number):
        return self.start_positions.get(number)

    # --- tilemap queries ---

    def _tile_at(self, grid, pos, outside_value):
        grid_width, grid_height = grid.shape
        tile_x = int(pos.x // self.tiled_map.tilewidth)
        tile_y = int(pos.y // self.tiled_map.tileheight)
        if not (0 <= tile_x < grid_width and 0 <= tile_y < grid_height):
            return outside_value
        return grid[tile_x, tile_y]

    def ground_speed_at(self, pos):
        return self._tile_at(self.speed_grid, pos, self.offroad_speed)

    def is_on_road(self, pos):
        return self.ground_speed_at(pos) == 1.0

    def in_killzone(self, pos):
        return self._tile_at(self.killzone_grid, pos, True)