"""The persistent top 10: loaded at game start, saved at game end."""
import json
import re
import sys
from pathlib import Path
from typing import TypedDict

MAX_ENTRIES = 10
# A name: 1 to 10 letters, digits or spaces, as the subject requires
NAME_RULE = re.compile(r"[A-Za-z0-9 ]{1,10}")


class Entry(TypedDict):
    """One line of the leaderboard."""

    name: str
    score: int


def valid_entry(name: object, score: object) -> bool:
    """Tell whether name and score follow the rules of the subject.

    type(score) is int, not isinstance: True and False are ints too.
    """
    return (isinstance(name, str) and NAME_RULE.fullmatch(name) is not None
            and type(score) is int and score >= 0)


class Scores:
    """The top 10, kept in memory and saved as JSON.

    The file holds {"leaderboard": [{"name": ..., "score": ...}]}. A
    missing file means no score yet. A broken file or entry is reported
    and skipped, so the game always starts; the next save replaces it.
    """

    def __init__(self, filename: str) -> None:
        """Load the top 10 saved in filename."""
        self.path = Path(filename)
        self.entries = self._load()

    def fetch_entries(self) -> list[Entry]:
        """Return the top 10, best score first."""
        return self.entries

    def add_entry(self, name: str, score: int) -> bool:
        """Add a score, keep the 10 best and save them.

        Returns:
            False, and nothing changes, if name or score breaks the rules.
        """
        if not valid_entry(name, score):
            return False
        self.entries.append({"name": name, "score": score})
        self.entries.sort(key=lambda entry: entry["score"], reverse=True)
        del self.entries[MAX_ENTRIES:]
        self._save()
        return True

    def _load(self) -> list[Entry]:
        """Read the file, keeping only the entries that follow the rules."""
        if not self.path.exists():
            return []
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError) as error:  # unreadable or not JSON
            _warn(f"{self.path} can't be read ({error}); no score loaded.")
            return []
        raw = data.get("leaderboard") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            _warn(f'{self.path} has no "leaderboard" list; no score loaded.')
            return []
        entries: list[Entry] = [
            {"name": item["name"], "score": item["score"]} for item in raw
            if isinstance(item, dict)
            and valid_entry(item.get("name"), item.get("score"))]
        if len(entries) < len(raw):
            _warn(f"{len(raw) - len(entries)} invalid entries ignored in "
                  f"{self.path}.")
        entries.sort(key=lambda entry: entry["score"], reverse=True)
        return entries[:MAX_ENTRIES]

    def _save(self) -> None:
        """Write the top 10; a failure is reported, never fatal."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump({"leaderboard": self.entries}, file, indent=4)
        except OSError as error:
            _warn(f"the scores could not be saved in {self.path} ({error}).")


def _warn(message: str) -> None:
    """Print one highscore warning on stderr."""
    print(f"Highscores: {message}", file=sys.stderr)
