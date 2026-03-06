import types

from filescan.ast_scanner import AstScanner


# -------------------------------------------------
# BASIC SYMBOL EXTRACTION
# -------------------------------------------------

def test_ast_detects_module_and_function(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    file = root / "a.py"
    file.write_text(
        "def hello():\n"
        "    pass\n"
    )

    scanner = AstScanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    kinds = {node["kind"] for node in graph.nodes.values()}
    names = {node["name"] for node in graph.nodes.values()}

    assert "module" in kinds
    assert "function" in kinds
    assert "hello" in names


# -------------------------------------------------
# CLASS + METHOD DETECTION
# -------------------------------------------------

def test_ast_detects_class_and_method(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    file = root / "a.py"
    file.write_text(
        "class MyClass:\n"
        "    def method(self):\n"
        "        pass\n"
    )

    scanner = AstScanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    kinds = {node["kind"] for node in graph.nodes.values()}
    names = {node["name"] for node in graph.nodes.values()}

    assert "class" in kinds
    assert "method" in kinds
    assert "MyClass" in names
    assert "method" in names


# -------------------------------------------------
# FUNCTION CALL DETECTION
# -------------------------------------------------

def test_ast_detects_function_call(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    file = root / "a.py"
    file.write_text(
        "def foo():\n"
        "    pass\n"
        "\n"
        "def bar():\n"
        "    foo()\n"
    )

    scanner = AstScanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    # Check that at least one "calls" relation exists
    assert any(edge["relation"] == "calls" for edge in graph.edges)


# -------------------------------------------------
# INHERITANCE DETECTION
# -------------------------------------------------

def test_ast_detects_inheritance(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    file = root / "a.py"
    file.write_text(
        "class Base:\n"
        "    pass\n"
        "\n"
        "class Child(Base):\n"
        "    pass\n"
    )

    scanner = AstScanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    assert any(edge["relation"] == "inherits" for edge in graph.edges)


# -------------------------------------------------
# QUALIFIED NAME CORRECTNESS
# -------------------------------------------------

def test_ast_qualified_name(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    file = root / "a.py"
    file.write_text(
        "def hello():\n"
        "    pass\n"
    )

    scanner = AstScanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    qualified_names = {node["qualified_name"] for node in graph.nodes.values()}

    # Should include something like proj.a.hello
    assert any("hello" in q for q in qualified_names)


# -------------------------------------------------
# LINE NUMBER VALIDATION
# -------------------------------------------------

def test_ast_line_numbers(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    file = root / "a.py"
    file.write_text(
        "\n"
        "def hello():\n"
        "    pass\n"
    )

    scanner = AstScanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    # Find hello node
    hello_nodes = [
        node for node in graph.nodes.values()
        if node.get("name") == "hello"
    ]
    assert len(hello_nodes) == 1

    hello = hello_nodes[0]

    lineno = hello["lineno"]
    end_lineno = hello["end_lineno"]

    assert lineno == 2
    assert end_lineno >= lineno
