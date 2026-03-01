from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # -------------------------------------------------
    # Project root (must match AST scan root)
    # -------------------------------------------------
    # root = Path("../src/filescan").resolve()
    root = Path("..").resolve()

    # -------------------------------------------------
    # Load AST graph
    # -------------------------------------------------
    nodes_csv = Path("output/filescan_ast_nodes.csv")
    edges_csv = Path("output/filescan_ast_edges.csv")

    if not nodes_csv.exists() or not edges_csv.exists():
        print("AST graph files not found.")
        print("Please run GraphBuilder.build() first.")
        return

    builder = fscan.GraphBuilder()
    builder.load(nodes_csv, edges_csv, target="ast")

    if not builder.has_ast():
        print("AST graph failed to load.")
        return

    print("AST graph loaded.")
    print("Symbols indexed:", len(builder.ast.by_qname))
    print()

    # -------------------------------------------------
    # Create search engine (AST graph only)
    # -------------------------------------------------
    engine = fscan.SearchEngine(root, builder.ast)

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

        print("=" * 80)
        print(f"[{match_type.upper()}]  {file_path}:{line}")

        if symbol:
            print(f"Symbol: {symbol.get('qualified_name')}")
        else:
            print("Symbol: <no semantic symbol>")

        print(f"Code  : {text}")

        # Extract definition once per symbol
        if sid and sid not in printed_symbols:
            printed_symbols.add(sid)

            snippet = builder.extract_node_source(root, sid)
            if snippet:
                print("\n--- Definition Source ---")
                print(snippet.rstrip())
                print("--- End Definition ---")

        print()

    print("=" * 80)
    print(f"Total results: {len(results)}")


if __name__ == "__main__":
    main()