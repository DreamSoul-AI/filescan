from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # -------------------------------------------------
    # Root directory to scan
    # -------------------------------------------------
    root = Path("./data").resolve()
    output_prefix = Path("output/data")

    # Optional ignore file
    ignore_file = Path("data.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Build via GraphBuilder (filesystem only)
    # -------------------------------------------------
    builder = fscan.GraphBuilder()

    builder.build(
        roots=[root],
        ignore_file=ignore_file,
        include_filesystem=True,
        include_ast=False,
    )

    # -------------------------------------------------
    # Export
    # -------------------------------------------------
    builder.export_filesystem(output_prefix)

    print("Scan completed.")
    print("Generated:")
    print("  ", output_prefix.with_name(output_prefix.name + "_nodes.csv"))
    print("  ", output_prefix.with_name(output_prefix.name + "_edges.csv"))
    print("  ", output_prefix.with_suffix(".json"))


if __name__ == "__main__":
    main()