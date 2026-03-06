import types

from filescan.scanner import Scanner


def test_scanner_builds_basic_tree(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.txt").write_text("hello")
    (root / "b.txt").write_text("world")

    sub = root / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("!")

    scanner = Scanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    names = {node["name"] for node in graph.nodes.values()}

    assert "a.txt" in names
    assert "b.txt" in names
    assert "sub" in names
    assert "c.txt" in names


def test_scanner_creates_correct_number_of_nodes_and_edges(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.txt").write_text("x")

    sub = root / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("y")

    scanner = Scanner(root)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    # Expected nodes:
    # root directory
    # a.txt
    # sub directory
    # b.txt
    assert len(graph.nodes) == 4

    # Expected edges:
    # root -> a.txt
    # root -> sub
    # sub -> b.txt
    assert len(graph.edges) == 3


def test_scanner_respects_ignore_file(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    ignore_file = root / ".fscanignore"
    ignore_file.write_text("*.log")

    (root / "keep.txt").write_text("ok")
    (root / "ignore.log").write_text("no")

    scanner = Scanner(root, ignore_file=ignore_file)
    graph = types.SimpleNamespace(nodes={}, edges=[], edge_ids=set())
    scanner.scan_into(graph)

    names = {node["name"] for node in graph.nodes.values()}

    assert "keep.txt" in names
    assert "ignore.log" not in names
