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
    nodes = scanner.scan()

    kinds = {row[1] for row in nodes}
    names = {row[2] for row in nodes}

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
    nodes = scanner.scan()

    kinds = {row[1] for row in nodes}
    names = {row[2] for row in nodes}

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
    scanner.scan()

    edges = scanner._edges

    # Check that at least one "calls" relation exists
    assert any(edge[3] == "calls" for edge in edges)


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
    scanner.scan()

    edges = scanner._edges

    assert any(edge[3] == "inherits" for edge in edges)


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
    nodes = scanner.scan()

    qualified_names = {row[3] for row in nodes}

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
    nodes = scanner.scan()

    # Find hello node
    hello_nodes = [row for row in nodes if row[2] == "hello"]
    assert len(hello_nodes) == 1

    hello = hello_nodes[0]

    lineno = hello[5]
    end_lineno = hello[6]

    assert lineno == 2
    assert end_lineno >= lineno