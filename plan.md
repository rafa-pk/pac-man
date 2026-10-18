
# Game Engine

## Gameplay class
- Is created every time "start" button is pressed on main menu
- Initializes every basic stat needed for a gameplay (score, lives, ...)

### Responsabilities
- Manages levels (creates first one w/ seed, other ones randomly)
- Manages time constraint (Initiates timer when new level starts, if max_time is exceeded, game is over)
- Manages per frame updates of in-game state, starting positions and moves
- Manages general stats

## Level class
- Is created when a level is created, either at first start, or when previous level was completed
- Initiates every level interface, containing the game logic

### Responsabilities
- Owns game logic
- Manages every update and calls the different algorithms
- Sends in-game state updates back to gameplay


## Logic
- Player (pacman) starts in the middle of the maze, with N lives
- N pacgums are equally spread out accross the maze
- 4 super pacgums are placed at the 4 corners of the maze
- Player moves depending on events:
    - Up key: move up by 1
    - Down key: move down by 1
    - Left key: move left by 1
    - Right key: move right by 1
    - (Will have to be replaced by WASD)
- If player touches ghost —> dies, respawns back in the middle, -1 life
- If player eats pacgum —> +N points
- If player eats super pacgum —> +N points and ghosts are edible
- When all pacgums are eaten —> level passed
- When all levels have been completed —> Game finished


