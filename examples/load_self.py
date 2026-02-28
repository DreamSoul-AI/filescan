from pathlib import Path
from import_src import *
import filescan as fscan


# =====================================================
# Generic Printer (works for fs OR ast graph)
# =====================================================

def print_basic_graph_info(name, graph):
    print(f"{name} graph:")
    print("  Nodes loaded:", len(graph.nodes))
    print("  Edges loaded:", len(graph.edges))
    print()


def print_sample_nodes(graph, limit=5):
    print("  Sample nodes:")
    for i, (nid, node) in enumerate(graph.nodes.items()):
        if i >= limit:
            break
        print("   ", nid, node)
    print()


def print_sample_edges(graph, limit=5):
    print("  Sample edges:")
    for i, edge in enumerate(graph.edges):
        if i >= limit:
            break
        print("   ", edge)
    print()


# =====================================================
# Main
# =====================================================

def main():
    builder = fscan.GraphBuilder()

    # -------------------------------------------------
    # Load filesystem graph
    # -------------------------------------------------
    print("Loading filesystem graph...")

    fs_nodes = Path("output/filescan_nodes.csv")
    fs_edges = Path("output/filescan_edges.csv")

    if not fs_nodes.exists() or not fs_edges.exists():
        print("Filesystem graph files not found.")
        return

    builder.load(fs_nodes, fs_edges, target="filesystem")

    print("Filesystem graph loaded.\n")

    print_basic_graph_info("Filesystem", builder.filesystem)
    print_sample_nodes(builder.filesystem)
    print_sample_edges(builder.filesystem)

    # -------------------------------------------------
    # Load AST graph
    # -------------------------------------------------
    print("Loading AST graph...")

    ast_nodes = Path("output/filescan_ast_nodes.csv")
    ast_edges = Path("output/filescan_ast_edges.csv")

    if not ast_nodes.exists() or not ast_edges.exists():
        print("AST graph files not found.")
        return

    builder.load(ast_nodes, ast_edges, target="ast")

    print("AST graph loaded.\n")

    print_basic_graph_info("AST", builder.ast)
    print_sample_nodes(builder.ast)
    print_sample_edges(builder.ast)

    # -------------------------------------------------
    # Example semantic check
    # -------------------------------------------------

    if builder.has_ast():
        print("Semantic indexes:")
        print("  Qualified names indexed:", len(builder.ast.by_qname))
        print("  Files indexed:", len(builder.ast.symbols_by_file))
        print()


if __name__ == "__main__":
    main()