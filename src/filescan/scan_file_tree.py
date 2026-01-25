#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

try:
    from pathspec import PathSpec
except ImportError:
    PathSpec = None


def load_ignore_spec(ignore_file: Path):
    if ignore_file is None:
        return None
    if PathSpec is None:
        raise SystemExit(
            "Error: pathspec is required for ignore support.\n"
            "Install with: pip install pathspec"
        )
    patterns = ignore_file.read_text(encoding="utf-8").splitlines()
    return PathSpec.from_lines("gitwildmatch", patterns)


def scan_tree(root: Path, ignore_spec=None):
    """
    Recursively scan directory tree and emit flat nodes with parent pointers.
    """
    nodes = []
    next_id = 0

    def is_ignored(path: Path):
        if ignore_spec is None:
            return False
        rel = path.relative_to(root)
        return ignore_spec.match_file(str(rel))

    def walk(path: Path, parent_id):
        nonlocal next_id

        if parent_id is not None and is_ignored(path):
            return

        node_id = next_id
        next_id += 1

        is_dir = path.is_dir()
        size = None

        if not is_dir:
            try:
                size = path.stat().st_size
            except OSError:
                size = None

        nodes.append([
            node_id,
            parent_id,
            "d" if is_dir else "f",
            path.name,
            size
        ])

        if is_dir:
            try:
                children = sorted(
                    path.iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower())
                )
            except OSError:
                return

            for child in children:
                walk(child, node_id)

    walk(root, None)
    return nodes


def main():
    parser = argparse.ArgumentParser(
        description="Recursively scan a file tree with parent pointers and optional gitignore-style filtering."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--ignore-file",
        help="Optional gitignore-style file to exclude paths"
    )

    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()

    if not root.exists():
        raise SystemExit(f"Error: path does not exist: {root}")

    ignore_spec = None
    if args.ignore_file:
        ignore_file = Path(args.ignore_file).expanduser().resolve()
        if not ignore_file.exists():
            raise SystemExit(f"Error: ignore file not found: {ignore_file}")
        ignore_spec = load_ignore_spec(ignore_file)

    result = {
        "root": str(root),
        "schema": ["id", "parent_id", "type", "name", "size"],
        "nodes": scan_tree(root, ignore_spec)
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
