from pathlib import Path
import filescan as fscan


def main():
    # -------------------------------------------------
    # Project root (MUST match original AST scan root)
    # -------------------------------------------------
    # root = Path("..").resolve()
    root = Path("../src/filescan")

    # -------------------------------------------------
    # Locate exported AST graph
    # -------------------------------------------------
    nodes_csv = Path("output/filescan_ast_nodes.csv")
    edges_csv = Path("output/filescan_ast_edges.csv")

    if not nodes_csv.exists() or not edges_csv.exists():
        print("❌ AST graph files not found.")
        print("Run GraphBuilder.build(...) and export_ast(...) first.")
        return

    # -------------------------------------------------
    # Load AST graph
    # -------------------------------------------------
    builder = fscan.GraphBuilder()
    builder.load(nodes_csv, edges_csv, target="ast")

    if not builder.has_ast():
        print("❌ AST graph failed to load.")
        return

    print("✅ AST graph loaded.")
    print(f"Indexed symbols: {len(builder.ast.by_qname)}")
    print()

    # -------------------------------------------------
    # Create Search Engine (AST graph only)
    # -------------------------------------------------
    engine = fscan.SearchEngine(root, builder.ast)

    query = "_add_symbol"
    print(f"🔎 Searching for: {query}\n")

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

        # -------------------------------------------------
        # Extract definition once per symbol
        # -------------------------------------------------
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