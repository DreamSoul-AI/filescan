from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # Root directory to scan
    # root = Path("..").resolve()
    root = Path("../src/filescan")

    # Optional ignore file
    ignore_file = Path("self.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    # Create graph builder
    builder = fscan.GraphBuilder()

    # Build both graphs
    builder.build(
        roots=[root],
        ignore_file=ignore_file,
        include_filesystem=True,
        include_ast=True,
    )

    # Export filesystem graph
    builder.export_filesystem("output/filescan")

    print("Filesystem scan completed.")
    print("Generated: output/filescan_nodes.csv")
    print("Generated: output/filescan_edges.csv")
    print("Generated: output/filescan.json")

    # Export AST graph
    builder.export_ast("output/filescan_ast")

    print("AST scan completed.")
    print("Generated: output/filescan_ast_nodes.csv")
    print("Generated: output/filescan_ast_edges.csv")
    print("Generated: output/filescan_ast.json")


if __name__ == "__main__":
    main()