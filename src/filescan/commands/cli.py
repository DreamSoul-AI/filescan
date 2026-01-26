import argparse
from pathlib import Path
from ..scanner import Scanner


DEFAULT_IGNORE_NAME = ".fscanignore"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recursively scan a directory and export its structure "
            "as a flat graph (CSV or JSON)."
        )
    )

    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )

    parser.add_argument(
        "--ignore-file",
        help=(
            "Path to a gitignore-style file for excluding paths "
            f"(default: {DEFAULT_IGNORE_NAME} if present in root)"
        ),
    )

    parser.add_argument(
        "-o", "--output",
        help=(
            "Output file path. "
            "If omitted, defaults to <root_basename>.csv or .json"
        ),
    )

    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )

    args = parser.parse_args()

    # Resolve root
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    # Resolve ignore file
    if args.ignore_file:
        ignore_file = Path(args.ignore_file).expanduser().resolve()
    else:
        candidate = Path.cwd() / DEFAULT_IGNORE_NAME
        ignore_file = candidate if candidate.exists() else None

    scanner = Scanner(root, ignore_file=ignore_file)
    scanner.scan()

    # Dispatch output
    if args.format == "csv":
        scanner.to_csv(args.output)

    elif args.format == "json":
        scanner.to_json(args.output)
    return


if __name__ == "__main__":
    main()
