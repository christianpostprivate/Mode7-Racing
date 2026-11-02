import pygame as pg


class Scene:
    """Base class for all scenes. Scenes live on the game's scene stack."""

    # if True, the scene below this one is drawn first (e.g. pause menu overlay)
    transparent = False

    def __init__(self, game, **kwargs):
        self.game = game

    def startup(self):
        pass

    def cleanup(self):
        pass

    def get_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def draw_text(self, screen, text, pos, color="white", anchor="center"):
        # no antialiasing to keep hard pixel edges
        shadow = self.game.font.render(text, False, pg.Color("black"))
        text_surface = self.game.font.render(text, False, pg.Color(color))
        rect = text_surface.get_rect(**{anchor: pos})
        screen.blit(shadow, rect.move(1, 1))
        screen.blit(text_surface, rect)
        return rect