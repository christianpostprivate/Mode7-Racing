import glob
from os import path

import pygame as pg

from src.scenes.scene import Scene


class CourseSelect(Scene):
    def __init__(self, game, **kwargs):
        super().__init__(game)
        # every .tmx file in the assets folder is a course
        tmx_files = glob.glob(path.join(game.assets_folder, "courses", "*.tmx"))
        self.courses = sorted(path.splitext(path.basename(f))[0] for f in tmx_files)
        self.selected_index = 0


    def get_event(self, event):
        if event.type != pg.KEYDOWN:
            return
        if event.key == pg.K_ESCAPE:
            self.game.switch_scene("TitleScreen")
        elif not self.courses:
            return
        elif event.key in (pg.K_w, pg.K_UP):
            self.selected_index = (self.selected_index - 1) % len(self.courses)
        elif event.key in (pg.K_s, pg.K_DOWN):
            self.selected_index = (self.selected_index + 1) % len(self.courses)
        elif event.key in (pg.K_RETURN, pg.K_SPACE):
            self.game.switch_scene("KartSelect", course_name=self.courses[self.selected_index])


    def draw(self, screen):
        screen.fill(pg.Color("black"))
        center_x = screen.get_width() // 2
        self.draw_text(screen, "SELECT COURSE", (center_x, 20))

        if not self.courses:
            self.draw_text(screen, "No courses found", (center_x, 70), "red")
            return

        for index, course_name in enumerate(self.courses):
            is_selected = index == self.selected_index
            label = f"> {course_name} <" if is_selected else course_name
            color = "yellow" if is_selected else "white"
            self.draw_text(screen, label, (center_x, 50 + index * 14), color)