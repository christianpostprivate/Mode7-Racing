import pygame as pg

from src.scenes.scene import Scene


class TitleScreen(Scene):
    def __init__(self, game, **kwargs):
        super().__init__(game)
        self.blink_timer = 0

    def get_event(self, event):
        if event.type == pg.KEYDOWN and event.key != pg.K_F1:
            self.game.switch_scene("CourseSelect")

    def update(self, dt):
        self.blink_timer += dt

    def draw(self, screen):
        screen.fill(pg.Color("black"))
        center_x = screen.get_width() // 2
        self.draw_text(screen, "SUPER KART RACER", (center_x, 50))
        if int(self.blink_timer * 2) % 2 == 0:
            self.draw_text(screen, "Press any key", (center_x, 100))