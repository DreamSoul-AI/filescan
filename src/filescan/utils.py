import os
from pathlib import Path
from pathspec import PathSpec


def makedir_exist_ok(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def load_ignore_spec(ignore_file: Path):
    if ignore_file is None:
        return None
    patterns = ignore_file.read_text(encoding="utf-8").splitlines()
    ignore_spec = PathSpec.from_lines("gitwildmatch", patterns)
    return ignore_spec
