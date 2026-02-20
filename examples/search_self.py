from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # -------------------------------------------------
    # Project root (must match AST scan root)
    # -------------------------------------------------
    project_root = Path("../src/filescan").resolve()
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

    # -------------------------------------------------
    # Pretty Output
    # -------------------------------------------------
    for r in results:
        file_path = r["file"]
        line = r["line"]
        text = r["text"]
        match_type = r.get("match_type", "unknown")
        symbol = r.get("symbol")
        sid = r.get("symbol_id")

        # ---- Header ----
        print("=" * 80)
        print(f"[{match_type.upper()}]  {file_path}:{line}")

        # ---- Symbol Info ----
        if symbol:
            print(f"Symbol: {symbol.get('qualified_name')}")
        else:
            print("Symbol: <no semantic symbol>")

        # ---- Matched Line ----
        print(f"Code  : {text}")

        # ---- Extract Definition (once per symbol) ----
        if sid and sid not in printed_symbols:
            printed_symbols.add(sid)

            snippet = graph.extract_node_source(project_root, sid)
            if snippet:
                print("\n--- Definition Source ---")
                print(snippet.rstrip())
                print("--- End Definition ---")

        print()

    print("=" * 80)
    print(f"Total results: {len(results)}")


if __name__ == "__main__":
    main()