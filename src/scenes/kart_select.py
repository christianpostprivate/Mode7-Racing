from math import pi

import pygame as pg

from src.scenes.scene import Scene
from src.sprites import get_kart_frame


class KartSelect(Scene):
    SPIN_SPEED = pi  # rad/s, rotation of the selected kart
    SLOT_WIDTH = 45  # px between kart previews
    KART_BOTTOM = 90  # screen y of the kart previews

    def __init__(self, game, course_name="track2", **kwargs):
        super().__init__(game)
        self.course_name = course_name
        self.selected_index = 0
        self.spin_angle = 0.0

    def get_event(self, event):
        if event.type != pg.KEYDOWN:
            return
        kart_count = len(self.game.kart_names)
        if event.key == pg.K_ESCAPE:
            self.game.switch_scene("CourseSelect")
        elif event.key in (pg.K_a, pg.K_LEFT):
            self.selected_index = (self.selected_index - 1) % kart_count
            self.spin_angle = 0.0
        elif event.key in (pg.K_d, pg.K_RIGHT):
            self.selected_index = (self.selected_index + 1) % kart_count
            self.spin_angle = 0.0
        elif event.key in (pg.K_RETURN, pg.K_SPACE):
            self.game.switch_scene("Race", course_name=self.course_name,
                                   kart_name=self.game.kart_names[self.selected_index])

    def update(self, dt):
        self.spin_angle += self.SPIN_SPEED * dt

    def draw(self, screen):
        screen.fill(pg.Color("black"))
        center_x = screen.get_width() // 2
        self.draw_text(screen, "SELECT KART", (center_x, 20))

        kart_count = len(self.game.kart_names)
        first_x = center_x - (kart_count - 1) * self.SLOT_WIDTH / 2
        for index, kart_name in enumerate(self.game.kart_names):
            is_selected = index == self.selected_index
            yaw = self.spin_angle if is_selected else pi  # others face the camera
            image = get_kart_frame(self.game.kart_images[kart_name],
                                   self.game.kart_images_flipped[kart_name], yaw)
            slot_x = first_x + index * self.SLOT_WIDTH
            screen.blit(image, image.get_rect(midbottom=(slot_x, self.KART_BOTTOM)))
            if is_selected:
                self.draw_text(screen, "^", (slot_x, self.KART_BOTTOM + 10), "yellow")

        self.draw_text(screen, "Enter: start", (center_x, 130))