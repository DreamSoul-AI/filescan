from pathlib import Path
import time

from import_src import *
import filescan as fscan


def main():
    # -------------------------------------------------
    # Project root (scan this package itself)
    # -------------------------------------------------
    project_root = Path("../src/filescan").resolve()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Watching project:", project_root)
    print("Output directory :", output_dir)
    print("=" * 60)

    ignore_file = project_root / "default.fscanignore"
    if not ignore_file.exists():
        ignore_file = None

    # -------------------------------------------------
    # Initial full scan (via GraphBuilder)
    # -------------------------------------------------
    print("\nRunning initial scan...\n")

    builder = fscan.GraphBuilder()

    # Build in-memory graph (AST + FS)
    builder.build(
        roots=[project_root],
        ignore_file=ignore_file,
        include_filesystem=True,
        include_ast=True,
    )

    print("\nInitial scan complete.")
    print("Modify any .py file to trigger re-scan.")
    print("Press Ctrl+C to stop.\n")

    # -------------------------------------------------
    # Create watcher (unchanged behavior)
    # -------------------------------------------------
    watcher = fscan.FileWatcher(
        root=project_root,
        ignore_file=ignore_file,
        output="output/filescan",
        debounce_seconds=0.5,
    )

    # -------------------------------------------------
    # Start watching (blocking)
    # -------------------------------------------------
    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()