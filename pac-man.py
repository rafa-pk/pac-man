import sys
import pygame
from src.constants import (NAME_INPUT_MAX, frozen, resource_path,
                           user_data_path)
from src.parser import Parser
from src.gui import END_ITEMS, GUI
from src.game.scores import Scores

# State opened by each main-menu entry, in the order of the menu
MENU_STATES = ["game", "highscores", "instructions", "exit"]


class Pacman: 

    def __init__(self, config_file: str) -> None:
        self.config = Parser.get_config(config_file)
        
        pygame.init()
        sizes = pygame.display.get_desktop_sizes()
        width, height = sizes[0] if sizes else (1400, 800)
        # 90 % of the screen; resizable, so macOS enables the green button
        # (native fullscreen) next to the red one (close, i.e. pygame.QUIT)
        self.screen = pygame.display.set_mode((width * 9 // 10,
                                               height * 9 // 10),
                                              pygame.RESIZABLE)
        pygame.display.set_caption("Pac-man @ 42")
        self.running: bool = True
        self.state: str = "main_menu"
        self.win = False  # result of the last game, for the end screen
        self.final_score = 0  # score of the last game, saved by the player
        self.player_name = ""  # text typed in the end-screen name box
        self.end_index = 0  # button lit on the end screen (0 = SAVE SCORE)
        self.name_error = False  # the last name typed broke the rule
        self.current_level = 0
        scores_file = self.config.highscore_filename
        if frozen():  # the app's own folder is no place for the scores
            scores_file = user_data_path(scores_file)
        self.scores = Scores(scores_file)
        self.gui = GUI(self.screen, self)
        self.menu_index = 0
        self.game_active = False
        self.finished = False
        self._run()

    def _main_menu(self, events: list[pygame.event.Event],
                   dt: float) -> None:

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEMOTION:
                index = self.gui.menu_item_at(event.pos)
                if index is not None:
                    self.menu_index = index
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = self.gui.menu_item_at(event.pos)
                if index is not None:
                    self._open(index)
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.menu_index = (self.menu_index - 1) % len(MENU_STATES)
                elif event.key == pygame.K_DOWN:
                    self.menu_index = (self.menu_index + 1) % len(MENU_STATES)
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_RETURN:
                    self._open(self.menu_index)
                    return
        self.gui.draw_main_menu(self.menu_index)

    def _open(self, index: int) -> None:
        """Open the screen of the menu entry index, or quit on EXIT."""
        if MENU_STATES[index] == "exit":
            self.running = False
        else:
            self.state = MENU_STATES[index]

    def _wants_back(self, event: pygame.event.Event) -> bool:
        """Tell whether event asks to go back to the main menu."""
        if event.type == pygame.KEYDOWN:
            return event.key in (pygame.K_ESCAPE, pygame.K_RETURN)
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.gui.back_button_hit(event.pos))

    def _highscores(self, events: list[pygame.event.Event],
                    dt: float) -> None:

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif self._wants_back(event):
                self.state = "main_menu"
                return
        self.gui.draw_highscores(self.scores)

    def _instructions(self, events: list[pygame.event.Event],
                      dt: float) -> None:

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif self._wants_back(event):
                self.state = "main_menu"
                return
        self.gui.draw_instructions(self.config)

    def _game(self, events: list[pygame.event.Event], dt: float) -> None:
    
        from src.game.gameplay import Gameplay
        
        if not self.game_active:
            self.gameplay = Gameplay(self, self.config, self.scores, self.gui)
            self.game_active = True 
        self.gameplay.update(events, dt)
        self.gameplay.draw()
        if self.finished:
            self.state = "game_end"
            pygame.key.start_text_input()  # typed text for the name box

    def _game_end(self, events: list[pygame.event.Event],
                  dt: float) -> None:
        """Victory or game-over screen: type a name, save the score.

        Typed characters go in the name box (BACKSPACE erases), UP/DOWN
        and the mouse choose a button, ENTER and a click select it, ESC
        closes the program.
        """
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.TEXTINPUT:
                room = NAME_INPUT_MAX - len(self.player_name)
                self.player_name += event.text[:room]
                self.name_error = False
            elif event.type == pygame.MOUSEMOTION:
                index = self.gui.end_item_at(event.pos)
                if index is not None:
                    self.end_index = index
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = self.gui.end_item_at(event.pos)
                if index is not None:
                    self._select_end_item(index)
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                elif event.key == pygame.K_UP:
                    self.end_index = (self.end_index - 1) % len(END_ITEMS)
                elif event.key == pygame.K_DOWN:
                    self.end_index = (self.end_index + 1) % len(END_ITEMS)
                elif event.key == pygame.K_RETURN:
                    self._select_end_item(self.end_index)
                    return
        self.gui.draw_game_end(self.win, self.final_score, self.player_name,
                               self.end_index, self.name_error)

    def _select_end_item(self, index: int) -> None:
        """Save the score then show the high scores, or leave unsaved.

        A name that breaks the rule is not saved: the box is cleared and
        the rule is shown as an error.
        """
        if END_ITEMS[index] == "MAIN MENU":
            self._leave_game_end("main_menu")
        elif self.scores.add_entry(self.player_name, self.final_score):
            self._leave_game_end("highscores")
        else:
            self.player_name = ""
            self.name_error = True

    def _leave_game_end(self, state: str) -> None:
        """Close the end screen, ready for the next game, and open state."""
        pygame.key.stop_text_input()
        self.finished = False  # else the next game would end at once
        self.player_name = ""
        self.end_index = 0
        self.name_error = False
        self.state = state

    def _resize(self) -> None:
        """Fit every screen, and the maze of a running game, to the window."""
        self.screen = pygame.display.get_surface()
        self.gui.resize(self.screen)
        if self.game_active:
            self.gameplay.relayout()

    def _run(self) -> None:

        program_states = {
            "main_menu": self._main_menu,
            "highscores": self._highscores,
            "instructions": self._instructions,
            "game": self._game,
            "game_end": self._game_end,
        }

        clock = pygame.time.Clock()

        try:
            while self.running:
                dt = clock.tick(60) / 1000.0
                events = pygame.event.get()
                if any(event.type == pygame.WINDOWSIZECHANGED
                       for event in events):
                    self._resize()
                program_states[self.state](events, dt)
                pygame.display.flip()
            pygame.quit()
        except KeyboardInterrupt:
            print("Error: Main Loop: Program Interrupted.\n")
            pygame.quit()
            sys.exit(1)


def main() -> None:

    args = sys.argv[1:]
    if frozen():  # the downloadable app, usually started by a double-click
        # older macOS versions add a -psn_... argument to a double-click
        args = [arg for arg in args if not arg.startswith("-psn")]
        if not args:
            args = [resource_path("config.json")]  # the one it carries
    if len(args) != 1 or not args[0].endswith(".json"):
        print("Error: Wrong arguments.\nUsage: python3 pac-man.py config.json")
        sys.exit(1)
    else:
        Pacman(args[0])


if __name__ == "__main__":
    main()
