from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # root = Path("..").resolve()
    root = Path("../src/filescan")

    ignore_file = Path("self.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    builder = fscan.GraphBuilder()
    builder.build(
        roots=[root],
        ignore_file=ignore_file,
        include_filesystem=False,
        include_ast=True,
    )

    output_path = builder.export_ast_mermaid("output/filescan_uml.md")
    print(f"UML written to: {output_path}")


if __name__ == "__main__":
    main()
