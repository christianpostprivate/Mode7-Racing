import pygame as pg
import traceback
from src.game import Game

try:
    g = Game()
    g.run()
except Exception:
    traceback.print_exc()
    pg.quit()