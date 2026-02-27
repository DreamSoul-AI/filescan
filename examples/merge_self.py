from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # Root directory to scan
    root = Path("../src/filescan")

    # Optional ignore file (CWD-based, same logic as CLI)
    ignore_file = Path("self.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    # -------------------------------------------------
    # Filesystem scan (same as your script)
    # -------------------------------------------------
    scanner = fscan.Scanner([root], ignore_file=ignore_file, output="output/filescan")
    scanner.scan()
    scanner.to_csv()
    scanner.to_json()

    print("Scan completed.")
    print("Generated: filescan")

    # -------------------------------------------------
    # AST scan (same as your script)
    # -------------------------------------------------
    ast_scanner = fscan.AstScanner([root], ignore_file=ignore_file, output="output/filescan_ast")
    ast_scanner.scan()
    ast_scanner.to_csv()
    ast_scanner.to_json()

    print("AST scan completed.")
    print("Generated: filescan_ast")

    # -------------------------------------------------
    # Merge / concat (DONE INSIDE GraphLoader.merge)
    # -------------------------------------------------
    fs_nodes = Path("output/filescan_nodes.csv")
    fs_edges = Path("output/filescan_edges.csv")
    ast_nodes = Path("output/filescan_ast_nodes.csv")
    ast_edges = Path("output/filescan_ast_edges.csv")

    merged_out = Path("output/filescan_merged.csv")

    graph = fscan.GraphLoader()

    # Your GraphLoader.merge does concatenation into one file
    # AST can be None — but here we scanned it, so we pass paths.
    graph.merge(
        fs_nodes_path=fs_nodes,
        fs_edges_path=fs_edges,
        output_path=merged_out,
        ast_nodes_path=ast_nodes,
        ast_edges_path=ast_edges,
    )

    print("Merge completed.")
    print(f"Generated: {merged_out}")


if __name__ == "__main__":
    main()