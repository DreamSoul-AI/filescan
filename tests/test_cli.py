import types
from pathlib import Path

import pytest

from filescan.commands.cli import (
    cmd_scan,
    cmd_watch,
    cmd_search,
    cmd_context,
    cmd_uml,
    main,
)


# =====================================================
# Helpers
# =====================================================

class DummyScanner:
    def __init__(self, *args, **kwargs):
        self.called = []

    def scan(self):
        self.called.append("scan")

    def to_csv(self):
        self.called.append("csv")

    def to_json(self):
        self.called.append("json")


class DummyWatcher:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        raise KeyboardInterrupt


class DummySearchEngine:
    def __init__(self, root, graph):
        self.root = root
        self.graph = graph

    def search(self, query):
        return [
            {
                "file": str(Path(self.root) / "a.py"),
                "line": 1,
                "text": "def foo():",
                "match_type": "definition",
                "symbol": {"qualified_name": "proj.a.foo"},
                "symbol_id": "123",
            }
        ]


class DummyBuilder:
    def __init__(self):
        self.ast = types.SimpleNamespace()
        self.ast.nodes = {"123": {"qualified_name": "proj.a.foo"}}
        self.ast.edges = []
        self.ast.by_name = {"foo": ["123"]}
        self.ast.symbols_by_file = {}
        self._has_ast = True
        self.calls = []

    def build(self, roots, ignore_file=None, **kwargs):
        self.calls.append(("build", roots, ignore_file, kwargs))
        return self

    def export_filesystem(self, output_prefix):
        self.calls.append(("export_filesystem", output_prefix))

    def export_ast(self, output_prefix):
        self.calls.append(("export_ast", output_prefix))

    def export_ast_mermaid(self, output_path, **kwargs):
        self.calls.append(("export_ast_mermaid", output_path, kwargs))
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# AST UML\n")
        return out

    def load(self, *args, **kwargs):
        return self

    def has_ast(self):
        return self._has_ast

    def extract_node_source(self, root, sid):
        return "def foo():\n    pass\n"

    def export_context_merged(self, **kwargs):
        Path(kwargs["output_path"]).write_text("merged")


# =====================================================
# SCAN COMMAND
# =====================================================

def test_cmd_scan(monkeypatch, tmp_path):
    root = tmp_path
    args = types.SimpleNamespace(
        root=str(root),
        ignore_file=None,
        ast=False,
        ast_only=False,
        output="graph",
        output_ast=None,
    )

    dummy = DummyBuilder()
    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", lambda: dummy)

    cmd_scan(args)

    assert any(c[0] == "build" for c in dummy.calls)
    assert any(c[0] == "export_filesystem" for c in dummy.calls)


def test_cmd_scan_default_output_uses_root_name(monkeypatch, tmp_path):
    root = tmp_path
    args = types.SimpleNamespace(
        root=str(root),
        ignore_file=None,
        ast=False,
        ast_only=False,
        output=None,
        output_ast=None,
    )

    dummy = DummyBuilder()
    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", lambda: dummy)

    cmd_scan(args)

    fs_calls = [c for c in dummy.calls if c[0] == "export_filesystem"]
    assert len(fs_calls) == 1
    assert fs_calls[0][1] == root.name


def test_main_scan_defaults_root_to_current_dir(monkeypatch):
    called = {}

    def fake_cmd_scan(args):
        called["root"] = args.root

    monkeypatch.setattr("filescan.commands.cli.cmd_scan", fake_cmd_scan)
    monkeypatch.setattr("sys.argv", ["filescan", "scan"])

    main()

    assert called["root"] == "."


# =====================================================
# WATCH COMMAND
# =====================================================

def test_cmd_watch(monkeypatch, tmp_path):
    root = tmp_path
    args = types.SimpleNamespace(
        root=str(root),
        ignore_file=None,
        output="graph",
        output_ast=None,
        debounce=0.1,
    )

    monkeypatch.setattr("filescan.commands.cli.FileWatcher", DummyWatcher)

    # Should not crash (KeyboardInterrupt handled)
    cmd_watch(args)


# =====================================================
# SEARCH COMMAND
# =====================================================

def test_cmd_search(monkeypatch, tmp_path, capsys):
    root = tmp_path
    nodes = tmp_path / "nodes.csv"
    edges = tmp_path / "edges.csv"

    nodes.write_text("dummy")
    edges.write_text("dummy")

    args = types.SimpleNamespace(
        root=str(root),
        query="foo",
        nodes=str(nodes),
        edges=str(edges),
    )

    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", DummyBuilder)
    monkeypatch.setattr("filescan.commands.cli.SearchEngine", DummySearchEngine)

    cmd_search(args)

    captured = capsys.readouterr()
    assert "DEFINITION" in captured.out
    assert "proj.a.foo" in captured.out


# =====================================================
# CONTEXT COMMAND
# =====================================================

def test_cmd_context(monkeypatch, tmp_path, capsys):
    fs_nodes = tmp_path / "fs_nodes.csv"
    fs_edges = tmp_path / "fs_edges.csv"

    fs_nodes.write_text("dummy")
    fs_edges.write_text("dummy")

    out = tmp_path / "out.txt"

    args = types.SimpleNamespace(
        fs_nodes=str(fs_nodes),
        fs_edges=str(fs_edges),
        ast_nodes=None,
        ast_edges=None,
        output=str(out),
    )

    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", DummyBuilder)

    cmd_context(args)

    captured = capsys.readouterr()
    assert "Wrote context to" in captured.out
    assert out.exists()


def test_cmd_uml(monkeypatch, tmp_path, capsys):
    root = tmp_path
    out = tmp_path / "diagram.md"

    args = types.SimpleNamespace(
        root=str(root),
        ignore_file=None,
        output=str(out),
        show_private=True,
        module_path_filter="src/app",
        title="Project UML",
    )

    dummy = DummyBuilder()
    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", lambda: dummy)

    cmd_uml(args)

    assert any(c[0] == "build" for c in dummy.calls)
    uml_calls = [c for c in dummy.calls if c[0] == "export_ast_mermaid"]
    assert len(uml_calls) == 1
    _, output_path, kwargs = uml_calls[0]
    assert output_path == str(out)
    assert kwargs["show_private"] is True
    assert kwargs["module_path_filter"] == "src/app"
    assert kwargs["title"] == "Project UML"

    captured = capsys.readouterr()
    assert "Wrote Mermaid UML to" in captured.out
