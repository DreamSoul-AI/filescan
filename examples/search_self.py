from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    root = Path("../src/filescan")

    # -------------------------------------------------
    # Load AST graph (recommended for semantic search)
    # -------------------------------------------------

    nodes_csv = Path("output/filescan_ast_nodes.csv")
    edges_csv = Path("output/filescan_ast_edges.csv")

    graph = fscan.GraphLoader()
    graph.load(nodes_csv, edges_csv)

    print("Graph loaded.")
    print("Semantic graph:", graph.is_semantic_graph())

    # -------------------------------------------------
    # Create search engine
    # -------------------------------------------------

    engine = fscan.SearchEngine(root, graph)

    query = "_add_edge"

    print(f"\nSearching for: {query}\n")

    results = engine.search(query)

    if not results:
        print("No results found.")
        return

    for group in results:
        symbol = group["symbol"]

        if symbol:
            print("Symbol:", symbol.get("qualified_name"))
        else:
            print("Symbol: <unknown / no semantic match>")

        for match in group["matches"]:
            print(
                f"  {match['file']}:{match['line']}  {match['text']}"
            )

        print()


if __name__ == "__main__":
    main()
