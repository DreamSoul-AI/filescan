from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # This MUST match the root used during AST scanning
    project_root = Path("../src/filescan").resolve()

    # Search root should match scan root
    root = project_root

    # -------------------------------------------------
    # Load AST graph
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

    query = "_add_symbol"
    print(f"\nSearching for: {query}\n")

    results = engine.search(query)

    if not results:
        print("No results found.")
        return

    printed_symbols = set()

    for r in results:
        symbol = r["symbol"]
        sid = r["symbol_id"]

        if symbol:
            print("Symbol:", symbol.get("qualified_name"))
        else:
            print("Symbol: <unknown / no semantic match>")

        print(f"  {r['file']}:{r['line']}  {r['text']}")

        # Extract symbol source only once per symbol
        if sid and sid not in printed_symbols:
            printed_symbols.add(sid)

            snippet = graph.extract_node_source(project_root, sid)
            if snippet:
                print("\n--- Extracted Symbol Source ---")
                print(snippet.rstrip())
                print("--- End ---\n")
            else:
                print("\n(No extractable source)\n")

        print()


if __name__ == "__main__":
    main()
