from pathlib import Path
from import_src import *
import filescan as fscan


def print_basic_graph_info(graph):
    print("Nodes loaded:", len(graph.nodes))
    print("Edges loaded:", len(graph.edges))
    print("Semantic graph:", graph.is_semantic_graph())
    print()


def print_sample_nodes(graph, limit=5):
    print("Sample nodes:")
    for i, (nid, node) in enumerate(graph.nodes.items()):
        if i >= limit:
            break
        print("  ", nid, node)
    print()


def print_sample_edges(graph, limit=5):
    print("Sample edges:")
    for i, edge in enumerate(graph.edges):
        if i >= limit:
            break
        print("  ", edge)
    print()


def main():
    graph = fscan.GraphBuilder()

    # -------------------------------------------------
    # Load filesystem graph
    # -------------------------------------------------
    print("Loading filesystem graph...")

    fs_nodes = Path("output/filescan_nodes.csv")
    fs_edges = Path("output/filescan_edges.csv")

    if not fs_nodes.exists() or not fs_edges.exists():
        print("Filesystem graph files not found.")
        return

    graph.load(fs_nodes, fs_edges)

    print("Filesystem graph loaded.")
    print_basic_graph_info(graph)
    print_sample_nodes(graph)
    print_sample_edges(graph)

    # -------------------------------------------------
    # Load AST graph (same instance reused)
    # -------------------------------------------------
    print("Loading AST graph...")

    ast_nodes = Path("output/filescan_ast_nodes.csv")
    ast_edges = Path("output/filescan_ast_edges.csv")

    if not ast_nodes.exists() or not ast_edges.exists():
        print("AST graph files not found.")
        return

    graph.load(ast_nodes, ast_edges)

    print("AST graph loaded.")
    print_basic_graph_info(graph)
    print_sample_nodes(graph)
    print_sample_edges(graph)

    # Example semantic check
    if graph.is_semantic_graph():
        print("Example semantic lookup:")
        print("Symbols indexed:", len(graph.by_qname))
        print("Files indexed:", len(graph.symbols_by_file))
        print()


if __name__ == "__main__":
    main()