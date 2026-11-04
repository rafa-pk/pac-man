"""Shared pytest fixtures."""
import os
from pathlib import Path
from typing import Callable

import pytest

# Never open a window during the tests.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


@pytest.fixture
def write_config(tmp_path: Path) -> Callable[[str], str]:
    """Return a function that writes a config file and gives back its path."""
    def write(content: str) -> str:
        path = tmp_path / "config.json"
        path.write_text(content, encoding="utf-8")
        return str(path)
    return write
