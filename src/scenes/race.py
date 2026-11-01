import traceback
from enum import Enum, auto

import pygame as pg

from src.scenes.scene import Scene
from src.render import Mode7
from src.camera import Camera, FollowMode, OrbitMode
from src.course import Course
from src.sprites import Player, TrafficLight, Billboard, PathFollower
from src.hud import HUD, LAP_COMPLETED
import src.utils as utils


class RacePhase(Enum):
    COUNTDOWN = auto()  # traffic light, no control
    RACING = auto()     # player has control
    FINISHED = auto()   # results over the running scene


class Race(Scene):
    MAX_LAPS = 3

    def __init__(self, game, course_name="track2", kart_name="kart2", **kwargs):
        super().__init__(game)
        self.course_name = course_name
        self.kart_name = kart_name
        self.phase = RacePhase.COUNTDOWN

        # read by HUD
        self.race_time = 0.0
        self.lap_start_time = 0.0
        self.lap_times = []  # store all lap times
        self.current_lap = 1
        self.max_laps = self.MAX_LAPS
        self.current_checkpoint = 0

        self.course = None
        self.player = None
        self.map = None
        self.camera = None
        self.hud = None
        self.traffic_light = None
        self.checkpoints = []
        self.num_checkpoints = 0


    def startup(self):
        # sprites, Mode7 and Course queries reach the race objects through game
        self.game.all_sprites = pg.sprite.Group()
        self.game.billboards = pg.sprite.Group()
        self.game.started = False
        self.game.course = None

        try:
            self.course = Course(self.game.assets_folder, self.course_name)
        except Exception:
            traceback.print_exc()
        self.game.course = self.course

        self.player = self.game.player = Player(self.game, self.kart_name)
        self.traffic_light = TrafficLight(self.game, (100, 60))
        self.map = self.game.map = Mode7(self.game, self.course.image if self.course else None)
        self.camera = self.game.camera = Camera(self.game, target=self.player)

        if self.course:
            start_pos = self.course.get_start_position(self.game.config["Gameplay.player_start_pos"])
            if start_pos is not None:
                self.player.pos = start_pos
            self.checkpoints = self.course.game_object_data.get("checkpoints", [])
            self.num_checkpoints = max(
                (obj.properties.get("number", 0) for obj in self.checkpoints), default=0)
            
            for obj in self.course.game_object_data.get("sprites", []):
                if obj.type == "billboard":
                    Billboard(self.game, obj)
                    
            # AI karts on grid positions 1-3, all karts the player didn't pick
            if len(self.course.path_points) > 1:
                ai_kart_names = [name for name in self.game.kart_names
                                 if name != self.kart_name]
                for position, kart_name in enumerate(ai_kart_names, start=1):
                    start_pos = self.course.get_start_position(position)
                    if start_pos is None:
                        continue
                    PathFollower(self.game, self.course.path_points, kart_name,
                                 start_pos, self.player.angle)

        # HUD reads lap/time/player/course from the race scene
        self.hud = HUD(self, self.course.tiled_map if self.course else None)


    def cleanup(self):
        self.game.all_sprites.empty()
        self.game.billboards.empty()
        self.game.started = False


    def get_event(self, event):
        self.hud.handle_event(event)
        if event.type != pg.KEYDOWN:
            return
        if event.key == pg.K_ESCAPE:
            self.game.switch_scene("CourseSelect")
        elif event.key == pg.K_RETURN and self.phase == RacePhase.FINISHED:
            self.game.switch_scene("CourseSelect")
        elif event.key == pg.K_c:  # debug: toggle camera mode
            if isinstance(self.camera.mode, OrbitMode):
                self.camera.set_mode(FollowMode())
            else:
                self.camera.set_mode(OrbitMode())


    def check_lap_progress(self):
        for checkpoint in self.checkpoints:
            if not utils.point_in_polygon(self.player.pos, checkpoint.points):
                continue
            if checkpoint.name == "finish" and self.current_checkpoint == self.num_checkpoints:
                # show the lap time in the HUD
                lap_time = self.race_time - self.lap_start_time
                pg.event.post(
                    pg.event.Event(LAP_COMPLETED,
                    lap=self.current_lap,
                    lap_time=lap_time)
                )
                self.lap_times.append(lap_time)
                self.lap_start_time = self.race_time
                self.current_lap += 1
                self.current_checkpoint = 0
            elif checkpoint.name == "checkpoint":
                number = checkpoint.properties.get("number")
                if number == self.current_checkpoint + 1:
                    self.current_checkpoint = number


    def update(self, dt):
        self.map.update(dt)

        if self.phase == RacePhase.COUNTDOWN:
            self.game.all_sprites.update(dt)
            self.game.billboards.update(dt)
            if self.traffic_light.done:
                self.phase = RacePhase.RACING
                self.game.started = True

        elif self.phase == RacePhase.RACING:
            self.race_time += dt
            self.game.all_sprites.update(dt)
            self.game.billboards.update(dt)
            self.check_lap_progress()
            if self.current_lap > self.max_laps:
                self.phase = RacePhase.FINISHED

        elif self.phase == RacePhase.FINISHED:
            # world keeps running, player is frozen
            self.game.all_sprites.update(dt)
            for billboard in self.game.billboards:
                if billboard is not self.player:
                    billboard.update(dt)

        # after all movement, so floor and billboards use the same camera
        self.camera.update(dt)
        for billboard in self.game.billboards:
            billboard.project()

        # debugging
        self.game.debug_values["phase"] = self.phase.name
        self.game.debug_values["pos"] = f"{self.player.pos.x:.3f}, {self.player.pos.y:.3f}"
        self.game.debug_values["last_road_pos"] = (
            f"{self.player.last_road_pos.x:.3f}, {self.player.last_road_pos.y:.3f}")
        self.game.debug_values["lap"] = f"{self.current_lap}/{self.max_laps}"
        self.game.debug_values["checkpoint"] = f"{self.current_checkpoint}"


    def blit_scrolling(self, screen, image, rate, y):
        # rate 1.0 = moves with the ground, < 1.0 = farther away
        image_width = image.get_width()
        offset = int(self.player.angle * self.game.sky_speed * rate) % image_width
        x = -offset
        while x < screen.get_width():  # tile if image is narrower than screen
            screen.blit(image, (x, y))
            x += image_width


    def draw(self, screen):
        self.blit_scrolling(screen, self.game.background, self.game.config["Visuals.sky_scroll_rate"], 0)
        self.blit_scrolling(screen, self.game.mountains, self.game.config["Visuals.mountain_scroll_rate"], self.game.mountains_y)
        self.map.draw(screen)
        # world sprites far to near, then screen sprites (traffic light, particles)
        for billboard in sorted(self.game.billboards, key=lambda b: b.depth, reverse=True):
            billboard.draw(screen)
        for sprite in self.game.all_sprites:
            sprite.draw(screen)

        if self.phase in [RacePhase.COUNTDOWN, RacePhase.RACING]:
            self.hud.draw(screen)

        elif self.phase == RacePhase.FINISHED:
            shade = pg.Surface(screen.get_size(), pg.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            screen.blit(shade, (0, 0))

            center_x = screen.get_width() // 2
            line_height = 12

            lines = [f"Total {HUD.format_time(self.race_time)}"]
            lines += [f"Lap {lap} {HUD.format_time(t)}" for lap, t in enumerate(self.lap_times, start=1)]
            text_x = center_x - max(self.game.font.size(line)[0] for line in lines) // 2

            self.draw_text(screen, "FINISH!", (center_x, 40), "yellow")

            fastest_lap = self.lap_times.index(min(self.lap_times)) + 1
            y = 65
            for index, line in enumerate(lines):
                color = "gold" if index == fastest_lap else "white"
                line_rect = self.draw_text(screen, line, (text_x, y), color, anchor="midleft")
                if index == fastest_lap:
                    star_rect = self.game.star_image.get_rect(midleft=(line_rect.right + 2, line_rect.centery))
                    screen.blit(self.game.star_image, star_rect)
                y += line_height

            self.draw_text(screen, "Enter: continue", (center_x, y + line_height))