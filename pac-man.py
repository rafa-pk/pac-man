import sys
import pygame
from src.parser import Parser
from src.gui import GUI
from src.game.scores import Scores
from mazegenerator.mazegenerator import MazeGenerator


class Pacman: 

    def __init__(self, config_file: str) -> None:
        self.config = Parser.get_config(config_file)
        
        pygame.init()
        self.screen = pygame.display.set_mode((1400, 800))
        pygame.display.set_caption("Pac-man @ 42")
        self.running: bool = True
        self.state: str = "main_menu"
        self.win: bool = None
        self.current_level = 0
        self.scores = Scores(self.config.highscore_filename)
        self.gui = GUI(self.screen, self)
        self.menu_index = 0
        self.game_active = False
        self.finished = False
        self._run()

    def _main_menu(self, events: list[pygame.event.Event], dt: int) -> None:
        
        menu_items = ["game", "highscores", "instructions", "exit"]

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.menu_index = (self.menu_index - 1) % len(menu_items)
                elif event.key == pygame.K_DOWN:
                    self.menu_index = (self.menu_index + 1) % len(menu_items)
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_RETURN:
                    if menu_items[self.menu_index] == "exit":
                        self.running = False
                        return
                    self.state = menu_items[self.menu_index]
                    return
        self.gui.draw_main_menu(self.menu_index)

    def _highscores(self, events: list[pygame.event.Event], dt: int) -> None:

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_RETURN:
                    self.state = "main_menu"
                    return
        self.gui.draw_highscores(self.scores)

    def _instructions(self, events: list[pygame.event.Event], dt: int) -> None:

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_RETURN:
                    self.state = "main_menu"
                    return
        self.gui.draw_instructions()

    def _game(self, events: list[pygame.event.Event], dt: int) -> None:
    
        from src.game.gameplay import Gameplay
        
        if not self.game_active:
            self.gameplay = Gameplay(self, self.config, self.scores, self.gui)
            self.game_active = True 
        self.gameplay.update(events, dt)
        self.gameplay.draw()
        if self.finished:
            self.state = "game_end"


    # def game_end(self, events, dt) -> None:

    def _run(self) -> None:

        program_states = {
            "main_menu": self._main_menu,
            "highscores": self._highscores,
            "instructions": self._instructions,
            "game": self._game,
            # "game_end": self._end_game,
        }

        clock = pygame.time.Clock()

        try:
            while self.running:
                dt = clock.tick(60) / 1000.0
                events = pygame.event.get()
                program_states[self.state](events, dt)
                pygame.display.flip()
        except KeyboardInterrupt:
            print("Error: Main Loop: Program Interrupted.\n")
            pygame.quit()
            sys.exit(1)


def main() -> None:

    if len(sys.argv) != 2 or not sys.argv[1].endswith(".json"):
        print("Error: Wrong arguments.\nUsage: python3 pac-man.py config.json")
        sys.exit(1)
    else:
        Pacman(sys.argv[1])


if __name__ == "__main__":
    main()
