import pygame
from .constants import FONT, LOGO, TILE, TOP, RIGHT, BOTTOM, LEFT, WALL_COLOR, WALL, MAZE_OFFSET, LOGO_COLOR
from src.game.scores import Scores


class GUI:

    def __init__(self, screen: pygame.Surface, program: "Pacman") -> None:

        self.screen = screen
        self.program = program
        self.logo = pygame.image.load(LOGO).convert_alpha()
        self.pacgum_sprite = self.make_circle_sprite(3, (255, 253, 208))
        self.super_sprite = self.make_circle_sprite(6, (255, 253, 208))
 
    def fill_circle(self, surface: pygame.Surface, color: tuple[int, int, int], cx: int, cy: int, radius: int) -> None:

        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r2:
                    surface.set_at((cx + dx, cy + dy), color)

    def make_circle_sprite(self, radius: int, color: tuple[int, int, int]) -> pygame.Surface:
        size = radius * 2 + 1
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        self.fill_circle(sprite, color, radius, radius, radius)
        return sprite

    def string_put(self, x: int, y: int, color: tuple[int, int, int], font: str, text: str) -> None:

        string = font.render(text, False, color)
        self.screen.blit(string, (x, y))

    def draw_cursor(self, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:

        medial_point = size // 2

        for row in range(size):
            width = size * (medial_point - abs(row - medial_point)) // medial_point
            for px in range(width):
                self.screen.set_at((x + px, y + row), color)

    def draw_main_menu(self, menu_index: int) -> None:

        self.screen.fill((0, 0, 0))
        self.screen.blit(self.logo, (300, 20))

        font = pygame.font.Font(FONT, 30)
        self.string_put(500, 300, (255, 253, 208), font, "1 START")
        self.string_put(500, 370, (255, 253, 208), font, "2 HIGHSCORES")
        self.string_put(500, 440, (255, 253, 208), font, "3 INSTRUCTIONS")
        self.string_put(500, 510, (255, 253, 208), font, "4 EXIT")
        self.string_put(10, 650, (255, 253, 208), font, "© This project has been created as part of the")
        self.string_put(10, 700, (255, 253, 208), font, "42 curriculum by rvaz-da-")

        if menu_index == 0:
            self.draw_cursor(470, 300, 20, (255, 253, 208))
        elif menu_index == 1:
            self.draw_cursor(470, 370, 20, (255, 253, 208))
        elif menu_index == 2:
            self.draw_cursor(470, 440, 20, (255, 253, 208)) 
        elif menu_index == 3:
            self.draw_cursor(470, 510, 20, (255, 253, 208))

    def draw_highscores(self, scores: Scores) -> None:

        self.screen.fill((0, 0, 0))
        self.screen.blit(self.logo, (300, 20))

        title_font = pygame.font.Font(FONT, 50)
        self.string_put(415, 280, (255, 253, 208), title_font, "HIGH SCORES")
        
        top_ten = scores.fetch_entries()
        small_font = pygame.font.Font(FONT, 20)
        self.draw_cursor(80, 700, 20, (255, 253, 208))
        self.string_put(110, 703, (255, 253, 208), small_font, "Back")
        if top_ten == []: 
            self.string_put(520, 500, (255, 253, 208), small_font, "No scores yet :(")
            return

        rank_font = pygame.font.Font(FONT, 25)
        positions = ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH", "9TH", "10TH"]
        sx, sy = 370, 350
        for i, position in enumerate(positions[:len(top_ten)]):
            sy += 35
            self.string_put(sx, sy, (255, 253, 208), rank_font, position)
            pos_w = rank_font.size("W"*4)[0]
            sp_w = rank_font.size(" ")[0]
            name_x = sx + pos_w + sp_w
            self.string_put(name_x, sy, (255, 253, 208), rank_font, top_ten[i]["name"])
            name_w = rank_font.size("W"*15)[0]
            self.string_put(name_x + name_w + 15, sy, (255, 253, 208), rank_font, top_ten[i]["score"])
 
    def draw_instructions(self) -> None:

        self.screen.fill((0, 0, 0))
        self.screen.blit(self.logo, (300, 200))

        title_font = pygame.font.Font(FONT, 50)
        # self.string_put( , (255, 253, 208), title_font, "INSTRUCTIONS")

    def draw_rect(self, surface: pygame.Surface, color: tuple[int, int, int], x: int, y: int, w: int, h: int) -> None:

        for py in range(y, y + h):
            for px in range(x, x + w):
                surface.set_at((px, py), color) 

    def create_maze_surface(self, maze: list[list[int]]) -> pygame.Surface:

        surface = pygame.Surface((len(maze[0]) * TILE, len(maze) * TILE))

        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                px, py = x * TILE, y * TILE
                if cell == 15:
                    self.draw_rect(surface, LOGO_COLOR, px, py, TILE, TILE)
                if cell & TOP:
                    self.draw_rect(surface, WALL_COLOR, px, py, TILE, WALL)
                if cell & RIGHT:
                    self.draw_rect(surface, WALL_COLOR, px + TILE - WALL, py, WALL, TILE)
                if cell & BOTTOM:
                    self.draw_rect(surface, WALL_COLOR, px, py + TILE - WALL, TILE, WALL)
                if cell & LEFT:
                    self.draw_rect(surface, WALL_COLOR, px, py, WALL, TILE)
        return surface

    def draw_pacgums(self, available_pg: set[tuple[int, int]], available_spg: set[tuple[int, int]]) -> None:

        ox, oy = MAZE_OFFSET
        w_pg, h_pg = self.pacgum_sprite.get_size()
        w_spg, h_spg = self.super_sprite.get_size()

        for x, y in available_pg:
            px = ox + x * TILE + (TILE - w_pg) // 2
            py = oy + y * TILE + (TILE - h_pg) // 2
            self.screen.blit(self.pacgum_sprite, (px, py))
        for x, y in available_spg:
            px = ox + x * TILE + (TILE - w_spg) // 2
            py = oy + y * TILE + (TILE - h_spg) // 2
            self.screen.blit(self.super_sprite, (px, py))

    def draw_maze(self, maze_surface: pygame.Surface, available_pg: set[tuple[int, int]], available_spg: set[tuple[int, int]]) -> None:
    
        small_font = pygame.font.Font(FONT, 20)

        self.screen.fill((0, 0, 0))
        self.screen.blit(maze_surface, MAZE_OFFSET)
        self.draw_pacgums(available_pg, available_spg)
        self.draw_cursor(80, 700, 20, (255, 253, 208))
        self.string_put(110, 703, (255, 253, 208), small_font, "Back")


