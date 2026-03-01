from pathlib import Path

from filescan.graph_builder import GraphBuilder


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

def test_find_symbol_at(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    x = 1\n"
        "    return x\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    node_id = builder.find_symbol_at("a.py", 2)

    assert node_id is not None
    node = builder.ast.nodes[node_id]
    assert node["name"] == "foo"


# =====================================================
# EXTRACT NODE SOURCE (REALISTIC GUARANTEE)
# =====================================================

def test_extract_node_source(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.py").write_text(
        "def foo():\n"
        "    x = 1\n"
        "    return x\n"
    )

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    node_id = builder.find_symbol_at("a.py", 1)
    source = builder.extract_node_source(root, node_id)

    assert source is not None
    assert source.startswith("def foo()")


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