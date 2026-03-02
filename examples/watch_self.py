from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # -------------------------------------------------
    # Project root
    # -------------------------------------------------
    project_root = Path("../src/filescan").resolve()
    output_prefix = Path("output/filescan")

    output_prefix.parent.mkdir(exist_ok=True)

    print("=" * 60)
    print("Watching project :", project_root)
    print("Output prefix    :", output_prefix)
    print("=" * 60)

    ignore_file = project_root / "default.fscanignore"
    if not ignore_file.exists():
        ignore_file = None

    # -------------------------------------------------
    # Create watcher
    # -------------------------------------------------
    watcher = fscan.FileWatcher(
        root=project_root,
        ignore_file=ignore_file,
        output=output_prefix,
        debounce_seconds=0.5,
    )

    print("\nStarting watcher (initial build + incremental updates)...")
    print("Modify files to trigger update.")
    print("Press Ctrl+C to stop.\n")

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()