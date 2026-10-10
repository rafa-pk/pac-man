import json
import sys
import re
from typing import Any
from pathlib import Path


class Scores:

    def __init__(self, filename: str) -> None:

        self.filename = filename
        self.create_file(self.filename)
        self.name_entry_validation = re.compile(r"[A-Z0-9 ]{1, 10}", re.IGNORECASE)

    def create_file(self, filename: str) -> None:

        file = Path(filename)
        if not file.is_file():
            file.parent.mkdir(parents=True, exist_ok=True)
            file.touch(exist_ok=True)
            return
        try:
            contents = file.read_text(encoding="utf-8")
            data = json.loads(contents)
            if not isinstance(data, dict):
                raise Exception("Error: {filename} does not contain valid JSON.")
        except Exception as message:
            print(f"Error: Leaderboard file could not be opened or is invalid: {message}.")
            sys.exit(1)

    def add_entry(self, name: str, score: int) -> None:

        new_score = {
            "name": name,
            "score": score
        }

        try:
            self.name_entry_validation.fullmatch(new_score["name"])
            if not self.name_entry_validation:
                raise ValueError("Name must comply to: max 10 characters, alphanumeric and spaces only.")
            if new_score["score"] < 0:
                raise ValueError("Score cannot be negative.")
        except ValueError as error:
            print(f"Warning: {error}.")

        try:
            with open(self.filename, 'r') as file:
                content = json.loads(file)
        except Exception:
            content = {}
        current_scores = content.setdefault("leaderboard", [])
        current_scores["leaderboard"].append(new_score)
        current_scores.sort(key=lambda entry: float(entry["score"]), reverse=True)
        
        try:
            with open(self.filename, 'w') as file:
                json.dump(current_scores, file, indent=4)
        except Exception as error:
            print(f"Warning: Could not add score to leaderboard: {error}.")

    def fetch_entries(self) -> list[dict[Any]]:

        try:
            with open(self.filename, 'r') as file:
                scores = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []
        except OSError as message:
            print(f"Error: Could not fetch scores: {message}")
            sys.exit(1)
        # scores["leaderboard"].sort(key=lambda entry: float(entry["score"]), reverse=True)                 # For testing purposes, to be removed
        return scores["leaderboard"][:10]