import argparse
from pathlib import Path

from ..graph_builder import GraphBuilder
from ..search_engine import SearchEngine
from ..file_watcher import FileWatcher


DEFAULT_IGNORE_NAME = ".fscanignore"


# =====================================================
# Helpers
# =====================================================

def resolve_ignore_file(root: Path, ignore_arg: str | None):
    if ignore_arg:
        return Path(ignore_arg).expanduser().resolve()
    candidate = root / DEFAULT_IGNORE_NAME
    return candidate if candidate.exists() else None


# =====================================================
# Scan Command
# =====================================================

def cmd_scan(args):
    root = Path(args.root).expanduser().resolve()
    ignore_file = resolve_ignore_file(root, args.ignore_file)

    include_filesystem = not args.ast_only
    include_ast = bool(args.ast or args.ast_only)

    builder = GraphBuilder()
    builder.build(
        [root],
        ignore_file=ignore_file,
        include_filesystem=include_filesystem,
        include_ast=include_ast,
    )

    if include_filesystem:
        builder.export_filesystem(args.output)

    if include_ast:
        builder.export_ast(args.output_ast or args.output)


# =====================================================
# Watch Command
# =====================================================

def cmd_watch(args):
    root = Path(args.root).expanduser().resolve()
    ignore_file = resolve_ignore_file(root, args.ignore_file)

    watcher = FileWatcher(
        root=root,
        ignore_file=ignore_file,
        output=args.output,
        debounce_seconds=args.debounce,
    )

    if args.output_ast:
        watcher.output_ast = Path(args.output_ast).expanduser().resolve()

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


# =====================================================
# Search Command
# =====================================================

def cmd_search(args):
    root = Path(args.root).expanduser().resolve()

    nodes_csv = Path(args.nodes)
    edges_csv = Path(args.edges)

    if not nodes_csv.exists() or not edges_csv.exists():
        raise SystemExit("AST graph CSV files not found.")

    # Load AST graph into builder
    builder = GraphBuilder()
    builder.load(nodes_csv, edges_csv, target="ast")

    if not builder.has_ast():
        raise SystemExit("Failed to load AST graph.")

    engine = SearchEngine(root, builder.ast)

    results = engine.search(args.query)

    if not results:
        print("No results found.")
        return

    printed_symbols = set()

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


# =====================================================
# Context Command
# =====================================================

def cmd_context(args):
    """
    Concatenate FS and AST CSV graphs into one context file.
    """

    fs_nodes = Path(args.fs_nodes)
    fs_edges = Path(args.fs_edges)

    if not fs_nodes.exists() or not fs_edges.exists():
        raise SystemExit("Filesystem graph CSV files not found.")

    ast_nodes = Path(args.ast_nodes) if args.ast_nodes else None
    ast_edges = Path(args.ast_edges) if args.ast_edges else None

    if (ast_nodes is None) != (ast_edges is None):
        raise SystemExit("Provide both --ast-nodes and --ast-edges, or neither.")

    if ast_nodes and (not ast_nodes.exists() or not ast_edges.exists()):
        raise SystemExit("AST graph CSV files not found.")

    out_path = Path(args.output)

    builder = GraphBuilder()

    builder.export_context_merged(
        output_path=out_path,
        fs_nodes_path=fs_nodes,
        fs_edges_path=fs_edges,
        ast_nodes_path=ast_nodes,
        ast_edges_path=ast_edges,
    )

    print(f"Wrote context to: {out_path}")


# =====================================================
# UML Command
# =====================================================

def cmd_uml(args):
    root = Path(args.root).expanduser().resolve()
    ignore_file = resolve_ignore_file(root, args.ignore_file)

    builder = GraphBuilder()
    builder.build(
        [root],
        ignore_file=ignore_file,
        include_filesystem=False,
        include_ast=True,
    )

    output = builder.export_ast_mermaid(
        args.output,
        show_private=args.show_private,
        module_path_filter=args.module_path_filter,
        title=args.title,
    )

    print(f"Wrote Mermaid UML to: {output}")


# =====================================================
# CLI
# =====================================================

def main():
    parser = argparse.ArgumentParser(prog="fscan")
    sub = parser.add_subparsers(dest="command", required=True)

    # ----------------------
    # scan
    # ----------------------
    scan = sub.add_parser("scan", help="Run filesystem and/or AST scan")
    scan.add_argument("root", help="Root directory to scan")
    scan.add_argument("--ignore-file")
    scan.add_argument("--ast", action="store_true", help="Include AST scan")
    scan.add_argument("--ast-only", action="store_true", help="Only run AST scan")
    scan.add_argument("-o", "--output", default="graph")
    scan.add_argument("--output-ast", help="Separate output prefix for AST scan")
    scan.set_defaults(func=cmd_scan)

    # ----------------------
    # watch
    # ----------------------
    watch = sub.add_parser("watch", help="Watch project and auto-rescan")
    watch.add_argument("root", help="Root directory to watch")
    watch.add_argument("--ignore-file")
    watch.add_argument("-o", "--output", default="graph")
    watch.add_argument("--output-ast")
    watch.add_argument("--debounce", type=float, default=0.5)
    watch.set_defaults(func=cmd_watch)

    # ----------------------
    # search
    # ----------------------
    search = sub.add_parser("search", help="Search existing AST graph")
    search.add_argument("root", help="Project root (must match AST scan root)")
    search.add_argument("query", help="Search query")
    search.add_argument("--nodes", required=True, help="Path to AST *_nodes.csv")
    search.add_argument("--edges", required=True, help="Path to AST *_edges.csv")
    search.set_defaults(func=cmd_search)

    # ----------------------
    # context
    # ----------------------
    context = sub.add_parser(
        "context",
        help="Concatenate FS/AST CSV graphs into one context file",
    )
    context.add_argument("--fs-nodes", required=True)
    context.add_argument("--fs-edges", required=True)
    context.add_argument("--ast-nodes")
    context.add_argument("--ast-edges")
    context.add_argument("-o", "--output", required=True)
    context.set_defaults(func=cmd_context)

    # ----------------------
    # uml
    # ----------------------
    uml = sub.add_parser("uml", help="Export Mermaid class diagram from AST graph")
    uml.add_argument("root", help="Root directory to scan")
    uml.add_argument("--ignore-file")
    uml.add_argument(
        "-o",
        "--output",
        default="graph_uml.md",
        help="Path to output markdown file",
    )
    uml.add_argument(
        "--show-private",
        action="store_true",
        help="Include private methods in class diagrams",
    )
    uml.add_argument(
        "--module-path-filter",
        help="Only include AST nodes whose module_path contains this text",
    )
    uml.add_argument(
        "--title",
        default="AST UML",
        help="Markdown title",
    )
    uml.set_defaults(func=cmd_uml)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
