from src.parser import Config
from .scores import Scores
from src.gui import GUI, PANELS
from .level import Level, RANDOM_SEED
from src.ghost import GHOST_SPEED_RATIO
from src.player import level_speed
import math
from typing import Any
import pygame

# Arrow keys, and the WASD keys by physical position (scancodes), so the
# same keys work as ZQSD on an AZERTY keyboard.
ARROW_KEYS = {pygame.K_UP: "up", pygame.K_DOWN: "down",
              pygame.K_LEFT: "left", pygame.K_RIGHT: "right"}
WASD_SCANCODES = {pygame.KSCAN_W: "up", pygame.KSCAN_S: "down",
                  pygame.KSCAN_A: "left", pygame.KSCAN_D: "right"}


class Gameplay:

    # pac-man.py can't be imported by name (the hyphen), and the packaged
    # app doesn't ship it as a module, so the state machine is typed Any.
    def __init__(self, pacman: Any, config: Config, scores: Scores,
                 gui: GUI) -> None:
        
        self.state_machine = pacman
        self.gui = gui
        self.config = config
        self.scores = scores
        self.score = 0
        self.lives = config.lives
        self.level_index = 0
        self.menu: str | None = None  # "pause" or "cheat": game frozen
        self.menu_index = 0  # button lit in that menu
        self.invincible = False  # cheat: ghosts cost no life
        self.ghosts_frozen = False  # cheat: ghosts stand still
        self._load_level(0)

    def _load_level(self, level: int) -> None:

        self.level_index = level
        seed = self.config.seed if level == 0 else RANDOM_SEED
        self.level = Level(self.config.levels[level], self.config, seed)
        self.level.player.speed = level_speed(level)
        for ghost in self.level.ghosts:
            ghost.speed = GHOST_SPEED_RATIO * self.level.player.speed
        self.relayout()
        self.time_left = float(self.config.level_max_time)  # seconds

    def relayout(self) -> None:
        """Fit the maze of the current level to the window, as it is now.

        Called on each new level and whenever the window changes size; the
        game itself (score, positions, time) is left untouched. Every
        level starts on the left edge of the biggest maze on screen,
        centred on its height, so the maze never drifts to the right.
        """
        frame = self.gui.maze_frame(
            [(level.width, level.height) for level in self.config.levels])
        self.gui.set_layout(*self.level.dimensions, frame)
        self.surface = self.gui.create_maze_surface(self.level.maze)

    def update(self, events: list[pygame.event.Event], dt: float) -> None:

        if self.paused:  # nothing moves: dt is never used while paused
            self._update_menu(events)
            return
        for event in events:
            if event.type == pygame.QUIT:
                self.state_machine.running = False
                return
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and self.gui.back_button_hit(event.pos)):
                self._back_to_menu()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._back_to_menu()
                    return
                if event.key == pygame.K_SPACE:
                    self._pause("pause")
                    return  # frozen as it is: no move on this frame
                if event.key == pygame.K_c:
                    self._pause("cheat")
                    return
                direction = (ARROW_KEYS.get(event.key)
                             or WASD_SCANCODES.get(event.scancode))
                if direction is not None:
                    self.level.player.turn(direction)
        player = self.level.player
        for cell in player.update(self.level.maze, dt):
            if cell in self.level.available_super_pacgums:
                for ghost in self.level.ghosts:
                    ghost.frighten()
            self.score += self.level.eat(cell)
        for ghost in self.level.ghosts:
            if ghost.edible:
                ghost.flee(player)
            elif not ghost.eaten:
                ghost.chase(player, self.level.maze)
            if not self.ghosts_frozen:
                ghost.update(self.level.maze, dt)
            if ghost.eaten or not ghost.touches(player):
                continue
            if not ghost.edible:
                if self.invincible:
                    continue  # Pac-Man goes through the ghost
                self._lose_life()
                return
            ghost.get_eaten()
            self.score += self.config.points_per_ghost
        if self.level.cleared:
            self._next_level()
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self._time_up()

    @property
    def paused(self) -> bool:
        """Tell whether a menu (pause or cheat) freezes the game."""
        return self.menu is not None

    def _pause(self, menu: str) -> None:
        """Freeze the game and open a menu, its first button lit.

        Args:
            menu: The menu to open: "pause" or "cheat".
        """
        self.menu = menu
        self.menu_index = 0

    def _update_menu(self, events: list[pygame.event.Event]) -> None:
        """Run the open menu while the game stays frozen.

        UP/DOWN and the mouse choose a button, ENTER and a click select
        it. Every other key, SPACE, C and ESC included, is ignored.
        """
        assert self.menu is not None
        count = len(PANELS[self.menu][3])
        for event in events:
            if event.type == pygame.QUIT:
                self.state_machine.running = False
                return
            if event.type == pygame.MOUSEMOTION:
                index = self.gui.panel_item_at(self.menu, event.pos)
                if index is not None:
                    self.menu_index = index
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = self.gui.panel_item_at(self.menu, event.pos)
                if index is not None:
                    self._select_menu_item(index)
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.menu_index = (self.menu_index - 1) % count
                elif event.key == pygame.K_DOWN:
                    self.menu_index = (self.menu_index + 1) % count
                elif event.key == pygame.K_RETURN:
                    self._select_menu_item(self.menu_index)
                    return

    def _select_menu_item(self, index: int) -> None:
        """Do what the button at index of the open menu says.

        Pause: RESUME or MAIN MENU. Cheat: switch INVINCIBLE or FREEZE
        GHOSTS on or off (the menu stays open), SKIP LEVEL (the menu
        closes on the next level) or RESUME.
        """
        assert self.menu is not None
        item = PANELS[self.menu][3][index]
        if item == "RESUME":
            self.menu = None
        elif item == "MAIN MENU":
            self._back_to_menu()
        elif item == "INVINCIBLE":
            self.invincible = not self.invincible
        elif item == "FREEZE GHOSTS":
            self.ghosts_frozen = not self.ghosts_frozen
        elif item == "SKIP LEVEL":
            self.menu = None
            self._next_level()

    def _high_score(self) -> int:
        """Return the best score saved in the leaderboard, 0 if none."""
        entries = self.scores.fetch_entries()
        return entries[0]["score"] if entries else 0

    def _time_up(self) -> None:
        """Out of time: one life less, then the level timer starts again."""
        self._lose_life()
        self.time_left = float(self.config.level_max_time)

    def _lit_logo(self) -> list[tuple[int, int]]:
        """Return the cells of the "42" still lit, as a gauge of the time.

        The logo empties from the top, one cell at a time, as the time
        left goes down; Level.logo lists its cells row by row, top first.
        """
        logo = self.level.logo
        lit = math.ceil(len(logo) * self.time_left
                        / self.config.level_max_time)
        return logo[len(logo) - lit:]

    def _next_level(self) -> None:
        """Load the next level, or go back to the menu after the last one."""
        if self.level_index + 1 < len(self.config.levels):
            self._load_level(self.level_index + 1)
        else:
            self._end_game(won=True)

    def _back_to_menu(self) -> None:
        """End this game session and show the main menu."""
        self.state_machine.game_active = False
        self.state_machine.state = "main_menu"

    def _end_game(self, won: bool) -> None:
        """End this game session and open the victory or game-over screen.

        The state machine gets the result and the final score, so the end
        screen can save it under the name the player types.
        """
        self.state_machine.win = won
        self.state_machine.final_score = self.score
        self.state_machine.finished = True
        self.state_machine.game_active = False

    def _lose_life(self) -> None:
        """Pac-Man was caught: one life less, then everyone restarts."""
        self.lives -= 1
        if self.lives <= 0:
            self._end_game(won=False)
            return
        self.level.player.respawn()
        for ghost in self.level.ghosts:
            ghost.respawn()

    def draw(self) -> None:

        self.gui.draw_maze(self.surface)
        self.gui.draw_logo(self._lit_logo())
        self.gui.draw_pacgums(self.level.available_pacgums, self.level.available_super_pacgums)
        for ghost in self.level.ghosts:
            self.gui.draw_ghost(ghost.position, ghost.name, ghost.facing,
                                ghost.fright_time, ghost.eaten)
        player = self.level.player
        self.gui.draw_player(player.position, player.facing,
                             player.mouth_opening)
        self.gui.draw_hud(self.score, self.level_index + 1, self.lives,
                          self.time_left)
        if self.menu == "pause":
            self.gui.draw_pause(self.menu_index, self.score,
                                self._high_score())
        elif self.menu == "cheat":
            self.gui.draw_cheat(self.menu_index, self.score,
                                self.level_index + 1, self.lives,
                                self.time_left,
                                (self.invincible, self.ghosts_frozen))