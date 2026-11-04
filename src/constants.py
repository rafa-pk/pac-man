

import os
import sys
from pathlib import Path

APP_NAME = "Pacman42"  # name of the downloadable app (see make package)
# Folder holding assets/ and config.json when the game runs from the repo
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def frozen() -> bool:
    """Tell whether the game runs as the downloadable app.

    PyInstaller's launcher sets sys.frozen to True before starting the
    game; a plain python run never has this attribute, hence the getattr.
    """
    return bool(getattr(sys, "frozen", False))


def resource_path(relative: str) -> str:
    """Return the full path of a file shipped with the game.

    The app unpacks its files in the folder named by sys._MEIPASS;
    otherwise they sit in the project folder, wherever the game is
    started from.
    """
    return str(Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)) / relative)


def user_data_path(filename: str) -> str:
    """Return where the app keeps filename for the current user.

    The app's own folder may be read-only and is replaced by each new
    download, so the scores live in the user's data folder. An absolute
    path is kept as it is.
    """
    if Path(filename).is_absolute():
        return filename
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME")
                    or Path.home() / ".local" / "share")
    return str(base / APP_NAME / Path(filename).name)


FONT = resource_path("assets/Press_Start_2P/PressStart2P-Regular.ttf")
LOGO = resource_path("assets/pacman_logo.png")
# DEFAULT = [] (default config)
TILE = 50  # largest cell size in pixels; big mazes get smaller cells
MIN_TILE = 6  # smallest cell size: in a tiny window, the maze overflows
TOP, RIGHT, BOTTOM, LEFT = 1, 2, 4, 8
WALL_COLOR = (45, 75, 255)  # arcade neon blue
WALL = 3  # wall thickness for the largest cells
MAZE_LEFT = 300  # the HUD uses the screen left of this x
MARGIN = 25  # free space around the maze, in pixels
LOGO_COLOR = (255, 253, 208)  # the "42" cells
LOGO_SPENT_COLOR = WALL_COLOR  # a "42" cell once its share of time is spent
PACMAN_COLOR = (255, 255, 0)
TEXT_COLOR = (255, 253, 208)
BG_COLOR = (8, 8, 28)  # night blue
PACGUM_COLOR = (255, 184, 174)  # arcade peach
HIGHLIGHT_COLOR = (255, 200, 40)  # amber, like the logo
DIM_COLOR = (130, 130, 170)  # hints
GAME_OVER_COLOR = (255, 0, 0)  # arcade red, like Blinky
CHEAT_ON_COLOR = (60, 220, 60)  # green: a cheat that is on (off is red)
# Characters the name box takes: more than the 10 allowed, so a name too
# long is still typed, then refused with the rule when saved.
NAME_INPUT_MAX = 20
PAUSE_DIM_ALPHA = 170  # opacity (0-255) of the dark layer over a paused game
# Mouth openings of the Pac-Man frames, in degrees: closed, half, wide open
MOUTH_ANGLES = (0, 45, 90)
# Direction of the mouth, in degrees (the screen y axis points down)
FACING_ANGLES = {"right": 0, "down": 90, "left": 180, "up": 270}
# Body color of each ghost, as in the arcade game
GHOST_COLORS = {"blinky": (255, 0, 0), "pinky": (255, 184, 255),
                "inky": (0, 255, 255), "clyde": (255, 184, 82)}
EYE_COLOR = (255, 255, 255)
PUPIL_COLOR = (33, 33, 222)
# Edible ghosts are blue, and flash white in their last seconds
FRIGHT_COLOR = (33, 33, 255)
FLASH_COLOR = (255, 255, 255)
FLASH_TIME = 2.0  # seconds of flashing before a ghost is dangerous again
