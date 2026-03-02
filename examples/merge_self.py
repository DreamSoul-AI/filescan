from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # root = Path("../src/filescan").resolve()
    root = Path("..").resolve()

    ignore_file = Path("self.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    # ---------------------------------------------
    # Build both graphs using GraphBuilder
    # ---------------------------------------------
    builder = fscan.GraphBuilder()

    builder.build(
        roots=[root],
        ignore_file=ignore_file,
        include_filesystem=True,
        include_ast=True,
    )

    # ---------------------------------------------
    # Export graphs
    # ---------------------------------------------
    builder.export_filesystem("output/filescan")
    builder.export_ast("output/filescan_ast")

    # ---------------------------------------------
    # Merge context
    # ---------------------------------------------
    builder.export_context_merged(
        "output/filescan_merged.csv",
        fs_nodes_path=Path("output/filescan_nodes.csv"),
        fs_edges_path=Path("output/filescan_edges.csv"),
        ast_nodes_path=Path("output/filescan_ast_nodes.csv"),
        ast_edges_path=Path("output/filescan_ast_edges.csv"),
    )

    print("Context merge completed.")


if __name__ == "__main__":
    main()