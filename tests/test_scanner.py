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
    nodes = scanner.scan()

    names = {row[2] for row in nodes}  # name column

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
    scanner.scan()

    # Expected nodes:
    # root directory
    # a.txt
    # sub directory
    # b.txt
    assert len(scanner._nodes) == 4

    # Expected edges:
    # root -> a.txt
    # root -> sub
    # sub -> b.txt
    assert len(scanner._edges) == 3


def test_scanner_respects_ignore_file(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    ignore_file = root / ".fscanignore"
    ignore_file.write_text("*.log")

    (root / "keep.txt").write_text("ok")
    (root / "ignore.log").write_text("no")

    scanner = Scanner(root, ignore_file=ignore_file)
    nodes = scanner.scan()

    names = {row[2] for row in nodes}

    assert "keep.txt" in names
    assert "ignore.log" not in names