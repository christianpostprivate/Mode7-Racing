import pygame as pg
    
from math import pi
from os import path

from src.scenes import SCENES
from src.config import Config

vec = pg.math.Vector2


class Game:
    def __init__(self):
        pg.init()

        # specify the directories for asset loading
        # TODO create a Loader scene
        base_dir = path.dirname(__file__)
        self.assets_folder = path.join(base_dir, "..", "assets")

        # handle config file
        # the example file (readonly) contents get copied to the real settings file, which will be modified
        self.config = Config(path.join(base_dir, "..", "settings.toml"),
                             path.join(base_dir, "..", "settings.example.toml"))

        # debugging
        self.debug_font = pg.font.SysFont('consolas', self.config["Debug.font_size"])
        self.show_debug = False
        self.debug_values = {}

        # game variables
        self.clock = pg.time.Clock()
        self.display_screen = pg.display.set_mode(
            (self.config["Video.display_w"], self.config["Video.display_h"])
            )
        self.display_rect = self.display_screen.get_rect()
        self.game_screen = pg.Surface(
            (self.config["Video.game_screen_w"], self.config["Video.game_screen_h"])
            )
        self.game_screen_rect = self.game_screen.get_rect()

        self.assets = {
            "sprites": {},
            "spritesheets": {},
            "backgrounds": {},
            "fonts": {},
            # TODO music and sfx
        }  # gets populated by the AssetLoader scene
        # courses (tmx data) get loaded individually before each race

        # TODO make background scenery course-specific (via TMX data)

        self.all_sprites = pg.sprite.Group()  # TODO rename?
        self.billboards = pg.sprite.Group()  # sprites that are drawn relative to the Mode7 map and scaled up/down relative to the camera distance

        self.font = pg.font.Font(path.join(self.assets_folder, "fonts", "PressStart2P.ttf"), 8)  # menu text

        # race objects, set by the Race scene (sprites access them through game)
        self.player = None
        self.camera = None
        self.course = None
        self.map = None
        self.started = False  # if the race has started (starts after green light)

        # scene stack: top scene gets events/updates,
        # transparent scenes also draw the scene below them
        self.scene_stack = []
        self.push_scene("AssetLoader")

        # game loop active flag
        self.running = True

    # --- scene management ---

    def push_scene(self, name, **kwargs):
        scene = SCENES[name](self, **kwargs)
        self.scene_stack.append(scene)
        scene.startup()


    def pop_scene(self):
        self.scene_stack.pop().cleanup()
        if not self.scene_stack:
            self.running = False


    def switch_scene(self, name, **kwargs):
        # replace the whole stack with a new scene
        while self.scene_stack:
            self.scene_stack.pop().cleanup()
        self.debug_values.clear()
        self.push_scene(name, **kwargs)


    def ground_speed_at(self, pos):
        return self.course.ground_speed_at(pos) if self.course else 1.0


    def check_in_killzone(self, pos):
        return self.course.in_killzone(pos) if self.course else False


    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            if event.type == pg.KEYDOWN and event.key == pg.K_F1:
                self.show_debug = not self.show_debug

            # builtin and custom events go to the active scene
            if self.scene_stack:
                self.scene_stack[-1].get_event(event)


    def update(self, dt):
        if self.scene_stack:
            self.scene_stack[-1].update(dt)


    def draw_debug(self):
        line_y = 5
        for name, value in self.debug_values.items():
            if isinstance(value, float):
                value = f'{value:.4f}'
            text = self.debug_font.render(f'{name}: {value}', True,
                                        pg.Color('white'), pg.Color('black'))
            self.display_screen.blit(text, (5, line_y))
            line_y += text.get_height()
        

    def draw(self):
        # find the lowest visible scene, then draw upwards
        first_visible = len(self.scene_stack) - 1
        while first_visible > 0 and self.scene_stack[first_visible].transparent:
            first_visible -= 1
        for scene in self.scene_stack[first_visible:]:
            scene.draw(self.game_screen)

        # scale up the game screen to the display
        transformed_screen = pg.transform.scale(self.game_screen, self.display_rect.size)
        self.display_screen.blit(transformed_screen, (0, 0))

        if self.show_debug:
            self.draw_debug()

        pg.display.update()
        
        
    def run(self):
        self.running = True
        while self.running:
            delta_time = self.clock.tick(self.config["Video.fps"]) / 1000
            pg.display.set_caption(f"FPS: {round(self.clock.get_fps(), 2)}")
            self.events()        
            self.update(delta_time)
            self.draw()

        self.config.save()
        pg.quit()
        
        
        
