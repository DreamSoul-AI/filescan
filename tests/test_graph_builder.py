from pathlib import Path

from filescan.graph_builder import GraphBuilder
from filescan.search_engine import SearchEngine


# =====================================================
# BUILD + AST INGESTION
# =====================================================

def test_graph_builder_ingests_ast(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    pass\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    assert builder.has_ast()
    assert len(builder.ast.nodes) > 0
    assert len(builder.ast.edges) > 0


# =====================================================
# INDEX BUILDING
# =====================================================

def test_ast_indexes(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    pass\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    # by_qname
    assert "proj.a.foo" in builder.ast.by_qname

    # by_name
    assert "foo" in builder.ast.by_name
    assert len(builder.ast.by_name["foo"]) == 1


# =====================================================
# ADJACENCY INDEXES
# =====================================================

def test_adjacency_consistency(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    pass\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    for edge in builder.ast.edges:
        assert edge in builder.ast.out_edges[edge["source"]]
        assert edge in builder.ast.in_edges[edge["target"]]


# =====================================================
# FIND SYMBOL AT LINE
# =====================================================

def test_symbol_index_supports_find_symbol_at(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    x = 1\n"
        "    return x\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    engine = SearchEngine(root, builder.ast)
    node_id = engine._find_symbol_at("a.py", 2)

    assert node_id is not None
    node = builder.ast.nodes[node_id]
    assert node["name"] == "foo"


# =====================================================
# EXTRACT NODE SOURCE (REALISTIC GUARANTEE)
# =====================================================

def test_ast_symbols_by_file_index_contains_ranges(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    x = 1\n"
        "    return x\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    entries = builder.ast.symbols_by_file.get("a.py", [])
    assert entries

    foo_entries = []
    for start, end, nid in entries:
        node = builder.ast.nodes[nid]
        if node.get("name") == "foo":
            foo_entries.append((start, end))

    assert foo_entries
    start, end = foo_entries[0]
    assert start == 1
    assert end >= start


# =====================================================
# IMPORT + REFERENCE EDGE CHECK
# =====================================================

def test_import_and_reference_edges(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    pass\n"
    )

    (root / "b.py").write_text(
        "from proj.a import foo\n"
        "\n"
        "def bar():\n"
        "    foo()\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    relations = {e["relation"] for e in builder.ast.edges}

    # We expect syntactic linking, not guaranteed inference-based calls
    assert "imports" in relations
    assert "references" in relations


# =====================================================
# GRAPH DETERMINISM (CRITICAL INVARIANT)
# =====================================================

def test_graph_is_deterministic(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text("def foo(): pass\n")

    b1 = GraphBuilder().build([root], include_ast=True)
    b2 = GraphBuilder().build([root], include_ast=True)

    assert b1.ast.nodes == b2.ast.nodes
    assert b1.ast.edges == b2.ast.edges


def test_export_ast_mermaid_from_graph(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "class B:\n"
        "    def ping(self):\n"
        "        return 1\n"
        "\n"
        "class A:\n"
        "    def _hidden(self):\n"
        "        return 0\n"
        "\n"
        "    def run(self):\n"
        "        b = B()\n"
        "        return b.ping()\n",
        encoding="utf-8",
    )

    builder = GraphBuilder().build([root], include_ast=True)
    output = builder.export_ast_mermaid(tmp_path / "output" / "filescan_uml.md")

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "classDiagram" in content
    assert "class A {" in content
    assert "class B {" in content
    assert "+run()" in content
    assert "_hidden" not in content
    assert "A --> B" in content
