from src.parser import Config
from .scores import Scores
from src.gui import GUI
from .level import Level
import importlib
import random
import pygame


class Gameplay:

    pacman = importlib.import_module("pac-man")
    Pacman = pacman.Pacman

    def __init__(self, pacman: Pacman, config: Config, scores: Scores, gui: GUI) -> None:
        
        self.state_machine = pacman
        self.gui = gui
        self.config = config
        self.scores = scores
        self.level_timer = 0
        self._load_level(0)

    def _load_level(self, level: int) -> None:

        if level == 0:
            self.level = Level(self.config.levels[0], self.config, self.config.seed)
        else:
            self.level = Level(self.config.levels[level], self.config, random.Random())
        self.surface = self.gui.create_maze_surface(self.level.maze)
        self.level_timer = 0

    def update(self, events: list[pygame.event.Event], dt: int) -> None:

        for event in events:
            if event.type == pygame.QUIT:
                self.state_machine.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state_machine.running = False
                if event.key == pygame.K_RETURN:
                    self.state_machine.game_active = False
                    self.state_machine.state = "main_menu"
                    return
                # if event.key == pygame.K_w:
                    # Player goes up
                # if event.key == pygame.K_s:
                    # Player goes down
                # if event.key == pygame.K_a:
                    # Player goes left
                # if event.key == pygame.K_d:
                    # Player goes right
        # self.level.update()

    def draw(self) -> None:

        self.gui.draw_maze(self.surface)
        self.gui.draw_pacgums(self.level.available_pacgums, self.level.available_super_pacgums)
        self.gui.draw_player(self.level.player.start_position)