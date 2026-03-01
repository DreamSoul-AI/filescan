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
    # Build using scanners directly (export CSV)
    # ---------------------------------------------
    scanner = fscan.Scanner([root], ignore_file=ignore_file, output="output/filescan")
    scanner.scan()
    scanner.to_csv()

    ast_scanner = fscan.AstScanner([root], ignore_file=ignore_file, output="output/filescan_ast")
    ast_scanner.scan()
    ast_scanner.to_csv()

    # ---------------------------------------------
    # Merge context
    # ---------------------------------------------
    builder = fscan.GraphBuilder()

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