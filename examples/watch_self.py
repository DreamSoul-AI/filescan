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

    # -------------------------------------------------
    # Create watcher
    # -------------------------------------------------
    watcher = fscan.FileWatcher(
        root=project_root,
        ignore_file=project_root / "default.fscanignore",
        output=output_dir,
        debounce_seconds=0.5,
    )

    # -------------------------------------------------
    # Initial full scan
    # -------------------------------------------------
    print("\nRunning initial scan...\n")

    fs = fscan.Scanner(
        root=project_root,
        ignore_file=project_root / "default.fscanignore",
        output='output/filescan',
    )
    fs.scan()
    fs.to_csv()

    ast = fscan.AstScanner(
        root=project_root,
        ignore_file=project_root / "default.fscanignore",
        output='output/filescan_ast',
    )
    ast.scan()
    ast.to_csv()

    print("\nInitial scan complete.")
    print("Modify any .py file to trigger re-scan.")
    print("Press Ctrl+C to stop.\n")

    # -------------------------------------------------
    # Start watching (blocking)
    # -------------------------------------------------
    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()